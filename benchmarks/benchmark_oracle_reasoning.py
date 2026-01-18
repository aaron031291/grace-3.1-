"""
Benchmark Grace against Oracle Knowledge Base

Tests Grace on:
- GSM8K (grade school math)
- MATH (competition math)
- ARC (science reasoning)
- HumanEval (code generation)
- HellaSwag (commonsense)

Usage:
    # First download datasets
    python scripts/download_reasoning_datasets.py --benchmarks
    
    # Then run benchmarks
    python benchmarks/benchmark_oracle_reasoning.py --benchmark gsm8k
    python benchmarks/benchmark_oracle_reasoning.py --all
"""

import json
import logging
import time
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    benchmark_name: str
    total_problems: int
    correct: int
    accuracy: float
    avg_time_ms: float
    problems_results: List[Dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class OracleBenchmarkRunner:
    """Run benchmarks using Oracle knowledge base."""
    
    def __init__(self, oracle_path: str = "./data/oracle_knowledge"):
        self.oracle_path = Path(oracle_path)
        self.benchmark_path = self.oracle_path / "benchmarks"
        self.results_path = Path("./reports/benchmark_results")
        self.results_path.mkdir(parents=True, exist_ok=True)
    
    def load_benchmark(self, name: str) -> Dict[str, Any]:
        """Load a benchmark dataset."""
        
        path = self.benchmark_path / f"{name}_benchmark.json"
        if not path.exists():
            raise FileNotFoundError(
                f"Benchmark not found: {name}\n"
                f"Run: python scripts/download_reasoning_datasets.py --benchmarks"
            )
        
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def list_benchmarks(self) -> List[str]:
        """List available benchmarks."""
        
        if not self.benchmark_path.exists():
            return []
        
        return [p.stem.replace("_benchmark", "") 
                for p in self.benchmark_path.glob("*_benchmark.json")]
    
    def run_gsm8k(self, model_fn: Callable[[str], str], max_problems: int = 100) -> BenchmarkResult:
        """Run GSM8K benchmark (grade school math)."""
        
        data = self.load_benchmark("gsm8k")
        problems = data["problems"][:max_problems]
        
        correct = 0
        total_time = 0
        results = []
        
        for i, problem in enumerate(problems):
            question = problem.get("question", "")
            answer = problem.get("answer", "")
            
            # Extract final numeric answer from GSM8K format
            # GSM8K answers are like "#### 42"
            expected = self._extract_gsm8k_answer(answer)
            
            start = time.time()
            try:
                response = model_fn(question)
                predicted = self._extract_number(response)
            except Exception as e:
                response = str(e)
                predicted = None
            elapsed = (time.time() - start) * 1000
            total_time += elapsed
            
            is_correct = predicted is not None and abs(predicted - expected) < 0.01
            if is_correct:
                correct += 1
            
            results.append({
                "id": i,
                "question": question[:100] + "...",
                "expected": expected,
                "predicted": predicted,
                "correct": is_correct,
                "time_ms": elapsed,
            })
            
            if (i + 1) % 10 == 0:
                logger.info(f"GSM8K: {i+1}/{len(problems)} | Accuracy: {correct/(i+1)*100:.1f}%")
        
        return BenchmarkResult(
            benchmark_name="gsm8k",
            total_problems=len(problems),
            correct=correct,
            accuracy=correct / len(problems) * 100,
            avg_time_ms=total_time / len(problems),
            problems_results=results,
        )
    
    def run_math(self, model_fn: Callable[[str], str], max_problems: int = 100) -> BenchmarkResult:
        """Run MATH benchmark (competition math)."""
        
        data = self.load_benchmark("math")
        problems = data["problems"][:max_problems]
        
        correct = 0
        total_time = 0
        results = []
        
        for i, problem in enumerate(problems):
            question = problem.get("problem", "")
            expected = problem.get("solution", "")
            
            start = time.time()
            try:
                response = model_fn(question)
            except Exception as e:
                response = str(e)
            elapsed = (time.time() - start) * 1000
            total_time += elapsed
            
            # For MATH, use fuzzy matching on final answer
            is_correct = self._check_math_answer(response, expected)
            if is_correct:
                correct += 1
            
            results.append({
                "id": i,
                "question": question[:100] + "...",
                "correct": is_correct,
                "time_ms": elapsed,
            })
            
            if (i + 1) % 10 == 0:
                logger.info(f"MATH: {i+1}/{len(problems)} | Accuracy: {correct/(i+1)*100:.1f}%")
        
        return BenchmarkResult(
            benchmark_name="math",
            total_problems=len(problems),
            correct=correct,
            accuracy=correct / len(problems) * 100,
            avg_time_ms=total_time / len(problems),
            problems_results=results,
        )
    
    def run_arc(self, model_fn: Callable[[str], str], max_problems: int = 100) -> BenchmarkResult:
        """Run ARC benchmark (science reasoning)."""
        
        data = self.load_benchmark("arc")
        problems = data["problems"][:max_problems]
        
        correct = 0
        total_time = 0
        results = []
        
        for i, problem in enumerate(problems):
            question = problem.get("question", "")
            choices = problem.get("choices", {})
            answer_key = problem.get("answerKey", "")
            
            # Format as multiple choice
            choice_text = choices.get("text", [])
            choice_labels = choices.get("label", [])
            
            formatted_q = question + "\n"
            for label, text in zip(choice_labels, choice_text):
                formatted_q += f"{label}. {text}\n"
            formatted_q += "\nAnswer with just the letter."
            
            start = time.time()
            try:
                response = model_fn(formatted_q)
                predicted = self._extract_letter(response)
            except Exception as e:
                response = str(e)
                predicted = None
            elapsed = (time.time() - start) * 1000
            total_time += elapsed
            
            is_correct = predicted == answer_key
            if is_correct:
                correct += 1
            
            results.append({
                "id": i,
                "question": question[:100] + "...",
                "expected": answer_key,
                "predicted": predicted,
                "correct": is_correct,
                "time_ms": elapsed,
            })
            
            if (i + 1) % 10 == 0:
                logger.info(f"ARC: {i+1}/{len(problems)} | Accuracy: {correct/(i+1)*100:.1f}%")
        
        return BenchmarkResult(
            benchmark_name="arc",
            total_problems=len(problems),
            correct=correct,
            accuracy=correct / len(problems) * 100,
            avg_time_ms=total_time / len(problems),
            problems_results=results,
        )
    
    def run_humaneval(self, model_fn: Callable[[str], str], max_problems: int = 50) -> BenchmarkResult:
        """Run HumanEval benchmark (code generation)."""
        
        data = self.load_benchmark("humaneval")
        problems = data["problems"][:max_problems]
        
        correct = 0
        total_time = 0
        results = []
        
        for i, problem in enumerate(problems):
            prompt = problem.get("prompt", "")
            test = problem.get("test", "")
            entry_point = problem.get("entry_point", "")
            
            start = time.time()
            try:
                response = model_fn(prompt)
                # Try to execute the generated code
                is_correct = self._check_code(response, test, entry_point)
            except Exception as e:
                is_correct = False
            elapsed = (time.time() - start) * 1000
            total_time += elapsed
            
            if is_correct:
                correct += 1
            
            results.append({
                "id": i,
                "task_id": problem.get("task_id", ""),
                "correct": is_correct,
                "time_ms": elapsed,
            })
            
            if (i + 1) % 10 == 0:
                logger.info(f"HumanEval: {i+1}/{len(problems)} | Pass@1: {correct/(i+1)*100:.1f}%")
        
        return BenchmarkResult(
            benchmark_name="humaneval",
            total_problems=len(problems),
            correct=correct,
            accuracy=correct / len(problems) * 100,
            avg_time_ms=total_time / len(problems),
            problems_results=results,
        )
    
    def run_all(self, model_fn: Callable[[str], str], max_per_benchmark: int = 50) -> Dict[str, BenchmarkResult]:
        """Run all available benchmarks."""
        
        results = {}
        
        available = self.list_benchmarks()
        logger.info(f"Available benchmarks: {available}")
        
        benchmark_runners = {
            "gsm8k": self.run_gsm8k,
            "math": self.run_math,
            "arc": self.run_arc,
            "humaneval": self.run_humaneval,
        }
        
        for name in available:
            if name in benchmark_runners:
                logger.info(f"\n{'='*60}")
                logger.info(f"Running {name.upper()} benchmark")
                logger.info(f"{'='*60}")
                
                try:
                    result = benchmark_runners[name](model_fn, max_per_benchmark)
                    results[name] = result
                    self._save_result(result)
                except Exception as e:
                    logger.error(f"Failed to run {name}: {e}")
        
        # Print summary
        self._print_summary(results)
        
        return results
    
    def _extract_gsm8k_answer(self, answer: str) -> float:
        """Extract numeric answer from GSM8K format."""
        # GSM8K format: "...#### 42"
        match = re.search(r'####\s*(-?\d+\.?\d*)', answer)
        if match:
            return float(match.group(1).replace(',', ''))
        
        # Fallback: find last number
        numbers = re.findall(r'-?\d+\.?\d*', answer)
        if numbers:
            return float(numbers[-1].replace(',', ''))
        return 0.0
    
    def _extract_number(self, text: str) -> Optional[float]:
        """Extract a number from model response."""
        # Look for boxed answer first
        match = re.search(r'\\boxed\{([^}]+)\}', text)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except:
                pass
        
        # Look for "answer is X" pattern
        match = re.search(r'answer\s+is\s+(-?\d+\.?\d*)', text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', ''))
        
        # Find last number in text
        numbers = re.findall(r'-?\d+\.?\d*', text)
        if numbers:
            try:
                return float(numbers[-1].replace(',', ''))
            except:
                pass
        
        return None
    
    def _extract_letter(self, text: str) -> Optional[str]:
        """Extract answer letter (A, B, C, D) from response."""
        # Look for explicit answer
        match = re.search(r'\b([A-D])\b', text.upper())
        if match:
            return match.group(1)
        return None
    
    def _check_math_answer(self, response: str, expected: str) -> bool:
        """Check if math answer matches (fuzzy)."""
        # Extract final answer from expected solution
        resp_num = self._extract_number(response)
        exp_num = self._extract_number(expected)
        
        if resp_num is not None and exp_num is not None:
            return abs(resp_num - exp_num) < 0.01
        
        return False
    
    def _check_code(self, code: str, test: str, entry_point: str) -> bool:
        """Execute and check generated code."""
        try:
            # Create namespace and execute
            namespace = {}
            exec(code, namespace)
            exec(test, namespace)
            
            # Run check function if exists
            check_fn = namespace.get("check")
            if check_fn:
                check_fn(namespace[entry_point])
            
            return True
        except Exception:
            return False
    
    def _save_result(self, result: BenchmarkResult):
        """Save benchmark result to file."""
        
        filename = f"{result.benchmark_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = self.results_path / filename
        
        with open(path, "w") as f:
            json.dump({
                "benchmark_name": result.benchmark_name,
                "total_problems": result.total_problems,
                "correct": result.correct,
                "accuracy": result.accuracy,
                "avg_time_ms": result.avg_time_ms,
                "timestamp": result.timestamp,
            }, f, indent=2)
        
        logger.info(f"Result saved to {path}")
    
    def _print_summary(self, results: Dict[str, BenchmarkResult]):
        """Print summary of all benchmark results."""
        
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        
        for name, result in results.items():
            print(f"\n{name.upper()}")
            print(f"  Accuracy: {result.accuracy:.1f}%")
            print(f"  Correct: {result.correct}/{result.total_problems}")
            print(f"  Avg Time: {result.avg_time_ms:.1f}ms")
        
        print("\n" + "=" * 60)


def create_dummy_model():
    """Create a dummy model for testing the benchmark runner."""
    
    def dummy_model(prompt: str) -> str:
        # Just return a random number for testing
        import random
        return f"The answer is {random.randint(1, 100)}"
    
    return dummy_model


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Oracle benchmarks")
    parser.add_argument("--list", action="store_true", help="List available benchmarks")
    parser.add_argument("--benchmark", type=str, help="Run specific benchmark")
    parser.add_argument("--all", action="store_true", help="Run all benchmarks")
    parser.add_argument("--max", type=int, default=50, help="Max problems per benchmark")
    parser.add_argument("--test", action="store_true", help="Test with dummy model")
    
    args = parser.parse_args()
    
    runner = OracleBenchmarkRunner()
    
    if args.list:
        benchmarks = runner.list_benchmarks()
        if benchmarks:
            print("Available benchmarks:")
            for b in benchmarks:
                print(f"  - {b}")
        else:
            print("No benchmarks found. Run:")
            print("  python scripts/download_reasoning_datasets.py --benchmarks")
        return
    
    if args.test:
        model = create_dummy_model()
        logger.info("Using dummy model for testing")
    else:
        # TODO: Replace with actual Grace model
        logger.error("No model specified. Use --test for dummy model testing.")
        return
    
    if args.benchmark:
        benchmark_runners = {
            "gsm8k": runner.run_gsm8k,
            "math": runner.run_math,
            "arc": runner.run_arc,
            "humaneval": runner.run_humaneval,
        }
        
        if args.benchmark in benchmark_runners:
            result = benchmark_runners[args.benchmark](model, args.max)
            print(f"\nResult: {result.accuracy:.1f}% accuracy")
        else:
            print(f"Unknown benchmark: {args.benchmark}")
    elif args.all:
        runner.run_all(model, args.max)


if __name__ == "__main__":
    main()
