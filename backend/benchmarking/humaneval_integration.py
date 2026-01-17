"""
HumanEval Integration for Grace

HumanEval is OpenAI's benchmark for evaluating code generation:
- 164 hand-written Python problems
- Each problem has a function signature and docstring
- Tests measure Pass@1, Pass@k metrics
- Industry standard benchmark

Integration with Grace's Coding Agent for evaluation.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import tempfile
import os


class HumanEvalIntegration:
    """Integration with HumanEval benchmark."""
    
    def __init__(self, coding_agent=None):
        """
        Initialize HumanEval integration.
        
        Args:
            coding_agent: Grace's EnterpriseCodingAgent instance
        """
        self.coding_agent = coding_agent
        self.humaneval_path = None
        self.problems = []
        
    def install_humaneval(self) -> bool:
        """Install HumanEval dataset."""
        try:
            # Try multiple methods to load HumanEval
            # Method 1: Try datasets library
            try:
                import datasets
                from datasets import load_dataset
                
                # Load HumanEval dataset
                print("[HUMANEVAL] Loading dataset from HuggingFace...")
                # Try different dataset names
                dataset_names = [
                    "openai/humaneval",
                    "bigcode/humaneval",
                    "THUDM/humaneval"
                ]
                dataset = None
                for name in dataset_names:
                    try:
                        dataset = load_dataset(name, split="test")
                        print(f"[HUMANEVAL] Successfully loaded from {name}")
                        break
                    except:
                        continue
                if dataset is None:
                    raise Exception("Could not load from any HuggingFace dataset name")
                self.problems = [item for item in dataset]
                print(f"[HUMANEVAL] ✓ Loaded {len(self.problems)} problems from HuggingFace")
                return True
            except ImportError:
                # Install datasets library
                print("[HUMANEVAL] Installing datasets library...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "datasets", "-q"])
                
                import datasets
                from datasets import load_dataset
                
                print("[HUMANEVAL] Loading FULL dataset from HuggingFace...")
                # Try different dataset names
                dataset_names = [
                    "openai/humaneval",
                    "bigcode/humaneval",
                    "THUDM/humaneval"
                ]
                dataset = None
                for name in dataset_names:
                    try:
                        dataset = load_dataset(name, split="test")
                        print(f"[HUMANEVAL] ✓ Successfully loaded from {name}")
                        break
                    except Exception as e:
                        print(f"[HUMANEVAL] Failed to load from {name}: {e}")
                        continue
                if dataset is None:
                    raise Exception("Could not load from any HuggingFace dataset name")
                self.problems = [item for item in dataset]
                print(f"[HUMANEVAL] ✓ Loaded {len(self.problems)} problems from HuggingFace")
                return True
            except Exception as e1:
                # Method 2: Try direct download from GitHub
                print(f"[HUMANEVAL] HuggingFace load failed: {e1}")
                print("[HUMANEVAL] Trying direct download from GitHub...")
                try:
                    import json
                    import urllib.request
                    
                    # Try multiple GitHub URLs
                    urls = [
                        "https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl",
                        "https://github.com/openai/human-eval/raw/master/data/HumanEval.jsonl",
                        "https://raw.githubusercontent.com/bigcode-project/bigcode-evaluation-harness/main/humaneval/data/HumanEval.jsonl"
                    ]
                    url = None
                    for test_url in urls:
                        try:
                            with urllib.request.urlopen(test_url) as response:
                                data = response.read().decode('utf-8')
                                lines = data.strip().split('\n')
                                self.problems = [json.loads(line) for line in lines if line.strip()]
                            print(f"[HUMANEVAL] Loaded {len(self.problems)} problems from GitHub ({test_url})")
                            return True
                        except:
                            continue
                    raise Exception("Could not download from any GitHub URL")
                    with urllib.request.urlopen(url) as response:
                        data = response.read().decode('utf-8')
                        lines = data.strip().split('\n')
                        self.problems = [json.loads(line) for line in lines if line.strip()]
                    print(f"[HUMANEVAL] Loaded {len(self.problems)} problems from GitHub")
                    return True
                except Exception as e2:
                    print(f"[HUMANEVAL] GitHub download failed: {e2}")
                    # Method 3: Use local file if exists
                    local_file = Path(__file__).parent.parent.parent / "data" / "HumanEval.jsonl"
                    if local_file.exists():
                        print(f"[HUMANEVAL] Loading from local file: {local_file}")
                        import json
                        with open(local_file, 'r') as f:
                            lines = f.readlines()
                            self.problems = [json.loads(line) for line in lines if line.strip()]
                        print(f"[HUMANEVAL] Loaded {len(self.problems)} problems from local file")
                        return True
                    
                    # Method 4: Fallback to sample problems
                    print("[HUMANEVAL] WARNING: All download methods failed, falling back to sample problems")
                    print("[HUMANEVAL] NOTE: This will only test a subset. For full evaluation, ensure internet connection and datasets library.")
                    try:
                        from backend.benchmarking.humaneval_sample import HUMANEVAL_SAMPLE_PROBLEMS
                        self.problems = HUMANEVAL_SAMPLE_PROBLEMS
                        print(f"[HUMANEVAL] Loaded {len(self.problems)} sample problems")
                        return True
                    except Exception as e3:
                        print(f"[HUMANEVAL] Could not load sample problems: {e3}")
                        return False
                
        except Exception as e:
            print(f"[HUMANEVAL] Could not install HumanEval: {e}")
            return False
    
    def get_humaneval_problems(self) -> List[Dict[str, Any]]:
        """
        Get HumanEval problems.
        
        Returns:
            List of problem dictionaries with:
            - task_id: Problem identifier
            - prompt: Function signature + docstring
            - test: Test cases
            - entry_point: Function name
        """
        if not self.problems:
            if not self.install_humaneval():
                return []
        
        formatted_problems = []
        for i, problem in enumerate(self.problems):
            formatted_problems.append({
                "task_id": f"humaneval_{i}",
                "prompt": problem.get("prompt", ""),
                "test": problem.get("test", ""),
                "entry_point": problem.get("entry_point", ""),
                "canonical_solution": problem.get("canonical_solution", ""),
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
        Evaluate a solution against HumanEval test cases.
        
        Args:
            problem: Problem dictionary
            solution_code: Generated solution code
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with:
            - passed: Whether solution passed all tests
            - test_results: Individual test results
            - error: Error message if failed
        """
        try:
            # Create temporary file with solution
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                # Write the solution code
                f.write(solution_code)
                temp_file = f.name
            
            try:
                # Extract test cases from problem
                test_code = problem.get("test", "")
                entry_point = problem.get("entry_point", "")
                
                # Create test file
                test_file = temp_file.replace('.py', '_test.py')
                with open(test_file, 'w') as f:
                    # Write solution
                    f.write(solution_code)
                    f.write("\n\n")
                    # Write test cases
                    f.write(test_code)
                
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
        Run HumanEval evaluation on Grace's Coding Agent.
        
        Args:
            max_problems: Maximum number of problems to evaluate (None = all)
            timeout: Timeout per problem in seconds
            
        Returns:
            Dictionary with evaluation results:
            - total: Total problems evaluated
            - passed: Number of problems passed
            - failed: Number of problems failed
            - pass_rate: Pass rate percentage
            - results: Detailed results per problem
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
        
        problems = self.get_humaneval_problems()
        if not problems:
            return {
                "error": "Could not load HumanEval problems",
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
            
            try:
                # Create task for coding agent
                from backend.cognitive.enterprise_coding_agent import CodingTaskType
                
                task = self.coding_agent.create_task(
                    task_type=CodingTaskType.CODE_GENERATION,
                    description=problem["prompt"]
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
                        
                        # Clean up code - remove any dictionary/json artifacts
                        if code.startswith('{') or code.startswith("{"):
                            # Try to extract code from dict string
                            import json
                            try:
                                code_dict = json.loads(code)
                                code = code_dict.get('code', '') or code_dict.get('code_after', '')
                            except:
                                # If not JSON, try to find code between quotes
                                if 'code_after' in code or 'code' in code:
                                    # Extract code from string representation
                                    import re
                                    match = re.search(r'code[_\w]*["\']:\s*["\']([^"\']+)["\']', code)
                                    if match:
                                        code = match.group(1)
                        
                        # Extract just the function implementation if prompt is included
                        # HumanEval prompts include the function signature, so we need to extract just the body
                        if problem["prompt"] in code:
                            # Code includes the prompt, extract just the implementation
                            prompt_lines = problem["prompt"].split('\n')
                            code_lines = code.split('\n')
                            # Find where prompt ends and new code begins
                            for i, line in enumerate(code_lines):
                                if i < len(prompt_lines):
                                    continue
                                # Found new code
                                code = '\n'.join(code_lines[i:])
                                break
                        
                        if not code or len(code.strip()) < 10:
                            results["failed"] += 1
                            results["results"].append({
                                "task_id": problem["task_id"],
                                "status": "FAIL",
                                "passed": False,
                                "error": f"No valid code extracted (length: {len(code) if code else 0})"
                            })
                            continue
                        
                        # Evaluate solution
                        eval_result = self.evaluate_solution(problem, code, timeout)
                        
                        if eval_result["passed"]:
                            results["passed"] += 1
                            status = "PASS"
                        else:
                            results["failed"] += 1
                            status = "FAIL"
                        
                        results["results"].append({
                            "task_id": problem["task_id"],
                            "status": status,
                            "passed": eval_result["passed"],
                            "error": eval_result.get("error"),
                            "code": code[:200]  # First 200 chars
                        })
                    else:
                        results["failed"] += 1
                        results["results"].append({
                            "task_id": problem["task_id"],
                            "status": "FAIL",
                            "passed": False,
                            "error": "No code generated"
                        })
                else:
                    results["failed"] += 1
                    results["results"].append({
                        "task_id": problem["task_id"],
                        "status": "FAIL",
                        "passed": False,
                        "error": execution_result.get("error", "Task execution failed")
                    })
                    
            except Exception as e:
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
    
    def compare_to_leaderboard(self, pass_rate: float) -> Dict[str, Any]:
        """
        Compare Grace's performance to HumanEval leaderboard.
        
        Args:
            pass_rate: Grace's pass rate percentage
            
        Returns:
            Dictionary with leaderboard comparison
        """
        # HumanEval leaderboard (approximate, as of 2024)
        leaderboard = {
            "GPT-4": 67.0,
            "GPT-4-Turbo": 74.0,
            "Claude-3-Opus": 84.9,
            "Claude-3.5-Sonnet": 84.9,
            "DeepSeek-Coder-V2": 90.2,
            "Human Expert": 95.0
        }
        
        comparison = {
            "grace_pass_rate": pass_rate,
            "leaderboard": leaderboard,
            "rank": "Below leaderboard",
            "gap_to_top": leaderboard.get("DeepSeek-Coder-V2", 90.2) - pass_rate
        }
        
        # Determine rank
        sorted_models = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)
        for i, (model, rate) in enumerate(sorted_models):
            if pass_rate >= rate:
                comparison["rank"] = f"Above {model}"
                break
            elif i == len(sorted_models) - 1:
                comparison["rank"] = "Below all models"
        
        return comparison


def get_humaneval_integration(coding_agent=None):
    """Factory function to get HumanEval integration."""
    return HumanEvalIntegration(coding_agent=coding_agent)
