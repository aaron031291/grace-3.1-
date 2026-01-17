#!/usr/bin/env python3
"""
Test BigCodeBench Baseline - Current Performance

Runs a sample of BigCodeBench tasks to see where Grace currently stands.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from datetime import datetime
from typing import Dict, Any, List


async def test_baseline():
    """Test Grace's current baseline performance on BigCodeBench."""
    print("=" * 80)
    print("BIGCODEBENCH BASELINE TEST")
    print("=" * 80)
    print()
    print("Testing Grace's current performance on BigCodeBench")
    print("This will show where we stand before continuous training")
    print()
    
    # Initialize BigCodeBench
    print("Initializing BigCodeBench...")
    try:
        from backend.benchmarking.bigcodebench_integration import get_bigcodebench_integration
        
        bcb = get_bigcodebench_integration(install_if_missing=True)
        
        if not bcb.bigcodebench_available:
            print("ERROR: BigCodeBench not available. Installing...")
            if not bcb._install_bigcodebench():
                print("ERROR: Could not install BigCodeBench")
                return
            bcb.bigcodebench_available = bcb._check_bigcodebench()
        
        print("✓ BigCodeBench initialized")
    except Exception as e:
        print(f"ERROR: Could not initialize BigCodeBench: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Get sample tasks
    print()
    print("Getting sample tasks...")
    try:
        sample_tasks = bcb.get_task_sample(
            variant="complete",
            num_tasks=10  # Test with 10 tasks first
        )
        
        if not sample_tasks:
            print("WARNING: No tasks available. Trying to install BigCodeBench...")
            return
        
        print(f"✓ Got {len(sample_tasks)} sample tasks")
        print()
    except Exception as e:
        print(f"ERROR: Could not get tasks: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Initialize Grace Coding Agent
    print("Initializing Grace Coding Agent...")
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
        
        print("✓ Grace Coding Agent initialized")
        print()
    except Exception as e:
        print(f"WARNING: Could not initialize Coding Agent: {e}")
        coding_agent = None
    
    # Test each task
    print("=" * 80)
    print("TESTING TASKS")
    print("=" * 80)
    print()
    
    results = {
        "total": len(sample_tasks),
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "task_results": []
    }
    
    for i, task in enumerate(sample_tasks, 1):
        task_id = task.task_id
        prompt = task.prompt[:100] + "..." if len(task.prompt) > 100 else task.prompt
        
        print(f"[{i}/{len(sample_tasks)}] Task: {task_id}")
        print(f"  Prompt: {prompt}")
        
        try:
            # Generate code
            if coding_agent:
                coding_task = coding_agent.create_task(
                    task_type="code_generation",
                    description=task.prompt,
                    context={
                        "bigcodebench_task_id": task_id,
                        "variant": "complete"
                    }
                )
                
                execution_result = coding_agent.execute_task(coding_task.task_id)
                
                if execution_result.get("success"):
                    generation = execution_result.get("result", {}).get("generation")
                    if generation:
                        generated_code = generation.code_after if hasattr(generation, 'code_after') else str(generation)
                        
                        # Evaluate with BigCodeBench
                        print("  Evaluating with BigCodeBench...")
                        passed = False
                        try:
                            import bigcodebench
                            from bigcodebench import BigCodeBench
                            
                            bcb_eval = BigCodeBench()
                            eval_result = bcb_eval.evaluate_task(
                                task_id=task_id,
                                generated_code=generated_code,
                                variant="complete"
                            )
                            
                            passed = eval_result.get("passed", False)
                            
                            if passed:
                                print("  ✓ PASSED")
                                results["passed"] += 1
                            else:
                                print("  ✗ FAILED")
                                results["failed"] += 1
                                if eval_result.get("error"):
                                    print(f"    Error: {eval_result['error']}")
                        except Exception as e:
                            print(f"  ⚠ Evaluation error: {e}")
                            results["errors"] += 1
                            passed = False
                        
                        results["task_results"].append({
                            "task_id": task_id,
                            "passed": passed,
                            "error": eval_result.get("error") if 'eval_result' in locals() else None
                        })
                    else:
                        print("  ✗ No code generated")
                        results["failed"] += 1
                else:
                    print("  ✗ Task execution failed")
                    results["failed"] += 1
            else:
                print("  ⚠ Coding agent not available")
                results["errors"] += 1
            
            print()
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results["errors"] += 1
            print()
    
    # Calculate success rate
    if results["total"] > 0:
        success_rate = (results["passed"] / results["total"]) * 100.0
    else:
        success_rate = 0.0
    
    # Display results
    print()
    print("=" * 80)
    print("BASELINE RESULTS")
    print("=" * 80)
    print()
    print(f"Total Tasks Tested: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Errors: {results['errors']}")
    print()
    print(f"Success Rate: {success_rate:.2f}%")
    print()
    
    # Compare with leaderboard
    print("=" * 80)
    print("LEADERBOARD COMPARISON")
    print("=" * 80)
    print()
    print("Current Leaderboard (BigCodeBench-Complete):")
    print("  GPT-4o: 61.1%")
    print("  DeepSeek-Coder-V2: 59.7%")
    print("  Claude-3.5-Sonnet: 58.6%")
    print("  Human Expert: ~97%")
    print()
    print(f"Grace Current: {success_rate:.2f}%")
    print()
    
    if success_rate > 0:
        gap_to_gpt4o = 61.1 - success_rate
        gap_to_human = 97.0 - success_rate
        
        print(f"Gap to GPT-4o: {gap_to_gpt4o:+.2f}%")
        print(f"Gap to Human: {gap_to_human:+.2f}%")
        print()
        
        if success_rate >= 98.0:
            print("🎉 TARGET ACHIEVED! Grace is at 98%+ accuracy!")
        else:
            remaining = 98.0 - success_rate
            print(f"Remaining to 98% target: {remaining:.2f}%")
            print()
            print("Training will continue until 98% is reached.")
    
    print()
    print("=" * 80)
    print("Note: This is a baseline test with 10 tasks.")
    print("Full training will use all 1,140 tasks.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_baseline())
