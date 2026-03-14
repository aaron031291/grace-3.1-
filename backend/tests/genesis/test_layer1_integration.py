import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from backend.genesis.layer1_integration import Layer1Integration

# Mock session for tests
@pytest.fixture
def mock_session():
    return MagicMock()

@pytest.fixture
def layer1(mock_session):
    with patch('backend.genesis.layer1_integration.get_data_pipeline') as mock_pipeline, \
         patch('backend.genesis.layer1_integration.get_genesis_service') as mock_genesis, \
         patch('backend.genesis.layer1_integration.MemoryMeshIntegration') as mock_mesh:
        
        # Setup mocks
        pipeline_inst = MagicMock()
        pipeline_inst.process_input.return_value = {"genesis_key_id": "gk-123"}
        mock_pipeline.return_value = pipeline_inst
        
        mesh_inst = MagicMock()
        mesh_inst.ingest_learning_experience.return_value = "mem-123"
        mock_mesh.return_value = mesh_inst

        # Use a temporary directory for layer1_base to avoid creating real folders
        with patch('os.makedirs'):
            l1 = Layer1Integration(mock_session)
            l1.layer1_base = "/tmp/fake_layer1"
            yield l1

def test_process_user_input(layer1):
    with patch('builtins.open', MagicMock()), patch('json.dump', MagicMock()):
        with patch.object(layer1, '_trigger_autonomous_actions') as mock_trigger:
            layer1.metadata = {"input_sources": {"user_inputs": 0}, "total_inputs": 0}
            result = layer1.process_user_input("hello world", "user-1", "chat")
            
            assert result["genesis_key_id"] == "gk-123"
            assert layer1.pipeline.process_input.called
            assert layer1.metadata["input_sources"]["user_inputs"] == 1
            mock_trigger.assert_called_once_with(result)

def test_process_file_upload(layer1):
    with patch('builtins.open', MagicMock()), patch('json.dump', MagicMock()), patch('os.makedirs'):
        with patch.object(layer1, '_trigger_autonomous_actions') as mock_trigger:
            layer1.metadata = {"input_sources": {"file_uploads": 0}, "total_inputs": 0}
            result = layer1.process_file_upload(b"fake data", "test.txt", "text/plain", "user-1")
            
            assert result["genesis_key_id"] == "gk-123"
            assert layer1.pipeline.process_input.called
            assert layer1.metadata["input_sources"]["file_uploads"] == 1
            mock_trigger.assert_called_once()

def test_process_learning_memory(layer1):
    with patch('builtins.open', MagicMock()), patch('json.dump', MagicMock()), patch('os.makedirs'):
        with patch.object(layer1, '_trigger_autonomous_actions') as mock_trigger:
            layer1.metadata = {"input_sources": {"learning_memory": 0}, "total_inputs": 0}
            
            learning_data = {"context": "test", "action": "test_act", "outcome": {"positive": True}}
            result = layer1.process_learning_memory("feedback", learning_data, "user-1")
            
            assert result["genesis_key_id"] == "gk-123"
            assert "memory_mesh" in result
            assert result["memory_mesh"]["learning_example_id"] == "mem-123"
            assert layer1.memory_mesh.ingest_learning_experience.called
            mock_trigger.assert_called_once()

if __name__ == "__main__":
    pytest.main(['-v', __file__])
