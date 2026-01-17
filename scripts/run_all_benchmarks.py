#!/usr/bin/env python3
"""
Run All Benchmarks - Grace Coding Agent

Runs multiple benchmarks and generates a comparison report.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from datetime import datetime


def run_all_benchmarks(benchmark_names=None, max_problems=None):
    """Run all available benchmarks."""
    print("=" * 80)
    print("GRACE BENCHMARK SUITE")
    print("=" * 80)
    print()
    print("Running multiple benchmarks for comprehensive evaluation")
    print()
    
    # Initialize database
    print("Initializing database...")
    try:
        from backend.database.connection import DatabaseConnection, DatabaseConfig, DatabaseType
        
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database="grace",
            database_path=str(project_root / "data" / "grace.db"),
            echo=False,
        )
        DatabaseConnection.initialize(db_config)
        
        from backend.database.session import initialize_session_factory
        initialize_session_factory()
        
        print("[OK] Database initialized")
    except Exception as e:
        print(f"ERROR: Database initialization: {e}")
        return
    
    # Initialize Coding Agent
    print("Initializing Coding Agent...")
    try:
        from backend.database.session import get_session
        from backend.cognitive.enterprise_coding_agent import get_enterprise_coding_agent
        from backend.cognitive.autonomous_healing_system import TrustLevel
        
        session = next(get_session())
        coding_agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True,
            enable_sandbox=True
        )
        
        print("[OK] Coding Agent initialized")
        print()
    except Exception as e:
        print(f"ERROR: Could not initialize Coding Agent: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Initialize Benchmark Harness
    print("Initializing Benchmark Harness...")
    try:
        from backend.benchmarking.benchmark_harness import get_benchmark_harness
        
        harness = get_benchmark_harness(coding_agent=coding_agent)
        
        print(f"[OK] Benchmark Harness initialized")
        print(f"Available benchmarks: {list(harness.benchmarks.keys())}")
        print()
    except Exception as e:
        print(f"ERROR: Could not initialize Benchmark Harness: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Run benchmarks
    print("=" * 80)
    print("RUNNING BENCHMARKS")
    print("=" * 80)
    print()
    
    start_time = datetime.now()
    
    kwargs = {}
    if max_problems:
        kwargs["max_problems"] = max_problems
    
    results = harness.run_all_benchmarks(
        benchmark_names=benchmark_names,
        **kwargs
    )
    
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    # Generate report
    print()
    print("=" * 80)
    print("GENERATING REPORT")
    print("=" * 80)
    print()
    
    report_path = project_root / "data" / "benchmark_report.txt"
    report = harness.generate_report(results, output_path=report_path)
    
    print(report)
    print()
    print(f"Total Duration: {total_duration:.2f} seconds")
    print(f"Report saved to: {report_path}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run all benchmarks for Grace")
    parser.add_argument(
        "--benchmarks",
        nargs="+",
        default=None,
        help="Specific benchmarks to run (default: all)"
    )
    parser.add_argument(
        "--max-problems",
        type=int,
        default=None,
        help="Maximum number of problems per benchmark (default: all)"
    )
    
    args = parser.parse_args()
    
    run_all_benchmarks(
        benchmark_names=args.benchmarks,
        max_problems=args.max_problems
    )
