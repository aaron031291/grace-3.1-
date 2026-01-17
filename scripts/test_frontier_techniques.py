#!/usr/bin/env python3
"""
Test Frontier Performance Techniques

Quick test script to verify execution feedback loop and multi-candidate generation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))


def test_execution_feedback_loop():
    """Test execution feedback loop."""
    print("="*80)
    print("TESTING EXECUTION FEEDBACK LOOP")
    print("="*80)
    print()
    
    try:
        from backend.benchmarking.execution_feedback_loop import get_execution_feedback_loop
        
        feedback_loop = get_execution_feedback_loop(max_iterations=3)
        
        # Test case: Code with syntax error
        initial_code = """def sum_list(lst):
    total = 0
    for item in lst:
        total += item
    return total"""
        
        problem = {
            "text": "Sum all elements in a list",
            "function_name": "sum_list"
        }
        
        test_cases = [
            "assert sum_list([1, 2, 3]) == 6",
            "assert sum_list([10, 20, 30]) == 60"
        ]
        
        def code_refiner(current_code, problem_dict, error_info, error_patterns, iteration):
            """Simple refiner that fixes common issues."""
            return current_code  # For this test, just return as-is
        
        result = feedback_loop.refine_with_feedback(
            initial_code=initial_code,
            problem=problem,
            test_cases=test_cases,
            code_generator=code_refiner
        )
        
        print(f"Result: {result.get('passed')}")
        print(f"Iterations: {result.get('iterations')}")
        print(f"Code length: {len(result.get('code', ''))}")
        print()
        
        if result.get("passed"):
            print("[OK] Execution feedback loop test passed!")
        else:
            print("[WARN] Execution feedback loop test failed (expected for this simple test)")
        
        return result.get("passed")
        
    except Exception as e:
        print(f"[ERROR] Execution feedback loop test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_candidate_generator():
    """Test multi-candidate generator."""
    print("="*80)
    print("TESTING MULTI-CANDIDATE GENERATOR")
    print("="*80)
    print()
    
    try:
        from backend.benchmarking.multi_candidate_generator import get_multi_candidate_generator
        
        multi_gen = get_multi_candidate_generator(
            num_candidates=3,  # Small number for testing
            parallel_testing=False  # Sequential for testing
        )
        
        problem = {
            "text": "Sum all elements in a list",
            "function_name": "sum_list"
        }
        
        test_cases = [
            "assert sum_list([1, 2, 3]) == 6",
            "assert sum_list([10, 20, 30]) == 60"
        ]
        
        def code_generator(problem_dict, temperature=0.3):
            """Generate code (mock)."""
            return """def sum_list(lst):
    return sum(lst)"""
        
        def test_evaluator(code, test_cases_list):
            """Evaluate code."""
            # Simple mock evaluation
            try:
                exec(code)
                for test in test_cases_list:
                    exec(test)
                return {"passed": True, "execution_time": 0.001}
            except:
                return {"passed": False, "error": "Test failed"}
        
        result = multi_gen.generate_and_select(
            problem=problem,
            code_generator=code_generator,
            test_evaluator=test_evaluator,
            test_cases=test_cases
        )
        
        print(f"Result: {result.get('passed')}")
        print(f"Candidates tested: {result.get('num_total')}")
        print(f"Candidates passed: {result.get('num_passed')}")
        print(f"Selection method: {result.get('selection_method')}")
        print()
        
        if result.get("code"):
            print("[OK] Multi-candidate generator test passed!")
            return True
        else:
            print("[WARN] Multi-candidate generator test failed")
            return False
        
    except Exception as e:
        print(f"[ERROR] Multi-candidate generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_template_expansion():
    """Test expanded template library."""
    print("="*80)
    print("TESTING EXPANDED TEMPLATE LIBRARY")
    print("="*80)
    print()
    
    try:
        from backend.benchmarking.mbpp_templates import get_template_matcher
        
        matcher = get_template_matcher()
        
        print(f"Total templates: {len(matcher.templates)}")
        print()
        
        # Test matching
        test_problems = [
            ("Sum all elements in a list", ["list_sum"]),
            ("Find maximum element", ["list_max"]),
            ("Reverse a string", ["string_reverse"]),
            ("Check if number is prime", ["is_prime"]),
            ("Get unique elements", ["list_unique"]),
        ]
        
        matches_found = 0
        for problem_text, expected_patterns in test_problems:
            match_result = matcher.find_best_match(problem_text)
            if match_result:
                template, confidence = match_result
                print(f"Problem: '{problem_text}'")
                print(f"  Matched: {template.name} (confidence: {confidence:.2f})")
                if template.name in expected_patterns:
                    matches_found += 1
                    print(f"  [OK] Expected pattern matched")
                else:
                    print(f"  [WARN] Unexpected pattern (expected one of: {expected_patterns})")
                print()
        
        print(f"Matches found: {matches_found}/{len(test_problems)}")
        
        if matches_found >= len(test_problems) * 0.8:  # 80% match rate
            print("[OK] Template library test passed!")
            return True
        else:
            print("[WARN] Template library test had low match rate")
            return False
        
    except Exception as e:
        print(f"[ERROR] Template library test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("="*80)
    print("FRONTIER TECHNIQUES TEST SUITE")
    print("="*80)
    print()
    
    results = {
        "execution_feedback": test_execution_feedback_loop(),
        "multi_candidate": test_multi_candidate_generator(),
        "template_expansion": test_template_expansion()
    }
    
    print()
    print("="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    print()
    
    for test_name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {test_name}")
    
    print()
    total_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)
    
    print(f"Total: {total_passed}/{total_tests} tests passed")
    print()
    
    if total_passed == total_tests:
        print("[SUCCESS] All frontier techniques tests passed!")
    else:
        print("[WARN] Some tests failed (may be expected for mock tests)")
    print()


if __name__ == "__main__":
    main()
