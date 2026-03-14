import pytest
import os
import json
from pathlib import Path

from cognitive.architecture_compass import ArchitectureCompass
from cognitive.blueprint_engine import Blueprint, FunctionSpec, get_playbook_stats
from cognitive.architecture_proposer import ArchitectureProposer

def test_compass_actual_logic():
    """Verify that Architecture Compass physically maps the backend without mocks."""
    compass = ArchitectureCompass()
    
    # Physically scan the workspace code
    compass.build()
    
    diag = compass.diagnose()
    assert diag["total_components"] > 0
    assert diag["total_connections"] > 0
    
    # Ensure it parsed itself and extracted its public APIs and purpose
    explain_txt = compass.explain("architecture_compass")
    assert "ArchitectureCompass" in explain_txt or "architecture_compass" in explain_txt
    assert "Purpose:" in explain_txt
    
    # Assert dependency prediction logic calculates something (empty or not)
    issues = compass.predict_dependency_issues()
    assert isinstance(issues, list)
    
def test_blueprint_models_logic():
    """Check dataclass behaviors and defaults for the Blueprint Engine."""
    spec = FunctionSpec(
        name="hello_world",
        inputs={"name": "str"},
        output_type="str",
        description="Returns greeting"
    )
    
    bp = Blueprint(
        id="bp_test123",
        task="Say hello",
        functions=[spec.__dict__]
    )
    
    data = bp.to_dict()
    assert data["id"] == "bp_test123"
    assert data["status"] == "draft"
    assert len(data["functions"]) == 1
    assert data["functions"][0]["name"] == "hello_world"

def test_playbook_stats():
    """Verify playbook stats engine can safely run against local dirs."""
    stats = get_playbook_stats()
    assert "total" in stats
    assert "successes" in stats
    assert "failures" in stats
    assert isinstance(stats["success_rate"], float)

def test_architecture_proposer_logic(monkeypatch):
    """Test proposal pipeline logic + Compass lookup integration."""
    proposer = ArchitectureProposer()
    
    # We patch the Qwen LLM call to avoid API network hangs and cost
    class MockLLM:
        def generate(self, *args, **kwargs):
            return '{"need_score": 9.5, "connections": ["api/brain_api_v2.py"], "value_proposition": "Excellent value"}'
    
    import llm_orchestrator.factory as lf
    monkeypatch.setattr(lf, "get_llm_client", lambda: MockLLM())
    monkeypatch.setattr(lf, "get_llm_for_task", lambda x: MockLLM())
    
    json_spec = {
        "name": "QuantumRelay",
        "description": "Send events super fast",
        "capabilities": ["event_streaming", "fast_io"]
    }
    
    proposal = proposer.propose(json_spec)
    
    assert proposal["score"] == 9.5
    assert "api/brain_api_v2.py" in proposal["connections"]
    assert len(proposer.proposals) == 1
    assert proposal["spec"]["name"] == "QuantumRelay"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
