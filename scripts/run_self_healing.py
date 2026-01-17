#!/usr/bin/env python3
"""Run the self-healing system"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from cognitive.code_analyzer_self_healing import CodeAnalyzerSelfHealing

print("=" * 70)
print("GRACE SELF-HEALING SYSTEM")
print("=" * 70)
print()

print("[*] Initializing self-healing system...")
healing = CodeAnalyzerSelfHealing(enable_auto_fix=True)

print("[*] Starting analysis and healing...")
print()

# Run in auto-fix mode
result = healing.analyze_and_heal('backend', auto_fix=True, pre_flight=False)

print()
print("=" * 70)
print("HEALING RESULTS")
print("=" * 70)
print()
print(f"Issues Found: {result['issues_found']}")
print(f"  - By Severity: {result['issues_by_severity']}")
print(f"Fixable Issues: {result['fixable_issues']}")
print(f"Fixes Applied: {result['fixes_applied']}")
print(f"Health Status: {result['health_status']}")
print(f"Mode: {result['mode']}")
print(f"Timesense Enabled: {result['timesense_enabled']}")

if result['time_statistics']:
    stats = result['time_statistics']
    print()
    print("Time Statistics:")
    print(f"  - Total predictions: {stats.get('total_predictions', 0)}")
    print(f"  - Average error: {stats.get('avg_error_percent', 0):.1f}%")
    print(f"  - Prediction accuracy: {stats.get('accuracy_level', 'N/A')}")

if result['fixes_applied'] > 0:
    print()
    print("Fixes Applied:")
    for fix in healing.fixes_applied[:10]:  # Show first 10
        print(f"  - {fix['file']}:{fix['line']} [{fix['rule_id']}] {fix['message'][:50]}")

print()
print("=" * 70)
print("[OK] Self-healing system completed!")
print("=" * 70)
