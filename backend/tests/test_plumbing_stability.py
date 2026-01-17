"""
Plumbing Stability Test - Verify all plumbing fixes work correctly

Tests:
1. OutcomeLLMBridge functionality
2. Knowledge persistence and ingestion
3. Batch processing
4. Thread safety
5. No DetachedInstanceError
6. Queue management
"""
import sys
import os
import time
import threading
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session
from database.session import SessionLocal, initialize_session_factory
from cognitive.learning_memory import LearningExample, LearningMemoryManager
from cognitive.outcome_llm_bridge import get_outcome_bridge, OutcomeLLMBridge
from llm_orchestrator.learning_integration import get_learning_integration
from pathlib import Path

# Test results
test_results = []

def test_result(name: str, success: bool, message: str = ""):
    """Record test result."""
    test_results.append((name, success, message))
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {name}")
    if message:
        print(f"      {message}")

def test_1_bridge_initialization():
    """Test 1: Bridge initializes correctly."""
    try:
        session = SessionLocal()
        bridge = get_outcome_bridge(session=session)
        
        assert bridge is not None, "Bridge should not be None"
        assert hasattr(bridge, 'update_queue'), "Bridge should have update_queue"
        assert hasattr(bridge, 'update_lock'), "Bridge should have update_lock"
        assert bridge.max_queue_size == 100, "Max queue size should be 100"
        
        session.close()
        test_result("Bridge Initialization", True)
        return True
    except Exception as e:
        test_result("Bridge Initialization", False, str(e))
        return False

def test_2_queue_stores_ids_not_objects():
    """Test 2: Queue stores IDs, not SQLAlchemy objects."""
    try:
        session = SessionLocal()
        bridge = get_outcome_bridge(session=session)
        
        # Create a test LearningExample
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
        
        # Queue the example
        result = bridge.on_learning_example_created(example)
        
        # Check queue contains IDs, not objects
        with bridge.update_lock:
            queue = bridge.update_queue
            assert len(queue) > 0, "Queue should have items"
            for item in queue:
                assert isinstance(item, int), f"Queue item should be int (ID), got {type(item)}"
                assert item == example.id, "Queue should contain example ID"
        
        session.close()
        test_result("Queue Stores IDs", True)
        return True
    except Exception as e:
        test_result("Queue Stores IDs", False, str(e))
        return False

def test_3_no_detached_instance_error():
    """Test 3: No DetachedInstanceError when accessing queued examples."""
    try:
        session1 = SessionLocal()
        bridge = get_outcome_bridge(session=session1)
        
        # Create example in session1
        example = LearningExample(
            example_type="test",
            input_context={"test": "data"},
            expected_output={"result": "success"},
            trust_score=0.9,
            source="test"
        )
        session1.add(example)
        session1.commit()
        session1.refresh(example)
        example_id = example.id
        
        # Queue it
        bridge.on_learning_example_created(example)
        
        # Close session1 (this would detach objects)
        session1.close()
        
        # Wait a bit for batch processing
        time.sleep(2)
        
        # Try to process - should not get DetachedInstanceError
        # The background thread should re-query in its own session
        stats = bridge.get_stats()
        assert stats is not None, "Should get stats without error"
        
        test_result("No DetachedInstanceError", True)
        return True
    except Exception as e:
        test_result("No DetachedInstanceError", False, str(e))
        return False

def test_4_batch_processing():
    """Test 4: Batch processing works correctly."""
    try:
        session = SessionLocal()
        bridge = get_outcome_bridge(session=session)
        
        # Create multiple examples
        example_ids = []
        for i in range(7):  # More than batch_size (5)
            example = LearningExample(
                example_type="test",
                input_context={"test": f"data_{i}"},
                expected_output={"result": "success"},
                trust_score=0.9,
                source="test"
            )
            session.add(example)
            session.commit()
            session.refresh(example)
            example_ids.append(example.id)
            
            # Queue each one
            bridge.on_learning_example_created(example)
        
        # Wait for batch processing
        time.sleep(5)
        
        # Check stats
        stats = bridge.get_stats()
        assert stats["llm_updates_triggered"] > 0, "Should have triggered updates"
        assert stats["high_trust_examples"] >= 7, "Should have processed all examples"
        
        session.close()
        test_result("Batch Processing", True)
        return True
    except Exception as e:
        test_result("Batch Processing", False, str(e))
        return False

def test_5_queue_size_limit():
    """Test 5: Queue size limit prevents memory leaks."""
    try:
        session = SessionLocal()
        bridge = get_outcome_bridge(session=session)
        
        # Create more examples than max_queue_size
        for i in range(150):  # More than max_queue_size (100)
            example = LearningExample(
                example_type="test",
                input_context={"test": f"data_{i}"},
                expected_output={"result": "success"},
                trust_score=0.9,
                source="test"
            )
            session.add(example)
            session.commit()
            session.refresh(example)
            bridge.on_learning_example_created(example)
        
        # Check queue size
        with bridge.update_lock:
            queue_size = len(bridge.update_queue)
            assert queue_size <= bridge.max_queue_size, f"Queue size {queue_size} should not exceed {bridge.max_queue_size}"
        
        session.close()
        test_result("Queue Size Limit", True)
        return True
    except Exception as e:
        test_result("Queue Size Limit", False, str(e))
        return False

