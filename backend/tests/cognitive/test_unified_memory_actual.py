import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.unified_memory import UnifiedMemory, get_unified_memory, _coerce_dict

def test_singleton():
    mem1 = get_unified_memory()
    mem2 = get_unified_memory()
    assert mem1 is mem2

def test_coerce_dict():
    assert _coerce_dict({"a": 1}) == {"a": 1}
    assert _coerce_dict('{"a": 1}') == {"a": 1}
    assert _coerce_dict("just a string") == {"raw": "just a string"}
    assert _coerce_dict(None) == {}

@patch("backend.cognitive.unified_memory._get_session")
def test_store_episode(mock_session):
    mem = UnifiedMemory()
    db_session = MagicMock()
    mock_session.return_value = db_session
    
    # Mocking EpisodicBuffer would be needed here to avoid DB operations
    with patch("cognitive.episodic_memory.EpisodicBuffer") as MockBuffer:
        res = mem.store_episode("prob", "act", "out", 0.9, "test")
        assert res is True
        MockBuffer.return_value.record_episode.assert_called_once()
    
    db_session.close.assert_called_once()

@patch("backend.cognitive.unified_memory._get_session")
def test_store_learning(mock_session):
    mem = UnifiedMemory()
    db_session = MagicMock()
    mock_session.return_value = db_session
    
    with patch("cognitive.learning_memory.LearningMemoryManager") as MockMgr:
        res = mem.store_learning("context", "exp", "act", 0.9, "test")
        assert res is True
        MockMgr.return_value.ingest_learning_data.assert_called_once()
        
    db_session.close.assert_called_once()

if __name__ == "__main__":
    pytest.main(['-v', __file__])
