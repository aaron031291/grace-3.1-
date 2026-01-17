#!/usr/bin/env python3
"""
Test Grace Code Generation - Current Performance

Tests Grace's code generation capabilities on sample tasks
to see current baseline performance.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from datetime import datetime
from typing import Dict, Any, List


def test_code_generation():
    """Test Grace's code generation on sample tasks."""
    print("=" * 80)
    print("GRACE CODE GENERATION BASELINE TEST")
    print("=" * 80)
    print()
    print("Testing Grace's current code generation capabilities")
    print()
    
    # Initialize database
    print("Initializing database...")
    try:
        from backend.database.connection import DatabaseConnection, DatabaseConfig, DatabaseType
        
        # Use SQLite by default
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
        print(f"WARNING: Database initialization: {e}")
        import traceback
        traceback.print_exc()
    
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
        
        print("[OK] Grace Coding Agent initialized")
        print()
    except Exception as e:
        print(f"ERROR: Could not initialize Coding Agent: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test tasks (similar to BigCodeBench style)
    test_tasks = [
        {
            "id": "test_1",
            "type": "code_generation",
            "description": "Create a Python function that calculates the factorial of a number using recursion, with proper error handling and type hints.",
            "expected_elements": ["def", "factorial", "recursion", "try", "except", "int", "->"]
        },
        {
            "id": "test_2",
            "type": "code_generation",
            "description": "Write a function that finds the maximum value in a list of numbers, handling empty lists and non-numeric values gracefully.",
            "expected_elements": ["def", "max", "list", "try", "except", "if", "len"]
        },
        {
            "id": "test_3",
            "type": "code_generation",
            "description": "Create an async function that fetches data from a URL and returns the JSON response, with timeout and error handling.",
            "expected_elements": ["async def", "await", "aiohttp", "try", "except", "timeout", "json"]
        },
        {
            "id": "test_4",
            "type": "code_fix",
            "description": "Fix this broken code: def divide(a, b): return a / b",
            "expected_elements": ["def", "divide", "try", "except", "ZeroDivisionError", "return"]
        },
        {
            "id": "test_5",
            "type": "code_generation",
            "description": "Write a function that validates an email address using regex, returning True if valid, False otherwise.",
            "expected_elements": ["def", "email", "re", "match", "return", "True", "False"]
        }
    ]
    
    print("=" * 80)
    print("TESTING CODE GENERATION")
    print("=" * 80)
    print()
    
    results = {
        "total": len(test_tasks),
        "passed": 0,
        "failed": 0,
        "task_results": []
    }
    
    for i, task in enumerate(test_tasks, 1):
        task_id = task["id"]
        description = task["description"]
        expected_elements = task.get("expected_elements", [])
        
        print(f"[{i}/{len(test_tasks)}] Task: {task_id}")
        print(f"  Description: {description[:80]}...")
        
        try:
            # Create and execute task
            coding_task = coding_agent.create_task(
                task_type=task["type"],
                description=description
            )
            
            execution_result = coding_agent.execute_task(coding_task.task_id)
            
            if execution_result.get("success"):
                generation = execution_result.get("result", {}).get("generation")
                if generation:
                    generated_code = generation.code_after if hasattr(generation, 'code_after') else str(generation)
                    
                    # Check for expected elements
                    code_lower = generated_code.lower()
                    found_elements = [elem for elem in expected_elements if elem.lower() in code_lower]
                    coverage = len(found_elements) / len(expected_elements) if expected_elements else 1.0
                    
                    # Quality checks
                    has_error_handling = "try" in code_lower or "except" in code_lower
                    has_type_hints = "->" in generated_code or ":" in generated_code.split("\n")[0]
                    has_docstring = '"""' in generated_code or "'''" in generated_code
                    
                    # Score the generation
                    quality_score = 0.0
                    quality_score += 0.3 if coverage >= 0.8 else coverage * 0.3
                    quality_score += 0.25 if has_error_handling else 0.0
                    quality_score += 0.25 if has_type_hints else 0.0
                    quality_score += 0.2 if has_docstring else 0.0
                    
                    passed = quality_score >= 0.7  # 70% threshold
                    
                    if passed:
                        print(f"  [PASS] PASSED (Quality: {quality_score:.2f})")
                        results["passed"] += 1
                    else:
                        print(f"  [FAIL] FAILED (Quality: {quality_score:.2f})")
                        results["failed"] += 1
                    
                    print(f"    Coverage: {len(found_elements)}/{len(expected_elements)} elements")
                    print(f"    Error Handling: {'YES' if has_error_handling else 'NO'}")
                    print(f"    Type Hints: {'YES' if has_type_hints else 'NO'}")
                    print(f"    Docstring: {'YES' if has_docstring else 'NO'}")
                    
                    results["task_results"].append({
                        "task_id": task_id,
                        "passed": passed,
                        "quality_score": quality_score,
                        "coverage": coverage,
                        "has_error_handling": has_error_handling,
                        "has_type_hints": has_type_hints,
                        "has_docstring": has_docstring
                    })
                else:
                    print("  [FAIL] No code generated")
                    results["failed"] += 1
            else:
                print("  [FAIL] Task execution failed")
                results["failed"] += 1
                if execution_result.get("error"):
                    print(f"    Error: {execution_result['error']}")
            
            print()
            
        except Exception as e:
            print(f"  [ERROR] Error: {e}")
            results["failed"] += 1
            print()
    
    # Calculate success rate
    if results["total"] > 0:
        success_rate = (results["passed"] / results["total"]) * 100.0
    else:
        success_rate = 0.0
    
    # Calculate average quality
    if results["task_results"]:
        avg_quality = sum(r["quality_score"] for r in results["task_results"]) / len(results["task_results"])
    else:
        avg_quality = 0.0
    
    # Display results
    print()
    print("=" * 80)
    print("BASELINE RESULTS")
    print("=" * 80)
    print()
    print(f"Total Tasks Tested: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print()
    print(f"Success Rate: {success_rate:.2f}%")
    print(f"Average Quality Score: {avg_quality:.2f}")
    print()
    
    # Quality breakdown
    if results["task_results"]:
        print("Quality Breakdown:")
        error_handling_pct = (sum(1 for r in results["task_results"] if r["has_error_handling"]) / len(results["task_results"])) * 100
        type_hints_pct = (sum(1 for r in results["task_results"] if r["has_type_hints"]) / len(results["task_results"])) * 100
        docstring_pct = (sum(1 for r in results["task_results"] if r["has_docstring"]) / len(results["task_results"])) * 100
        
        print(f"  Error Handling: {error_handling_pct:.1f}%")
        print(f"  Type Hints: {type_hints_pct:.1f}%")
        print(f"  Docstrings: {docstring_pct:.1f}%")
        print()
    
    # Projection to BigCodeBench
    print("=" * 80)
    print("PROJECTION TO BIGCODEBENCH")
    print("=" * 80)
    print()
    print("Based on current performance:")
    print(f"  Estimated BigCodeBench Performance: {success_rate:.1f}% - {success_rate * 1.2:.1f}%")
    print()
    print("Current Leaderboard (BigCodeBench-Complete):")
    print("  GPT-4o: 61.1%")
    print("  DeepSeek-Coder-V2: 59.7%")
    print("  Claude-3.5-Sonnet: 58.6%")
    print("  Human Expert: ~97%")
    print()
    
    if success_rate > 0:
        gap_to_gpt4o = 61.1 - success_rate
        gap_to_human = 97.0 - success_rate
        
        print(f"Estimated Gap to GPT-4o: {gap_to_gpt4o:+.1f}%")
        print(f"Estimated Gap to Human: {gap_to_human:+.1f}%")
        print()
        
        if success_rate >= 98.0:
            print("🎉 TARGET ACHIEVED! Grace is at 98%+ accuracy!")
        else:
            remaining = 98.0 - success_rate
            print(f"Remaining to 98% target: {remaining:.1f}%")
            print()
            print("Training will continue until 98% is reached.")
    
    print()
    print("=" * 80)
    print("Note: This is a baseline test with sample tasks.")
    print("Full BigCodeBench evaluation requires BigCodeBench installation.")
    print("Continuous training will improve performance over time.")
    print("=" * 80)


if __name__ == "__main__":
    test_code_generation()
