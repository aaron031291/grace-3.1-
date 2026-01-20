"""
Comprehensive Component Tests for Autonomous Sandbox Lab

Tests the complete lifecycle of Grace's self-improvement experiments:
- Experiment creation and management
- Trust score calculation
- Trial execution and metrics tracking
- Promotion workflow (sandbox -> trial -> production)
- Continuous learning orchestration
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import os
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ==================== Experiment Status Tests ====================

class TestExperimentStatus:
    """Test ExperimentStatus enum"""

    def test_all_statuses_exist(self):
        """Test all expected statuses are defined"""
        from cognitive.autonomous_sandbox_lab import ExperimentStatus

        assert hasattr(ExperimentStatus, 'PROPOSED')
        assert hasattr(ExperimentStatus, 'SANDBOX')
        assert hasattr(ExperimentStatus, 'TRIAL')
        assert hasattr(ExperimentStatus, 'VALIDATED')
        assert hasattr(ExperimentStatus, 'APPROVED')
        assert hasattr(ExperimentStatus, 'PRODUCTION')
        assert hasattr(ExperimentStatus, 'REJECTED')
        assert hasattr(ExperimentStatus, 'ARCHIVED')

    def test_status_values(self):
        """Test status string values"""
        from cognitive.autonomous_sandbox_lab import ExperimentStatus

        assert ExperimentStatus.PROPOSED.value == "proposed"
        assert ExperimentStatus.SANDBOX.value == "sandbox"
        assert ExperimentStatus.TRIAL.value == "trial"
        assert ExperimentStatus.VALIDATED.value == "validated"
        assert ExperimentStatus.APPROVED.value == "approved"
        assert ExperimentStatus.PRODUCTION.value == "production"
        assert ExperimentStatus.REJECTED.value == "rejected"
        assert ExperimentStatus.ARCHIVED.value == "archived"


class TestExperimentType:
    """Test ExperimentType enum"""

    def test_all_types_exist(self):
        """Test all expected types are defined"""
        from cognitive.autonomous_sandbox_lab import ExperimentType

        assert hasattr(ExperimentType, 'ALGORITHM_IMPROVEMENT')
        assert hasattr(ExperimentType, 'NEW_CAPABILITY')
        assert hasattr(ExperimentType, 'PERFORMANCE_OPTIMIZATION')
        assert hasattr(ExperimentType, 'ERROR_REDUCTION')
        assert hasattr(ExperimentType, 'LEARNING_ENHANCEMENT')
        assert hasattr(ExperimentType, 'SELF_MODELING')

    def test_type_values(self):
        """Test type string values"""
        from cognitive.autonomous_sandbox_lab import ExperimentType

        assert ExperimentType.ALGORITHM_IMPROVEMENT.value == "algorithm_improvement"
        assert ExperimentType.NEW_CAPABILITY.value == "new_capability"
        assert ExperimentType.PERFORMANCE_OPTIMIZATION.value == "performance_optimization"


class TestTrustThreshold:
    """Test TrustThreshold values"""

    def test_threshold_values(self):
        """Test trust thresholds are properly defined"""
        from cognitive.autonomous_sandbox_lab import TrustThreshold

        assert TrustThreshold.SANDBOX_ENTRY == 0.3
        assert TrustThreshold.TRIAL_ENTRY == 0.6
        assert TrustThreshold.PRODUCTION_READY == 0.85
        assert TrustThreshold.AUTO_APPROVE == 0.95

    def test_threshold_ordering(self):
        """Test thresholds increase at each stage"""
        from cognitive.autonomous_sandbox_lab import TrustThreshold

        assert TrustThreshold.SANDBOX_ENTRY < TrustThreshold.TRIAL_ENTRY
        assert TrustThreshold.TRIAL_ENTRY < TrustThreshold.PRODUCTION_READY
        assert TrustThreshold.PRODUCTION_READY < TrustThreshold.AUTO_APPROVE


# ==================== Experiment Tests ====================

class TestExperiment:
    """Test Experiment class"""

    def test_experiment_creation(self):
        """Test creating an experiment"""
        from cognitive.autonomous_sandbox_lab import Experiment, ExperimentType, ExperimentStatus

        exp = Experiment(
            name="Test Experiment",
            description="A test experiment",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            proposed_by="test_user",
            motivation="Testing purposes"
        )

        assert exp.name == "Test Experiment"
        assert exp.description == "A test experiment"
        assert exp.experiment_type == ExperimentType.ALGORITHM_IMPROVEMENT
        assert exp.proposed_by == "test_user"
        assert exp.motivation == "Testing purposes"
        assert exp.status == ExperimentStatus.PROPOSED
        assert exp.experiment_id.startswith("EXP-")

    def test_experiment_with_custom_id(self):
        """Test creating experiment with custom ID"""
        from cognitive.autonomous_sandbox_lab import Experiment

        exp = Experiment(
            experiment_id="EXP-CUSTOM-001",
            name="Custom ID Experiment"
        )

        assert exp.experiment_id == "EXP-CUSTOM-001"

    def test_experiment_initial_values(self):
        """Test experiment initial values"""
        from cognitive.autonomous_sandbox_lab import Experiment

        exp = Experiment(name="Test")

        assert exp.initial_trust_score == 0.0
        assert exp.current_trust_score == 0.0
        assert exp.trust_history == []
        assert exp.baseline_metrics == {}
        assert exp.experiment_metrics == {}
        assert exp.improvement_percentage is None
        assert exp.trial_duration_days == 90
        assert exp.trial_data_points == 0
        assert exp.trial_successes == 0
        assert exp.trial_failures == 0
        assert exp.implementation_code is None
        assert exp.files_modified == []
        assert exp.requires_user_approval == True

    def test_get_success_rate_no_data(self):
        """Test success rate with no trial data"""
        from cognitive.autonomous_sandbox_lab import Experiment

        exp = Experiment(name="Test")
        assert exp.get_success_rate() == 0.0

    def test_get_success_rate_with_data(self):
        """Test success rate calculation"""
        from cognitive.autonomous_sandbox_lab import Experiment

        exp = Experiment(name="Test")
        exp.trial_data_points = 100
        exp.trial_successes = 90
        exp.trial_failures = 10

        assert exp.get_success_rate() == 0.9

    def test_get_trial_days_elapsed_no_trial(self):
        """Test trial days with no trial started"""
        from cognitive.autonomous_sandbox_lab import Experiment

        exp = Experiment(name="Test")
        assert exp.get_trial_days_elapsed() == 0

    def test_get_trial_days_elapsed_active_trial(self):
        """Test trial days with active trial"""
        from cognitive.autonomous_sandbox_lab import Experiment

        exp = Experiment(name="Test")
        exp.trial_started_at = datetime.now() - timedelta(days=30)

        assert exp.get_trial_days_elapsed() == 30

    def test_get_trial_days_remaining(self):
        """Test trial days remaining calculation"""
        from cognitive.autonomous_sandbox_lab import Experiment

        exp = Experiment(name="Test")
        exp.trial_started_at = datetime.now() - timedelta(days=30)

        assert exp.get_trial_days_remaining() == 60

    def test_is_trial_complete(self):
        """Test trial completion check"""
        from cognitive.autonomous_sandbox_lab import Experiment

        exp = Experiment(name="Test")
        exp.trial_started_at = datetime.now() - timedelta(days=91)

        assert exp.is_trial_complete() == True

    def test_is_trial_not_complete(self):
        """Test trial not complete"""
        from cognitive.autonomous_sandbox_lab import Experiment

        exp = Experiment(name="Test")
        exp.trial_started_at = datetime.now() - timedelta(days=30)

        assert exp.is_trial_complete() == False


class TestExperimentGates:
    """Test experiment gate checks"""

    def test_can_enter_sandbox_true(self):
        """Test can enter sandbox with sufficient trust"""
        from cognitive.autonomous_sandbox_lab import Experiment, ExperimentStatus, TrustThreshold

        exp = Experiment(name="Test")
        exp.status = ExperimentStatus.PROPOSED
        exp.current_trust_score = 0.35

        assert exp.can_enter_sandbox() == True

    def test_can_enter_sandbox_low_trust(self):
        """Test cannot enter sandbox with low trust"""
        from cognitive.autonomous_sandbox_lab import Experiment, ExperimentStatus

        exp = Experiment(name="Test")
        exp.status = ExperimentStatus.PROPOSED
        exp.current_trust_score = 0.2

        assert exp.can_enter_sandbox() == False

    def test_can_enter_sandbox_wrong_status(self):
        """Test cannot enter sandbox from wrong status"""
        from cognitive.autonomous_sandbox_lab import Experiment, ExperimentStatus

        exp = Experiment(name="Test")
        exp.status = ExperimentStatus.SANDBOX
        exp.current_trust_score = 0.5

        assert exp.can_enter_sandbox() == False

    def test_can_enter_trial_true(self):
        """Test can enter trial with all requirements"""
        from cognitive.autonomous_sandbox_lab import Experiment, ExperimentStatus

        exp = Experiment(name="Test")
        exp.status = ExperimentStatus.SANDBOX
        exp.current_trust_score = 0.65
        exp.implementation_code = "def improve(): pass"

        assert exp.can_enter_trial() == True

    def test_can_enter_trial_no_implementation(self):
        """Test cannot enter trial without implementation"""
        from cognitive.autonomous_sandbox_lab import Experiment, ExperimentStatus

        exp = Experiment(name="Test")
        exp.status = ExperimentStatus.SANDBOX
        exp.current_trust_score = 0.65

        assert exp.can_enter_trial() == False

    def test_can_promote_to_production(self):
        """Test can promote with all requirements met"""
        from cognitive.autonomous_sandbox_lab import Experiment, ExperimentStatus

        exp = Experiment(name="Test")
        exp.status = ExperimentStatus.VALIDATED
        exp.current_trust_score = 0.90
        exp.trial_started_at = datetime.now() - timedelta(days=91)
        exp.trial_data_points = 1000
        exp.trial_successes = 950

        assert exp.can_promote_to_production() == True

    def test_can_auto_approve(self):
        """Test auto-approve eligibility"""
        from cognitive.autonomous_sandbox_lab import Experiment, ExperimentStatus

        exp = Experiment(name="Test")
        exp.status = ExperimentStatus.VALIDATED
        exp.current_trust_score = 0.96
        exp.trial_started_at = datetime.now() - timedelta(days=91)
        exp.trial_data_points = 1000
        exp.trial_successes = 950
        exp.improvement_percentage = 25.0

        assert exp.can_auto_approve() == True

    def test_cannot_auto_approve_low_improvement(self):
        """Test cannot auto-approve with low improvement"""
        from cognitive.autonomous_sandbox_lab import Experiment, ExperimentStatus

        exp = Experiment(name="Test")
        exp.status = ExperimentStatus.VALIDATED
        exp.current_trust_score = 0.96
        exp.trial_started_at = datetime.now() - timedelta(days=91)
        exp.trial_data_points = 1000
        exp.trial_successes = 950
        exp.improvement_percentage = 15.0  # Below 20%

        assert exp.can_auto_approve() == False


class TestExperimentTrustScore:
    """Test trust score calculation"""

    def test_calculate_trust_score_rule_based(self):
        """Test rule-based trust score calculation"""
        from cognitive.autonomous_sandbox_lab import Experiment

        exp = Experiment(name="Test")
        exp.trial_data_points = 1000
        exp.trial_successes = 900
        exp.trial_started_at = datetime.now() - timedelta(days=45)
        exp.improvement_percentage = 30.0

        score = exp.calculate_trust_score()

        assert 0.0 <= score <= 1.0
        assert len(exp.trust_history) == 1
        assert 'factors' in exp.trust_history[0]

    def test_calculate_trust_score_with_ml_scorer(self):
        """Test trust score with ML scorer"""
        from cognitive.autonomous_sandbox_lab import Experiment

        exp = Experiment(name="Test")
        exp.trial_data_points = 1000
        exp.trial_successes = 900

        mock_scorer = Mock()
        mock_scorer.compute_trust_score.return_value = (0.85, 0.05)

        score = exp.calculate_trust_score(ml_trust_scorer=mock_scorer)

        assert score == 0.85
        assert exp.current_trust_score == 0.85
        mock_scorer.compute_trust_score.assert_called_once()

    def test_calculate_trust_score_ml_fallback(self):
        """Test trust score falls back to rules when ML fails"""
        from cognitive.autonomous_sandbox_lab import Experiment

        exp = Experiment(name="Test")
        exp.trial_data_points = 100
        exp.trial_successes = 90

        mock_scorer = Mock()
        mock_scorer.compute_trust_score.side_effect = Exception("ML unavailable")

        score = exp.calculate_trust_score(ml_trust_scorer=mock_scorer)

        assert 0.0 <= score <= 1.0


class TestExperimentTypeRisk:
    """Test experiment type risk factors"""

    def test_risk_factor_low_risk(self):
        """Test low risk type"""
        from cognitive.autonomous_sandbox_lab import Experiment, ExperimentType

        exp = Experiment(
            name="Test",
            experiment_type=ExperimentType.PERFORMANCE_OPTIMIZATION
        )

        risk = exp._get_type_risk_factor()
        assert risk == 0.9

    def test_risk_factor_high_risk(self):
        """Test high risk type"""
        from cognitive.autonomous_sandbox_lab import Experiment, ExperimentType

        exp = Experiment(
            name="Test",
            experiment_type=ExperimentType.NEW_CAPABILITY
        )

        risk = exp._get_type_risk_factor()
        assert risk == 0.4


class TestExperimentSerialization:
    """Test experiment serialization"""

    def test_to_dict(self):
        """Test experiment to_dict serialization"""
        from cognitive.autonomous_sandbox_lab import Experiment, ExperimentType

        exp = Experiment(
            name="Test Experiment",
            description="Test description",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test motivation"
        )
        exp.current_trust_score = 0.5

        data = exp.to_dict()

        assert data['name'] == "Test Experiment"
        assert data['description'] == "Test description"
        assert data['experiment_type'] == "algorithm_improvement"
        assert data['motivation'] == "Test motivation"
        assert data['status'] == "proposed"
        assert 'trust_scores' in data
        assert data['trust_scores']['current'] == 0.5
        assert 'metrics' in data
        assert 'trial' in data
        assert 'approval' in data
        assert 'gates' in data


# ==================== AutonomousSandboxLab Tests ====================

class TestAutonomousSandboxLab:
    """Test AutonomousSandboxLab class"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sandbox_lab(self, temp_storage):
        """Create sandbox lab with temp storage"""
        from cognitive.autonomous_sandbox_lab import AutonomousSandboxLab

        return AutonomousSandboxLab(storage_path=temp_storage)

    def test_lab_initialization(self, sandbox_lab):
        """Test lab initializes correctly"""
        assert sandbox_lab.experiments == {}
        assert sandbox_lab.active_trials == []
        assert sandbox_lab.storage_path.exists()

    def test_propose_experiment(self, sandbox_lab):
        """Test proposing an experiment"""
        from cognitive.autonomous_sandbox_lab import ExperimentType, ExperimentStatus

        exp = sandbox_lab.propose_experiment(
            name="Test Improvement",
            description="Improve something",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Testing",
            proposed_by="test_user",
            initial_trust_score=0.25  # Below sandbox entry
        )

        assert exp.name == "Test Improvement"
        assert exp.experiment_id in sandbox_lab.experiments
        assert exp.status == ExperimentStatus.PROPOSED
        assert sandbox_lab.stats['total_experiments'] == 1

    def test_propose_experiment_auto_sandbox(self, sandbox_lab):
        """Test experiment auto-enters sandbox with high trust"""
        from cognitive.autonomous_sandbox_lab import ExperimentType, ExperimentStatus

        exp = sandbox_lab.propose_experiment(
            name="High Trust Experiment",
            description="Good experiment",
            experiment_type=ExperimentType.PERFORMANCE_OPTIMIZATION,
            motivation="Testing auto-entry",
            initial_trust_score=0.5  # Above sandbox entry
        )

        assert exp.status == ExperimentStatus.SANDBOX

    def test_enter_sandbox(self, sandbox_lab):
        """Test entering sandbox"""
        from cognitive.autonomous_sandbox_lab import ExperimentType, ExperimentStatus

        exp = sandbox_lab.propose_experiment(
            name="Test",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test",
            initial_trust_score=0.35
        )

        # Already in sandbox due to auto-entry
        assert exp.status == ExperimentStatus.SANDBOX

    def test_enter_sandbox_low_trust(self, sandbox_lab):
        """Test cannot enter sandbox with low trust"""
        from cognitive.autonomous_sandbox_lab import ExperimentType

        exp = sandbox_lab.propose_experiment(
            name="Low Trust",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test",
            initial_trust_score=0.2  # Below threshold
        )

        result = sandbox_lab.enter_sandbox(exp.experiment_id)
        assert result == False

    def test_record_sandbox_implementation(self, sandbox_lab):
        """Test recording sandbox implementation"""
        from cognitive.autonomous_sandbox_lab import ExperimentType, ExperimentStatus

        exp = sandbox_lab.propose_experiment(
            name="Test",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test",
            initial_trust_score=0.5
        )

        # Enter sandbox first
        exp.status = ExperimentStatus.SANDBOX

        code = "def improved_algorithm(): return True"
        files = ["test.py"]

        result = sandbox_lab.record_sandbox_implementation(
            exp.experiment_id,
            code,
            files
        )

        assert result == True
        assert exp.implementation_code == code
        assert exp.implementation_hash is not None
        assert exp.files_modified == files

    def test_start_trial(self, sandbox_lab):
        """Test starting a trial"""
        from cognitive.autonomous_sandbox_lab import ExperimentType, ExperimentStatus

        exp = sandbox_lab.propose_experiment(
            name="Trial Test",
            description="Test",
            experiment_type=ExperimentType.PERFORMANCE_OPTIMIZATION,
            motivation="Test trial start",
            initial_trust_score=0.65
        )

        exp.status = ExperimentStatus.SANDBOX
        exp.implementation_code = "def test(): pass"

        baseline = {"accuracy": 0.8, "speed": 100}
        result = sandbox_lab.start_trial(exp.experiment_id, baseline)

        assert result == True
        assert exp.status == ExperimentStatus.TRIAL
        assert exp.trial_started_at is not None
        assert exp.baseline_metrics == baseline
        assert exp.experiment_id in sandbox_lab.active_trials

    def test_record_trial_result_success(self, sandbox_lab):
        """Test recording successful trial result"""
        from cognitive.autonomous_sandbox_lab import ExperimentType, ExperimentStatus

        exp = sandbox_lab.propose_experiment(
            name="Trial Result Test",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test",
            initial_trust_score=0.65
        )

        exp.status = ExperimentStatus.TRIAL
        exp.trial_started_at = datetime.now()
        exp.baseline_metrics = {"accuracy": 0.8}

        result = sandbox_lab.record_trial_result(
            exp.experiment_id,
            success=True,
            metrics={"accuracy": 0.9}
        )

        assert result == True
        assert exp.trial_data_points == 1
        assert exp.trial_successes == 1
        assert exp.trial_failures == 0

    def test_record_trial_result_failure(self, sandbox_lab):
        """Test recording failed trial result"""
        from cognitive.autonomous_sandbox_lab import ExperimentType, ExperimentStatus

        exp = sandbox_lab.propose_experiment(
            name="Trial Failure Test",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test",
            initial_trust_score=0.65
        )

        exp.status = ExperimentStatus.TRIAL
        exp.trial_started_at = datetime.now()

        result = sandbox_lab.record_trial_result(
            exp.experiment_id,
            success=False
        )

        assert result == True
        assert exp.trial_data_points == 1
        assert exp.trial_successes == 0
        assert exp.trial_failures == 1

    def test_trial_validates_on_completion(self, sandbox_lab):
        """Test trial validates when complete with high success rate"""
        from cognitive.autonomous_sandbox_lab import ExperimentType, ExperimentStatus

        exp = sandbox_lab.propose_experiment(
            name="Validation Test",
            description="Test",
            experiment_type=ExperimentType.PERFORMANCE_OPTIMIZATION,
            motivation="Test validation",
            initial_trust_score=0.7
        )

        exp.status = ExperimentStatus.TRIAL
        exp.trial_started_at = datetime.now() - timedelta(days=91)
        exp.trial_data_points = 999
        exp.trial_successes = 920
        exp.current_trust_score = 0.90
        exp.baseline_metrics = {"accuracy": 0.8}

        # Record final result
        sandbox_lab.record_trial_result(
            exp.experiment_id,
            success=True,
            metrics={"accuracy": 0.9}
        )

        assert exp.status == ExperimentStatus.VALIDATED

    def test_approve_for_production(self, sandbox_lab):
        """Test approving for production"""
        from cognitive.autonomous_sandbox_lab import ExperimentType, ExperimentStatus

        exp = sandbox_lab.propose_experiment(
            name="Approval Test",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test approval",
            initial_trust_score=0.9
        )

        # Set up for approval
        exp.status = ExperimentStatus.VALIDATED
        exp.trial_started_at = datetime.now() - timedelta(days=91)
        exp.trial_data_points = 1000
        exp.trial_successes = 950
        exp.current_trust_score = 0.90

        result = sandbox_lab.approve_for_production(
            exp.experiment_id,
            approved_by="test_user",
            notes="Approved for testing"
        )

        assert result == True
        assert exp.status == ExperimentStatus.APPROVED
        assert exp.approved_by == "test_user"
        assert exp.approval_notes == "Approved for testing"

    def test_promote_to_production(self, sandbox_lab):
        """Test promoting to production"""
        from cognitive.autonomous_sandbox_lab import ExperimentType, ExperimentStatus

        exp = sandbox_lab.propose_experiment(
            name="Production Test",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test promotion",
            initial_trust_score=0.9
        )

        exp.status = ExperimentStatus.APPROVED

        result = sandbox_lab.promote_to_production(exp.experiment_id)

        assert result == True
        assert exp.status == ExperimentStatus.PRODUCTION
        assert exp.production_at is not None

    def test_get_experiment(self, sandbox_lab):
        """Test getting experiment by ID"""
        from cognitive.autonomous_sandbox_lab import ExperimentType

        exp = sandbox_lab.propose_experiment(
            name="Get Test",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test get",
            initial_trust_score=0.5
        )

        retrieved = sandbox_lab.get_experiment(exp.experiment_id)

        assert retrieved is not None
        assert retrieved.experiment_id == exp.experiment_id

    def test_get_experiment_not_found(self, sandbox_lab):
        """Test getting non-existent experiment"""
        result = sandbox_lab.get_experiment("EXP-NONEXISTENT")
        assert result is None

    def test_list_experiments(self, sandbox_lab):
        """Test listing experiments"""
        from cognitive.autonomous_sandbox_lab import ExperimentType

        # Create multiple experiments
        for i in range(3):
            sandbox_lab.propose_experiment(
                name=f"Experiment {i}",
                description="Test",
                experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
                motivation="Test",
                initial_trust_score=0.5
            )

        experiments = sandbox_lab.list_experiments()
        assert len(experiments) == 3

    def test_list_experiments_filter_by_status(self, sandbox_lab):
        """Test filtering experiments by status"""
        from cognitive.autonomous_sandbox_lab import ExperimentType, ExperimentStatus

        exp1 = sandbox_lab.propose_experiment(
            name="Proposed",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test",
            initial_trust_score=0.2  # Won't auto-enter sandbox
        )

        exp2 = sandbox_lab.propose_experiment(
            name="Sandbox",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test",
            initial_trust_score=0.5  # Will auto-enter sandbox
        )

        proposed = sandbox_lab.list_experiments(status=ExperimentStatus.PROPOSED)
        sandbox = sandbox_lab.list_experiments(status=ExperimentStatus.SANDBOX)

        assert len(proposed) == 1
        assert len(sandbox) == 1

    def test_list_experiments_filter_by_type(self, sandbox_lab):
        """Test filtering experiments by type"""
        from cognitive.autonomous_sandbox_lab import ExperimentType

        sandbox_lab.propose_experiment(
            name="Algorithm",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test",
            initial_trust_score=0.5
        )

        sandbox_lab.propose_experiment(
            name="Performance",
            description="Test",
            experiment_type=ExperimentType.PERFORMANCE_OPTIMIZATION,
            motivation="Test",
            initial_trust_score=0.5
        )

        algo = sandbox_lab.list_experiments(experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT)
        perf = sandbox_lab.list_experiments(experiment_type=ExperimentType.PERFORMANCE_OPTIMIZATION)

        assert len(algo) == 1
        assert len(perf) == 1

    def test_get_active_trials(self, sandbox_lab):
        """Test getting active trials"""
        from cognitive.autonomous_sandbox_lab import ExperimentType, ExperimentStatus

        exp = sandbox_lab.propose_experiment(
            name="Active Trial",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test",
            initial_trust_score=0.65
        )

        exp.status = ExperimentStatus.SANDBOX
        exp.implementation_code = "def test(): pass"

        sandbox_lab.start_trial(exp.experiment_id, {"accuracy": 0.8})

        active = sandbox_lab.get_active_trials()
        assert len(active) == 1
        assert active[0].experiment_id == exp.experiment_id

    def test_get_awaiting_approval(self, sandbox_lab):
        """Test getting experiments awaiting approval"""
        from cognitive.autonomous_sandbox_lab import ExperimentType, ExperimentStatus

        exp = sandbox_lab.propose_experiment(
            name="Awaiting Approval",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test",
            initial_trust_score=0.5
        )

        exp.status = ExperimentStatus.VALIDATED
        exp.approval_requested_at = datetime.now()

        awaiting = sandbox_lab.get_awaiting_approval()
        assert len(awaiting) == 1

    def test_get_statistics(self, sandbox_lab):
        """Test getting lab statistics"""
        from cognitive.autonomous_sandbox_lab import ExperimentType

        sandbox_lab.propose_experiment(
            name="Stats Test",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test",
            initial_trust_score=0.5
        )

        stats = sandbox_lab.get_statistics()

        assert 'total_experiments' in stats
        assert 'sandbox_experiments' in stats
        assert 'trial_experiments' in stats
        assert 'production_experiments' in stats
        assert 'rejected_experiments' in stats
        assert 'active_trials_count' in stats
        assert 'awaiting_approval_count' in stats
        assert 'average_trust_score' in stats


