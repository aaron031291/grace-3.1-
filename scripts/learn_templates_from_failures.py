#!/usr/bin/env python3
"""
Learn Templates from MBPP Failures

Uses proactive learning to analyze failures and suggest new templates.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.benchmarking.template_learning_system import analyze_and_learn_templates

if __name__ == "__main__":
    results_file = project_root / "full_mbpp_results.json"
    
    if not results_file.exists():
        print(f"ERROR: Results file not found: {results_file}")
        print("Please run MBPP evaluation first: python scripts/run_full_mbpp.py")
        sys.exit(1)
    
    learner, suggestions = analyze_and_learn_templates(str(results_file))
    
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Failure patterns identified: {len(learner.failure_patterns)}")
    print(f"Template candidates generated: {len(learner.template_candidates)}")
    print(f"High-confidence suggestions: {len(suggestions)}")
    print(f"\nNext steps:")
    print(f"1. Review learned_templates.json")
    print(f"2. Add promising templates to mbpp_templates.py")
    print(f"3. Re-run evaluation to test improvements")
