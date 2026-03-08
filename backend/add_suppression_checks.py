"""
Quick script to add suppression checks to Genesis error logging.
Run this to update all Genesis files to respect SUPPRESS_GENESIS_ERRORS flag.
"""
import re
import os
from pathlib import Path

# Files to update
genesis_files = [
    "genesis/kb_integration.py",
    "genesis/file_watcher.py",
    "genesis/symbiotic_version_control.py",
    "genesis/autonomous_triggers.py",
]

backend_dir = Path(__file__).parent

# Add settings import if not present
settings_import = """
try:
    from settings import settings
except ImportError:
    settings = None
"""

# Pattern to find logger.error calls
error_pattern = r'(\s+)(logger\.error\(f?".*?"\))'

# Replacement with suppression check
def add_suppression_check(match):
    indent = match.group(1)
    error_call = match.group(2)
    return f'{indent}if not (settings and settings.SUPPRESS_GENESIS_ERRORS):\n{indent}    {error_call}'

for file_path in genesis_files:
    full_path = backend_dir / file_path
    if not full_path.exists():
        print(f"Skipping {file_path} - not found")
        continue
    
    print(f"Processing {file_path}...")
    
    with open(full_path, 'r') as f:
        content = f.read()
    
    # Add settings import if not present
    if 'from settings import settings' not in content:
        # Find where to insert (after other imports)
        import_section_end = content.find('\nlogger = ')
        if import_section_end > 0:
            content = content[:import_section_end] + '\n' + settings_import + content[import_section_end:]
    
    # Add suppression checks to logger.error calls
    # Only if not already wrapped
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a logger.error line
        if 'logger.error(' in line and 'if not (settings and settings.SUPPRESS_GENESIS_ERRORS)' not in lines[i-1] if i > 0 else True:
            # Get indentation
            indent = len(line) - len(line.lstrip())
            indent_str = ' ' * indent
            
            # Add suppression check
            new_lines.append(f'{indent_str}if not (settings and settings.SUPPRESS_GENESIS_ERRORS):')
            new_lines.append(' ' * 4 + line)
        else:
            new_lines.append(line)
        
        i += 1
    
    content = '\n'.join(new_lines)
    
    # Write back
    with open(full_path, 'w') as f:
        f.write(content)
    
    print(f"✓ Updated {file_path}")

print("\n✓ All files updated!")
print("Restart the server to apply changes.")
