#!/usr/bin/env python3
"""Analyze full MBPP failures to identify patterns for new templates."""

import json
from pathlib import Path
from collections import Counter
import re

def analyze_failures():
    """Analyze failure patterns."""
    project_root = Path(__file__).parent.parent
    results_file = project_root / "full_mbpp_results.json"
    
    if not results_file.exists():
        print("No full results file found.")
        return
    
    with open(results_file) as f:
        data = json.load(f)
    
    results = data.get("results", {}).get("results", [])
    
    if not results:
        print("No results found.")
        return
    
    failures = [r for r in results if not r.get("passed")]
    passed = [r for r in results if r.get("passed")]
    
    print("="*80)
    print("FULL MBPP FAILURE ANALYSIS")
    print("="*80)
    print(f"Total: {len(results)}")
    print(f"Passed: {len(passed)} ({len(passed)/len(results)*100:.1f}%)")
    print(f"Failed: {len(failures)} ({len(failures)/len(results)*100:.1f}%)")
    print()
    
    # Extract keywords from problem texts
    keywords = Counter()
    for f in failures[:100]:  # Analyze first 100 failures
        text = f.get("problem_text", "").lower()
        # Extract common patterns
        if "find" in text:
            keywords["find"] += 1
        if "count" in text:
            keywords["count"] += 1
        if "check" in text:
            keywords["check"] += 1
        if "remove" in text:
            keywords["remove"] += 1
        if "sort" in text:
            keywords["sort"] += 1
        if "convert" in text:
            keywords["convert"] += 1
        if "calculate" in text:
            keywords["calculate"] += 1
        if "list" in text or "array" in text:
            keywords["list/array"] += 1
        if "string" in text:
            keywords["string"] += 1
        if "number" in text or "integer" in text:
            keywords["number"] += 1
    
    print("Common keywords in failures:")
    for keyword, count in keywords.most_common(10):
        print(f"  {keyword}: {count}")
    print()
    
    # Show sample failures
    print("Sample failures (first 10):")
    for i, failure in enumerate(failures[:10], 1):
        print(f"\n{i}. Problem: {failure.get('problem_text', '')[:100]}...")
        error = failure.get('error', '')
        if error:
            error_line = error.split('\n')[0] if '\n' in error else error[:100]
            print(f"   Error: {error_line}")

if __name__ == "__main__":
    analyze_failures()
