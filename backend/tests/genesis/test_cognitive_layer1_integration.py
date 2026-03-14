import pytest
from unittest.mock import MagicMock, patch
from backend.genesis.cognitive_layer1_integration import CognitiveLayer1Integration

@pytest.fixture
def cognitive_layer1():
    with patch('backend.genesis.cognitive_layer1_integration.Layer1Integration') as mock_layer1:
        mock_l1_instance = MagicMock()
        mock_l1_instance.process_user_input.return_value = {"status": "success", "genesis_key": "gk-1"}
        mock_l1_instance.process_file_upload.return_value = {"status": "success", "genesis_key": "gk-2"}
        mock_l1_instance.process_external_api.return_value = {"status": "success", "genesis_key": "gk-3"}
        mock_layer1.return_value = mock_l1_instance
        
        # Also need to patch CognitiveEngine so tests don't break if cognitive engine has missing deps
        with patch('backend.genesis.cognitive_layer1_integration.CognitiveEngine') as mock_engine:
            mock_engine_instance = MagicMock()
            
            # mock act to just call the function so we test the wrapper
            def side_effect_act(context, action, dry_run=False):
                return action()
            mock_engine_instance.act.side_effect = side_effect_act
            mock_engine_instance.begin_decision.return_value = MagicMock(decision_id="dec-1")
            mock_engine.return_value = mock_engine_instance
            
            with patch('backend.genesis.cognitive_layer1_integration.DecisionLogger'):
                yield CognitiveLayer1Integration()

def test_process_user_input(cognitive_layer1):
    result = cognitive_layer1.process_user_input(
        user_input="hello", 
        user_id="u1", 
        input_type="chat"
    )
    
    assert result["status"] == "success"
    assert "cognitive" in result
    assert result["cognitive"]["decision_id"] == "dec-1"
    
    cognitive_layer1.layer1.process_user_input.assert_called_once_with(
        user_input="hello", 
        user_id="u1", 
        input_type="chat",
        metadata=None
    )
    cognitive_layer1.cognitive_engine.begin_decision.assert_called_once()
    cognitive_layer1.cognitive_engine.finalize_decision.assert_called_once()

def test_process_file_upload(cognitive_layer1):
    result = cognitive_layer1.process_file_upload(
        file_content=b"data", 
        file_name="test.txt", 
        file_type="text", 
        user_id="u1"
    )
    
    assert result["status"] == "success"
    assert result["cognitive"]["irreversible_operation"] is True
    
    cognitive_layer1.layer1.process_file_upload.assert_called_once()
    cognitive_layer1.cognitive_engine.begin_decision.assert_called_once()

def test_process_external_api(cognitive_layer1):
    result = cognitive_layer1.process_external_api(
        api_name="github",
        api_endpoint="/repos",
        api_data={"data": 123}
    )
    assert result["status"] == "success"
    cognitive_layer1.layer1.process_external_api.assert_called_once()

if __name__ == "__main__":
    pytest.main(['-v', __file__])
