#!/usr/bin/env python3
"""Check GitHub failures training progress."""

import json
import sys
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Check training results
results_file = Path("github_training_results.json")
failures_file = Path("github_failures_10000.json")

print("="*80)
print("GITHUB FAILURES TRAINING STATUS")
print("="*80)

# Check failures collection
if failures_file.exists():
    with open(failures_file, 'r', encoding='utf-8') as f:
        failures_data = json.load(f)
    examples_count = len(failures_data.get('examples', []))
    metadata = failures_data.get('metadata', {})
    print(f"\n✓ Failures Collection:")
    print(f"  Total examples: {examples_count}")
    print(f"  Collection date: {metadata.get('collection_date', 'N/A')}")
    stats = metadata.get('stats', {})
    print(f"  API calls: {stats.get('api_calls', 0)}")
    print(f"  Rate limit hits: {stats.get('rate_limit_hits', 0)}")
else:
    print("\n✗ Failures collection file not found")

# Check training results
if results_file.exists():
    with open(results_file, 'r', encoding='utf-8') as f:
        results_data = json.load(f)
    meta = results_data.get('metadata', {})
    print(f"\n✓ Training Results:")
    print(f"  Total examples: {meta.get('total_examples', 0)}")
    print(f"  Attempted: {meta.get('attempted', 0)}")
    print(f"  Fixed: {meta.get('fixed', 0)}")
    print(f"  Failed: {meta.get('failed', 0)}")
    print(f"  Errors: {meta.get('errors', 0)}")
    print(f"  Skipped: {meta.get('skipped', 0)}")
    print(f"  Success Rate: {meta.get('success_rate', 0):.1f}%")
    print(f"  Started: {meta.get('started_at', 'N/A')}")
    print(f"  Last update: {meta.get('last_update', 'N/A')}")
    
    attempts = results_data.get('fix_attempts', [])
    if attempts:
        print(f"\n  Recent attempts: {len(attempts)}")
        fixed_count = sum(1 for a in attempts if a.get('status') == 'fixed')
        print(f"  Fixed: {fixed_count}/{len(attempts)}")
else:
    print("\n✗ Training results not yet available")
    print("  Training may still be running...")

print("\n" + "="*80)
