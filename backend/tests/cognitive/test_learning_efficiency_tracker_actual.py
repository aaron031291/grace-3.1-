import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.learning_efficiency_tracker import LearningEfficiencyTracker
from datetime import timedelta

def test_record_data_consumption():
    session = MagicMock()
    session.query.return_value.count.return_value = 0
    tracker = LearningEfficiencyTracker(session=session)
    
    # Check initial
    tracker.record_data_consumption(bytes_consumed=1024, documents_consumed=2, chunks_consumed=10)
    
    assert tracker.total_bytes_consumed == 1024
    assert tracker.total_documents_consumed == 2
    assert tracker.total_chunks_consumed == 10

def test_record_insight():
    session = MagicMock()
    session.query.return_value.count.return_value = 0
    tracker = LearningEfficiencyTracker(session=session)
    
    insight = tracker.record_insight(
        insight_type="pattern",
        description="test insight",
        trust_score=0.8
    )
    
    assert insight.insight_type == "pattern"
    assert len(tracker.insights) == 1
    assert tracker.last_insight_time is not None

def test_get_efficiency_metrics():
    session = MagicMock()
    session.query.return_value.count.return_value = 0
    tracker = LearningEfficiencyTracker(session=session)
    
    # Record some data and insights
    tracker.record_data_consumption(bytes_consumed=2048, documents_consumed=1, chunks_consumed=5)
    
    insight1 = tracker.record_insight(
        insight_type="concept",
        description="concept 1",
        trust_score=0.9,
        time_to_insight=timedelta(seconds=60)
    )
    
    metrics = tracker.get_efficiency_metrics()
    
    assert metrics.bytes_per_insight > 0
    assert metrics.seconds_per_insight == 60.0

if __name__ == "__main__":
    pytest.main(['-v', __file__])
