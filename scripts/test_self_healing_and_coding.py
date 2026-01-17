#!/usr/bin/env python3
"""
Test Self-Healing and Coding Agent

Comprehensive test of both systems.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from datetime import datetime
from typing import Dict, Any


def test_coding_agent():
    """Test Coding Agent."""
    print("=" * 80)
    print("CODING AGENT TEST")
    print("=" * 80)
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
        return None
    
    # Initialize Coding Agent
    print("Initializing Coding Agent...")
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
        
        print("[OK] Coding Agent initialized")
        print()
    except Exception as e:
        print(f"ERROR: Could not initialize Coding Agent: {e}")
        return None
    
    # Test tasks
    test_tasks = [
        {
            "id": "test_1",
            "type": "code_generation",
            "description": "Create a Python function that calculates the factorial of a number using recursion, with proper error handling and type hints.",
        },
        {
            "id": "test_2",
            "type": "code_generation",
            "description": "Write a function that finds the maximum value in a list of numbers, handling empty lists and non-numeric values gracefully.",
        },
    ]
    
    print("Testing code generation...")
    results = {
        "total": len(test_tasks),
        "passed": 0,
        "failed": 0,
        "task_results": []
    }
    
    for i, task in enumerate(test_tasks, 1):
        print(f"  [{i}/{len(test_tasks)}] Task: {task['id']}")
        
        try:
            coding_task = coding_agent.create_task(
                task_type=task["type"],
                description=task["description"]
            )
            
            execution_result = coding_agent.execute_task(coding_task.task_id)
            
            if execution_result.get("success"):
                generation = execution_result.get("result", {}).get("generation")
                if generation:
                    print(f"    [OK] Code generated")
                    results["passed"] += 1
                else:
                    print(f"    [FAIL] No code generated")
                    results["failed"] += 1
            else:
                print(f"    [FAIL] Task execution failed")
                results["failed"] += 1
        except Exception as e:
            print(f"    [ERROR] {e}")
            results["failed"] += 1
    
    success_rate = (results["passed"] / results["total"]) * 100.0 if results["total"] > 0 else 0.0
    
    print()
    print(f"Results: {results['passed']}/{results['total']} passed ({success_rate:.1f}%)")
    print()
    
    return {
        "success_rate": success_rate,
        "passed": results["passed"],
        "total": results["total"]
    }


def test_self_healing():
    """Test Self-Healing System."""
    print("=" * 80)
    print("SELF-HEALING SYSTEM TEST")
    print("=" * 80)
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
        return None
    
    # Check Memory Mesh for knowledge
    print("Checking Memory Mesh for knowledge...")
    try:
        from backend.database.session import get_session
        from cognitive.memory_mesh_integration import MemoryMeshIntegration
        
        session = next(get_session())
        kb_path = project_root / "knowledge_base"
        memory_mesh = MemoryMeshIntegration(session=session, knowledge_base_path=kb_path)
        
        # Check for learning examples
        from cognitive.learning_memory import LearningExample
        examples = session.query(LearningExample).filter(
            LearningExample.example_type == "external_knowledge"
        ).limit(10).all()
        
        print(f"[OK] Memory Mesh accessible")
        print(f"  External knowledge examples: {len(examples)}")
        
        if examples:
            print("  Sample knowledge:")
            for ex in examples[:3]:
                try:
                    import json
                    if hasattr(ex, 'input_context'):
                        context = ex.input_context if isinstance(ex.input_context, dict) else json.loads(ex.input_context) if ex.input_context else {}
                    else:
                        context = {}
                    title = context.get("title", "Unknown")[:60]
                    print(f"    - {title}")
                except Exception:
                    print(f"    - Example ID: {ex.id}")
        
        print()
        
        return {
            "memory_mesh_accessible": True,
            "external_knowledge_count": len(examples)
        }
        
    except Exception as e:
        print(f"ERROR: Memory Mesh check failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run both tests."""
    print("=" * 80)
    print("COMPREHENSIVE SYSTEM TESTS")
    print("=" * 80)
    print()
    print(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test Coding Agent
    coding_results = test_coding_agent()
    
    print()
    
    # Test Self-Healing
    healing_results = test_self_healing()
    
    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    if coding_results:
        print(f"Coding Agent:")
        print(f"  Success Rate: {coding_results['success_rate']:.1f}%")
        print(f"  Passed: {coding_results['passed']}/{coding_results['total']}")
    else:
        print("Coding Agent: TEST FAILED")
    
    print()
    
    if healing_results:
        print(f"Self-Healing / Memory Mesh:")
        print(f"  Memory Mesh: {'Accessible' if healing_results.get('memory_mesh_accessible') else 'Not Accessible'}")
        print(f"  External Knowledge: {healing_results.get('external_knowledge_count', 0)} examples")
    else:
        print("Self-Healing: TEST FAILED")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
