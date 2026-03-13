import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from backend.cognitive.central_orchestrator import CentralOrchestrator, SystemState, get_orchestrator
import sys

# Pre-mock the event_bus module before anything tries to import it
sys.modules['cognitive.event_bus'] = MagicMock()
sys.modules['backend.cognitive.event_bus'] = MagicMock()

@pytest.fixture(autouse=True)
def mock_event_bus():
    # Provide a clean mock for each test
    sys.modules['cognitive.event_bus'] = MagicMock()
    sys.modules['backend.cognitive.event_bus'] = MagicMock()
    yield sys.modules['backend.cognitive.event_bus']

def test_central_orchestrator_initialization(mock_event_bus):
    orchestrator = CentralOrchestrator()
    assert not orchestrator._initialized
    assert not orchestrator._event_handlers_registered

    # The initialization tries to sync state from other systems, so mock them
    with patch.object(orchestrator, '_sync_initial_state'):
        orchestrator.initialize()

        assert orchestrator._initialized
        assert orchestrator._event_handlers_registered

def test_central_orchestrator_singleton():
    orch1 = get_orchestrator()
    orch2 = get_orchestrator()
    assert orch1 is orch2

def test_system_state_updates():
    state = SystemState()
    
    state.update("llm", {"status": "active", "provider": "test_provider"})
    
    llm_state = state.get("llm")
    assert llm_state["status"] == "active"
    assert llm_state["provider"] == "test_provider"
    assert "last_updated" in llm_state

def test_system_state_task_management():
    state = SystemState()
    
    test_task = {"id": 1, "type": "test_task"}
    state.add_task(test_task)
    
    tasks = state.get_active_tasks()
    assert len(tasks) == 1
    assert tasks[0]["id"] == 1

def test_route_task_publish(mock_event_bus):
    orchestrator = CentralOrchestrator()
    
    # Needs to be mocked since the router imports internal modules inside the method
    with patch('backend.cognitive.event_bus.publish') as mock_publish:
        result = orchestrator.route_task("code_generation", {"prompt": "write a function"})
        
        assert result["routed_to"] == "pipeline"
        assert result["task_type"] == "code_generation"
        
        # Verify the task was added to state
        tasks = orchestrator.state.get_active_tasks()
        assert len(tasks) > 0
        assert tasks[-1]["type"] == "code_generation"
        assert tasks[-1]["target"] == "pipeline"

def test_event_handlers():
    orchestrator = CentralOrchestrator()
    
    # Create a mock event object matching the expected structure
    class MockEvent:
        def __init__(self, topic, data):
            self.topic = topic
            self.data = data
            self.timestamp = datetime.utcnow().isoformat()
            
    # Test LLM Called event
    event = MockEvent("llm.called", {"provider": "openai"})
    orchestrator._on_llm_called(event)
    
    llm_state = orchestrator.state.get("llm")
    assert llm_state["status"] == "active"
    assert llm_state["provider"] == "openai"
    
    # Test Genesis Event
    genesis_event = MockEvent("genesis.key_created", {})
    orchestrator._on_genesis_event(genesis_event)
    
    genesis_state = orchestrator.state.get("genesis")
    assert genesis_state["total_keys"] == 1
    
    # Hit it again to test key increment
    orchestrator._on_genesis_event(genesis_event)
    genesis_state = orchestrator.state.get("genesis")
    assert genesis_state["total_keys"] == 2
