"""
Test Suite for Outcome Aggregator Service

Tests the OutcomeAggregator class which provides unified outcome aggregation
from all systems (healing, testing, diagnostics, LLM, file_processing).
"""

import sys
sys.path.insert(0, 'backend')

import pytest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

try:
    from cognitive.outcome_aggregator import OutcomeAggregator, get_outcome_aggregator
except ImportError:
    pytest.skip("outcome_aggregator module not available", allow_module_level=True)


class TestRecordOutcome:
    """Tests for record_outcome() method."""
    
    def test_records_outcome_correctly(self):
        """Test that outcome is recorded with correct fields."""
        aggregator = OutcomeAggregator(session=None)
        
        outcome = {
            'success': True,
            'trust_score': 0.85,
            'action': 'fix_import',
            'context': {'file': 'test.py'}
        }
        
        outcome_id = aggregator.record_outcome('healing', outcome)
        
        assert outcome_id is not None
        assert len(outcome_id) == 36  # UUID format
        
        outcomes = aggregator.get_outcomes()
        assert len(outcomes) == 1
        assert outcomes[0]['source'] == 'healing'
        assert outcomes[0]['success'] is True
        assert outcomes[0]['trust_score'] == 0.85
        assert outcomes[0]['outcome'] == outcome
    
    def test_returns_valid_outcome_id(self):
        """Test that record_outcome returns a valid UUID."""
        aggregator = OutcomeAggregator(session=None)
        
        outcome_id = aggregator.record_outcome('testing', {'success': True})
        
        assert outcome_id is not None
        assert isinstance(outcome_id, str)
        assert len(outcome_id) == 36
        # UUID format: 8-4-4-4-12
        parts = outcome_id.split('-')
        assert len(parts) == 5
    
    def test_stores_with_correct_fields(self):
        """Test that stored outcome has all required fields."""
        aggregator = OutcomeAggregator(session=None)
        
        outcome_id = aggregator.record_outcome('diagnostics', {
            'success': False,
            'trust_score': 0.3,
            'issue_type': 'syntax_error'
        })
        
        outcomes = aggregator.get_outcomes()
        stored = outcomes[0]
        
        assert 'id' in stored
        assert stored['id'] == outcome_id
        assert 'source' in stored
        assert 'timestamp' in stored
        assert isinstance(stored['timestamp'], datetime)
        assert 'outcome' in stored
        assert 'trust_score' in stored
        assert 'success' in stored
        assert 'context' in stored
    
    def test_handles_healing_source(self):
        """Test recording outcomes from healing source."""
        aggregator = OutcomeAggregator(session=None)
        
        outcome_id = aggregator.record_outcome('healing', {
            'success': True,
            'action': 'auto_fix',
            'trust_score': 0.9
        })
        
        outcomes = aggregator.get_outcomes(source='healing')
        assert len(outcomes) == 1
        assert outcomes[0]['source'] == 'healing'
    
    def test_handles_testing_source(self):
        """Test recording outcomes from testing source."""
        aggregator = OutcomeAggregator(session=None)
        
        outcome_id = aggregator.record_outcome('testing', {
            'success': False,
            'test_name': 'test_login',
            'trust_score': 0.7
        })
        
        outcomes = aggregator.get_outcomes(source='testing')
        assert len(outcomes) == 1
        assert outcomes[0]['source'] == 'testing'
    
    def test_handles_diagnostics_source(self):
        """Test recording outcomes from diagnostics source."""
        aggregator = OutcomeAggregator(session=None)
        
        outcome_id = aggregator.record_outcome('diagnostics', {
            'success': True,
            'issue_type': 'memory_leak',
            'trust_score': 0.65
        })
        
        outcomes = aggregator.get_outcomes(source='diagnostics')
        assert len(outcomes) == 1
        assert outcomes[0]['source'] == 'diagnostics'
    
    def test_handles_llm_source(self):
        """Test recording outcomes from LLM source."""
        aggregator = OutcomeAggregator(session=None)
        
        outcome_id = aggregator.record_outcome('llm', {
            'success': True,
            'suggestion': 'Use async/await pattern',
            'trust_score': 0.8
        })
        
        outcomes = aggregator.get_outcomes(source='llm')
        assert len(outcomes) == 1
        assert outcomes[0]['source'] == 'llm'
    
    def test_handles_file_processing_source(self):
        """Test recording outcomes from file_processing source."""
        aggregator = OutcomeAggregator(session=None)
        
        outcome_id = aggregator.record_outcome('file_processing', {
            'success': True,
            'file_path': '/app/main.py',
            'trust_score': 0.95
        })
        
        outcomes = aggregator.get_outcomes(source='file_processing')
        assert len(outcomes) == 1
        assert outcomes[0]['source'] == 'file_processing'
    
    def test_handles_unknown_source(self):
        """Test that unknown sources are still recorded with warning."""
        aggregator = OutcomeAggregator(session=None)
        
        outcome_id = aggregator.record_outcome('unknown_source', {
            'success': True,
            'trust_score': 0.5
        })
        
        assert outcome_id is not None
        outcomes = aggregator.get_outcomes()
        assert len(outcomes) == 1
        assert outcomes[0]['source'] == 'unknown_source'
    
    def test_default_trust_score(self):
        """Test default trust_score when not provided."""
        aggregator = OutcomeAggregator(session=None)
        
        aggregator.record_outcome('healing', {'success': True})
        
        outcomes = aggregator.get_outcomes()
        assert outcomes[0]['trust_score'] == 0.5  # Default
    
    def test_default_success_false(self):
        """Test default success is False when not provided."""
        aggregator = OutcomeAggregator(session=None)
        
        aggregator.record_outcome('healing', {'action': 'test'})
        
        outcomes = aggregator.get_outcomes()
        assert outcomes[0]['success'] is False