class TestSandboxLabPersistence:
    """Test sandbox lab persistence"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_save_experiment(self, temp_storage):
        """Test experiment is saved to disk"""
        from cognitive.autonomous_sandbox_lab import AutonomousSandboxLab, ExperimentType

        lab = AutonomousSandboxLab(storage_path=temp_storage)

        exp = lab.propose_experiment(
            name="Save Test",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test save",
            initial_trust_score=0.5
        )

        # Check file exists
        exp_file = temp_storage / f"{exp.experiment_id}.json"
        assert exp_file.exists()

        # Verify contents
        with open(exp_file) as f:
            data = json.load(f)

        assert data['name'] == "Save Test"
        assert data['experiment_id'] == exp.experiment_id


class TestSandboxLabSeeding:
    """Test sandbox lab seeding"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_seed_initial_experiments(self, temp_storage):
        """Test seeding initial experiments"""
        from cognitive.autonomous_sandbox_lab import AutonomousSandboxLab

        lab = AutonomousSandboxLab(storage_path=temp_storage)
        lab.seed_initial_experiments()

        assert len(lab.experiments) == 5

    def test_seed_does_not_duplicate(self, temp_storage):
        """Test seeding doesn't duplicate if experiments exist"""
        from cognitive.autonomous_sandbox_lab import AutonomousSandboxLab, ExperimentType

        lab = AutonomousSandboxLab(storage_path=temp_storage)

        # Create an experiment first
        lab.propose_experiment(
            name="Existing",
            description="Test",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Test",
            initial_trust_score=0.5
        )

        # Try to seed
        lab.seed_initial_experiments()

        # Should still only have the one we created
        assert len(lab.experiments) == 1


