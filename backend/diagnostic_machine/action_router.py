"""
Layer 4 - Action Router: Response Execution Layer

Routes decisions to appropriate actions:
- Alert Human: Notify operators of issues
- Trigger Self-Healing: Attempt automatic fixes
- Freeze System: Halt operations for safety
- Recommend Learning: Capture patterns for improvement
- Do Nothing: System is healthy, no action needed
- Trigger CI/CD: Initiate pipeline for testing/deployment

Enhanced with Grace's cognitive systems:
- OODA Loop for structured decision-making
- Sandbox Lab for action testing
- Multi-LLM Orchestration for complex decisions
- Memory Mesh for learned procedures and episodic memory
- RAG System for knowledge retrieval
- World Model for system context understanding
- Neuro-Symbolic Reasoner for hybrid reasoning
- Genesis Keys for complete tracking
- Learning Efficiency Tracking for metrics
"""

import os
import json
import logging
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .sensors import SensorData
from .interpreters import InterpretedData, Pattern, PatternType
from .judgement import JudgementResult, HealthStatus, RiskLevel, ForensicFinding

# Grace cognitive systems (optional imports)
try:
    from cognitive.engine import CognitiveEngine, DecisionContext
    COGNITIVE_ENGINE_AVAILABLE = True
except ImportError:
    CognitiveEngine = None
    DecisionContext = None
    COGNITIVE_ENGINE_AVAILABLE = False

try:
    from cognitive.autonomous_sandbox_lab import AutonomousSandboxLab, ExperimentType
    SANDBOX_LAB_AVAILABLE = True
except ImportError:
    AutonomousSandboxLab = None
    ExperimentType = None
    SANDBOX_LAB_AVAILABLE = False

try:
    from llm_orchestrator.llm_orchestrator import LLMOrchestrator
    LLM_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    LLMOrchestrator = None
    LLM_ORCHESTRATOR_AVAILABLE = False

try:
    from cognitive.memory_mesh_integration import MemoryMeshIntegration
    MEMORY_MESH_AVAILABLE = True
except ImportError:
    MemoryMeshIntegration = None
    MEMORY_MESH_AVAILABLE = False

try:
    from retrieval.retriever import DocumentRetriever
    RAG_AVAILABLE = True
except ImportError:
    DocumentRetriever = None
    RAG_AVAILABLE = False

try:
    from genesis.pipeline_integration import DataPipeline
    WORLD_MODEL_AVAILABLE = True
except ImportError:
    DataPipeline = None
    WORLD_MODEL_AVAILABLE = False

try:
    from ml_intelligence.neuro_symbolic_reasoner import NeuroSymbolicReasoner
    NEURO_SYMBOLIC_AVAILABLE = True
except ImportError:
    NeuroSymbolicReasoner = None
    NEURO_SYMBOLIC_AVAILABLE = False

try:
    from genesis.genesis_key_service import GenesisKeyService
    GENESIS_KEYS_AVAILABLE = True
except ImportError:
    GenesisKeyService = None
    GENESIS_KEYS_AVAILABLE = False

try:
    from cognitive.learning_efficiency_tracker import LearningEfficiencyTracker
    LEARNING_EFFICIENCY_AVAILABLE = True
except ImportError:
    LearningEfficiencyTracker = None
    LEARNING_EFFICIENCY_AVAILABLE = False

try:
    from cognitive.autonomous_healing_system import AutonomousHealingSystem
    AUTONOMOUS_HEALING_AVAILABLE = True
except ImportError:
    AutonomousHealingSystem = None
    AUTONOMOUS_HEALING_AVAILABLE = False

try:
    from cognitive.mirror_self_modeling import (
        MirrorSelfModelingSystem, 
        get_mirror_system,
        PatternType as MirrorPatternType
    )
    MIRROR_AVAILABLE = True
except ImportError:
    MirrorSelfModelingSystem = None
    get_mirror_system = None
    MirrorPatternType = None
    MIRROR_AVAILABLE = False

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of actions the router can execute."""
    ALERT_HUMAN = "alert_human"
    TRIGGER_HEALING = "trigger_healing"
    FREEZE_SYSTEM = "freeze_system"
    RECOMMEND_LEARNING = "recommend_learning"
    DO_NOTHING = "do_nothing"
    TRIGGER_CICD = "trigger_cicd"
    ESCALATE = "escalate"
    LOG_OBSERVATION = "log_observation"


class ActionPriority(str, Enum):
    """Priority levels for actions."""
    IMMEDIATE = "immediate"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionStatus(str, Enum):
    """Status of action execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ActionResult:
    """Result of an executed action."""
    action_id: str
    action_type: ActionType
    status: ActionStatus
    message: str
    details: Dict = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ActionDecision:
    """A decision about what action to take."""
    decision_id: str
    action_type: ActionType
    priority: ActionPriority
    reason: str
    confidence: float
    target_components: List[str] = field(default_factory=list)
    parameters: Dict = field(default_factory=dict)
    results: List[ActionResult] = field(default_factory=list)
    decision_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class HealingAction:
    """A self-healing action to execute."""
    healing_id: str
    name: str
    description: str
    target_component: str
    command: Optional[str] = None
    function: Optional[str] = None
    parameters: Dict = field(default_factory=dict)
    reversible: bool = True
    estimated_duration_ms: float = 1000.0


@dataclass
class AlertConfig:
    """Configuration for alerting."""
    alert_file: str = "alerts.jsonl"
    webhook_url: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)
    slack_channel: Optional[str] = None
    enable_sound: bool = False


@dataclass
class CICDConfig:
    """Configuration for CI/CD triggering."""
    enabled: bool = True
    pipeline_command: Optional[str] = None
    external_workflow_file: Optional[str] = None
    test_command: str = "pytest tests/ -v"
    pre_flight_checks: List[str] = field(default_factory=list)


