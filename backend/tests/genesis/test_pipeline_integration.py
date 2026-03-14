import pytest
import os
import json
from unittest.mock import MagicMock, patch
from backend.genesis.pipeline_integration import DataPipeline
from models.genesis_key_models import GenesisKeyType

@pytest.fixture
def temp_pipeline(tmp_path):
    with patch('backend.genesis.pipeline_integration.get_genesis_service') as mock_gk, \
         patch('backend.genesis.pipeline_integration.get_symbiotic_version_control') as mock_vc, \
         patch('backend.genesis.pipeline_integration.get_kb_integration') as mock_kb:
        
        mock_gk_instance = MagicMock()
        mock_key = MagicMock()
        mock_key.key_id = "gk-123"
        mock_key.key_type = GenesisKeyType.USER_INPUT
        mock_key.what_description = "Test description"
        mock_gk_instance.create_key.return_value = mock_key
        mock_gk.return_value = mock_gk_instance
        
        mock_vc_instance = MagicMock()
        mock_vc_instance.track_file_change.return_value = {
            "version_key_id": "vk-1",
            "version_number": 1
        }
        mock_vc.return_value = mock_vc_instance
        
        mock_kb_instance = MagicMock()
        mock_kb.return_value = mock_kb_instance
        
        # We need to mock the path where metadata is stored so we don't pollute real directory
        with patch('backend.genesis.pipeline_integration.Path') as mock_path:
            mock_path_obj = MagicMock()
            mock_path_obj.parent.parent.__truediv__.return_value = tmp_path / "metadata.json"
            mock_path.return_value = mock_path_obj
            
            # Since the class does Path(__file__).parent.parent we need to wrap that up
            
            pipeline = DataPipeline()
            # Override paths to tmp_path for safety
            pipeline.pipeline_metadata_file = str(tmp_path / ".genesis_pipeline_metadata.json")
            
            # Re-initialize to ensure metadata loaded from tmp_path
            pipeline._load_or_create_metadata()
            yield pipeline, tmp_path

def test_process_input_no_file(temp_pipeline):
    pipeline, tmp_path = temp_pipeline
    
    # Needs a bit more path mocking for immutable files
    with patch('backend.genesis.pipeline_integration.Path') as mock_path:
        mock_path_obj = MagicMock()
        def path_join(s):
            return tmp_path / s
        mock_path_obj.parent.parent.__truediv__.side_effect = path_join
        mock_path.return_value = mock_path_obj
        mock_path.parent.parent = tmp_path
        
        result = pipeline.process_input(
            input_data="Hello AI",
            input_type="user_input",
            user_id="u1"
        )
        
        assert result["complete"] is True
        assert result["stages"]["layer_1_input"]["status"] == "completed"
        assert result["stages"]["genesis_key"]["status"] == "completed"
        assert result["stages"]["version_control"]["status"] == "skipped"
        assert result["stages"]["librarian"]["status"] == "completed"
        assert result["stages"]["rag"]["status"] == "completed"
        assert result["stages"]["world_model"]["status"] == "completed"
        
        # Check files were created
        assert os.path.exists(tmp_path / ".genesis_immutable_pipeline.json")
        assert os.path.exists(tmp_path / ".genesis_rag_index.json")

def test_process_input_with_file(temp_pipeline):
    pipeline, tmp_path = temp_pipeline
    
    with patch('backend.genesis.pipeline_integration.Path') as mock_path:
        mock_path_obj = MagicMock()
        def path_join(s):
            return tmp_path / s
        mock_path_obj.parent.parent.__truediv__.side_effect = path_join
        mock_path.return_value = mock_path_obj
        
        result = pipeline.process_input(
            input_data=b"File content",
            input_type="file_change",
            user_id="u1",
            file_path="src/main.py"
        )
        
        assert result["complete"] is True
        assert result["stages"]["version_control"]["status"] == "completed"
        assert pipeline.symbiotic_vc.track_file_change.called

def test_pipeline_stats(temp_pipeline):
    pipeline, tmp_path = temp_pipeline
    
    stats = pipeline.get_pipeline_stats()
    assert stats["total_inputs_processed"] == 0
    assert not stats["pipeline_complete"]

if __name__ == "__main__":
    pytest.main(['-v', __file__])
