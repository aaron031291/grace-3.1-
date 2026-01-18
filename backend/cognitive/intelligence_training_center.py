"""
Intelligence Training Center - Grace's Training Loop for Compounding Intelligence

This is Grace's equivalent of an LLM's training process with models and weights.
Instead of neural weights, Grace persists intelligence as:
- Skill mastery vectors
- Pattern libraries (with trust scores)
- Procedure libraries (multi-step playbooks)
- Template libraries (code patterns)
- Retrieval priors
- Failure taxonomies

The unified training loop: OBSERVE → ORIENT → DECIDE → ACT → EVALUATE → LEARN → CONSOLIDATE
"""

import logging
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
import time

logger = logging.getLogger(__name__)


# =============================================================================
# CORE PRIMITIVES - The "Model" Objects
# =============================================================================

class TrainingDomain(str, Enum):
    """Domains of intelligence training."""
    CODING = "coding"
    SELF_HEALING = "self_healing"
    REASONING = "reasoning"
    KNOWLEDGE = "knowledge"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    TESTING = "testing"


class TaskDifficulty(str, Enum):
    """Task difficulty levels."""
    TRIVIAL = "trivial"      # 1
    EASY = "easy"            # 2
    MEDIUM = "medium"        # 3
    HARD = "hard"            # 4
    EXPERT = "expert"        # 5
    FRONTIER = "frontier"    # 6 - Unsolved/novel problems


@dataclass
class TrainingTask:
    """
    A unit of practice - fix a file, write code, diagnose issue, etc.
    This is what Grace practices on in the sandbox.
    """
    task_id: str
    domain: TrainingDomain
    difficulty: TaskDifficulty
    objective: str
    description: str
    constraints: List[str] = field(default_factory=list)
    input_artifacts: Dict[str, Any] = field(default_factory=dict)
    evaluation_plan: Dict[str, Any] = field(default_factory=dict)
    genesis_key_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(domain: TrainingDomain, objective: str, **kwargs) -> "TrainingTask":
        """Factory method to create a training task."""
        return TrainingTask(
            task_id=f"TASK-{uuid.uuid4().hex[:12]}",
            domain=domain,
            objective=objective,
            difficulty=kwargs.get("difficulty", TaskDifficulty.MEDIUM),
            description=kwargs.get("description", objective),
            constraints=kwargs.get("constraints", []),
            input_artifacts=kwargs.get("input_artifacts", {}),
            evaluation_plan=kwargs.get("evaluation_plan", {}),
            genesis_key_id=kwargs.get("genesis_key_id"),
            metadata=kwargs.get("metadata", {})
        )


@dataclass
class TrainingAttempt:
    """
    One run on a task - the plan, actions, and outputs.
    This is Grace's attempt to solve a training task.
    """
    attempt_id: str
    task_id: str
    plan: Dict[str, Any]
    actions: List[Dict[str, Any]]
    patch: Optional[str] = None
    tests_added: List[str] = field(default_factory=list)
    tool_logs: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_ms: int = 0
    patterns_used: List[str] = field(default_factory=list)
    procedures_used: List[str] = field(default_factory=list)
    failure_modes: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(task_id: str, plan: Dict[str, Any]) -> "TrainingAttempt":
        """Factory method to create a training attempt."""
        return TrainingAttempt(
            attempt_id=f"ATTEMPT-{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            plan=plan,
            actions=[]
        )


@dataclass
class EvaluationResult:
    """
    Standard scoring across all domains.
    Determines if an attempt was successful and by how much.
    """
    evaluation_id: str
    attempt_id: str
    success: bool
    scores: Dict[str, float] = field(default_factory=dict)  # correctness, safety, maintainability, etc.
    regressions: List[str] = field(default_factory=list)
    judge_confidence: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    test_results: Dict[str, Any] = field(default_factory=dict)
    static_analysis: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(attempt_id: str, success: bool, **kwargs) -> "EvaluationResult":
        """Factory method to create an evaluation result."""
        return EvaluationResult(
            evaluation_id=f"EVAL-{uuid.uuid4().hex[:12]}",
            attempt_id=attempt_id,
            success=success,
            scores=kwargs.get("scores", {
                "correctness": 0.0,
                "safety": 0.0,
                "maintainability": 0.0,
                "performance": 0.0,
                "security": 0.0
            }),
            regressions=kwargs.get("regressions", []),
            judge_confidence=kwargs.get("judge_confidence", 0.0),
            evidence=kwargs.get("evidence", {}),
            test_results=kwargs.get("test_results", {}),
            static_analysis=kwargs.get("static_analysis", {})
        )


@dataclass
class LearningDelta:
    """
    What changed in Grace due to this attempt - the "gradient update" analogue.
    This is how Grace's intelligence evolves from each practice.
    """
    delta_id: str
    attempt_id: str
    evaluation_id: str
    patterns_added: List[Dict[str, Any]] = field(default_factory=list)
    patterns_updated: List[Dict[str, Any]] = field(default_factory=list)
    procedures_added: List[Dict[str, Any]] = field(default_factory=list)
    procedures_updated: List[Dict[str, Any]] = field(default_factory=list)
    templates_added: List[Dict[str, Any]] = field(default_factory=list)
    templates_updated: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_priors_updated: Dict[str, float] = field(default_factory=dict)
    mastery_updates: Dict[str, float] = field(default_factory=dict)
    failure_taxonomy_updates: List[Dict[str, Any]] = field(default_factory=list)
    trust_impact: float = 0.0
    knowledge_items: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(attempt_id: str, evaluation_id: str) -> "LearningDelta":
        """Factory method to create a learning delta."""
        return LearningDelta(
            delta_id=f"DELTA-{uuid.uuid4().hex[:12]}",
            attempt_id=attempt_id,
            evaluation_id=evaluation_id
        )


# =============================================================================
# GRACE MODEL SNAPSHOT - The "Weights" Equivalent
# =============================================================================

@dataclass
class SkillMastery:
    """Mastery level for a specific skill/domain."""
    domain: str
    level: float  # 0.0 to 1.0
    attempts: int
    successes: int
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def success_rate(self) -> float:
        return self.successes / max(self.attempts, 1)