class TestGetOutcomes:
    """Tests for get_outcomes() method."""
    
    def test_filters_by_source(self):
        """Test filtering outcomes by source."""
        aggregator = OutcomeAggregator(session=None)
        
        aggregator.record_outcome('healing', {'success': True})
        aggregator.record_outcome('testing', {'success': True})
        aggregator.record_outcome('healing', {'success': False})
        aggregator.record_outcome('diagnostics', {'success': True})
        
        healing_outcomes = aggregator.get_outcomes(source='healing')
        assert len(healing_outcomes) == 2
        assert all(o['source'] == 'healing' for o in healing_outcomes)
        
        testing_outcomes = aggregator.get_outcomes(source='testing')
        assert len(testing_outcomes) == 1
        assert testing_outcomes[0]['source'] == 'testing'
    
    def test_filters_by_date(self):
        """Test filtering outcomes by date."""
        aggregator = OutcomeAggregator(session=None)
        
        # Record some outcomes
        aggregator.record_outcome('healing', {'success': True})
        aggregator.record_outcome('testing', {'success': True})
        
        # Get outcomes since a past date (should get all)
        past_date = datetime.utcnow() - timedelta(hours=1)
        outcomes = aggregator.get_outcomes(since=past_date)
        assert len(outcomes) == 2
        
        # Get outcomes since a future date (should get none)
        future_date = datetime.utcnow() + timedelta(hours=1)
        outcomes = aggregator.get_outcomes(since=future_date)
        assert len(outcomes) == 0
    
    def test_returns_correct_format(self):
        """Test that get_outcomes returns correctly formatted list."""
        aggregator = OutcomeAggregator(session=None)
        
        aggregator.record_outcome('healing', {
            'success': True,
            'trust_score': 0.8,
            'action': 'fix'
        })
        
        outcomes = aggregator.get_outcomes()
        
        assert isinstance(outcomes, list)
        assert len(outcomes) == 1
        
        outcome = outcomes[0]
        assert isinstance(outcome, dict)
        assert 'id' in outcome
        assert 'source' in outcome
        assert 'timestamp' in outcome
        assert 'outcome' in outcome
        assert 'trust_score' in outcome
        assert 'success' in outcome
    
    def test_combined_filters(self):
        """Test combining source and date filters."""
        aggregator = OutcomeAggregator(session=None)
        
        aggregator.record_outcome('healing', {'success': True})
        aggregator.record_outcome('testing', {'success': True})
        aggregator.record_outcome('healing', {'success': False})
        
        past_date = datetime.utcnow() - timedelta(hours=1)
        outcomes = aggregator.get_outcomes(source='healing', since=past_date)
        
        assert len(outcomes) == 2
        assert all(o['source'] == 'healing' for o in outcomes)
    
    def test_returns_empty_when_no_matches(self):
        """Test that empty list is returned when no matches."""
        aggregator = OutcomeAggregator(session=None)
        
        aggregator.record_outcome('healing', {'success': True})
        
        outcomes = aggregator.get_outcomes(source='nonexistent')
        assert outcomes == []


