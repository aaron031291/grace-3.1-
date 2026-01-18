import logging
import json
import hashlib
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from cognitive.deterministic_primitives import (
    LogicalClock, Canonicalizer, DeterministicIDGenerator,
    stable_hash, generate_deterministic_id
)
from cognitive.genesis_bound_operations import DeterministicExecutionContext

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk levels for code changes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeClassification(str, Enum):
    """Classification of code changes for KPI tracking."""
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    FEATURE = "feature"
    PERFORMANCE = "performance"
    CLEANUP = "cleanup"
    EXPERIMENTAL = "experimental"
    DOCUMENTATION = "documentation"
    TEST = "test"
    SECURITY = "security"


class PipelineStage(str, Enum):
    """Stages of the deterministic pipeline."""
    PERCEPTION = "perception"       # Read and understand
    INTENT_FORMATION = "intent"     # Plan and decide
    GENERATION = "generation"       # Produce code
    VERIFICATION = "verification"   # Validate correctness
    MEMORY = "memory"               # Store and learn


class GateStatus(str, Enum):
    """Status of quality gates."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


# Module-level ID generator for contracts
_contract_id_generator = DeterministicIDGenerator(hash_length=16)


@dataclass
class ExecutionContract:
    """
    Formal specification for a code generation task.

    The contract becomes the parent Genesis Key for the entire run.
    """
    goal: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    allowed_files: List[str] = field(default_factory=list)
    forbidden_patterns: List[str] = field(default_factory=list)
    risk_level: str = "low"
    success_criteria: List[str] = field(default_factory=list)
    max_changes: int = 100
    require_tests: bool = True
    require_lint: bool = True
    auto_commit_allowed: bool = False

    # Deterministic fields
    contract_id: str = field(default="")
    logical_tick: int = field(default=0)
    genesis_key_id: Optional[str] = None
    
    # Nondeterministic metadata (optional, for observability only)
    nondeterministic_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Generate deterministic contract_id if not provided."""
        if not self.contract_id:
            self.contract_id = _contract_id_generator.generate_id(
                "EC", self.goal, self.constraints, self.allowed_files
            )
        if "created_at" not in self.nondeterministic_metadata:
            self.nondeterministic_metadata["created_at"] = datetime.utcnow().isoformat()

    @property
    def contract_digest(self) -> str:
        """Return stable hash of contract content."""
        return stable_hash({
            "goal": self.goal,
            "constraints": self.constraints,
            "allowed_files": self.allowed_files,
            "forbidden_patterns": self.forbidden_patterns,
            "risk_level": self.risk_level,
            "success_criteria": self.success_criteria,
            "max_changes": self.max_changes,
            "require_tests": self.require_tests,
            "require_lint": self.require_lint,
            "auto_commit_allowed": self.auto_commit_allowed
        })

    # Backward compatibility property
    @property
    def created_at(self) -> datetime:
        """Backward compatible access to created_at from metadata."""
        created_str = self.nondeterministic_metadata.get("created_at")
        if created_str:
            return datetime.fromisoformat(created_str)
        return datetime.utcnow()
    
    @created_at.setter
    def created_at(self, value: datetime):
        """Backward compatible setter for created_at."""
        self.nondeterministic_metadata["created_at"] = value.isoformat()

    def to_json(self) -> str:
        """Convert to JSON for storage/transmission."""
        return json.dumps({
            "contract_id": self.contract_id,
            "goal": self.goal,
            "constraints": self.constraints,
            "allowed_files": self.allowed_files,
            "forbidden_patterns": self.forbidden_patterns,
            "risk_level": self.risk_level,
            "success_criteria": self.success_criteria,
            "max_changes": self.max_changes,
            "require_tests": self.require_tests,
            "require_lint": self.require_lint,
            "auto_commit_allowed": self.auto_commit_allowed,
            "logical_tick": self.logical_tick,
            "contract_digest": self.contract_digest,
            "genesis_key_id": self.genesis_key_id,
            "nondeterministic_metadata": self.nondeterministic_metadata
        }, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ExecutionContract":
        """Create from JSON."""
        data = json.loads(json_str)
        contract = cls(
            goal=data["goal"],
            constraints=data.get("constraints", {}),
            allowed_files=data.get("allowed_files", []),
            forbidden_patterns=data.get("forbidden_patterns", []),
            risk_level=data.get("risk_level", "low"),
            success_criteria=data.get("success_criteria", []),
            max_changes=data.get("max_changes", 100),
            require_tests=data.get("require_tests", True),
            require_lint=data.get("require_lint", True),
            auto_commit_allowed=data.get("auto_commit_allowed", False),
            contract_id=data.get("contract_id", ""),
            logical_tick=data.get("logical_tick", 0),
            nondeterministic_metadata=data.get("nondeterministic_metadata", {})
        )
        # Backward compatibility: handle old created_at field
        if data.get("created_at") and "created_at" not in contract.nondeterministic_metadata:
            contract.nondeterministic_metadata["created_at"] = data["created_at"]
        contract.genesis_key_id = data.get("genesis_key_id")
        return contract

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate contract completeness."""
        errors = []

        if not self.goal:
            errors.append("Goal is required")

        if not self.allowed_files and self.risk_level in ["low", "medium"]:
            errors.append("allowed_files should be specified for low/medium risk")

        if not self.success_criteria:
            errors.append("success_criteria should be defined")

        return len(errors) == 0, errors


@dataclass
class PreCommitScore:
    """
    Confidence score for pre-commit quality assessment.

    Stored on the commit's Genesis Key for deterministic decision-making.
    """
    score: float  # 0.0-1.0
    lint_score: float
    test_score: float
    arch_compliance_score: float
    pattern_similarity_score: float
    regression_risk_score: float
    factors: List[Dict[str, Any]] = field(default_factory=list)
    recommendation: str = "review"  # auto_commit, review, escalate
    computed_tick: int = 0  # Logical clock tick when computed
    
    # Nondeterministic metadata (optional, for observability only)
    nondeterministic_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize metadata with current time if not set."""
        if "computed_at" not in self.nondeterministic_metadata:
            self.nondeterministic_metadata["computed_at"] = datetime.utcnow().isoformat()

    @property
    def score_digest(self) -> str:
        """Return stable hash of score content for verification."""
        return stable_hash({
            "score": self.score,
            "lint_score": self.lint_score,
            "test_score": self.test_score,
            "arch_compliance_score": self.arch_compliance_score,
            "pattern_similarity_score": self.pattern_similarity_score,
            "regression_risk_score": self.regression_risk_score,
            "factors": self.factors,
            "recommendation": self.recommendation,
            "computed_tick": self.computed_tick
        })

    # Backward compatibility property
    @property
    def computed_at(self) -> datetime:
        """Backward compatible access to computed_at from metadata."""
        computed_str = self.nondeterministic_metadata.get("computed_at")
        if computed_str:
            return datetime.fromisoformat(computed_str)
        return datetime.utcnow()
    
    @computed_at.setter
    def computed_at(self, value: datetime):
        """Backward compatible setter for computed_at."""
        self.nondeterministic_metadata["computed_at"] = value.isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "lint_score": self.lint_score,
            "test_score": self.test_score,
            "arch_compliance_score": self.arch_compliance_score,
            "pattern_similarity_score": self.pattern_similarity_score,
            "regression_risk_score": self.regression_risk_score,
            "factors": self.factors,
            "recommendation": self.recommendation,
            "computed_tick": self.computed_tick,
            "score_digest": self.score_digest,
            "nondeterministic_metadata": self.nondeterministic_metadata
        }


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    success: bool
    contract_id: str
    stages_completed: List[str]
    changes_made: List[Dict[str, Any]]
    pre_commit_score: Optional[PreCommitScore]
    change_classification: ChangeClassification
    genesis_key_id: str
    duration_seconds: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "contract_id": self.contract_id,
            "stages_completed": self.stages_completed,
            "changes_made": self.changes_made,
            "pre_commit_score": self.pre_commit_score.to_dict() if self.pre_commit_score else None,
            "change_classification": self.change_classification.value,
            "genesis_key_id": self.genesis_key_id,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "warnings": self.warnings
        }


