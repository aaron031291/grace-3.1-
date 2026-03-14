import os
import shutil
import pytest
from pathlib import Path
from datetime import datetime, timedelta

from backend.cognitive.autonomous_sandbox_lab import (
    AutonomousSandboxLab, ExperimentStatus, ExperimentType, TrustThreshold
)

@pytest.fixture
def sandbox_lab():
    test_storage = Path("backend/data/sandbox_test_lab")
    if test_storage.exists():
        shutil.rmtree(test_storage)
        
    lab = AutonomousSandboxLab(storage_path=test_storage)
    
    yield lab
    
    if test_storage.exists():
        shutil.rmtree(test_storage)


def test_sandbox_end_to_end_logic(sandbox_lab):
    """
    Test the actual logical workflow of the Sandbox Lab without mocks.
    Validates state transitions, trust scoring math, and promotion gates.
    """
    
    # 1. Propose Experiment
    exp = sandbox_lab.propose_experiment(
        name="Test Actual Logic",
        description="Testing the sandbox math and state logic natively",
        experiment_type=ExperimentType.PERFORMANCE_OPTIMIZATION,
        motivation="Need to verify genuine functionality",
        proposed_by="integration_test",
        initial_trust_score=0.4 # Over sandbox entry threshold (0.3)
    )
    
    # Because trust was 0.4, it should immediately enter SANDBOX state.
    assert exp.status == ExperimentStatus.SANDBOX
    assert sandbox_lab.stats["sandbox_experiments"] == 1
    
    # 2. Record Implementation
    recorded = sandbox_lab.record_sandbox_implementation(
        exp.experiment_id,
        implementation_code="def accelerated_math(): return 2 + 2",
        files_modified=["math.py"]
    )
    assert recorded is True
    assert exp.implementation_code is not None
    assert exp.can_enter_trial() is False # Cannot enter trial until score >= 0.6
    
    # Manually boost trust to test trial entry (simulating sandbox tests passing)
    exp.current_trust_score = 0.65
    assert exp.can_enter_trial() is True
    
    # 3. Start Trial 
    started = sandbox_lab.start_trial(
        exp.experiment_id, 
        baseline_metrics={"speed_ms": 100.0, "memory_mb": 50.0}
    )
    assert started is True
    assert exp.status == ExperimentStatus.TRIAL
    assert exp.experiment_id in sandbox_lab.active_trials
    
    # 4. Record Trial Results (Simulate 90 days of positive data)
    for _ in range(100):
        # Fake a massive improvement to offset the trial average
        sandbox_lab.record_trial_result(
            exp.experiment_id,
            success=True,
            metrics={"speed_ms": 65.0, "memory_mb": 35.0} # Lower is better metrics
        )
        
    assert exp.trial_data_points == 100
    assert exp.trial_successes == 100
    assert exp.get_success_rate() == 1.0
    
    # Force the trial to be considered "completed" time-wise
    exp.trial_started_at = datetime.now() - timedelta(days=95)
    
    # We need to trigger one final result calculation to trip the state change
    sandbox_lab.record_trial_result(
        exp.experiment_id,
        success=True,
        metrics={"speed_ms": 60.0, "memory_mb": 35.0}  # Drop memory enough to hit average 35% improvement
    )
    
    # Trust score should have updated dynamically, improvement calculated
    assert exp.improvement_percentage is not None
    assert exp.improvement_percentage >= 30.0 # 100->60 is a 40% improvement
    
    # It should have shifted automatically to VALIDATED status
    assert exp.status == ExperimentStatus.VALIDATED
    
    # 5. Production Promotion Gate
    can_promote = exp.can_promote_to_production()
    assert can_promote is True
    
    # If trust is exceptionally high and improvement > 30%, it can auto-approve
    if exp.current_trust_score >= TrustThreshold.AUTO_APPROVE:
        assert exp.can_auto_approve() is True
    
    # Approve and Promote
    approved = sandbox_lab.approve_for_production(exp.experiment_id, approved_by="auto")
    assert approved is True
    assert exp.status == ExperimentStatus.APPROVED
    
    promoted = sandbox_lab.promote_to_production(exp.experiment_id)
    assert promoted is True
    assert exp.status == ExperimentStatus.PRODUCTION
    assert sandbox_lab.stats["production_experiments"] == 1
    assert exp.experiment_id not in sandbox_lab.active_trials

if __name__ == "__main__":
    pytest.main(['-v', __file__])
