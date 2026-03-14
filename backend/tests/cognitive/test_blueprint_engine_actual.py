import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.blueprint_engine import (
    Blueprint, create_from_prompt, _design_blueprint, _build_from_blueprint
)

def test_blueprint_initialization():
    bp = Blueprint(id="bp_1", task="do thing")
    assert bp.status == "draft"
    assert bp.task == "do thing"

@patch("backend.cognitive.blueprint_engine._save_blueprint")
@patch("backend.cognitive.blueprint_engine._design_blueprint")
@patch("backend.cognitive.blueprint_engine._build_from_blueprint")
@patch("backend.cognitive.blueprint_engine._test_code")
@patch("backend.cognitive.blueprint_engine._track_blueprint")
def test_create_from_prompt_success(mock_track, mock_test, mock_build, mock_design, mock_save):
    # Setup mocks
    mock_design.return_value = {
        "architecture": "arch",
        "functions": [],
        "dependencies": [],
        "success_criteria": [],
        "consensus_score": 0.9
    }
    mock_build.return_value = "def foo(): pass"
    mock_test.return_value = {"passed": True, "trust_score": 0.9}
    
    res = create_from_prompt("create a foo function")
    
    assert res["result"] == "SUCCESS"
    assert "status" in res
    assert mock_save.called
    assert mock_track.called

@patch("cognitive.consensus_engine.run_consensus")
def test_design_blueprint(mock_consensus):
    mock_result = MagicMock()
    mock_result.final_output = '{"architecture": "arch", "functions": []}'
    mock_result.confidence = 0.9
    mock_consensus.return_value = mock_result
    
    bp = Blueprint(id="1", task="test")
    res = _design_blueprint("test prompt", bp)
    
    assert res is not None
    assert res["architecture"] == "arch"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
