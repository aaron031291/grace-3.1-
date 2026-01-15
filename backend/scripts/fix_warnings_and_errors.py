#!/usr/bin/env python
"""
Script to fix remaining warnings and silent errors.

1. Fix datetime.now(UTC) warnings (respecting user reverts)
2. Fix silent errors (bare except clauses)
3. Fix Pydantic deprecation warnings
"""

import re
from pathlib import Path
from typing import List, Tuple, Set

# Files to skip (user reverted changes)
SKIP_FILES = {
    'backend/genesis/genesis_key_service.py',
    'genesis/genesis_key_service.py',
}

def fix_datetime_utcnow(file_path: Path) -> Tuple[int, List[str]]:
    """Fix datetime.now(UTC) calls in a file."""
    if any(skip in str(file_path) for skip in SKIP_FILES):
        return 0, ["Skipped (user preference)"]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return 0, [f"Error reading: {e}"]
    
    if 'datetime.now(UTC)' not in content:
        return 0, []
    
    original_content = content
    replacement_count = 0
    
    # Fix imports
    if 'from datetime import' in content:
        if re.search(r'from datetime import datetime(?![\s,]*UTC)', content):
            if 'UTC' not in content or not re.search(r'from datetime import[^;]*UTC', content):
                content = re.sub(
                    r'from datetime import datetime(?![\s,]*UTC)',
                    r'from datetime import datetime, UTC',
                    content,
                    count=1
                )
        
        if re.search(r'from datetime import datetime, timedelta, UTC(?![\s,]*UTC)', content):
            content = re.sub(
                r'from datetime import datetime, timedelta(?![\s,]*UTC)',
                r'from datetime import datetime, timedelta, UTC',
                content,
                count=1
            )
    
    # Fix datetime.now(UTC) calls
    count_before = content.count('datetime.now(UTC)')
    content = content.replace('datetime.now(UTC)', 'datetime.now(UTC)')
    replacement_count += count_before
    
    # Fix SQLAlchemy defaults
    content = re.sub(
        r'default=datetime\.utcnow(?!\()',
        r'default=lambda: datetime.now(UTC)',
        content
    )
    content = re.sub(
        r'onupdate=datetime\.utcnow(?!\()',
        r'onupdate=lambda: datetime.now(UTC)',
        content
    )
    
    # Fix default_factory
    content = re.sub(
        r'default_factory=datetime\.utcnow(?!\()',
        r'default_factory=lambda: datetime.now(UTC)',
        content
    )
    
    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return replacement_count, [f"Fixed {replacement_count} instances"]
        except Exception as e:
            return 0, [f"Error writing: {e}"]
    
    return 0, []