# ==================== ContinuousLearningOrchestrator Tests ====================

class TestContinuousLearningOrchestrator:
    """Test ContinuousLearningOrchestrator class"""

    def test_orchestrator_creation(self):
        """Test orchestrator initializes correctly"""
        from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

        orchestrator = ContinuousLearningOrchestrator()

        assert orchestrator.running == False
        assert orchestrator.orchestrator_thread is None
        assert orchestrator.sandbox_lab is None
        assert orchestrator.mirror_system is None

    def test_orchestrator_default_config(self):
        """Test orchestrator default configuration"""
        from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

        orchestrator = ContinuousLearningOrchestrator()

        assert orchestrator.config['ingestion_interval_seconds'] == 60
        assert orchestrator.config['learning_cycle_interval_seconds'] == 300
        assert orchestrator.config['mirror_observation_interval_seconds'] == 600
        assert orchestrator.config['experiment_check_interval_seconds'] == 120
        assert orchestrator.config['auto_propose_experiments'] == True
        assert orchestrator.config['auto_start_trials'] == True
        assert orchestrator.config['min_trust_for_auto_trial'] == 0.65

    def test_orchestrator_stats(self):
        """Test orchestrator statistics initialization"""
        from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

        orchestrator = ContinuousLearningOrchestrator()

        assert orchestrator.stats['total_ingestions'] == 0
        assert orchestrator.stats['total_learning_cycles'] == 0
        assert orchestrator.stats['total_mirror_observations'] == 0
        assert orchestrator.stats['total_experiments_proposed'] == 0
        assert orchestrator.stats['total_trials_started'] == 0
        assert orchestrator.stats['total_improvements_deployed'] == 0

    def test_orchestrator_get_status(self):
        """Test getting orchestrator status"""
        from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

        orchestrator = ContinuousLearningOrchestrator()
        status = orchestrator.get_status()

        assert 'running' in status
        assert 'uptime_seconds' in status
        assert 'stats' in status
        assert 'config' in status
        assert 'queues' in status
        assert 'last_operations' in status
        assert 'current_metrics' in status

    def test_should_run_ingestion_first_time(self):
        """Test ingestion should run first time"""
        from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

        orchestrator = ContinuousLearningOrchestrator()

        assert orchestrator._should_run_ingestion() == True

    def test_should_run_ingestion_after_interval(self):
        """Test ingestion runs after interval"""
        from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

        orchestrator = ContinuousLearningOrchestrator()
        orchestrator.last_ingestion_check = datetime.now() - timedelta(seconds=70)

        assert orchestrator._should_run_ingestion() == True

    def test_should_not_run_ingestion_too_soon(self):
        """Test ingestion doesn't run too soon"""
        from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

        orchestrator = ContinuousLearningOrchestrator()
        orchestrator.last_ingestion_check = datetime.now() - timedelta(seconds=30)

        assert orchestrator._should_run_ingestion() == False

    def test_should_run_learning_first_time(self):
        """Test learning should run first time"""
        from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

        orchestrator = ContinuousLearningOrchestrator()

        assert orchestrator._should_run_learning() == True

    def test_should_run_mirror_first_time(self):
        """Test mirror should run first time"""
        from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

        orchestrator = ContinuousLearningOrchestrator()

        assert orchestrator._should_run_mirror() == True

    def test_should_check_experiments_first_time(self):
        """Test experiment check should run first time"""
        from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

        orchestrator = ContinuousLearningOrchestrator()

        assert orchestrator._should_check_experiments() == True


