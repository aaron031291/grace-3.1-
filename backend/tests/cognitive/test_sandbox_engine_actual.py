import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.sandbox_engine import (
    ExperimentStatus, Experiment, propose_and_start_experiment,
    start_experiment, record_checkpoint, analyse_experiment,
    approve_experiment, run_autonomous_experiment
)

@patch("backend.cognitive.sandbox_engine._save_experiment")
@patch("backend.cognitive.sandbox_engine._capture_baseline_metrics")
@patch("cognitive.consensus_engine.run_consensus")
@patch("cognitive.event_bus.publish")
def test_propose_and_start_experiment(mock_publish, mock_consensus, mock_baseline, mock_save):
    mock_baseline.return_value = {"trust_score": 0.8}
    
    mock_decision = MagicMock()
    mock_decision.final_output = "Yes, proceed with the experiment."
    mock_decision.confidence = 0.95
    mock_consensus.return_value = mock_decision
    
    exp = propose_and_start_experiment(
        title="Test Exp",
        description="Desc",
        hypothesis="Hyp",
        use_consensus=True
    )
    
    assert exp.status == ExperimentStatus.RUNNING
    assert exp.baseline["trust_score"] == 0.8
    assert mock_save.called

@patch("backend.cognitive.sandbox_engine._save_experiment")
@patch("backend.cognitive.sandbox_engine._load_experiment")
def test_analyse_experiment(mock_load, mock_save):
    exp = Experiment(
        id="exp_1", title="T1", description="D", hypothesis="H", domain="general",
        status=ExperimentStatus.TRACKING, created_at="2024-01-01T00:00:00Z"
    )
    exp.baseline = {"trust_score": 0.5, "llm_latency_ms": 1000}
    exp.current = {"trust_score": 0.8, "llm_latency_ms": 800} # latency goes down = improved
    
    mock_load.return_value = exp
    
    res = analyse_experiment("exp_1")
    
    assert res["improved_metrics"] == 2
    assert res["recommendation"] == "adopt"
    assert exp.status == ExperimentStatus.AWAITING_APPROVAL

@patch("backend.cognitive.sandbox_engine._save_experiment")
@patch("backend.cognitive.sandbox_engine._load_experiment")
def test_approve_experiment(mock_load, mock_save):
    exp = Experiment(
        id="exp_1", title="T1", description="D", hypothesis="H", domain="general",
        status=ExperimentStatus.AWAITING_APPROVAL, created_at="2024-01-01T00:00:00Z"
    )
    mock_load.return_value = exp
    
    res = approve_experiment("exp_1", approved=True)
    
    assert res["approved"] is True
    assert exp.status == ExperimentStatus.APPROVED

if __name__ == "__main__":
    pytest.main(['-v', __file__])
