#!/usr/bin/env python3
"""
Monitor MBPP Evaluation Progress

Continuously monitors the progress of a running MBPP evaluation.
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime

def monitor_evaluation():
    """Monitor evaluation progress."""
    project_root = Path(__file__).parent.parent
    results_file = project_root / "full_mbpp_results.json"
    
    print("="*80)
    print("MBPP EVALUATION MONITOR")
    print("="*80)
    print("Monitoring: full_mbpp_results.json")
    print("Press Ctrl+C to stop monitoring")
    print("="*80)
    print()
    
    last_total = 0
    last_passed = 0
    
    try:
        while True:
            if results_file.exists():
                try:
                    with open(results_file, 'r') as f:
                        data = json.load(f)
                    
                    results = data.get("results", {})
                    total = results.get("total", 0)
                    passed = results.get("passed", 0)
                    failed = results.get("failed", 0)
                    pass_rate = results.get("pass_rate", 0.0)
                    template_matches = results.get("template_matches", 0)
                    llm_generated = results.get("llm_generated", 0)
                    timestamp = data.get("timestamp", "Unknown")
                    
                    # Check if evaluation is complete
                    if total == 500 and (passed + failed) == 500:
                        print("\n" + "="*80)
                        print("EVALUATION COMPLETE!")
                        print("="*80)
                        print(f"Timestamp: {timestamp}")
                        print(f"Total problems: {total}")
                        print(f"Passed: {passed}")
                        print(f"Failed: {failed}")
                        print(f"Pass rate: {pass_rate:.2%}")
                        print(f"Template matches: {template_matches}")
                        print(f"LLM generated: {llm_generated}")
                        print("="*80)
                        break
                    
                    # Show progress if changed
                    if total != last_total or passed != last_passed:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Progress: {total}/500 problems")
                        print(f"  Passed: {passed} | Failed: {failed} | Pass rate: {pass_rate:.2%}")
                        print(f"  Templates: {template_matches} | LLM: {llm_generated}")
                        print()
                        
                        last_total = total
                        last_passed = passed
                    
                except json.JSONDecodeError:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Results file exists but not yet valid JSON (evaluation in progress)...")
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Error reading results: {e}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for results file...")
            
            time.sleep(5)  # Check every 5 seconds
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
        if results_file.exists():
            print("\nFinal status:")
            try:
                with open(results_file, 'r') as f:
                    data = json.load(f)
                results = data.get("results", {})
                print(f"  Total: {results.get('total', 0)}")
                print(f"  Passed: {results.get('passed', 0)}")
                print(f"  Failed: {results.get('failed', 0)}")
                print(f"  Pass rate: {results.get('pass_rate', 0.0):.2%}")
            except:
                print("  Could not read final results")

if __name__ == "__main__":
    monitor_evaluation()
