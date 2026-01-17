"""
BigCodeBench Integration

Integrates BigCodeBench benchmark for comprehensive code generation evaluation.
BigCodeBench: 1,140 Python tasks across 7 domains, 139 libraries.

Resources:
- GitHub: https://github.com/bigcode-project/bigcodebench
- PyPI: bigcodebench
- Leaderboard: https://bigcode-bench.github.io/
"""

import logging
import subprocess
import sys
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class BigCodeBenchVariant(str, Enum):
    """BigCodeBench evaluation variants."""
    COMPLETE = "complete"  # Tasks with detailed docstrings
    INSTRUCT = "instruct"  # Natural language instructions
    HARD = "hard"  # Hard subset (~150 tasks)


@dataclass
class BigCodeBenchTask:
    """A BigCodeBench task."""
    task_id: str
    variant: BigCodeBenchVariant
    prompt: str
    docstring: Optional[str] = None
    test_cases: List[Dict[str, Any]] = None
    domain: Optional[str] = None
    libraries: List[str] = None


@dataclass
class BigCodeBenchResult:
    """Result from BigCodeBench evaluation."""
    variant: BigCodeBenchVariant
    total_tasks: int
    pass_at_1: float  # Percentage passing on first try
    pass_at_5: Optional[float] = None  # Percentage passing in 5 tries
    calibrated_pass_at_1: Optional[float] = None  # Calibrated score
    task_results: List[Dict[str, Any]] = None
    execution_time_seconds: float = 0.0


