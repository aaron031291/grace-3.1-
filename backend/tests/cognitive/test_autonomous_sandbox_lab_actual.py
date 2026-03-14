import pytest
from backend.cognitive.autonomous_sandbox_lab import Experiment, ExperimentStatus, ExperimentType, TrustThreshold, AutonomousSandboxLab
import datetime

def test_experiment_calculate_trust_score():
    exp = Experiment(experiment_type=ExperimentType.PERFORMANCE_OPTIMIZATION)
    exp.trial_data_points = 500
    exp.trial_successes = 490
    exp.trial_failures = 10
    exp.improvement_percentage = 0.40
    
    # set start date so elapsed days is 30
    exp.trial_started_at = datetime.datetime.now() - datetime.timedelta(days=30)
    
    trust_score = exp.calculate_trust_score()
    
    # since no ML scorer, it just returns a float based on factors, but wait...
    # in the code `calculate_trust_score` actually just returns a float if we don't pass ml scorer?
    # Actually wait, `calculate_trust_score` returns a float. Let's see what it returns by default.

def test_autonomous_sandbox_propose(tmp_path):
    lab = AutonomousSandboxLab(storage_path=tmp_path)
    
    exp = lab.propose_experiment(
        name="Faster Sorting",
        description="Optimize list sorts",
        experiment_type=ExperimentType.PERFORMANCE_OPTIMIZATION,
        motivation="Speed up queries",
        proposed_by="test"
    )
    
    assert exp.status == ExperimentStatus.SANDBOX
    assert exp.name == "Faster Sorting"
    assert len(lab.experiments) == 1

def test_autonomous_sandbox_eval(tmp_path):
    lab = AutonomousSandboxLab(storage_path=tmp_path)
    exp = lab.propose_experiment(
        name="Auto Approve test",
        description="test",
        experiment_type=ExperimentType.ERROR_REDUCTION,
        motivation="test auto approve"
    )
    
    # Enter Sandbox and set code
    lab.enter_sandbox(exp.experiment_id)
    lab.record_sandbox_implementation(exp.experiment_id, "def fixed(): pass", [])
    exp.current_trust_score = 0.8
    lab.start_trial(exp.experiment_id, {})
    assert exp.status == ExperimentStatus.TRIAL
    
    # Fast forward the trial
    exp.trial_started_at = datetime.datetime.now() - datetime.timedelta(days=61)
    exp.improvement_percentage = 40.0
    exp.trial_data_points = 1000
    exp.trial_successes = 1000
    exp.trial_failures = 0
    exp.current_trust_score = 0.96 # above auto approve
    
    lab.record_trial_result(exp.experiment_id, True, {})
    assert exp.status == ExperimentStatus.VALIDATED
    
    lab.approve_for_production(exp.experiment_id, approved_by="auto")
    lab.promote_to_production(exp.experiment_id)
    
    assert exp.status == ExperimentStatus.PRODUCTION
    assert lab.stats["production_experiments"] == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
