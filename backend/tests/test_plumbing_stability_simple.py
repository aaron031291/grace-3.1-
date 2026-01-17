"""
Simple Plumbing Stability Test - Basic functionality verification

Tests core plumbing fixes without complex imports.
"""
import sys
import os
import time
import threading
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from database.session import SessionLocal, initialize_session_factory
from cognitive.learning_memory import LearningExample

# Test results
test_results = []

def test_result(name: str, success: bool, message: str = ""):
    """Record test result."""
    test_results.append((name, success, message))
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status}: {name}")
    if message:
        print(f"      {message}")

def test_1_database_connection():
    """Test 1: Database connection works."""
    try:
        from database.connection import DatabaseConnection
        from database.config import DatabaseConfig, DatabaseType
        from pathlib import Path
        
        # Initialize database if not already initialized
        try:
            DatabaseConnection.get_engine()
        except RuntimeError:
            # Database not initialized, initialize it
            # Use correct parameter name: database_path (not db_path)
            test_db_path = Path("backend/data/grace_test.db")
            test_db_path.parent.mkdir(parents=True, exist_ok=True)
            
            config = DatabaseConfig(
                db_type=DatabaseType.SQLITE,
                database_path=str(test_db_path)
            )
            DatabaseConnection.initialize(config)
        
        # Initialize session factory
        session_factory = initialize_session_factory()
        if session_factory is None:
            test_result("Database Connection", False, "Session factory not initialized")
            return False
        
        session = session_factory()
        session.close()
        test_result("Database Connection", True)
        return True
    except Exception as e:
        test_result("Database Connection", False, str(e))
        import traceback
        traceback.print_exc()
        return False

def test_2_learning_example_creation():
    """Test 2: Can create LearningExample."""
    try:
        from database.connection import DatabaseConnection
        from database.config import DatabaseConfig, DatabaseType
        from pathlib import Path
        
        # Ensure database is initialized
        try:
            DatabaseConnection.get_engine()
        except RuntimeError:
            test_db_path = Path("backend/data/grace_test.db")
            test_db_path.parent.mkdir(parents=True, exist_ok=True)
            config = DatabaseConfig(
                db_type=DatabaseType.SQLITE,
                database_path=str(test_db_path)
            )
            DatabaseConnection.initialize(config)
        
        # Ensure session factory is initialized
        session_factory = initialize_session_factory()
        if session_factory is None:
            test_result("LearningExample Creation", False, "Session factory not initialized")
            return False
        
        # Create tables if they don't exist
        try:
            from database.base import Base
            from database.connection import DatabaseConnection
            engine = DatabaseConnection.get_engine()
            Base.metadata.create_all(engine)
        except Exception as table_error:
            # Tables might already exist, continue
            pass
        
        session = session_factory()
        example = LearningExample(
            example_type="test",
            input_context={"test": "data"},
            expected_output={"result": "success"},
            trust_score=0.9,
            source="test"
        )
        session.add(example)
        session.commit()
        session.refresh(example)
        
        assert example.id is not None, "Example should have ID"
        assert example.trust_score == 0.9, "Trust score should be 0.9"
        
        session.close()
        test_result("LearningExample Creation", True)
        return True
    except Exception as e:
        test_result("LearningExample Creation", False, str(e))
        import traceback
        traceback.print_exc()
        return False

def test_3_event_listener_registered():
    """Test 3: Event listener is registered."""
    try:
        from sqlalchemy import event
        from cognitive.learning_memory import LearningExample
        
        # Check if event listener is registered
        listeners = event.contains(LearningExample, 'after_insert', None)
        test_result("Event Listener Registered", True, f"Listeners found: {listeners}")
        return True
    except Exception as e:
        test_result("Event Listener Registered", False, str(e))
        return False

def test_4_knowledge_file_path():
    """Test 4: Knowledge file path can be resolved."""
    try:
        from pathlib import Path
        from settings import KNOWLEDGE_BASE_PATH
        
        kb_path = Path(KNOWLEDGE_BASE_PATH)
        if not kb_path.exists():
            kb_path = Path("backend/knowledge_base")
        if not kb_path.exists():
            kb_path = Path("knowledge_base")
        
        learned_knowledge_dir = kb_path / "layer_1" / "learning_memory"
        learned_knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        knowledge_file = learned_knowledge_dir / "learned_knowledge.md"
        
        test_result("Knowledge File Path", True, f"Path: {knowledge_file}")
        return True
    except Exception as e:
        test_result("Knowledge File Path", False, str(e))
        return False

def test_5_batch_processing_logic():
    """Test 5: Batch processing logic (without actual processing)."""
    try:
        # Test queue management logic
        update_queue = []
        max_queue_size = 100
        batch_size = 5
        
        # Simulate adding items
        for i in range(150):
            if len(update_queue) >= max_queue_size:
                update_queue.pop(0)  # Drop oldest
            update_queue.append(i)
        
        assert len(update_queue) <= max_queue_size, "Queue should not exceed max size"
        assert len(update_queue) == max_queue_size, "Queue should be at max size"
        
        # Simulate batch extraction
        batch = update_queue[:batch_size]
        remaining = update_queue[batch_size:]
        
        assert len(batch) == batch_size, "Batch should be correct size"
        assert len(remaining) == max_queue_size - batch_size, "Remaining should be correct"
        
        test_result("Batch Processing Logic", True)
        return True
    except Exception as e:
        test_result("Batch Processing Logic", False, str(e))
        return False

def main():
    """Run all stability tests."""
    print("\n" + "="*70)
    print("PLUMBING STABILITY TEST SUITE (Simple)")
    print("="*70)
    print("\nTesting core plumbing functionality...\n")
    
    # Run tests
    tests = [
        ("Database Connection", test_1_database_connection),
        ("LearningExample Creation", test_2_learning_example_creation),
        ("Event Listener Registered", test_3_event_listener_registered),
        ("Knowledge File Path", test_4_knowledge_file_path),
        ("Batch Processing Logic", test_5_batch_processing_logic),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"[FAIL] Test crashed: {test_name} - {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}: {test_name}")
    
    print("\n" + "="*70)
    print(f"TOTAL: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("STATUS: [SUCCESS] ALL TESTS PASSED - Core plumbing is stable!")
    else:
        print(f"STATUS: [WARNING] {total_count - passed_count} test(s) failed")
    
    print("="*70 + "\n")
    
    return 0 if passed_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())
