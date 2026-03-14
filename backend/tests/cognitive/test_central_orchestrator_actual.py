import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.central_orchestrator import CentralOrchestrator, SystemState

def test_system_state():
    state = SystemState()
    state.update("llm", {"status": "active"})
    res = state.get("llm")
    assert res["status"] == "active"
    assert "last_updated" in res
    
    state.add_task({"id": 1})
    tasks = state.get_active_tasks()
    assert len(tasks) == 1
    assert tasks[0]["id"] == 1

def test_singleton():
    c1 = CentralOrchestrator.get_instance()
    c2 = CentralOrchestrator.get_instance()
    assert c1 is c2

@patch("cognitive.event_bus.subscribe")
def test_initialize(mock_subscribe):
    orchestrator = CentralOrchestrator()
    orchestrator._event_handlers_registered = False
    
    with patch("backend.cognitive.central_orchestrator.CentralOrchestrator._sync_initial_state"):
        orchestrator.initialize()
        
    assert orchestrator._initialized is True
    assert mock_subscribe.called

def test_event_handlers():
    orchestrator = CentralOrchestrator()
    mock_event = MagicMock()
    mock_event.timestamp = "2026-01-01T00:00:00Z"
    mock_event.data = {"provider": "test_provider"}
    
    orchestrator._on_llm_called(mock_event)
    state = orchestrator.state.get("llm")
    assert state["status"] == "active"
    assert state["provider"] == "test_provider"

@patch("backend.cognitive.central_orchestrator.CentralOrchestrator._sync_initial_state")
def test_sync_state(mock_sync):
    orchestrator = CentralOrchestrator()
    orchestrator.state.update("test", {"value": 1})
    res = orchestrator.sync_state()
    assert "test" in res["components"]
    assert res["components"]["test"]["value"] == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
