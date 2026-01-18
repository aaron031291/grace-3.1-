#!/usr/bin/env python3
"""
Clarity Framework Demo - Grace-Aligned Coding Agent

Demonstrates the template-first approach that competes with LLMs.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from cognitive.clarity_framework import ClarityFramework


def main():
    print("=" * 70)
    print("    CLARITY FRAMEWORK - Grace-Aligned Coding Agent Demo")
    print("    Template-First Approach to Compete with LLMs")
    print("=" * 70)
    print()
    
    # Initialize framework
    framework = ClarityFramework(enable_llm_fallback=False)
    
    print(f"[OK] Framework initialized with {len(framework.template_compiler.templates)} templates")
    print(f"[OK] Genesis tracking: {'enabled' if framework.genesis_tracker.genesis_service else 'disabled'}")
    print(f"[OK] Oracle: {'connected' if framework.oracle_liaison.oracle_hub else 'local'}")
    print()
    
    # Test cases
    test_cases = [
        {
            "name": "Factorial",
            "description": "Write a function that calculates the factorial of n",
            "test_cases": ["assert factorial(5) == 120", "assert factorial(0) == 1", "assert factorial(1) == 1"],
            "function_name": "factorial"
        },
        {
            "name": "Fibonacci",
            "description": "Write a function that returns the nth fibonacci number",
            "test_cases": ["assert fib(10) == 55", "assert fib(1) == 1", "assert fib(0) == 0"],
            "function_name": "fib"
        },
        {
            "name": "Prime Check",
            "description": "Write a function to check if a number is prime",
            "test_cases": ["assert is_prime(7) == True", "assert is_prime(4) == False", "assert is_prime(2) == True"],
            "function_name": "is_prime"
        },
        {
            "name": "GCD",
            "description": "Write a function to find the greatest common divisor of two numbers",
            "test_cases": ["assert gcd(12, 8) == 4", "assert gcd(17, 5) == 1"],
            "function_name": "gcd"
        },
        {
            "name": "LCM",
            "description": "Write a function to find the least common multiple of two numbers",
            "test_cases": ["assert lcm(4, 6) == 12"],
            "function_name": "lcm"
        },
        {
            "name": "Binary Search",
            "description": "Write a binary search function to find an element in a sorted list",
            "test_cases": ["assert binary_search([1,2,3,4,5], 3) == 2", "assert binary_search([1,2,3,4,5], 6) == -1"],
            "function_name": "binary_search"
        },
    ]
    
    print("-" * 70)
    print("Running Test Cases (Template-First, No LLM)")
    print("-" * 70)
    print()
    
    results = []
    for test in test_cases:
        result = framework.solve(
            description=test["description"],
            test_cases=test["test_cases"],
            function_name=test["function_name"]
        )
        results.append(result)
        
        status = "[PASS]" if result["success"] else "[FAIL]"
        llm_status = "(LLM)" if result.get("llm_used") else "(Template)"
        trust = result.get("trust_score", 0)
        template = result.get("template_used", "None")
        
        print(f"{status} {test['name']:20} {llm_status:12} Trust: {trust:.2f}  Template: {template}")
        
        if result["success"]:
            print(f"      Code: {result['code'][:60]}...")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    template_only = sum(1 for r in results if r["success"] and not r.get("llm_used"))
    
    print(f"Total tasks:          {total}")
    print(f"Passed:               {passed} ({passed/total*100:.0f}%)")
    print(f"Template-only solved: {template_only} ({template_only/total*100:.0f}%)")
    print(f"LLM fallback needed:  {total - template_only}")
    print()
    
    # KPI Dashboard
    dashboard = framework.get_kpi_dashboard()
    print("-" * 70)
    print("KPI Dashboard")
    print("-" * 70)
    print(f"LLM Independence Rate: {dashboard['competing_metrics']['llm_independence_rate']:.1f}%")
    print(f"Autonomous Rate:       {dashboard['competing_metrics']['autonomous_rate']:.1f}%")
    print(f"Avg Trust Score:       {dashboard['summary']['avg_trust_score']:.3f}")
    print(f"Templates Available:   {dashboard['template_coverage']['total_templates']}")
    print()
    
    # Grace Integration Status
    print("-" * 70)
    print("Grace Integration Status")
    print("-" * 70)
    grace = dashboard['grace_integration']
    print(f"Genesis Tracking: {'YES' if grace['genesis_tracking'] else 'NO'}")
    print(f"Oracle Connected: {'YES' if grace['oracle_connected'] else 'NO'}")
    print(f"Memory Mesh:      {'YES' if grace['memory_mesh_active'] else 'NO'}")
    print(f"Trust Scorer:     {'YES' if grace['trust_scorer'] else 'NO'}")
    print()
    
    # Memory Mesh Stats
    print("-" * 70)
    print("Memory Mesh Learning Stats")
    print("-" * 70)
    memory = dashboard.get('memory_mesh', {})
    print(f"Total Learnings:   {memory.get('total_learnings', 0)}")
    print(f"Success Rate:      {memory.get('success_rate', 0) * 100:.1f}%")
    print(f"Knowledge Gaps:    {memory.get('knowledge_gaps_found', 0)}")
    
    systems = memory.get('systems', {})
    print(f"File-Based Memory: {systems.get('file_based_entries', 0)} entries")
    print()
    
    # Show knowledge gaps if any
    gaps = dashboard.get('knowledge_gaps', [])
    if gaps:
        print("-" * 70)
        print("Knowledge Gaps (Templates needing improvement)")
        print("-" * 70)
        for gap in gaps[:3]:
            print(f"  - {gap.get('template_id', 'unknown')}: {gap.get('reason', '')}")
        print()
    
    print("=" * 70)
    print("Demo Complete - Clarity Framework is competing with LLMs!")
    print("=" * 70)


if __name__ == "__main__":
    main()
