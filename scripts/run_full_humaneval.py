#!/usr/bin/env python3
"""
Run Full HumanEval Dataset Evaluation

Runs evaluation on all HumanEval problems (164 problems).
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

from backend.benchmarking.humaneval_integration import HumanEvalIntegration
from backend.cognitive.enterprise_coding_agent import EnterpriseCodingAgent


def main():
    """Run full HumanEval evaluation."""
    print("="*80)
    print("FULL HUMANEVAL DATASET EVALUATION")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dataset: HumanEval (164 problems)")
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
        
        print("[INIT] Initializing HumanEval integration...")
        humaneval = HumanEvalIntegration(coding_agent=agent)
        
        print("[INIT] Loading HumanEval dataset...")
        if not humaneval.install_humaneval():
            print("[ERROR] Failed to load HumanEval dataset")
            return
        
        problems = humaneval.get_humaneval_problems()
        print(f"[INIT] Loaded {len(problems)} problems")
        print()
        print("[CONFIG] Configuration:")
        print(f"  - Total problems: {len(problems)} (full dataset)")
        print(f"  - Templates: enabled (template-first)")
        print(f"  - Timeout: 10 seconds per problem")
        print()
        
        start_time = time.time()
        
        # Check if HumanEval has run_evaluation method
        if hasattr(humaneval, 'run_evaluation'):
            print("[EVAL] Starting evaluation...")
            try:
                results = humaneval.run_evaluation(
                    max_problems=None,  # Run all problems
                    timeout=10,
                    use_templates=True,
                    template_first=True
                )
            except TypeError:
                # Fallback to basic evaluation
                print("[EVAL] Using basic evaluation...")
                results = humaneval.run_evaluation(
                    max_problems=None,
                    timeout=10
                )
        else:
            # Manual evaluation
            print("[EVAL] Starting manual evaluation...")
            results = {
                "total": len(problems),
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "results": []
            }
            
            for i, problem in enumerate(problems, 1):
                print(f"[{i}/{len(problems)}] Evaluating problem {problem.get('task_id', i)}...")
                try:
                    from backend.cognitive.enterprise_coding_agent import CodingTaskType
                    task = agent.create_task(
                        task_type=CodingTaskType.CODE_GENERATION,
                        description=problem.get("prompt", "")
                    )
                    
                    execution_result = agent.execute_task(task.task_id)
                    
                    if execution_result.get("success"):
                        generation = execution_result.get("result", {}).get("generation")
                        code = ""
                        if generation:
                            if hasattr(generation, 'code_after'):
                                code = generation.code_after
                            elif hasattr(generation, 'code'):
                                code = generation.code
                            elif isinstance(generation, dict):
                                code = generation.get('code', '') or generation.get('code_after', '')
                        
                        eval_result = humaneval.evaluate_solution(problem, code, timeout=10)
                        
                        if eval_result.get("passed"):
                            results["passed"] += 1
                            print(f"  [PASS]")
                        else:
                            results["failed"] += 1
                            print(f"  [FAIL]")
                    else:
                        results["failed"] += 1
                        print(f"  [FAIL] No code generated")
                        
                except Exception as e:
                    results["failed"] += 1
                    print(f"  [FAIL] Error: {e}")
            
            if results["total"] > 0:
                results["pass_rate"] = results["passed"] / results["total"]
        
        elapsed_time = time.time() - start_time
        
        print()
        print("="*80)
        print("FULL HUMANEVAL RESULTS")
        print("="*80)
        print(f"Total problems: {results.get('total', 0)}")
        print(f"Passed: {results.get('passed', 0)}")
        print(f"Failed: {results.get('failed', 0)}")
        print(f"Pass rate: {results.get('pass_rate', 0.0):.2%}")
        print(f"Template matches: {results.get('template_matches', 0)}")
        print(f"LLM generated: {results.get('llm_generated', 0)}")
        print(f"Total time: {elapsed_time/60:.2f} minutes ({elapsed_time:.2f} seconds)")
        print("="*80)
        
        # Save results
        output_file = project_root / "full_humaneval_results.json"
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
