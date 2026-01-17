#!/usr/bin/env python3
"""
Check MBPP Evaluation Progress

Monitors progress of full MBPP evaluation by checking the results file.
"""

import json
from pathlib import Path
from datetime import datetime

def check_progress():
    """Check evaluation progress."""
    project_root = Path(__file__).parent.parent
    
    # Check for full results
    full_results_file = project_root / "full_mbpp_results.json"
    benchmark_results_file = project_root / "benchmark_results.json"
    
    if full_results_file.exists():
        print("="*80)
        print("FULL MBPP EVALUATION - COMPLETE")
        print("="*80)
        with open(full_results_file) as f:
            data = json.load(f)
        
        results = data.get("results", {})
        config = data.get("configuration", {})
        
        print(f"Timestamp: {data.get('timestamp', 'N/A')}")
        print(f"Total problems: {results.get('total', 0)}")
        print(f"Passed: {results.get('passed', 0)}")
        print(f"Failed: {results.get('failed', 0)}")
        print(f"Pass rate: {results.get('pass_rate', 0):.2%}")
        print(f"Template matches: {results.get('template_matches', 0)}")
        print(f"LLM generated: {results.get('llm_generated', 0)}")
        print(f"Elapsed time: {data.get('elapsed_time_seconds', 0)/60:.2f} minutes")
        print("="*80)
        
    elif benchmark_results_file.exists():
        print("="*80)
        print("MBPP EVALUATION - IN PROGRESS")
        print("="*80)
        with open(benchmark_results_file) as f:
            data = json.load(f)
        
        mbpp_results = data.get("mbpp", {})
        if mbpp_results:
            print(f"Timestamp: {data.get('timestamp', 'N/A')}")
            print(f"Problems evaluated: {mbpp_results.get('total', 0)}")
            print(f"Passed: {mbpp_results.get('passed', 0)}")
            print(f"Failed: {mbpp_results.get('failed', 0)}")
            if mbpp_results.get('total', 0) > 0:
                print(f"Pass rate: {mbpp_results.get('pass_rate', 0):.2%}")
            print(f"Template matches: {mbpp_results.get('template_matches', 0)}")
            print(f"LLM generated: {mbpp_results.get('llm_generated', 0)}")
            
            # Estimate progress if not complete
            total = mbpp_results.get('total', 0)
            if total < 500:
                print(f"\nProgress: {total}/500 problems ({total/500*100:.1f}%)")
                print("Evaluation still running...")
        print("="*80)
    else:
        print("No results file found. Evaluation may not have started yet.")
        print("Run: python scripts/run_full_mbpp.py")

if __name__ == "__main__":
    check_progress()