class TestContinuousLearningOrchestratorLifecycle:
    """Test orchestrator lifecycle (start/stop)"""

    def test_start_sets_running(self):
        """Test start sets running flag"""
        from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

        orchestrator = ContinuousLearningOrchestrator()

        with patch.object(orchestrator, 'initialize_components'):
            orchestrator.start()

        assert orchestrator.running == True
        assert orchestrator.orchestrator_thread is not None

        # Clean up
        orchestrator.stop()

    def test_stop_clears_running(self):
        """Test stop clears running flag"""
        from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

        orchestrator = ContinuousLearningOrchestrator()

        with patch.object(orchestrator, 'initialize_components'):
            orchestrator.start()
            orchestrator.stop()

        assert orchestrator.running == False

    def test_start_idempotent(self):
        """Test calling start twice doesn't create duplicate threads"""
        from cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

        orchestrator = ContinuousLearningOrchestrator()

        with patch.object(orchestrator, 'initialize_components'):
            orchestrator.start()
            first_thread = orchestrator.orchestrator_thread

            orchestrator.start()  # Second call
            second_thread = orchestrator.orchestrator_thread

        assert first_thread == second_thread

        orchestrator.stop()


class TestContinuousLearningOrchestratorSingleton:
    """Test singleton pattern"""

    def test_get_continuous_orchestrator_singleton(self):
        """Test get_continuous_orchestrator returns singleton"""
        from cognitive.continuous_learning_orchestrator import (
            get_continuous_orchestrator,
            _continuous_orchestrator
        )

        # Reset singleton
        import cognitive.continuous_learning_orchestrator as module
        module._continuous_orchestrator = None

        orch1 = get_continuous_orchestrator()
        orch2 = get_continuous_orchestrator()

        assert orch1 is orch2


