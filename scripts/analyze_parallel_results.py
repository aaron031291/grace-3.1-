#!/usr/bin/env python3
"""Analyze parallel MBPP results."""

import json
from pathlib import Path
from collections import Counter

project_root = Path(__file__).parent.parent
results_file = project_root / "full_mbpp_results_parallel.json"

with open(results_file) as f:
    data = json.load(f)

results = data['results']['results']

print("="*80)
print("MBPP PARALLEL RESULTS ANALYSIS")
print("="*80)
print(f"\nTotal: {data['results']['total']}")
print(f"Passed: {data['results']['passed']}")
print(f"Failed: {data['results']['failed']}")
print(f"Pass Rate: {data['results']['pass_rate']:.2%}")
print()

# Generation methods
methods = Counter(r.get('generation_method', 'unknown') for r in results)
print("Generation Methods:")
for method, count in methods.most_common():
    print(f"  {method}: {count}")

# Passed by method
passed_by_method = Counter()
for r in results:
    if r.get('passed'):
        passed_by_method[r.get('generation_method', 'unknown')] += 1

print("\nPassed by Method:")
for method, count in passed_by_method.most_common():
    total = methods[method]
    rate = count / total if total > 0 else 0
    print(f"  {method}: {count}/{total} ({rate:.2%})")

# Common errors
errors = Counter()
for r in results:
    if not r.get('passed') and r.get('error'):
        error = r['error']
        if 'NameError' in error:
            errors['NameError'] += 1
        elif 'AssertionError' in error:
            errors['AssertionError'] += 1
        elif 'TypeError' in error:
            errors['TypeError'] += 1
        elif 'def to(' in r.get('code', ''):
            errors['Function name "to"'] += 1

print("\nCommon Error Types:")
for error, count in errors.most_common():
    print(f"  {error}: {count}")

# Function name issues
to_functions = sum(1 for r in results if 'def to(' in r.get('code', ''))
print(f"\nFunction name issues (def to): {to_functions}")

# Check for collaboration
collab_count = sum(1 for r in results if 'collaboration' in r.get('generation_method', '').lower())
print(f"Collaboration usage: {collab_count}")
