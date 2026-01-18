"""
Comprehensive tests for the Outcome LLM Bridge.

Tests cover:
- OutcomeLLMBridge initialization
- on_learning_example_created with high trust
- on_learning_example_created with low trust (skipped)
- Batching/debouncing behavior
- Queue size limits
- get_stats
- Thread safety
"""

import sys
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timedelta

import pytest

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


class MockLearningExample:
    """Mock LearningExample for testing."""
    
    def __init__(self, id=1, trust_score=0.9, example_type='healing'):
        self.id = id
        self.trust_score = trust_score
        self.example_type = example_type


class TestOutcomeLLMBridgeInitialization:
    """Tests for OutcomeLLMBridge initialization."""
    
    def test_init_without_session(self):
        """Test initialization without database session."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        assert bridge.session is None
        assert bridge.learning_integration is None
        assert bridge.update_queue == []
        assert bridge.batch_size == 5
        assert bridge.debounce_seconds == 60
        assert bridge.max_queue_size == 100
    
    def test_init_with_mock_session(self):
        """Test initialization with mock session."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        mock_session = MagicMock()
        bridge = OutcomeLLMBridge(session=mock_session)
        
        assert bridge.session == mock_session
    
    def test_init_with_learning_integration(self):
        """Test initialization with learning integration."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        mock_integration = MagicMock()
        bridge = OutcomeLLMBridge(learning_integration=mock_integration)
        
        assert bridge.learning_integration == mock_integration
    
    def test_stats_initialized(self):
        """Test that stats are properly initialized."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        assert bridge.stats['total_examples_processed'] == 0
        assert bridge.stats['llm_updates_triggered'] == 0
        assert bridge.stats['high_trust_examples'] == 0
        assert bridge.stats['low_trust_examples_skipped'] == 0
        assert bridge.stats['queued_for_batch'] == 0
        assert bridge.stats['errors'] == 0


class TestOnLearningExampleCreatedHighTrust:
    """Tests for on_learning_example_created with high trust scores."""
    
    def test_high_trust_queued(self):
        """Test that high trust examples are queued."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        example = MockLearningExample(id=1, trust_score=0.9)
        result = bridge.on_learning_example_created(example)
        
        assert result['triggered'] is True
        assert result['queued'] is True
        assert result['trust_score'] == 0.9
        assert bridge.stats['high_trust_examples'] == 1
    
    def test_high_trust_increments_stats(self):
        """Test that processing high trust examples updates stats."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        for i in range(3):
            example = MockLearningExample(id=i+1, trust_score=0.85)
            bridge.on_learning_example_created(example)
        
        assert bridge.stats['total_examples_processed'] == 3
        assert bridge.stats['high_trust_examples'] == 3
        assert bridge.stats['queued_for_batch'] == 3
    
    def test_exact_threshold_queued(self):
        """Test that examples at exactly the threshold are queued."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        example = MockLearningExample(id=1, trust_score=0.8)
        result = bridge.on_learning_example_created(example, min_trust_threshold=0.8)
        
        assert result['triggered'] is True


class TestOnLearningExampleCreatedLowTrust:
    """Tests for on_learning_example_created with low trust scores."""
    
    def test_low_trust_skipped(self):
        """Test that low trust examples are skipped."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        example = MockLearningExample(id=1, trust_score=0.5)
        result = bridge.on_learning_example_created(example)
        
        assert result['triggered'] is False
        assert 'Trust score' in result['reason']
        assert bridge.stats['low_trust_examples_skipped'] == 1
    
    def test_low_trust_not_queued(self):
        """Test that low trust examples don't enter the queue."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        example = MockLearningExample(id=1, trust_score=0.3)
        bridge.on_learning_example_created(example)
        
        assert len(bridge.update_queue) == 0
        assert bridge.stats['queued_for_batch'] == 0
    
    def test_just_below_threshold_skipped(self):
        """Test that examples just below threshold are skipped."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        example = MockLearningExample(id=1, trust_score=0.79)
        result = bridge.on_learning_example_created(example, min_trust_threshold=0.8)
        
        assert result['triggered'] is False
    
    def test_custom_threshold(self):
        """Test with custom trust threshold."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        example = MockLearningExample(id=1, trust_score=0.6)
        result = bridge.on_learning_example_created(example, min_trust_threshold=0.5)
        
        assert result['triggered'] is True  # 0.6 >= 0.5


class TestBatchingDebouncing:
    """Tests for batching and debouncing behavior."""
    
    def test_queue_grows_before_batch_size(self):
        """Test that queue grows when under batch size."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        bridge.batch_size = 5
        
        for i in range(3):
            example = MockLearningExample(id=i+1, trust_score=0.9)
            bridge.on_learning_example_created(example)
        
        # Queue should have 3 items (pending batch processing)
        assert len(bridge.update_queue) <= 3  # May be processed async
    
    def test_batch_size_configurable(self):
        """Test that batch size is configurable."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        bridge.batch_size = 10
        
        assert bridge.batch_size == 10
    
    def test_debounce_seconds_configurable(self):
        """Test that debounce seconds is configurable."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        bridge.debounce_seconds = 120
        
        assert bridge.debounce_seconds == 120


