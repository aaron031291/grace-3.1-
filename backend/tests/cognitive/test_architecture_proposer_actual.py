import pytest
import sys
from unittest.mock import MagicMock
from backend.cognitive.architecture_proposer import ArchitectureProposer

# Mock the entire architecture compass module
mock_ac = MagicMock()
mock_compass = MagicMock()
mock_compass.find_for.return_value = ["api/brain_api_v2.py"]
mock_compass.diagnose.return_value = {"total_components": 150}
mock_ac.get_compass.return_value = mock_compass
sys.modules["cognitive.architecture_compass"] = mock_ac

# Mock the LLM factory
mock_factory = MagicMock()
mock_llm = MagicMock()
mock_llm.generate.return_value = '{"need_score": 9.5, "connections": ["cognitive/pipeline.py"], "value_proposition": "test"}'
mock_factory.get_llm_for_task.return_value = mock_llm
mock_factory.get_llm_client.return_value = mock_llm
sys.modules["llm_orchestrator.factory"] = mock_factory

# Mock event bus
mock_eb = MagicMock()
sys.modules["cognitive.event_bus"] = mock_eb

# Mock hunter assimilator
mock_ha = MagicMock()
mock_hunter = MagicMock()
mock_hunter_result = MagicMock()
mock_hunter_result.request_id = "req_123"
mock_hunter.assimilate.return_value = mock_hunter_result
mock_ha.get_hunter.return_value = mock_hunter
sys.modules["cognitive.hunter_assimilator"] = mock_ha

def test_proposer_propose_success():
    proposer = ArchitectureProposer()
    
    res = proposer.propose({
        "name": "TestComponent",
        "description": "test",
        "capabilities": ["api", "testing"]
    })
    
    assert res["score"] == 9.5
    assert len(proposer.proposals) == 1
    assert "prop_1" in proposer.proposals

def test_proposer_build():
    proposer = ArchitectureProposer()
    proposer.proposals["prop_1"] = {
        "proposal_id": "prop_1",
        "spec": {"name": "test"},
        "connections": [],
        "value": "v",
        "status": "proposed"
    }
    
    res = proposer.build("prop_1")
    assert res.get("status") == "building"
    assert res.get("request_id") == "req_123"
    assert proposer.proposals["prop_1"]["status"] == "building"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
