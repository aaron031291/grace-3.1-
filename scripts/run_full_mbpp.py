#!/usr/bin/env python3
"""
Run Full MBPP Dataset Evaluation

Runs evaluation on all 500 MBPP test problems with progress tracking.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.benchmarking.mbpp_integration import MBPPIntegration
from backend.cognitive.enterprise_coding_agent import EnterpriseCodingAgent


def main():
    """Run full MBPP evaluation."""
    print("="*80)
    print("FULL MBPP DATASET EVALUATION")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dataset: MBPP test set (500 problems)")
    print("="*80)
    print()
    
    try:
        # Create database session
        print("[INIT] Initializing coding agent...")
        try:
            from backend.database.session import initialize_session_factory
            session_factory = initialize_session_factory()
            session = session_factory()
        except Exception as e:
            print(f"[INIT] WARNING: Could not create database session: {e}")
            print("[INIT] Creating mock session...")
            from unittest.mock import MagicMock
            session = MagicMock()
        
        agent = EnterpriseCodingAgent(session=session)
        
        print("[INIT] Initializing MBPP integration...")
        mbpp = MBPPIntegration(coding_agent=agent)
        
        print("[INIT] Loading MBPP dataset...")
        if not mbpp.install_mbpp():
            print("[ERROR] Failed to load MBPP dataset")
            return
        
        print()
        print("[CONFIG] Configuration:")
        print(f"  - Total problems: 500 (full dataset)")
        print(f"  - Templates: enabled (LLM-first, templates as fallback)")
        print(f"  - Feedback loop: enabled")
        print(f"  - Multi-candidate: enabled (8 candidates)")
        print(f"  - Timeout: 10 seconds per problem")
        print()
        
        start_time = time.time()
        
        # Run evaluation on full dataset (max_problems=None means all)
        # template_first=False means LLM first, templates as fallback
        results = mbpp.run_evaluation(
            max_problems=None,  # Run all 500 problems
            timeout=10,
            use_templates=True,
            template_first=False,  # LLM first, templates as fallback
            use_feedback_loop=True,
            use_multi_candidate=True,
            num_candidates=8
        )
        
        elapsed_time = time.time() - start_time
        
        print()
        print("="*80)
        print("FULL MBPP RESULTS")
        print("="*80)
        print(f"Total problems: {results['total']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Pass rate: {results['pass_rate']:.2%}")
        print(f"Template matches: {results.get('template_matches', 0)}")
        print(f"LLM generated: {results.get('llm_generated', 0)}")
        print(f"Feedback loop improvements: {results.get('feedback_loop_improvements', 0)}")
        print(f"Multi-candidate improvements: {results.get('multi_candidate_improvements', 0)}")
        print(f"Total time: {elapsed_time/60:.2f} minutes ({elapsed_time:.2f} seconds)")
        print("="*80)
        
        # Save results
        output_file = project_root / "full_mbpp_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "configuration": {
                    "max_problems": None,
                    "use_frontier": True,
                    "full_dataset": True
                },
                "results": results,
                "elapsed_time_seconds": elapsed_time
            }, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        
        return results
        
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Evaluation stopped by user")
        print("Partial results may be available in benchmark_results.json")
        return None
    except Exception as e:
        print(f"\n[ERROR] Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
