#!/usr/bin/env python3
"""Analyze MBPP failures to understand why pass rate dropped."""

import json
from pathlib import Path
from collections import Counter

def analyze_failures():
    """Analyze failure patterns."""
    project_root = Path(__file__).parent.parent
    results_file = project_root / "benchmark_results.json"
    
    if not results_file.exists():
        print("No results file found.")
        return
    
    with open(results_file) as f:
        data = json.load(f)
    
    results = data.get("mbpp", {}).get("results", [])
    
    if not results:
        print("No results found.")
        return
    
    # Separate by generation method
    template_results = [r for r in results if r.get("generation_method") == "template"]
    llm_results = [r for r in results if r.get("generation_method") == "llm"]
    
    # Calculate pass rates
    template_passed = sum(1 for r in template_results if r.get("passed"))
    template_total = len(template_results)
    template_rate = (template_passed / template_total * 100) if template_total > 0 else 0
    
    llm_passed = sum(1 for r in llm_results if r.get("passed"))
    llm_total = len(llm_results)
    llm_rate = (llm_passed / llm_total * 100) if llm_total > 0 else 0
    
    print("="*80)
    print("FAILURE ANALYSIS")
    print("="*80)
    print(f"Total problems: {len(results)}")
    print(f"Template generated: {template_total} ({template_rate:.1f}% pass rate)")
    print(f"LLM generated: {llm_total} ({llm_rate:.1f}% pass rate)")
    print()
    
    # Analyze failures
    failures = [r for r in results if not r.get("passed")]
    print(f"Total failures: {len(failures)}")
    print()
    
    # Error types
    error_types = Counter()
    for f in failures:
        error = f.get("error", "")
        if "NameError" in error:
            error_types["NameError (function name mismatch)"] += 1
        elif "TypeError" in error:
            error_types["TypeError (wrong parameters/types)"] += 1
        elif "AssertionError" in error:
            error_types["AssertionError (wrong output)"] += 1
        elif "SyntaxError" in error:
            error_types["SyntaxError"] += 1
        elif "AttributeError" in error:
            error_types["AttributeError"] += 1
        else:
            error_types["Other"] += 1
    
    print("Error types:")
    for err_type, count in error_types.most_common():
        print(f"  {err_type}: {count}")
    print()
    
    # Check first 10 vs rest
    first_10 = results[:10]
    rest = results[10:]
    
    first_10_passed = sum(1 for r in first_10 if r.get("passed"))
    rest_passed = sum(1 for r in rest if r.get("passed"))
    
    print("Comparison:")
    print(f"  First 10 problems: {first_10_passed}/10 passed ({first_10_passed/10*100:.1f}%)")
    if rest:
        print(f"  Problems 11-{len(results)}: {rest_passed}/{len(rest)} passed ({rest_passed/len(rest)*100:.1f}%)")
    print()
    
    # Show sample failures
    print("Sample failures (first 5):")
    for i, failure in enumerate(failures[:5], 1):
        print(f"\n{i}. {failure.get('task_id', 'unknown')}")
        print(f"   Problem: {failure.get('problem_text', '')[:100]}...")
        error = failure.get('error', '')
        if error:
            error_line = error.split('\n')[0] if '\n' in error else error[:100]
            print(f"   Error: {error_line}")
        print(f"   Code: {failure.get('code', '')[:80]}...")

if __name__ == "__main__":
    analyze_failures()
