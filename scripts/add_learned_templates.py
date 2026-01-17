#!/usr/bin/env python3
"""
Automatically add learned templates to mbpp_templates.py

Reads learned_templates.json and adds high-confidence templates to the template library.
"""

import json
import sys
from pathlib import Path
import re

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def add_templates_to_library(min_confidence=0.4):
    """Add learned templates to mbpp_templates.py."""
    learned_file = project_root / "learned_templates.json"
    templates_file = project_root / "backend" / "benchmarking" / "mbpp_templates.py"
    
    if not learned_file.exists():
        print(f"ERROR: {learned_file} not found. Run learn_templates_from_failures.py first.")
        return False
    
    # Read learned templates
    with open(learned_file) as f:
        data = json.load(f)
    
    templates = data.get("templates", [])
    high_confidence = [t for t in templates if t.get("confidence", 0) >= min_confidence]
    
    if not high_confidence:
        print(f"No templates with confidence >= {min_confidence:.0%}")
        return False
    
    print(f"Found {len(high_confidence)} templates with confidence >= {min_confidence:.0%}")
    
    # Read current templates file
    with open(templates_file, 'r') as f:
        content = f.read()
    
    # Find where to insert (before the closing bracket of TEMPLATES list)
    # Look for the last template before the closing bracket
    last_template_match = re.search(r'(    MBPPTemplate\([^)]+\)\s*,\s*)\n\]', content, re.DOTALL)
    
    if not last_template_match:
        # Try alternative pattern
        last_template_match = re.search(r'(    \),\s*)\n\]', content)
        if not last_template_match:
            print("ERROR: Could not find insertion point in templates file")
            return False
    
    insertion_point = last_template_match.start(1)
    
    # Generate template code blocks
    new_templates_code = "\n"
    added_count = 0
    
    for template in high_confidence:
        name = template["name"]
        keywords = template["pattern_keywords"]
        regex = template.get("pattern_regex", "")
        code = template["template_code"]
        description = template.get("description", "Auto-learned template")
        examples = template.get("examples", [])
        
        # Format keywords list
        keywords_str = "[" + ", ".join(f'"{kw}"' for kw in keywords[:10]) + "]"
        
        # Format regex
        regex_str = f'r"{regex}"' if regex else "None"
        
        # Format template code - handle nested triple quotes properly
        # Replace inner triple quotes with escaped version
        if '"""' in code:
            # Split by triple quotes and escape inner ones
            parts = code.split('"""')
            code_escaped = '\\"\\"\\"'.join(parts)
        else:
            code_escaped = code
        
        # Format examples
        examples_str = "[" + ", ".join(f'"{ex}"' for ex in examples[:3]) + "]" if examples else "[]"
        
        # Create template block with proper escaping
        template_block = f"""    MBPPTemplate(
        name="{name}",
        pattern_keywords={keywords_str},
        pattern_regex={regex_str},
        template_code=\"\"\"{code_escaped}\"\"\",
        description="{description}",
        examples={examples_str}
    ),
"""
        new_templates_code += template_block
        added_count += 1
    
    # Insert new templates
    new_content = content[:insertion_point] + new_templates_code + content[insertion_point:]
    
    # Write back
    with open(templates_file, 'w') as f:
        f.write(new_content)
    
    print(f"\nSuccessfully added {added_count} templates to {templates_file}")
    print("\nAdded templates:")
    for template in high_confidence:
        print(f"  - {template['name']} (confidence: {template['confidence']:.1%})")
    
    return True

if __name__ == "__main__":
    min_confidence = float(sys.argv[1]) if len(sys.argv) > 1 else 0.4
    success = add_templates_to_library(min_confidence)
    sys.exit(0 if success else 1)
