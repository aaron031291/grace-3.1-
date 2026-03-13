import pytest
import sys
from unittest.mock import patch, MagicMock

# Mock out all external Grace subsystems touched by Hunter
mock_genesis = MagicMock()
sys.modules['api._genesis_tracker'] = mock_genesis

mock_circuit = MagicMock()
mock_circuit.enter_loop.return_value = True
sys.modules['cognitive.circuit_breaker'] = mock_circuit

mock_consensus = MagicMock()
mock_consensus_result = MagicMock()
mock_consensus_result.verification.get.return_value = True
mock_consensus_result.final_output = "Mocked consensus analysis"
mock_consensus.run_consensus.return_value = mock_consensus_result
mock_consensus._check_model_available.return_value = True
sys.modules['cognitive.consensus_engine'] = mock_consensus

mock_kimi = MagicMock()
mock_kimi_instance = MagicMock()
mock_kimi_instance.review_code.return_value = {"review": "Looks good"}
mock_kimi_instance._call.return_value = "Basic Kimi Analysis"
mock_kimi.get_kimi_enhanced.return_value = mock_kimi_instance
sys.modules['llm_orchestrator.kimi_enhanced'] = mock_kimi

mock_pipeline = MagicMock()
mock_pipeline_ctx = MagicMock()
mock_pipeline_ctx.stages_passed = 8
mock_pipeline_ctx.stages_failed = 0
mock_pipeline_ctx.trust_score = 90
mock_pipeline_ctx.llm_response = None
mock_pipeline.CognitivePipeline.return_value.run.return_value = mock_pipeline_ctx
sys.modules['cognitive.pipeline'] = mock_pipeline

mock_trust = MagicMock()
mock_trust_comp = MagicMock()
mock_trust_comp.trust_score = 85
mock_trust.get_trust_engine.return_value.score_output.return_value = mock_trust_comp
sys.modules['cognitive.trust_engine'] = mock_trust

mock_librarian = MagicMock()
sys.modules['cognitive.librarian_autonomous'] = mock_librarian

mock_genesis_rt = MagicMock()
sys.modules['genesis.realtime'] = mock_genesis_rt

mock_registry = MagicMock()
sys.modules['cognitive.system_registry'] = mock_registry

mock_magma = MagicMock()
sys.modules['cognitive.magma_bridge'] = mock_magma

mock_immune = MagicMock()
mock_immune.get_immune_system.return_value.scan.return_value = {"overall_health": {"status": "ok"}}
sys.modules['cognitive.immune_system'] = mock_immune

from backend.cognitive.hunter_assimilator import get_hunter, AssimilationResult

@pytest.fixture
def hunter():
    return get_hunter()

def test_is_hunter_request(hunter):
    assert hunter.is_hunter_request("Please run HUNTER on this") is True
    assert hunter.is_hunter_request("Can you implement this feature?") is False

@patch("pathlib.Path.write_text")
@patch("pathlib.Path.exists")
@patch("pathlib.Path.mkdir")
def test_assimilate_full_pipeline(mock_mkdir, mock_exists, mock_write, hunter):
    code = """
```filepath: new_feature.py
class NewFeature(BaseModel):
    pass
```
    """
    
    # Mock exists to say kb doesn't conflict
    mock_exists.return_value = False
    
    result = hunter.assimilate(code, description="Implement NewFeature")
    
    assert isinstance(result, AssimilationResult)
    assert result.status == "complete"
    assert len(result.files_created) == 1
    assert "new_feature.py" in result.files_created[0]
    assert len(result.schemas_detected) >= 1
    assert "NewFeature" in result.schemas_detected
    assert result.trust_score == 85
    
    # Step verification
    steps = [s["step"] for s in result.steps]
    expected_steps = [
        "parse", "kimi_analyse", "pipeline_verify", "code_review",
        "trust_score", "healing_precheck", "write_files", "migrate_schemas",
        "librarian_organise", "handshake", "contradiction_check", "feed_learning",
        "immune_postcheck", "update_kpi"
    ]
    for es in expected_steps:
        assert es in steps

def test_assimilate_with_issues_fixed(hunter):
    code = """
```filepath: buggy.py
eval("print(1)")
import os; os.system("rm -rf")
```
    """
    
    # Mock pipeline returning fixed code
    global mock_pipeline
    mock_pipeline_ctx = MagicMock()
    mock_pipeline_ctx.llm_response = "print(1)"
    mock_pipeline.CognitivePipeline.return_value.run.return_value = mock_pipeline_ctx
    
    result = hunter.assimilate(code, description="Buggy feature")
    
    assert len(result.issues_found) >= 2
    assert "fix_issues" in [s["step"] for s in result.steps]
    assert result.status == "complete"
