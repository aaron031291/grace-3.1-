import pytest
import threading
from unittest.mock import patch, MagicMock
from backend.self_healing.trigger_fabric import (
    start, 
    _wire_event_bus_triggers,
    _probe_tcp,
    _on_llm_error,
    _on_rate_limited,
    _started
)

def test_probe_tcp():
    # Should fail fast for a port we know is not listening
    assert _probe_tcp("localhost", 1, timeout=0.1) is False
    
def test_wire_event_bus_triggers():
    import sys
    sys.modules['cognitive.event_bus'] = MagicMock()
    
    # Reload the module to use the mock
    import importlib
    import backend.self_healing.trigger_fabric as tf
    importlib.reload(tf)
    
    tf._wire_event_bus_triggers()
    
    assert sys.modules["cognitive.event_bus"].subscribe.call_count >= 9

@patch("backend.self_healing.trigger_fabric._route_exception")
def test_on_llm_error_routes_properly(mock_route):
    data = {"provider": "Ollama", "error": "Connection reset by peer"}
    _on_llm_error(data)
    
    mock_route.assert_called_once()
    args, kwargs = mock_route.call_args
    
    assert "Ollama" in str(args[0])
    assert kwargs["module"] == "llm_orchestrator"
    assert kwargs["function"] == "Ollama"

def test_on_rate_limited_tracks_genesis():
    import sys
    sys.modules['api._genesis_tracker'] = MagicMock()
    
    # Reload the module to use the mock
    import importlib
    import backend.self_healing.trigger_fabric as tf
    importlib.reload(tf)
    
    data = {"service": "OpenAI", "error": "429 Too Many Requests"}
    
    tf._on_rate_limited(data)
    
    sys.modules['api._genesis_tracker'].track.assert_called_once()
    kwargs = sys.modules['api._genesis_tracker'].track.call_args[1]
    
    assert kwargs["key_type"] == "system_event"
    assert "Rate limit" in kwargs["what_description"]
    assert kwargs["context_data"] == data

@patch("backend.self_healing.trigger_fabric.threading.Thread")
@patch("backend.self_healing.trigger_fabric._wire_fastapi_middleware")
@patch("backend.self_healing.trigger_fabric._wire_ouroboros_code_action")
def test_start_fabric_idempotent(mock_ouroboros, mock_middleware, mock_thread):
    import backend.self_healing.trigger_fabric as tf
    
    # Reset lock for test
    tf._started = False
    
    app_mock = MagicMock()
    start(app_mock)
    
    assert tf._started is True
    assert mock_thread.call_count >= 3  # Network, mirror, mttr loops (and potentially others)
    mock_middleware.assert_called_once_with(app_mock)
    
    # Calling start again should do nothing
    start(app_mock)
    assert mock_middleware.call_count == 1  # No new calls


if __name__ == "__main__":
    pytest.main(['-v', __file__])
