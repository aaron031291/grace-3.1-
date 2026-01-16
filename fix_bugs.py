#!/usr/bin/env python3
"""
Fix identified bugs from bug hunt
"""
import json
from pathlib import Path

# Load bug report
with open('bug_hunt_report.json', 'r') as f:
    report = json.load(f)

print("=" * 60)
print("CRITICAL BUGS TO FIX")
print("=" * 60)

bugs = [b for b in report['bugs'] if b['severity'] == 'ERROR']
print(f"\nFound {len(bugs)} critical bugs:\n")

for i, bug in enumerate(bugs, 1):
    print(f"{i}. {bug['category']}: {bug['file']}:{bug['line']}")
    print(f"   {bug['message']}\n")

# Group by category
by_category = {}
for bug in bugs:
    cat = bug['category']
    if cat not in by_category:
        by_category[cat] = []
    by_category[cat].append(bug)

print("\n" + "=" * 60)
print("BUGS BY CATEGORY")
print("=" * 60)

for category, bug_list in by_category.items():
    print(f"\n{category}: {len(bug_list)} bugs")
    for bug in bug_list:
        print(f"  - {bug['file']}:{bug['line']} - {bug['message'][:80]}")
