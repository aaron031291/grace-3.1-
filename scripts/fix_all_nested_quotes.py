#!/usr/bin/env python3
"""Fix all nested triple quotes in auto-learned templates."""
import re
from pathlib import Path

templates_file = Path("backend/benchmarking/mbpp_templates.py")

with open(templates_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Check if this is a template_code line with nested quotes
    if 'template_code="""def {' in line and i + 1 < len(lines):
        # Look ahead for nested triple quotes
        if '"""' in lines[i+1] and not lines[i+1].strip().startswith('#'):
            # This line has nested quotes - fix it
            fixed_lines.append(line)
            i += 1
            # Fix the next few lines that contain nested quotes
            while i < len(lines) and ('"""' in lines[i] or '..."""' in lines[i]):
                # Replace """ with \"\"\"
                fixed_line = lines[i].replace('"""', '\\"\\"\\"')
                fixed_lines.append(fixed_line)
                i += 1
            continue
    
    fixed_lines.append(line)
    i += 1

with open(templates_file, 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("Fixed nested triple quotes")
