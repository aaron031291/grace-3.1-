import pytest
import time
from backend.genesis.realtime import GenesisRealtimeEngine

@pytest.fixture
def engine():
    return GenesisRealtimeEngine()

def test_on_key_created(engine):
    engine.on_key_created("test", "test action")
    assert engine._stats["total_events"] == 1
    recent = engine.get_recent(1)
    assert len(recent) == 1
    assert recent[0]["key_type"] == "test"
    assert recent[0]["is_error"] is False

def test_error_tracking(engine):
    engine.on_key_created("error_type", "error action", is_error=True)
    assert engine._stats["total_errors"] == 1
    recent = engine.get_recent(1, errors_only=True)
    assert len(recent) == 1
    assert recent[0]["is_error"] is True

def test_watchers(engine):
    events_caught = []
    
    def on_event(event):
        events_caught.append(event)
        
    engine.watch("test", on_event)
    engine.on_key_created("test", "test action")
    engine.on_key_created("other", "other action")
    
    assert len(events_caught) == 1
    assert events_caught[0]["key_type"] == "test"

def test_error_watchers(engine):
    error_caught = []
    def on_err(event):
        error_caught.append(event)
        
    engine.watch("__error__", on_err)
    engine.on_key_created("test", "test action", is_error=True)
    
    assert len(error_caught) == 1

def test_alerts(engine):
    # Alter rules to trigger immediately
    engine._alert_rules = [
        {"type": "error_spike", "threshold": 2, "window_seconds": 60, "severity": 0.8}
    ]
    
    engine.on_key_created("test", "err1", is_error=True)
    engine.on_key_created("test", "err2", is_error=True)
    
    alerts = engine.get_alerts()
    assert len(alerts) > 0
    assert alerts[0]["type"] == "error_spike"

def test_stream_stats(engine):
    engine.on_key_created("test", "action")
    stats = engine.get_stream_stats(window_seconds=60)
    assert stats["total_events"] == 1
    assert stats["error_rate"] == 0.0

if __name__ == "__main__":
    pytest.main(['-v', __file__])
