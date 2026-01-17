#!/usr/bin/env python3
"""
Run BigCodeBench Evaluation for Grace

Evaluates Grace (Coding Agent) on BigCodeBench and compares with leaderboard.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.benchmarking.bigcodebench_integration import (
    get_bigcodebench_integration,
    BigCodeBenchVariant
)


def grace_code_generator(prompt: str) -> str:
    """
    Generate code using Grace Coding Agent.
    
    This function will be called for each BigCodeBench task.
    """
    try:
        from backend.database.session import get_session
        from cognitive.enterprise_coding_agent import get_enterprise_coding_agent
        from cognitive.autonomous_healing_system import TrustLevel
        
        session = next(get_session())
        coding_agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True,
            enable_sandbox=True
        )
        
        # Create task
        task = coding_agent.create_task(
            task_type="code_generation",
            description=prompt
        )
        
        # Execute
        result = coding_agent.execute_task(task.task_id)
        
        if result.get("success"):
            generation = result.get("result", {}).get("generation")
            if generation:
                return generation.code_after if hasattr(generation, 'code_after') else str(generation)
        
        return ""
    except Exception as e:
        print(f"Error generating code: {e}")
        return ""


async def run_evaluation():
    """Run BigCodeBench evaluation."""
    print("=" * 80)
    print("BIGCODEBENCH EVALUATION - GRACE")
    print("=" * 80)
    print()
    print("BigCodeBench: 1,140 Python tasks across 7 domains, 139 libraries")
    print("Leaderboard: https://bigcode-bench.github.io/")
    print()
    
    # Initialize BigCodeBench
    print("Initializing BigCodeBench...")
    bcb = get_bigcodebench_integration(install_if_missing=True)
    
    if not bcb.bigcodebench_available:
        print("ERROR: BigCodeBench not available. Install with: pip install bigcodebench")
        return
    
    print("✓ BigCodeBench initialized")
    print()
    
    # Test with sample first
    print("Getting sample tasks...")
    sample_tasks = bcb.get_task_sample(
        variant=BigCodeBenchVariant.COMPLETE,
        num_tasks=3
    )
    
    if sample_tasks:
        print(f"✓ Got {len(sample_tasks)} sample tasks")
        print("\nSample task:")
        print(f"  ID: {sample_tasks[0].task_id}")
        print(f"  Prompt: {sample_tasks[0].prompt[:200]}...")
        print()
    
    # Run evaluation
    print("Running evaluation on BigCodeBench-Complete...")
    print("(This may take a while - 1,140 tasks)")
    print()
    
    result = bcb.evaluate_model(
        model_name="grace_coding_agent",
        variant=BigCodeBenchVariant.COMPLETE,
        generate_function=grace_code_generator,
        output_dir=Path("bigcodebench_results")
    )
    
    if result:
        print()
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()
        print(f"Variant: {result.variant.value}")
        print(f"Total Tasks: {result.total_tasks}")
        print(f"Pass@1: {result.pass_at_1:.2f}%")
        if result.calibrated_pass_at_1:
            print(f"Calibrated Pass@1: {result.calibrated_pass_at_1:.2f}%")
        print()
        
        # Compare with leaderboard
        print("LEADERBOARD COMPARISON")
        print("-" * 80)
        comparison = bcb.compare_with_leaderboard(result)
        
        print(f"Grace Score: {comparison['model_score']:.2f}%")
        print()
        print("vs. Leaderboard:")
        for model_name, comp_data in comparison.get("leaderboard_comparison", {}).items():
            print(f"  {model_name}:")
            print(f"    Leaderboard: {comp_data['leaderboard_score']:.2f}%")
            print(f"    Difference: {comp_data['difference']:+.2f}%")
            print(f"    Grace is {comp_data['percentage_of_leaderboard']:.1f}% of {model_name}")
        print()
        
        # Human baseline
        print("Human Expert Baseline: ~97%")
        human_gap = 97.0 - result.pass_at_1
        print(f"Gap to Human: {human_gap:.2f}%")
        print()
        
        print("=" * 80)
        print("Results saved to: bigcodebench_results/")
        print("=" * 80)
    else:
        print("ERROR: Evaluation failed")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
