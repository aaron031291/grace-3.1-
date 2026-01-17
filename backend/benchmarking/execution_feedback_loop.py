"""
Execution Feedback Loop for Code Generation

Implements iterative refinement based on test failures.
This is a key technique for achieving frontier performance on MBPP/HumanEval.

Based on PerfCodeGen and ReflectionCoder techniques:
- Generate code → Run tests → Get errors → Refine → Repeat
- Use test failures to guide fixes
- Iterate up to 5 times for best results
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import subprocess
import sys
import tempfile
import os
import re

logger = logging.getLogger(__name__)


class ExecutionFeedbackLoop:
    """
    Iterative code refinement using execution feedback.
    
    Flow:
    1. Generate initial code
    2. Run tests
    3. If tests fail, analyze errors
    4. Refine code based on errors
    5. Repeat until tests pass or max iterations
    """
    
    def __init__(
        self,
        max_iterations: int = 5,
        timeout_per_test: int = 10,
        enable_performance_feedback: bool = True
    ):
        """
        Initialize execution feedback loop.
        
        Args:
            max_iterations: Maximum refinement iterations
            timeout_per_test: Timeout per test execution
            enable_performance_feedback: Whether to optimize for performance
        """
        self.max_iterations = max_iterations
        self.timeout_per_test = timeout_per_test
        self.enable_performance_feedback = enable_performance_feedback
    
    def refine_with_feedback(
        self,
        initial_code: str,
        problem: Dict[str, Any],
        test_cases: List[str],
        code_generator=None,
        iteration_callback=None
    ) -> Dict[str, Any]:
        """
        Refine code iteratively using execution feedback.
        
        Args:
            initial_code: Initial code to refine
            problem: Problem description
            test_cases: Test cases to run
            code_generator: Function to generate refined code
            iteration_callback: Callback after each iteration
            
        Returns:
            Dictionary with:
            - code: Final refined code
            - passed: Whether tests passed
            - iterations: Number of iterations
            - errors: List of errors encountered
            - performance: Performance metrics if enabled
        """
        current_code = initial_code
        errors = []
        iteration_history = []
        
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"[FEEDBACK-LOOP] Iteration {iteration}/{self.max_iterations}")
            
            # Run tests
            test_result = self._run_tests(current_code, test_cases, problem)
            
            if test_result["passed"]:
                logger.info(f"[FEEDBACK-LOOP] Tests passed after {iteration} iterations")
                return {
                    "code": current_code,
                    "passed": True,
                    "iterations": iteration,
                    "errors": errors,
                    "iteration_history": iteration_history,
                    "performance": test_result.get("performance")
                }
            
            # Tests failed - analyze errors
            error_info = test_result.get("error", "")
            errors.append({
                "iteration": iteration,
                "error": error_info,
                "code": current_code
            })
            
            # Extract error patterns
            error_patterns = self._extract_error_patterns(error_info, test_result)
            
            # Generate refined code
            if code_generator:
                refined_code = code_generator(
                    current_code=current_code,
                    problem=problem,
                    error_info=error_info,
                    error_patterns=error_patterns,
                    iteration=iteration
                )
                
                if refined_code and refined_code != current_code:
                    current_code = refined_code
                    iteration_history.append({
                        "iteration": iteration,
                        "error": error_info[:200],
                        "refined": True
                    })
                else:
                    # No refinement possible
                    logger.warning(f"[FEEDBACK-LOOP] Could not refine code at iteration {iteration}")
                    break
            else:
                # Try automatic refinement
                refined_code = self._auto_refine_code(
                    current_code,
                    error_info,
                    error_patterns
                )
                
                if refined_code:
                    current_code = refined_code
                    iteration_history.append({
                        "iteration": iteration,
                        "error": error_info[:200],
                        "refined": True
                    })
                else:
                    # Cannot auto-refine
                    break
            
            # Callback
            if iteration_callback:
                iteration_callback(iteration, test_result, current_code)
        
        # Max iterations reached
        logger.warning(f"[FEEDBACK-LOOP] Max iterations reached, tests still failing")
        return {
            "code": current_code,
            "passed": False,
            "iterations": self.max_iterations,
            "errors": errors,
            "iteration_history": iteration_history,
            "final_error": errors[-1]["error"] if errors else "Unknown error"
        }
    
    def _run_tests(
        self,
        code: str,
        test_cases: List[str],
        problem: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run tests and return results."""
        try:
            # Create test file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                # Write code
                f.write(code)
                f.write("\n\n")
                
                # Write test cases
                for test in test_cases:
                    f.write(test)
                    f.write("\n")
                
                test_file = f.name
            
            try:
                # Run tests
                import time
                start_time = time.time()
                
                result = subprocess.run(
                    [sys.executable, test_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_per_test
                )
                
                execution_time = time.time() - start_time
                
                passed = result.returncode == 0
                
                return {
                    "passed": passed,
                    "error": result.stderr if not passed else None,
                    "stdout": result.stdout,
                    "returncode": result.returncode,
                    "execution_time": execution_time,
                    "performance": {
                        "time": execution_time,
                        "efficient": execution_time < 1.0  # Under 1 second is efficient
                    } if self.enable_performance_feedback else None
                }
            finally:
                os.unlink(test_file)
                
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "error": f"Timeout after {self.timeout_per_test} seconds",
                "performance": None
            }
        except Exception as e:
            return {
                "passed": False,
                "error": str(e),
                "performance": None
            }
    
    def _extract_error_patterns(
        self,
        error_message: str,
        test_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract patterns from error messages."""
        patterns = {
            "error_type": None,
            "line_number": None,
            "function_name": None,
            "variable_name": None,
            "syntax_error": False,
            "name_error": False,
            "type_error": False,
            "value_error": False,
            "indentation_error": False
        }
        
        error_lower = error_message.lower()
        
        # Error types
        if "syntaxerror" in error_lower or "invalid syntax" in error_lower:
            patterns["syntax_error"] = True
            patterns["error_type"] = "syntax"
        elif "nameerror" in error_lower or "not defined" in error_lower:
            patterns["name_error"] = True
            patterns["error_type"] = "name"
        elif "typeerror" in error_lower or "type" in error_lower:
            patterns["type_error"] = True
            patterns["error_type"] = "type"
        elif "valueerror" in error_lower:
            patterns["value_error"] = True
            patterns["error_type"] = "value"
        elif "indentationerror" in error_lower or "unexpected indent" in error_lower:
            patterns["indentation_error"] = True
            patterns["error_type"] = "indentation"
        
        # Extract line number
        line_match = re.search(r'line\s+(\d+)', error_message, re.IGNORECASE)
        if line_match:
            patterns["line_number"] = int(line_match.group(1))
        
        # Extract function name
        func_match = re.search(r"name\s+'(\w+)'\s+is not defined", error_message, re.IGNORECASE)
        if func_match:
            patterns["function_name"] = func_match.group(1)
        
        return patterns
    
    def _auto_refine_code(
        self,
        code: str,
        error_info: str,
        error_patterns: Dict[str, Any]
    ) -> Optional[str]:
        """Automatically refine code based on error patterns."""
        refined = code
        
        # Fix syntax errors
        if error_patterns.get("syntax_error"):
            # Try to fix common syntax issues
            refined = self._fix_syntax_errors(refined, error_info)
        
        # Fix name errors
        if error_patterns.get("name_error"):
            refined = self._fix_name_errors(refined, error_patterns)
        
        # Fix indentation errors
        if error_patterns.get("indentation_error"):
            refined = self._fix_indentation(refined)
        
        # Fix type errors
        if error_patterns.get("type_error"):
            refined = self._fix_type_errors(refined, error_info)
        
        return refined if refined != code else None
    
    def _fix_syntax_errors(self, code: str, error_info: str) -> str:
        """Fix common syntax errors."""
        # Remove trailing colons if present incorrectly
        lines = code.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Fix missing colons after if/for/while/def
            if re.match(r'^\s*(if|for|while|def|elif|else)\s+.*[^:]$', stripped):
                if not stripped.endswith(':'):
                    line = line.rstrip() + ':'
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_name_errors(self, code: str, error_patterns: Dict[str, Any]) -> str:
        """Fix name errors."""
        missing_name = error_patterns.get("function_name")
        if missing_name:
            # Try to find where function should be defined
            # This is heuristic-based
            pass
        
        return code
    
    def _fix_indentation(self, code: str) -> str:
        """Fix indentation errors."""
        lines = code.split('\n')
        fixed_lines = []
        expected_indent = 0
        
        for line in lines:
            stripped = line.lstrip()
            if not stripped:
                fixed_lines.append('')
                continue
            
            # Calculate expected indentation
            if stripped.startswith(('def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:')):
                # This line should be at base level or indented based on context
                pass
            
            # Use 4 spaces for indentation
            fixed_lines.append(' ' * expected_indent + stripped)
        
        return '\n'.join(fixed_lines)
    
    def _fix_type_errors(self, code: str, error_info: str) -> str:
        """Fix type errors."""
        # Extract type mismatch information
        # This is heuristic-based
        return code


def get_execution_feedback_loop(
    max_iterations: int = 5,
    timeout_per_test: int = 10,
    enable_performance_feedback: bool = True
) -> ExecutionFeedbackLoop:
    """Get execution feedback loop instance."""
    return ExecutionFeedbackLoop(
        max_iterations=max_iterations,
        timeout_per_test=timeout_per_test,
        enable_performance_feedback=enable_performance_feedback
    )
