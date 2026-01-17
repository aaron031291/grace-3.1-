"""
Parallel MBPP Integration with Multi-threading and Subagents

Uses parallel processing to evaluate multiple problems simultaneously.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import tempfile
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from threading import Lock
import time
from backend.cognitive.enterprise_coding_agent import EnterpriseCodingAgent


class ParallelMBPPIntegration:
    """Parallel MBPP integration with multi-threading."""
    
    def __init__(self, coding_agent=None, max_workers: int = 8):
        """
        Initialize parallel MBPP integration.
        
        Args:
            coding_agent: Grace's EnterpriseCodingAgent instance
            max_workers: Number of parallel workers (default: 8)
        """
        self.coding_agent = coding_agent
        self.problems = []
        self.max_workers = max_workers
        self.results_lock = Lock()
        
    def install_mbpp(self) -> bool:
        """Install MBPP dataset (same as regular integration)."""
        try:
            import datasets
            from datasets import load_dataset
            
            print("[MBPP] Loading FULL dataset from HuggingFace...")
            dataset = load_dataset("mbpp", split="test")
            self.problems = [item for item in dataset]
            print(f"[MBPP] Loaded {len(self.problems)} problems from HuggingFace")
            return True
        except Exception as e:
            print(f"[MBPP] Failed to load dataset: {e}")
            return False
    
    def get_mbpp_problems(self) -> List[Dict[str, Any]]:
        """Get MBPP problems."""
        return self.problems
    
    def _test_code(
        self,
        code: str,
        problem: Dict[str, Any],
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Test generated code against test cases.
        Same implementation as MBPPIntegration._test_code
        """
        try:
            import tempfile
            import subprocess
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
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
                    f.write(code)
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
    
    def _evaluate_single_problem(
        self,
        problem: Dict[str, Any],
        index: int,
        total: int,
        timeout: int = 10,
        use_templates: bool = True,
        template_first: bool = False,
        use_feedback_loop: bool = True,
        use_multi_candidate: bool = True,
        num_candidates: int = 8
    ) -> Dict[str, Any]:
        """
        Evaluate a single problem (runs in parallel worker).
        
        This is a standalone function that can run in parallel.
        Each worker gets its own subagent instance.
        """
        # Create subagent for this worker (thread-safe)
        try:
            from backend.database.session import initialize_session_factory
            session_factory = initialize_session_factory()
            worker_session = session_factory()
        except Exception as e:
            # Fallback to mock session if database unavailable
            from unittest.mock import MagicMock
            worker_session = MagicMock()
        
        # Create subagent instance for this worker
        worker_agent = EnterpriseCodingAgent(session=worker_session)
        
        from backend.benchmarking.mbpp_integration import MBPPIntegration
        
        # Create a new integration instance for this worker with its own subagent
        mbpp = MBPPIntegration(coding_agent=worker_agent)
        
        task_id = problem.get("task_id", f"mbpp_{index}")
        
        try:
            # Try template generation first if enabled
            code = None
            generation_method = None
            
            if use_templates and template_first:
                code = mbpp._try_template_generation(problem)
                if code:
                    generation_method = "template"
            
            # If no template, try LLM (using worker's subagent)
            if not code:
                from backend.cognitive.enterprise_coding_agent import CodingTaskType
                
                task = worker_agent.create_task(
                    task_type=CodingTaskType.CODE_GENERATION,
                    description=problem["text"]
                )
                
                execution_result = worker_agent.execute_task(task.task_id)
                
                if execution_result.get("success"):
                    generation = execution_result.get("result", {}).get("generation")
                    if generation:
                        generation_method = "llm"
                        if hasattr(generation, 'code_after'):
                            code = generation.code_after
                        elif hasattr(generation, 'code'):
                            code = generation.code
                        elif isinstance(generation, dict):
                            code = generation.get('code', '') or generation.get('code_after', '')
                        else:
                            code = str(generation)
            
            # Template fallback if LLM failed
            if not code and use_templates and not template_first:
                code = mbpp._try_template_generation(problem)
                if code:
                    generation_method = "template_fallback"
            
            if not code:
                return {
                    "task_id": task_id,
                    "status": "FAIL",
                    "passed": False,
                    "error": "No code generated",
                    "code": "",
                    "problem_text": problem.get("text", ""),
                    "generation_method": "none"
                }
            
            # Test the code (using same method as regular integration)
            test_result = self._test_code(code, problem, timeout)
            
            return {
                "task_id": task_id,
                "status": "PASS" if test_result["passed"] else "FAIL",
                "passed": test_result["passed"],
                "error": test_result.get("error", ""),
                "code": code,
                "problem_text": problem.get("text", ""),
                "generation_method": generation_method or "unknown"
            }
            
        except Exception as e:
            return {
                "task_id": task_id,
                "status": "FAIL",
                "passed": False,
                "error": str(e),
                "code": "",
                "problem_text": problem.get("text", ""),
                "generation_method": "error"
            }
    
    def run_evaluation_parallel(
        self,
        max_problems: Optional[int] = None,
        timeout: int = 10,
        use_templates: bool = True,
        template_first: bool = False,
        use_feedback_loop: bool = True,
        use_multi_candidate: bool = True,
        num_candidates: int = 8,
        use_threading: bool = True  # Use threading (faster for I/O bound) vs multiprocessing
    ) -> Dict[str, Any]:
        """
        Run MBPP evaluation in parallel.
        
        Args:
            max_problems: Maximum number of problems to evaluate
            timeout: Timeout per problem in seconds
            use_templates: Whether to use template matching
            template_first: Try templates before LLM
            use_threading: Use ThreadPoolExecutor (True) or ProcessPoolExecutor (False)
            
        Returns:
            Dictionary with evaluation results
        """
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
            "results": [],
            "template_matches": 0,
            "llm_generated": 0,
            "feedback_loop_improvements": 0,
            "multi_candidate_improvements": 0
        }
        
        print(f"\n[PARALLEL] Starting parallel evaluation with {self.max_workers} workers...")
        print(f"[PARALLEL] Using {'threading' if use_threading else 'multiprocessing'}")
        
        start_time = time.time()
        
        # Use ThreadPoolExecutor for I/O-bound tasks (LLM calls, file I/O)
        # Use ProcessPoolExecutor for CPU-bound tasks (but requires pickling)
        executor_class = ThreadPoolExecutor if use_threading else ProcessPoolExecutor
        
        with executor_class(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_problem = {
                executor.submit(
                    self._evaluate_single_problem,
                    problem,
                    i,
                    len(problems),
                    timeout,
                    use_templates,
                    template_first,
                    use_feedback_loop,
                    use_multi_candidate,
                    num_candidates
                ): (i, problem) for i, problem in enumerate(problems, 1)
            }
            
            # Process completed tasks
            completed = 0
            for future in as_completed(future_to_problem):
                completed += 1
                i, problem = future_to_problem[future]
                
                try:
                    result = future.result()
                    
                    # Update results thread-safely
                    with self.results_lock:
                        results["results"].append(result)
                        
                        if result["passed"]:
                            results["passed"] += 1
                        else:
                            results["failed"] += 1
                        
                        # Track generation methods
                        method = result.get("generation_method", "")
                        if method == "template" or method == "template_fallback":
                            results["template_matches"] += 1
                        elif method == "llm":
                            results["llm_generated"] += 1
                    
                    # Progress update
                    if completed % 10 == 0 or completed == len(problems):
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        remaining = (len(problems) - completed) / rate if rate > 0 else 0
                        print(f"[PARALLEL] Progress: {completed}/{len(problems)} "
                              f"({completed/len(problems)*100:.1f}%) | "
                              f"Rate: {rate:.2f} prob/s | "
                              f"ETA: {remaining/60:.1f} min")
                
                except Exception as e:
                    print(f"[PARALLEL] Error processing problem {i}: {e}")
                    with self.results_lock:
                        results["failed"] += 1
                        results["results"].append({
                            "task_id": problem.get("task_id", f"mbpp_{i}"),
                            "status": "FAIL",
                            "passed": False,
                            "error": str(e),
                            "generation_method": "error"
                        })
        
        elapsed_time = time.time() - start_time
        
        # Calculate pass rate
        results["pass_rate"] = results["passed"] / results["total"] if results["total"] > 0 else 0.0
        
        print(f"\n[PARALLEL] Evaluation complete!")
        print(f"[PARALLEL] Total time: {elapsed_time/60:.2f} minutes")
        print(f"[PARALLEL] Average rate: {results['total']/elapsed_time:.2f} problems/second")
        
        return results
