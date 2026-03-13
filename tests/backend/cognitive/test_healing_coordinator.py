import pytest
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime

# Prevent SQLAlchemy cascade
import sys
sys.modules['backend.api'] = MagicMock()
sys.modules['backend.api._genesis_tracker'] = MagicMock()
sys.modules['api._genesis_tracker'] = MagicMock()
sys.modules['embedding.embedder'] = MagicMock()
sys.modules['vector_db.client'] = MagicMock()
sys.modules['retrieval.retriever'] = MagicMock()
sys.modules['llm_orchestrator.factory'] = MagicMock()

from backend.cognitive.healing_coordinator import get_coordinator

@pytest.fixture
def coordinator():
    return get_coordinator()

@patch('core.async_parallel.run_background')
@patch('api.brain_api_v2.call_brain')
@patch('cognitive.magma_bridge.store_decision')
@patch('cognitive.magma_bridge.store_pattern')
@patch('cognitive.magma_bridge.ingest')
@patch('cognitive.pipeline.FeedbackLoop.record_outcome')
@patch('cognitive.trust_engine.get_trust_engine')
def test_resolve_via_self_healing_fast_path(
    mock_get_trust_engine, mock_record_outcome, mock_ingest,
    mock_store_pat, mock_store_dec, mock_call_brain, mock_run_background, coordinator
):
    problem = {
        "component": "database",
        "description": "Connection timed out",
        "severity": "high"
    }

    # Make call_brain return success for reset_db
    mock_call_brain.return_value = {"ok": True}

    result = coordinator.resolve(problem)

    assert result["resolved"] is True
    assert result["resolution"] == "self_healing"
    assert len(result["steps"]) == 1
    assert result["steps"][0]["step"] == "self_heal"
    assert result["steps"][0]["action"] == "database_reconnect"

    # Verify background learning was triggered (or attempted)
    mock_run_background.assert_called_with(ANY, "learn_after_heal")

@patch('core.async_parallel.run_parallel')
@patch('core.async_parallel.run_background')
@patch('api.brain_api_v2.call_brain')
@patch('cognitive.magma_bridge.store_decision')
@patch('cognitive.magma_bridge.store_pattern')
@patch('cognitive.magma_bridge.ingest')
@patch('cognitive.pipeline.FeedbackLoop.record_outcome')
@patch('cognitive.trust_engine.get_trust_engine')
def test_resolve_via_coding_agent(
    mock_get_trust_engine, mock_record_outcome, mock_ingest,
    mock_store_pat, mock_store_dec, mock_call_brain, mock_run_background, mock_run_parallel, coordinator
):
    problem = {
        "component": "auth_service",
        "description": "SyntaxError in auth.py during startup",
        "error": "SyntaxError: invalid syntax",
        "file_path": "backend/auth/auth.py",
        "severity": "high"
    }

    def side_effect_call_brain(domain, action, payload):
        if domain == "govern" and action == "heal":
            return {"ok": False}  # self-healing fails
        elif domain == "code" and action == "generate":
            return {"ok": True, "data": {"code": "def fix(): pass", "trust_score": 0.9}}
        return {"ok": True}

    mock_call_brain.side_effect = side_effect_call_brain

    # Mock python parallelism wrapper to return diagnostics
    mock_run_parallel.return_value = ("Syntax error in auth.py", "Syntax error found")

    result = coordinator.resolve(problem)

    assert result["resolved"] is True
    assert result["resolution"] == "coding_agent"
    
    # Needs 4 steps: self_heal, diagnose, agree_fix, code_fix
    assert len(result["steps"]) == 4
    assert result["steps"][0]["step"] == "self_heal"
    assert result["steps"][1]["step"] == "diagnose"
    assert result["steps"][2]["step"] == "agree_fix"
    assert result["steps"][3]["step"] == "code_fix"

    mock_run_background.assert_called_with(ANY, "heal_learn_after_code_fix")

@patch('core.async_parallel.run_parallel')
@patch('core.async_parallel.run_background')
@patch('api.brain_api_v2.call_brain')
@patch('cognitive.magma_bridge.store_decision')
@patch('cognitive.magma_bridge.store_pattern')
@patch('cognitive.magma_bridge.ingest')
@patch('cognitive.pipeline.FeedbackLoop.record_outcome')
@patch('cognitive.trust_engine.get_trust_engine')
def test_resolve_via_coordinated_fix(
    mock_get_trust_engine, mock_record_outcome, mock_ingest,
    mock_store_pat, mock_store_dec, mock_call_brain, mock_run_background, mock_run_parallel, coordinator
):
    problem = {
        "component": "auth_service",
        "description": "Unknown attribute missing error",
        "error": "AttributeError: 'NoneType' object has no attribute 'secret'",
        "file_path": "backend/auth/auth.py",
        "severity": "critical"
    }

    # Step 1: Self heal fails
    # Step 4: Code generate fails
    def side_effect_call_brain(domain, action, payload):
        if domain == "govern" and action == "heal":
            return {"ok": False}
        elif domain == "code" and action == "generate":
            return {"ok": False}
        return {"ok": True}
        
    mock_call_brain.side_effect = side_effect_call_brain

    # Step 2: Diagnostics
    mock_run_parallel.return_value = ("Check secret config", "Check config")
    
    # Step 5: External context
    import sys
    sys.modules['retrieval.retriever'].DocumentRetriever.return_value.retrieve.return_value = [{"text": "The auth_secret must be set in config.yaml"}]

    # Step 6: LLM coordinated Rediagnose
    mock_llm_client = MagicMock()
    mock_llm_client.chat.return_value = "Add auth_secret to config.yaml"
    sys.modules['llm_orchestrator.factory'].get_llm_client.return_value = mock_llm_client

    # Run resolution
    result = coordinator.resolve(problem)

    assert result["resolved"] is True
    assert result["resolution"] == "coordinated_fix"
    
    assert len(result["steps"]) == 7
    assert result["steps"][-2]["step"] == "rediagnose"
    assert result["steps"][-1]["step"] == "apply_fix"
    assert result["steps"][-1]["resolved"] is True