def fix_silent_errors(file_path: Path) -> Tuple[int, List[str]]:
    """Fix bare except clauses by adding logging."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return 0, []
    
    original_lines = lines.copy()
    changes = []
    import logging_added = False
    
    # Check if logging is imported
    has_logging = any('import logging' in line or 'from logging import' in line for line in lines)
    
    # Find bare except clauses
    for i, line in enumerate(lines):
        # Match: except: or except : (with optional whitespace)
        if re.match(r'^\s*except\s*:\s*$', line):
            # Get next line to see what happens
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                indent = len(line) - len(line.lstrip())
                
                # If it's just pass, add logging
                if 'pass' in next_line.strip():
                    if not has_logging and not logging_added:
                        # Add logging import at top
                        for j, import_line in enumerate(lines):
                            if 'import ' in import_line and j < 20:
                                lines.insert(j + 1, 'import logging\n')
                                logging_added = True
                                has_logging = True
                                break
                    
                    # Replace bare except with logged exception
                    logger_name = 'logger' if has_logging else 'logging'
                    lines[i] = line.rstrip() + f'  # Silent error - consider logging\n'
                    lines[i + 1] = ' ' * indent + f'{logger_name}.debug("Silent exception caught", exc_info=True)\n' + next_line
                    changes.append(f"Line {i+1}: Added logging to bare except")
                elif 'continue' in next_line.strip() or 'return' in next_line.strip():
                    # For continue/return, add minimal logging
                    if not has_logging and not logging_added:
                        for j, import_line in enumerate(lines):
                            if 'import ' in import_line and j < 20:
                                lines.insert(j + 1, 'import logging\n')
                                logging_added = True
                                has_logging = True
                                break
                    
                    logger_name = 'logger' if has_logging else 'logging'
                    lines[i] = line.rstrip() + f'  # Silent error - consider logging\n'
                    changes.append(f"Line {i+1}: Marked bare except for review")
    
    if lines != original_lines:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return len(changes), changes
        except Exception as e:
            return 0, [f"Error writing: {e}"]
    
    return 0, []


def fix_pydantic_config(file_path: Path) -> Tuple[int, List[str]]:
    """Fix Pydantic class-based config deprecation."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return 0, []
    
    if 'class Config:' not in content or 'ConfigDict' in content:
        return 0, []
    
    original_content = content
    changes = []
    
    # Pattern: class SomeModel(BaseModel): ... class Config: ...
    # Replace with: ConfigDict
    
    # Find class Config: blocks inside BaseModel classes
    pattern = r'(class\s+\w+\([^)]*BaseModel[^)]*\):.*?)(\s+class\s+Config\s*:.*?)(\n\s+[A-Z])'
    
    def replace_config(match):
        model_def = match.group(1)
        config_block = match.group(2)
        next_class = match.group(3)
        
        # Extract config fields
        config_lines = config_block.split('\n')
        config_dict_items = []
        for line in config_lines[1:]:  # Skip "class Config:"
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().rstrip(',')
                    config_dict_items.append(f"        {key}={value}")
        
        if config_dict_items:
            configdict = "    model_config = ConfigDict(\n" + ",\n".join(config_dict_items) + "\n    )"
            return model_def + configdict + next_class
        return match.group(0)
    
    # Simple replacement for common cases
    content = re.sub(
        r'class\s+Config\s*:\s*\n\s+orm_mode\s*=\s*True',
        'model_config = ConfigDict(from_attributes=True)',
        content
    )
    
    content = re.sub(
        r'class\s+Config\s*:\s*\n\s+from_attributes\s*=\s*True',
        'model_config = ConfigDict(from_attributes=True)',
        content
    )
    
    if content != original_content:
        # Add ConfigDict import if needed
        if 'ConfigDict' not in content and 'from pydantic import' in content:
            content = re.sub(
                r'from pydantic import ([^,\n]+)',
                r'from pydantic import \1, ConfigDict',
                content,
                count=1
            )
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return 1, ["Fixed Pydantic Config"]
        except Exception as e:
            return 0, [f"Error: {e}"]
    
    return 0, []


def main():
    """Fix warnings and errors in all Python files."""
    backend_dir = Path(__file__).parent.parent
    
    python_files = [
        f for f in backend_dir.rglob("*.py")
        if '__pycache__' not in str(f)
        and 'knowledge_base' not in str(f)
        and 'scripts' not in str(f)
    ]
    
    datetime_fixes = 0
    error_fixes = 0
    pydantic_fixes = 0
    
    print(f"Scanning {len(python_files)} files...")
    print()
    
    for file_path in sorted(python_files):
        rel_path = file_path.relative_to(backend_dir)
        
        # Fix datetime
        dt_count, dt_changes = fix_datetime_utcnow(file_path)
        if dt_count > 0:
            datetime_fixes += dt_count
            print(f"  {rel_path}: {dt_count} datetime fixes")
        
        # Fix silent errors
        err_count, err_changes = fix_silent_errors(file_path)
        if err_count > 0:
            error_fixes += err_count
            print(f"  {rel_path}: {err_count} error handling fixes")
        
        # Fix Pydantic
        pyd_count, pyd_changes = fix_pydantic_config(file_path)
        if pyd_count > 0:
            pydantic_fixes += pyd_count
            print(f"  {rel_path}: {pyd_count} Pydantic fixes")
    
    print()
    print(f"Fixed {datetime_fixes} datetime warnings")
    print(f"Fixed {error_fixes} silent error handlers")
    print(f"Fixed {pydantic_fixes} Pydantic configs")
    print("Run tests to verify!")


if __name__ == "__main__":
    main()
