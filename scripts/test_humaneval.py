#!/usr/bin/env python3
"""
HumanEval Test - Grace Coding Agent

Tests Grace's code generation on HumanEval benchmark.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from datetime import datetime


def test_humaneval(max_problems=None):
    """Test Grace on HumanEval benchmark."""
    print("=" * 80)
    print("HUMANEVAL BENCHMARK TEST - GRACE CODING AGENT")
    print("=" * 80)
    print()
    print("Testing Grace's code generation on HumanEval benchmark")
    print(f"(Evaluating {max_problems or 'all'} problems)")
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
    
    # Initialize HumanEval Integration
    print("Initializing HumanEval Integration...")
    try:
        from backend.benchmarking.humaneval_integration import get_humaneval_integration
        
        humaneval = get_humaneval_integration(coding_agent=coding_agent)
        
        print("[OK] HumanEval Integration initialized")
        print()
    except Exception as e:
        print(f"ERROR: Could not initialize HumanEval Integration: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Run evaluation
    print("=" * 80)
    print("RUNNING EVALUATION")
    print("=" * 80)
    print()
    
    start_time = datetime.now()
    results = humaneval.run_evaluation(max_problems=max_problems, timeout=10)
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Display results
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    print(f"Total Problems: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Pass Rate: {results['pass_rate']:.2f}%")
    print(f"Duration: {duration:.2f} seconds")
    print()
    
    # Compare to leaderboard
    print("=" * 80)
    print("LEADERBOARD COMPARISON")
    print("=" * 80)
    print()
    
    comparison = humaneval.compare_to_leaderboard(results['pass_rate'])
    
    print(f"Grace Pass Rate: {comparison['grace_pass_rate']:.2f}%")
    print()
    print("HumanEval Leaderboard:")
    for model, rate in comparison['leaderboard'].items():
        gap = comparison['grace_pass_rate'] - rate
        symbol = "+" if gap >= 0 else ""
        print(f"  {model}: {rate:.1f}% ({symbol}{gap:.1f}%)")
    print()
    print(f"Rank: {comparison['rank']}")
    print(f"Gap to Top: {comparison['gap_to_top']:.1f}%")
    print()
    
    # Show sample failures
    if results['failed'] > 0:
        print("=" * 80)
        print("SAMPLE FAILURES")
        print("=" * 80)
        print()
        
        failures = [r for r in results['results'] if not r['passed']]
        for i, failure in enumerate(failures[:5], 1):  # Show first 5 failures
            print(f"{i}. {failure['task_id']}")
            if failure.get('error'):
                print(f"   Error: {failure['error'][:100]}")
            print()
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Grace on HumanEval benchmark")
    parser.add_argument(
        "--max-problems",
        type=int,
        default=None,
        help="Maximum number of problems to evaluate (default: all)"
    )
    
    args = parser.parse_args()
    
    test_humaneval(max_problems=args.max_problems)
