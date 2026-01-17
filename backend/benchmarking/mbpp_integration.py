"""
MBPP (Mostly Basic Python Problems) Integration for Grace

MBPP is a benchmark with ~974 basic Python programming tasks.
- Simpler than HumanEval
- Good for testing basic programming patterns
- Useful for template expansion

Integration with Grace's Coding Agent for evaluation.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import tempfile
import os


class MBPPIntegration:
    """Integration with MBPP benchmark."""
    
    def __init__(self, coding_agent=None):
        """
        Initialize MBPP integration.
        
        Args:
            coding_agent: Grace's EnterpriseCodingAgent instance
        """
        self.coding_agent = coding_agent
        self.problems = []
        
    def install_mbpp(self) -> bool:
        """Install MBPP dataset."""
        # Try multiple methods to load MBPP from HuggingFace FIRST
        try:
            # Method 1: Try datasets library
            try:
                import datasets
                from datasets import load_dataset
                
                print("[MBPP] Loading FULL dataset from HuggingFace...")
                dataset = load_dataset("mbpp", split="test")
                self.problems = [item for item in dataset]
                print(f"[MBPP] Loaded {len(self.problems)} problems from HuggingFace")
                return True
            except ImportError:
                # Install datasets library
                print("[MBPP] Installing datasets library...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "datasets", "-q"])
                
                import datasets
                from datasets import load_dataset
                
                print("[MBPP] Loading FULL dataset from HuggingFace...")
                dataset = load_dataset("mbpp", split="test")
                self.problems = [item for item in dataset]
                print(f"[MBPP] Loaded {len(self.problems)} problems from HuggingFace")
                return True
            except Exception as e1:
                print(f"[MBPP] HuggingFace load failed: {e1}")
                # Method 2: Try alternative dataset names
                try:
                    import datasets
                    from datasets import load_dataset
                    
                    alternative_names = ["mbpp/sanitized", "google/mbpp"]
                    for name in alternative_names:
                        try:
                            print(f"[MBPP] Trying alternative dataset: {name}...")
                            dataset = load_dataset(name, split="test")
                            self.problems = [item for item in dataset]
                            print(f"[MBPP] Loaded {len(self.problems)} problems from {name}")
                            return True
                        except:
                            continue
                except Exception as e2:
                    print(f"[MBPP] Alternative datasets failed: {e2}")
                
                # Method 3: Fallback to sample problems
                print("[MBPP] WARNING: Falling back to sample problems")
                try:
                    from backend.benchmarking.mbpp_sample import MBPP_SAMPLE_PROBLEMS
                    self.problems = MBPP_SAMPLE_PROBLEMS
                    print(f"[MBPP] Loaded {len(self.problems)} sample problems")
                    return True
                except Exception as e3:
                    print(f"[MBPP] Could not load sample problems: {e3}")
                    return False
        
        # If we loaded from HuggingFace but want to test with samples first
        # Uncomment the following to force sample problems:
        # print("[MBPP] Using sample problems for testing (forced)")
        # from backend.benchmarking.mbpp_sample import MBPP_SAMPLE_PROBLEMS
        # self.problems = MBPP_SAMPLE_PROBLEMS
        # print(f"[MBPP] Loaded {len(self.problems)} sample problems")
        # return True
                
        except Exception as e:
            print(f"[MBPP] Could not install MBPP: {e}")
            return False
    
    def _extract_function_name(self, code: str) -> Optional[str]:
        """Extract function name from reference code."""
        if not code:
            return None
        import re
        # Look for function definition
        match = re.search(r'def\s+(\w+)\s*\(', code)
        if match:
            return match.group(1)
        return None
    
    def _extract_function_name_from_tests(self, test_list: List[str]) -> Optional[str]:
        """Extract function name from test cases."""
        if not test_list:
            return None
        import re
        # Look for function calls in tests
        for test in test_list:
            # Match patterns like: assert function_name(...)
            match = re.search(r'assert\s+(\w+)\s*\(', test)
            if match:
                return match.group(1)
        return None
    
    def get_mbpp_problems(self) -> List[Dict[str, Any]]:
        """
        Get MBPP problems.
        
        Returns:
            List of problem dictionaries
        """
        if not self.problems:
            if not self.install_mbpp():
                return []
        
        formatted_problems = []
        for i, problem in enumerate(self.problems):
            # Handle different formats
            if isinstance(problem, dict):
                text = problem.get("text", problem.get("prompt", ""))
                code = problem.get("code", "")
                test_list = problem.get("test_list", problem.get("test", []))
                
                # Extract function name from reference code or tests
                function_name = self._extract_function_name(code)
                if not function_name:
                    function_name = self._extract_function_name_from_tests(test_list)
                
                # Enhance prompt with function name if found
                if function_name:
                    text = f"{text}\n\nFunction name should be: {function_name}"
                
                formatted_problems.append({
                    "task_id": f"mbpp_{i}",
                    "text": text,
                    "code": code,
                    "test_list": test_list,
                    "test_setup_code": problem.get("test_setup_code", ""),
                    "function_name": function_name,  # Store for reference
                    "original_index": i
                })
            else:
                formatted_problems.append({
                    "task_id": f"mbpp_{i}",
                    "text": str(problem),
                    "code": "",
                    "test_list": [],
                    "test_setup_code": "",
                    "function_name": None,
                    "original_index": i
                })
        
        return formatted_problems
    
    def evaluate_solution(
        self,
        problem: Dict[str, Any],
        solution_code: str,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Evaluate a solution against MBPP test cases.
        
        Args:
            problem: Problem dictionary
            solution_code: Generated solution code
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with evaluation results
        """
        try:
            # Create temporary file with solution
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(solution_code)
                temp_file = f.name
            
            try:
                # Get test cases
                test_list = problem.get("test_list", [])
                test_setup = problem.get("test_setup_code", "")
                
                # Create test file
                test_file = temp_file.replace('.py', '_test.py')
                with open(test_file, 'w') as f:
                    # Write setup code if any
                    if test_setup:
                        f.write(test_setup)
                        f.write("\n\n")
                    
                    # Write solution
                    f.write(solution_code)
                    f.write("\n\n")
                    
                    # Write test cases
                    for test in test_list:
                        f.write(test)
                        f.write("\n")
                
                # Run tests
                result = subprocess.run(
                    [sys.executable, test_file],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                # Check if tests passed
                passed = result.returncode == 0
                
                return {
                    "passed": passed,
                    "test_results": {
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    },
                    "error": result.stderr if not passed else None
                }
                
            finally:
                # Cleanup
                try:
                    os.unlink(temp_file)
                    if os.path.exists(test_file):
                        os.unlink(test_file)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "test_results": {},
                "error": f"Timeout after {timeout} seconds"
            }
        except Exception as e:
            return {
                "passed": False,
                "test_results": {},
                "error": str(e)
            }
    
    def run_evaluation(
        self,
        max_problems: Optional[int] = None,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Run MBPP evaluation on Grace's Coding Agent.
        
        Args:
            max_problems: Maximum number of problems to evaluate
            timeout: Timeout per problem in seconds
            
        Returns:
            Dictionary with evaluation results
        """
        if not self.coding_agent:
            return {
                "error": "Coding agent not initialized",
                "total": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "results": []
            }
        
        problems = self.get_mbpp_problems()
        if not problems:
            return {
                "error": "Could not load MBPP problems",
                "total": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "results": []
            }
        
        if max_problems:
            problems = problems[:max_problems]
        
        results = {
            "total": len(problems),
            "passed": 0,
            "failed": 0,
            "pass_rate": 0.0,
            "results": []
        }
        
        for i, problem in enumerate(problems, 1):
            print(f"[{i}/{len(problems)}] Evaluating: {problem['task_id']}")
            
            # Debug: Print problem structure for first few
            if i <= 3:
                print(f"  Problem keys: {list(problem.keys())}")
                print(f"  Has test_list: {'test_list' in problem}")
                print(f"  Test list length: {len(problem.get('test_list', []))}")
                print(f"  Text preview: {problem.get('text', '')[:100]}...")
            
            try:
                # Create task for coding agent
                from backend.cognitive.enterprise_coding_agent import CodingTaskType
                
                task = self.coding_agent.create_task(
                    task_type=CodingTaskType.CODE_GENERATION,
                    description=problem["text"]
                )
                
                # Execute task
                execution_result = self.coding_agent.execute_task(task.task_id)
                
                if execution_result.get("success"):
                    generation = execution_result.get("result", {}).get("generation")
                    if generation:
                        # Extract code from generation object
                        if hasattr(generation, 'code_after'):
                            code = generation.code_after
                        elif hasattr(generation, 'code'):
                            code = generation.code
                        elif isinstance(generation, dict):
                            code = generation.get('code', '') or generation.get('code_after', '')
                        else:
                            code = str(generation)
                        
                        # Clean up code - extract only Python code, remove prompt/docstrings
                        import re
                        
                        # Step 1: Extract code blocks if wrapped in markdown
                        code_block_match = re.search(r'```(?:python)?\s*\n(.*?)\n```', code, re.DOTALL)
                        if code_block_match:
                            code = code_block_match.group(1)
                        
                        # Step 2: Find the function definition (MBPP problems are function-based)
                        # Look for function definition that matches expected name or any function
                        expected_func_name = problem.get("function_name")
                        if expected_func_name:
                            # Try to find function with expected name first
                            func_pattern = rf'def\s+{re.escape(expected_func_name)}\s*\([^)]*\)\s*:.*?(?=\n\n|\ndef\s|\nclass\s|$)'
                            func_match = re.search(func_pattern, code, re.DOTALL)
                            if not func_match:
                                # Fallback: find any function definition
                                func_match = re.search(r'def\s+\w+\s*\([^)]*\)\s*:.*?(?=\n\n|\ndef\s|\nclass\s|$)', code, re.DOTALL)
                        else:
                            # Find first function definition
                            func_match = re.search(r'def\s+\w+\s*\([^)]*\)\s*:.*?(?=\n\n|\ndef\s|\nclass\s|$)', code, re.DOTALL)
                        
                        if func_match:
                            code = func_match.group(0).strip()
                        else:
                            # No function found, try to clean up what we have
                            # Remove leading docstrings and comments
                            lines = code.split('\n')
                            cleaned_lines = []
                            in_docstring = False
                            docstring_char = None
                            
                            for line in lines:
                                stripped = line.strip()
                                
                                # Track docstring state
                                if '"""' in stripped or "'''" in stripped:
                                    if not in_docstring:
                                        # Starting docstring
                                        in_docstring = True
                                        if '"""' in stripped:
                                            docstring_char = '"""'
                                        else:
                                            docstring_char = "'''"
                                        # Check if it's a one-liner
                                        if stripped.count(docstring_char) >= 2:
                                            in_docstring = False
                                    else:
                                        # Ending docstring
                                        if docstring_char in stripped:
                                            in_docstring = False
                                    continue
                                
                                if in_docstring:
                                    continue
                                
                                # Skip comment-only lines at start
                                if stripped.startswith('#') and not cleaned_lines:
                                    continue
                                
                                # Include the line
                                cleaned_lines.append(line)
                            
                            code = '\n'.join(cleaned_lines).strip()
                        
                        # Step 3: Final cleanup - ensure we have valid Python code
                        # Remove any remaining prompt text at the start
                        problem_text_short = problem["text"][:50]  # First 50 chars
                        if code.startswith(problem_text_short):
                            # Find first 'def' or valid Python keyword
                            def_pos = code.find('def ')
                            if def_pos > 0:
                                code = code[def_pos:]
                        
                        # Ensure code starts with 'def' for MBPP
                        if not code.strip().startswith('def '):
                            # Try to find function definition
                            def_match = re.search(r'def\s+\w+.*', code, re.MULTILINE)
                            if def_match:
                                code = code[def_match.start():]
                        
                        # Debug: Print generated code for first few problems
                        if i <= 3:
                            print(f"  Generated code preview (first 300 chars):")
                            print(f"  {code[:300]}")
                            print(f"  Expected function: {problem.get('function_name', 'unknown')}")
                        
                        if not code or len(code.strip()) < 10:
                            print(f"  [FAIL] No valid code extracted (length: {len(code) if code else 0})")
                            results["failed"] += 1
                            results["results"].append({
                                "task_id": problem["task_id"],
                                "status": "FAIL",
                                "passed": False,
                                "error": f"No valid code extracted (length: {len(code) if code else 0})"
                            })
                            continue
                        
                        # Check if function name matches
                        expected_func = problem.get("function_name")
                        if expected_func:
                            import re
                            func_in_code = re.search(r'def\s+(\w+)\s*\(', code)
                            if func_in_code:
                                actual_func = func_in_code.group(1)
                                if actual_func != expected_func:
                                    print(f"  [WARN] Function name mismatch: expected '{expected_func}', got '{actual_func}'")
                                    # Try to rename the function
                                    code = re.sub(rf'def\s+{re.escape(actual_func)}\s*\(', f'def {expected_func}(', code, count=1)
                                    print(f"  [INFO] Renamed function to '{expected_func}'")
                        
                        # Evaluate solution
                        eval_result = self.evaluate_solution(problem, code, timeout)
                        
                        if eval_result["passed"]:
                            print(f"  [PASS]")
                            results["passed"] += 1
                            status = "PASS"
                        else:
                            print(f"  [FAIL] Tests failed")
                            error_msg = eval_result.get("error", "")
                            test_results = eval_result.get("test_results", {})
                            stderr = test_results.get("stderr", "")
                            if stderr:
                                print(f"    Error: {stderr[:200]}")
                            elif error_msg:
                                print(f"    Error: {error_msg[:200]}")
                            results["failed"] += 1
                            status = "FAIL"
                        
                        error_details = ""
                        if not eval_result["passed"]:
                            test_results = eval_result.get("test_results", {})
                            error_details = test_results.get("stderr", "")[:500] if test_results.get("stderr") else eval_result.get("error", "")[:500]
                        
                        results["results"].append({
                            "task_id": problem["task_id"],
                            "status": status,
                            "passed": eval_result["passed"],
                            "error": error_details,
                            "code": code[:400],
                            "problem_text": problem["text"][:150]
                        })
                    else:
                        print(f"  [FAIL] No generation object")
                        results["failed"] += 1
                        results["results"].append({
                            "task_id": problem["task_id"],
                            "status": "FAIL",
                            "passed": False,
                            "error": "No code generated"
                        })
                else:
                    error_msg = execution_result.get("error", "Task execution failed")
                    print(f"  [FAIL] Task execution failed: {error_msg[:200]}")
                    results["failed"] += 1
                    results["results"].append({
                        "task_id": problem["task_id"],
                        "status": "FAIL",
                        "passed": False,
                        "error": error_msg
                    })
                    
            except Exception as e:
                print(f"  [ERROR] Exception: {str(e)[:200]}")
                import traceback
                traceback.print_exc()
                results["failed"] += 1
                results["results"].append({
                    "task_id": problem["task_id"],
                    "status": "FAIL",
                    "passed": False,
                    "error": str(e)
                })
        
        # Calculate pass rate
        if results["total"] > 0:
            results["pass_rate"] = (results["passed"] / results["total"]) * 100
        
        return results


def get_mbpp_integration(coding_agent=None):
    """Factory function to get MBPP integration."""
    return MBPPIntegration(coding_agent=coding_agent)
