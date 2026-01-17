#!/usr/bin/env python3
"""Test G012 detection and fix application"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from cognitive.grace_code_analyzer import GraceCodeAnalyzer
from cognitive.code_analyzer_self_healing import CodeFixApplicator

# Test file content - class without logger
test_file_content = '''class TestClass:
    def __init__(self):
        self.value = 42
    
    def method(self):
        pass
'''

print("Testing G012 detection and fix...")
print("=" * 70)

# Write test file
test_file = Path(__file__).parent.parent / "backend" / "test_g012_class.py"
test_file.write_text(test_file_content, encoding='utf-8')
print(f"[*] Created test file: {test_file}")

try:
    # Analyze the test file
    analyzer = GraceCodeAnalyzer()
    results = analyzer.analyze_file(str(test_file))
    
    print(f"\n[*] Found {len(results)} issues")
    g012_issues = [i for i in results if i.rule_id == 'G012']
    
    if g012_issues:
        print(f"[OK] G012 detected: {len(g012_issues)} issue(s)")
        for issue in g012_issues:
            print(f"  - Line {issue.line_number}: {issue.message}")
        
        # Apply fix
        print(f"\n[*] Applying AST transformer fix...")
        fix_app = CodeFixApplicator()
        success, fixed_code = fix_app.apply_fix(g012_issues[0], test_file_content)
        
        if success:
            print("[OK] Fix applied successfully!")
            print("\nFixed code:")
            print("-" * 70)
            print(fixed_code)
            print("-" * 70)
            
            # Verify import is present
            if 'import logging' in fixed_code:
                print("[OK] logging import added")
            else:
                print("[WARNING] logging import missing")
        else:
            print("[ERROR] Fix failed")
    else:
        print("[!] G012 not detected - rule may need adjustment")
        print("\nAll issues found:")
        for issue in results:
            print(f"  - {issue.rule_id}: {issue.message} (line {issue.line_number})")
finally:
    # Clean up
    if test_file.exists():
        test_file.unlink()
        print(f"\n[*] Cleaned up test file")
