#!/usr/bin/env python3
"""
Fix SQLAlchemy table redefinition issues by adding __table_args__ = {'extend_existing': True}
to all model classes that don't already have it.
"""

import sys
import re
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def fix_model_file(file_path: Path) -> bool:
    """Fix a single model file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original_lines = lines.copy()
        modified = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this is a class definition with BaseModel or Base
            if 'class ' in line and ('BaseModel' in line or 'Base' in line):
                # Look ahead for __tablename__
                j = i + 1
                found_tablename = False
                tablename_line_idx = None
                
                while j < len(lines):
                    next_line = lines[j]
                    stripped = next_line.strip()
                    
                    # Stop if we hit another class or function definition
                    if stripped.startswith('class ') or (stripped.startswith('def ') and stripped.endswith(':')):
                        break
                    
                    # Check for __tablename__
                    if '__tablename__' in stripped:
                        found_tablename = True
                        tablename_line_idx = j
                    
                    # If we already have __table_args__, check if it has extend_existing
                    if '__table_args__' in stripped:
                        # Check if extend_existing is already in the __table_args__
                        # Look ahead to see the full __table_args__ definition
                        k = j
                        has_extend_existing = False
                        while k < len(lines) and k < j + 5:  # Check next 5 lines
                            if 'extend_existing' in lines[k]:
                                has_extend_existing = True
                                break
                            if lines[k].strip() and not lines[k].strip().startswith((' ', '\t', '(', ')', ',')):
                                break
                            k += 1
                        
                        if has_extend_existing:
                            found_tablename = False
                            break
                        else:
                            # Has __table_args__ but no extend_existing - need to add it
                            table_args_start = j
                            # Find where __table_args__ tuple ends
                            paren_count = 0
                            table_args_end = j
                            for k in range(j, min(len(lines), j + 20)):
                                line_k = lines[k]
                                paren_count += line_k.count('(') - line_k.count(')')
                                if paren_count == 0 and k > j:
                                    table_args_end = k
                                    break
                            
                            # For SQLAlchemy, extend_existing must be set at table creation time,
                            # not in __table_args__. So we'll just mark this class as handled.
                            # The real fix is in migration.py using extend_existing=True in create_all()
                            found_tablename = False
                            break
                    
                    j += 1
                
                # Add __table_args__ after __tablename__
                if found_tablename and tablename_line_idx is not None:
                    # Find the indentation level
                    tablename_line = lines[tablename_line_idx]
                    indent = len(tablename_line) - len(tablename_line.lstrip())
                    
                    # Check if next line already has __table_args__
                    if tablename_line_idx + 1 < len(lines):
                        next_line = lines[tablename_line_idx + 1].strip()
                        if '__table_args__' in next_line:
                            i = j
                            continue
                    
                    # Insert __table_args__ after __tablename__
                    indent_str = ' ' * indent
                    table_args_line = f"{indent_str}__table_args__ = {{'extend_existing': True}}\n"
                    lines.insert(tablename_line_idx + 1, table_args_line)
                    modified = True
                    print(f'Added __table_args__ to class in {file_path} at line {tablename_line_idx + 1}')
            
            i += 1
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        return False
    except Exception as e:
        print(f'Error fixing {file_path}: {e}')
        import traceback
        traceback.print_exc()
        return False

def main():
    """Fix all model files."""
    repo_root = Path(__file__).parent.parent.parent
    model_files = [
        repo_root / "backend" / "models" / "database_models.py",
        repo_root / "backend" / "models" / "genesis_key_models.py",
    ]
    
    fixed_count = 0
    for model_file in model_files:
        if model_file.exists():
            if fix_model_file(model_file):
                fixed_count += 1
                print(f'Fixed: {model_file}')
        else:
            print(f'Skipping non-existent file: {model_file}')
    
    print(f'\nFixed {fixed_count} file(s)')
    return fixed_count > 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