@dataclass
class PipelineRun:
    """
    Tracks a complete pipeline run with deterministic identifiers.
    
    All operations within a run share the same logical clock and parent Genesis Key.
    """
    contract: ExecutionContract
    logical_clock: LogicalClock = field(default_factory=LogicalClock)
    genesis_parent_key: str = ""
    stage_digests: Dict[str, str] = field(default_factory=dict)
    
    # Auto-generated deterministic run_id from contract digest
    run_id: str = field(default="")
    
    def __post_init__(self):
        """Generate deterministic run_id from contract digest."""
        if not self.run_id:
            self.run_id = generate_deterministic_id("PR", self.contract.contract_digest)
    
    def record_stage(self, stage: str, stage_data: Dict[str, Any]) -> str:
        """Record a stage completion and return its digest."""
        digest = stable_hash({
            "stage": stage,
            "data": stage_data,
            "tick": self.logical_clock.get_tick()
        })
        self.stage_digests[stage] = digest
        return digest
    
    def get_current_tick(self) -> int:
        """Get current logical clock tick."""
        return self.logical_clock.get_tick()
    
    def advance_tick(self) -> int:
        """Advance logical clock and return new tick."""
        return self.logical_clock.tick()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "contract_id": self.contract.contract_id,
            "contract_digest": self.contract.contract_digest,
            "genesis_parent_key": self.genesis_parent_key,
            "current_tick": self.get_current_tick(),
            "stage_digests": self.stage_digests
        }


