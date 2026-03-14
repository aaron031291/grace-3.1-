import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from backend.cognitive.memory_mesh_integration import MemoryMeshIntegration

@pytest.fixture
def mock_session():
    return MagicMock()

def test_ingest_learning_experience(mock_session, tmp_path):
    import sys
    sys.modules["api._genesis_tracker"] = MagicMock()
    
    kb_path = tmp_path / "kb"
    
    integration = MemoryMeshIntegration(mock_session, kb_path)
    
    # Mock the internal components
    integration.learning_memory = MagicMock()
    mock_learning_example = MagicMock()
    mock_learning_example.trust_score = 0.9  # High trust to trigger episodic and procedural
    mock_learning_example.id = "lex-1"
    integration.learning_memory.ingest_learning_data.return_value = mock_learning_example
    
    integration.episodic_buffer = MagicMock()
    integration.procedural_repo = MagicMock()

    # Mock internal methods
    integration._add_to_episodic_memory = MagicMock()
    
    mock_episode = MagicMock()
    mock_episode.id = "ep-1"
    integration._add_to_episodic_memory.return_value = mock_episode
    
    integration._update_procedural_memory = MagicMock()
    mock_procedure = MagicMock()
    mock_procedure.id = "proc-1"
    integration._update_procedural_memory.return_value = mock_procedure

    # Execute
    context = {"goal": "test"}
    action = {"do": "something"}
    outcome = {"result": "ok"}
    
    res = integration.ingest_learning_experience(
        experience_type="success",
        context=context,
        action_taken=action,
        outcome=outcome,
        expected_outcome={"result": "ok"}
    )
    
    # Assert
    assert res == "lex-1"
    integration.learning_memory.ingest_learning_data.assert_called_once()
    integration._add_to_episodic_memory.assert_called_once()
    integration._update_procedural_memory.assert_called_once()
    assert mock_learning_example.episodic_episode_id == "ep-1"
    assert mock_learning_example.procedure_id == "proc-1"
    
def test_calculate_prediction_error(mock_session, tmp_path):
    integration = MemoryMeshIntegration(mock_session, tmp_path)
    
    actual = {"score": 5, "name": "test"}
    expected = {"score": 10, "name": "test"}
    
    err = integration._calculate_prediction_error(actual, expected)
    
    # score diff = 5 / max(10, 5) = 0.5
    # name diff = 0.0
    # avg = 0.25
    assert err == 0.25

if __name__ == "__main__":
    pytest.main(['-v', __file__])
