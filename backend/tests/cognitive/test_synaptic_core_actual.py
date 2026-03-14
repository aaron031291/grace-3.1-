import pytest
from unittest.mock import MagicMock, patch
from cognitive.synaptic_core import SynapticCore, get_synaptic_core

@patch("cognitive.synaptic_core.get_unified_memory")
def test_dispatch(mock_memory):
    core = SynapticCore()
    
    with patch("cognitive.synaptic_core.get_llm_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.generate.return_value = "Response text"
        mock_get_client.return_value = mock_client
        
        # Test basic dispatch
        res = core.dispatch("opus", "Hello")
        assert res == "Response text"
        mock_client.generate.assert_called_once()
        
    with patch("llm_orchestrator.factory._ollama_with_model") as mock_ollama:
        mock_client = MagicMock()
        mock_client.generate.return_value = "Ollama response"
        mock_ollama.return_value = mock_client
        
        # Test ollama dispatch
        res = core.dispatch("code", "Write code")
        assert res == "Ollama response"

@patch("cognitive.synaptic_core.get_unified_memory")
@patch("cognitive.synaptic_core.SynapticCore.dispatch")
def test_orchestrate_chain(mock_dispatch, mock_memory):
    core = SynapticCore()
    
    # Sequence of responses for each step
    mock_dispatch.side_effect = ["Step 1 output", "Step 2 output"]
    
    chain = [
        {"model": "kimi", "instruction": "Step 1"},
        {"model": "qwen", "instruction": "Step 2"}
    ]
    
    res = core.orchestrate_chain(chain, "Initial state")
    
    assert res["final_output"] == "Step 2 output"
    assert len(res["history"]) == 2
    assert res["history"][0]["output"] == "Step 1 output"

@patch("cognitive.synaptic_core.get_unified_memory")
def test_log_to_memory(mock_memory):
    core = SynapticCore()
    
    mock_mem_instance = MagicMock()
    mock_mem_instance.store_episode.return_value = True
    core.memory = mock_mem_instance
    
    res = core.log_to_memory("Problem", "Action", "Outcome", 0.9)
    assert res is True
    mock_mem_instance.store_episode.assert_called_once()

if __name__ == "__main__":
    pytest.main(['-v', __file__])