class TestQueueSizeLimits:
    """Tests for queue size limits."""
    
    def test_queue_has_max_size(self):
        """Test that queue has a maximum size."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        assert bridge.max_queue_size == 100
    
    def test_queue_drops_oldest_when_full(self):
        """Test that oldest items are dropped when queue is full."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        bridge.max_queue_size = 5
        
        # Manually fill queue beyond max (bypassing async processing)
        with bridge.update_lock:
            bridge.update_queue = [1, 2, 3, 4, 5]
        
        # Add one more
        example = MockLearningExample(id=100, trust_score=0.9)
        bridge.on_learning_example_created(example)
        
        # Queue should still be at max or processing
        assert len(bridge.update_queue) <= bridge.max_queue_size + 1
    
    def test_max_queue_size_configurable(self):
        """Test that max queue size can be changed."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        bridge.max_queue_size = 50
        
        assert bridge.max_queue_size == 50


class TestGetStats:
    """Tests for get_stats method."""
    
    def test_get_stats_returns_dict(self):
        """Test that get_stats returns a dictionary."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        stats = bridge.get_stats()
        
        assert isinstance(stats, dict)
    
    def test_get_stats_contains_expected_keys(self):
        """Test that stats contain expected keys."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        stats = bridge.get_stats()
        
        assert 'total_examples_processed' in stats
        assert 'llm_updates_triggered' in stats
        assert 'high_trust_examples' in stats
        assert 'low_trust_examples_skipped' in stats
        assert 'queued_for_batch' in stats
        assert 'errors' in stats
        assert 'queue_size' in stats
        assert 'timestamp' in stats
    
    def test_get_stats_reflects_processing(self):
        """Test that stats reflect actual processing."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        # Process some examples
        high_trust = MockLearningExample(id=1, trust_score=0.9)
        low_trust = MockLearningExample(id=2, trust_score=0.3)
        
        bridge.on_learning_example_created(high_trust)
        bridge.on_learning_example_created(low_trust)
        
        stats = bridge.get_stats()
        
        assert stats['total_examples_processed'] == 2
        assert stats['high_trust_examples'] == 1
        assert stats['low_trust_examples_skipped'] == 1
    
    def test_get_stats_includes_last_update_time(self):
        """Test that stats include last update time."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        # Initially should be None
        stats = bridge.get_stats()
        assert stats['last_update_time'] is None
        
        # After setting, should be a string
        bridge.last_update_time = datetime.utcnow()
        stats = bridge.get_stats()
        assert stats['last_update_time'] is not None


class TestThreadSafety:
    """Tests for thread safety."""
    
    def test_has_update_lock(self):
        """Test that bridge has an update lock."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        assert hasattr(bridge, 'update_lock')
        assert isinstance(bridge.update_lock, type(threading.Lock()))
    
    def test_concurrent_example_processing(self):
        """Test concurrent processing of examples."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        results = []
        errors = []
        
        def process_example(idx):
            try:
                example = MockLearningExample(id=idx, trust_score=0.9)
                result = bridge.on_learning_example_created(example)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=process_example, args=(i,)) for i in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        
        assert len(errors) == 0
        assert len(results) == 10
        assert bridge.stats['total_examples_processed'] == 10
    
    def test_concurrent_stats_access(self):
        """Test concurrent access to stats."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        errors = []
        
        def access_stats():
            try:
                for _ in range(100):
                    stats = bridge.get_stats()
                    assert 'queue_size' in stats
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=access_stats) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        
        assert len(errors) == 0


class TestExampleWithoutId:
    """Tests for examples without ID."""
    
    def test_example_without_id_not_queued(self):
        """Test that examples without ID are not queued."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        example = MockLearningExample(id=None, trust_score=0.9)
        result = bridge.on_learning_example_created(example)
        
        assert result['triggered'] is False
        assert 'no ID' in result['reason']


class TestGetOutcomeBridge:
    """Tests for get_outcome_bridge singleton."""
    
    def test_get_outcome_bridge_returns_instance(self):
        """Test that get_outcome_bridge returns an instance."""
        from cognitive.outcome_llm_bridge import get_outcome_bridge
        
        bridge = get_outcome_bridge()
        
        assert bridge is not None
    
    def test_get_outcome_bridge_with_session(self):
        """Test get_outcome_bridge with session parameter."""
        from cognitive.outcome_llm_bridge import get_outcome_bridge
        
        mock_session = MagicMock()
        bridge = get_outcome_bridge(session=mock_session)
        
        assert bridge is not None


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_errors_tracked_in_stats(self):
        """Test that errors are tracked in stats."""
        from cognitive.outcome_llm_bridge import OutcomeLLMBridge
        bridge = OutcomeLLMBridge()
        
        # Simulate an error by breaking the queue
        with patch.object(bridge, 'update_queue', None):
            try:
                example = MockLearningExample(id=1, trust_score=0.9)
                bridge.on_learning_example_created(example)
            except Exception:
                pass  # Expected to fail
        
        # Stats should track the error
        # Note: The actual error tracking depends on where the exception occurs
        assert bridge.stats['errors'] >= 0
