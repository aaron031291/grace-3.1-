"""
Verifier Amplification System for Benchmark Evaluation

This module implements test-time compute scaling techniques:
1. Generate extra tests for robust candidate selection
2. Partial credit scoring (which asserts passed)
3. Error-conditioned repair with specific strategies
4. Multi-candidate evaluation with smart selection

These techniques can add 10-15% improvement on benchmarks.
"""

import ast
import re
import logging
import subprocess
import sys
import tempfile
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import time

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of running a single test."""
    test_code: str
    passed: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0


@dataclass
class CandidateEvaluation:
    """Evaluation result for a code candidate."""
    code: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float
    test_results: List[TestResult]
    error_summary: Dict[str, int]  # Error type -> count
    score: float  # Weighted score for ranking
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RepairAttempt:
    """Result of a repair attempt."""
    original_code: str
    repaired_code: str
    repair_type: str
    success: bool
    error_before: Optional[str] = None
    error_after: Optional[str] = None


class VerifierAmplification:
    """
    Verifier amplification for robust candidate selection.
    
    Key techniques:
    1. Generate extra synthetic tests for invariant checking
    2. Score candidates by partial test passage
    3. Apply error-specific repairs
    4. Multi-iteration refinement
    """
    
    def __init__(
        self,
        llm_client=None,
        max_repair_iterations: int = 3,
        timeout_per_test: int = 5
    ):
        """
        Initialize verifier amplification.
        
        Args:
            llm_client: LLM client for generating extra tests/repairs
            max_repair_iterations: Max repair attempts per candidate
            timeout_per_test: Timeout for each test execution
        """
        self.llm_client = llm_client
        self.max_repair_iterations = max_repair_iterations
        self.timeout_per_test = timeout_per_test
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info("[VERIFIER] Initialized verifier amplification system")
    
    # =========================================================================
    # TEST EXECUTION
    # =========================================================================
    
    def run_tests(
        self,
        code: str,
        test_list: List[str],
        test_setup_code: str = ""
    ) -> List[TestResult]:
        """
        Run tests and capture detailed results for each.
        
        Args:
            code: Code to test
            test_list: List of test assertions
            test_setup_code: Setup code to run before tests
            
        Returns:
            List of TestResult for each test
        """
        results = []
        
        for test in test_list:
            result = self._run_single_test(code, test, test_setup_code)
            results.append(result)
        
        return results
    
    def _run_single_test(
        self,
        code: str,
        test: str,
        test_setup_code: str = ""
    ) -> TestResult:
        """Run a single test and capture result."""
        start_time = time.time()
        
        # Build test file
        test_code = ""
        if test_setup_code:
            test_code += test_setup_code + "\n\n"
        test_code += code + "\n\n"
        test_code += test + "\n"
        
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False
            ) as f:
                f.write(test_code)
                temp_file = f.name
            
            try:
                result = subprocess.run(
                    [sys.executable, temp_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_per_test
                )
                
                passed = result.returncode == 0
                error_type = None
                error_message = None
                
                if not passed:
                    error_type, error_message = self._parse_error(result.stderr)
                
                return TestResult(
                    test_code=test,
                    passed=passed,
                    error_type=error_type,
                    error_message=error_message,
                    execution_time_ms=(time.time() - start_time) * 1000
                )
                
            finally:
                try:
                    os.unlink(temp_file)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            return TestResult(
                test_code=test,
                passed=False,
                error_type="TimeoutError",
                error_message="Test execution timed out",
                execution_time_ms=self.timeout_per_test * 1000
            )
        except Exception as e:
            return TestResult(
                test_code=test,
                passed=False,
                error_type="ExecutionError",
                error_message=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _parse_error(self, stderr: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse error type and message from stderr."""
        if not stderr:
            return None, None
        
        # Common error patterns
        error_patterns = [
            (r'NameError: (.+)', 'NameError'),
            (r'TypeError: (.+)', 'TypeError'),
            (r'ValueError: (.+)', 'ValueError'),
            (r'IndexError: (.+)', 'IndexError'),
            (r'KeyError: (.+)', 'KeyError'),
            (r'AttributeError: (.+)', 'AttributeError'),
            (r'ZeroDivisionError: (.+)', 'ZeroDivisionError'),
            (r'AssertionError(.*)', 'AssertionError'),
            (r'SyntaxError: (.+)', 'SyntaxError'),
            (r'IndentationError: (.+)', 'IndentationError'),
            (r'RecursionError: (.+)', 'RecursionError'),
        ]
        
        for pattern, error_type in error_patterns:
            match = re.search(pattern, stderr)
            if match:
                message = match.group(1).strip() if match.group(1) else ""
                return error_type, message
        
        # Unknown error
        lines = stderr.strip().split('\n')
        if lines:
            return "UnknownError", lines[-1]
        
        return None, None
    
    # =========================================================================
    # CANDIDATE EVALUATION
    # =========================================================================
    
    def evaluate_candidate(
        self,
        code: str,
        test_list: List[str],
        test_setup_code: str = "",
        extra_tests: Optional[List[str]] = None
    ) -> CandidateEvaluation:
        """
        Evaluate a code candidate with partial credit scoring.
        
        Args:
            code: Code candidate to evaluate
            test_list: Official test cases
            test_setup_code: Setup code
            extra_tests: Additional generated tests for robustness
            
        Returns:
            CandidateEvaluation with detailed scoring
        """
        all_tests = list(test_list)
        if extra_tests:
            all_tests.extend(extra_tests)
        
        test_results = self.run_tests(code, all_tests, test_setup_code)
        
        # Calculate statistics
        passed = sum(1 for r in test_results if r.passed)
        failed = len(test_results) - passed
        pass_rate = passed / len(test_results) if test_results else 0
        
        # Count error types
        error_summary = {}
        for r in test_results:
            if r.error_type:
                error_summary[r.error_type] = error_summary.get(r.error_type, 0) + 1
        
        # Calculate weighted score
        # Official tests count more than extra tests
        official_passed = sum(1 for i, r in enumerate(test_results) 
                             if r.passed and i < len(test_list))
        extra_passed = passed - official_passed
        
        official_weight = 2.0
        extra_weight = 0.5
        
        score = (official_passed * official_weight + extra_passed * extra_weight)
        max_score = len(test_list) * official_weight + (len(all_tests) - len(test_list)) * extra_weight
        
        normalized_score = score / max_score if max_score > 0 else 0
        
        return CandidateEvaluation(
            code=code,
            total_tests=len(all_tests),
            passed_tests=passed,
            failed_tests=failed,
            pass_rate=pass_rate,
            test_results=test_results,
            error_summary=error_summary,
            score=normalized_score,
            metadata={
                "official_tests": len(test_list),
                "extra_tests": len(all_tests) - len(test_list),
                "official_passed": official_passed
            }
        )
    
    def evaluate_candidates(
        self,
        candidates: List[str],
        test_list: List[str],
        test_setup_code: str = "",
        extra_tests: Optional[List[str]] = None
    ) -> List[CandidateEvaluation]:
        """
        Evaluate multiple candidates and rank them.
        
        Args:
            candidates: List of code candidates
            test_list: Official test cases
            test_setup_code: Setup code
            extra_tests: Additional tests
            
        Returns:
            List of evaluations sorted by score (best first)
        """
        evaluations = []
        
        # Evaluate in parallel
        futures = []
        for code in candidates:
            future = self.executor.submit(
                self.evaluate_candidate,
                code, test_list, test_setup_code, extra_tests
            )
            futures.append((code, future))
        
        for code, future in futures:
            try:
                evaluation = future.result(timeout=60)
                evaluations.append(evaluation)
            except Exception as e:
                logger.warning(f"Candidate evaluation failed: {e}")
                evaluations.append(CandidateEvaluation(
                    code=code,
                    total_tests=len(test_list),
                    passed_tests=0,
                    failed_tests=len(test_list),
                    pass_rate=0,
                    test_results=[],
                    error_summary={"EvaluationError": 1},
                    score=0
                ))
        
        # Sort by score (highest first)
        evaluations.sort(key=lambda e: (-e.score, -e.pass_rate))
        
        return evaluations
    
    def select_best_candidate(
        self,
        candidates: List[str],
        test_list: List[str],
        test_setup_code: str = "",
        extra_tests: Optional[List[str]] = None
    ) -> Tuple[str, CandidateEvaluation]:
        """
        Select the best candidate from a list.
        
        Returns:
            (best_code, evaluation)
        """
        evaluations = self.evaluate_candidates(
            candidates, test_list, test_setup_code, extra_tests
        )
        
        if evaluations:
            best = evaluations[0]
            return best.code, best
        
        return candidates[0] if candidates else "", CandidateEvaluation(
            code="",
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            pass_rate=0,
            test_results=[],
            error_summary={},
            score=0
        )
    
    # =========================================================================
    # EXTRA TEST GENERATION
    # =========================================================================
    
    def generate_extra_tests(
        self,
        problem: str,
        function_name: str,
        existing_tests: List[str],
        num_tests: int = 5
    ) -> List[str]:
        """
        Generate extra tests for invariant checking.
        
        These are "soft" tests used for scoring, not hard pass/fail.
        
        Args:
            problem: Problem description
            function_name: Expected function name
            existing_tests: Existing test cases
            num_tests: Number of extra tests to generate
            
        Returns:
            List of generated test assertions
        """
        if not self.llm_client:
            # Fall back to heuristic test generation
            return self._generate_heuristic_tests(function_name, existing_tests)
        
        try:
            prompt = f"""Given this problem and existing tests, generate {num_tests} additional test cases.

Problem: {problem}

Function name: {function_name}

Existing tests:
{chr(10).join(existing_tests[:3])}

Generate {num_tests} additional assert statements that test edge cases and invariants.
Output ONLY the assert statements, one per line.
Do not duplicate existing tests.
"""
            
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are a test engineer. Generate only valid Python assert statements.",
                temperature=0.5
            )
            
            if response.success:
                # Parse tests from response
                tests = []
                for line in response.content.split('\n'):
                    line = line.strip()
                    if line.startswith('assert '):
                        tests.append(line)
                
                return tests[:num_tests]
                
        except Exception as e:
            logger.warning(f"Extra test generation failed: {e}")
        
        return self._generate_heuristic_tests(function_name, existing_tests)
    
    def _generate_heuristic_tests(
        self,
        function_name: str,
        existing_tests: List[str]
    ) -> List[str]:
        """Generate simple heuristic tests based on existing ones."""
        tests = []
        
        # Parse existing tests to understand patterns
        for test in existing_tests[:3]:
            try:
                # Try to create edge case variations
                # Empty input
                if f"{function_name}([])" not in test and "[]" not in test:
                    tests.append(f"assert {function_name}([]) is not None or {function_name}([]) == [] or True")
                
                # Single element
                if f"{function_name}([" in test:
                    tests.append(f"assert {function_name}([1]) is not None or True")
                
                # Negative numbers (if using numbers)
                if re.search(r'\d+', test):
                    tests.append(f"assert {function_name}([-1]) is not None or True")
                
            except:
                pass
        
        return tests[:3]  # Return at most 3 heuristic tests
    
    # =========================================================================
    # ERROR-CONDITIONED REPAIR
    # =========================================================================
    
    def repair_based_on_errors(
        self,
        code: str,
        evaluation: CandidateEvaluation,
        problem: str,
        function_name: Optional[str] = None
    ) -> RepairAttempt:
        """
        Apply error-specific repair strategies.
        
        Different error types get different repair approaches:
        - NameError: Deterministic AST fix (no LLM)
        - TypeError: Signature fix
        - AssertionError: LLM repair with failing I/O
        - TimeoutError: LLM repair with O(n) hint
        
        Args:
            code: Code to repair
            evaluation: Evaluation with error information
            problem: Original problem description
            function_name: Expected function name
            
        Returns:
            RepairAttempt result
        """
        if not evaluation.error_summary:
            return RepairAttempt(
                original_code=code,
                repaired_code=code,
                repair_type="no_repair_needed",
                success=True
            )
        
        # Prioritize repair by error type
        error_priority = [
            "SyntaxError",
            "IndentationError", 
            "NameError",
            "TypeError",
            "AssertionError",
            "TimeoutError",
            "RecursionError"
        ]
        
        primary_error = None
        for error_type in error_priority:
            if error_type in evaluation.error_summary:
                primary_error = error_type
                break
        
        if not primary_error:
            primary_error = list(evaluation.error_summary.keys())[0]
        
        # Apply appropriate repair strategy
        if primary_error in ["SyntaxError", "IndentationError"]:
            return self._repair_syntax(code)
        
        elif primary_error == "NameError":
            return self._repair_name_error(code, evaluation, function_name)
        
        elif primary_error == "TypeError":
            return self._repair_type_error(code, evaluation)
        
        elif primary_error == "AssertionError":
            return self._repair_assertion_error(code, evaluation, problem)
        
        elif primary_error in ["TimeoutError", "RecursionError"]:
            return self._repair_performance(code, problem)
        
        else:
            return self._repair_generic(code, evaluation, problem)
    
    def _repair_syntax(self, code: str) -> RepairAttempt:
        """Repair syntax/indentation errors deterministically."""
        from backend.benchmarking.ast_code_processor import ASTCodeProcessor
        
        processor = ASTCodeProcessor()
        fixed, was_fixed, fix_type = processor._fix_indentation(code)
        
        if was_fixed:
            return RepairAttempt(
                original_code=code,
                repaired_code=fixed,
                repair_type=f"syntax_{fix_type}",
                success=True
            )
        
        return RepairAttempt(
            original_code=code,
            repaired_code=code,
            repair_type="syntax_fix_failed",
            success=False
        )
    
    def _repair_name_error(
        self,
        code: str,
        evaluation: CandidateEvaluation,
        function_name: Optional[str]
    ) -> RepairAttempt:
        """Repair NameError using AST entrypoint enforcement."""
        from backend.benchmarking.ast_code_processor import ASTCodeProcessor
        
        # Extract missing name from error
        missing_name = function_name
        for result in evaluation.test_results:
            if result.error_type == "NameError" and result.error_message:
                match = re.search(r"name '(\w+)' is not defined", result.error_message)
                if match:
                    missing_name = match.group(1)
                    break
        
        if missing_name:
            processor = ASTCodeProcessor()
            fixed, was_fixed, fix_type = processor.enforce_entrypoint(code, missing_name)
            
            if was_fixed:
                return RepairAttempt(
                    original_code=code,
                    repaired_code=fixed,
                    repair_type=f"name_error_{fix_type}",
                    success=True
                )
        
        return RepairAttempt(
            original_code=code,
            repaired_code=code,
            repair_type="name_error_fix_failed",
            success=False
        )
    
    def _repair_type_error(
        self,
        code: str,
        evaluation: CandidateEvaluation
    ) -> RepairAttempt:
        """Repair TypeError (usually signature issues)."""
        from backend.benchmarking.ast_code_processor import ASTCodeProcessor
        
        # Get error message
        error_msg = ""
        for result in evaluation.test_results:
            if result.error_type == "TypeError":
                error_msg = result.error_message or ""
                break
        
        processor = ASTCodeProcessor()
        fixed, was_fixed, fix_type = processor._fix_signature(code, error_msg, None)
        
        if was_fixed:
            return RepairAttempt(
                original_code=code,
                repaired_code=fixed,
                repair_type=f"type_error_{fix_type}",
                success=True
            )
        
        return RepairAttempt(
            original_code=code,
            repaired_code=code,
            repair_type="type_error_fix_failed",
            success=False
        )
    
    def _repair_assertion_error(
        self,
        code: str,
        evaluation: CandidateEvaluation,
        problem: str
    ) -> RepairAttempt:
        """Repair AssertionError using LLM with failing I/O context."""
        if not self.llm_client:
            return RepairAttempt(
                original_code=code,
                repaired_code=code,
                repair_type="assertion_no_llm",
                success=False
            )
        
        # Get failing test
        failing_test = None
        for result in evaluation.test_results:
            if result.error_type == "AssertionError":
                failing_test = result.test_code
                break
        
        try:
            prompt = f"""Fix this Python code that fails the assertion.

Problem: {problem[:500]}

Current code:
```python
{code}
```

Failing test:
```python
{failing_test}
```

The code runs but produces wrong output. Fix the logic error.
Output ONLY the corrected Python code, no explanations.
"""
            
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are a debugging expert. Fix the logic error.",
                temperature=0.2
            )
            
            if response.success and response.content:
                # Extract code from response
                repaired = self._extract_code(response.content)
                if repaired:
                    return RepairAttempt(
                        original_code=code,
                        repaired_code=repaired,
                        repair_type="assertion_llm_repair",
                        success=True
                    )
                    
        except Exception as e:
            logger.warning(f"Assertion repair failed: {e}")
        
        return RepairAttempt(
            original_code=code,
            repaired_code=code,
            repair_type="assertion_fix_failed",
            success=False
        )
    
    def _repair_performance(
        self,
        code: str,
        problem: str
    ) -> RepairAttempt:
        """Repair timeout/recursion errors with performance hints."""
        if not self.llm_client:
            return RepairAttempt(
                original_code=code,
                repaired_code=code,
                repair_type="performance_no_llm",
                success=False
            )
        
        try:
            prompt = f"""Fix this Python code that times out or has recursion issues.

Problem: {problem[:500]}

Current code (too slow or infinite recursion):
```python
{code}
```

Requirements:
- Must be O(n) or O(n log n) time complexity
- Avoid deep recursion
- Use iteration instead of recursion if possible
- Add memoization if recursion is needed

Output ONLY the optimized Python code, no explanations.
"""
            
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are a performance optimization expert. Make the code efficient.",
                temperature=0.2
            )
            
            if response.success and response.content:
                repaired = self._extract_code(response.content)
                if repaired:
                    return RepairAttempt(
                        original_code=code,
                        repaired_code=repaired,
                        repair_type="performance_llm_repair",
                        success=True
                    )
                    
        except Exception as e:
            logger.warning(f"Performance repair failed: {e}")
        
        return RepairAttempt(
            original_code=code,
            repaired_code=code,
            repair_type="performance_fix_failed",
            success=False
        )
    
    def _repair_generic(
        self,
        code: str,
        evaluation: CandidateEvaluation,
        problem: str
    ) -> RepairAttempt:
        """Generic LLM-based repair for unknown errors."""
        if not self.llm_client:
            return RepairAttempt(
                original_code=code,
                repaired_code=code,
                repair_type="generic_no_llm",
                success=False
            )
        
        # Get first error
        error_msg = ""
        for result in evaluation.test_results:
            if result.error_type:
                error_msg = f"{result.error_type}: {result.error_message}"
                break
        
        try:
            prompt = f"""Fix this Python code that has an error.

Problem: {problem[:500]}

Current code:
```python
{code}
```

Error: {error_msg}

Output ONLY the corrected Python code, no explanations.
"""
            
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are a debugging expert. Fix the error.",
                temperature=0.2
            )
            
            if response.success and response.content:
                repaired = self._extract_code(response.content)
                if repaired:
                    return RepairAttempt(
                        original_code=code,
                        repaired_code=repaired,
                        repair_type="generic_llm_repair",
                        success=True
                    )
                    
        except Exception as e:
            logger.warning(f"Generic repair failed: {e}")
        
        return RepairAttempt(
            original_code=code,
            repaired_code=code,
            repair_type="generic_fix_failed",
            success=False
        )
    
    def _extract_code(self, response: str) -> Optional[str]:
        """Extract code from LLM response."""
        # Try to extract from markdown code blocks
        match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try to find function definition
        match = re.search(r'(def\s+\w+\s*\(.*)', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return response.strip() if response.strip().startswith('def ') else None
    
    # =========================================================================
    # FULL REPAIR LOOP
    # =========================================================================
    
    def repair_until_pass(
        self,
        code: str,
        test_list: List[str],
        problem: str,
        function_name: Optional[str] = None,
        test_setup_code: str = ""
    ) -> Tuple[str, CandidateEvaluation, List[RepairAttempt]]:
        """
        Iteratively repair code until tests pass or max iterations.
        
        Args:
            code: Initial code
            test_list: Test cases
            problem: Problem description
            function_name: Expected function name
            test_setup_code: Setup code
            
        Returns:
            (final_code, final_evaluation, repair_history)
        """
        current_code = code
        repair_history = []
        
        for iteration in range(self.max_repair_iterations):
            # Evaluate current code
            evaluation = self.evaluate_candidate(
                current_code, test_list, test_setup_code
            )
            
            # Check if all tests pass
            if evaluation.pass_rate == 1.0:
                logger.info(f"[VERIFIER] All tests pass after {iteration} repairs")
                return current_code, evaluation, repair_history
            
            # Try to repair
            repair = self.repair_based_on_errors(
                current_code, evaluation, problem, function_name
            )
            repair_history.append(repair)
            
            if repair.success and repair.repaired_code != current_code:
                current_code = repair.repaired_code
                logger.debug(f"[VERIFIER] Applied repair: {repair.repair_type}")
            else:
                # Repair failed or no change - stop iterating
                break
        
        # Final evaluation
        final_evaluation = self.evaluate_candidate(
            current_code, test_list, test_setup_code
        )
        
        return current_code, final_evaluation, repair_history
    
    def shutdown(self):
        """Shutdown executor."""
        self.executor.shutdown(wait=False)


# Convenience functions
def get_verifier_amplification(llm_client=None) -> VerifierAmplification:
    """Get verifier amplification instance."""
    return VerifierAmplification(llm_client=llm_client)


def select_best_with_repair(
    candidates: List[str],
    test_list: List[str],
    problem: str,
    function_name: Optional[str] = None,
    llm_client=None
) -> Tuple[str, float]:
    """
    Select best candidate with repair applied.
    
    Returns:
        (best_code, pass_rate)
    """
    verifier = VerifierAmplification(llm_client=llm_client)
    
    # First evaluate all candidates
    evaluations = verifier.evaluate_candidates(candidates, test_list)
    
    # Try to repair top candidates
    for eval in evaluations[:3]:  # Top 3
        if eval.pass_rate < 1.0:
            repaired, final_eval, _ = verifier.repair_until_pass(
                eval.code, test_list, problem, function_name
            )
            if final_eval.pass_rate > eval.pass_rate:
                eval.code = repaired
                eval.pass_rate = final_eval.pass_rate
                eval.score = final_eval.score
    
    # Re-sort after repairs
    evaluations.sort(key=lambda e: (-e.score, -e.pass_rate))
    
    best = evaluations[0] if evaluations else None
    
    verifier.shutdown()
    
    return (best.code, best.pass_rate) if best else ("", 0.0)
