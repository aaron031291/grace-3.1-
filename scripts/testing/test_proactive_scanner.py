#!/usr/bin/env python3
"""Test the proactive code scanner"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from diagnostic_machine.proactive_code_scanner import get_proactive_scanner

scanner = get_proactive_scanner()
issues = scanner.scan_all()

print(f"\nProactive Scanner Results:")
print(f"  Total Issues Found: {len(issues)}")
print(f"  Critical: {len([i for i in issues if i.severity == 'critical'])}")
print(f"  High: {len([i for i in issues if i.severity == 'high'])}")
print(f"  Medium: {len([i for i in issues if i.severity == 'medium'])}")
print(f"  Low: {len([i for i in issues if i.severity == 'low'])}")

print(f"\nTop 10 Issues:")
for i, issue in enumerate(issues[:10], 1):
    print(f"  {i}. [{issue.severity.upper()}] {issue.issue_type}")
    print(f"     {issue.file_path}:{issue.line_number}")
    print(f"     {issue.message[:80]}")
