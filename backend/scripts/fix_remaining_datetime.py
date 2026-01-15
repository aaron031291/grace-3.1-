#!/usr/bin/env python
"""
Fix remaining datetime.now(UTC) warnings.

Respects user preferences (skips genesis_key_service.py).
"""

import re
from pathlib import Path

SKIP_FILES = {
    'genesis/genesis_key_service.py',
    'genesis_key_service.py',
}

def fix_file(file_path: Path) -> int:
    """Fix datetime.now(UTC) in a file."""
    if any(skip in str(file_path) for skip in SKIP_FILES):
        return 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return 0
    
    if 'datetime.now(UTC)' not in content:
        return 0
    
    original = content
    
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
    
    # Fix calls
    count = content.count('datetime.now(UTC)')
    content = content.replace('datetime.now(UTC)', 'datetime.now(UTC)')
    
    # Fix defaults
    content = re.sub(r'default=datetime\.utcnow(?!\()', r'default=lambda: datetime.now(UTC)', content)
    content = re.sub(r'onupdate=datetime\.utcnow(?!\()', r'onupdate=lambda: datetime.now(UTC)', content)
    content = re.sub(r'default_factory=datetime\.utcnow(?!\()', r'default_factory=lambda: datetime.now(UTC)', content)
    
    if content != original:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return count
        except:
            return 0
    
    return 0

def main():
    backend = Path(__file__).parent.parent
    files = [f for f in backend.rglob("*.py")
             if '__pycache__' not in str(f) and 'knowledge_base' not in str(f)]
    
    total = 0
    for f in sorted(files):
        count = fix_file(f)
        if count > 0:
            print(f"  {f.relative_to(backend)}: {count}")
            total += count
    
    print(f"\nFixed {total} instances")

if __name__ == "__main__":
    main()
