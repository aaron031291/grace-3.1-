#!/usr/bin/env python3
"""Test AST Transformer for G012 fixes"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from cognitive.code_analyzer_self_healing import CodeFixApplicator, ASTCodeTransformer
from cognitive.grace_code_analyzer import GraceCodeAnalyzer

# Test on a simple file
test_code = '''
class TestClass:
    def __init__(self):
        self.value = 42
    
    def method(self):
        pass
'''

print("Testing AST Transformer for G012...")
print("=" * 70)

# Create a mock issue for G012
from cognitive.grace_code_analyzer import CodeIssue, Severity, Confidence

issue = CodeIssue(
    rule_id='G012',
    message='Class should have logger = logging.getLogger(__name__)',
    severity=Severity.LOW,
    confidence=Confidence.MEDIUM,
    file_path='test.py',
    line_number=2,
    suggested_fix='Add logger initialization in class __init__ or module level',
    fix_confidence=0.9  # Set high confidence for testing
)

print(f"\nIssue: {issue.rule_id}")
print(f"Has suggested_fix: {issue.suggested_fix is not None}")
print(f"Fix confidence: {issue.fix_confidence}")

# Test fix applicator
fix_app = CodeFixApplicator()
print(f"\nCan auto-fix: {fix_app.can_auto_fix(issue)}")

# Apply fix
success, fixed_code = fix_app.apply_fix(issue, test_code)

print(f"\nFix applied: {success}")
if success:
    print("\nFixed code:")
    print("-" * 70)
    print(fixed_code)
    print("-" * 70)
    
    # Verify syntax
    import ast
    try:
        ast.parse(fixed_code)
        print("\n[OK] Fixed code has valid syntax")
    except SyntaxError as e:
        print(f"\n[ERROR] Syntax error: {e}")
    
    # Verify logging import exists
    if 'import logging' in fixed_code:
        print("[OK] logging import added")
    else:
        print("[WARNING] logging import not found - code will fail at runtime")
        print("Note: The AST transformer should add 'import logging' if missing")