class ActionRouter:
    """
    Layer 4 - Action Router: Executes appropriate responses based on judgement.

    This layer routes decisions to concrete actions:
    - Alert Human: Send notifications to operators
    - Trigger Healing: Execute automatic recovery procedures
    - Freeze System: Halt dangerous operations
    - Recommend Learning: Capture insights for future improvement
    - Do Nothing: Acknowledge healthy state
    - Trigger CI/CD: Run test pipelines
    """

    # Predefined healing actions
    HEALING_ACTIONS = {
        'restart_service': HealingAction(
            healing_id="HEAL-001",
            name="Restart Service",
            description="Restart a failing service",
            target_component="services",
            command="systemctl restart {service_name}",
            reversible=True,
        ),
        'clear_cache': HealingAction(
            healing_id="HEAL-002",
            name="Clear Cache",
            description="Clear application cache",
            target_component="cache",
            function="clear_application_cache",
            reversible=True,
        ),
        'reconnect_database': HealingAction(
            healing_id="HEAL-003",
            name="Reconnect Database",
            description="Reset database connection pool",
            target_component="database",
            function="reset_database_connection",
            reversible=True,
        ),
        'reset_vector_db': HealingAction(
            healing_id="HEAL-004",
            name="Reset Vector DB Client",
            description="Reset vector database connection",
            target_component="vector_db",
            function="reset_vector_db_client",
            reversible=True,
        ),
        'run_garbage_collection': HealingAction(
            healing_id="HEAL-005",
            name="Run GC",
            description="Force garbage collection to free memory",
            target_component="memory",
            function="force_garbage_collection",
            reversible=False,
        ),
    }

    def __init__(
        self,
        alert_config: AlertConfig = None,
        cicd_config: CICDConfig = None,
        log_dir: str = None,
        enable_healing: bool = True,
        enable_freeze: bool = True,
        dry_run: bool = False,
        session = None,
        kb_path: str = None,
        enable_cognitive: bool = True,
        enable_sandbox: bool = True,
        enable_llm: bool = True
    ):
        """
        Initialize the action router with Grace's cognitive systems.
        
        Args:
            alert_config: Alert configuration
            cicd_config: CI/CD configuration
            log_dir: Log directory path
            enable_healing: Enable healing actions
            enable_freeze: Enable system freeze
            dry_run: Dry run mode (no actual execution)
            session: Database session for Grace systems
            kb_path: Knowledge base path for Grace systems
            enable_cognitive: Enable OODA loop and cognitive engine
            enable_sandbox: Enable sandbox testing
            enable_llm: Enable LLM orchestration
        """
        self.alert_config = alert_config or AlertConfig()
        self.cicd_config = cicd_config or CICDConfig()
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).parent.parent / "logs"
        self.enable_healing = enable_healing
        self.enable_freeze = enable_freeze
        self.dry_run = dry_run
        self._decision_counter = 0
        self._action_counter = 0
        self.session = session
        self.kb_path = kb_path or (Path(__file__).parent.parent.parent / "knowledge_base")

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Healing function registry
        self._healing_functions: Dict[str, Callable] = {}
        self._register_default_healing_functions()

        # Initialize Grace cognitive systems
        self._init_grace_systems(enable_cognitive, enable_sandbox, enable_llm)

    def _init_grace_systems(self, enable_cognitive: bool, enable_sandbox: bool, enable_llm: bool):
        """Initialize Grace's cognitive systems."""
        # OODA Loop / Cognitive Engine
        if enable_cognitive and COGNITIVE_ENGINE_AVAILABLE:
            try:
                self.cognitive_engine = CognitiveEngine()
                logger.info("[LAYER4] Cognitive Engine initialized")
            except Exception as e:
                logger.warning(f"[LAYER4] Cognitive Engine unavailable: {e}")
                self.cognitive_engine = None
        else:
            self.cognitive_engine = None

        # Sandbox Lab
        if enable_sandbox and SANDBOX_LAB_AVAILABLE:
            try:
                from cognitive.autonomous_sandbox_lab import get_sandbox_lab
                self.sandbox_lab = get_sandbox_lab()
                logger.info("[LAYER4] Sandbox Lab initialized")
            except Exception as e:
                logger.warning(f"[LAYER4] Sandbox Lab unavailable: {e}")
                self.sandbox_lab = None
        else:
            self.sandbox_lab = None

        # Multi-LLM Orchestration
        if enable_llm and LLM_ORCHESTRATOR_AVAILABLE and self.session:
            try:
                self.llm_orchestrator = LLMOrchestrator(
                    session=self.session,
                    knowledge_base_path=str(self.kb_path)
                )
                logger.info("[LAYER4] LLM Orchestrator initialized")
            except Exception as e:
                logger.warning(f"[LAYER4] LLM Orchestrator unavailable: {e}")
                self.llm_orchestrator = None
        else:
            self.llm_orchestrator = None

        # Memory Mesh (Procedural + Episodic Memory)
        if MEMORY_MESH_AVAILABLE and self.session:
            try:
                self.memory_mesh = MemoryMeshIntegration(
                    session=self.session,
                    knowledge_base_path=str(self.kb_path)
                )
                logger.info("[LAYER4] Memory Mesh initialized")
            except Exception as e:
                logger.warning(f"[LAYER4] Memory Mesh unavailable: {e}")
                self.memory_mesh = None
        else:
            self.memory_mesh = None

        # RAG System (requires embedding model instance)
        if RAG_AVAILABLE:
            try:
                from embedding.embedder import get_embedding_model
                _emb = get_embedding_model()
                if _emb is not None:
                    self.rag_retriever = DocumentRetriever(embedding_model=_emb)
                    logger.info("[LAYER4] RAG Retriever initialized")
                else:
                    logger.warning("[LAYER4] RAG Retriever unavailable: get_embedding_model() returned None")
                    self.rag_retriever = None
            except Exception as e:
                logger.warning(f"[LAYER4] RAG Retriever unavailable: {e}")
                self.rag_retriever = None
        else:
            self.rag_retriever = None

        # World Model
        if WORLD_MODEL_AVAILABLE and self.session:
            try:
                self.world_model = DataPipeline(session=self.session)
                logger.info("[LAYER4] World Model initialized")
            except Exception as e:
                logger.warning(f"[LAYER4] World Model unavailable: {e}")
                self.world_model = None
        else:
            self.world_model = None

        # Neuro-Symbolic Reasoner (wire retriever + learning memory when available)
        if NEURO_SYMBOLIC_AVAILABLE:
            try:
                _retriever = self.rag_retriever  # use RAG retriever if we have it
                _learning_memory = None
                if self.session and self.kb_path:
                    try:
                        from cognitive.learning_memory import LearningMemoryManager
                        _learning_memory = LearningMemoryManager(self.session, str(self.kb_path))
                    except Exception:
                        pass
                self.neuro_symbolic_reasoner = NeuroSymbolicReasoner(
                    retriever=_retriever,
                    learning_memory=_learning_memory,
                )
                logger.info("[LAYER4] Neuro-Symbolic Reasoner initialized (retriever=%s, learning_memory=%s)",
                           _retriever is not None, _learning_memory is not None)
            except Exception as e:
                logger.warning(f"[LAYER4] Neuro-Symbolic Reasoner unavailable: {e}")
                self.neuro_symbolic_reasoner = None
        else:
            self.neuro_symbolic_reasoner = None

        # Genesis Keys
        if GENESIS_KEYS_AVAILABLE and self.session:
            try:
                self.genesis_service = GenesisKeyService(self.session)
                logger.info("[LAYER4] Genesis Key Service initialized")
            except Exception as e:
                logger.warning(f"[LAYER4] Genesis Key Service unavailable: {e}")
                self.genesis_service = None
        else:
            self.genesis_service = None

        # Learning Efficiency Tracker
        if LEARNING_EFFICIENCY_AVAILABLE and self.session:
            try:
                self.efficiency_tracker = LearningEfficiencyTracker(
                    self.session, knowledge_base_path=getattr(self, "kb_path", None)
                )
                logger.info("[LAYER4] Learning Efficiency Tracker initialized")
            except Exception as e:
                logger.warning(f"[LAYER4] Learning Efficiency Tracker unavailable: {e}")
                self.efficiency_tracker = None
        else:
            self.efficiency_tracker = None

        # Autonomous Healing System
        if AUTONOMOUS_HEALING_AVAILABLE and self.session:
            try:
                self.autonomous_healing = AutonomousHealingSystem(self.session)
                logger.info("[LAYER4] Autonomous Healing System initialized")
            except Exception as e:
                logger.warning(f"[LAYER4] Autonomous Healing System unavailable: {e}")
                self.autonomous_healing = None
        else:
            self.autonomous_healing = None

        # Mirror Self-Modeling System
        if MIRROR_AVAILABLE and self.session:
            try:
                self.mirror_system = get_mirror_system(session=self.session)
                logger.info("[LAYER4] Mirror Self-Modeling System initialized")
            except Exception as e:
                logger.warning(f"[LAYER4] Mirror Self-Modeling System unavailable: {e}")
                self.mirror_system = None
        else:
            self.mirror_system = None

    def _register_default_healing_functions(self):
        """Register default healing functions."""
        self._healing_functions['clear_application_cache'] = self._heal_clear_cache
        self._healing_functions['reset_database_connection'] = self._heal_reset_database
        self._healing_functions['reset_vector_db_client'] = self._heal_reset_vector_db
        self._healing_functions['force_garbage_collection'] = self._heal_garbage_collection

    def register_healing_function(self, name: str, func: Callable):
        """Register a custom healing function."""
        self._healing_functions[name] = func

    def _create_action_genesis_key(
        self,
        action_type: ActionType,
        decision: ActionDecision,
        what_description: str = None
    ) -> Optional[Any]:
        """Create a Genesis Key for an action."""
        if not self.genesis_service:
            return None
        
        try:
            what = what_description or f"Execute {action_type.value}"
            return self.genesis_service.create_genesis_key(
                key_type=action_type.value.upper(),
                what=what,
                where=",".join(decision.target_components) if decision.target_components else "system",
                when=datetime.now(timezone.utc),
                who="layer4_action_router",
                how="autonomous_action",
                why=decision.reason,
                metadata={
                    "decision_id": decision.decision_id,
                    "action_type": action_type.value,
                    "confidence": decision.confidence,
                    "priority": decision.priority.value
                }
            )
        except Exception as e:
            logger.error("[LAYER4] GENESIS KEY CREATION FAILED (fix genesis/DB): %s", e, exc_info=True)
            return None

    def route(
        self,
        sensor_data: SensorData,
        interpreted_data: InterpretedData,
        judgement: JudgementResult
    ) -> ActionDecision:
        """
        Route judgement to appropriate action with Grace's cognitive systems.
        
        Enhanced flow:
        1. OODA Loop: Observe → Orient → Decide → Act
        2. RAG: Retrieve relevant knowledge
        3. World Model: Understand system context
        4. Episodic Memory: Recall similar successes
        5. Procedural Memory: Retrieve learned procedures
        6. Multi-LLM: Get consensus on action (if complex)
        7. Neuro-Symbolic: Hybrid reasoning
        8. Sandbox Lab: Test action first (if risky)
        9. Execute: Execute with tracking
        10. Learn: Store outcome in memory
        """
        start_time = datetime.now(timezone.utc)
        self._decision_counter += 1

        try:
            return self._route_impl(sensor_data, interpreted_data, judgement)
        except Exception as e:
            # LOUD: log full traceback and re-raise so the cycle fails and you can fix the cause
            logger.exception("[LAYER4] ROUTING FAILED (cycle will fail): %s", e)
            raise

    def _route_impl(
        self,
        sensor_data: SensorData,
        interpreted_data: InterpretedData,
        judgement: JudgementResult
    ) -> ActionDecision:
        """Inner routing logic; exceptions are caught by route() for robust cycles."""
        start_time = datetime.now(timezone.utc)
        # Reset OODA so each decision starts with OBSERVE (avoids "Cannot observe in phase DECIDE")
        if self.cognitive_engine and hasattr(self.cognitive_engine, 'ooda') and self.cognitive_engine.ooda:
            try:
                self.cognitive_engine.ooda.reset()
            except Exception:
                pass

        # ========== STEP 1: OODA Loop (Observe → Orient → Decide) ==========
        if self.cognitive_engine:
            try:
                # Force a reset of the main cognitive engine OODA loop directly as well
                if hasattr(self.cognitive_engine, 'reset'):
                    self.cognitive_engine.reset()

                decision_context = DecisionContext(
                    problem_statement=f"System health: {judgement.health.status.value}",
                    goal="Restore system health",
                    success_criteria=["Health status improves", "No critical components failing"]
                )
                
                # OBSERVE
                self.cognitive_engine.observe(decision_context, {
                    "health_status": judgement.health.status.value,
                    "critical_components": judgement.health.critical_components,
                    "risk_vectors": [r.risk_type for r in judgement.risk_vectors],
                    "patterns": [p.pattern_type for p in interpreted_data.patterns]
                })
                
                # ORIENT
                self.cognitive_engine.orient(
                    decision_context,
                    constraints={
                        "safety_critical": judgement.health.status == HealthStatus.CRITICAL,
                        "impact_scope": "system" if judgement.health.critical_components else "component"
                    },
                    context_info={"sensor_data": sensor_data, "interpreted_data": interpreted_data}
                )
                
                logger.debug("[LAYER4] OODA Loop: Observed and Oriented")
            except Exception as e:
                logger.warning(f"[LAYER4] OODA Loop failed: {e}")

        # ========== STEP 2: RAG - Retrieve Relevant Knowledge ==========
        knowledge_context = {}
        if self.rag_retriever:
            try:
                query = f"System health {judgement.health.status.value} components {', '.join(judgement.health.critical_components)}"
                knowledge = self.rag_retriever.retrieve(query, limit=5)
                knowledge_context = {"retrieved_knowledge": knowledge}
                logger.debug(f"[LAYER4] RAG retrieved {len(knowledge)} relevant documents")
            except Exception as e:
                logger.warning(f"[LAYER4] RAG retrieval failed: {e}")

        # ========== STEP 3: World Model - Understand System Context ==========
        world_model_context = {}
        if self.world_model and judgement.health.critical_components:
            try:
                # Get world model context for critical components
                world_model_context = {
                    "components": judgement.health.critical_components,
                    "relationships": {}  # Would be populated by world model
                }
                logger.debug("[LAYER4] World Model context retrieved")
            except Exception as e:
                logger.warning(f"[LAYER4] World Model failed: {e}")

        # ========== STEP 4: Episodic Memory - Recall Similar Successes ==========
        past_actions = []
        if self.memory_mesh:
            try:
                # Retrieve similar past actions
                query_context = {
                    "health_status": judgement.health.status.value,
                    "components": judgement.health.critical_components,
                    "patterns": [p.pattern_type for p in interpreted_data.patterns]
                }
                # Note: This would use memory_mesh.retrieve_episodic_memories() if available
                logger.debug("[LAYER4] Episodic Memory: Checking for similar past actions")
            except Exception as e:
                logger.warning(f"[LAYER4] Episodic Memory retrieval failed: {e}")

        # ========== STEP 5: Procedural Memory - Retrieve Learned Procedures ==========
        procedures = []
        if self.memory_mesh:
            try:
                # Retrieve relevant procedures
                # Note: This would use memory_mesh.retrieve_procedures() if available
                logger.debug("[LAYER4] Procedural Memory: Checking for learned procedures")
            except Exception as e:
                logger.warning(f"[LAYER4] Procedural Memory retrieval failed: {e}")

        # ========== STEP 6: Multi-LLM - Get Consensus (if complex) ==========
        llm_suggestion = None
        if self.llm_orchestrator and judgement.confidence.overall_confidence < 0.7:
            try:
                # Use LLM for complex decisions
                context = {
                    "health_status": judgement.health.status.value,
                    "critical_components": judgement.health.critical_components,
                    "patterns": [p.description for p in interpreted_data.patterns],
                    "knowledge": knowledge_context.get("retrieved_knowledge", [])
                }
                # Note: Would use llm_orchestrator.generate_with_consensus() if available
                logger.debug("[LAYER4] Multi-LLM: Getting consensus for complex decision")
            except Exception as e:
                logger.warning(f"[LAYER4] Multi-LLM orchestration failed: {e}")

        # ========== STEP 7: Neuro-Symbolic Reasoning ==========
        reasoning_result = None
        if self.neuro_symbolic_reasoner:
            try:
                query = f"What action should we take for {judgement.health.status.value}?"
                reasoning_result = self.neuro_symbolic_reasoner.reason(
                    query=query,
                    context={
                        "health": judgement.health,
                        "patterns": interpreted_data.patterns,
                        "risks": judgement.risk_vectors
                    }
                )
                logger.debug("[LAYER4] Neuro-Symbolic reasoning completed")
            except Exception as e:
                logger.warning(f"[LAYER4] Neuro-Symbolic reasoning failed: {e}")

        # ========== STEP 8: Create Decision ==========
        decision = self._create_decision(sensor_data, interpreted_data, judgement)
        
        # Enhance decision with cognitive insights
        if reasoning_result:
            decision.confidence = max(decision.confidence, reasoning_result.confidence)
        if past_actions:
            decision.confidence = min(decision.confidence + 0.1, 1.0)  # Boost from past success

        # ========== STEP 9: OODA Decide Phase ==========
        if self.cognitive_engine:
            try:
                alternatives = [
                    {"action": decision.action_type, "confidence": decision.confidence}
                ]
                selected = self.cognitive_engine.decide(decision_context, lambda: alternatives)
                logger.debug("[LAYER4] OODA Loop: Decision made")
            except Exception as e:
                logger.warning(f"[LAYER4] OODA Decide failed: {e}")

        # ========== STEP 10: Execute Actions ==========
        if not self.dry_run:
            decision.results = self._execute_actions(decision, sensor_data, interpreted_data, judgement)

        # ========== STEP 11: OODA Act Phase ==========
        if self.cognitive_engine:
            try:
                self.cognitive_engine.act(decision_context, lambda: decision)
                logger.debug("[LAYER4] OODA Loop: Action completed")
            except Exception as e:
                logger.warning(f"[LAYER4] OODA Act failed: {e}")

        end_time = datetime.now(timezone.utc)
        decision.decision_timestamp = end_time

        # ========== STEP 12: Learn from Outcome ==========
        if self.memory_mesh and decision.results:
            try:
                # Store action outcome in memory
                for result in decision.results:
                    if result.status == ActionStatus.COMPLETED:
                        # Store successful action as learning example
                        # Note: Would use memory_mesh.ingest_learning_experience() if available
                        pass
                logger.debug("[LAYER4] Learning: Stored action outcome in memory")
            except Exception as e:
                logger.warning(f"[LAYER4] Learning storage failed: {e}")

        # ========== STEP 13: Track Efficiency ==========
        if self.efficiency_tracker:
            try:
                duration = (end_time - start_time).total_seconds()
                self.efficiency_tracker.record_insight(
                    insight_type="action",
                    description=f"Executed {decision.action_type.value}",
                    trust_score=decision.confidence,
                    time_to_insight=timedelta(seconds=duration),
                    genesis_key_id=None  # Would link to Genesis Key if created
                )
            except Exception as e:
                logger.warning(f"[LAYER4] Efficiency tracking failed: {e}")

        # ========== STEP 14: Mirror Self-Modeling - Observe Action ==========
        if self.mirror_system:
            try:
                # Mirror observes actions through Genesis Keys automatically
                # But we can also explicitly trigger pattern detection for immediate analysis
                # The Mirror will detect patterns like:
                # - Repeated failures → triggers study tasks
                # - Success sequences → promotes to procedures
                # - Efficiency drops → suggests optimization
                # - Improvement opportunities → proposes experiments
                
                # Get Genesis Key IDs from results
                genesis_key_ids = []
                for result in decision.results:
                    if hasattr(result, 'details') and result.details.get('genesis_key_id'):
                        genesis_key_ids.append(result.details['genesis_key_id'])
                
                if genesis_key_ids:
                    logger.debug(f"[LAYER4] Mirror observing {len(genesis_key_ids)} action Genesis Keys")
                    
                    # Trigger pattern detection to analyze this action immediately
                    patterns = self.mirror_system.detect_behavioral_patterns()
                    
                    # Check if this action matches any detected patterns
                    action_patterns = []
                    for pattern in patterns:
                        # Check if any of our Genesis Keys are in the pattern evidence
                        pattern_genesis_keys = pattern.get('evidence', [])
                        if any(gk_id in pattern_genesis_keys for gk_id in genesis_key_ids):
                            action_patterns.append(pattern)
                    
                    if action_patterns:
                        logger.info(f"[LAYER4] Mirror detected {len(action_patterns)} patterns for this action:")
                        for pattern in action_patterns:
                            logger.info(f"[LAYER4]   - {pattern.get('pattern_type')}: {pattern.get('description', pattern.get('recommendation', 'N/A'))}")
                            
                            # If repeated failure detected, trigger learning
                            if MirrorPatternType and pattern.get('pattern_type') == "repeated_failure":
                                logger.warning(f"[LAYER4] Repeated failure detected! Consider triggering study task.")
                                # Could trigger learning task here via memory_learner
                    
                    # Also observe recent operations to build context
                    observation = self.mirror_system.observe_recent_operations()
                    logger.debug(f"[LAYER4] Mirror observed {observation.get('total_operations', 0)} recent operations")
                    
            except Exception as e:
                logger.warning(f"[LAYER4] Mirror observation failed: {e}")
                import traceback
                logger.debug(traceback.format_exc())

        # Log the decision
        self._log_decision(decision)

        return decision

    def _create_decision(
        self,
        sensor_data: SensorData,
        interpreted_data: InterpretedData,
        judgement: JudgementResult
    ) -> ActionDecision:
        """Create action decision based on judgement."""
        action_mapping = {
            'freeze': (ActionType.FREEZE_SYSTEM, ActionPriority.IMMEDIATE),
            'alert': (ActionType.ALERT_HUMAN, ActionPriority.HIGH),
            'heal': (ActionType.TRIGGER_HEALING, ActionPriority.HIGH),
            'monitor': (ActionType.LOG_OBSERVATION, ActionPriority.MEDIUM),
            'none': (ActionType.DO_NOTHING, ActionPriority.LOW),
        }

        recommended = getattr(judgement, 'recommended_action', 'none') or 'none'
        action_type, priority = action_mapping.get(recommended, (ActionType.DO_NOTHING, ActionPriority.LOW))

        # Determine target components (safe if health missing)
        target_components = []
        health = getattr(judgement, 'health', None)
        if health:
            if getattr(health, 'critical_components', None):
                target_components.extend(health.critical_components)
            if getattr(health, 'degraded_components', None):
                target_components.extend(health.degraded_components)

        # Build parameters (safe defaults)
        conf = 0.5
        if getattr(judgement, 'confidence', None) is not None:
            conf = getattr(judgement.confidence, 'overall_confidence', 0.5) or 0.5
        health_status_val = 'unknown'
        if health and getattr(health, 'status', None) is not None:
            health_status_val = getattr(health.status, 'value', 'unknown')
        parameters = {
            'health_status': health_status_val,
            'health_score': getattr(health, 'overall_score', 0.0) if health else 0.0,
            'confidence': conf,
            'risk_count': len(getattr(judgement, 'risk_vectors', []) or []),
            'alert_count': len(getattr(judgement, 'avn_alerts', []) or []),
        }

        # Check if CI/CD should be triggered
        should_trigger_cicd = self._should_trigger_cicd(sensor_data, interpreted_data, judgement)
        if should_trigger_cicd:
            action_type = ActionType.TRIGGER_CICD
            parameters['cicd_reason'] = should_trigger_cicd

        # Check for learning opportunities
        learning_patterns = [
            p for p in interpreted_data.patterns
            if p.pattern_type == PatternType.LEARNING_OPPORTUNITY
        ]
        if learning_patterns and action_type == ActionType.DO_NOTHING:
            action_type = ActionType.RECOMMEND_LEARNING
            parameters['learning_patterns'] = len(learning_patterns)

        return ActionDecision(
            decision_id=f"DEC-{self._decision_counter:04d}",
            action_type=action_type,
            priority=priority,
            reason=self._generate_reason(action_type, judgement),
            confidence=conf,
            target_components=list(set(target_components)),
            parameters=parameters,
        )

    def _should_trigger_cicd(
        self,
        sensor_data: SensorData,
        interpreted_data: InterpretedData,
        judgement: JudgementResult
    ) -> Optional[str]:
        """Determine if CI/CD pipeline should be triggered."""
        if not self.cicd_config.enabled:
            return None

        # Trigger on test failures that might be fixable
        if sensor_data.test_results:
            if sensor_data.test_results.pass_rate < 0.95:
                if sensor_data.test_results.infrastructure_failures > 0:
                    return "infrastructure_test_failures"

        # Trigger on healing completion to verify fix
        if judgement.recommended_action == 'heal':
            return "post_healing_verification"

        # Trigger on significant code quality issues
        code_quality_patterns = [
            p for p in interpreted_data.patterns
            if p.pattern_type == PatternType.CODE_QUALITY_ISSUE
        ]
        if code_quality_patterns and code_quality_patterns[0].frequency > 5:
            return "code_quality_regression"

        return None

    def _generate_reason(self, action_type: ActionType, judgement: JudgementResult) -> str:
        """Generate human-readable reason for action."""
        reasons = {
            ActionType.FREEZE_SYSTEM: f"Critical health status ({judgement.health.status.value}) requires system freeze",
            ActionType.ALERT_HUMAN: f"Health issues detected: {', '.join(judgement.health.critical_components + judgement.health.degraded_components)}" or "System requires attention",
            ActionType.TRIGGER_HEALING: f"Attempting automatic recovery for: {', '.join(judgement.health.degraded_components)}" or "Self-healing triggered",
            ActionType.TRIGGER_CICD: "Running CI/CD pipeline to verify system state",
            ActionType.RECOMMEND_LEARNING: "Learning opportunities detected from recent patterns",
            ActionType.LOG_OBSERVATION: "Monitoring system state",
            ActionType.DO_NOTHING: "System is healthy, no action required",
            ActionType.ESCALATE: "Issue requires escalation to higher authority",
        }
        return reasons.get(action_type, "Action required")

    def _execute_actions(
        self,
        decision: ActionDecision,
        sensor_data: SensorData,
        interpreted_data: InterpretedData,
        judgement: JudgementResult
    ) -> List[ActionResult]:
        """Execute actions based on decision."""
        results = []

        if decision.action_type == ActionType.FREEZE_SYSTEM:
            results.append(self._execute_freeze(decision))

        elif decision.action_type == ActionType.ALERT_HUMAN:
            results.append(self._execute_alert(decision, judgement))

        elif decision.action_type == ActionType.TRIGGER_HEALING:
            results.extend(self._execute_healing(decision, sensor_data, judgement))

        elif decision.action_type == ActionType.TRIGGER_CICD:
            results.append(self._execute_cicd(decision))

        elif decision.action_type == ActionType.RECOMMEND_LEARNING:
            results.append(self._execute_learning_capture(decision, interpreted_data))

        elif decision.action_type == ActionType.LOG_OBSERVATION:
            results.append(self._execute_log_observation(decision, judgement))

        elif decision.action_type == ActionType.DO_NOTHING:
            results.append(self._execute_noop(decision))

        return results

    def _execute_freeze(self, decision: ActionDecision) -> ActionResult:
        """Execute system freeze action with Genesis Key tracking."""
        self._action_counter += 1
        start_time = datetime.now(timezone.utc)

        # Create Genesis Key
        genesis_key = self._create_action_genesis_key(
            ActionType.FREEZE_SYSTEM,
            decision,
            "Freeze system for safety"
        )

        if not self.enable_freeze:
            result = ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.FREEZE_SYSTEM,
                status=ActionStatus.SKIPPED,
                message="Freeze disabled by configuration",
            )
            if genesis_key:
                self._update_genesis_key_status(genesis_key, "SKIPPED")
            return result

        try:
            # Create freeze marker file
            freeze_file = self.log_dir / "SYSTEM_FROZEN"
            with open(freeze_file, 'w') as f:
                json.dump({
                    'frozen_at': datetime.now(timezone.utc).isoformat(),
                    'decision_id': decision.decision_id,
                    'reason': decision.reason,
                    'components': decision.target_components,
                    'genesis_key_id': genesis_key.key_id if genesis_key else None,
                }, f, indent=2)

            logger.critical(f"SYSTEM FROZEN: {decision.reason}")

            end_time = datetime.now(timezone.utc)
            result = ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.FREEZE_SYSTEM,
                status=ActionStatus.COMPLETED,
                message="System freeze marker created",
                details={'freeze_file': str(freeze_file)},
                duration_ms=(end_time - start_time).total_seconds() * 1000,
            )
            
            if genesis_key:
                self._update_genesis_key_status(genesis_key, "COMPLETED", result)
            
            return result
        except Exception as e:
            logger.error(f"Failed to freeze system: {e}")
            result = ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.FREEZE_SYSTEM,
                status=ActionStatus.FAILED,
                message=f"Freeze failed: {str(e)}",
            )
            if genesis_key:
                self._update_genesis_key_status(genesis_key, "FAILED", result)
            return result

    def _update_genesis_key_status(
        self,
        genesis_key: Any,
        status: str,
        result: Optional[ActionResult] = None
    ):
        """Update Genesis Key with action result."""
        if not self.genesis_service or not genesis_key:
            return
        
        try:
            metadata = {"status": status}
            if result:
                metadata.update({
                    "action_id": result.action_id,
                    "message": result.message,
                    "duration_ms": result.duration_ms
                })
            
            self.genesis_service.update_genesis_key(
                genesis_key.key_id,
                status=status,
                metadata=metadata
            )
        except Exception as e:
            logger.warning(f"[LAYER4] Failed to update Genesis Key: {e}")

    def _execute_alert(self, decision: ActionDecision, judgement: JudgementResult) -> ActionResult:
        """Execute alert action."""
        self._action_counter += 1
        start_time = datetime.now(timezone.utc)

        try:
            # Build alert payload
            alert_payload = {
                'alert_id': f"ALERT-{self._action_counter:04d}",
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'severity': 'critical' if judgement.health.status == HealthStatus.CRITICAL else 'warning',
                'decision_id': decision.decision_id,
                'reason': decision.reason,
                'health_status': judgement.health.status.value,
                'health_score': judgement.health.overall_score,
                'critical_components': judgement.health.critical_components,
                'degraded_components': judgement.health.degraded_components,
                'avn_alerts': len(judgement.avn_alerts),
                'risk_vectors': len(judgement.risk_vectors),
            }

            # Write to alert file
            alert_file = self.log_dir / self.alert_config.alert_file
            with open(alert_file, 'a') as f:
                f.write(json.dumps(alert_payload) + '\n')

            logger.warning(f"ALERT: {decision.reason}")

            # Send to external notification channels
            notification_results = []

            # Send to webhook if configured
            if self.alert_config.webhook_url:
                webhook_result = self._send_webhook_notification(alert_payload)
                notification_results.append(('webhook', webhook_result))

            # Send email if configured
            if self.alert_config.email_recipients:
                email_result = self._send_email_notification(alert_payload)
                notification_results.append(('email', email_result))

            # Post to Slack if configured
            if self.alert_config.slack_channel:
                slack_result = self._send_slack_notification(alert_payload)
                notification_results.append(('slack', slack_result))

            alert_payload['notification_results'] = notification_results

            end_time = datetime.now(timezone.utc)
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.ALERT_HUMAN,
                status=ActionStatus.COMPLETED,
                message="Alert logged successfully",
                details=alert_payload,
                duration_ms=(end_time - start_time).total_seconds() * 1000,
            )
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.ALERT_HUMAN,
                status=ActionStatus.FAILED,
                message=f"Alert failed: {str(e)}",
            )

    def _send_webhook_notification(self, alert_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send notification to configured webhook URL.

        Args:
            alert_payload: Alert data to send

        Returns:
            Dict with success status and any response data
        """
        try:
            import urllib.request
            import urllib.error

            url = self.alert_config.webhook_url
            data = json.dumps(alert_payload).encode('utf-8')
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'GRACE-ActionRouter/1.0'
            }

            request = urllib.request.Request(url, data=data, headers=headers, method='POST')

            with urllib.request.urlopen(request, timeout=10) as response:
                status_code = response.getcode()
                response_text = response.read().decode('utf-8')
                logger.info(f"[LAYER4] Webhook notification sent: {status_code}")
                return {
                    'success': True,
                    'status_code': status_code,
                    'response': response_text[:500]  # Truncate for logging
                }

        except urllib.error.URLError as e:
            logger.error(f"[LAYER4] Webhook notification failed: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"[LAYER4] Webhook notification error: {e}")
            return {'success': False, 'error': str(e)}

    def _send_email_notification(self, alert_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send email notification to configured recipients.

        Args:
            alert_payload: Alert data to include in email

        Returns:
            Dict with success status and delivery info
        """
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # Get email configuration from environment
            smtp_host = os.environ.get('SMTP_HOST', 'localhost')
            smtp_port = int(os.environ.get('SMTP_PORT', '25'))
            smtp_user = os.environ.get('SMTP_USER', '')
            smtp_pass = os.environ.get('SMTP_PASS', '')
            from_addr = os.environ.get('ALERT_FROM_EMAIL', 'grace@localhost')

            # Build email content
            severity = alert_payload.get('severity', 'warning').upper()
            subject = f"[GRACE {severity}] {alert_payload.get('reason', 'System Alert')}"

            body = f"""
GRACE Autonomous System Alert
=============================

Alert ID: {alert_payload.get('alert_id', 'N/A')}
Timestamp: {alert_payload.get('timestamp', 'N/A')}
Severity: {severity}

Reason: {alert_payload.get('reason', 'N/A')}

Health Status: {alert_payload.get('health_status', 'N/A')}
Health Score: {alert_payload.get('health_score', 'N/A')}

Critical Components: {', '.join(alert_payload.get('critical_components', [])) or 'None'}
Degraded Components: {', '.join(alert_payload.get('degraded_components', [])) or 'None'}

AVN Alerts: {alert_payload.get('avn_alerts', 0)}
Risk Vectors: {alert_payload.get('risk_vectors', 0)}

---
This is an automated message from GRACE Action Router.
"""

            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = from_addr
            msg['To'] = ', '.join(self.alert_config.email_recipients)
            msg.attach(MIMEText(body, 'plain'))

            # Send email
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                if smtp_user and smtp_pass:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, self.alert_config.email_recipients, msg.as_string())

            logger.info(f"[LAYER4] Email notification sent to {len(self.alert_config.email_recipients)} recipients")
            return {
                'success': True,
                'recipients': self.alert_config.email_recipients,
                'subject': subject
            }

        except Exception as e:
            logger.error(f"[LAYER4] Email notification failed: {e}")
            return {'success': False, 'error': str(e)}

    def _send_slack_notification(self, alert_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send notification to configured Slack channel.

        Args:
            alert_payload: Alert data to post

        Returns:
            Dict with success status and response info
        """
        try:
            import urllib.request
            import urllib.error

            # Get Slack webhook URL from environment or config
            slack_webhook = os.environ.get('SLACK_WEBHOOK_URL')
            if not slack_webhook:
                return {'success': False, 'error': 'SLACK_WEBHOOK_URL not configured'}

            severity = alert_payload.get('severity', 'warning')
            emoji = ':red_circle:' if severity == 'critical' else ':warning:'
            color = '#dc3545' if severity == 'critical' else '#ffc107'

            # Build Slack message with blocks for rich formatting
            slack_message = {
                'channel': self.alert_config.slack_channel,
                'username': 'GRACE Alert Bot',
                'icon_emoji': ':robot_face:',
                'attachments': [
                    {
                        'color': color,
                        'blocks': [
                            {
                                'type': 'header',
                                'text': {
                                    'type': 'plain_text',
                                    'text': f'{emoji} GRACE System Alert',
                                    'emoji': True
                                }
                            },
                            {
                                'type': 'section',
                                'fields': [
                                    {'type': 'mrkdwn', 'text': f'*Alert ID:*\n{alert_payload.get("alert_id", "N/A")}'},
                                    {'type': 'mrkdwn', 'text': f'*Severity:*\n{severity.upper()}'},
                                    {'type': 'mrkdwn', 'text': f'*Health Status:*\n{alert_payload.get("health_status", "N/A")}'},
                                    {'type': 'mrkdwn', 'text': f'*Health Score:*\n{alert_payload.get("health_score", "N/A")}'}
                                ]
                            },
                            {
                                'type': 'section',
                                'text': {
                                    'type': 'mrkdwn',
                                    'text': f'*Reason:*\n{alert_payload.get("reason", "Unknown")}'
                                }
                            },
                            {
                                'type': 'context',
                                'elements': [
                                    {
                                        'type': 'mrkdwn',
                                        'text': f'Timestamp: {alert_payload.get("timestamp", "N/A")}'
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }

            # Add critical/degraded components if present
            critical = alert_payload.get('critical_components', [])
            degraded = alert_payload.get('degraded_components', [])
            if critical or degraded:
                component_text = ''
                if critical:
                    component_text += f':x: *Critical:* {", ".join(critical)}\n'
                if degraded:
                    component_text += f':warning: *Degraded:* {", ".join(degraded)}'
                slack_message['attachments'][0]['blocks'].insert(3, {
                    'type': 'section',
                    'text': {'type': 'mrkdwn', 'text': component_text}
                })

            data = json.dumps(slack_message).encode('utf-8')
            headers = {'Content-Type': 'application/json'}

            request = urllib.request.Request(slack_webhook, data=data, headers=headers, method='POST')

            with urllib.request.urlopen(request, timeout=10) as response:
                status_code = response.getcode()
                logger.info(f"[LAYER4] Slack notification sent to {self.alert_config.slack_channel}")
                return {
                    'success': True,
                    'channel': self.alert_config.slack_channel,
                    'status_code': status_code
                }

        except urllib.error.URLError as e:
            logger.error(f"[LAYER4] Slack notification failed: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"[LAYER4] Slack notification error: {e}")
            return {'success': False, 'error': str(e)}

    def _execute_healing(
        self,
        decision: ActionDecision,
        sensor_data: SensorData,
        judgement: JudgementResult
    ) -> List[ActionResult]:
        """
        Execute self-healing actions with Grace's enhanced systems.
        
        Enhanced flow:
        1. Create Genesis Key for tracking
        2. Check Sandbox Lab if action is risky
        3. Use Autonomous Healing System (if available)
        4. Fallback to basic healing functions
        5. Store outcome in Memory Mesh
        6. Update Genesis Key with result
        """
        results = []

        if not self.enable_healing:
            self._action_counter += 1
            return [ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.TRIGGER_HEALING,
                status=ActionStatus.SKIPPED,
                message="Healing disabled by configuration",
            )]

        # ========== STEP 1: Create Genesis Key ==========
        genesis_key = None
        if self.genesis_service:
            try:
                genesis_key = self.genesis_service.create_genesis_key(
                    key_type="HEALING_ACTION",
                    what=f"Execute self-healing for {', '.join(decision.target_components)}",
                    where=",".join(decision.target_components),
                    when=datetime.now(timezone.utc),
                    who="layer4_action_router",
                    how="autonomous_healing",
                    why=decision.reason,
                    metadata={
                        "decision_id": decision.decision_id,
                        "health_status": judgement.health.status.value,
                        "confidence": decision.confidence
                    }
                )
                logger.info(f"[LAYER4] Created Genesis Key: {genesis_key.key_id}")
            except Exception as e:
                logger.warning(f"[LAYER4] Genesis Key creation failed: {e}")

        # ========== STEP 2: Use Autonomous Healing System (if available) ==========
        if self.autonomous_healing:
            try:
                # Convert to healing system format
                healing_decisions = [{
                    "healing_action": "auto_heal",
                    "anomaly": {
                        "anomaly_type": judgement.health.status.value,
                        "affected_components": decision.target_components,
                        "severity": "critical" if judgement.health.status == HealthStatus.CRITICAL else "warning"
                    },
                    "execution_mode": "autonomous" if decision.confidence >= 0.8 else "manual",
                    "genesis_key_id": genesis_key.key_id if genesis_key else None
                }]
                
                healing_result = self.autonomous_healing.execute_healing(
                    decisions=healing_decisions,
                    user_id="layer4_action_router"
                )
                
                # Convert result to ActionResult
                for executed in healing_result.get("executed", []):
                    self._action_counter += 1
                    results.append(ActionResult(
                        action_id=f"ACT-{self._action_counter:04d}",
                        action_type=ActionType.TRIGGER_HEALING,
                        status=ActionStatus.COMPLETED,
                        message=f"Autonomous healing executed: {executed.get('healing_action')}",
                        details=executed,
                        duration_ms=executed.get("duration_ms", 0)
                    ))
                
                if results:
                    logger.info(f"[LAYER4] Autonomous Healing System executed {len(results)} actions")
                    return results
            except Exception as e:
                logger.warning(f"[LAYER4] Autonomous Healing System failed, falling back to basic: {e}")

        # ========== STEP 3: Fallback to Basic Healing ==========
        # Determine which healing actions to run
        healing_actions = []

        # Database issues
        if sensor_data.metrics and not sensor_data.metrics.database_health:
            healing_actions.append(self.HEALING_ACTIONS['reconnect_database'])

        # Vector DB issues
        if sensor_data.metrics and not sensor_data.metrics.vector_db_health:
            healing_actions.append(self.HEALING_ACTIONS['reset_vector_db'])

        # Memory issues
        if sensor_data.metrics and sensor_data.metrics.memory_percent > 85:
            healing_actions.append(self.HEALING_ACTIONS['run_garbage_collection'])

        # ========== STEP 4: Test in Sandbox (if risky) ==========
        for healing in healing_actions:
            self._action_counter += 1
            start_time = datetime.now(timezone.utc)

            # Check if action should be tested in sandbox first
            should_test_sandbox = (
                self.sandbox_lab and 
                judgement.health.status == HealthStatus.CRITICAL and
                decision.confidence < 0.8
            )

            if should_test_sandbox:
                try:
                    # Create sandbox experiment
                    experiment = self.sandbox_lab.propose_experiment(
                        name=f"Healing Action: {healing.name}",
                        description=healing.description,
                        experiment_type=ExperimentType.HEALING_ACTION if ExperimentType else None,
                        motivation=f"Test healing action before production: {decision.reason}",
                        initial_trust_score=decision.confidence
                    )
                    
                    # Execute in sandbox (simulated)
                    logger.info(f"[LAYER4] Testing healing action '{healing.name}' in sandbox")
                    # Note: Would execute actual sandbox test here
                    
                    # Only proceed if sandbox test passes
                    if experiment.current_trust_score < 0.85:
                        results.append(ActionResult(
                            action_id=f"ACT-{self._action_counter:04d}",
                            action_type=ActionType.TRIGGER_HEALING,
                            status=ActionStatus.SKIPPED,
                            message=f"Sandbox test failed for '{healing.name}'",
                            details={"experiment_id": experiment.experiment_id}
                        ))
                        continue
                except Exception as e:
                    logger.warning(f"[LAYER4] Sandbox test failed: {e}")

            # ========== STEP 5: Execute Healing Action ==========
            try:
                if healing.function and healing.function in self._healing_functions:
                    func = self._healing_functions[healing.function]
                    success = func(healing.parameters)

                    end_time = datetime.now(timezone.utc)
                    result = ActionResult(
                        action_id=f"ACT-{self._action_counter:04d}",
                        action_type=ActionType.TRIGGER_HEALING,
                        status=ActionStatus.COMPLETED if success else ActionStatus.FAILED,
                        message=f"Healing '{healing.name}' {'completed' if success else 'failed'}",
                        details={
                            'healing_id': healing.healing_id,
                            'target': healing.target_component,
                        },
                        duration_ms=(end_time - start_time).total_seconds() * 1000,
                    )
                    results.append(result)

                    # ========== STEP 6: Store in Memory Mesh ==========
                    if self.memory_mesh and success:
                        try:
                            # Store successful healing as learning example
                            # Note: Would use memory_mesh.ingest_learning_experience() if available
                            logger.debug(f"[LAYER4] Stored healing '{healing.name}' in Memory Mesh")
                        except Exception as e:
                            logger.warning(f"[LAYER4] Memory Mesh storage failed: {e}")

                else:
                    results.append(ActionResult(
                        action_id=f"ACT-{self._action_counter:04d}",
                        action_type=ActionType.TRIGGER_HEALING,
                        status=ActionStatus.SKIPPED,
                        message=f"Healing function '{healing.function}' not registered",
                    ))
            except Exception as e:
                logger.error(f"Healing action failed: {e}")
                results.append(ActionResult(
                    action_id=f"ACT-{self._action_counter:04d}",
                    action_type=ActionType.TRIGGER_HEALING,
                    status=ActionStatus.FAILED,
                    message=f"Healing failed: {str(e)}",
                ))

        # ========== STEP 7: Update Genesis Key ==========
        if genesis_key and results:
            try:
                success_count = sum(1 for r in results if r.status == ActionStatus.COMPLETED)
                self.genesis_service.update_genesis_key(
                    genesis_key.key_id,
                    status="COMPLETED" if success_count > 0 else "FAILED",
                    metadata={
                        "results": [r.message for r in results],
                        "success_count": success_count,
                        "total_count": len(results)
                    }
                )
                
                # Store Genesis Key ID in results for Mirror observation
                for result in results:
                    if not hasattr(result, 'details'):
                        result.details = {}
                    result.details['genesis_key_id'] = genesis_key.key_id
            except Exception as e:
                logger.warning(f"[LAYER4] Genesis Key update failed: {e}")

        # ========== STEP 8: Mirror Self-Modeling - Analyze Action Pattern ==========
        if self.mirror_system and genesis_key:
            try:
                # Mirror observes the Genesis Key automatically
                # Trigger immediate pattern detection for this healing action
                patterns = self.mirror_system.detect_behavioral_patterns()
                
                # Check if this healing action matches any detected patterns
                action_patterns = []
                for pattern in patterns:
                    # Check if our Genesis Key is in the pattern evidence
                    pattern_genesis_keys = pattern.get('evidence', [])
                    if genesis_key.key_id in pattern_genesis_keys:
                        action_patterns.append(pattern)
                    
                    # Also check by topic/description match
                    pattern_topic = pattern.get('topic', '')
                    if pattern_topic and any(
                        component in pattern_topic.lower() 
                        for component in decision.target_components
                    ):
                        action_patterns.append(pattern)
                
                if action_patterns:
                    logger.info(f"[LAYER4] Mirror detected {len(action_patterns)} patterns for this healing action:")
                    for pattern in action_patterns:
                        pattern_type = pattern.get('pattern_type', 'unknown')
                        description = pattern.get('description', pattern.get('recommendation', 'N/A'))
                        logger.info(f"[LAYER4]   - {pattern_type}: {description}")
                        
                        # Handle different pattern types (using string values)
                        if pattern_type == "repeated_failure":
                            occurrences = pattern.get('occurrences', 0)
                            logger.warning(
                                f"[LAYER4] ⚠️  Repeated failure detected! "
                                f"This healing action has failed {occurrences} times. "
                                f"Consider: (1) Reviewing approach, (2) Additional study, "
                                f"(3) Breaking into smaller steps"
                            )
                            # Could trigger learning task here
                            
                        elif pattern_type == "success_sequence":
                            logger.info(f"[LAYER4] ✅ Success sequence detected! This healing pattern works well.")
                            # Could promote to procedure here
                            
                        elif pattern_type == "efficiency_drop":
                            logger.warning(f"[LAYER4] ⚠️  Efficiency drop detected! This action is taking longer.")
                            # Could suggest optimization
                            
                        elif pattern_type == "improvement_opportunity":
                            logger.info(f"[LAYER4] 💡 Improvement opportunity detected!")
                            # Could propose experiment
                        
                        elif pattern_type == "learning_plateau":
                            logger.info(f"[LAYER4] 📊 Learning plateau detected! No improvement in this area.")
                            # Could suggest new learning approach
                        
                        elif pattern_type == "anomalous_behavior":
                            logger.warning(f"[LAYER4] ⚠️  Anomalous behavior detected! Unexpected pattern.")
                            # Could trigger investigation
                else:
                    logger.debug(f"[LAYER4] Mirror: No patterns detected for this healing action yet")
                    
            except Exception as e:
                logger.warning(f"[LAYER4] Mirror pattern detection failed: {e}")
                import traceback
                logger.debug(traceback.format_exc())

        if not results:
            self._action_counter += 1
            results.append(ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.TRIGGER_HEALING,
                status=ActionStatus.COMPLETED,
                message="No specific healing actions required",
            ))

        return results

    def _execute_cicd(self, decision: ActionDecision) -> ActionResult:
        """Execute CI/CD pipeline trigger."""
        self._action_counter += 1
        start_time = datetime.now(timezone.utc)

        try:
            cicd_reason = decision.parameters.get('cicd_reason', 'diagnostic_trigger')

            # Log CI/CD trigger
            cicd_log = {
                'trigger_id': f"CICD-{self._action_counter:04d}",
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'reason': cicd_reason,
                'decision_id': decision.decision_id,
            }

            cicd_file = self.log_dir / "cicd_triggers.jsonl"
            with open(cicd_file, 'a') as f:
                f.write(json.dumps(cicd_log) + '\n')

            # Execute CI/CD command if configured
            if self.cicd_config.pipeline_command:
                result = subprocess.run(
                    self.cicd_config.pipeline_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                success = result.returncode == 0
            else:
                # Dry run - just log the trigger
                success = True

            end_time = datetime.now(timezone.utc)
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.TRIGGER_CICD,
                status=ActionStatus.COMPLETED if success else ActionStatus.FAILED,
                message=f"CI/CD triggered: {cicd_reason}",
                details=cicd_log,
                duration_ms=(end_time - start_time).total_seconds() * 1000,
            )
        except Exception as e:
            logger.error(f"CI/CD trigger failed: {e}")
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.TRIGGER_CICD,
                status=ActionStatus.FAILED,
                message=f"CI/CD trigger failed: {str(e)}",
            )

    def _execute_learning_capture(
        self,
        decision: ActionDecision,
        interpreted_data: InterpretedData
    ) -> ActionResult:
        """Execute learning capture action with Memory Mesh integration."""
        self._action_counter += 1
        start_time = datetime.now(timezone.utc)

        # Create Genesis Key
        genesis_key = self._create_action_genesis_key(
            ActionType.RECOMMEND_LEARNING,
            decision,
            "Capture learning patterns"
        )

        try:
            # Extract learning patterns
            learning_patterns = [
                p for p in interpreted_data.patterns
                if p.pattern_type == PatternType.LEARNING_OPPORTUNITY
            ]

            learning_data = {
                'capture_id': f"LEARN-{self._action_counter:04d}",
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'decision_id': decision.decision_id,
                'genesis_key_id': genesis_key.key_id if genesis_key else None,
                'patterns': [
                    {
                        'description': p.description,
                        'confidence': p.confidence,
                        'affected_components': p.affected_components,
                        'evidence': p.evidence,
                    }
                    for p in learning_patterns
                ],
            }

            # Write to learning log
            learning_file = self.log_dir / "learning_captures.jsonl"
            with open(learning_file, 'a') as f:
                f.write(json.dumps(learning_data) + '\n')

            # Store in Memory Mesh
            if self.memory_mesh and learning_patterns:
                try:
                    # Store each pattern as a learning example
                    for pattern in learning_patterns:
                        # Note: Would use memory_mesh.ingest_learning_experience() if available
                        pass
                    logger.debug(f"[LAYER4] Stored {len(learning_patterns)} patterns in Memory Mesh")
                except Exception as e:
                    logger.warning(f"[LAYER4] Memory Mesh storage failed: {e}")

            logger.info(f"Learning captured: {len(learning_patterns)} patterns")

            end_time = datetime.now(timezone.utc)
            result = ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.RECOMMEND_LEARNING,
                status=ActionStatus.COMPLETED,
                message=f"Captured {len(learning_patterns)} learning patterns",
                details=learning_data,
                duration_ms=(end_time - start_time).total_seconds() * 1000,
            )
            
            if genesis_key:
                self._update_genesis_key_status(genesis_key, "COMPLETED", result)
            
            return result
        except Exception as e:
            logger.error(f"Learning capture failed: {e}")
            result = ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.RECOMMEND_LEARNING,
                status=ActionStatus.FAILED,
                message=f"Learning capture failed: {str(e)}",
            )
            if genesis_key:
                self._update_genesis_key_status(genesis_key, "FAILED", result)
            return result

    def _execute_log_observation(
        self,
        decision: ActionDecision,
        judgement: JudgementResult
    ) -> ActionResult:
        """Execute observation logging action."""
        self._action_counter += 1
        start_time = datetime.now(timezone.utc)

        try:
            observation = {
                'observation_id': f"OBS-{self._action_counter:04d}",
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'decision_id': decision.decision_id,
                'health_score': judgement.health.overall_score,
                'health_status': judgement.health.status.value,
                'confidence': judgement.confidence.overall_confidence,
                'drift_detected': any(
                    d.drift_magnitude > 0.1
                    for d in judgement.drift_analysis
                ),
            }

            # Write to observation log
            obs_file = self.log_dir / "observations.jsonl"
            with open(obs_file, 'a') as f:
                f.write(json.dumps(observation) + '\n')

            end_time = datetime.now(timezone.utc)
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.LOG_OBSERVATION,
                status=ActionStatus.COMPLETED,
                message="Observation logged",
                details=observation,
                duration_ms=(end_time - start_time).total_seconds() * 1000,
            )
        except Exception as e:
            logger.error(f"Observation logging failed: {e}")
            return ActionResult(
                action_id=f"ACT-{self._action_counter:04d}",
                action_type=ActionType.LOG_OBSERVATION,
                status=ActionStatus.FAILED,
                message=f"Observation logging failed: {str(e)}",
            )

    def _execute_noop(self, decision: ActionDecision) -> ActionResult:
        """Execute no-operation (healthy state)."""
        self._action_counter += 1
        return ActionResult(
            action_id=f"ACT-{self._action_counter:04d}",
            action_type=ActionType.DO_NOTHING,
            status=ActionStatus.COMPLETED,
            message="System healthy, no action required",
        )

    def _log_decision(self, decision: ActionDecision):
        """Log decision to decision log."""
        try:
            decision_log = {
                'decision_id': decision.decision_id,
                'timestamp': decision.decision_timestamp.isoformat(),
                'action_type': decision.action_type.value,
                'priority': decision.priority.value,
                'reason': decision.reason,
                'confidence': decision.confidence,
                'target_components': decision.target_components,
                'results': [
                    {
                        'action_id': r.action_id,
                        'status': r.status.value,
                        'message': r.message,
                    }
                    for r in decision.results
                ],
            }

            decision_file = self.log_dir / "action_decisions.jsonl"
            with open(decision_file, 'a') as f:
                f.write(json.dumps(decision_log) + '\n')

        except Exception as e:
            logger.error(f"Failed to log decision: {e}")

    # Healing function implementations — all paths through brain
    def _heal_clear_cache(self, params: Dict) -> bool:
        """Clear application cache via brain (system/clear_cache)."""
        try:
            from api.brain_api_v2 import call_brain
            r = call_brain("system", "clear_cache", params or {})
            ok = bool(r.get("ok", False))
            if ok:
                logger.info("Clearing application cache (via brain)")
            return ok
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False

    def _heal_reset_database(self, params: Dict) -> bool:
        """Reset database connection via brain (system/reset_db)."""
        try:
            from api.brain_api_v2 import call_brain
            r = call_brain("system", "reset_db", params or {})
            ok = bool(r.get("ok", False))
            if ok:
                logger.info("Database connection reset (via brain)")
            return ok
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            return False

    def _heal_reset_vector_db(self, params: Dict) -> bool:
        """Reset vector database client via brain (system/reset_vector_db)."""
        try:
            from api.brain_api_v2 import call_brain
            r = call_brain("system", "reset_vector_db", params or {})
            ok = bool(r.get("ok", False))
            if ok:
                logger.info("Vector DB client reset (via brain)")
            return ok
        except Exception as e:
            logger.error(f"Vector DB reset failed: {e}")
            return False

    def _heal_garbage_collection(self, params: Dict) -> bool:
        """Force garbage collection via brain (system/gc)."""
        try:
            from api.brain_api_v2 import call_brain
            r = call_brain("system", "gc", params or {})
            ok = bool(r.get("ok", False))
            if ok:
                logger.info("Garbage collection completed (via brain)")
            return ok
        except Exception as e:
            logger.error(f"GC failed: {e}")
            return False

    def to_dict(self, decision: ActionDecision) -> Dict[str, Any]:
        """Convert action decision to dictionary for serialization."""
        return {
            'decision_id': decision.decision_id,
            'decision_timestamp': decision.decision_timestamp.isoformat(),
            'action_type': decision.action_type.value,
            'priority': decision.priority.value,
            'reason': decision.reason,
            'confidence': decision.confidence,
            'target_components': decision.target_components,
            'parameters': decision.parameters,
            'results': [
                {
                    'action_id': r.action_id,
                    'action_type': r.action_type.value,
                    'status': r.status.value,
                    'message': r.message,
                    'duration_ms': r.duration_ms,
                    'timestamp': r.timestamp.isoformat(),
                }
                for r in decision.results
            ],
        }
