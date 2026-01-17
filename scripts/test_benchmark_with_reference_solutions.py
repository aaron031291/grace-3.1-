#!/usr/bin/env python3
"""
Test Benchmark Framework with Reference Solutions

Tests the benchmark evaluation framework using reference solutions from datasets.
This validates:
1. Dataset loading works correctly
2. Test execution framework works
3. Evaluation logic is correct
4. Shows what 100% performance looks like

This does NOT use LLM generation - it uses the reference solutions provided with the datasets.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))


def test_mbpp_with_reference_solutions(max_problems=None):
    """Test MBPP using reference solutions from dataset."""
    print("=" * 80)
    print("MBPP BENCHMARK TEST - USING REFERENCE SOLUTIONS")
    print("=" * 80)
    print()
    print("This test uses the reference solutions provided in the MBPP dataset.")
    print("It validates that the evaluation framework works correctly.")
    print()
    
    try:
        from datasets import load_dataset
        from backend.benchmarking.mbpp_integration import MBPPIntegration
        
        # Load dataset
        print("Loading MBPP dataset...")
        dataset = load_dataset("mbpp", split="test")
        problems = [item for item in dataset]
        print(f"Loaded {len(problems)} problems")
        print()
        
        if max_problems:
            problems = problems[:max_problems]
            print(f"Testing with first {len(problems)} problems")
        else:
            print(f"Testing with all {len(problems)} problems")
        print()
        
        # Initialize integration (without coding agent - we'll use reference solutions)
        mbpp_integration = MBPPIntegration(coding_agent=None)
        
        results = {
            "total": len(problems),
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "results": []
        }
        
        print("=" * 80)
        print("TESTING WITH REFERENCE SOLUTIONS")
        print("=" * 80)
        print()
        
        for i, problem in enumerate(problems, 1):
            task_id = f"mbpp_{i-1}"
            print(f"[{i}/{len(problems)}] Testing: {task_id}")
            
            # Format problem
            formatted_problem = {
                "task_id": task_id,
                "text": problem.get("text", ""),
                "code": problem.get("code", ""),
                "test_list": problem.get("test_list", []),
                "test_setup_code": problem.get("test_setup_code", ""),
            }
            
            # Extract function name from reference code
            reference_code = problem.get("code", "")
            if not reference_code:
                print(f"  [SKIP] No reference code provided")
                results["errors"] += 1
                continue
            
            # Use reference solution directly
            print(f"  Using reference solution (length: {len(reference_code)} chars)")
            
            # Evaluate reference solution
            try:
                eval_result = mbpp_integration.evaluate_solution(
                    problem=formatted_problem,
                    solution_code=reference_code,
                    timeout=10
                )
                
                if eval_result["passed"]:
                    print(f"  [PASS] Reference solution passed all tests")
                    results["passed"] += 1
                    status = "PASS"
                else:
                    print(f"  [FAIL] Reference solution failed tests")
                    error_msg = eval_result.get("error", "")
                    if error_msg:
                        print(f"    Error: {error_msg[:200]}")
                    results["failed"] += 1
                    status = "FAIL"
                
                results["results"].append({
                    "task_id": task_id,
                    "status": status,
                    "passed": eval_result["passed"],
                    "error": eval_result.get("error", "")[:200] if not eval_result["passed"] else None
                })
                
            except Exception as e:
                print(f"  [ERROR] Evaluation failed: {e}")
                results["errors"] += 1
                results["results"].append({
                    "task_id": task_id,
                    "status": "ERROR",
                    "passed": False,
                    "error": str(e)[:200]
                })
            
            print()
        
        # Calculate pass rate
        if results["total"] > 0:
            results["pass_rate"] = (results["passed"] / results["total"]) * 100.0
        
        # Display results
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()
        print(f"Total Problems: {results['total']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Errors: {results['errors']}")
        print()
        print(f"Pass Rate: {results.get('pass_rate', 0.0):.2f}%")
        print()
        
        # Expected: Should be 100% since we're using reference solutions
        if results["pass_rate"] < 100.0:
            print("=" * 80)
            print("WARNING: Reference solutions should pass 100%!")
            print("=" * 80)
            print()
            print("Failed problems:")
            for result in results["results"]:
                if not result["passed"]:
                    print(f"  - {result['task_id']}: {result.get('error', 'Unknown error')}")
            print()
        
        return results
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_humaneval_with_reference_solutions(max_problems=None):
    """Test HumanEval using reference solutions from dataset."""
    print("=" * 80)
    print("HUMANEVAL BENCHMARK TEST - USING REFERENCE SOLUTIONS")
    print("=" * 80)
    print()
    print("This test uses the reference solutions provided in the HumanEval dataset.")
    print("It validates that the evaluation framework works correctly.")
    print()
    
    try:
        # Try to load HumanEval using same method as integration
        # Method 1: Try HuggingFace datasets library (preferred)
        try:
            from datasets import load_dataset
            print("Loading HumanEval from HuggingFace...")
            dataset_names = [
                "openai/openai_humaneval",
                "openai/humaneval",
                "bigcode/humaneval",
                "THUDM/humaneval"
            ]
            problems = []
            for name in dataset_names:
                try:
                    dataset = load_dataset(name, split="test")
                    problems = [item for item in dataset]
                    print(f"Loaded {len(problems)} problems from {name}")
                    break
                except Exception as e:
                    print(f"Failed to load from {name}: {e}")
                    continue
        except ImportError:
            # Install datasets library
            print("Installing datasets library...")
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "datasets", "-q"])
            from datasets import load_dataset
            
            print("Loading HumanEval from HuggingFace...")
            dataset_names = [
                "openai/openai_humaneval",
                "openai/humaneval",
                "bigcode/humaneval",
                "THUDM/humaneval"
            ]
            problems = []
            for name in dataset_names:
                try:
                    dataset = load_dataset(name, split="test")
                    problems = [item for item in dataset]
                    print(f"Loaded {len(problems)} problems from {name}")
                    break
                except Exception as e:
                    print(f"Failed to load from {name}: {e}")
                    continue
        
        # Method 2: Fallback to GitHub download
        if not problems:
            print("Trying GitHub download as fallback...")
            import urllib.request
            import json
            
            urls = [
                "https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl",
                "https://github.com/openai/human-eval/raw/master/data/HumanEval.jsonl",
                "https://raw.githubusercontent.com/bigcode-project/bigcode-evaluation-harness/main/humaneval/data/HumanEval.jsonl"
            ]
            
            for url in urls:
                try:
                    with urllib.request.urlopen(url, timeout=10) as response:
                        data = response.read().decode('utf-8')
                        lines = data.strip().split('\n')
                        problems = [json.loads(line) for line in lines if line.strip()]
                        print(f"Loaded {len(problems)} problems from {url}")
                        break
                except Exception as e:
                    print(f"Failed to load from {url}: {e}")
                    continue
        
        if not problems:
            print("ERROR: Could not load HumanEval dataset from any source")
            return None
        
        if max_problems:
            problems = problems[:max_problems]
            print(f"Testing with first {len(problems)} problems")
        else:
            print(f"Testing with all {len(problems)} problems")
        print()
        
        from backend.benchmarking.humaneval_integration import HumanEvalIntegration
        
        # Initialize integration
        humaneval_integration = HumanEvalIntegration(coding_agent=None)
        
        results = {
            "total": len(problems),
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "results": []
        }
        
        print("=" * 80)
        print("TESTING WITH REFERENCE SOLUTIONS")
        print("=" * 80)
        print()
        
        for i, problem in enumerate(problems, 1):
            task_id = problem.get("task_id", f"humaneval_{i-1}")
            print(f"[{i}/{len(problems)}] Testing: {task_id}")
            
            # Format problem
            formatted_problem = {
                "task_id": task_id,
                "prompt": problem.get("prompt", ""),
                "test": problem.get("test", ""),
                "entry_point": problem.get("entry_point", ""),
                "canonical_solution": problem.get("canonical_solution", "")
            }
            
            # Use reference solution
            # HumanEval canonical solutions are just the function body
            # We need to combine the prompt (which includes the signature) with the body
            prompt = problem.get("prompt", "")
            canonical_body = problem.get("canonical_solution", "")
            
            if not canonical_body:
                print(f"  [SKIP] No reference solution provided")
                results["errors"] += 1
                continue
            
            # Combine prompt (signature) with canonical solution (body)
            # The prompt ends with the function signature, canonical solution is the body
            reference_code = prompt + canonical_body
            
            print(f"  Using reference solution (prompt: {len(prompt)} chars, body: {len(canonical_body)} chars, total: {len(reference_code)} chars)")
            
            # Evaluate reference solution
            try:
                eval_result = humaneval_integration.evaluate_solution(
                    problem=formatted_problem,
                    solution_code=reference_code,
                    timeout=10
                )
                
                if eval_result["passed"]:
                    print(f"  [PASS] Reference solution passed all tests")
                    results["passed"] += 1
                    status = "PASS"
                else:
                    print(f"  [FAIL] Reference solution failed tests")
                    error_msg = eval_result.get("error", "")
                    if error_msg:
                        print(f"    Error: {error_msg[:200]}")
                    results["failed"] += 1
                    status = "FAIL"
                
                results["results"].append({
                    "task_id": task_id,
                    "status": status,
                    "passed": eval_result["passed"],
                    "error": eval_result.get("error", "")[:200] if not eval_result["passed"] else None
                })
                
            except Exception as e:
                print(f"  [ERROR] Evaluation failed: {e}")
                results["errors"] += 1
                results["results"].append({
                    "task_id": task_id,
                    "status": "ERROR",
                    "passed": False,
                    "error": str(e)[:200]
                })
            
            print()
        
        # Calculate pass rate
        if results["total"] > 0:
            results["pass_rate"] = (results["passed"] / results["total"]) * 100.0
        
        # Display results
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()
        print(f"Total Problems: {results['total']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Errors: {results['errors']}")
        print()
        print(f"Pass Rate: {results.get('pass_rate', 0.0):.2f}%")
        print()
        
        # Expected: Should be 100% since we're using reference solutions
        if results["pass_rate"] < 100.0:
            print("=" * 80)
            print("WARNING: Reference solutions should pass 100%!")
            print("=" * 80)
            print()
            print("Failed problems:")
            for result in results["results"]:
                if not result["passed"]:
                    print(f"  - {result['task_id']}: {result.get('error', 'Unknown error')}")
            print()
        
        return results
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test benchmarks with reference solutions")
    parser.add_argument(
        "--benchmark",
        choices=["mbpp", "humaneval", "both"],
        default="both",
        help="Which benchmark to test"
    )
    parser.add_argument(
        "--max-problems",
        type=int,
        default=None,
        help="Maximum number of problems to test (default: all)"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("BENCHMARK FRAMEWORK VALIDATION")
    print("=" * 80)
    print()
    print("Testing evaluation framework using reference solutions from datasets.")
    print("This validates that the framework works correctly.")
    print("Expected: 100% pass rate (reference solutions should pass)")
    print()
    
    all_results = {}
    
    if args.benchmark in ["mbpp", "both"]:
        mbpp_results = test_mbpp_with_reference_solutions(max_problems=args.max_problems)
        all_results["mbpp"] = mbpp_results
        
        if args.benchmark == "both":
            print()
            print()
    
    if args.benchmark in ["humaneval", "both"]:
        humaneval_results = test_humaneval_with_reference_solutions(max_problems=args.max_problems)
        all_results["humaneval"] = humaneval_results
    
    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    for benchmark_name, results in all_results.items():
        if results:
            pass_rate = results.get("pass_rate", 0.0)
            total = results.get("total", 0)
            passed = results.get("passed", 0)
            
            print(f"{benchmark_name.upper()}:")
            print(f"  Pass Rate: {pass_rate:.2f}% ({passed}/{total})")
            
            if pass_rate < 100.0:
                print(f"  [WARN] Expected 100% with reference solutions!")
                print(f"  This indicates issues with the evaluation framework.")
            else:
                print(f"  [OK] Framework validated - evaluation works correctly")
            print()
    
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()
    print("If reference solutions pass 100%, the evaluation framework is working correctly.")
    print("Any failures indicate issues with:")
    print("  1. Test execution logic")
    print("  2. Code extraction/formatting")
    print("  3. Test case parsing")
    print()
    print("Once framework is validated, you can challenge LLM-generated code results.")
    print()


if __name__ == "__main__":
    main()
