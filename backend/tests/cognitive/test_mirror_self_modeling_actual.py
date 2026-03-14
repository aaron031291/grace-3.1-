import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from backend.cognitive.mirror_self_modeling import MirrorSelfModelingSystem, PatternType

class DummyGenesisKey:
    def __init__(self, key_type, created_at, context_data=None, description=""):
        self.key_type = key_type
        self.created_at = created_at
        self.context_data = context_data or {}
        self.what_description = description
        self.key_id = "gk_123"

class DummyEnum:
    def __init__(self, value):
        self.value = value
    def __eq__(self, other):
        return self.value == other.value

def test_mirror_observation(monkeypatch):
    session_mock = MagicMock()
    
    now = datetime.now(timezone.utc)
    # mock keys
    k1 = DummyGenesisKey(DummyEnum("error"), now)
    k2 = DummyGenesisKey(DummyEnum("success"), now)
    
    query_mock = MagicMock()
    filter_mock = MagicMock()
    order_mock = MagicMock()
    order_mock.all.return_value = [k1, k2]
    filter_mock.order_by.return_value = order_mock
    query_mock.filter.return_value = filter_mock
    session_mock.query.return_value = query_mock
    
    mirror = MirrorSelfModelingSystem(session=session_mock)
    
    obs = mirror.observe_recent_operations()
    assert obs["total_operations"] == 2
    assert "error" in obs["operations_by_type"]

def test_mirror_detect_failures(monkeypatch):
    session_mock = MagicMock()
    
    now = datetime.now(timezone.utc)
    
    # 3 failures on same topic to trigger repeated failure
    failures = [
        DummyGenesisKey(DummyEnum("error"), now, {"topic": "DB_CONNECTION"}),
        DummyGenesisKey(DummyEnum("error"), now, {"topic": "DB_CONNECTION"}),
        DummyGenesisKey(DummyEnum("error"), now, {"topic": "DB_CONNECTION"})
    ]
    
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.all.return_value = failures
    query_mock.filter.return_value = filter_mock
    session_mock.query.return_value = query_mock
    
    mirror = MirrorSelfModelingSystem(session=session_mock, min_pattern_occurrences=3)
    
    patterns = mirror._detect_repeated_failures()
    assert len(patterns) == 1
    assert patterns[0]["pattern_type"] == PatternType.REPEATED_FAILURE
    assert patterns[0]["topic"] == "DB_CONNECTION"

def test_mirror_build_self_model(monkeypatch):
    session_mock = MagicMock()
    
    # Mock observe_recent_operations
    monkeypatch.setattr(MirrorSelfModelingSystem, "observe_recent_operations", lambda s: {
        "total_operations": 10,
        "operations_by_type": {}
    })
    
    # Mock detect_behavioral_patterns
    monkeypatch.setattr(MirrorSelfModelingSystem, "detect_behavioral_patterns", lambda s: [
        {"pattern_type": PatternType.REPEATED_FAILURE, "topic": "API", "occurrences": 3, "recommendation": "fix API"}
    ])
    
    # Mock _analyze_learning_progress
    monkeypatch.setattr(MirrorSelfModelingSystem, "_analyze_learning_progress", lambda s: {
        "total_examples": 5,
        "avg_confidence": 0.8,
        "success_rate": 0.6,
        "topics_studied": 2
    })
    
    mirror = MirrorSelfModelingSystem(session=session_mock)
    model = mirror.build_self_model()
    
    assert model["operations_observed"] == 10
    assert model["behavioral_patterns"]["total_detected"] == 1
    assert "improvement_suggestions" in model
    assert len(model["improvement_suggestions"]) == 1
    assert model["improvement_suggestions"][0]["topic"] == "API"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