# ==================== Integration Tests ====================

class TestSandboxLabIntegration:
    """Integration tests for sandbox lab with other components"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_full_experiment_lifecycle(self, temp_storage):
        """Test complete experiment lifecycle from proposal to production"""
        from cognitive.autonomous_sandbox_lab import (
            AutonomousSandboxLab,
            ExperimentType,
            ExperimentStatus
        )

        lab = AutonomousSandboxLab(storage_path=temp_storage)

        # 1. Propose experiment (high trust for auto-sandbox entry)
        exp = lab.propose_experiment(
            name="Full Lifecycle Test",
            description="Test complete lifecycle",
            experiment_type=ExperimentType.PERFORMANCE_OPTIMIZATION,
            motivation="Integration testing",
            initial_trust_score=0.65
        )

        # Should be in sandbox
        assert exp.status == ExperimentStatus.SANDBOX

        # 2. Record implementation
        result = lab.record_sandbox_implementation(
            exp.experiment_id,
            "def optimized(): return True",
            ["optimization.py"]
        )
        assert result == True

        # 3. Start trial
        result = lab.start_trial(
            exp.experiment_id,
            {"latency_ms": 100, "throughput": 500}
        )
        assert result == True
        assert exp.status == ExperimentStatus.TRIAL

        # 4. Record trial results
        for i in range(100):
            lab.record_trial_result(
                exp.experiment_id,
                success=True,
                metrics={"latency_ms": 50, "throughput": 1000}
            )

        # 5. Fast-forward trial completion
        exp.trial_started_at = datetime.now() - timedelta(days=91)
        exp.current_trust_score = 0.90

        # Record final result to trigger validation
        lab.record_trial_result(exp.experiment_id, success=True)

        # Should be validated
        assert exp.status == ExperimentStatus.VALIDATED

        # 6. Approve
        result = lab.approve_for_production(
            exp.experiment_id,
            approved_by="test_user",
            notes="All tests passed"
        )
        assert result == True

        # 7. Promote
        result = lab.promote_to_production(exp.experiment_id)
        assert result == True
        assert exp.status == ExperimentStatus.PRODUCTION


class TestApprovalRequestGeneration:
    """Test approval request message generation"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_generate_approval_request(self, temp_storage):
        """Test approval request message is properly formatted"""
        from cognitive.autonomous_sandbox_lab import (
            AutonomousSandboxLab,
            ExperimentType,
            ExperimentStatus
        )

        lab = AutonomousSandboxLab(storage_path=temp_storage)

        exp = lab.propose_experiment(
            name="Approval Request Test",
            description="Test approval message",
            experiment_type=ExperimentType.ALGORITHM_IMPROVEMENT,
            motivation="Testing message generation",
            initial_trust_score=0.5
        )

        exp.status = ExperimentStatus.VALIDATED
        exp.trial_data_points = 10000
        exp.trial_successes = 9500
        exp.current_trust_score = 0.92
        exp.improvement_percentage = 25.5
        exp.baseline_metrics = {"accuracy": 0.8}
        exp.experiment_metrics = {"accuracy": 0.95}

        message = lab._generate_approval_request(exp)

        assert "EXPERIMENT READY FOR APPROVAL" in message
        assert exp.experiment_id in message
        assert "Approval Request Test" in message
        assert "10,000" in message  # Data points with comma formatting
        assert "95.0%" in message  # Success rate
        assert "25.5%" in message  # Improvement
        assert "TO APPROVE:" in message
        assert "TO REJECT:" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