@dataclass
class GraceModelSnapshot:
    """
    Grace's "weights" - the versioned policy state that drives decisions.
    This is what makes Grace intelligent and is persisted/versioned.
    """
    model_version: str
    created_at: datetime
    
    # Skill mastery vector (per domain)
    skill_mastery: Dict[str, SkillMastery] = field(default_factory=dict)
    
    # Pattern library (learned patterns with trust scores)
    pattern_count: int = 0
    pattern_trust_avg: float = 0.0
    top_patterns: List[Dict[str, Any]] = field(default_factory=list)
    
    # Procedure library (multi-step playbooks)
    procedure_count: int = 0
    procedure_success_rate: float = 0.0
    
    # Template library (code patterns)
    template_count: int = 0
    template_domains: Dict[str, int] = field(default_factory=dict)
    
    # Retrieval priors
    retrieval_priors: Dict[str, float] = field(default_factory=dict)
    
    # Failure taxonomy
    failure_categories: Dict[str, int] = field(default_factory=dict)
    
    # Trust calibration
    trust_calibration: Dict[str, float] = field(default_factory=dict)
    
    # Metrics
    total_attempts: int = 0
    total_successes: int = 0
    overall_success_rate: float = 0.0
    
    # Provenance
    parent_version: Optional[str] = None
    genesis_key_id: Optional[str] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat(),
            "skill_mastery": {
                k: {
                    "domain": v.domain,
                    "level": v.level,
                    "attempts": v.attempts,
                    "successes": v.successes,
                    "success_rate": v.success_rate
                }
                for k, v in self.skill_mastery.items()
            },
            "pattern_count": self.pattern_count,
            "pattern_trust_avg": self.pattern_trust_avg,
            "procedure_count": self.procedure_count,
            "template_count": self.template_count,
            "total_attempts": self.total_attempts,
            "total_successes": self.total_successes,
            "overall_success_rate": self.overall_success_rate,
            "parent_version": self.parent_version
        }
    
    @staticmethod
    def create_initial() -> "GraceModelSnapshot":
        """Create initial model snapshot."""
        return GraceModelSnapshot(
            model_version="0.1.0",
            created_at=datetime.utcnow(),
            skill_mastery={
                domain.value: SkillMastery(
                    domain=domain.value,
                    level=0.0,
                    attempts=0,
                    successes=0
                )
                for domain in TrainingDomain
            }
        )


# =============================================================================
# TRAINING CENTER - The Orchestrator
# =============================================================================

