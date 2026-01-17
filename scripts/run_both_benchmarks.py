#!/usr/bin/env python3
"""
Run Both MBPP and HumanEval Benchmarks

Unified script to run both benchmark evaluations with frontier techniques.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))


def run_mbpp_evaluation(max_problems=None, use_frontier=True):
    """Run MBPP evaluation."""
    print("="*80)
    print("MBPP BENCHMARK EVALUATION")
    print("="*80)
    print()
    
    try:
        from backend.benchmarking.mbpp_integration import MBPPIntegration
        from backend.cognitive.enterprise_coding_agent import EnterpriseCodingAgent
        
        print("[MBPP] Initializing coding agent...")
        # Create database session
        try:
            from backend.database.session import initialize_session_factory
            session_factory = initialize_session_factory()
            session = session_factory()
        except Exception as e:
            print(f"[MBPP] WARNING: Could not create database session: {e}")
            print("[MBPP] Creating mock session...")
            from unittest.mock import MagicMock
            session = MagicMock()
        
        agent = EnterpriseCodingAgent(session=session)
        
        print("[MBPP] Initializing MBPP integration...")
        mbpp = MBPPIntegration(coding_agent=agent)
        
        print("[MBPP] Loading MBPP dataset...")
        if not mbpp.install_mbpp():
            print("[MBPP] ERROR: Failed to load MBPP dataset")
            return None
        
        print(f"[MBPP] Loaded {len(mbpp.get_mbpp_problems())} problems")
        print()
        
        # Run evaluation
        print("[MBPP] Starting evaluation...")
        print(f"[MBPP] Configuration:")
        print(f"  - Max problems: {max_problems or 'all'}")
        print(f"  - Use frontier techniques: {use_frontier}")
        print(f"  - Feedback loop: {use_frontier}")
        print(f"  - Multi-candidate: {use_frontier}")
        print()
        
        results = mbpp.run_evaluation(
            max_problems=max_problems,
            timeout=10,
            use_templates=True,
            template_first=True,  # Prioritize templates for better performance
            use_feedback_loop=use_frontier,
            use_multi_candidate=use_frontier,
            num_candidates=8 if use_frontier else 1
        )
        
        print()
        print("="*80)
        print("MBPP RESULTS")
        print("="*80)
        print(f"Total problems: {results.get('total', 0)}")
        print(f"Passed: {results.get('passed', 0)}")
        print(f"Failed: {results.get('failed', 0)}")
        print(f"Pass rate: {results.get('pass_rate', 0.0):.2%}")
        print(f"Template matches: {results.get('template_matches', 0)}")
        print(f"LLM generated: {results.get('llm_generated', 0)}")
        print()
        
        return results
        
    except Exception as e:
        print(f"[MBPP] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_humaneval_evaluation(max_problems=None, use_frontier=True):
    """Run HumanEval evaluation."""
    print("="*80)
    print("HUMANEVAL BENCHMARK EVALUATION")
    print("="*80)
    print()
    
    try:
        from backend.benchmarking.humaneval_integration import HumanEvalIntegration
        from backend.cognitive.enterprise_coding_agent import EnterpriseCodingAgent
        
        print("[HUMANEVAL] Initializing coding agent...")
        # Create database session
        try:
            from backend.database.session import initialize_session_factory
            session_factory = initialize_session_factory()
            session = session_factory()
        except Exception as e:
            print(f"[HUMANEVAL] WARNING: Could not create database session: {e}")
            print("[HUMANEVAL] Creating mock session...")
            from unittest.mock import MagicMock
            session = MagicMock()
        
        agent = EnterpriseCodingAgent(session=session)
        
        print("[HUMANEVAL] Initializing HumanEval integration...")
        humaneval = HumanEvalIntegration(coding_agent=agent)
        
        print("[HUMANEVAL] Loading HumanEval dataset...")
        if not humaneval.install_humaneval():
            print("[HUMANEVAL] ERROR: Failed to load HumanEval dataset")
            return None
        
        problems = humaneval.get_humaneval_problems()
        print(f"[HUMANEVAL] Loaded {len(problems)} problems")
        print()
        
        # Check if HumanEval has run_evaluation method with frontier support
        # If not, use basic evaluation
        if hasattr(humaneval, 'run_evaluation'):
            print("[HUMANEVAL] Starting evaluation with frontier techniques...")
            print(f"[HUMANEVAL] Configuration:")
            print(f"  - Max problems: {max_problems or 'all'}")
            print(f"  - Use frontier techniques: {use_frontier}")
            print()
            
            # Try to call with frontier parameters if supported
            try:
                results = humaneval.run_evaluation(
                    max_problems=max_problems,
                    timeout=10,
                    use_templates=True,
                    template_first=False,
                    use_feedback_loop=use_frontier,
                    use_multi_candidate=use_frontier,
                    num_candidates=8 if use_frontier else 1
                )
            except TypeError:
                # Fallback to basic evaluation if frontier params not supported
                print("[HUMANEVAL] Frontier techniques not yet integrated, using basic evaluation...")
                results = humaneval.run_evaluation(
                    max_problems=max_problems,
                    timeout=10
                )
        else:
            print("[HUMANEVAL] Starting basic evaluation...")
            # Use basic evaluation method
            results = {
                "total": len(problems) if not max_problems else min(max_problems, len(problems)),
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "results": []
            }
            
            # Run evaluation manually
            eval_problems = problems[:max_problems] if max_problems else problems
            
            for i, problem in enumerate(eval_problems, 1):
                print(f"[{i}/{len(eval_problems)}] Evaluating problem {problem.get('task_id', i)}...")
                try:
                    # Create task
                    from backend.cognitive.enterprise_coding_agent import CodingTaskType
                    task = agent.create_task(
                        task_type=CodingTaskType.CODE_GENERATION,
                        description=problem.get("prompt", "")
                    )
                    
                    # Execute task
                    execution_result = agent.execute_task(task.task_id)
                    
                    if execution_result.get("success"):
                        # Extract code
                        generation = execution_result.get("result", {}).get("generation")
                        code = ""
                        if generation:
                            if hasattr(generation, 'code_after'):
                                code = generation.code_after
                            elif hasattr(generation, 'code'):
                                code = generation.code
                            elif isinstance(generation, dict):
                                code = generation.get('code', '') or generation.get('code_after', '')
                        
                        # Evaluate
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
            else:
                results["pass_rate"] = 0.0
        
        print()
        print("="*80)
        print("HUMANEVAL RESULTS")
        print("="*80)
        print(f"Total problems: {results.get('total', 0)}")
        print(f"Passed: {results.get('passed', 0)}")
        print(f"Failed: {results.get('failed', 0)}")
        print(f"Pass rate: {results.get('pass_rate', 0.0):.2%}")
        print()
        
        return results
        
    except Exception as e:
        print(f"[HUMANEVAL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run both benchmarks."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run MBPP and HumanEval benchmarks")
    parser.add_argument("--max-problems", type=int, default=None, help="Maximum number of problems per benchmark (default: None = all problems)")
    parser.add_argument("--no-frontier", action="store_true", help="Disable frontier techniques")
    parser.add_argument("--mbpp-only", action="store_true", help="Run only MBPP")
    parser.add_argument("--humaneval-only", action="store_true", help="Run only HumanEval")
    parser.add_argument("--output", type=str, default=None, help="Output file for results JSON")
    
    args = parser.parse_args()
    
    use_frontier = not args.no_frontier
    
    print("="*80)
    print("BENCHMARK EVALUATION SUITE")
    print("="*80)
    print()
    print(f"Configuration:")
    print(f"  - Max problems per benchmark: {args.max_problems or 'all'}")
    print(f"  - Frontier techniques: {'enabled' if use_frontier else 'disabled'}")
    print(f"  - Run MBPP: {not args.humaneval_only}")
    print(f"  - Run HumanEval: {not args.mbpp_only}")
    print()
    
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "max_problems": args.max_problems,
            "use_frontier": use_frontier
        },
        "mbpp": None,
        "humaneval": None
    }
    
    # Run MBPP
    if not args.humaneval_only:
        mbpp_results = run_mbpp_evaluation(
            max_problems=args.max_problems,
            use_frontier=use_frontier
        )
        all_results["mbpp"] = mbpp_results
        
        if mbpp_results:
            print()
            print("="*80)
            print("MBPP SUMMARY")
            print("="*80)
            print(f"Pass rate: {mbpp_results.get('pass_rate', 0.0):.2%}")
            print()
    
    # Run HumanEval
    if not args.mbpp_only:
        humaneval_results = run_humaneval_evaluation(
            max_problems=args.max_problems,
            use_frontier=use_frontier
        )
        all_results["humaneval"] = humaneval_results
        
        if humaneval_results:
            print()
            print("="*80)
            print("HUMANEVAL SUMMARY")
            print("="*80)
            print(f"Pass rate: {humaneval_results.get('pass_rate', 0.0):.2%}")
            print()
    
    # Overall summary
    print()
    print("="*80)
    print("OVERALL SUMMARY")
    print("="*80)
    print()
    
    if all_results["mbpp"]:
        mbpp_rate = all_results["mbpp"].get('pass_rate', 0.0)
        print(f"MBPP:     {mbpp_rate:.2%} ({all_results['mbpp'].get('passed', 0)}/{all_results['mbpp'].get('total', 0)})")
    
    if all_results["humaneval"]:
        he_rate = all_results["humaneval"].get('pass_rate', 0.0)
        print(f"HumanEval: {he_rate:.2%} ({all_results['humaneval'].get('passed', 0)}/{all_results['humaneval'].get('total', 0)})")
    
    if all_results["mbpp"] and all_results["humaneval"]:
        avg_rate = (mbpp_rate + he_rate) / 2
        print(f"Average:   {avg_rate:.2%}")
    
    print()
    
    # Save results
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"Results saved to: {output_path}")
    else:
        # Save to default location
        output_path = project_root / "benchmark_results.json"
        with open(output_path, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"Results saved to: {output_path}")
    
    print()
    print("="*80)
    print("EVALUATION COMPLETE")
    print("="*80)
    print()


if __name__ == "__main__":
    main()
