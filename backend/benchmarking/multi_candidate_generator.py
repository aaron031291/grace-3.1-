"""
Multi-Candidate Code Generation

Generates multiple code candidates and selects the best one.
This is a key technique for achieving frontier performance.

Based on PerfCodeGen and other SOTA techniques:
- Generate k candidates (k=8-20)
- Test all candidates
- Rank by correctness and performance
- Select best candidate
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)


class MultiCandidateGenerator:
    """
    Generate multiple code candidates and select the best.
    
    This improves pass@1 by:
    1. Generating multiple diverse solutions
    2. Testing all candidates
    3. Selecting best performing one
    """
    
    def __init__(
        self,
        num_candidates: int = 8,
        temperature_range: tuple = (0.2, 0.8),
        parallel_testing: bool = True,
        max_workers: int = 4
    ):
        """
        Initialize multi-candidate generator.
        
        Args:
            num_candidates: Number of candidates to generate (k)
            temperature_range: Temperature range for diversity
            parallel_testing: Whether to test candidates in parallel
            max_workers: Max workers for parallel testing
        """
        self.num_candidates = num_candidates
        self.temperature_range = temperature_range
        self.parallel_testing = parallel_testing
        self.max_workers = max_workers
    
    def generate_and_select(
        self,
        problem: Dict[str, Any],
        code_generator: Callable,
        test_evaluator: Callable,
        test_cases: List[str]
    ) -> Dict[str, Any]:
        """
        Generate multiple candidates and select the best.
        
        Args:
            problem: Problem description
            code_generator: Function to generate code (takes problem, temperature)
            test_evaluator: Function to evaluate code (takes code, test_cases)
            test_cases: Test cases to run
            
        Returns:
            Dictionary with:
            - code: Best code candidate
            - passed: Whether best candidate passed
            - candidates: All candidates with results
            - selection_method: How candidate was selected
        """
        logger.info(f"[MULTI-CANDIDATE] Generating {self.num_candidates} candidates...")
        
        # Generate candidates with different temperatures
        candidates = []
        temperatures = self._generate_temperatures()
        
        for i, temp in enumerate(temperatures, 1):
            logger.debug(f"[MULTI-CANDIDATE] Generating candidate {i}/{self.num_candidates} (temp={temp:.2f})")
            
            try:
                code = code_generator(problem, temperature=temp)
                if code:
                    candidates.append({
                        "code": code,
                        "temperature": temp,
                        "candidate_id": i,
                        "tested": False
                    })
            except Exception as e:
                logger.warning(f"[MULTI-CANDIDATE] Failed to generate candidate {i}: {e}")
        
        if not candidates:
            return {
                "code": None,
                "passed": False,
                "candidates": [],
                "error": "No candidates generated"
            }
        
        logger.info(f"[MULTI-CANDIDATE] Generated {len(candidates)} candidates, testing...")
        
        # Test all candidates
        if self.parallel_testing:
            tested_candidates = self._test_parallel(candidates, test_evaluator, test_cases)
        else:
            tested_candidates = self._test_sequential(candidates, test_evaluator, test_cases)
        
        # Select best candidate
        best_candidate = self._select_best(tested_candidates)
        
        logger.info(f"[MULTI-CANDIDATE] Selected candidate {best_candidate.get('candidate_id')} "
                   f"(passed={best_candidate.get('passed', False)})")
        
        return {
            "code": best_candidate.get("code"),
            "passed": best_candidate.get("passed", False),
            "candidates": tested_candidates,
            "selection_method": "best_performance" if best_candidate.get("passed") else "best_attempt",
            "num_passed": sum(1 for c in tested_candidates if c.get("passed", False)),
            "num_total": len(tested_candidates)
        }
    
    def _generate_temperatures(self) -> List[float]:
        """Generate temperature values for diversity."""
        if self.num_candidates == 1:
            return [0.3]  # Single candidate
        
        min_temp, max_temp = self.temperature_range
        step = (max_temp - min_temp) / (self.num_candidates - 1)
        
        temperatures = []
        for i in range(self.num_candidates):
            temp = min_temp + (i * step)
            temperatures.append(round(temp, 2))
        
        return temperatures
    
    def _test_parallel(
        self,
        candidates: List[Dict[str, Any]],
        test_evaluator: Callable,
        test_cases: List[str]
    ) -> List[Dict[str, Any]]:
        """Test candidates in parallel."""
        tested = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(test_evaluator, cand["code"], test_cases): cand
                for cand in candidates
            }
            
            for future in as_completed(futures):
                candidate = futures[future]
                try:
                    result = future.result()
                    candidate.update({
                        "tested": True,
                        "passed": result.get("passed", False),
                        "error": result.get("error"),
                        "execution_time": result.get("execution_time"),
                        "test_results": result
                    })
                    tested.append(candidate)
                except Exception as e:
                    candidate.update({
                        "tested": True,
                        "passed": False,
                        "error": str(e)
                    })
                    tested.append(candidate)
        
        return tested
    
    def _test_sequential(
        self,
        candidates: List[Dict[str, Any]],
        test_evaluator: Callable,
        test_cases: List[str]
    ) -> List[Dict[str, Any]]:
        """Test candidates sequentially."""
        tested = []
        
        for candidate in candidates:
            try:
                result = test_evaluator(candidate["code"], test_cases)
                candidate.update({
                    "tested": True,
                    "passed": result.get("passed", False),
                    "error": result.get("error"),
                    "execution_time": result.get("execution_time"),
                    "test_results": result
                })
            except Exception as e:
                candidate.update({
                    "tested": True,
                    "passed": False,
                    "error": str(e)
                })
            
            tested.append(candidate)
        
        return tested
    
    def _select_best(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select best candidate from tested candidates."""
        if not candidates:
            return {}
        
        # Prioritize: passed > execution_time > candidate_id
        passed_candidates = [c for c in candidates if c.get("passed", False)]
        
        if passed_candidates:
            # Select fastest among passed
            best = min(passed_candidates, key=lambda x: x.get("execution_time", float('inf')))
            return best
        else:
            # Select candidate with least errors
            best = min(candidates, key=lambda x: len(str(x.get("error", ""))))
            return best


def get_multi_candidate_generator(
    num_candidates: int = 8,
    temperature_range: tuple = (0.2, 0.8),
    parallel_testing: bool = True
) -> MultiCandidateGenerator:
    """Get multi-candidate generator instance."""
    return MultiCandidateGenerator(
        num_candidates=num_candidates,
        temperature_range=temperature_range,
        parallel_testing=parallel_testing
    )
