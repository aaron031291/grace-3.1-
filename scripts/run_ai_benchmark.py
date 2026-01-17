#!/usr/bin/env python3
"""
Run AI Comparison Benchmark

Tests Grace (Coding Agent & Self-Healing) against:
- Claude
- Gemini
- Cursor
- ChatGPT
- DeepSeek
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.benchmarking.ai_comparison_benchmark import (
    get_ai_comparison_benchmark,
    BenchmarkTask,
    AIProvider
)


def create_benchmark_tasks() -> list:
    """Create benchmark tasks."""
    tasks = []
    
    # Task 1: Code Generation
    tasks.append(BenchmarkTask(
        task_id="code_gen_1",
        task_type="code_generation",
        prompt="Create a Python function that calculates the factorial of a number using recursion, with proper error handling and type hints.",
        context={},
        expected_output="def factorial"
    ))
    
    # Task 2: Code Fix
    tasks.append(BenchmarkTask(
        task_id="code_fix_1",
        task_type="code_fix",
        prompt="Fix this broken code: def divide(a, b): return a / b",
        context={
            "broken_code": "def divide(a, b):\n    return a / b"
        },
        expected_output="try:"
    ))
    
    # Task 3: Code Review
    tasks.append(BenchmarkTask(
        task_id="code_review_1",
        task_type="code_review",
        prompt="Review this code and suggest improvements: def process_data(data): result = []\nfor item in data:\n    result.append(item * 2)\nreturn result",
        context={},
        expected_output="list comprehension"
    ))
    
    return tasks


async def run_benchmark():
    """Run the benchmark."""
    print("=" * 80)
    print("AI COMPARISON BENCHMARK")
    print("=" * 80)
    print()
    print("Testing Grace against:")
    print("  - Claude")
    print("  - Gemini")
    print("  - Cursor")
    print("  - ChatGPT")
    print("  - DeepSeek")
    print()
    
    # Initialize systems
    print("Initializing Grace systems...")
    
    try:
        from backend.database.session import get_session
        from cognitive.enterprise_coding_agent import get_enterprise_coding_agent
        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
        from pathlib import Path
        
        session = next(get_session())
        
        # Get coding agent
        coding_agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True,
            enable_sandbox=True
        )
        
        # Get self-healing
        self_healing = get_autonomous_healing(
            session=session,
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True
        )
        
        print("✓ Grace systems initialized")
    except Exception as e:
        print(f"WARNING: Could not initialize Grace systems: {e}")
        coding_agent = None
        self_healing = None
    
    # Create benchmark
    benchmark = get_ai_comparison_benchmark(
        session=session if 'session' in locals() else None,
        coding_agent=coding_agent,
        self_healing=self_healing,
        enable_claude=True,
        enable_gemini=True,
        enable_cursor=True,
        enable_chatgpt=True,
        enable_deepseek=True
    )
    
    # Create tasks
    tasks = create_benchmark_tasks()
    print(f"Created {len(tasks)} benchmark tasks")
    print()
    
    # Run benchmarks
    print("Running benchmarks...")
    print()
    
    for i, task in enumerate(tasks, 1):
        print(f"[{i}/{len(tasks)}] Running: {task.task_id}")
        result = await benchmark.run_benchmark(task)
        
        # Show quick results
        if result.rankings and "overall" in result.rankings:
            print(f"  Top performer: {result.rankings['overall'][0].value}")
            if result.summary:
                print(f"  Best score: {result.summary.get('best_performer', {}).get('score', 0):.3f}")
        print()
    
    # Generate report
    print("Generating report...")
    report = benchmark.generate_report(
        output_path=Path("ai_benchmark_report.txt")
    )
    
    print()
    print("=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)
    print()
    print("Report saved to: ai_benchmark_report.txt")
    print()
    print(report[:2000])  # Show first 2000 chars
    if len(report) > 2000:
        print("\n... (see full report in ai_benchmark_report.txt)")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