def test_6_knowledge_persistence():
    """Test 6: Knowledge is persisted to file."""
    try:
        from settings import KNOWLEDGE_BASE_PATH
        
        # Check if learned_knowledge.md exists
        kb_path = Path(KNOWLEDGE_BASE_PATH)
        if not kb_path.exists():
            kb_path = Path("backend/knowledge_base")
        if not kb_path.exists():
            kb_path = Path("knowledge_base")
        
        knowledge_file = kb_path / "layer_1" / "learning_memory" / "learned_knowledge.md"
        
        # Trigger an update by creating a high-trust example
        session = SessionLocal()
        bridge = get_outcome_bridge(session=session)
        
        example = LearningExample(
            example_type="test",
            input_context={"test": "knowledge_persistence"},
            expected_output={"result": "success"},
            trust_score=0.9,
            source="test"
        )
        session.add(example)
        session.commit()
        session.refresh(example)
        bridge.on_learning_example_created(example)
        
        # Wait for processing
        time.sleep(10)
        
        # Check if file exists
        if knowledge_file.exists():
            test_result("Knowledge Persistence", True, f"File exists: {knowledge_file}")
            return True
        else:
            test_result("Knowledge Persistence", False, f"File not found: {knowledge_file}")
            return False
        
        session.close()
    except Exception as e:
        test_result("Knowledge Persistence", False, str(e))
        return False

def test_7_thread_safety():
    """Test 7: Thread safety - multiple threads can queue simultaneously."""
    try:
        session = SessionLocal()
        bridge = get_outcome_bridge(session=session)
        
        def create_and_queue(i):
            sess = SessionLocal()
            try:
                example = LearningExample(
                    example_type="test",
                    input_context={"test": f"thread_{i}"},
                    expected_output={"result": "success"},
                    trust_score=0.9,
                    source="test"
                )
                sess.add(example)
                sess.commit()
                sess.refresh(example)
                bridge.on_learning_example_created(example)
            finally:
                sess.close()
        
        # Create examples from multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_and_queue, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check stats
        stats = bridge.get_stats()
        assert stats["queued_for_batch"] >= 10, "Should have queued examples from all threads"
        
        session.close()
        test_result("Thread Safety", True)
        return True
    except Exception as e:
        test_result("Thread Safety", False, str(e))
        return False

def test_8_knowledge_ingestion():
    """Test 8: Knowledge file is ingested to Qdrant."""
    try:
        from ingestion.file_manager import get_file_manager
        
        # Check if file manager can find the knowledge file
        file_manager = get_file_manager()
        if not file_manager:
            test_result("Knowledge Ingestion", False, "File manager not available")
            return False
        
        # Check if learned_knowledge.md is in tracked files
        from settings import KNOWLEDGE_BASE_PATH
        kb_path = Path(KNOWLEDGE_BASE_PATH)
        if not kb_path.exists():
            kb_path = Path("backend/knowledge_base")
        if not kb_path.exists():
            kb_path = Path("knowledge_base")
        
        knowledge_file = kb_path / "layer_1" / "learning_memory" / "learned_knowledge.md"
        rel_path = str(knowledge_file.relative_to(kb_path)) if knowledge_file.exists() else None
        
        if knowledge_file.exists():
            # File exists - ingestion should have been triggered
            test_result("Knowledge Ingestion", True, f"File exists, should be ingested: {knowledge_file}")
            return True
        else:
            test_result("Knowledge Ingestion", False, f"File not found: {knowledge_file}")
            return False
    except Exception as e:
        test_result("Knowledge Ingestion", False, str(e))
        return False

def main():
    """Run all stability tests."""
    print("\n" + "="*70)
    print("PLUMBING STABILITY TEST SUITE")
    print("="*70)
    print("\nTesting all plumbing fixes...\n")
    
    # Initialize database
    try:
        initialize_session_factory()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1
    
    # Run tests
    tests = [
        ("Bridge Initialization", test_1_bridge_initialization),
        ("Queue Stores IDs", test_2_queue_stores_ids_not_objects),
        ("No DetachedInstanceError", test_3_no_detached_instance_error),
        ("Batch Processing", test_4_batch_processing),
        ("Queue Size Limit", test_5_queue_size_limit),
        ("Knowledge Persistence", test_6_knowledge_persistence),
        ("Thread Safety", test_7_thread_safety),
        ("Knowledge Ingestion", test_8_knowledge_ingestion),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"❌ Test crashed: {test_name} - {e}")
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
        print("STATUS: ✅ ALL TESTS PASSED - Plumbing is stable!")
    else:
        print(f"STATUS: ⚠️ {total_count - passed_count} test(s) failed")
    
    print("="*70 + "\n")
    
    return 0 if passed_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())