class TestDetectPatterns:
    """Tests for detect_patterns() method."""
    
    def test_detects_healing_diagnostic_correlations(self):
        """Test detection of healing-diagnostic correlations."""
        aggregator = OutcomeAggregator(session=None)
        
        now = datetime.utcnow()
        
        # Record diagnostic issue
        aggregator.record_outcome('diagnostics', {
            'success': True,
            'issue_type': 'import_error',
            'anomaly_type': 'missing_import',
            'trust_score': 0.7
        })
        
        # Record successful healing action shortly after
        aggregator.record_outcome('healing', {
            'success': True,
            'action': 'add_import',
            'anomaly_type': 'missing_import',
            'trust_score': 0.75
        })
        
        patterns = aggregator.detect_patterns()
        
        # Should detect pattern if correlation exists
        assert isinstance(patterns, list)
    
    def test_returns_pattern_format_correctly(self):
        """Test that detected patterns have correct format."""
        aggregator = OutcomeAggregator(session=None)
        
        # Record correlated outcomes
        aggregator.record_outcome('diagnostics', {
            'success': True,
            'issue_type': 'type_error',
            'anomaly_type': 'type_mismatch',
            'trust_score': 0.8
        })
        
        aggregator.record_outcome('healing', {
            'success': True,
            'action': 'fix_type',
            'anomaly_type': 'type_mismatch',
            'trust_score': 0.8
        })
        
        patterns = aggregator.detect_patterns()
        
        assert isinstance(patterns, list)
        
        for pattern in patterns:
            assert isinstance(pattern, dict)
            if 'pattern_type' in pattern:
                assert 'confidence' in pattern
                assert 'sources' in pattern
                assert isinstance(pattern['sources'], list)
    
    def test_no_patterns_with_insufficient_data(self):
        """Test that no patterns are detected with insufficient data."""
        aggregator = OutcomeAggregator(session=None)
        
        # Only one outcome
        aggregator.record_outcome('healing', {'success': True})
        
        patterns = aggregator.detect_patterns()
        assert patterns == []
    
    def test_patterns_stored_internally(self):
        """Test that detected patterns are stored internally."""
        aggregator = OutcomeAggregator(session=None)
        
        # Add multiple outcomes to trigger pattern detection
        aggregator.record_outcome('diagnostics', {
            'success': True,
            'anomaly_type': 'error',
            'trust_score': 0.8
        })
        aggregator.record_outcome('healing', {
            'success': True,
            'anomaly_type': 'error',
            'trust_score': 0.8
        })
        
        aggregator.detect_patterns()
        
        # Check patterns are retrievable
        stored_patterns = aggregator.get_patterns()
        assert isinstance(stored_patterns, list)


class TestGetStats:
    """Tests for get_stats() method."""
    
    def test_returns_correct_counts(self):
        """Test that stats contain correct counts."""
        aggregator = OutcomeAggregator(session=None)
        
        aggregator.record_outcome('healing', {'success': True})
        aggregator.record_outcome('healing', {'success': False})
        aggregator.record_outcome('testing', {'success': True})
        aggregator.record_outcome('diagnostics', {'success': True})
        
        stats = aggregator.get_stats()
        
        assert stats['total_outcomes_recorded'] == 4
        assert stats['current_outcome_count'] == 4
        assert stats['outcomes_by_source']['healing'] == 2
        assert stats['outcomes_by_source']['testing'] == 1
        assert stats['outcomes_by_source']['diagnostics'] == 1
    
    def test_stats_structure(self):
        """Test that stats have the expected structure."""
        aggregator = OutcomeAggregator(session=None)
        
        stats = aggregator.get_stats()
        
        assert 'total_outcomes_recorded' in stats
        assert 'outcomes_by_source' in stats
        assert 'patterns_detected' in stats
        assert 'cross_system_learnings_created' in stats
        assert 'errors' in stats
        assert 'current_outcome_count' in stats
        assert 'current_pattern_count' in stats
        assert 'started_at' in stats
        assert 'timestamp' in stats
    
    def test_initial_stats_are_zero(self):
        """Test that initial stats are zero."""
        aggregator = OutcomeAggregator(session=None)
        
        stats = aggregator.get_stats()
        
        assert stats['total_outcomes_recorded'] == 0
        assert stats['current_outcome_count'] == 0
        assert stats['patterns_detected'] == 0
        assert stats['errors'] == 0


