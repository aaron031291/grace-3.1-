"""
Unified Benchmark Harness for Grace

Provides a unified interface for running multiple benchmarks:
- BigCodeBench
- HumanEval
- MBPP
- Mercury
- COMPASS
- SWE-Bench
- CoderEval
- DS-1000
- LiveCodeBench
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path


class BenchmarkHarness:
    """Unified harness for running multiple benchmarks."""
    
    def __init__(self, coding_agent=None):
        """
        Initialize benchmark harness.
        
        Args:
            coding_agent: Grace's EnterpriseCodingAgent instance
        """
        self.coding_agent = coding_agent
        self.benchmarks = {}
        
    def register_benchmark(self, name: str, benchmark_instance):
        """Register a benchmark instance."""
        self.benchmarks[name] = benchmark_instance
    
    def run_benchmark(
        self,
        benchmark_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run a specific benchmark.
        
        Args:
            benchmark_name: Name of benchmark to run
            **kwargs: Additional arguments for benchmark
            
        Returns:
            Dictionary with benchmark results
        """
        if benchmark_name not in self.benchmarks:
            return {
                "error": f"Benchmark '{benchmark_name}' not found",
                "available": list(self.benchmarks.keys())
            }
        
        benchmark = self.benchmarks[benchmark_name]
        
        # Run benchmark
        start_time = datetime.now()
        try:
            if hasattr(benchmark, 'run_evaluation'):
                results = benchmark.run_evaluation(**kwargs)
            elif hasattr(benchmark, 'evaluate'):
                results = benchmark.evaluate(**kwargs)
            else:
                results = {"error": "Benchmark does not have run_evaluation or evaluate method"}
        except Exception as e:
            results = {
                "error": str(e),
                "benchmark": benchmark_name
            }
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        results["benchmark_name"] = benchmark_name
        results["duration_seconds"] = duration
        results["timestamp"] = datetime.now().isoformat()
        
        return results
    
    def run_all_benchmarks(
        self,
        benchmark_names: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run multiple benchmarks.
        
        Args:
            benchmark_names: List of benchmark names to run (None = all)
            **kwargs: Additional arguments for benchmarks
            
        Returns:
            Dictionary with results for all benchmarks
        """
        if benchmark_names is None:
            benchmark_names = list(self.benchmarks.keys())
        
        all_results = {
            "total_benchmarks": len(benchmark_names),
            "completed": 0,
            "failed": 0,
            "results": {},
            "summary": {}
        }
        
        for benchmark_name in benchmark_names:
            print(f"\n{'='*80}")
            print(f"Running benchmark: {benchmark_name}")
            print(f"{'='*80}\n")
            
            result = self.run_benchmark(benchmark_name, **kwargs)
            
            if "error" in result:
                all_results["failed"] += 1
                all_results["results"][benchmark_name] = result
            else:
                all_results["completed"] += 1
                all_results["results"][benchmark_name] = result
                
                # Extract summary
                if "pass_rate" in result:
                    all_results["summary"][benchmark_name] = {
                        "pass_rate": result["pass_rate"],
                        "passed": result.get("passed", 0),
                        "total": result.get("total", 0)
                    }
        
        return all_results
    
    def generate_report(
        self,
        results: Dict[str, Any],
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate a comparison report from benchmark results.
        
        Args:
            results: Results dictionary from run_all_benchmarks
            output_path: Optional path to save report
            
        Returns:
            Report string
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("GRACE BENCHMARK COMPARISON REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"Generated: {datetime.now().isoformat()}")
        report_lines.append("")
        
        # Summary
        report_lines.append("SUMMARY")
        report_lines.append("-" * 80)
        report_lines.append(f"Total Benchmarks: {results['total_benchmarks']}")
        report_lines.append(f"Completed: {results['completed']}")
        report_lines.append(f"Failed: {results['failed']}")
        report_lines.append("")
        
        # Individual Results
        report_lines.append("INDIVIDUAL RESULTS")
        report_lines.append("-" * 80)
        
        for benchmark_name, result in results["results"].items():
            if "error" in result:
                report_lines.append(f"{benchmark_name}: ERROR - {result['error']}")
            else:
                pass_rate = result.get("pass_rate", 0)
                passed = result.get("passed", 0)
                total = result.get("total", 0)
                duration = result.get("duration_seconds", 0)
                
                report_lines.append(f"{benchmark_name}:")
                report_lines.append(f"  Pass Rate: {pass_rate:.2f}%")
                report_lines.append(f"  Passed: {passed}/{total}")
                report_lines.append(f"  Duration: {duration:.2f}s")
            report_lines.append("")
        
        # Comparison Table
        if results["summary"]:
            report_lines.append("COMPARISON TABLE")
            report_lines.append("-" * 80)
            report_lines.append(f"{'Benchmark':<20} {'Pass Rate':<15} {'Passed/Total':<15}")
            report_lines.append("-" * 80)
            
            for benchmark_name, summary in results["summary"].items():
                pass_rate = summary["pass_rate"]
                passed = summary["passed"]
                total = summary["total"]
                report_lines.append(
                    f"{benchmark_name:<20} {pass_rate:>6.2f}%       {passed:>4}/{total:<4}"
                )
            report_lines.append("")
        
        report = "\n".join(report_lines)
        
        # Save if path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report)
            report_lines.append(f"Report saved to: {output_path}")
        
        return report


def get_benchmark_harness(coding_agent=None):
    """Factory function to get benchmark harness."""
    harness = BenchmarkHarness(coding_agent=coding_agent)
    
    # Register available benchmarks
    try:
        from backend.benchmarking.bigcodebench_integration import get_bigcodebench_training
        bigcodebench = get_bigcodebench_training()
        if bigcodebench:
            harness.register_benchmark("bigcodebench", bigcodebench)
    except:
        pass
    
    try:
        from backend.benchmarking.humaneval_integration import get_humaneval_integration
        humaneval = get_humaneval_integration(coding_agent=coding_agent)
        harness.register_benchmark("humaneval", humaneval)
    except:
        pass
    
    try:
        from backend.benchmarking.mbpp_integration import get_mbpp_integration
        mbpp = get_mbpp_integration(coding_agent=coding_agent)
        harness.register_benchmark("mbpp", mbpp)
    except:
        pass
    
    return harness
