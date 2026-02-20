"""
Autonomous Sandbox Lab

Grace's self-improvement laboratory where she can:
1. Practice and experiment autonomously
2. Build new algorithms and improvements
3. Test against live data in isolated sandbox
4. Track trust scores and performance metrics
5. Graduate experiments to production after 90-day trial
6. Request user approval for significant changes

Architecture:
- Sandbox Isolation: Experiments run in isolated environment
- Trust Scoring: Every experiment tracked with neural trust scorer
- Performance Monitoring: Continuous metrics collection
- Trial Period: 90-day validation with live data
- Promotion Workflow: Automated promotion with user approval gates
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pathlib import Path
import hashlib
import uuid

logger = logging.getLogger(__name__)
def _check_hia(text):
    try:
        from security.honesty_integrity_accountability import get_hia_framework
        return get_hia_framework().verify_llm_output(text)
    except Exception:
        return None

def _record_time(op, ms):
    try:
        from cognitive.timesense_governance import get_timesense_governance
        get_timesense_governance().record(op, ms, 'autonomous_sandbox_lab')
    except Exception:
        pass


def _track_sandbox(desc, **kwargs):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("sandbox_lab", desc, **kwargs)
    except Exception:
        pass


class ExperimentStatus(Enum):
    """Experiment lifecycle stages"""
    PROPOSED = "proposed"  # Grace has an idea
    SANDBOX = "sandbox"  # Testing in isolation
    TRIAL = "trial"  # 90-day trial with live data
    VALIDATED = "validated"  # Trial passed, awaiting approval
    APPROVED = "approved"  # User approved for production
    PRODUCTION = "production"  # Integrated into main system
    REJECTED = "rejected"  # Failed validation or denied
    ARCHIVED = "archived"  # Completed experiment


class ExperimentType(Enum):
    """Types of experiments Grace can run"""
    ALGORITHM_IMPROVEMENT = "algorithm_improvement"  # Better chunking, retrieval, etc.
    NEW_CAPABILITY = "new_capability"  # Entirely new feature
    PERFORMANCE_OPTIMIZATION = "performance_optimization"  # Speed/memory improvements
    ERROR_REDUCTION = "error_reduction"  # Fix bugs autonomously
    LEARNING_ENHANCEMENT = "learning_enhancement"  # Better learning algorithms
    SELF_MODELING = "self_modeling"  # Improve self-awareness


class TrustThreshold:
    """Trust score thresholds for promotion"""
    SANDBOX_ENTRY = 0.3  # Minimum to enter sandbox
    TRIAL_ENTRY = 0.6  # Minimum to start 90-day trial
    PRODUCTION_READY = 0.85  # Minimum for production promotion
    AUTO_APPROVE = 0.95  # Can auto-approve (still notify user)


class Experiment:
    """
    Single autonomous experiment

    Tracks Grace's self-improvement attempts from idea to production
    """

    def __init__(
        self,
        experiment_id: Optional[str] = None,
        name: str = "",
        description: str = "",
        experiment_type: ExperimentType = ExperimentType.ALGORITHM_IMPROVEMENT,
        proposed_by: str = "grace_mirror",
        motivation: str = ""
    ):
        self.experiment_id = experiment_id or f"EXP-{uuid.uuid4().hex[:12]}"
        self.name = name
        self.description = description
        self.experiment_type = experiment_type
        self.proposed_by = proposed_by
        self.motivation = motivation

        # Lifecycle
        self.status = ExperimentStatus.PROPOSED
        self.created_at = datetime.now()
        self.sandbox_started_at: Optional[datetime] = None
        self.trial_started_at: Optional[datetime] = None
        self.production_at: Optional[datetime] = None

        # Trust scoring
        self.initial_trust_score = 0.0
        self.current_trust_score = 0.0
        self.trust_history: List[Dict] = []

        # Performance metrics
        self.baseline_metrics: Dict[str, float] = {}
        self.experiment_metrics: Dict[str, float] = {}
        self.improvement_percentage: Optional[float] = None

        # Trial tracking
        self.trial_duration_days = 90
        self.trial_data_points = 0
        self.trial_successes = 0
        self.trial_failures = 0

        # Code/implementation
        self.implementation_code: Optional[str] = None
        self.implementation_hash: Optional[str] = None
        self.files_modified: List[str] = []

        # User approval
        self.requires_user_approval = True
        self.approval_requested_at: Optional[datetime] = None
        self.approved_by: Optional[str] = None
        self.approval_notes: Optional[str] = None

    def calculate_trust_score(self, ml_trust_scorer=None) -> float:
        """Calculate current trust score for experiment"""
        factors = {
            "trial_success_rate": self.get_success_rate(),
            "improvement_magnitude": self.improvement_percentage or 0.0,
            "trial_duration_days": self.get_trial_days_elapsed(),
            "data_points_tested": min(self.trial_data_points / 1000, 1.0),
            "error_rate": 1.0 - (self.trial_failures / max(self.trial_data_points, 1)),
            "experiment_type_risk": self._get_type_risk_factor(),
        }

        if ml_trust_scorer:
            # Use neural trust scorer
            try:
                trust_score, uncertainty = ml_trust_scorer.compute_trust_score(
                    learning_example=factors,
                    use_neural=True,
                    fallback_to_rules=True
                )
                self.current_trust_score = trust_score

                # Record in history
                self.trust_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "trust_score": trust_score,
                    "uncertainty": uncertainty,
                    "factors": factors
                })

                return trust_score
            except Exception as e:
                logger.warning(f"Neural trust scoring failed: {e}, using rule-based")

        # Rule-based fallback
        weights = {
            "trial_success_rate": 0.35,
            "improvement_magnitude": 0.25,
            "trial_duration_days": 0.15,
            "data_points_tested": 0.10,
            "error_rate": 0.10,
            "experiment_type_risk": 0.05
        }

        trust_score = sum(factors[k] * weights[k] for k in weights.keys())
        self.current_trust_score = min(max(trust_score, 0.0), 1.0)

        self.trust_history.append({
            "timestamp": datetime.now().isoformat(),
            "trust_score": self.current_trust_score,
            "factors": factors
        })

        return self.current_trust_score

    def get_success_rate(self) -> float:
        """Get trial success rate"""
        if self.trial_data_points == 0:
            return 0.0
        return self.trial_successes / self.trial_data_points

    def get_trial_days_elapsed(self) -> int:
        """Get days elapsed in trial"""
        if not self.trial_started_at:
            return 0
        return (datetime.now() - self.trial_started_at).days

    def get_trial_days_remaining(self) -> int:
        """Get days remaining in trial"""
        if not self.trial_started_at:
            return self.trial_duration_days
        elapsed = self.get_trial_days_elapsed()
        return max(0, self.trial_duration_days - elapsed)

    def is_trial_complete(self) -> bool:
        """Check if trial period is complete"""
        return self.get_trial_days_elapsed() >= self.trial_duration_days

    def _get_type_risk_factor(self) -> float:
        """Get risk factor based on experiment type"""
        risk_map = {
            ExperimentType.PERFORMANCE_OPTIMIZATION: 0.9,  # Low risk
            ExperimentType.ERROR_REDUCTION: 0.85,
            ExperimentType.ALGORITHM_IMPROVEMENT: 0.7,
            ExperimentType.LEARNING_ENHANCEMENT: 0.6,
            ExperimentType.SELF_MODELING: 0.5,
            ExperimentType.NEW_CAPABILITY: 0.4,  # Higher risk
        }
        return risk_map.get(self.experiment_type, 0.5)

    def can_enter_sandbox(self) -> bool:
        """Check if experiment can enter sandbox"""
        return (
            self.status == ExperimentStatus.PROPOSED and
            self.current_trust_score >= TrustThreshold.SANDBOX_ENTRY
        )

    def can_enter_trial(self) -> bool:
        """Check if experiment can enter 90-day trial"""
        return (
            self.status == ExperimentStatus.SANDBOX and
            self.current_trust_score >= TrustThreshold.TRIAL_ENTRY and
            self.implementation_code is not None
        )

    def can_promote_to_production(self) -> bool:
        """Check if experiment can be promoted to production"""
        return (
            self.status == ExperimentStatus.VALIDATED and
            self.current_trust_score >= TrustThreshold.PRODUCTION_READY and
            self.is_trial_complete() and
            self.get_success_rate() >= 0.9  # 90% success rate minimum
        )

    def can_auto_approve(self) -> bool:
        """Check if experiment can be auto-approved"""
        return (
            self.can_promote_to_production() and
            self.current_trust_score >= TrustThreshold.AUTO_APPROVE and
            self.improvement_percentage and
            self.improvement_percentage > 20.0  # 20% improvement
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "experiment_type": self.experiment_type.value,
            "status": self.status.value,
            "proposed_by": self.proposed_by,
            "motivation": self.motivation,
            "created_at": self.created_at.isoformat(),
            "sandbox_started_at": self.sandbox_started_at.isoformat() if self.sandbox_started_at else None,
            "trial_started_at": self.trial_started_at.isoformat() if self.trial_started_at else None,
            "production_at": self.production_at.isoformat() if self.production_at else None,
            "trust_scores": {
                "initial": self.initial_trust_score,
                "current": self.current_trust_score,
                "history": self.trust_history
            },
            "metrics": {
                "baseline": self.baseline_metrics,
                "experiment": self.experiment_metrics,
                "improvement_percentage": self.improvement_percentage
            },
            "trial": {
                "duration_days": self.trial_duration_days,
                "days_elapsed": self.get_trial_days_elapsed(),
                "days_remaining": self.get_trial_days_remaining(),
                "data_points": self.trial_data_points,
                "successes": self.trial_successes,
                "failures": self.trial_failures,
                "success_rate": self.get_success_rate(),
                "is_complete": self.is_trial_complete()
            },
            "approval": {
                "requires_user_approval": self.requires_user_approval,
                "approval_requested_at": self.approval_requested_at.isoformat() if self.approval_requested_at else None,
                "approved_by": self.approved_by,
                "approval_notes": self.approval_notes
            },
            "gates": {
                "can_enter_sandbox": self.can_enter_sandbox(),
                "can_enter_trial": self.can_enter_trial(),
                "can_promote_to_production": self.can_promote_to_production(),
                "can_auto_approve": self.can_auto_approve()
            }
        }


class AutonomousSandboxLab:
    """
    Grace's autonomous experimentation laboratory

    Manages the complete lifecycle of self-improvement experiments:
    - Idea generation (from Mirror observations)
    - Sandbox testing
    - 90-day trials with live data
    - Trust-based promotion to production
    - User approval workflows
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("backend/data/sandbox_lab")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.experiments: Dict[str, Experiment] = {}
        self.active_trials: List[str] = []

        # ML Intelligence integration
        self.ml_trust_scorer = None

        # Statistics
        self.stats = {
            "total_experiments": 0,
            "sandbox_experiments": 0,
            "trial_experiments": 0,
            "production_experiments": 0,
            "rejected_experiments": 0,
            "average_trust_score": 0.0,
            "average_improvement": 0.0,
            "auto_approved": 0,
            "user_approved": 0
        }

        self._load_experiments()

    def initialize_ml_intelligence(self):
        """Initialize ML Intelligence for trust scoring"""
        try:
            from ml_intelligence.integration_orchestrator import MLIntelligenceOrchestrator
            orchestrator = MLIntelligenceOrchestrator()
            orchestrator.initialize()
            self.ml_trust_scorer = orchestrator
            logger.info("[SANDBOX_LAB] ML Intelligence initialized for trust scoring")
        except Exception as e:
            logger.warning(f"[SANDBOX_LAB] ML Intelligence unavailable: {e}")

    def propose_experiment(
        self,
        name: str,
        description: str,
        experiment_type: ExperimentType,
        motivation: str,
        proposed_by: str = "grace_mirror",
        initial_trust_score: float = 0.5
    ) -> Experiment:
        """
        Propose a new experiment

        This is typically called by Mirror when it detects improvement opportunities
        """
        exp = Experiment(
            name=name,
            description=description,
            experiment_type=experiment_type,
            proposed_by=proposed_by,
            motivation=motivation
        )
        exp.initial_trust_score = initial_trust_score
        exp.current_trust_score = initial_trust_score

        self.experiments[exp.experiment_id] = exp
        self.stats["total_experiments"] += 1

        self._save_experiment(exp)

        logger.info(f"[SANDBOX_LAB] New experiment proposed: {exp.experiment_id} - {name}")
        logger.info(f"[SANDBOX_LAB] Initial trust score: {initial_trust_score:.2f}")

        # Auto-enter sandbox if trust is high enough
        if exp.can_enter_sandbox():
            self.enter_sandbox(exp.experiment_id)

        return exp

    def enter_sandbox(self, experiment_id: str) -> bool:
        """Move experiment to sandbox for testing"""
        exp = self.experiments.get(experiment_id)
        if not exp or not exp.can_enter_sandbox():
            return False

        exp.status = ExperimentStatus.SANDBOX
        exp.sandbox_started_at = datetime.now()
        self.stats["sandbox_experiments"] += 1

        self._save_experiment(exp)

        logger.info(f"[SANDBOX_LAB] Experiment {experiment_id} entered sandbox")
        return True

    def record_sandbox_implementation(
        self,
        experiment_id: str,
        implementation_code: str,
        files_modified: List[str]
    ) -> bool:
        """Record the implementation code for sandbox experiment"""
        exp = self.experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.SANDBOX:
            return False

        exp.implementation_code = implementation_code
        exp.implementation_hash = hashlib.sha256(implementation_code.encode()).hexdigest()
        exp.files_modified = files_modified

        self._save_experiment(exp)

        logger.info(f"[SANDBOX_LAB] Implementation recorded for {experiment_id}")
        return True

    def start_trial(
        self,
        experiment_id: str,
        baseline_metrics: Dict[str, float]
    ) -> bool:
        """Start 90-day trial with live data"""
        exp = self.experiments.get(experiment_id)
        if not exp or not exp.can_enter_trial():
            return False

        exp.status = ExperimentStatus.TRIAL
        exp.trial_started_at = datetime.now()
        exp.baseline_metrics = baseline_metrics
        self.active_trials.append(experiment_id)
        self.stats["trial_experiments"] += 1

        self._save_experiment(exp)

        logger.info(f"[SANDBOX_LAB] Trial started for {experiment_id}")
        logger.info(f"[SANDBOX_LAB] 90-day trial period begins - will complete on {(datetime.now() + timedelta(days=90)).date()}")

        return True

    def record_trial_result(
        self,
        experiment_id: str,
        success: bool,
        metrics: Optional[Dict[str, float]] = None
    ) -> bool:
        """Record a single trial data point"""
        exp = self.experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.TRIAL:
            return False

        exp.trial_data_points += 1
        if success:
            exp.trial_successes += 1
        else:
            exp.trial_failures += 1

        if metrics:
            exp.experiment_metrics = metrics
            # Calculate improvement
            if exp.baseline_metrics:
                improvements = []
                for key in exp.baseline_metrics:
                    if key in metrics:
                        baseline = exp.baseline_metrics[key]
                        current = metrics[key]
                        if baseline > 0:
                            improvement = ((current - baseline) / baseline) * 100
                            improvements.append(improvement)

                if improvements:
                    exp.improvement_percentage = sum(improvements) / len(improvements)

        # Recalculate trust score
        exp.calculate_trust_score(self.ml_trust_scorer)

        # Check if trial is complete and successful
        if exp.is_trial_complete():
            if exp.get_success_rate() >= 0.9 and exp.current_trust_score >= TrustThreshold.PRODUCTION_READY:
                exp.status = ExperimentStatus.VALIDATED
                logger.info(f"[SANDBOX_LAB] Trial VALIDATED for {experiment_id}")
                logger.info(f"[SANDBOX_LAB] Success rate: {exp.get_success_rate():.1%}, Trust: {exp.current_trust_score:.2f}")

                # Check for auto-approval
                if exp.can_auto_approve():
                    logger.info(f"[SANDBOX_LAB] Experiment meets auto-approval criteria!")
                    logger.info(f"[SANDBOX_LAB] Trust score: {exp.current_trust_score:.2f} >= {TrustThreshold.AUTO_APPROVE}")
                    logger.info(f"[SANDBOX_LAB] Improvement: {exp.improvement_percentage:.1f}%")

                # Request user approval
                self.request_user_approval(experiment_id)
            else:
                exp.status = ExperimentStatus.REJECTED
                self.stats["rejected_experiments"] += 1
                logger.warning(f"[SANDBOX_LAB] Trial REJECTED for {experiment_id}")
                logger.warning(f"[SANDBOX_LAB] Success rate: {exp.get_success_rate():.1%}, Trust: {exp.current_trust_score:.2f}")

        self._save_experiment(exp)
        return True

    def request_user_approval(self, experiment_id: str) -> bool:
        """Request user approval for production promotion"""
        exp = self.experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.VALIDATED:
            return False

        exp.approval_requested_at = datetime.now()
        self._save_experiment(exp)

        # Generate approval request
        approval_msg = self._generate_approval_request(exp)
        logger.info(f"\n{approval_msg}\n")

        return True

    def approve_for_production(
        self,
        experiment_id: str,
        approved_by: str = "user",
        notes: Optional[str] = None
    ) -> bool:
        """Approve experiment for production"""
        exp = self.experiments.get(experiment_id)
        if not exp or not exp.can_promote_to_production():
            return False

        exp.status = ExperimentStatus.APPROVED
        exp.approved_by = approved_by
        exp.approval_notes = notes

        self._save_experiment(exp)

        if approved_by == "auto":
            self.stats["auto_approved"] += 1
        else:
            self.stats["user_approved"] += 1

        logger.info(f"[SANDBOX_LAB] Experiment {experiment_id} APPROVED for production by {approved_by}")

        return True

    def promote_to_production(self, experiment_id: str) -> bool:
        """Promote approved experiment to production"""
        exp = self.experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.APPROVED:
            return False

        exp.status = ExperimentStatus.PRODUCTION
        exp.production_at = datetime.now()
        self.stats["production_experiments"] += 1

        if self.active_trials and experiment_id in self.active_trials:
            self.active_trials.remove(experiment_id)

        self._save_experiment(exp)

        logger.info(f"[SANDBOX_LAB] Experiment {experiment_id} promoted to PRODUCTION!")
        logger.info(f"[SANDBOX_LAB] Final trust score: {exp.current_trust_score:.2f}")
        improvement_str = f"{exp.improvement_percentage:.1f}%" if exp.improvement_percentage is not None else "N/A"
        logger.info(f"[SANDBOX_LAB] Improvement: {improvement_str}")

        return True

    def _generate_approval_request(self, exp: Experiment) -> str:
        """Generate user-friendly approval request message"""
        msg = [
            "=" * 70,
            "🔬 EXPERIMENT READY FOR APPROVAL",
            "=" * 70,
            "",
            f"Experiment ID: {exp.experiment_id}",
            f"Name: {exp.name}",
            f"Type: {exp.experiment_type.value}",
            "",
            "MOTIVATION:",
            f"  {exp.motivation}",
            "",
            "TRIAL RESULTS (90 days):",
            f"  Data Points: {exp.trial_data_points:,}",
            f"  Success Rate: {exp.get_success_rate():.1%}",
            f"  Failures: {exp.trial_failures}",
            f"  Trust Score: {exp.current_trust_score:.2f}/1.00",
            "",
            "PERFORMANCE:",
            f"  Improvement: {exp.improvement_percentage:.1f}%" if exp.improvement_percentage else "  Improvement: N/A",
        ]

        if exp.baseline_metrics and exp.experiment_metrics:
            msg.append("")
            msg.append("METRICS COMPARISON:")
            for key in exp.baseline_metrics:
                if key in exp.experiment_metrics:
                    baseline = exp.baseline_metrics[key]
                    current = exp.experiment_metrics[key]
                    diff = current - baseline
                    msg.append(f"  {key}: {baseline:.3f} -> {current:.3f} ({diff:+.3f})")

        msg.extend([
            "",
            "RECOMMENDATION:",
        ])

        if exp.can_auto_approve():
            msg.append(f"  ✅ AUTO-APPROVE: Trust score {exp.current_trust_score:.2f} >= {TrustThreshold.AUTO_APPROVE}")
            msg.append(f"  ✅ Improvement {exp.improvement_percentage:.1f}% > 20%")
            msg.append("  ✅ Grace recommends immediate production deployment")
        else:
            msg.append(f"  ⚠️  MANUAL REVIEW: Trust score {exp.current_trust_score:.2f} < {TrustThreshold.AUTO_APPROVE}")
            msg.append("  ⚠️  User approval required before production")

        msg.extend([
            "",
            "TO APPROVE:",
            f"  curl -X POST http://localhost:8000/sandbox-lab/experiments/{exp.experiment_id}/approve",
            "",
            "TO REJECT:",
            f"  curl -X POST http://localhost:8000/sandbox-lab/experiments/{exp.experiment_id}/reject",
            "",
            "=" * 70
        ])

        return "\n".join(msg)

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID"""
        return self.experiments.get(experiment_id)

    def list_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
        experiment_type: Optional[ExperimentType] = None
    ) -> List[Experiment]:
        """List experiments with optional filters"""
        experiments = list(self.experiments.values())

        if status:
            experiments = [e for e in experiments if e.status == status]

        if experiment_type:
            experiments = [e for e in experiments if e.experiment_type == experiment_type]

        return experiments

    def get_active_trials(self) -> List[Experiment]:
        """Get all active trial experiments"""
        return [self.experiments[eid] for eid in self.active_trials if eid in self.experiments]

    def get_awaiting_approval(self) -> List[Experiment]:
        """Get experiments awaiting user approval"""
        return [
            e for e in self.experiments.values()
            if e.status == ExperimentStatus.VALIDATED and e.approval_requested_at
        ]

    def _save_experiment(self, exp: Experiment):
        """Save experiment to disk"""
        exp_file = self.storage_path / f"{exp.experiment_id}.json"
        with open(exp_file, "w") as f:
            json.dump(exp.to_dict(), f, indent=2)

    def _load_experiments(self):
        """Load all experiments from disk"""
        if not self.storage_path.exists():
            return

        for exp_file in self.storage_path.glob("EXP-*.json"):
            try:
                with open(exp_file, "r") as f:
                    data = json.load(f)
                    exp_id = data["experiment_id"]
                    # Reconstruct experiment from JSON
                    # (simplified - would need full deserialization)
                    logger.info(f"[SANDBOX_LAB] Loaded experiment: {exp_id}")
            except Exception as e:
                logger.error(f"[SANDBOX_LAB] Failed to load {exp_file}: {e}")

    def seed_initial_experiments(self):
        """
        Seed the sandbox lab with initial experiments for cold start.

        This ensures there are always experiments running for continuous learning.
        Only seeds if no experiments exist.
        """
        if len(self.experiments) > 0:
            logger.info(f"[SANDBOX_LAB] Already have {len(self.experiments)} experiments, skipping seed")
            return

        logger.info("[SANDBOX_LAB] Seeding initial experiments for cold start...")

        seed_experiments = [
            {
                "name": "Retrieval Quality Optimization",
                "description": "Improve semantic search accuracy by optimizing embedding similarity thresholds and re-ranking strategies",
                "experiment_type": ExperimentType.ALGORITHM_IMPROVEMENT,
                "motivation": "Core capability that affects all RAG operations",
                "initial_trust_score": 0.5
            },
            {
                "name": "Adaptive Chunking Strategy",
                "description": "Implement dynamic chunk sizing based on content type and semantic boundaries",
                "experiment_type": ExperimentType.ALGORITHM_IMPROVEMENT,
                "motivation": "Better chunking leads to better context preservation and retrieval",
                "initial_trust_score": 0.5
            },
            {
                "name": "Learning Retention Enhancement",
                "description": "Improve knowledge consolidation through spaced repetition and active recall patterns",
                "experiment_type": ExperimentType.LEARNING_ENHANCEMENT,
                "motivation": "Continuous learning requires effective long-term retention",
                "initial_trust_score": 0.5
            },
            {
                "name": "Trust Score Calibration",
                "description": "Calibrate trust scoring weights based on actual prediction accuracy",
                "experiment_type": ExperimentType.SELF_MODELING,
                "motivation": "Accurate trust scores are essential for autonomous decision making",
                "initial_trust_score": 0.5
            },
            {
                "name": "Response Quality Improvement",
                "description": "Optimize context assembly and prompt engineering for better response quality",
                "experiment_type": ExperimentType.PERFORMANCE_OPTIMIZATION,
                "motivation": "Higher quality responses increase user trust and system value",
                "initial_trust_score": 0.5
            }
        ]

        for seed in seed_experiments:
            try:
                exp = self.propose_experiment(
                    name=seed["name"],
                    description=seed["description"],
                    experiment_type=seed["experiment_type"],
                    motivation=seed["motivation"],
                    proposed_by="sandbox_lab_seed",
                    initial_trust_score=seed["initial_trust_score"]
                )

                # Move to sandbox status immediately (since these are pre-vetted)
                exp.status = ExperimentStatus.SANDBOX
                exp.sandbox_started_at = datetime.now()
                exp.current_trust_score = seed["initial_trust_score"]

                # Add placeholder implementation code
                exp.implementation_code = f"# Seed experiment: {seed['name']}\n# Implementation pending"

                self._save_experiment(exp)

                logger.info(f"[SANDBOX_LAB] Seeded experiment: {exp.experiment_id} - {exp.name}")

            except Exception as e:
                logger.error(f"[SANDBOX_LAB] Failed to seed experiment {seed['name']}: {e}")

        logger.info(f"[SANDBOX_LAB] Seeded {len(self.experiments)} initial experiments")

    def get_statistics(self) -> Dict[str, Any]:
        """Get lab statistics"""
        experiments = list(self.experiments.values())

        if experiments:
            self.stats["average_trust_score"] = sum(e.current_trust_score for e in experiments) / len(experiments)

            improvements = [e.improvement_percentage for e in experiments if e.improvement_percentage is not None]
            if improvements:
                self.stats["average_improvement"] = sum(improvements) / len(improvements)

        return {
            **self.stats,
            "active_trials_count": len(self.active_trials),
            "awaiting_approval_count": len(self.get_awaiting_approval()),
            "production_experiments": self.stats["production_experiments"]
        }


# Singleton instance
_sandbox_lab: Optional[AutonomousSandboxLab] = None


def get_sandbox_lab() -> AutonomousSandboxLab:
    """Get or create sandbox lab instance"""
    global _sandbox_lab
    if _sandbox_lab is None:
        _sandbox_lab = AutonomousSandboxLab()
        _sandbox_lab.initialize_ml_intelligence()
        _sandbox_lab.seed_initial_experiments()
    return _sandbox_lab
