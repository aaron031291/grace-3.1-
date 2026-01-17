#!/usr/bin/env python3
"""Fix nested triple quotes in auto-learned templates."""
import re
from pathlib import Path

templates_file = Path("backend/benchmarking/mbpp_templates.py")

with open(templates_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix nested triple quotes: """def to(...): """docstring""" -> """def {function_name}(...): \"\"\"docstring\"\"\"
# Pattern: template_code="""def to(...):\n    """docstring"""
pattern = r'(template_code="""def )to\(([^:)]+):\s+\"\"\"([^"]+)\"\"\"'

def replace_func(match):
    prefix = match.group(1)
    params = match.group(2)
    docstring = match.group(3)
    return f'{prefix}{{function_name}}({params}):\n    \\"\\"\\"{docstring}\\"\\"\\"'

content = re.sub(pattern, replace_func, content)

with open(templates_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed nested triple quotes in templates")
