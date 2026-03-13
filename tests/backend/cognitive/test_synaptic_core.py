import sys
from unittest.mock import MagicMock, patch

# Mock out problematic dependencies that trigger huggingface_hub errors on import during test collection
sys.modules['embedding.embedder'] = MagicMock()
sys.modules['backend.embedding.embedder'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()

import pytest
from backend.cognitive.synaptic_core import SynapticCore

@patch("backend.cognitive.synaptic_core.get_unified_memory")
@patch("backend.cognitive.synaptic_core.get_llm_client")
@patch("backend.llm_orchestrator.factory._ollama_with_model", create=True)
def test_synaptic_core_dispatch(mock_ollama, mock_get_client, mock_get_memory):
    mock_memory_instance = MagicMock()
    mock_get_memory.return_value = mock_memory_instance
    
    mock_client_instance = MagicMock()
    mock_client_instance.generate.return_value = "Mocked LLM Response"
    mock_get_client.return_value = mock_client_instance
    
    core = SynapticCore()
    
    # Test valid dispatch
    response = core.dispatch(model_id="runpod", prompt="Hello", system_prompt="Sys")
    assert response == "Mocked LLM Response"
    mock_client_instance.generate.assert_called_once_with(
        prompt="Hello",
        system_prompt="Sys",
        temperature=0.4,
        max_tokens=4096
    )

@patch("backend.cognitive.synaptic_core.get_unified_memory")
@patch("backend.cognitive.synaptic_core.get_llm_client")
def test_synaptic_core_orchestrate_chain(mock_get_client, mock_get_memory):
    mock_memory_instance = MagicMock()
    mock_get_memory.return_value = mock_memory_instance
    
    mock_client_instance = MagicMock()
    mock_client_instance.generate.side_effect = ["Step 1 Output", "Step 2 Output"]
    mock_get_client.return_value = mock_client_instance
    
    core = SynapticCore()
    
    with patch.object(core, 'dispatch', side_effect=["Step 1 Output", "Step 2 Output"]) as mock_dispatch:
        chain_def = [
            {"model": "qwen", "instruction": "Step 1"},
            {"model": "opus", "instruction": "Step 2"}
        ]
        
        result = core.orchestrate_chain(chain_definition=chain_def, initial_state="Start")
        
        assert result["final_output"] == "Step 2 Output"
        assert len(result["history"]) == 2
        assert mock_dispatch.call_count == 2
        
        first_call = mock_dispatch.call_args_list[0]
        assert "Start" in first_call.kwargs["prompt"]
        assert "Step 1" in first_call.kwargs["prompt"]
        
        second_call = mock_dispatch.call_args_list[1]
        assert "Step 1 Output" in second_call.kwargs["prompt"]
        assert "Step 2" in second_call.kwargs["prompt"]

@patch("backend.cognitive.synaptic_core.get_unified_memory")
def test_synaptic_core_log_to_memory(mock_get_memory):
    mock_memory_instance = MagicMock()
    mock_memory_instance.store_episode.return_value = True
    mock_get_memory.return_value = mock_memory_instance
    
    core = SynapticCore()
    success = core.log_to_memory(
        problem="Test Problem",
        action="Chain logic",
        outcome="Test Outcome",
        trust=0.9
    )
    
    assert success is True
    mock_memory_instance.store_episode.assert_called_once()
    kwargs = mock_memory_instance.store_episode.call_args.kwargs
    assert kwargs["problem"] == "Test Problem"
    assert kwargs["action"] == {"orchestration_chain": "Chain logic"}
    assert kwargs["trust"] == 0.9
