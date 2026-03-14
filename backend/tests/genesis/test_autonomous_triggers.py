import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from backend.genesis.autonomous_triggers import GenesisTriggerPipeline
from models.genesis_key_models import GenesisKey, GenesisKeyType

@pytest.fixture
def mock_orchestrator():
    orchestrator = MagicMock()
    orchestrator.submit_study_task.return_value = "task-123"
    orchestrator.submit_practice_task.return_value = "task-456"
    return orchestrator

@pytest.fixture
def pipeline(mock_orchestrator):
    with patch('backend.genesis.autonomous_triggers.initialize_session_factory'):
        pl = GenesisTriggerPipeline(knowledge_base_path=Path("/tmp/kb"))
        pl.set_orchestrator(mock_orchestrator)
        return pl

@patch('backend.genesis.autonomous_triggers.GenesisTriggerPipeline._should_trigger_mirror_analysis')
def test_on_genesis_key_created_file_operation(mock_mirror_check, pipeline, mock_orchestrator):
    mock_mirror_check.return_value = False
    
    gk = GenesisKey(
        key_id="GK-1",
        key_type=GenesisKeyType.FILE_OPERATION,
        context_data={
            "operation_type": "modify",
            "file_path": "backend/api/users.py"
        }
    )
    
    result = pipeline.on_genesis_key_created(gk)
    
    assert result["triggered"] is True
    assert len(result["actions_triggered"]) == 1
    
    action = result["actions_triggered"][0]
    assert action["action"] == "autonomous_study"
    topic = action.get("topic", "")
    assert "users.py" in topic or "Backend" in topic or "Api" in topic or "API" in topic
    
    mock_orchestrator.submit_study_task.assert_called_once()

@patch('backend.genesis.autonomous_triggers.GenesisTriggerPipeline._should_trigger_mirror_analysis')
def test_handle_user_input(mock_mirror_check, pipeline, mock_orchestrator):
    mock_mirror_check.return_value = False
    
    gk = GenesisKey(
        key_id="GK-2",
        key_type=GenesisKeyType.USER_INPUT,
        context_data={
            "input_text": "How do I build a react frontend?"
        }
    )
    
    result = pipeline.on_genesis_key_created(gk)
    
    assert result["triggered"] is True
    assert result["actions_triggered"][0]["action"] == "predictive_prefetch"
    mock_orchestrator.submit_study_task.assert_called()

@patch('backend.genesis.autonomous_triggers.GenesisTriggerPipeline._should_trigger_mirror_analysis')
def test_handle_practice_outcome_recursive(mock_mirror_check, pipeline, mock_orchestrator):
    mock_mirror_check.return_value = False
    
    gk = GenesisKey(
        key_id="GK-3",
        key_type=GenesisKeyType.PRACTICE_OUTCOME,
        user_id="U-1",
        context_data={
            "success": False,
            "skill_name": "python",
            "feedback": "Syntax error"
        }
    )
    
    # We need to mock the session adding logic for the GAP_IDENTIFIED key
    with patch.object(pipeline, 'session_factory') as mock_factory:
        mock_session = MagicMock()
        mock_factory.return_value = mock_session
        
        result = pipeline.on_genesis_key_created(gk)
        
        assert result["triggered"] is True
        assert result["actions_triggered"][0]["action"] == "recursive_gap_analysis"
        assert result["actions_triggered"][0]["recursive_loop"] is True
        
        mock_session.add.assert_called()
        mock_session.commit.assert_called()

def test_is_learning_file(pipeline):
    assert pipeline._is_learning_file("src/main.py") is True
    assert pipeline._is_learning_file("src/main.txt") is True
    assert pipeline._is_learning_file("node_modules/index.js") is False
    assert pipeline._is_learning_file("binary.exe") is False

if __name__ == "__main__":
    pytest.main(['-v', __file__])