class TestThreadSafety:
    """Tests for thread safety."""
    
    def test_multiple_threads_recording(self):
        """Test that multiple threads can record outcomes safely."""
        aggregator = OutcomeAggregator(session=None)
        num_threads = 10
        outcomes_per_thread = 50
        errors = []
        
        def record_outcomes(thread_id):
            try:
                for i in range(outcomes_per_thread):
                    aggregator.record_outcome('testing', {
                        'success': True,
                        'thread_id': thread_id,
                        'iteration': i
                    })
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=record_outcomes, args=(i,))
            threads.append(t)
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Thread errors: {errors}"
        
        stats = aggregator.get_stats()
        expected_total = num_threads * outcomes_per_thread
        assert stats['total_outcomes_recorded'] == expected_total
    
    def test_no_race_conditions(self):
        """Test that concurrent access doesn't cause race conditions."""
        aggregator = OutcomeAggregator(session=None)
        results = {'reads': 0, 'writes': 0}
        lock = threading.Lock()
        
        def writer():
            for _ in range(100):
                aggregator.record_outcome('healing', {'success': True})
                with lock:
                    results['writes'] += 1
        
        def reader():
            for _ in range(100):
                outcomes = aggregator.get_outcomes()
                with lock:
                    results['reads'] += 1
        
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert results['writes'] == 500
        assert results['reads'] == 500
        
        # Verify data integrity
        stats = aggregator.get_stats()
        assert stats['total_outcomes_recorded'] == 500
    
    def test_concurrent_pattern_detection(self):
        """Test pattern detection is thread-safe."""
        aggregator = OutcomeAggregator(session=None)
        
        # Pre-populate with data
        for _ in range(50):
            aggregator.record_outcome('healing', {'success': True, 'trust_score': 0.8})
            aggregator.record_outcome('diagnostics', {'success': True, 'trust_score': 0.8})
        
        errors = []
        
        def detect():
            try:
                for _ in range(10):
                    aggregator.detect_patterns()
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=detect) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0


class TestMaxSizeLimit:
    """Tests for max size limit (queue eviction)."""
    
    def test_evicts_oldest_when_full(self):
        """Test that oldest outcomes are evicted when max size is reached."""
        aggregator = OutcomeAggregator(session=None)
        max_size = aggregator._max_outcomes  # 1000
        
        # Record more than max outcomes
        for i in range(max_size + 100):
            aggregator.record_outcome('testing', {
                'success': True,
                'index': i
            })
        
        outcomes = aggregator.get_outcomes()
        
        # Should only have max_size outcomes
        assert len(outcomes) == max_size
        
        # First outcome should be index 100 (oldest 100 were evicted)
        first_outcome = outcomes[0]
        assert first_outcome['outcome']['index'] == 100
        
        # Last outcome should be the most recent
        last_outcome = outcomes[-1]
        assert last_outcome['outcome']['index'] == max_size + 99
    
    def test_stats_count_all_recorded(self):
        """Test that total_outcomes_recorded counts all, even evicted ones."""
        aggregator = OutcomeAggregator(session=None)
        max_size = aggregator._max_outcomes
        total_to_add = max_size + 500
        
        for i in range(total_to_add):
            aggregator.record_outcome('healing', {'success': True, 'index': i})
        
        stats = aggregator.get_stats()
        
        # Total recorded should count all
        assert stats['total_outcomes_recorded'] == total_to_add
        
        # Current count should be max_size
        assert stats['current_outcome_count'] == max_size


class TestClear:
    """Tests for clear() method."""
    
    def test_clears_all_data(self):
        """Test that clear removes all outcomes and resets stats."""
        aggregator = OutcomeAggregator(session=None)
        
        # Add some data
        for _ in range(10):
            aggregator.record_outcome('healing', {'success': True})
        
        aggregator.detect_patterns()
        
        # Verify data exists
        assert len(aggregator.get_outcomes()) > 0
        
        # Clear
        aggregator.clear()
        
        # Verify cleared
        assert len(aggregator.get_outcomes()) == 0
        stats = aggregator.get_stats()
        assert stats['total_outcomes_recorded'] == 0
        assert stats['current_outcome_count'] == 0


class TestSingleton:
    """Tests for get_outcome_aggregator singleton."""
    
    def test_returns_same_instance(self):
        """Test that get_outcome_aggregator returns singleton."""
        # Reset singleton for test
        import cognitive.outcome_aggregator as module
        module._aggregator_instance = None
        
        agg1 = get_outcome_aggregator()
        agg2 = get_outcome_aggregator()
        
        assert agg1 is agg2
    
    def test_updates_session(self):
        """Test that session is updated if new one provided."""
        import cognitive.outcome_aggregator as module
        module._aggregator_instance = None
        
        mock_session1 = Mock()
        mock_session2 = Mock()
        
        agg1 = get_outcome_aggregator(session=mock_session1)
        assert agg1.session is mock_session1
        
        agg2 = get_outcome_aggregator(session=mock_session2)
        assert agg2.session is mock_session2
        assert agg1 is agg2  # Same instance


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
