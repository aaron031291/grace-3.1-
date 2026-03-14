import pytest
from unittest.mock import MagicMock, patch

from backend.cognitive.magma_bridge import (
    _get_magma,
    is_available,
    query_context,
    query_results,
    query_causal,
    ingest,
    store_pattern,
    store_decision,
    store_procedure,
    get_stats
)
import backend.cognitive.magma_bridge as mb

@pytest.fixture(autouse=True)
def reset_magma_state():
    mb._magma = None
    mb._available = None

def test_get_magma_unavailable():
    # If the import throws, it shouldn't crash
    import sys
    with patch.dict(sys.modules, {"cognitive.magma.grace_magma_system": None}):
        assert _get_magma() is None
        assert is_available() is False

def test_get_magma_available():
    mock_magma_obj = MagicMock()
    
    mock_system = MagicMock()
    mock_system.get_grace_magma.return_value = mock_magma_obj
    
    import sys
    with patch.dict(sys.modules, {"cognitive.magma.grace_magma_system": mock_system}):
        m = _get_magma()
        assert m is mock_magma_obj
        assert is_available() is True

def test_bridge_functions_skip_silently():
    # Calling functions when magma is unavailable should just do nothing / return defaults
    mb._available = False
    
    assert query_context("test") == ""
    assert query_results("test") == []
    assert query_causal("why") is None
    
    # these shouldn't crash
    ingest("some text")
    store_pattern("test", "test desc")
    store_decision("act", "target", "rationale")
    store_procedure("proc", "desc", ["step1"])
    
    assert get_stats() == {"available": False}

def test_bridge_functions_delegate():
    mock_magma_obj = MagicMock()
    mock_magma_obj.get_context.return_value = "hello"
    mock_magma_obj.query.return_value = [{"res": 1}]
    mock_magma_obj.why.return_value = "because"
    mock_magma_obj.get_stats.return_value = {"nodes": 5}
    
    mb._magma = mock_magma_obj
    mb._available = True
    
    assert query_context("x") == "hello"
    assert query_results("x") == [{"res": 1}]
    assert query_causal("x") == "because"
    assert get_stats() == {"available": True, "nodes": 5}
    
    ingest("txt")
    mock_magma_obj.ingest.assert_called_once()
    
    store_pattern("ptk", "ptv")
    mock_magma_obj.store_pattern.assert_called_once()
    
    store_decision("a", "t", "r")
    mock_magma_obj.store_decision.assert_called_once()

if __name__ == "__main__":
    pytest.main(['-v', __file__])
