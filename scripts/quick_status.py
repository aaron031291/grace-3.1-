#!/usr/bin/env python3
"""Quick status check - simpler version."""
import json
from pathlib import Path
import sys

results_file = Path("full_mbpp_results.json")
if results_file.exists():
    try:
        with open(results_file) as f:
            data = json.load(f)
        results = data.get("results", {})
        
        total = results.get("total", 0)
        passed = results.get("passed", 0)
        failed = results.get("failed", 0)
        pass_rate = results.get("pass_rate", 0.0)
        template_matches = results.get("template_matches", 0)
        llm_generated = results.get("llm_generated", 0)
        
        print("="*70)
        print("MBPP EVALUATION STATUS")
        print("="*70)
        print(f"Total: {total}/500")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Pass rate: {pass_rate:.2%}")
        print(f"Template matches: {template_matches}")
        print(f"LLM generated: {llm_generated}")
        print("="*70)
        
        if total == 500:
            print("\n[COMPLETE] Evaluation finished!")
        elif total > 0:
            progress = (total / 500) * 100
            print(f"\n[IN PROGRESS] {progress:.1f}% complete ({total}/500)")
        else:
            print("\n[WAITING] Evaluation starting...")
            
    except Exception as e:
        print(f"Error reading results: {e}")
        sys.exit(1)
else:
    print("Results file not found. Evaluation may be starting...")
    sys.exit(0)
