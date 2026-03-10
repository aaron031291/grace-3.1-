import os
import re

def replace_in_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if 'datetime.now(timezone.utc)' in content or 'utcnow()' in content:
            new_content = content.replace('datetime.datetime.now(datetime.timezone.utc)', 'datetime.datetime.now(datetime.timezone.utc)')
            new_content = new_content.replace('datetime.now(timezone.utc)', 'datetime.now(timezone.utc)')
            
            # Need to ensure 'timezone' is imported if we use 'datetime.now(timezone.utc)'
            if 'datetime.now(timezone.utc)' in new_content and 'from datetime import timezone' not in new_content and 'import timezone' not in new_content:
                # find a place to put it
                if 'from datetime import datetime' in new_content:
                    new_content = new_content.replace('from datetime import datetime', 'from datetime import datetime, timezone', 1)
                else:
                    lines = new_content.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith('import ') or line.startswith('from '):
                            lines.insert(i, 'from datetime import timezone')
                            break
                    new_content = '\n'.join(lines)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {filepath}")
    except Exception as e:
        print(f"Error reading {filepath}: {e}")

for root, dirs, files in os.walk(r'd:\grace-3.1-\backend'):
    if '__pycache__' in dirs:
        dirs.remove('__pycache__')
    for file in files:
        if file.endswith('.py'):
            replace_in_file(os.path.join(root, file))