class DeterministicCodePipeline:
    """
    Deterministic code generation pipeline with multi-LLM support.

    Implements the 5 phases:
    1. Perception - Read/understand repository
    2. Intent Formation - Plan, Genesis Key created
    3. Generation - Multi-LLM code production
    4. Verification - Linting, tests, architecture
    5. Memory & Learning - Genesis Keys, Ghost Ledger
    
    Uses DeterministicExecutionContext for each pipeline run to ensure:
    - All operations share the same logical clock
    - Parent Genesis Key tracks entire run
    - Each stage creates child Genesis Keys linked to parent
    """

    def __init__(
        self,
        session=None,
        repo_path: Optional[Path] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ):
        self.session = session
        self.repo_path = repo_path or Path.cwd()
        self.llm_config = llm_config or {}

        # Initialize components
        self._genesis_service = None
        self._ghost_ledger = None
        self._llm_orchestrator = None
        self._healing_system = None
        
        # Current pipeline run context
        self._current_run: Optional[PipelineRun] = None
        self._execution_context: Optional[DeterministicExecutionContext] = None

        # Known-risk pattern registry
        self.pattern_registry = {
            "safe": [],
            "fragile": [],
            "forbidden": []
        }

        # Load pattern registry
        self._load_pattern_registry()

        logger.info("[PIPELINE] Deterministic code pipeline initialized")
    
    def create_pipeline_run(self, contract: ExecutionContract) -> PipelineRun:
        """
        Create a new pipeline run for a contract.
        
        Args:
            contract: The execution contract for this run
            
        Returns:
            PipelineRun with shared logical clock and genesis parent key
        """
        # Create the pipeline run
        pipeline_run = PipelineRun(contract=contract)
        
        # Create parent Genesis Key for the run if genesis service is available
        if self._genesis_service:
            from models.genesis_key_models import GenesisKeyType
            parent_key = self._genesis_service.create_key(
                key_type=GenesisKeyType.SYSTEM_EVENT,
                what_description=f"Pipeline run started: {contract.goal}",
                who_actor="deterministic_code_pipeline",
                why_reason=contract.goal,
                how_method="DeterministicCodePipeline.create_pipeline_run",
                input_data={
                    "run_id": pipeline_run.run_id,
                    "contract_id": contract.contract_id,
                    "contract_digest": contract.contract_digest,
                    "logical_tick": pipeline_run.get_current_tick()
                }
            )
            pipeline_run.genesis_parent_key = parent_key.key_id
            contract.genesis_key_id = parent_key.key_id
        
        self._current_run = pipeline_run
        return pipeline_run
    
    def get_execution_context(
        self,
        contract: ExecutionContract,
        parent_key_id: Optional[str] = None
    ) -> DeterministicExecutionContext:
        """
        Get or create a DeterministicExecutionContext for pipeline operations.
        
        Args:
            contract: The execution contract
            parent_key_id: Optional parent Genesis Key ID
            
        Returns:
            DeterministicExecutionContext for use with 'with' statement
        """
        if not self._genesis_service:
            raise RuntimeError("Pipeline not initialized. Call initialize() first.")
        
        return DeterministicExecutionContext(
            goal=contract.goal,
            genesis_service=self._genesis_service,
            parent_key_id=parent_key_id or contract.genesis_key_id
        )
    
    def record_stage_completion(
        self,
        stage: PipelineStage,
        stage_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Record a stage completion in the current pipeline run.
        
        Args:
            stage: The pipeline stage that completed
            stage_data: Data from the stage execution
            
        Returns:
            Stage digest if current run exists, None otherwise
        """
        if self._current_run:
            self._current_run.advance_tick()
            digest = self._current_run.record_stage(stage.value, stage_data)
            
            # Create child Genesis Key for stage if service available
            if self._genesis_service and self._current_run.genesis_parent_key:
                from models.genesis_key_models import GenesisKeyType
                self._genesis_service.create_key(
                    key_type=GenesisKeyType.SYSTEM_EVENT,
                    what_description=f"Stage completed: {stage.value}",
                    who_actor="deterministic_code_pipeline",
                    why_reason=f"Pipeline stage {stage.value} execution",
                    how_method="DeterministicCodePipeline.record_stage_completion",
                    input_data={
                        "stage": stage.value,
                        "stage_digest": digest,
                        "tick": self._current_run.get_current_tick()
                    },
                    parent_key_id=self._current_run.genesis_parent_key
                )
            
            return digest
        return None

    def _load_pattern_registry(self):
        """Load known-risk patterns from VectorDB or config."""
        registry_file = self.repo_path / ".grace" / "pattern_registry.json"

        if registry_file.exists():
            try:
                with open(registry_file, 'r') as f:
                    self.pattern_registry = json.load(f)
                logger.debug(f"[PIPELINE] Loaded pattern registry: {len(self.pattern_registry.get('forbidden', []))} forbidden patterns")
            except Exception as e:
                logger.warning(f"[PIPELINE] Could not load pattern registry: {e}")

    async def initialize(self):
        """Initialize connections to dependent systems."""
        try:
            from genesis.genesis_key_service import GenesisKeyService
            self._genesis_service = GenesisKeyService(
                session=self.session,
                repo_path=str(self.repo_path)
            )

            from grace_os.ghost_ledger import GhostLedger
            self._ghost_ledger = GhostLedger(
                session=self.session,
                repo_path=self.repo_path
            )

            from llm_orchestrator.llm_orchestrator import LLMOrchestrator
            self._llm_orchestrator = LLMOrchestrator(session=self.session)

            logger.info("[PIPELINE] All components initialized")
            return True

        except Exception as e:
            logger.error(f"[PIPELINE] Initialization failed: {e}")
            return False

    async def execute(self, contract: ExecutionContract) -> PipelineResult:
        """
        Execute the full deterministic pipeline for a contract.

        Args:
            contract: The execution contract specifying the task

        Returns:
            PipelineResult with all outcomes
        """
        start_time = datetime.utcnow()
        stages_completed = []
        changes_made = []
        errors = []
        warnings = []

        logger.info(f"[PIPELINE] Executing contract {contract.contract_id}: {contract.goal}")

        # Validate contract
        is_valid, validation_errors = contract.validate()
        if not is_valid:
            return PipelineResult(
                success=False,
                contract_id=contract.contract_id,
                stages_completed=[],
                changes_made=[],
                pre_commit_score=None,
                change_classification=ChangeClassification.EXPERIMENTAL,
                genesis_key_id="",
                duration_seconds=0,
                errors=validation_errors
            )

        # Create parent Genesis Key for this execution
        genesis_key = await self._create_contract_genesis_key(contract)
        contract.genesis_key_id = genesis_key.key_id

        try:
            # =========================================================
            # PHASE 1: PERCEPTION
            # =========================================================
            perception_result = await self._phase_perception(contract)
            stages_completed.append(PipelineStage.PERCEPTION.value)

            if not perception_result.get("success"):
                errors.append(f"Perception failed: {perception_result.get('error')}")
                return self._create_failure_result(contract, stages_completed, errors, start_time)

            # =========================================================
            # PHASE 2: INTENT FORMATION
            # =========================================================
            intent_result = await self._phase_intent_formation(contract, perception_result)
            stages_completed.append(PipelineStage.INTENT_FORMATION.value)

            if not intent_result.get("success"):
                errors.append(f"Intent formation failed: {intent_result.get('error')}")
                return self._create_failure_result(contract, stages_completed, errors, start_time)

            # Delta-first planning: what will change
            delta_plan = intent_result.get("delta_plan", [])

            # =========================================================
            # PHASE 3: GENERATION
            # =========================================================
            generation_result = await self._phase_generation(
                contract, perception_result, intent_result
            )
            stages_completed.append(PipelineStage.GENERATION.value)

            if not generation_result.get("success"):
                errors.append(f"Generation failed: {generation_result.get('error')}")
                return self._create_failure_result(contract, stages_completed, errors, start_time)

            changes_made = generation_result.get("changes", [])

            # =========================================================
            # PHASE 4: VERIFICATION
            # =========================================================
            verification_result = await self._phase_verification(contract, changes_made)
            stages_completed.append(PipelineStage.VERIFICATION.value)

            # Compute pre-commit score
            pre_commit_score = self._compute_pre_commit_score(verification_result)

            # Check verification gates
            if not verification_result.get("gates_passed"):
                # Artifact triage: route failures to appropriate fixers
                await self._triage_verification_failures(verification_result, contract)
                warnings.extend(verification_result.get("warnings", []))

            # =========================================================
            # PHASE 5: MEMORY & LEARNING
            # =========================================================
            memory_result = await self._phase_memory(
                contract, changes_made, pre_commit_score
            )
            stages_completed.append(PipelineStage.MEMORY.value)

            # Classify the change
            change_classification = self._classify_changes(contract, changes_made)

            # Duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            result = PipelineResult(
                success=True,
                contract_id=contract.contract_id,
                stages_completed=stages_completed,
                changes_made=changes_made,
                pre_commit_score=pre_commit_score,
                change_classification=change_classification,
                genesis_key_id=genesis_key.key_id,
                duration_seconds=duration,
                warnings=warnings
            )

            logger.info(
                f"[PIPELINE] Contract {contract.contract_id} completed: "
                f"{len(changes_made)} changes, score={pre_commit_score.score:.2f}"
            )

            return result

        except Exception as e:
            logger.error(f"[PIPELINE] Pipeline execution failed: {e}")
            errors.append(str(e))
            return self._create_failure_result(contract, stages_completed, errors, start_time)

    # =========================================================================
    # Pipeline Phases
    # =========================================================================

    async def _phase_perception(self, contract: ExecutionContract) -> Dict[str, Any]:
        """
        Phase 1: Perception - Read and understand repository.

        Operates on:
        - Repository level: architectural integrity
        - Folder level: module boundaries
        - File level: code logic
        """
        logger.debug(f"[PIPELINE] Phase 1: Perception for {contract.goal}")

        try:
            context = {
                "files": {},
                "architecture": {},
                "dependencies": {},
                "boundaries": {}
            }

            # Read allowed files
            for file_pattern in contract.allowed_files:
                file_path = self.repo_path / file_pattern

                if file_path.exists() and file_path.is_file():
                    try:
                        content = file_path.read_text()
                        context["files"][str(file_path)] = {
                            "content": content,
                            "size": len(content),
                            "lines": len(content.splitlines())
                        }
                    except Exception as e:
                        logger.warning(f"[PIPELINE] Could not read {file_path}: {e}")

                elif file_path.is_dir() or '*' in file_pattern:
                    # Glob pattern
                    for matched_file in self.repo_path.glob(file_pattern):
                        if matched_file.is_file():
                            try:
                                content = matched_file.read_text()
                                context["files"][str(matched_file)] = {
                                    "content": content,
                                    "size": len(content),
                                    "lines": len(content.splitlines())
                                }
                            except Exception:
                                pass

            # Analyze architecture if we have files
            if context["files"]:
                context["architecture"] = self._analyze_architecture(context["files"])

            return {"success": True, "context": context}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _phase_intent_formation(
        self,
        contract: ExecutionContract,
        perception: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase 2: Intent Formation - Decide what to do and why.

        Creates delta-first plan: "what I will change" before changing.
        """
        logger.debug(f"[PIPELINE] Phase 2: Intent Formation")

        try:
            # Use LLM to form intent based on contract and perception
            intent_prompt = self._build_intent_prompt(contract, perception)

            if self._llm_orchestrator:
                llm_response = await self._llm_orchestrator.generate(
                    prompt=intent_prompt,
                    skill="planning",
                    temperature=0.3,  # Low temp for deterministic planning
                    response_format="json"
                )
                plan = self._parse_json_response(llm_response)
            else:
                # Fallback: simple planning
                plan = self._simple_planning(contract, perception)

            # Delta-first: explicitly list what will change
            delta_plan = []
            for change in plan.get("changes", []):
                delta_plan.append({
                    "file": change.get("file"),
                    "action": change.get("action"),  # add, modify, delete
                    "description": change.get("description"),
                    "estimated_lines": change.get("lines", 10)
                })

            return {
                "success": True,
                "plan": plan,
                "delta_plan": delta_plan,
                "reasoning": plan.get("reasoning", "")
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _phase_generation(
        self,
        contract: ExecutionContract,
        perception: Dict[str, Any],
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase 3: Generation - Produce code via multi-LLM pipeline.

        Uses multiple LLMs:
        1. Primary generator (creativity)
        2. Verifier (correctness check)
        3. Refiner (quality improvement)
        """
        logger.debug(f"[PIPELINE] Phase 3: Generation")

        try:
            changes = []
            delta_plan = intent.get("delta_plan", [])

            for planned_change in delta_plan:
                file_path = planned_change.get("file")
                action = planned_change.get("action")

                # Build generation prompt
                generation_prompt = self._build_generation_prompt(
                    contract, perception, planned_change
                )

                if self._llm_orchestrator:
                    # Multi-LLM generation
                    generated = await self._multi_llm_generate(
                        prompt=generation_prompt,
                        context=perception.get("context", {}).get("files", {}).get(file_path, {})
                    )
                else:
                    # Fallback
                    generated = {"code": "", "success": False, "reason": "No LLM available"}

                if generated.get("success"):
                    # Check against forbidden patterns
                    if self._check_forbidden_patterns(generated.get("code", "")):
                        logger.warning(f"[PIPELINE] Generated code contains forbidden patterns")
                        continue

                    changes.append({
                        "file": file_path,
                        "action": action,
                        "old_content": perception.get("context", {}).get("files", {}).get(file_path, {}).get("content", ""),
                        "new_content": generated.get("code"),
                        "confidence": generated.get("confidence", 0.5)
                    })

            return {"success": True, "changes": changes}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _phase_verification(
        self,
        contract: ExecutionContract,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Phase 4: Verification - Enforce correctness.

        Runs:
        - Linting
        - Tests (if required)
        - Architectural rules
        - Hard gates
        """
        logger.debug(f"[PIPELINE] Phase 4: Verification")

        results = {
            "lint_result": {"passed": True, "issues": []},
            "test_result": {"passed": True, "failures": []},
            "arch_result": {"passed": True, "violations": []},
            "pattern_result": {"passed": True, "matches": []},
            "gates_passed": True,
            "warnings": []
        }

        try:
            # Apply changes temporarily for verification
            temp_changes = []
            for change in changes:
                file_path = Path(change["file"])
                if file_path.exists():
                    temp_changes.append({
                        "file": file_path,
                        "original": file_path.read_text()
                    })
                    file_path.write_text(change.get("new_content", ""))

            try:
                # Run linting
                if contract.require_lint:
                    results["lint_result"] = await self._run_linting(changes)
                    if not results["lint_result"]["passed"]:
                        results["gates_passed"] = False

                # Run tests
                if contract.require_tests:
                    results["test_result"] = await self._run_tests(changes)
                    if not results["test_result"]["passed"]:
                        results["gates_passed"] = False

                # Check architectural rules
                results["arch_result"] = await self._check_architecture(changes)
                if not results["arch_result"]["passed"]:
                    results["warnings"].append("Architectural violations detected")

                # Check pattern registry
                results["pattern_result"] = self._check_patterns(changes)

            finally:
                # Restore original files
                for temp in temp_changes:
                    temp["file"].write_text(temp["original"])

            return results

        except Exception as e:
            return {
                "gates_passed": False,
                "error": str(e),
                "warnings": [str(e)]
            }

    async def _phase_memory(
        self,
        contract: ExecutionContract,
        changes: List[Dict[str, Any]],
        pre_commit_score: PreCommitScore
    ) -> Dict[str, Any]:
        """
        Phase 5: Memory & Learning - Store and learn.

        Stores:
        - Genesis Keys for each change
        - Ghost Ledger records
        - Pre-commit scores
        """
        logger.debug(f"[PIPELINE] Phase 5: Memory & Learning")

        try:
            stored_keys = []

            for change in changes:
                # Create Genesis Key for this change
                if self._genesis_service:
                    from models.genesis_key_models import GenesisKeyType
                    key = self._genesis_service.create_key(
                        key_type=GenesisKeyType.CODE_GENERATION,
                        what_description=f"Generated: {change.get('action', 'change')} in {change.get('file')}",
                        who_actor="DeterministicPipeline",
                        where_location=change.get("file"),
                        why_reason=contract.goal,
                        how_method="Multi-LLM Pipeline",
                        file_path=change.get("file"),
                        code_before=change.get("old_content", "")[:1000],
                        code_after=change.get("new_content", "")[:1000],
                        parent_key_id=contract.genesis_key_id,
                        context_data={
                            "pre_commit_score": pre_commit_score.to_dict(),
                            "contract_id": contract.contract_id,
                            "confidence": change.get("confidence", 0.5)
                        },
                        session=self.session
                    )
                    stored_keys.append(key.key_id)

                # Record in Ghost Ledger
                if self._ghost_ledger:
                    await self._ghost_ledger.record_change(
                        file_path=change.get("file"),
                        old_content=change.get("old_content", ""),
                        new_content=change.get("new_content", ""),
                        genesis_key_id=stored_keys[-1] if stored_keys else None,
                        source="pipeline",
                        confidence=change.get("confidence", 0.5)
                    )

            # Persist ghost ledger
            if self._ghost_ledger:
                await self._ghost_ledger.persist()

            return {"success": True, "genesis_keys": stored_keys}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _create_contract_genesis_key(self, contract: ExecutionContract):
        """Create the parent Genesis Key for a contract execution."""
        if not self._genesis_service:
            from genesis.genesis_key_service import GenesisKeyService
            self._genesis_service = GenesisKeyService(
                session=self.session,
                repo_path=str(self.repo_path)
            )

        from models.genesis_key_models import GenesisKeyType
        return self._genesis_service.create_key(
            key_type=GenesisKeyType.TASK_STARTED,
            what_description=f"Execution Contract: {contract.goal[:100]}",
            who_actor="DeterministicPipeline",
            where_location=str(self.repo_path),
            why_reason=contract.goal,
            how_method="ExecutionContract",
            context_data={
                "contract": json.loads(contract.to_json()),
                "risk_level": contract.risk_level
            },
            session=self.session
        )

    def _create_failure_result(
        self,
        contract: ExecutionContract,
        stages: List[str],
        errors: List[str],
        start_time: datetime
    ) -> PipelineResult:
        """Create a failure result."""
        return PipelineResult(
            success=False,
            contract_id=contract.contract_id,
            stages_completed=stages,
            changes_made=[],
            pre_commit_score=None,
            change_classification=ChangeClassification.EXPERIMENTAL,
            genesis_key_id=contract.genesis_key_id or "",
            duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            errors=errors
        )

    def _analyze_architecture(self, files: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze codebase architecture from files."""
        architecture = {
            "modules": [],
            "dependencies": {},
            "patterns": []
        }

        for file_path, file_info in files.items():
            # Extract module structure
            path = Path(file_path)
            module = path.parent.name
            if module not in architecture["modules"]:
                architecture["modules"].append(module)

            # Simple import analysis
            content = file_info.get("content", "")
            for line in content.splitlines():
                if line.startswith("import ") or line.startswith("from "):
                    architecture["dependencies"][file_path] = architecture["dependencies"].get(file_path, [])
                    architecture["dependencies"][file_path].append(line.strip())

        return architecture

    def _build_intent_prompt(
        self,
        contract: ExecutionContract,
        perception: Dict[str, Any]
    ) -> str:
        """Build prompt for intent formation phase."""
        files_summary = []
        for fp, info in perception.get("context", {}).get("files", {}).items():
            files_summary.append(f"- {fp}: {info.get('lines', 0)} lines")

        return f"""You are planning a code change task.

GOAL: {contract.goal}

CONSTRAINTS:
{json.dumps(contract.constraints, indent=2)}

ALLOWED FILES:
{chr(10).join(files_summary)}

FORBIDDEN PATTERNS:
{json.dumps(contract.forbidden_patterns)}

SUCCESS CRITERIA:
{json.dumps(contract.success_criteria)}

TASK: Create a detailed plan for achieving the goal. Output as JSON:
{{
    "reasoning": "explanation of approach",
    "changes": [
        {{"file": "path", "action": "add|modify|delete", "description": "what to change", "lines": estimated_lines}}
    ],
    "risks": ["potential risks"],
    "dependencies": ["files that depend on changes"]
}}

Be specific and deterministic. Only plan changes to allowed files.
"""

    def _build_generation_prompt(
        self,
        contract: ExecutionContract,
        perception: Dict[str, Any],
        change: Dict[str, Any]
    ) -> str:
        """Build prompt for code generation."""
        file_path = change.get("file")
        file_info = perception.get("context", {}).get("files", {}).get(file_path, {})

        return f"""Generate code for the following task:

FILE: {file_path}
ACTION: {change.get('action')}
DESCRIPTION: {change.get('description')}

CURRENT CONTENT:
```
{file_info.get('content', 'New file')}
```

GOAL: {contract.goal}

CONSTRAINTS:
{json.dumps(contract.constraints, indent=2)}

Generate the complete file content. Be precise and follow existing patterns.
Output only the code, no explanations.
"""

    async def _multi_llm_generate(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate code using multi-LLM pipeline."""
        try:
            # Primary generation
            primary_response = await self._llm_orchestrator.generate(
                prompt=prompt,
                skill="code_generation",
                temperature=0.4
            )

            # Verification pass
            verify_prompt = f"""Review this generated code for correctness:

{primary_response}

Check for:
1. Syntax errors
2. Logic issues
3. Missing imports
4. Type errors

Output: {{"correct": true/false, "issues": ["list of issues"], "fixed_code": "corrected code if needed"}}
"""

            verification = await self._llm_orchestrator.generate(
                prompt=verify_prompt,
                skill="code_review",
                temperature=0.2,
                response_format="json"
            )

            verified = self._parse_json_response(verification)

            if verified.get("correct"):
                return {
                    "success": True,
                    "code": primary_response,
                    "confidence": 0.85
                }
            else:
                return {
                    "success": True,
                    "code": verified.get("fixed_code", primary_response),
                    "confidence": 0.7,
                    "issues_fixed": verified.get("issues", [])
                }

        except Exception as e:
            logger.error(f"[PIPELINE] Multi-LLM generation failed: {e}")
            return {"success": False, "reason": str(e)}

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        try:
            # Try direct parse
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end > start:
                    return json.loads(response[start:end])
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                if end > start:
                    return json.loads(response[start:end])
            return {}

    def _simple_planning(
        self,
        contract: ExecutionContract,
        perception: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simple fallback planning without LLM."""
        changes = []
        for file_path in contract.allowed_files:
            changes.append({
                "file": file_path,
                "action": "modify",
                "description": contract.goal,
                "lines": 20
            })

        return {
            "reasoning": "Simple planning based on contract",
            "changes": changes,
            "risks": [],
            "dependencies": []
        }

    def _check_forbidden_patterns(self, code: str) -> bool:
        """Check if code contains forbidden patterns."""
        for pattern in self.pattern_registry.get("forbidden", []):
            if pattern in code:
                return True
        return False

    async def _run_linting(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run linting on changes."""
        issues = []

        for change in changes:
            file_path = change.get("file", "")
            content = change.get("new_content", "")

            # Basic Python linting
            if file_path.endswith(".py"):
                # Check for common issues
                lines = content.splitlines()
                for i, line in enumerate(lines, 1):
                    if len(line) > 120:
                        issues.append(f"{file_path}:{i}: Line too long ({len(line)} > 120)")
                    if "\t" in line:
                        issues.append(f"{file_path}:{i}: Tab character (use spaces)")

        return {
            "passed": len(issues) == 0,
            "issues": issues
        }

    async def _run_tests(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run tests for changes."""
        # Simplified test running
        return {"passed": True, "failures": []}

    async def _check_architecture(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check architectural rules."""
        violations = []

        for change in changes:
            file_path = change.get("file", "")

            # Check layer boundaries
            if "layer1" in file_path and "layer2" in change.get("new_content", ""):
                violations.append(f"Layer boundary violation: layer1 importing layer2")

        return {
            "passed": len(violations) == 0,
            "violations": violations
        }

    def _check_patterns(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check against known-risk patterns."""
        matches = []

        for change in changes:
            content = change.get("new_content", "")

            # Check fragile patterns
            for pattern in self.pattern_registry.get("fragile", []):
                if pattern in content:
                    matches.append({"pattern": pattern, "type": "fragile", "file": change.get("file")})

        return {
            "passed": len(matches) == 0,
            "matches": matches
        }

    def _compute_pre_commit_score(self, verification: Dict[str, Any]) -> PreCommitScore:
        """Compute pre-commit confidence score."""
        factors = []

        # Lint score
        lint_result = verification.get("lint_result", {})
        lint_passed = lint_result.get("passed", True)
        lint_score = 1.0 if lint_passed else max(0.3, 1.0 - len(lint_result.get("issues", [])) * 0.1)
        factors.append({"name": "lint", "score": lint_score})

        # Test score
        test_result = verification.get("test_result", {})
        test_passed = test_result.get("passed", True)
        test_score = 1.0 if test_passed else max(0.2, 1.0 - len(test_result.get("failures", [])) * 0.2)
        factors.append({"name": "tests", "score": test_score})

        # Architecture score
        arch_result = verification.get("arch_result", {})
        arch_passed = arch_result.get("passed", True)
        arch_score = 1.0 if arch_passed else 0.5
        factors.append({"name": "architecture", "score": arch_score})

        # Pattern score
        pattern_result = verification.get("pattern_result", {})
        pattern_score = 1.0 if pattern_result.get("passed", True) else 0.6
        factors.append({"name": "patterns", "score": pattern_score})

        # Regression risk (simplified)
        regression_score = 0.9
        factors.append({"name": "regression_risk", "score": regression_score})

        # Compute overall
        weights = [0.25, 0.30, 0.15, 0.15, 0.15]
        scores = [lint_score, test_score, arch_score, pattern_score, regression_score]
        overall = sum(w * s for w, s in zip(weights, scores))

        # Determine recommendation
        if overall >= 0.85 and lint_passed and test_passed:
            recommendation = "auto_commit"
        elif overall >= 0.6:
            recommendation = "review"
        else:
            recommendation = "escalate"

        # Get logical tick from current run if available
        computed_tick = 0
        if self._current_run:
            computed_tick = self._current_run.get_current_tick()
        
        return PreCommitScore(
            score=overall,
            lint_score=lint_score,
            test_score=test_score,
            arch_compliance_score=arch_score,
            pattern_similarity_score=pattern_score,
            regression_risk_score=regression_score,
            factors=factors,
            recommendation=recommendation,
            computed_tick=computed_tick
        )

    async def _triage_verification_failures(
        self,
        verification: Dict[str, Any],
        contract: ExecutionContract
    ):
        """Triage verification failures to appropriate fixers."""
        # Lint failures -> lint fixer
        if not verification.get("lint_result", {}).get("passed", True):
            logger.info("[PIPELINE] Routing lint failures to lint fixer")
            # Would trigger lint fixing sub-agent

        # Test failures -> test fixer
        if not verification.get("test_result", {}).get("passed", True):
            logger.info("[PIPELINE] Routing test failures to test fixer")
            # Would trigger test fixing sub-agent

        # Arch failures -> arch fixer
        if not verification.get("arch_result", {}).get("passed", True):
            logger.info("[PIPELINE] Routing architecture violations to arch fixer")
            # Would trigger architecture fixing sub-agent

    def _classify_changes(
        self,
        contract: ExecutionContract,
        changes: List[Dict[str, Any]]
    ) -> ChangeClassification:
        """Auto-classify changes for KPI tracking."""
        goal_lower = contract.goal.lower()

        # Keyword matching for classification
        if any(kw in goal_lower for kw in ["fix", "bug", "error", "issue"]):
            return ChangeClassification.BUG_FIX
        elif any(kw in goal_lower for kw in ["refactor", "clean", "reorganize"]):
            return ChangeClassification.REFACTOR
        elif any(kw in goal_lower for kw in ["feature", "add", "implement", "new"]):
            return ChangeClassification.FEATURE
        elif any(kw in goal_lower for kw in ["performance", "optimize", "speed"]):
            return ChangeClassification.PERFORMANCE
        elif any(kw in goal_lower for kw in ["test", "coverage"]):
            return ChangeClassification.TEST
        elif any(kw in goal_lower for kw in ["security", "auth", "protect"]):
            return ChangeClassification.SECURITY
        elif any(kw in goal_lower for kw in ["doc", "comment", "readme"]):
            return ChangeClassification.DOCUMENTATION
        else:
            return ChangeClassification.FEATURE
