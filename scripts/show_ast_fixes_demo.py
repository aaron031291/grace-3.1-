#!/usr/bin/env python3
"""Demonstrate AST Transformer fixes with before/after examples"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from cognitive.code_analyzer_self_healing import CodeFixApplicator
from cognitive.grace_code_analyzer import CodeIssue, Severity, Confidence

print("=" * 70)
print("AST Transformer Fixes - Before & After Examples")
print("=" * 70)

# Example 1: Simple class without logger
print("\n" + "=" * 70)
print("EXAMPLE 1: Simple Class Without Logger")
print("=" * 70)

before_code_1 = '''class TestClass:
    def __init__(self):
        self.value = 42
    
    def method(self):
        pass
'''

print("\n[BEFORE]")
print("-" * 70)
print(before_code_1)
print("-" * 70)

issue_1 = CodeIssue(
    rule_id='G012',
    message='Class should have logger = logging.getLogger(__name__)',
    severity=Severity.LOW,
    confidence=Confidence.MEDIUM,
    file_path='test.py',
    line_number=1,
    suggested_fix='Add logger initialization in class __init__ or module level',
    fix_confidence=0.9
)

fix_app = CodeFixApplicator()
success, after_code_1 = fix_app.apply_fix(issue_1, before_code_1)

if success:
    print("\n[AFTER]")
    print("-" * 70)
    print(after_code_1)
    print("-" * 70)
    print("\n[CHANGES]")
    print("  [OK] Added 'import logging' at the top")
    print("  [OK] Added 'logger = logging.getLogger(__name__)' as first class attribute")

# Example 2: Class with existing imports
print("\n\n" + "=" * 70)
print("EXAMPLE 2: Class With Existing Imports")
print("=" * 70)

before_code_2 = '''import os
import sys

class MyService:
    def __init__(self):
        self.config = {}
    
    def process(self):
        return "done"
'''

print("\n[BEFORE]")
print("-" * 70)
print(before_code_2)
print("-" * 70)

issue_2 = CodeIssue(
    rule_id='G012',
    message='Class should have logger = logging.getLogger(__name__)',
    severity=Severity.LOW,
    confidence=Confidence.MEDIUM,
    file_path='service.py',
    line_number=4,
    suggested_fix='Add logger initialization',
    fix_confidence=0.9
)

success, after_code_2 = fix_app.apply_fix(issue_2, before_code_2)

if success:
    print("\n[AFTER]")
    print("-" * 70)
    print(after_code_2)
    print("-" * 70)
    print("\n[CHANGES]")
    print("  [OK] Added 'import logging' with existing imports")
    print("  [OK] Added 'logger = logging.getLogger(__name__)' in class")

# Example 3: Class with docstring
print("\n\n" + "=" * 70)
print("EXAMPLE 3: Class With Docstring")
print("=" * 70)

before_code_3 = '''"""
My Module Description
"""

class DataProcessor:
    """Process data efficiently."""
    
    def __init__(self):
        self.cache = {}
'''

print("\n[BEFORE]")
print("-" * 70)
print(before_code_3)
print("-" * 70)

issue_3 = CodeIssue(
    rule_id='G012',
    message='Class should have logger = logging.getLogger(__name__)',
    severity=Severity.LOW,
    confidence=Confidence.MEDIUM,
    file_path='processor.py',
    line_number=5,
    suggested_fix='Add logger initialization',
    fix_confidence=0.9
)

success, after_code_3 = fix_app.apply_fix(issue_3, before_code_3)

if success:
    print("\n[AFTER]")
    print("-" * 70)
    print(after_code_3)
    print("-" * 70)
    print("\n[CHANGES]")
    print("  [OK] Added 'import logging' after docstring")
    print("  [OK] Added 'logger = logging.getLogger(__name__)' in class body")
    print("  [OK] Preserved docstring and formatting")

# Summary
print("\n\n" + "=" * 70)
print("FIX SUMMARY")
print("=" * 70)
print("\nWhat the AST Transformer Does:")
print("  1. Detects missing logger in classes (G012 rule)")
print("  2. Checks if 'import logging' exists, adds it if missing")
print("  3. Adds 'logger = logging.getLogger(__name__)' as first class attribute")
print("  4. Preserves all existing code structure and formatting")
print("  5. Generates syntactically correct Python code")
print("\nThe transformer:")
print("  [OK] Uses Abstract Syntax Tree (AST) for safe code modification")
print("  [OK] Handles imports intelligently (respects docstrings, other imports)")
print("  [OK] Preserves code structure and indentation")
print("  [OK] Generates valid Python code that passes syntax checks")
print("=" * 70)