class BigCodeBenchIntegration:
    """
    Integrate BigCodeBench for comprehensive evaluation.
    
    BigCodeBench provides:
    - 1,140 Python function-level tasks
    - 7 domains (data science, web, etc.)
    - 139 distinct Python libraries
    - High test coverage (~99% branch coverage)
    - Realistic software engineering challenges
    """
    
    def __init__(self, install_if_missing: bool = True):
        """Initialize BigCodeBench integration."""
        self.install_if_missing = install_if_missing
        self.bigcodebench_available = self._check_bigcodebench()
        
        if not self.bigcodebench_available and install_if_missing:
            logger.info("[BIGCODEBENCH] Installing bigcodebench...")
            self._install_bigcodebench()
            self.bigcodebench_available = self._check_bigcodebench()
        
        if self.bigcodebench_available:
            logger.info("[BIGCODEBENCH] BigCodeBench available")
        else:
            logger.warning("[BIGCODEBENCH] BigCodeBench not available")
    
    def _check_bigcodebench(self) -> bool:
        """Check if bigcodebench is installed."""
        try:
            import bigcodebench
            return True
        except ImportError:
            return False
    
    def _install_bigcodebench(self) -> bool:
        """Install bigcodebench package."""
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "bigcodebench"
            ])
            return True
        except Exception as e:
            logger.error(f"[BIGCODEBENCH] Installation failed: {e}")
            return False
    
    def evaluate_model(
        self,
        model_name: str,
        variant: BigCodeBenchVariant = BigCodeBenchVariant.COMPLETE,
        generate_function: Optional[callable] = None,
        output_dir: Optional[Path] = None
    ) -> Optional[BigCodeBenchResult]:
        """
        Evaluate a model on BigCodeBench.
        
        Args:
            model_name: Name of the model/system
            variant: Which BigCodeBench variant to use
            generate_function: Function that takes prompt and returns code
            output_dir: Directory to save results
        
        Returns:
            BigCodeBenchResult with scores
        """
        if not self.bigcodebench_available:
            logger.error("[BIGCODEBENCH] BigCodeBench not available")
            return None
        
        try:
            import bigcodebench
            from bigcodebench import BigCodeBench
            
            # Initialize BigCodeBench
            bcb = BigCodeBench()
            
            # Get tasks for variant
            if variant == BigCodeBenchVariant.COMPLETE:
                tasks = bcb.get_tasks(split="complete")
            elif variant == BigCodeBenchVariant.INSTRUCT:
                tasks = bcb.get_tasks(split="instruct")
            elif variant == BigCodeBenchVariant.HARD:
                tasks = bcb.get_tasks(split="hard")
            else:
                tasks = bcb.get_tasks()
            
            logger.info(f"[BIGCODEBENCH] Evaluating {model_name} on {len(tasks)} tasks ({variant.value})")
            
            # Evaluate each task
            results = []
            passed = 0
            
            for i, task in enumerate(tasks):
                if i % 100 == 0:
                    logger.info(f"[BIGCODEBENCH] Progress: {i}/{len(tasks)}")
                
                # Generate code
                if generate_function:
                    prompt = task.get("prompt") or task.get("instruction", "")
                    generated_code = generate_function(prompt)
                else:
                    # Use default generation (would need model integration)
                    generated_code = ""
                
                # Evaluate
                try:
                    # BigCodeBench evaluation
                    result = bcb.evaluate_task(
                        task_id=task.get("task_id"),
                        generated_code=generated_code,
                        variant=variant.value
                    )
                    
                    if result.get("passed", False):
                        passed += 1
                    
                    results.append({
                        "task_id": task.get("task_id"),
                        "passed": result.get("passed", False),
                        "error": result.get("error"),
                        "test_results": result.get("test_results")
                    })
                except Exception as e:
                    logger.warning(f"[BIGCODEBENCH] Task {task.get('task_id')} evaluation error: {e}")
                    results.append({
                        "task_id": task.get("task_id"),
                        "passed": False,
                        "error": str(e)
                    })
            
            # Calculate scores
            pass_at_1 = (passed / len(tasks)) * 100.0 if tasks else 0.0
            
            # Calibrated score (accounts for missing imports, etc.)
            calibrated_passed = sum(1 for r in results if r.get("passed") and not r.get("error"))
            calibrated_pass_at_1 = (calibrated_passed / len(tasks)) * 100.0 if tasks else 0.0
            
            result = BigCodeBenchResult(
                variant=variant,
                total_tasks=len(tasks),
                pass_at_1=pass_at_1,
                calibrated_pass_at_1=calibrated_pass_at_1,
                task_results=results
            )
            
            # Save results
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                result_file = output_dir / f"{model_name}_{variant.value}_results.json"
                import json
                result_file.write_text(json.dumps({
                    "model_name": model_name,
                    "variant": variant.value,
                    "pass_at_1": pass_at_1,
                    "calibrated_pass_at_1": calibrated_pass_at_1,
                    "total_tasks": len(tasks),
                    "task_results": results
                }, indent=2))
                logger.info(f"[BIGCODEBENCH] Results saved to {result_file}")
            
            return result
            
        except Exception as e:
            logger.error(f"[BIGCODEBENCH] Evaluation error: {e}")
            return None
    
    def compare_with_leaderboard(
        self,
        model_result: BigCodeBenchResult
    ) -> Dict[str, Any]:
        """
        Compare model results with BigCodeBench leaderboard.
        
        Leaderboard reference (as of 2024):
        - GPT-4o: ~61.1% (Complete), ~51.1% (Instruct)
        - DeepSeek-Coder-V2: ~59.7%
        - Claude-3.5-Sonnet: ~58.6%
        - Human experts: ~97%
        """
        leaderboard_scores = {
            "gpt-4o": {
                "complete": 61.1,
                "instruct": 51.1
            },
            "deepseek-coder-v2": {
                "complete": 59.7,
                "instruct": None
            },
            "claude-3.5-sonnet": {
                "complete": 58.6,
                "instruct": None
            },
            "human_expert": {
                "complete": 97.0,
                "instruct": 97.0
            }
        }
        
        variant_key = model_result.variant.value
        model_score = model_result.pass_at_1
        
        comparison = {
            "model_score": model_score,
            "variant": variant_key,
            "leaderboard_comparison": {}
        }
        
        for model_name, scores in leaderboard_scores.items():
            if variant_key in scores and scores[variant_key]:
                leaderboard_score = scores[variant_key]
                comparison["leaderboard_comparison"][model_name] = {
                    "leaderboard_score": leaderboard_score,
                    "difference": model_score - leaderboard_score,
                    "percentage_of_leaderboard": (model_score / leaderboard_score * 100) if leaderboard_score > 0 else 0
                }
        
        return comparison
    
    def get_task_sample(
        self,
        variant: BigCodeBenchVariant = BigCodeBenchVariant.COMPLETE,
        num_tasks: int = 5
    ) -> List[BigCodeBenchTask]:
        """Get a sample of BigCodeBench tasks for testing."""
        if not self.bigcodebench_available:
            return []
        
        try:
            import bigcodebench
            from bigcodebench import BigCodeBench
            
            bcb = BigCodeBench()
            
            if variant == BigCodeBenchVariant.COMPLETE:
                tasks = bcb.get_tasks(split="complete")
            elif variant == BigCodeBenchVariant.INSTRUCT:
                tasks = bcb.get_tasks(split="instruct")
            elif variant == BigCodeBenchVariant.HARD:
                tasks = bcb.get_tasks(split="hard")
            else:
                tasks = bcb.get_tasks()
            
            sample_tasks = []
            for task in tasks[:num_tasks]:
                sample_tasks.append(BigCodeBenchTask(
                    task_id=task.get("task_id", ""),
                    variant=variant,
                    prompt=task.get("prompt") or task.get("instruction", ""),
                    docstring=task.get("docstring"),
                    test_cases=task.get("test_cases", []),
                    domain=task.get("domain"),
                    libraries=task.get("libraries", [])
                ))
            
            return sample_tasks
            
        except Exception as e:
            logger.error(f"[BIGCODEBENCH] Error getting task sample: {e}")
            return []


def get_bigcodebench_integration(
    install_if_missing: bool = True
) -> BigCodeBenchIntegration:
    """Factory function to get BigCodeBench integration."""
    return BigCodeBenchIntegration(install_if_missing=install_if_missing)
