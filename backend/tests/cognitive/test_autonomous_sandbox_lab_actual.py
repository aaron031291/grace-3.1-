import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from backend.cognitive.autonomous_sandbox_lab import (
    Experiment, ExperimentStatus, ExperimentType, TrustThreshold
)

def test_experiment_initialization():
    exp = Experiment(name="Test Exp", description="Desc")
    assert exp.status == ExperimentStatus.PROPOSED
    assert exp.experiment_type == ExperimentType.ALGORITHM_IMPROVEMENT
    assert exp.requires_user_approval is True

def test_calculate_trust_score_rule_based():
    exp = Experiment()
    # Mock data to calculate score
    exp.trial_successes = 90
    exp.trial_data_points = 100
    exp.improvement_percentage = 35.0
    exp.trial_duration_days = 60
    exp.trial_started_at = datetime.now() - timedelta(days=60)
    
    score = exp.calculate_trust_score()
    
    assert 0.0 <= score <= 1.0
    assert len(exp.trust_history) == 1

def test_lifecycle_gates():
    exp = Experiment()
    exp.current_trust_score = TrustThreshold.SANDBOX_ENTRY + 0.1
    assert exp.can_enter_sandbox() is True
    
    exp.status = ExperimentStatus.SANDBOX
    exp.implementation_code = "def foo(): pass"
    exp.current_trust_score = TrustThreshold.TRIAL_ENTRY + 0.1
    assert exp.can_enter_trial() is True
    
    exp.status = ExperimentStatus.VALIDATED
    exp.trial_started_at = datetime.now() - timedelta(days=61)
    exp.trial_data_points = 100
    exp.trial_successes = 95
    exp.improvement_percentage = 35.0
    exp.current_trust_score = TrustThreshold.PRODUCTION_READY + 0.1
    assert exp.can_promote_to_production() is True
    
    exp.current_trust_score = TrustThreshold.AUTO_APPROVE + 0.01
    assert exp.can_auto_approve() is True

if __name__ == "__main__":
    pytest.main(['-v', __file__])
