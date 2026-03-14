import pytest
import asyncio
from unittest.mock import MagicMock, patch
from backend.genesis.autonomous_engine import (
    AutonomousEngine, ActionType, ActionContext, TriggerType, ActionPriority
)

@pytest.fixture
def mock_engine():
    with patch('backend.genesis.autonomous_engine.get_genesis_key_service', return_value=None), \
         patch('backend.genesis.autonomous_engine.get_mirror_system', return_value=None), \
         patch('backend.genesis.autonomous_engine.get_cognitive_engine', return_value=None), \
         patch('backend.genesis.autonomous_engine.get_kpi_tracker', return_value=None):
        engine = AutonomousEngine()
        yield engine

@pytest.mark.asyncio
async def test_queue_action(mock_engine):
    engine = mock_engine
    context = ActionContext(source="test", trigger_type=TriggerType.EVENT)
    
    action = await engine.queue_action(
        action_type=ActionType.HEALTH_CHECK,
        context=context,
        priority=ActionPriority.NORMAL
    )
    
    assert action.id in engine.actions
    assert engine.action_queue[ActionPriority.NORMAL].qsize() == 1

@pytest.mark.asyncio
async def test_execute_action_success(mock_engine):
    engine = mock_engine
    
    # Mock handler
    handler_mock = MagicMock()
    handler_mock.return_value = asyncio.Future()
    handler_mock.return_value.set_result({"status": "ok"})
    engine.handlers[ActionType.HEALTH_CHECK] = handler_mock
    
    context = ActionContext(source="test", trigger_type=TriggerType.EVENT)
    action = await engine.queue_action(ActionType.HEALTH_CHECK, context)
    
    res = await engine.execute_action(action)
    
    assert res.status == "success"
    assert res.output == {"status": "ok"}
    assert action.status == "completed"

@pytest.mark.asyncio
async def test_execute_action_failure(mock_engine):
    engine = mock_engine
    
    # Mock handler to raise
    async def failing_handler(*args):
        raise ValueError("test error")
        
    engine.handlers[ActionType.HEALTH_CHECK] = failing_handler
    
    context = ActionContext(source="test", trigger_type=TriggerType.EVENT)
    action = await engine.queue_action(ActionType.HEALTH_CHECK, context)
    
    res = await engine.execute_action(action)
    
    assert res.status == "failed"
    assert "test error" in res.error
    assert action.status == "failed"

@pytest.mark.asyncio
async def test_emit_event(mock_engine):
    engine = mock_engine
    
    # Let's emit 'file_created' which is in our default rules
    await engine.emit_event("file_created", {"file_path": "test.txt"})
    
    # Should have queued INGEST_FILE
    # Priority is NORMAL
    assert engine.action_queue[ActionPriority.NORMAL].qsize() > 0

def test_get_status(mock_engine):
    engine = mock_engine
    status = engine.get_status()
    assert "running" in status
    assert "stats" in status

if __name__ == "__main__":
    pytest.main(['-v', __file__])
