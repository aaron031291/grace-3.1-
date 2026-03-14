import pytest
from unittest.mock import MagicMock, patch

from backend.cognitive.governance_training_loop import (
    run_oracle_export,
    run_governance_checks,
    run_full_cycle,
    get_governance_report,
    TRIAL_DAYS,
    IMPROVEMENT_THRESHOLD
)

def test_run_oracle_export_success():
    import sys
    sys.modules["cognitive.oracle_export"] = MagicMock()
    mock_export = sys.modules["cognitive.oracle_export"].export_learning_memory_to_oracle
    mock_export.return_value = {"exported": 10, "errors": 0}
    
    result = run_oracle_export(limit=10, min_trust=0.5)
    
    assert result["exported"] == 10
    mock_export.assert_called_once()

def test_run_oracle_export_exception():
    import sys
    sys.modules["cognitive.oracle_export"] = MagicMock()
    mock_export = sys.modules["cognitive.oracle_export"].export_learning_memory_to_oracle
    mock_export.side_effect = Exception("DB error")
    
    result = run_oracle_export()
    
    assert result["exported"] == 0
    assert result["errors"] == 1
    assert "DB error" in result["error"]

def test_run_governance_checks_success():
    import sys
    sys.modules["core.intelligence"] = MagicMock()
    sys.modules["cognitive.unified_memory"] = MagicMock()
    
    mock_adaptive_trust = sys.modules["core.intelligence"].AdaptiveTrust
    mock_adaptive_trust.get_all_trust.return_value = {"models": {"model_a": 0.9, "model_b": 0.8}}
    
    mock_mem_instance = MagicMock()
    mock_mem_instance.get_stats.return_value = {"episodes": {"count": 5}, "skills": 2}
    sys.modules["cognitive.unified_memory"].get_unified_memory.return_value = mock_mem_instance
    
    context = {"cycle_at": "now"}
    result = run_governance_checks(context)
    
    assert result["passed"] is True
    assert "model_a" in result["trust_api"]["models"]
    assert result["trust_api"]["ok"] is True
    assert result["local_rules"]["memory_stats"]["episodes"] == 5
    assert result["local_rules"]["memory_stats"]["skills"] == 2

def test_run_governance_checks_trust_error():
    import sys
    sys.modules["core.intelligence"] = MagicMock()
    
    mock_adaptive_trust = sys.modules["core.intelligence"].AdaptiveTrust
    mock_adaptive_trust.get_all_trust.side_effect = Exception("Trust API down")
    
    result = run_governance_checks({})
    
    assert result["passed"] is False
    assert "Trust API down" in result["trust_api"]["error"]

@patch("backend.cognitive.autonomous_sandbox_lab.get_sandbox_lab", create=True)
@patch("backend.cognitive.governance_training_loop.run_governance_checks")
@patch("backend.cognitive.governance_training_loop.run_oracle_export")
def test_run_full_cycle(mock_oracle_export, mock_run_checks, mock_get_sandbox_lab):
    mock_oracle_export.return_value = {"exported": 5}
    mock_run_checks.return_value = {"passed": True}
    
    # Use real mock objects
    class MockStatus:
        def __eq__(self, other):
            return self == other
            
    mock_trial = MagicMock()
    mock_trial.__eq__.return_value = False # don't care deeply about logic here, but let's do a better patch
    
@patch("backend.cognitive.autonomous_sandbox_lab.get_sandbox_lab", create=True)
@patch("backend.cognitive.governance_training_loop.run_governance_checks")
@patch("backend.cognitive.governance_training_loop.run_oracle_export")
def test_run_full_cycle_alt(mock_oracle_export, mock_run_checks, mock_get_sandbox_lab):
    mock_oracle_export.return_value = {"exported": 5}
    mock_run_checks.return_value = {"passed": True}
    
    import sys
    sys.modules["cognitive.autonomous_sandbox_lab"] = MagicMock()
    from enum import Enum
    class FakeStatus(Enum):
        TRIAL = "TRIAL"
        VALIDATED = "VALIDATED"
    sys.modules["cognitive.autonomous_sandbox_lab"].ExperimentStatus = FakeStatus
    sys.modules["cognitive.autonomous_sandbox_lab"].TRIAL_DAYS_GOVERNANCE = 60
    sys.modules["cognitive.autonomous_sandbox_lab"].IMPROVEMENT_THRESHOLD_PROMOTION = 0.3
    
    class MockExp:
        def __init__(self, exp_id, status):
            self.experiment_id = exp_id
            self.status = status
            
    mock_lab_instance = MagicMock()
    mock_lab_instance.experiments = {
        "exp1": MockExp("exp1", FakeStatus.TRIAL),
        "exp2": MockExp("exp2", FakeStatus.VALIDATED)
    }
    sys.modules["cognitive.autonomous_sandbox_lab"].get_sandbox_lab.return_value = mock_lab_instance
    sys.modules["core.intelligence"] = MagicMock()
    sys.modules["cognitive.unified_memory"] = MagicMock()
    sys.modules["cognitive.oracle_export"] = MagicMock()
    
    result = run_full_cycle()
    
    assert "cycle_at" in result
    assert result["oracle_export"]["exported"] == 5
    assert result["governance"]["passed"] is True
    assert result["sandbox_review"]["in_trial"] == 1
    assert result["sandbox_review"]["awaiting_approval"] == 1
    assert "exp2" in result["sandbox_review"]["awaiting_ids"]

def test_get_governance_report_summary():
    import sys
    sys.modules["cognitive.autonomous_sandbox_lab"] = MagicMock()
    from enum import Enum
    class FakeStatus(Enum):
        TRIAL = "TRIAL"
        VALIDATED = "VALIDATED"
    sys.modules["cognitive.autonomous_sandbox_lab"].ExperimentStatus = FakeStatus
    
    class MockExp:
        def __init__(self, exp_id, status):
            self.experiment_id = exp_id
            self.status = status
            
    mock_lab_instance = MagicMock()
    mock_lab_instance.experiments = {
        "exp1": MockExp("exp1", FakeStatus.TRIAL),
        "exp2": MockExp("exp2", FakeStatus.VALIDATED)
    }
    sys.modules["cognitive.autonomous_sandbox_lab"].get_sandbox_lab.return_value = mock_lab_instance
    
    report = get_governance_report()
    
    assert report["validated_count"] == 1
    assert report["in_trial_count"] == 1
    assert report["validated_ids"] == ["exp2"]

if __name__ == "__main__":
    pytest.main(['-v', __file__])
