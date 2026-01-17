#!/usr/bin/env python3
"""Test can_auto_fix logic"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from cognitive.code_analyzer_self_healing import CodeFixApplicator
from cognitive.grace_code_analyzer import CodeIssue, Severity, Confidence

fix_app = CodeFixApplicator()

# Test IMPORT_ERROR issue
issue = CodeIssue(
    rule_id='IMPORT_ERROR',
    message='Import error',
    severity=Severity.HIGH,
    confidence=Confidence.MEDIUM,
    file_path='test.py',
    line_number=1,
    suggested_fix='fix import',
    fix_confidence=0.8
)

print(f"Rule ID: {issue.rule_id}")
print(f"In diagnostic rules: {issue.rule_id in ['SYNTAX_ERROR', 'IMPORT_ERROR', 'MISSING_FILE']}")
print(f"Has suggested_fix: {issue.suggested_fix is not None}")
print(f"suggested_fix value: {issue.suggested_fix}")
print(f"Can auto-fix: {fix_app.can_auto_fix(issue)}")