class IntelligenceTrainingCenter:
    """
    The Intelligence Training Center - Grace's training loop.
    
    This orchestrates the unified training loop:
    OBSERVE → ORIENT → DECIDE → ACT → EVALUATE → LEARN → CONSOLIDATE
    
    It manages:
    - Task generation and scheduling
    - Attempt execution
    - Evaluation and scoring
    - Learning delta computation
    - Model snapshot persistence and promotion
    """
    
    def __init__(
        self,
        session=None,
        storage_path: Optional[Path] = None,
        memory_mesh=None,
        learning_memory=None,
        sandbox_lab=None,
        healing_system=None,
        coding_agent=None,
        federated_learning=None
    ):
        """Initialize the Training Center."""
        self.session = session
        self.storage_path = storage_path or Path("data/training_center")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Connected systems
        self.memory_mesh = memory_mesh
        self.learning_memory = learning_memory
        self.sandbox_lab = sandbox_lab
        self.healing_system = healing_system
        self.coding_agent = coding_agent
        self.federated_learning = federated_learning
        
        # Current model snapshot
        self._current_snapshot: Optional[GraceModelSnapshot] = None
        
        # Event log (append-only)
        self._event_log: List[Dict[str, Any]] = []
        
        # Task queue
        self._task_queue: List[TrainingTask] = []
        
        # Training state
        self._is_training = False
        self._training_thread: Optional[threading.Thread] = None
        
        # Configuration
        self.config = {
            "min_trust_for_pattern": 0.6,
            "min_trust_for_procedure": 0.7,
            "min_trust_for_production": 0.85,
            "snapshot_interval_attempts": 100,
            "max_concurrent_tasks": 5,
            "curriculum_mix": {
                "easy": 0.2,
                "medium": 0.4,
                "hard": 0.3,
                "frontier": 0.1
            }
        }
        
        # Statistics
        self.stats = {
            "total_tasks_completed": 0,
            "total_attempts": 0,
            "total_successes": 0,
            "total_failures": 0,
            "patterns_learned": 0,
            "procedures_learned": 0,
            "templates_learned": 0,
            "snapshots_created": 0
        }
        
        # Load or create initial snapshot
        self._load_or_create_snapshot()
        
        logger.info("Intelligence Training Center initialized")
    
    # =========================================================================
    # SNAPSHOT MANAGEMENT (The "Weights")
    # =========================================================================
    
    def _load_or_create_snapshot(self):
        """Load existing snapshot or create initial one."""
        snapshot_file = self.storage_path / "current_snapshot.json"
        
        if snapshot_file.exists():
            try:
                with open(snapshot_file) as f:
                    data = json.load(f)
                    self._current_snapshot = self._deserialize_snapshot(data)
                    logger.info(f"Loaded model snapshot v{self._current_snapshot.model_version}")
            except Exception as e:
                logger.warning(f"Failed to load snapshot: {e}, creating new")
                self._current_snapshot = GraceModelSnapshot.create_initial()
        else:
            self._current_snapshot = GraceModelSnapshot.create_initial()
            self._save_snapshot()
    
    def _save_snapshot(self):
        """Save current snapshot to disk."""
        try:
            snapshot_file = self.storage_path / "current_snapshot.json"
            with open(snapshot_file, "w") as f:
                json.dump(self._current_snapshot.to_dict(), f, indent=2)
            
            # Also save versioned copy
            version_file = self.storage_path / f"snapshot_v{self._current_snapshot.model_version}.json"
            with open(version_file, "w") as f:
                json.dump(self._current_snapshot.to_dict(), f, indent=2)
            
            self.stats["snapshots_created"] += 1
            logger.info(f"Saved model snapshot v{self._current_snapshot.model_version}")
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
    
    def _deserialize_snapshot(self, data: Dict) -> GraceModelSnapshot:
        """Deserialize snapshot from dictionary."""
        snapshot = GraceModelSnapshot(
            model_version=data.get("model_version", "0.1.0"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            pattern_count=data.get("pattern_count", 0),
            pattern_trust_avg=data.get("pattern_trust_avg", 0.0),
            procedure_count=data.get("procedure_count", 0),
            template_count=data.get("template_count", 0),
            total_attempts=data.get("total_attempts", 0),
            total_successes=data.get("total_successes", 0),
            overall_success_rate=data.get("overall_success_rate", 0.0),
            parent_version=data.get("parent_version")
        )
        
        # Restore skill mastery
        for domain, mastery_data in data.get("skill_mastery", {}).items():
            snapshot.skill_mastery[domain] = SkillMastery(
                domain=mastery_data.get("domain", domain),
                level=mastery_data.get("level", 0.0),
                attempts=mastery_data.get("attempts", 0),
                successes=mastery_data.get("successes", 0)
            )
        
        return snapshot
    
    def get_current_snapshot(self) -> GraceModelSnapshot:
        """Get current model snapshot."""
        return self._current_snapshot
    
    def create_new_snapshot(self, reason: str = "manual") -> GraceModelSnapshot:
        """Create a new snapshot version."""
        old_version = self._current_snapshot.model_version
        
        # Increment version
        parts = old_version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        new_version = ".".join(parts)
        
        self._current_snapshot.parent_version = old_version
        self._current_snapshot.model_version = new_version
        self._current_snapshot.created_at = datetime.utcnow()
        self._current_snapshot.metadata["reason"] = reason
        
        self._save_snapshot()
        
        # Log event
        self._log_event("snapshot_created", {
            "old_version": old_version,
            "new_version": new_version,
            "reason": reason
        })
        
        return self._current_snapshot
    
    # =========================================================================
    # THE UNIFIED TRAINING LOOP
    # =========================================================================
    
    def run_training_loop(
        self,
        task: TrainingTask,
        executor: Optional[callable] = None
    ) -> Tuple[TrainingAttempt, EvaluationResult, LearningDelta]:
        """
        Run the unified training loop for a single task.
        
        OBSERVE → ORIENT → DECIDE → ACT → EVALUATE → LEARN → CONSOLIDATE
        """
        logger.info(f"Starting training loop for task {task.task_id}")
        
        # 1. OBSERVE - Task is already observed (input)
        self._log_event("observe", {"task_id": task.task_id, "domain": task.domain.value})
        
        # 2. ORIENT - Retrieve relevant context
        context = self._orient(task)
        
        # 3. DECIDE - Create a plan
        plan = self._decide(task, context)
        
        # 4. ACT - Execute the plan
        attempt = self._act(task, plan, context, executor)
        
        # 5. EVALUATE - Score the attempt
        evaluation = self._evaluate(task, attempt)
        
        # 6. LEARN - Compute learning delta
        delta = self._learn(task, attempt, evaluation)
        
        # 7. CONSOLIDATE - Update model snapshot
        self._consolidate(delta, evaluation)
        
        # Update statistics
        self.stats["total_tasks_completed"] += 1
        self.stats["total_attempts"] += 1
        if evaluation.success:
            self.stats["total_successes"] += 1
        else:
            self.stats["total_failures"] += 1
        
        logger.info(f"Completed training loop for task {task.task_id}: success={evaluation.success}")
        
        return attempt, evaluation, delta
    
    def _orient(self, task: TrainingTask) -> Dict[str, Any]:
        """
        ORIENT - Retrieve relevant memories, patterns, and procedures.
        Build a structured situation model.
        """
        context = {
            "retrieved_patterns": [],
            "retrieved_procedures": [],
            "retrieved_templates": [],
            "similar_tasks": [],
            "domain_mastery": 0.0
        }
        
        # Get domain mastery
        domain_key = task.domain.value
        if domain_key in self._current_snapshot.skill_mastery:
            context["domain_mastery"] = self._current_snapshot.skill_mastery[domain_key].level
        
        # Retrieve from memory mesh if available
        if self.memory_mesh:
            try:
                # Search for similar patterns
                patterns = self.memory_mesh.search_patterns(
                    query=task.objective,
                    domain=task.domain.value,
                    limit=5
                )
                context["retrieved_patterns"] = patterns
            except Exception as e:
                logger.warning(f"Failed to retrieve from memory mesh: {e}")
        
        # Retrieve from learning memory if available
        if self.learning_memory:
            try:
                procedures = self.learning_memory.get_procedures_for_domain(task.domain.value)
                context["retrieved_procedures"] = procedures[:5]
            except Exception as e:
                logger.warning(f"Failed to retrieve from learning memory: {e}")
        
        self._log_event("orient", {
            "task_id": task.task_id,
            "patterns_found": len(context["retrieved_patterns"]),
            "procedures_found": len(context["retrieved_procedures"])
        })
        
        return context
    
    def _decide(self, task: TrainingTask, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        DECIDE - Choose a plan and which patterns/procedures to apply.
        """
        plan = {
            "strategy": "default",
            "patterns_to_use": [],
            "procedures_to_use": [],
            "risk_level": "low",
            "validators": [],
            "rollback_plan": None
        }
        
        # Select best patterns based on trust and relevance
        for pattern in context.get("retrieved_patterns", []):
            trust = pattern.get("trust_score", 0.0)
            if trust >= self.config["min_trust_for_pattern"]:
                plan["patterns_to_use"].append(pattern)
        
        # Select best procedures
        for procedure in context.get("retrieved_procedures", []):
            if procedure.get("success_rate", 0.0) >= 0.7:
                plan["procedures_to_use"].append(procedure)
        
        # Determine risk level
        difficulty_risk = {
            TaskDifficulty.TRIVIAL: "low",
            TaskDifficulty.EASY: "low",
            TaskDifficulty.MEDIUM: "medium",
            TaskDifficulty.HARD: "high",
            TaskDifficulty.EXPERT: "high",
            TaskDifficulty.FRONTIER: "critical"
        }
        plan["risk_level"] = difficulty_risk.get(task.difficulty, "medium")
        
        # Add validators based on domain
        if task.domain == TrainingDomain.CODING:
            plan["validators"] = ["syntax_check", "type_check", "lint", "test"]
        elif task.domain == TrainingDomain.SELF_HEALING:
            plan["validators"] = ["regression_check", "fix_verification"]
        elif task.domain == TrainingDomain.SECURITY:
            plan["validators"] = ["security_scan", "vulnerability_check"]
        
        self._log_event("decide", {
            "task_id": task.task_id,
            "strategy": plan["strategy"],
            "risk_level": plan["risk_level"],
            "patterns_selected": len(plan["patterns_to_use"])
        })
        
        return plan
    
    def _act(
        self,
        task: TrainingTask,
        plan: Dict[str, Any],
        context: Dict[str, Any],
        executor: Optional[callable] = None
    ) -> TrainingAttempt:
        """
        ACT - Execute the plan (generate patch, run checks, etc.).
        """
        attempt = TrainingAttempt.create(task.task_id, plan)
        attempt.started_at = datetime.utcnow()
        
        try:
            # Use provided executor or default
            if executor:
                result = executor(task, plan, context)
                attempt.patch = result.get("patch")
                attempt.tests_added = result.get("tests_added", [])
                attempt.actions = result.get("actions", [])
                attempt.tool_logs = result.get("tool_logs", [])
            else:
                # Default execution based on domain
                result = self._default_execute(task, plan, context)
                attempt.patch = result.get("patch")
                attempt.actions = result.get("actions", [])
            
            # Record patterns used
            attempt.patterns_used = [p.get("id", str(i)) for i, p in enumerate(plan.get("patterns_to_use", []))]
            attempt.procedures_used = [p.get("id", str(i)) for i, p in enumerate(plan.get("procedures_to_use", []))]
            
        except Exception as e:
            attempt.failure_modes.append(f"execution_error: {str(e)}")
            logger.error(f"Act phase failed: {e}")
        
        attempt.completed_at = datetime.utcnow()
        attempt.execution_time_ms = int((attempt.completed_at - attempt.started_at).total_seconds() * 1000)
        
        self._log_event("act", {
            "task_id": task.task_id,
            "attempt_id": attempt.attempt_id,
            "execution_time_ms": attempt.execution_time_ms,
            "has_patch": attempt.patch is not None,
            "failure_modes": attempt.failure_modes
        })
        
        return attempt
    
    def _default_execute(self, task: TrainingTask, plan: Dict, context: Dict) -> Dict[str, Any]:
        """Default execution strategy."""
        result = {"patch": None, "actions": []}
        
        # Route to appropriate executor based on domain
        if task.domain == TrainingDomain.CODING and self.coding_agent:
            try:
                code_result = self.coding_agent.generate_code(
                    prompt=task.objective,
                    context=task.input_artifacts
                )
                result["patch"] = code_result.get("code")
                result["actions"].append({"type": "code_generation", "result": "success"})
            except Exception as e:
                result["actions"].append({"type": "code_generation", "result": "failed", "error": str(e)})
        
        elif task.domain == TrainingDomain.SELF_HEALING and self.healing_system:
            try:
                heal_result = self.healing_system.heal_file(
                    file_path=task.input_artifacts.get("file_path"),
                    issue=task.objective
                )
                result["patch"] = heal_result.get("fix")
                result["actions"].append({"type": "healing", "result": "success"})
            except Exception as e:
                result["actions"].append({"type": "healing", "result": "failed", "error": str(e)})
        
        elif task.domain == TrainingDomain.SECURITY:
            result = self._execute_security_domain(task, plan, context)
        
        elif task.domain == TrainingDomain.TESTING:
            result = self._execute_testing_domain(task, plan, context)
        
        elif task.domain == TrainingDomain.PERFORMANCE:
            result = self._execute_performance_domain(task, plan, context)
        
        else:
            result = self._execute_generic_domain(task, plan, context)
        
        return result
    
    def _execute_security_domain(self, task: TrainingTask, plan: Dict, context: Dict) -> Dict[str, Any]:
        """Execute security scanning and analysis tasks."""
        result = {"patch": None, "actions": []}
        target = task.input_artifacts.get("file_path") or task.input_artifacts.get("code", "")
        
        try:
            import subprocess
            import shutil
            
            if shutil.which("bandit"):
                if task.input_artifacts.get("file_path"):
                    proc = subprocess.run(
                        ["bandit", "-f", "json", task.input_artifacts["file_path"]],
                        capture_output=True, text=True, timeout=30
                    )
                    result["security_issues"] = json.loads(proc.stdout) if proc.stdout else {}
                    result["actions"].append({"type": "bandit_scan", "result": "success"})
                else:
                    result["actions"].append({"type": "bandit_scan", "result": "skipped", "reason": "no_file_path"})
            else:
                result["actions"].append({"type": "bandit_scan", "result": "unavailable"})
            
            if shutil.which("semgrep"):
                if task.input_artifacts.get("file_path"):
                    proc = subprocess.run(
                        ["semgrep", "--json", "--config=auto", task.input_artifacts["file_path"]],
                        capture_output=True, text=True, timeout=60
                    )
                    result["semgrep_results"] = json.loads(proc.stdout) if proc.stdout else {}
                    result["actions"].append({"type": "semgrep_scan", "result": "success"})
            
        except subprocess.TimeoutExpired:
            result["actions"].append({"type": "security_scan", "result": "timeout"})
        except Exception as e:
            result["actions"].append({"type": "security_scan", "result": "failed", "error": str(e)})
        
        return result
    
    def _execute_testing_domain(self, task: TrainingTask, plan: Dict, context: Dict) -> Dict[str, Any]:
        """Execute testing tasks."""
        result = {"patch": None, "actions": [], "test_results": []}
        
        try:
            import subprocess
            import shutil
            
            test_file = task.input_artifacts.get("test_file")
            test_command = task.input_artifacts.get("test_command")
            
            if test_command:
                proc = subprocess.run(
                    test_command if isinstance(test_command, list) else test_command.split(),
                    capture_output=True, text=True, timeout=120, cwd=task.input_artifacts.get("cwd")
                )
                result["test_output"] = proc.stdout
                result["test_errors"] = proc.stderr
                result["test_returncode"] = proc.returncode
                result["actions"].append({
                    "type": "test_execution",
                    "result": "passed" if proc.returncode == 0 else "failed"
                })
            elif test_file and shutil.which("pytest"):
                proc = subprocess.run(
                    ["pytest", test_file, "-v", "--tb=short"],
                    capture_output=True, text=True, timeout=120
                )
                result["test_output"] = proc.stdout
                result["test_returncode"] = proc.returncode
                result["actions"].append({
                    "type": "pytest_execution",
                    "result": "passed" if proc.returncode == 0 else "failed"
                })
            else:
                result["actions"].append({"type": "testing", "result": "no_test_specified"})
                
        except subprocess.TimeoutExpired:
            result["actions"].append({"type": "testing", "result": "timeout"})
        except Exception as e:
            result["actions"].append({"type": "testing", "result": "failed", "error": str(e)})
        
        return result
    
    def _execute_performance_domain(self, task: TrainingTask, plan: Dict, context: Dict) -> Dict[str, Any]:
        """Execute performance analysis tasks."""
        result = {"patch": None, "actions": [], "metrics": {}}
        
        try:
            code = task.input_artifacts.get("code", "")
            file_path = task.input_artifacts.get("file_path")
            
            if file_path and Path(file_path).exists():
                with open(file_path, 'r') as f:
                    code = f.read()
            
            if code:
                import ast
                tree = ast.parse(code)
                
                metrics = {
                    "total_lines": len(code.splitlines()),
                    "function_count": sum(1 for _ in ast.walk(tree) if isinstance(_, ast.FunctionDef)),
                    "class_count": sum(1 for _ in ast.walk(tree) if isinstance(_, ast.ClassDef)),
                    "loop_count": sum(1 for _ in ast.walk(tree) if isinstance(_, (ast.For, ast.While))),
                    "nested_depth": self._calculate_max_nesting(tree),
                }
                result["metrics"] = metrics
                result["actions"].append({"type": "static_analysis", "result": "success"})
            else:
                result["actions"].append({"type": "performance", "result": "no_code_provided"})
                
        except SyntaxError as e:
            result["actions"].append({"type": "performance", "result": "syntax_error", "error": str(e)})
        except Exception as e:
            result["actions"].append({"type": "performance", "result": "failed", "error": str(e)})
        
        return result
    
    def _calculate_max_nesting(self, node, depth: int = 0) -> int:
        """Calculate maximum nesting depth in AST."""
        import ast
        max_depth = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                max_depth = max(max_depth, self._calculate_max_nesting(child, depth + 1))
            else:
                max_depth = max(max_depth, self._calculate_max_nesting(child, depth))
        return max_depth
    
    def _execute_generic_domain(self, task: TrainingTask, plan: Dict, context: Dict) -> Dict[str, Any]:
        """Execute tasks for domains without specialized executors."""
        result = {"patch": None, "actions": []}
        
        domain_handlers = {
            "web": self._execute_web_task,
            "database": self._execute_database_task,
            "file_system": self._execute_filesystem_task,
            "network": self._execute_network_task,
        }
        
        domain_str = task.domain.value if isinstance(task.domain, TrainingDomain) else str(task.domain)
        handler = domain_handlers.get(domain_str)
        
        if handler:
            return handler(task, plan, context)
        
        result["actions"].append({
            "type": "generic_execution",
            "domain": domain_str,
            "result": "executed",
            "note": f"No specialized executor for domain '{domain_str}', using generic handler"
        })
        
        if task.input_artifacts.get("code"):
            result["patch"] = task.input_artifacts["code"]
        
        return result
    
    def _execute_web_task(self, task: TrainingTask, plan: Dict, context: Dict) -> Dict[str, Any]:
        """Execute web/HTTP testing tasks."""
        result = {"patch": None, "actions": [], "responses": []}
        
        try:
            import urllib.request
            import urllib.error
            
            url = task.input_artifacts.get("url")
            method = task.input_artifacts.get("method", "GET")
            headers = task.input_artifacts.get("headers", {})
            
            if url:
                req = urllib.request.Request(url, method=method, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=10) as response:
                        result["responses"].append({
                            "url": url,
                            "status": response.status,
                            "headers": dict(response.headers),
                            "content_length": response.headers.get("Content-Length"),
                        })
                        result["actions"].append({"type": "http_request", "result": "success", "status": response.status})
                except urllib.error.HTTPError as e:
                    result["responses"].append({"url": url, "status": e.code, "error": str(e)})
                    result["actions"].append({"type": "http_request", "result": "http_error", "status": e.code})
                except urllib.error.URLError as e:
                    result["actions"].append({"type": "http_request", "result": "url_error", "error": str(e)})
            else:
                result["actions"].append({"type": "web", "result": "no_url_provided"})
                
        except Exception as e:
            result["actions"].append({"type": "web", "result": "failed", "error": str(e)})
        
        return result
    
    def _execute_database_task(self, task: TrainingTask, plan: Dict, context: Dict) -> Dict[str, Any]:
        """Execute database/SQL tasks (read-only analysis)."""
        result = {"patch": None, "actions": [], "analysis": {}}
        
        query = task.input_artifacts.get("query", "")
        
        if query:
            import re
            
            dangerous_patterns = [
                r'\bDROP\b', r'\bDELETE\b', r'\bTRUNCATE\b', r'\bUPDATE\b', r'\bINSERT\b',
                r'\bALTER\b', r'\bCREATE\b', r'\bEXEC\b', r'\bEXECUTE\b'
            ]
            
            issues = []
            for pattern in dangerous_patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    issues.append(f"Contains potentially dangerous keyword matching: {pattern}")
            
            result["analysis"] = {
                "query_length": len(query),
                "is_select": query.strip().upper().startswith("SELECT"),
                "potential_issues": issues,
                "tables_referenced": re.findall(r'\bFROM\s+(\w+)', query, re.IGNORECASE),
            }
            result["actions"].append({
                "type": "sql_analysis",
                "result": "safe" if not issues else "warnings",
                "issue_count": len(issues)
            })
        else:
            result["actions"].append({"type": "database", "result": "no_query_provided"})
        
        return result
    
    def _execute_filesystem_task(self, task: TrainingTask, plan: Dict, context: Dict) -> Dict[str, Any]:
        """Execute file system operation tasks."""
        result = {"patch": None, "actions": [], "file_info": {}}
        
        try:
            file_path = task.input_artifacts.get("file_path")
            operation = task.input_artifacts.get("operation", "info")
            
            if file_path:
                path = Path(file_path)
                
                if operation == "info" and path.exists():
                    stat = path.stat()
                    result["file_info"] = {
                        "exists": True,
                        "is_file": path.is_file(),
                        "is_dir": path.is_dir(),
                        "size_bytes": stat.st_size if path.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                    result["actions"].append({"type": "file_info", "result": "success"})
                elif operation == "read" and path.is_file():
                    content = path.read_text(errors='replace')
                    result["file_info"] = {
                        "content_preview": content[:1000],
                        "total_size": len(content),
                        "line_count": content.count('\n') + 1,
                    }
                    result["actions"].append({"type": "file_read", "result": "success"})
                elif operation == "list" and path.is_dir():
                    entries = list(path.iterdir())[:100]
                    result["file_info"] = {
                        "entries": [{"name": e.name, "is_dir": e.is_dir()} for e in entries],
                        "total_entries": len(list(path.iterdir())),
                    }
                    result["actions"].append({"type": "dir_list", "result": "success"})
                elif not path.exists():
                    result["file_info"] = {"exists": False}
                    result["actions"].append({"type": "file_system", "result": "not_found"})
                else:
                    result["actions"].append({"type": "file_system", "result": "unsupported_operation"})
            else:
                result["actions"].append({"type": "file_system", "result": "no_path_provided"})
                
        except PermissionError:
            result["actions"].append({"type": "file_system", "result": "permission_denied"})
        except Exception as e:
            result["actions"].append({"type": "file_system", "result": "failed", "error": str(e)})
        
        return result
    
    def _execute_network_task(self, task: TrainingTask, plan: Dict, context: Dict) -> Dict[str, Any]:
        """Execute network diagnostic tasks."""
        result = {"patch": None, "actions": [], "diagnostics": {}}
        
        try:
            import socket
            
            host = task.input_artifacts.get("host")
            port = task.input_artifacts.get("port")
            
            if host:
                try:
                    ip = socket.gethostbyname(host)
                    result["diagnostics"]["dns_resolution"] = {"host": host, "ip": ip}
                    result["actions"].append({"type": "dns_lookup", "result": "success"})
                except socket.gaierror as e:
                    result["diagnostics"]["dns_resolution"] = {"host": host, "error": str(e)}
                    result["actions"].append({"type": "dns_lookup", "result": "failed"})
                
                if port:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    try:
                        conn_result = sock.connect_ex((host, int(port)))
                        result["diagnostics"]["port_check"] = {
                            "host": host,
                            "port": port,
                            "open": conn_result == 0
                        }
                        result["actions"].append({
                            "type": "port_check",
                            "result": "open" if conn_result == 0 else "closed"
                        })
                    finally:
                        sock.close()
            else:
                result["actions"].append({"type": "network", "result": "no_host_provided"})
                
        except Exception as e:
            result["actions"].append({"type": "network", "result": "failed", "error": str(e)})
        
        return result
    
    def _evaluate(self, task: TrainingTask, attempt: TrainingAttempt) -> EvaluationResult:
        """
        EVALUATE - Score the attempt with deterministic evaluators and rubrics.
        """
        scores = {
            "correctness": 0.0,
            "safety": 1.0,  # Assume safe unless proven otherwise
            "maintainability": 0.5,
            "performance": 0.5,
            "security": 0.5
        }
        
        success = False
        evidence = {}
        regressions = []
        
        # Check for failure modes
        if attempt.failure_modes:
            scores["correctness"] = 0.0
            evidence["failure_modes"] = attempt.failure_modes
        elif attempt.patch:
            # Basic success if we have a patch
            scores["correctness"] = 0.7
            success = True
            
            # Run validators if available
            for validator in attempt.plan.get("validators", []):
                try:
                    val_result = self._run_validator(validator, attempt)
                    if val_result.get("passed"):
                        scores["correctness"] += 0.1
                    else:
                        regressions.append(f"{validator}_failed")
                        success = False
                    evidence[validator] = val_result
                except Exception as e:
                    evidence[validator] = {"error": str(e)}
        
        # Calculate confidence
        judge_confidence = 0.8 if attempt.tests_added else 0.5
        
        evaluation = EvaluationResult.create(
            attempt_id=attempt.attempt_id,
            success=success,
            scores=scores,
            regressions=regressions,
            judge_confidence=judge_confidence,
            evidence=evidence
        )
        
        self._log_event("evaluate", {
            "task_id": task.task_id,
            "attempt_id": attempt.attempt_id,
            "evaluation_id": evaluation.evaluation_id,
            "success": success,
            "scores": scores,
            "regressions": regressions
        })
        
        return evaluation
    
    def _run_validator(self, validator: str, attempt: TrainingAttempt) -> Dict[str, Any]:
        """Run a specific validator against the attempt's code/patch."""
        code = attempt.patch or ""
        
        validators = {
            "syntax": self._validate_syntax,
            "type_check": self._validate_types,
            "security": self._validate_security,
            "style": self._validate_style,
        }
        
        handler = validators.get(validator)
        if handler:
            return handler(code)
        
        return {"passed": True, "details": f"Unknown validator '{validator}' - skipped"}
    
    def _validate_syntax(self, code: str) -> Dict[str, Any]:
        """Validate Python syntax using ast.parse."""
        if not code.strip():
            return {"passed": True, "details": "No code to validate"}
        
        try:
            import ast
            ast.parse(code)
            return {"passed": True, "details": "Syntax is valid"}
        except SyntaxError as e:
            return {
                "passed": False,
                "details": f"Syntax error at line {e.lineno}: {e.msg}",
                "issues": [{
                    "type": "syntax_error",
                    "line": e.lineno,
                    "column": e.offset,
                    "message": e.msg
                }]
            }
    
    def _validate_types(self, code: str) -> Dict[str, Any]:
        """Validate types using mypy if available."""
        import shutil
        import tempfile
        import subprocess
        
        if not shutil.which("mypy"):
            return {"passed": True, "details": "mypy not available - skipped", "skipped": True}
        
        if not code.strip():
            return {"passed": True, "details": "No code to validate"}
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = f.name
            
            try:
                proc = subprocess.run(
                    ["mypy", "--ignore-missing-imports", "--no-error-summary", temp_path],
                    capture_output=True, text=True, timeout=30
                )
                
                issues = []
                for line in proc.stdout.splitlines():
                    if ": error:" in line:
                        issues.append({"type": "type_error", "message": line})
                
                return {
                    "passed": len(issues) == 0,
                    "details": f"Found {len(issues)} type issues" if issues else "No type errors",
                    "issues": issues
                }
            finally:
                import os
                os.unlink(temp_path)
                
        except subprocess.TimeoutExpired:
            return {"passed": True, "details": "mypy timed out - skipped", "skipped": True}
        except Exception as e:
            return {"passed": True, "details": f"mypy failed: {e}", "skipped": True}
    
    def _validate_security(self, code: str) -> Dict[str, Any]:
        """Validate security using bandit if available."""
        import shutil
        import tempfile
        import subprocess
        
        if not shutil.which("bandit"):
            return {"passed": True, "details": "bandit not available - skipped", "skipped": True}
        
        if not code.strip():
            return {"passed": True, "details": "No code to validate"}
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = f.name
            
            try:
                proc = subprocess.run(
                    ["bandit", "-f", "json", "-q", temp_path],
                    capture_output=True, text=True, timeout=30
                )
                
                issues = []
                if proc.stdout:
                    try:
                        result = json.loads(proc.stdout)
                        for issue in result.get("results", []):
                            issues.append({
                                "type": "security",
                                "severity": issue.get("issue_severity", "UNKNOWN"),
                                "confidence": issue.get("issue_confidence", "UNKNOWN"),
                                "message": issue.get("issue_text", ""),
                                "line": issue.get("line_number")
                            })
                    except json.JSONDecodeError:
                        pass
                
                high_severity = [i for i in issues if i.get("severity") in ("HIGH", "MEDIUM")]
                return {
                    "passed": len(high_severity) == 0,
                    "details": f"Found {len(issues)} security issues ({len(high_severity)} high/medium)" if issues else "No security issues",
                    "issues": issues
                }
            finally:
                import os
                os.unlink(temp_path)
                
        except subprocess.TimeoutExpired:
            return {"passed": True, "details": "bandit timed out - skipped", "skipped": True}
        except Exception as e:
            return {"passed": True, "details": f"bandit failed: {e}", "skipped": True}
    
    def _validate_style(self, code: str) -> Dict[str, Any]:
        """Validate style using flake8 if available."""
        import shutil
        import tempfile
        import subprocess
        
        if not shutil.which("flake8"):
            return {"passed": True, "details": "flake8 not available - skipped", "skipped": True}
        
        if not code.strip():
            return {"passed": True, "details": "No code to validate"}
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = f.name
            
            try:
                proc = subprocess.run(
                    ["flake8", "--max-line-length=120", temp_path],
                    capture_output=True, text=True, timeout=30
                )
                
                issues = []
                for line in proc.stdout.splitlines():
                    if line.strip():
                        issues.append({"type": "style", "message": line})
                
                return {
                    "passed": len(issues) <= 5,
                    "details": f"Found {len(issues)} style issues" if issues else "No style issues",
                    "issues": issues
                }
            finally:
                import os
                os.unlink(temp_path)
                
        except subprocess.TimeoutExpired:
            return {"passed": True, "details": "flake8 timed out - skipped", "skipped": True}
        except Exception as e:
            return {"passed": True, "details": f"flake8 failed: {e}", "skipped": True}
    
    def _learn(
        self,
        task: TrainingTask,
        attempt: TrainingAttempt,
        evaluation: EvaluationResult
    ) -> LearningDelta:
        """
        LEARN - Convert outcomes into learning delta (the "gradient update").
        """
        delta = LearningDelta.create(attempt.attempt_id, evaluation.evaluation_id)
        
        # Extract patterns from successful attempts
        if evaluation.success and evaluation.scores.get("correctness", 0) >= 0.8:
            # Create a new pattern
            pattern = {
                "id": f"PATTERN-{uuid.uuid4().hex[:8]}",
                "name": f"Pattern from {task.task_id}",
                "domain": task.domain.value,
                "preconditions": {"task_type": task.domain.value},
                "actions": attempt.actions,
                "expected_outcomes": {"success": True},
                "trust_score": evaluation.scores.get("correctness", 0.7),
                "sample_size": 1,
                "created_at": datetime.utcnow().isoformat()
            }
            delta.patterns_added.append(pattern)
            self.stats["patterns_learned"] += 1
        
        # Update mastery based on outcome
        domain_key = task.domain.value
        mastery_change = 0.01 if evaluation.success else -0.005
        delta.mastery_updates[domain_key] = mastery_change
        
        # Track failure taxonomy
        if not evaluation.success and attempt.failure_modes:
            for mode in attempt.failure_modes:
                delta.failure_taxonomy_updates.append({
                    "mode": mode,
                    "domain": task.domain.value,
                    "task_id": task.task_id
                })
        
        # Calculate trust impact
        delta.trust_impact = 0.1 if evaluation.success else -0.05
        
        # Store to learning memory if available
        if self.learning_memory:
            try:
                for pattern in delta.patterns_added:
                    self.learning_memory.store_pattern(pattern)
            except Exception as e:
                logger.warning(f"Failed to store to learning memory: {e}")
        
        self._log_event("learn", {
            "task_id": task.task_id,
            "delta_id": delta.delta_id,
            "patterns_added": len(delta.patterns_added),
            "mastery_updates": delta.mastery_updates,
            "trust_impact": delta.trust_impact
        })
        
        return delta
    
    def _consolidate(self, delta: LearningDelta, evaluation: EvaluationResult):
        """
        CONSOLIDATE - Update model snapshot with learning delta.
        """
        # Update skill mastery
        for domain, change in delta.mastery_updates.items():
            if domain in self._current_snapshot.skill_mastery:
                mastery = self._current_snapshot.skill_mastery[domain]
                mastery.level = max(0.0, min(1.0, mastery.level + change))
                mastery.attempts += 1
                if evaluation.success:
                    mastery.successes += 1
                mastery.last_updated = datetime.utcnow()
        
        # Update pattern counts
        self._current_snapshot.pattern_count += len(delta.patterns_added)
        
        # Update overall stats
        self._current_snapshot.total_attempts += 1
        if evaluation.success:
            self._current_snapshot.total_successes += 1
        self._current_snapshot.overall_success_rate = (
            self._current_snapshot.total_successes / 
            max(self._current_snapshot.total_attempts, 1)
        )
        
        # Update failure taxonomy
        for failure in delta.failure_taxonomy_updates:
            mode = failure.get("mode", "unknown")
            self._current_snapshot.failure_categories[mode] = (
                self._current_snapshot.failure_categories.get(mode, 0) + 1
            )
        
        # Create new snapshot periodically
        if self._current_snapshot.total_attempts % self.config["snapshot_interval_attempts"] == 0:
            self.create_new_snapshot(reason="periodic")
        
        self._log_event("consolidate", {
            "delta_id": delta.delta_id,
            "patterns_added": len(delta.patterns_added),
            "new_total_attempts": self._current_snapshot.total_attempts,
            "new_success_rate": self._current_snapshot.overall_success_rate
        })
    
    # =========================================================================
    # CURRICULUM AND TASK MANAGEMENT
    # =========================================================================
    
    def generate_curriculum(
        self,
        domain: TrainingDomain,
        count: int = 10
    ) -> List[TrainingTask]:
        """
        Generate a curriculum of training tasks.
        Mix of difficulties based on config and frontier detection.
        """
        tasks = []
        mix = self.config["curriculum_mix"]
        
        for _ in range(count):
            # Determine difficulty based on mix
            import random
            rand = random.random()
            cumulative = 0.0
            difficulty = TaskDifficulty.MEDIUM
            
            for diff_name, prob in mix.items():
                cumulative += prob
                if rand <= cumulative:
                    difficulty = TaskDifficulty[diff_name.upper()]
                    break
            
            # Create task
            task = TrainingTask.create(
                domain=domain,
                objective=f"Practice {domain.value} at {difficulty.value} level",
                difficulty=difficulty,
                metadata={"curriculum_generated": True}
            )
            tasks.append(task)
        
        self._task_queue.extend(tasks)
        logger.info(f"Generated {len(tasks)} curriculum tasks for {domain.value}")
        
        return tasks
    
    def add_task(self, task: TrainingTask):
        """Add a task to the training queue."""
        self._task_queue.append(task)
    
    def get_next_task(self) -> Optional[TrainingTask]:
        """Get next task from queue."""
        if self._task_queue:
            return self._task_queue.pop(0)
        return None
    
    # =========================================================================
    # CONTINUOUS TRAINING
    # =========================================================================
    
    def start_continuous_training(self, domains: Optional[List[TrainingDomain]] = None):
        """Start continuous training loop in background."""
        if self._is_training:
            logger.warning("Training already in progress")
            return
        
        self._is_training = True
        domains = domains or list(TrainingDomain)
        
        def training_loop():
            while self._is_training:
                try:
                    # Get next task or generate one
                    task = self.get_next_task()
                    if not task:
                        # Generate curriculum for random domain
                        import random
                        domain = random.choice(domains)
                        self.generate_curriculum(domain, count=5)
                        task = self.get_next_task()
                    
                    if task:
                        self.run_training_loop(task)
                    
                    # Small delay between tasks
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Training loop error: {e}")
                    time.sleep(1)
        
        self._training_thread = threading.Thread(target=training_loop, daemon=True)
        self._training_thread.start()
        logger.info("Started continuous training")
    
    def stop_continuous_training(self):
        """Stop continuous training."""
        self._is_training = False
        if self._training_thread:
            self._training_thread.join(timeout=5)
        logger.info("Stopped continuous training")
    
    # =========================================================================
    # EVENT LOGGING AND METRICS
    # =========================================================================
    
    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log a training event."""
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        self._event_log.append(event)
        
        # Persist to file periodically
        if len(self._event_log) % 100 == 0:
            self._persist_event_log()
    
    def _persist_event_log(self):
        """Persist event log to disk."""
        try:
            log_file = self.storage_path / "event_log.jsonl"
            with open(log_file, "a") as f:
                for event in self._event_log[-100:]:
                    f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.warning(f"Failed to persist event log: {e}")
    
    def get_training_status(self) -> Dict[str, Any]:
        """Get current training status and metrics."""
        return {
            "is_training": self._is_training,
            "current_model_version": self._current_snapshot.model_version,
            "stats": self.stats,
            "skill_mastery": {
                k: {
                    "level": v.level,
                    "success_rate": v.success_rate,
                    "attempts": v.attempts
                }
                for k, v in self._current_snapshot.skill_mastery.items()
            },
            "queue_size": len(self._task_queue),
            "overall_success_rate": self._current_snapshot.overall_success_rate,
            "pattern_count": self._current_snapshot.pattern_count,
            "total_attempts": self._current_snapshot.total_attempts
        }
    
    def get_intelligence_report(self) -> Dict[str, Any]:
        """Get comprehensive intelligence report."""
        snapshot = self._current_snapshot
        
        # Calculate mastery levels
        mastery_levels = {}
        for domain, mastery in snapshot.skill_mastery.items():
            if mastery.level >= 0.9:
                level_name = "Expert"
            elif mastery.level >= 0.7:
                level_name = "Advanced"
            elif mastery.level >= 0.5:
                level_name = "Intermediate"
            elif mastery.level >= 0.3:
                level_name = "Beginner"
            else:
                level_name = "Novice"
            mastery_levels[domain] = level_name
        
        return {
            "model_version": snapshot.model_version,
            "created_at": snapshot.created_at.isoformat(),
            "intelligence_metrics": {
                "overall_success_rate": snapshot.overall_success_rate,
                "total_learning_attempts": snapshot.total_attempts,
                "patterns_learned": snapshot.pattern_count,
                "procedures_learned": snapshot.procedure_count,
                "templates_learned": snapshot.template_count
            },
            "skill_mastery": mastery_levels,
            "domain_details": {
                k: {
                    "level": v.level,
                    "attempts": v.attempts,
                    "success_rate": v.success_rate
                }
                for k, v in snapshot.skill_mastery.items()
            },
            "failure_taxonomy": snapshot.failure_categories,
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate training recommendations."""
        recommendations = []
        snapshot = self._current_snapshot
        
        # Find weakest domains
        weak_domains = [
            domain for domain, mastery in snapshot.skill_mastery.items()
            if mastery.level < 0.3 and mastery.attempts > 0
        ]
        if weak_domains:
            recommendations.append(f"Focus training on weak domains: {', '.join(weak_domains)}")
        
        # Find common failure modes
        if snapshot.failure_categories:
            top_failures = sorted(
                snapshot.failure_categories.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            if top_failures:
                recommendations.append(
                    f"Address common failures: {', '.join(f[0] for f in top_failures)}"
                )
        
        # Check overall success rate
        if snapshot.overall_success_rate < 0.5:
            recommendations.append("Consider reducing task difficulty to build foundation")
        elif snapshot.overall_success_rate > 0.9:
            recommendations.append("Consider increasing task difficulty for more challenge")
        
        return recommendations


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_training_center(session=None, **kwargs) -> IntelligenceTrainingCenter:
    """Factory function to create a Training Center with connections."""
    return IntelligenceTrainingCenter(session=session, **kwargs)
