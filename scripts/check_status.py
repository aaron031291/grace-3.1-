#!/usr/bin/env python3
"""Quick status check for MBPP evaluation."""
import json
from pathlib import Path

results_file = Path("full_mbpp_results.json")
if results_file.exists():
    with open(results_file) as f:
        data = json.load(f)
    results = data.get("results", {})
    print("="*60)
    print("CURRENT STATUS")
    print("="*60)
    print(f"Timestamp: {data.get('timestamp', 'Unknown')}")
    print(f"Total: {results.get('total', 0)}/500")
    print(f"Passed: {results.get('passed', 0)}")
    print(f"Failed: {results.get('failed', 0)}")
    print(f"Pass rate: {results.get('pass_rate', 0.0):.2%}")
    print(f"Template matches: {results.get('template_matches', 0)}")
    print(f"LLM generated: {results.get('llm_generated', 0)}")
    print("="*60)
    
    if results.get('total', 0) == 500:
        print("\n[COMPLETE] EVALUATION COMPLETE!")
    else:
        print(f"\n[IN PROGRESS] Evaluation in progress... ({results.get('total', 0)}/500)")
else:
    print("Results file not found. Evaluation may not have started yet.")
