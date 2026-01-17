#!/usr/bin/env python3
"""
Analyze Template Failures

Analyzes why templates are matching but failing tests.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def analyze_template_failures():
    """Analyze why templates are failing."""
    results_file = project_root / "full_mbpp_results.json"
    
    if not results_file.exists():
        print(f"ERROR: {results_file} not found")
        return
    
    with open(results_file) as f:
        data = json.load(f)
    
    results = data.get("results", {}).get("results", [])
    
    # Categorize results
    template_matches = []
    template_passed = []
    template_failed = []
    llm_generated = []
    
    for result in results:
        method = result.get("generation_method", "unknown")
        passed = result.get("passed", False)
        
        if method == "template" or method == "template_fallback":
            template_matches.append(result)
            if passed:
                template_passed.append(result)
            else:
                template_failed.append(result)
        elif method == "llm":
            llm_generated.append(result)
    
    print("="*80)
    print("TEMPLATE FAILURE ANALYSIS")
    print("="*80)
    print(f"\nTotal template matches: {len(template_matches)}")
    print(f"Template passed: {len(template_passed)} ({len(template_passed)/len(template_matches)*100:.1f}%)")
    print(f"Template failed: {len(template_failed)} ({len(template_failed)/len(template_matches)*100:.1f}%)")
    print(f"\nLLM generated: {len(llm_generated)}")
    
    # Analyze failure reasons
    print("\n" + "="*80)
    print("FAILURE REASONS")
    print("="*80)
    
    error_types = Counter()
    error_patterns = defaultdict(int)
    
    for failure in template_failed[:50]:  # Analyze first 50 failures
        error = failure.get("error", "")
        code = failure.get("code", "")
        problem_text = failure.get("problem_text", "")
        
        # Categorize error
        if "AssertionError" in error or "assert" in error.lower():
            error_types["AssertionError"] += 1
        elif "NameError" in error:
            error_types["NameError"] += 1
        elif "TypeError" in error:
            error_types["TypeError"] += 1
        elif "SyntaxError" in error:
            error_types["SyntaxError"] += 1
        elif "IndentationError" in error:
            error_types["IndentationError"] += 1
        elif "AttributeError" in error:
            error_types["AttributeError"] += 1
        else:
            error_types["Other"] += 1
        
        # Extract patterns
        if "function" in error.lower() and "not defined" in error.lower():
            error_patterns["Function not defined"] += 1
        if "parameter" in error.lower() or "argument" in error.lower():
            error_patterns["Parameter mismatch"] += 1
        if "return" in error.lower() and "none" in error.lower():
            error_patterns["Return value issue"] += 1
    
    print("\nError Types:")
    for error_type, count in error_types.most_common():
        print(f"  {error_type}: {count}")
    
    print("\nError Patterns:")
    for pattern, count in sorted(error_patterns.items(), key=lambda x: -x[1]):
        print(f"  {pattern}: {count}")
    
    # Sample failures
    print("\n" + "="*80)
    print("SAMPLE FAILURES (First 5)")
    print("="*80)
    
    for i, failure in enumerate(template_failed[:5], 1):
        print(f"\n{i}. Problem: {failure.get('problem_text', '')[:100]}...")
        print(f"   Error: {failure.get('error', '')[:200]}...")
        print(f"   Code preview: {failure.get('code', '')[:150]}...")
    
    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    total_failures = len(template_failed)
    assertion_errors = error_types.get("AssertionError", 0)
    name_errors = error_types.get("NameError", 0)
    type_errors = error_types.get("TypeError", 0)
    
    print(f"\n1. Template Code Quality:")
    print(f"   - {assertion_errors}/{total_failures} failures are AssertionErrors (wrong logic)")
    print(f"   - Need better template implementations")
    
    print(f"\n2. Function Name Matching:")
    print(f"   - {name_errors}/{total_failures} failures are NameErrors (function name mismatch)")
    print(f"   - Need better function name extraction from test cases")
    
    print(f"\n3. Parameter Handling:")
    print(f"   - {type_errors}/{total_failures} failures are TypeErrors (parameter issues)")
    print(f"   - Need better parameter inference from test cases")
    
    print(f"\n4. Template Expansion:")
    print(f"   - Current templates may be too generic")
    print(f"   - Need more specific templates for common patterns")
    print(f"   - Use reversed KNN to learn from failures")
    
    return {
        "template_matches": len(template_matches),
        "template_passed": len(template_passed),
        "template_failed": len(template_failed),
        "error_types": dict(error_types),
        "error_patterns": dict(error_patterns)
    }

if __name__ == "__main__":
    analyze_template_failures()
