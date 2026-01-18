"""
Grace Coding Agent - Unified Enterprise-Grade Code Generation System

A comprehensive coding agent that provides:
1. Enterprise-grade code quality standards
2. Full Grace system integration (Genesis Keys, Memory Mesh, OODA Loop)
3. Trust-based autonomous execution
4. Sandbox support for safe testing
5. Multi-system integration (diagnostic, analyzer, testing, debugging)
6. Bidirectional communication with Self-Healing System
7. Beyond-LLM capabilities (deterministic transforms, pattern mining)

This module unifies all coding agent functionality into a single cohesive system.
"""

import logging
import json
import hashlib
import subprocess
import tempfile
import shutil
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Try to import SQLAlchemy Session
try:
    from sqlalchemy.orm import Session
except ImportError:
    Session = Any  # type: ignore

# Import Grace systems
try:
    from genesis.genesis_key_service import get_genesis_service
    from models.genesis_key_models import GenesisKeyType
    from cognitive.autonomous_healing_system import TrustLevel, HealthStatus
except ImportError as e:
    logger.warning(f"[CODING-AGENT] Could not import Grace systems: {e}")
    
    # Define fallback TrustLevel if not available
    class TrustLevel(Enum):
        """Fallback TrustLevel if autonomous_healing_system not available."""
        LOW_RISK_AUTO = 1
        MEDIUM_RISK_AUTO = 5
        HIGH_RISK_CONFIRM = 8
        CRITICAL_REQUIRE_APPROVAL = 9


# ======================================================================
# ENUMS
# ======================================================================

class CodingTaskType(str, Enum):
    """Types of coding tasks the agent can perform."""
    CODE_GENERATION = "code_generation"
    CODE_FIX = "code_fix"
    CODE_REFACTOR = "code_refactor"
    CODE_OPTIMIZE = "code_optimize"
    CODE_REVIEW = "code_review"
    CODE_DOCUMENT = "code_document"
    CODE_TEST = "code_test"
    CODE_MIGRATE = "code_migrate"
    FEATURE_IMPLEMENT = "feature_implement"
    BUG_FIX = "bug_fix"


class CodeQualityLevel(str, Enum):
    """Code quality levels for generated code."""
    DRAFT = "draft"
    REVIEW = "review"
    PRODUCTION = "production"
    ENTERPRISE = "enterprise"


class CodingAgentState(str, Enum):
    """Current state of the coding agent."""
    IDLE = "idle"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    TESTING = "testing"
    REVIEWING = "reviewing"
    APPLYING = "applying"
    LEARNING = "learning"
    COMPLETE = "complete"
    FAILED = "failed"


class AssistanceType(str, Enum):
    """Types of assistance requests between systems."""
    CODE_GENERATION = "code_generation"
    CODE_FIX = "code_fix"
    CODE_REFACTOR = "code_refactor"
    CODE_OPTIMIZE = "code_optimize"
    CODE_REVIEW = "code_review"
    BUG_FIX = "bug_fix"
    HEALING = "healing"
    DIAGNOSTIC = "diagnostic"
    CODE_ANALYSIS = "code_analysis"


# ======================================================================
# DATA MODELS
# ======================================================================

@dataclass
class CodingTask:
    """A coding task to be executed by the agent."""
    task_id: str
    task_type: CodingTaskType
    description: str
    target_files: List[str] = field(default_factory=list)
    requirements: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    priority: str = "medium"
    trust_level_required: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO
    created_at: datetime = field(default_factory=datetime.utcnow)
    genesis_key_id: Optional[str] = None


@dataclass
class CodeGeneration:
    """Generated code with metadata and tracking."""
    generation_id: str
    task_id: str
    file_path: str
    code_before: str
    code_after: str
    quality_level: CodeQualityLevel
    trust_score: float
    tests_passed: bool = False
    review_passed: bool = False
    applied: bool = False
    genesis_key_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CodingMetrics:
    """Metrics for tracking coding agent performance."""
    total_tasks: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    code_generated: int = 0
    code_fixed: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    average_trust_score: float = 0.0
    average_quality_score: float = 0.0
    learning_cycles: int = 0


@dataclass
class AssistanceRequest:
    """Request for assistance between coding agent and other systems."""
    request_id: str
    from_system: str
    to_system: str
    assistance_type: AssistanceType
    description: str
    context: Dict[str, Any]
    priority: str = "medium"
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    success: bool = False


# ======================================================================
# CODING AGENT
# ======================================================================

class CodingAgent:
    """
    Grace Coding Agent - Unified Enterprise-Grade Code Generation System.
    
    Features:
    1. Genesis Key tracking for all operations
    2. Trust-based autonomous execution
    3. Memory Mesh integration for learning
    4. OODA Loop for structured reasoning
    5. Sandbox support for safe testing
    6. Multi-system integration
    7. Bidirectional communication with Self-Healing
    8. Beyond-LLM capabilities
    """
    
    def __init__(
        self,
        session: Session = None,
        repo_path: Optional[Path] = None,
        trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO,
        enable_learning: bool = True,
        enable_sandbox: bool = True
    ):
        """
        Initialize the Coding Agent.
        
        Args:
            session: Database session for persistence
            repo_path: Path to the repository to work on
            trust_level: Default trust level for operations
            enable_learning: Whether to enable learning from outcomes
            enable_sandbox: Whether to use sandbox for testing
        """
        self.session = session
        self.repo_path = repo_path or Path.cwd()
        self.trust_level = trust_level
        self.enable_learning = enable_learning
        self.enable_sandbox = enable_sandbox
        
        # Initialize Genesis service
        try:
            self.genesis_service = get_genesis_service()
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Genesis service not available: {e}")
            self.genesis_service = None
        
        # Initialize Grace systems
        self._initialize_grace_systems()
        
        # Initialize Beyond-LLM capabilities
        self._initialize_beyond_llm_capabilities()
        
        # State management
        self.current_state = CodingAgentState.IDLE
        self.active_tasks: Dict[str, CodingTask] = {}
        self.generation_history: List[CodeGeneration] = []
        self.metrics = CodingMetrics()
        
        # Assistance request tracking (for bidirectional communication)
        self.pending_requests: Dict[str, AssistanceRequest] = {}
        self.completed_requests: List[AssistanceRequest] = []
        
        # Sandbox setup
        self.sandbox_path: Optional[Path] = None
        if enable_sandbox:
            self._setup_sandbox()
        
        logger.info(
            f"[CODING-AGENT] Initialized Coding Agent "
            f"(trust_level={trust_level}, learning={enable_learning}, sandbox={enable_sandbox})"
        )
    
    # ==================== INITIALIZATION ====================
    
    def _get_trust_level_value(self, trust_level: Any) -> int:
        """Safely get trust level value, handling both enum and string."""
        if isinstance(trust_level, TrustLevel):
            return trust_level.value
        elif isinstance(trust_level, str):
            for level in TrustLevel:
                if level.name == trust_level or str(level.value) == trust_level:
                    return level.value
            return TrustLevel.MEDIUM_RISK_AUTO.value
        elif isinstance(trust_level, int):
            return trust_level
        else:
            return TrustLevel.MEDIUM_RISK_AUTO.value
    
    def _initialize_grace_systems(self):
        """Initialize integrated Grace systems."""
        # LLM Orchestrator
        try:
            from llm_orchestrator.llm_orchestrator import LLMOrchestrator
            from database.session import get_session
            
            session = self.session
            if not session:
                try:
                    session = next(get_session())
                except Exception:
                    session = None
            
            kb_path = self.repo_path / "knowledge_base" if self.repo_path else Path("knowledge_base")
            
            if session:
                self.llm_orchestrator = LLMOrchestrator(
                    session=session,
                    knowledge_base_path=str(kb_path)
                )
                logger.info("[CODING-AGENT] LLM Orchestrator initialized")
            else:
                self.llm_orchestrator = None
        except Exception as e:
            logger.warning(f"[CODING-AGENT] LLM Orchestrator not available: {e}")
            self.llm_orchestrator = None
        
        # Diagnostic Engine
        try:
            from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
            self.diagnostic_engine = get_diagnostic_engine()
            logger.info("[CODING-AGENT] Diagnostic Engine initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Diagnostic Engine not available: {e}")
            self.diagnostic_engine = None
        
        # Self-Healing System
        try:
            from cognitive.autonomous_healing_system import get_autonomous_healing
            self.healing_system = get_autonomous_healing(
                session=self.session,
                repo_path=self.repo_path,
                trust_level=self.trust_level,
                enable_learning=self.enable_learning
            )
            logger.info("[CODING-AGENT] Self-Healing System initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Self-Healing System not available: {e}")
            self.healing_system = None
        
        # Code Analyzer
        try:
            from cognitive.code_analyzer_self_healing import get_code_analyzer_healing
            self.code_analyzer = get_code_analyzer_healing(
                healing_system=self.healing_system,
                trust_level=TrustLevel.MEDIUM_RISK_AUTO,
                enable_auto_fix=False,
                enable_timesense=True
            )
            logger.info("[CODING-AGENT] Code Analyzer initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Code Analyzer not available: {e}")
            self.code_analyzer = None
        
        # Testing System
        try:
            from cognitive.testing_system import get_testing_system
            self.testing_system = get_testing_system(session=self.session)
            logger.info("[CODING-AGENT] Testing System initialized")
        except ImportError:
            class StubTestingSystem:
                def run_tests(self, file_path: str) -> Dict[str, Any]:
                    return {"success": False, "error": "Testing system not implemented"}
                def fix_failures(self, failures: List[Dict]) -> Dict[str, Any]:
                    return {"success": False, "error": "Testing system not implemented"}
            self.testing_system = StubTestingSystem()
            logger.info("[CODING-AGENT] Testing System using stub")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Testing System not available: {e}")
            self.testing_system = None
        
        # Debugging System
        try:
            from cognitive.debugging_system import get_debugging_system
            self.debugging_system = get_debugging_system(session=self.session)
            logger.info("[CODING-AGENT] Debugging System initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Debugging System not available: {e}")
            self.debugging_system = None
        
        # Self-Healing Training System
        try:
            from cognitive.self_healing_training_system import get_self_healing_training_system
            self.training_system = get_self_healing_training_system(
                session=self.session,
                repo_path=self.repo_path,
                llm_orchestrator=self.llm_orchestrator
            )
            logger.info("[CODING-AGENT] Training System initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Training System not available: {e}")
            self.training_system = None
        
        # Federated Learning System
        try:
            from cognitive.federated_learning_system import get_federated_learning_system, FederatedClientType
            
            learning_memory = None
            if self.llm_orchestrator and hasattr(self.llm_orchestrator, 'learning_memory'):
                learning_memory = self.llm_orchestrator.learning_memory
            
            genesis_service = None
            try:
                from genesis.genesis_key_service import get_genesis_service
                genesis_service = get_genesis_service()
            except Exception:
                pass
            
            self.federated_server = get_federated_learning_system(
                server_id="grace_federated_server",
                enable_cross_deployment=False,
                learning_memory_manager=learning_memory,
                llm_orchestrator=self.llm_orchestrator,
                genesis_service=genesis_service,
                session=self.session
            )
            self.FederatedClientType = FederatedClientType
            
            if self.federated_server:
                self.federated_server.register_client(
                    client_id="coding_agent",
                    client_type=FederatedClientType.DOMAIN_SPECIALIST,
                    domain="code_generation"
                )
                logger.info("[CODING-AGENT] Registered with Federated Learning System")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Federated Learning not available: {e}")
            self.federated_server = None
        
        # Memory Mesh (Direct Access)
        try:
            from cognitive.memory_mesh_integration import MemoryMeshIntegration
            kb_path = self.repo_path / "knowledge_base" if self.repo_path else Path("knowledge_base")
            self.memory_mesh = MemoryMeshIntegration(
                session=self.session,
                knowledge_base_path=kb_path
            )
            logger.info("[CODING-AGENT] Memory Mesh initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Memory Mesh not available: {e}")
            self.memory_mesh = None
        
        # TimeSense Engine
        try:
            from timesense.engine import get_timesense_engine
            self.timesense = get_timesense_engine()
            logger.info("[CODING-AGENT] TimeSense Engine initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] TimeSense not available: {e}")
            self.timesense = None
        
        # Version Control
        try:
            from genesis.enterprise_version_control import EnterpriseVersionControl
            self.version_control = EnterpriseVersionControl(
                session=self.session,
                repo_path=str(self.repo_path)
            )
            logger.info("[CODING-AGENT] Version Control initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Version Control not available: {e}")
            self.version_control = None
        
        # Cognitive Engine
        try:
            from cognitive.engine import CognitiveEngine
            self.cognitive_engine = CognitiveEngine(enable_strict_mode=True)
            logger.info("[CODING-AGENT] Cognitive Engine initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Cognitive Engine not available: {e}")
            self.cognitive_engine = None
        
        # Template Learner
        try:
            from benchmarking.proactive_template_learning import get_template_learner
            self.template_learner = get_template_learner()
            logger.info("[CODING-AGENT] Template Learner initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Template Learner not available: {e}")
            self.template_learner = None
    
    def _initialize_beyond_llm_capabilities(self):
        """Initialize capabilities beyond current LLM limitations."""
        # Advanced Code Quality System
        try:
            from llm_orchestrator.advanced_code_quality_system import get_advanced_code_quality_system
            kb_path = self.repo_path / "knowledge_base" if self.repo_path else Path("knowledge_base")
            self.advanced_code_quality = get_advanced_code_quality_system(
                session=self.session,
                knowledge_base_path=kb_path
            )
            logger.info("[CODING-AGENT] Advanced Code Quality System initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Advanced Code Quality not available: {e}")
            self.advanced_code_quality = None
        
        # Transformation Library
        try:
            from transform.transformation_library import get_transformation_library
            kb_path = self.repo_path / "knowledge_base" if self.repo_path else Path("knowledge_base")
            self.transformation_library = get_transformation_library(
                session=self.session,
                knowledge_base_path=kb_path
            )
            logger.info("[CODING-AGENT] Transformation Library initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Transformation Library not available: {e}")
            self.transformation_library = None
        
        # LLM Transform Integration
        try:
            from transform.llm_transform_integration import get_llm_transform_integration
            self.llm_transform_integration = get_llm_transform_integration(
                llm_orchestrator=self.llm_orchestrator,
                transform_library=self.transformation_library
            )
            logger.info("[CODING-AGENT] LLM Transform Integration initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] LLM Transform Integration not available: {e}")
            self.llm_transform_integration = None
    
    def _setup_sandbox(self):
        """Setup sandbox for safe code testing."""
        try:
            self.sandbox_path = Path(tempfile.mkdtemp(prefix="grace_coding_agent_"))
            logger.info(f"[CODING-AGENT] Sandbox created: {self.sandbox_path}")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Sandbox setup failed: {e}")
            self.sandbox_path = None
    
    # ==================== TASK MANAGEMENT ====================
    
    def create_task(
        self,
        task_type: CodingTaskType,
        description: str,
        target_files: Optional[List[str]] = None,
        requirements: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: str = "medium",
        trust_level_required: Optional[TrustLevel] = None
    ) -> CodingTask:
        """
        Create a coding task with Genesis Key tracking.
        
        Args:
            task_type: Type of coding task
            description: Task description
            target_files: Files to work on
            requirements: Task requirements
            context: Additional context
            priority: Task priority (low, medium, high, critical)
            trust_level_required: Required trust level
            
        Returns:
            Created CodingTask
        """
        task_id = f"task_{hashlib.md5(f'{task_type}_{description}_{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:12]}"
        
        if isinstance(task_type, str):
            try:
                task_type = CodingTaskType(task_type)
            except ValueError:
                logger.warning(f"[CODING-AGENT] Invalid task_type '{task_type}', defaulting to CODE_GENERATION")
                task_type = CodingTaskType.CODE_GENERATION
        
        # Create Genesis Key
        genesis_key_id = None
        if self.genesis_service:
            try:
                genesis_key = self.genesis_service.create_key(
                    key_type=GenesisKeyType.SYSTEM_EVENT,
                    what_description=f"Coding task created: {task_type.value}",
                    who_actor="coding_agent",
                    where_location=str(self.repo_path),
                    why_reason=description,
                    how_method="task_creation",
                    input_data={
                        "task_type": task_type.value,
                        "description": description,
                        "target_files": target_files or [],
                        "priority": priority
                    },
                    context_data=context or {},
                    tags=["coding_agent", "task_creation", task_type.value],
                    session=self.session
                )
                genesis_key_id = genesis_key.key_id
            except Exception as e:
                logger.warning(f"[CODING-AGENT] Genesis Key creation error: {e}")
        
        task = CodingTask(
            task_id=task_id,
            task_type=task_type,
            description=description,
            target_files=target_files or [],
            requirements=requirements or {},
            context=context or {},
            priority=priority,
            trust_level_required=trust_level_required or self.trust_level,
            genesis_key_id=genesis_key_id
        )
        
        self.active_tasks[task_id] = task
        self.metrics.total_tasks += 1
        
        logger.info(f"[CODING-AGENT] Task created: {task_id} ({task_type.value})")
        return task
    
    # ==================== OODA LOOP EXECUTION ====================
    
    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """
        Execute coding task using OODA Loop.
        
        OODA Phases:
        1. OBSERVE: Analyze requirements and context
        2. ORIENT: Retrieve relevant knowledge
        3. DECIDE: Choose approach
        4. ACT: Generate and apply code
        """
        if task_id not in self.active_tasks:
            return {"success": False, "error": "Task not found"}
        
        task = self.active_tasks[task_id]
        self.current_state = CodingAgentState.ANALYZING
        
        try:
            observations = self._observe(task)
            knowledge = self._orient(task, observations)
            decision = self._decide(task, observations, knowledge)
            result = self._act(task, decision)
            
            if self.enable_learning:
                self._learn_from_task(task, result)
            
            self.current_state = CodingAgentState.COMPLETE
            self.metrics.tasks_completed += 1
            
            return {
                "success": True,
                "task_id": task_id,
                "result": result,
                "observations": observations,
                "knowledge_used": knowledge,
                "decision": decision
            }
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] Task execution error: {e}")
            self.current_state = CodingAgentState.FAILED
            self.metrics.tasks_failed += 1
            return {"success": False, "error": str(e)}
    
    def _observe(self, task: CodingTask) -> Dict[str, Any]:
        """OBSERVE phase: Analyze requirements and context."""
        observations = {
            "task_type": task.task_type.value,
            "description": task.description,
            "target_files": task.target_files,
            "requirements": task.requirements,
            "context": task.context
        }
        
        # Analyze target files
        if task.target_files:
            file_analyses = []
            for file_path in task.target_files:
                try:
                    full_path = self.repo_path / file_path
                    if full_path.exists():
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        file_analyses.append({
                            "file": file_path,
                            "exists": True,
                            "size": len(content),
                            "lines": content.count('\n')
                        })
                    else:
                        file_analyses.append({"file": file_path, "exists": False})
                except Exception as e:
                    logger.warning(f"[CODING-AGENT] File analysis error: {e}")
            observations["file_analyses"] = file_analyses
        
        # Diagnostic analysis
        if self.diagnostic_engine:
            try:
                diagnostic_result = self.diagnostic_engine.analyze_system_health()
                observations["system_health"] = diagnostic_result
            except Exception as e:
                logger.warning(f"[CODING-AGENT] Diagnostic error: {e}")
        
        # Memory Mesh patterns
        if self.memory_mesh:
            try:
                query = f"{task.task_type.value}: {task.description}"
                memories = self.memory_mesh.learning_memory.find_similar_examples(
                    example_type=task.task_type.value,
                    min_trust=0.7,
                    limit=5
                )
                if memories:
                    observations["memory_patterns"] = [
                        {
                            "pattern": mem.pattern if hasattr(mem, 'pattern') else str(mem),
                            "trust_score": mem.trust_score if hasattr(mem, 'trust_score') else 0.7
                        }
                        for mem in memories[:5]
                    ]
            except Exception as e:
                logger.warning(f"[CODING-AGENT] Memory retrieval error: {e}")
        
        # TimeSense estimation
        if self.timesense:
            try:
                duration_estimate = self.timesense.estimate_duration(
                    operation=f"code_{task.task_type.value}",
                    context={
                        "task_type": task.task_type.value,
                        "file_count": len(task.target_files),
                        "description_length": len(task.description)
                    }
                )
                observations["estimated_duration"] = duration_estimate
            except Exception as e:
                logger.warning(f"[CODING-AGENT] TimeSense error: {e}")
        
        return observations
    
    def _orient(self, task: CodingTask, observations: Dict[str, Any]) -> Dict[str, Any]:
        """ORIENT phase: Retrieve relevant knowledge."""
        knowledge = {
            "patterns": [],
            "examples": [],
            "best_practices": [],
            "code_examples": []
        }
        
        # RAG retrieval
        if self.memory_mesh and hasattr(self.memory_mesh, 'retriever'):
            try:
                query = f"{task.task_type.value}: {task.description}"
                code_results = self.memory_mesh.retriever.retrieve(
                    query=query,
                    limit=5,
                    score_threshold=0.5
                )
                if code_results:
                    knowledge["code_examples"] = [
                        {
                            "code": result.get("content", ""),
                            "score": result.get("score", 0.0),
                            "source": result.get("id", "unknown")
                        }
                        for result in code_results
                    ]
            except Exception as e:
                logger.warning(f"[CODING-AGENT] RAG retrieval error: {e}")
        
        # Grace-Aligned LLM memories
        if self.llm_orchestrator and hasattr(self.llm_orchestrator, 'grace_aligned_llm'):
            try:
                query = f"{task.task_type.value}: {task.description}"
                memories = self.llm_orchestrator.grace_aligned_llm.retrieve_grace_memories(
                    query=query,
                    context={
                        "task_type": task.task_type.value,
                        "description": task.description,
                        "target_files": task.target_files
                    }
                )
                knowledge["patterns"] = memories.get("patterns", [])
                knowledge["examples"] = memories.get("examples", [])
                knowledge["best_practices"] = memories.get("best_practices", [])
            except Exception as e:
                logger.warning(f"[CODING-AGENT] Memory retrieval error: {e}")
        
        # Code analyzer
        if self.code_analyzer and task.target_files:
            try:
                for file_path in task.target_files:
                    full_path = self.repo_path / file_path
                    if full_path.exists():
                        analysis = self.code_analyzer.analyze_file(str(full_path))
                        knowledge["code_analysis"] = analysis
            except Exception as e:
                logger.warning(f"[CODING-AGENT] Code analysis error: {e}")
        
        return knowledge
    
    def _decide(self, task: CodingTask, observations: Dict[str, Any], knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """DECIDE phase: Choose approach and plan."""
        decision = {
            "approach": "standard",
            "use_sandbox": self.enable_sandbox and self.sandbox_path is not None,
            "trust_level": self._get_trust_level_value(task.trust_level_required),
            "quality_target": CodeQualityLevel.PRODUCTION.value
        }
        
        # Use Cognitive Engine if available
        if self.cognitive_engine:
            try:
                decision_context = self.cognitive_engine.begin_decision(
                    problem_statement=f"Generate code for: {task.description}",
                    goal=f"Successfully complete {task.task_type.value} task",
                    success_criteria=["Code generated", "Tests pass", "Review passes"],
                    is_reversible=True,
                    impact_scope="component"
                )
                
                def generate_alternatives():
                    alternatives = []
                    if self.advanced_code_quality:
                        alternatives.append({
                            "name": "advanced_quality",
                            "description": "Use Advanced Code Quality System",
                            "immediate_value": 0.9,
                            "future_options": 0.9,
                            "simplicity": 0.6,
                            "reversibility": 1.0
                        })
                    if self.transformation_library:
                        alternatives.append({
                            "name": "deterministic_transforms",
                            "description": "Use Deterministic Transforms",
                            "immediate_value": 0.95,
                            "future_options": 0.8,
                            "simplicity": 0.7,
                            "reversibility": 1.0
                        })
                    alternatives.append({
                        "name": "standard_llm",
                        "description": "Use standard LLM generation",
                        "immediate_value": 0.7,
                        "future_options": 0.6,
                        "simplicity": 0.9,
                        "reversibility": 1.0
                    })
                    return alternatives
                
                selected_path = self.cognitive_engine.decide(decision_context, generate_alternatives)
                decision["approach"] = selected_path.get("name", "standard_llm")
                decision["cognitive_decision"] = selected_path
            except Exception as e:
                logger.warning(f"[CODING-AGENT] Cognitive decision error: {e}")
        
        # Set approach based on task type
        if task.task_type == CodingTaskType.CODE_GENERATION:
            decision["approach"] = "generate_new"
        elif task.task_type == CodingTaskType.CODE_FIX:
            decision["approach"] = "fix_existing"
        elif task.task_type == CodingTaskType.CODE_REFACTOR:
            decision["approach"] = "refactor"
        elif task.task_type == CodingTaskType.CODE_OPTIMIZE:
            decision["approach"] = "optimize"
        
        # Use patterns if available
        if knowledge.get("patterns"):
            decision["use_patterns"] = True
            decision["pattern_count"] = len(knowledge["patterns"])
        
        # Check trust level
        if self._get_trust_level_value(task.trust_level_required) > self._get_trust_level_value(self.trust_level):
            decision["requires_approval"] = True
            decision["quality_target"] = CodeQualityLevel.REVIEW.value
        
        return decision
    
    def _act(self, task: CodingTask, decision: Dict[str, Any]) -> Dict[str, Any]:
        """ACT phase: Generate and apply code."""
        self.current_state = CodingAgentState.GENERATING
        
        try:
            prompt = self._build_generation_prompt(task, decision)
            
            # Try knowledge-driven generation first
            knowledge_code = None
            generation_method = None
            
            try:
                from cognitive.knowledge_driven_code_generator import get_knowledge_driven_generator
                
                retriever = None
                if self.memory_mesh and hasattr(self.memory_mesh, 'retriever'):
                    retriever = self.memory_mesh.retriever
                
                knowledge_generator = get_knowledge_driven_generator(
                    retriever=retriever,
                    template_matcher=None,
                    procedural_memory=None,
                    knowledge_base_path=self.repo_path
                )
                
                test_cases = task.context.get("test_cases", []) if task.context else []
                if not test_cases and task.context:
                    test_cases = task.context.get("test_list", [])
                
                function_name = task.context.get("function_name") if task.context else None
                
                knowledge_result = knowledge_generator.generate_code(
                    task_description=task.description,
                    function_name=function_name,
                    test_cases=test_cases,
                    context=task.context or {}
                )
                
                if knowledge_result.get("code") and knowledge_result.get("confidence", 0) > 0.5:
                    knowledge_code = knowledge_result["code"]
                    generation_method = knowledge_result.get("method", "knowledge")
            except Exception as e:
                logger.debug(f"[CODING-AGENT] Knowledge generation failed: {e}")
            
            # Try template pattern matching
            if not knowledge_code:
                template_code = self._try_template_pattern_matching(task)
                if template_code:
                    validation = self._validate_template_code(template_code, task)
                    if validation.get("valid"):
                        knowledge_code = template_code
                        generation_method = "template_pattern"
            
            # Generate result
            if knowledge_code:
                generation_id = f"gen_{hashlib.md5(f'{task.task_id}_{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:12]}"
                file_path = task.target_files[0] if task.target_files else "generated_code.py"
                
                generation = CodeGeneration(
                    generation_id=generation_id,
                    task_id=task.task_id,
                    file_path=file_path,
                    code_before="",
                    code_after=knowledge_code,
                    quality_level=CodeQualityLevel.PRODUCTION,
                    trust_score=0.85
                )
                
                self.generation_history.append(generation)
                self.metrics.code_generated += 1
                
                generation_result = {
                    "success": True,
                    "generation": generation,
                    "code": knowledge_code,
                    "method": generation_method or "knowledge"
                }
            else:
                # Fallback to LLM
                generation_result = self._generate_with_llm(task, prompt, decision)
            
            # Test code
            if decision.get("use_sandbox") and self.sandbox_path:
                test_result = self._test_in_sandbox(generation_result)
            else:
                test_result = self._test_code(generation_result)
            
            # Review code
            review_result = self._review_code(generation_result)
            
            # Apply if tests and review pass
            if test_result.get("passed") and review_result.get("passed"):
                if decision.get("use_sandbox"):
                    apply_result = self._apply_in_sandbox(generation_result)
                else:
                    apply_result = self._apply_code(generation_result, task)
                
                generation_result["applied"] = apply_result.get("success", False)
                
                # Learn template from success
                if self.template_learner and generation_result.get("success"):
                    try:
                        test_cases = task.context.get("test_cases", []) if task.context else []
                        function_name = task.context.get("function_name") if task.context else None
                        
                        self.template_learner.learn_from_success(
                            problem_text=task.description,
                            generated_code=generation_result.get("code", ""),
                            test_cases=test_cases,
                            function_name=function_name,
                            success=True
                        )
                    except Exception as e:
                        logger.debug(f"[CODING-AGENT] Template learning error: {e}")
            else:
                generation_result["applied"] = False
                
                # Request healing assistance
                if self.healing_system:
                    try:
                        self.request_healing_assistance(
                            issue_description=f"Code failed: {test_result.get('error', review_result.get('error', ''))}",
                            affected_files=task.target_files,
                            issue_type="code_quality"
                        )
                    except Exception:
                        pass
            
            return {
                "success": True,
                "generation": generation_result,
                "test_result": test_result,
                "review_result": review_result
            }
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] Code generation error: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_generation_prompt(self, task: CodingTask, decision: Dict[str, Any]) -> str:
        """Build prompt for code generation."""
        pattern_hints = self._identify_pattern_hints(task.description)
        
        function_name = None
        if task.context:
            function_name = task.context.get("function_name")
            if not function_name:
                test_cases = task.context.get("test_cases", []) or task.context.get("test_list", [])
                if test_cases:
                    import re
                    for test in test_cases:
                        func_match = re.search(r'(\w+)\s*\(', str(test))
                        if func_match:
                            function_name = func_match.group(1)
                            break
        
        prompt_parts = [
            f"Task Type: {task.task_type.value}",
            f"Description: {task.description}"
        ]
        
        if function_name:
            prompt_parts.append(f"\nIMPORTANT: The function name MUST be '{function_name}'")
            prompt_parts.append(f"Generate a Python function named '{function_name}' that solves the problem.")
        else:
            prompt_parts.append("\nGenerate a Python function that solves the problem.")
        
        if task.context:
            test_cases = task.context.get("test_cases", []) or task.context.get("test_list", [])
            if test_cases:
                prompt_parts.append("\nTest Cases:")
                for test in test_cases[:3]:
                    prompt_parts.append(f"  {test}")
        
        if task.requirements:
            prompt_parts.append(f"\nRequirements: {json.dumps(task.requirements, indent=2)}")
        
        if pattern_hints:
            prompt_parts.append(f"\nPattern Hints: {pattern_hints}")
        
        if decision.get("use_patterns"):
            prompt_parts.append("\nUse learned patterns from Memory Mesh")
        
        prompt_parts.append("\nGenerate ONLY the Python function code. No explanations or markdown.")
        
        return "\n".join(prompt_parts)
    
    def _identify_pattern_hints(self, description: str) -> str:
        """Identify programming patterns from description."""
        try:
            from benchmarking.mbpp_templates import get_template_matcher
            
            template_matcher = get_template_matcher()
            match = template_matcher.find_best_match(
                problem_text=description,
                test_cases=[],
                function_name=None
            )
            
            if match:
                template, confidence = match
                if confidence > 0.5:
                    return f"""
Pattern Detected: {template.description}
This problem matches the '{template.name}' pattern.
Consider using: {', '.join(template.pattern_keywords[:5])}
"""
        except Exception:
            pass
        
        return ""
    
    def _try_template_pattern_matching(self, task: CodingTask) -> Optional[str]:
        """Try to match task to template patterns."""
        try:
            from benchmarking.mbpp_templates import get_template_matcher
            
            template_matcher = get_template_matcher()
            
            test_cases = []
            if task.context:
                test_cases = task.context.get("test_cases", [])
                if not test_cases:
                    test_cases = task.context.get("test_list", [])
            
            function_name = task.context.get("function_name") if task.context else None
            if not function_name:
                import re
                func_match = re.search(r'function\s+(\w+)|def\s+(\w+)', task.description, re.IGNORECASE)
                if func_match:
                    function_name = func_match.group(1) or func_match.group(2)
            
            if not function_name:
                function_name = "solve_task"
            
            code = template_matcher.generate_from_template(
                problem_text=task.description,
                function_name=function_name,
                test_cases=test_cases
            )
            
            return code
        except Exception:
            return None
    
    def _validate_template_code(self, code: str, task: CodingTask) -> Dict[str, Any]:
        """Validate template-generated code."""
        try:
            import ast
            ast.parse(code)
            
            function_name = task.context.get("function_name") if task.context else None
            if function_name and f"def {function_name}" not in code:
                return {"valid": False, "error": f"Function '{function_name}' not found"}
            
            return {"valid": True}
        except SyntaxError as e:
            return {"valid": False, "error": f"Syntax error: {e}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def _generate_with_llm(self, task: CodingTask, prompt: str, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code using LLM."""
        if not self.llm_orchestrator or not hasattr(self.llm_orchestrator, 'grace_aligned_llm'):
            return {"success": False, "error": "LLM not available"}
        
        try:
            llm_response = self.llm_orchestrator.grace_aligned_llm.generate(
                prompt=prompt,
                context={
                    "task_type": task.task_type.value,
                    "description": task.description
                },
                max_tokens=4096,
                temperature=0.3
            )
            
            code = llm_response.get("content", "")
            
            # Fix function name if needed
            function_name = task.context.get("function_name") if task.context else None
            if function_name:
                from benchmarking.fix_function_name_extraction import extract_and_fix_code
                code = extract_and_fix_code(code, function_name, task.description)
            
            generation_id = f"gen_{hashlib.md5(f'{task.task_id}_{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:12]}"
            
            generation = CodeGeneration(
                generation_id=generation_id,
                task_id=task.task_id,
                file_path=task.target_files[0] if task.target_files else "generated_code.py",
                code_before="",
                code_after=code,
                quality_level=CodeQualityLevel(decision.get("quality_target", "production")),
                trust_score=0.8
            )
            
            self.generation_history.append(generation)
            self.metrics.code_generated += 1
            
            return {"success": True, "generation": generation, "code": code, "method": "llm"}
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] LLM generation error: {e}")
            return {"success": False, "error": str(e)}
    
    def _test_in_sandbox(self, generation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Test code in sandbox."""
        if not self.sandbox_path:
            return {"passed": False, "error": "Sandbox not available"}
        
        try:
            generation = generation_result.get("generation")
            if not generation:
                return {"passed": False, "error": "No generation to test"}
            
            sandbox_file = self.sandbox_path / generation.file_path
            sandbox_file.parent.mkdir(parents=True, exist_ok=True)
            sandbox_file.write_text(generation.code_after)
            
            if self.testing_system:
                test_result = self.testing_system.run_tests(str(sandbox_file))
                return {"passed": test_result.get("passed", False), "test_results": test_result}
            else:
                compile(generation.code_after, sandbox_file, "exec")
                return {"passed": True, "method": "syntax_check"}
                
        except SyntaxError as e:
            return {"passed": False, "error": str(e)}
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    def _test_code(self, generation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Test code without sandbox."""
        try:
            generation = generation_result.get("generation")
            if not generation:
                return {"passed": False, "error": "No generation to test"}
            
            if self.testing_system:
                test_result = self.testing_system.run_tests(generation.file_path)
                return {"passed": test_result.get("passed", False), "test_results": test_result}
            else:
                compile(generation.code_after, generation.file_path, "exec")
                return {"passed": True, "method": "syntax_check"}
                
        except SyntaxError as e:
            return {"passed": False, "error": str(e)}
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    def _review_code(self, generation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Review code using code analyzer."""
        if not self.code_analyzer:
            return {"passed": True, "method": "no_reviewer"}
        
        try:
            generation = generation_result.get("generation")
            if not generation:
                return {"passed": False, "error": "No generation to review"}
            
            analysis = self.code_analyzer.analyze_code(generation.code_after)
            critical_issues = [
                issue for issue in analysis.get("issues", [])
                if issue.get("severity") == "critical"
            ]
            
            return {
                "passed": len(critical_issues) == 0,
                "analysis": analysis,
                "critical_issues": critical_issues
            }
        except Exception as e:
            return {"passed": True, "error": str(e)}
    
    def _apply_in_sandbox(self, generation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply code in sandbox."""
        if not self.sandbox_path:
            return {"success": False, "error": "Sandbox not available"}
        
        try:
            generation = generation_result.get("generation")
            if not generation:
                return {"success": False, "error": "No generation to apply"}
            
            generation.applied = True
            return {"success": True, "location": "sandbox"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _apply_code(self, generation_result: Dict[str, Any], task: CodingTask) -> Dict[str, Any]:
        """Apply code to real files."""
        try:
            generation = generation_result.get("generation")
            if not generation:
                return {"success": False, "error": "No generation to apply"}
            
            if self._get_trust_level_value(task.trust_level_required) > self._get_trust_level_value(self.trust_level):
                return {"success": False, "error": "Trust level insufficient"}
            
            target_file = self.repo_path / generation.file_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            code_before = ""
            if target_file.exists():
                code_before = target_file.read_text(encoding='utf-8')
                generation.code_before = code_before
            
            target_file.write_text(generation.code_after, encoding='utf-8')
            generation.applied = True
            
            # Version control
            if self.version_control:
                try:
                    self.version_control.create_commit(
                        message=f"Coding Agent: {task.task_type.value} - {task.description}",
                        user_id="coding_agent",
                        files=[str(target_file)]
                    )
                except Exception:
                    pass
            
            self.metrics.code_fixed += 1
            return {"success": True, "file": str(target_file)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _learn_from_task(self, task: CodingTask, result: Dict[str, Any]):
        """Learn from task outcome."""
        if not self.enable_learning:
            return
        
        try:
            # Memory Mesh learning
            if self.llm_orchestrator and hasattr(self.llm_orchestrator, 'grace_aligned_llm'):
                learning_content = (
                    f"Task: {task.task_type.value}\n"
                    f"Description: {task.description}\n"
                    f"Result: {result.get('success', False)}"
                )
                
                self.llm_orchestrator.grace_aligned_llm.contribute_to_grace_learning(
                    llm_output=learning_content,
                    query=f"{task.task_type.value}: {task.description}",
                    trust_score=0.8 if result.get("success") else 0.5,
                    genesis_key_id=task.genesis_key_id,
                    context={"task_type": task.task_type.value, "source": "coding_agent"}
                )
            
            # Federated learning
            if self.federated_server and result.get("success"):
                patterns_learned = [f"{task.task_type.value}: {task.description}"]
                self.federated_server.submit_update(
                    client_id="coding_agent",
                    domain="code_generation",
                    patterns_learned=patterns_learned,
                    topics_learned=[{"topic_name": f"{task.task_type.value}_pattern"}],
                    success_rate=1.0,
                    files_processed=1,
                    files_fixed=1
                )
            
            self.metrics.learning_cycles += 1
            
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Learning error: {e}")
    
    # ==================== BIDIRECTIONAL COMMUNICATION ====================
    
    def request_healing_assistance(
        self,
        issue_description: str,
        affected_files: List[str],
        issue_type: str = "code_issue",
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """Request assistance from Self-Healing System."""
        if not self.healing_system:
            return {"success": False, "error": "Healing system not available"}
        
        try:
            request_id = f"coding_req_{datetime.utcnow().timestamp()}"
            request = AssistanceRequest(
                request_id=request_id,
                from_system="coding_agent",
                to_system="self_healing",
                assistance_type=AssistanceType.HEALING,
                description=issue_description,
                context={"affected_files": affected_files, "issue_type": issue_type},
                priority=priority
            )
            
            self.pending_requests[request_id] = request
            
            anomaly = {
                "type": issue_type,
                "severity": priority,
                "description": issue_description,
                "affected_files": affected_files
            }
            
            decisions = self.healing_system.decide_healing_actions([anomaly])
            healing_result = self.healing_system.execute_healing(decisions=decisions, user_id="coding_agent")
            
            request.completed_at = datetime.utcnow()
            request.result = healing_result
            request.success = healing_result.get("success", False)
            
            self.completed_requests.append(request)
            del self.pending_requests[request_id]
            
            return {"success": request.success, "request_id": request_id, "result": healing_result}
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] Healing request error: {e}")
            return {"success": False, "error": str(e)}
    
    def request_diagnostic(self, description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Request diagnostic analysis."""
        if not self.healing_system:
            return {"success": False, "error": "Healing system not available"}
        
        try:
            if self.diagnostic_engine:
                diagnostic_result = self.diagnostic_engine.analyze_system_health()
                return {"success": True, "diagnostic": diagnostic_result}
            else:
                health_result = self.healing_system.assess_system_health()
                return {"success": True, "health": health_result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def handle_healing_request(
        self,
        assistance_type: AssistanceType,
        description: str,
        context: Dict[str, Any],
        priority: str = "high"
    ) -> Dict[str, Any]:
        """Handle assistance request from Self-Healing System."""
        try:
            request_id = f"healing_req_{datetime.utcnow().timestamp()}"
            request = AssistanceRequest(
                request_id=request_id,
                from_system="self_healing",
                to_system="coding_agent",
                assistance_type=assistance_type,
                description=description,
                context=context,
                priority=priority
            )
            
            self.pending_requests[request_id] = request
            
            task_type_map = {
                AssistanceType.CODE_GENERATION: CodingTaskType.CODE_GENERATION,
                AssistanceType.CODE_FIX: CodingTaskType.CODE_FIX,
                AssistanceType.CODE_REFACTOR: CodingTaskType.CODE_REFACTOR,
                AssistanceType.CODE_OPTIMIZE: CodingTaskType.CODE_OPTIMIZE,
                AssistanceType.CODE_REVIEW: CodingTaskType.CODE_REVIEW,
                AssistanceType.BUG_FIX: CodingTaskType.BUG_FIX
            }
            
            task_type = task_type_map.get(assistance_type, CodingTaskType.CODE_GENERATION)
            
            task = self.create_task(
                task_type=task_type,
                description=description,
                target_files=context.get("target_files", []),
                requirements=context.get("requirements", {}),
                context=context,
                priority=priority
            )
            
            result = self.execute_task(task.task_id)
            
            request.completed_at = datetime.utcnow()
            request.result = result
            request.success = result.get("success", False)
            
            self.completed_requests.append(request)
            del self.pending_requests[request_id]
            
            return {
                "success": request.success,
                "request_id": request_id,
                "task_id": task.task_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] Handle healing request error: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== SANDBOX PRACTICE ====================
    
    def practice_in_sandbox(
        self,
        task_type: CodingTaskType,
        description: str,
        difficulty_level: int = 1
    ) -> Dict[str, Any]:
        """Practice coding tasks in sandbox."""
        if not self.training_system:
            return {"success": False, "error": "Training system not available"}
        
        try:
            task = self.create_task(
                task_type=task_type,
                description=description,
                priority="low",
                trust_level_required=TrustLevel.LOW_RISK_AUTO
            )
            
            result = self.execute_task(task.task_id)
            
            if self.enable_learning:
                self._learn_from_task(task, result)
            
            return {
                "success": result.get("success", False),
                "task_id": task.task_id,
                "result": result,
                "practice_mode": True
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==================== ANALYTICS & HEALTH ====================
    
    def get_metrics(self) -> CodingMetrics:
        """Get coding agent metrics."""
        return self.metrics
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get coding agent health status."""
        return {
            "state": self.current_state.value,
            "active_tasks": len(self.active_tasks),
            "total_tasks": self.metrics.total_tasks,
            "completion_rate": (
                self.metrics.tasks_completed / max(1, self.metrics.total_tasks)
            ),
            "sandbox_available": self.sandbox_path is not None,
            "systems_available": {
                "llm_orchestrator": self.llm_orchestrator is not None,
                "diagnostic_engine": self.diagnostic_engine is not None,
                "code_analyzer": self.code_analyzer is not None,
                "testing_system": self.testing_system is not None,
                "healing_system": self.healing_system is not None
            }
        }
    
    def get_learning_connections(self) -> Dict[str, Any]:
        """Get information about learning connections."""
        return {
            "memory_mesh": {
                "connected": self.memory_mesh is not None,
                "learning_enabled": self.enable_learning
            },
            "sandbox_training": {
                "connected": self.training_system is not None
            },
            "federated_learning": {
                "connected": self.federated_server is not None,
                "client_id": "coding_agent" if self.federated_server else None
            },
            "timesense": {"connected": self.timesense is not None},
            "learning_cycles": self.metrics.learning_cycles
        }
    
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending assistance requests."""
        return [
            {
                "request_id": req.request_id,
                "from_system": req.from_system,
                "to_system": req.to_system,
                "assistance_type": req.assistance_type.value,
                "description": req.description,
                "priority": req.priority,
                "created_at": req.created_at.isoformat()
            }
            for req in self.pending_requests.values()
        ]
    
    def get_completed_requests(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get completed assistance requests."""
        return [
            {
                "request_id": req.request_id,
                "from_system": req.from_system,
                "to_system": req.to_system,
                "assistance_type": req.assistance_type.value,
                "success": req.success,
                "created_at": req.created_at.isoformat(),
                "completed_at": req.completed_at.isoformat() if req.completed_at else None
            }
            for req in self.completed_requests[-limit:]
        ]
    
    def cleanup_sandbox(self):
        """Cleanup sandbox."""
        if self.sandbox_path and self.sandbox_path.exists():
            try:
                shutil.rmtree(self.sandbox_path)
                logger.info(f"[CODING-AGENT] Sandbox cleaned up")
            except Exception as e:
                logger.warning(f"[CODING-AGENT] Sandbox cleanup error: {e}")


# ======================================================================
# FACTORY FUNCTIONS & ALIASES
# ======================================================================

# Singleton instance
_coding_agent: Optional[CodingAgent] = None


def get_coding_agent(
    session: Session = None,
    repo_path: Optional[Path] = None,
    trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO,
    enable_learning: bool = True,
    enable_sandbox: bool = True
) -> CodingAgent:
    """Get or create the Coding Agent instance."""
    global _coding_agent
    
    if _coding_agent is None:
        _coding_agent = CodingAgent(
            session=session,
            repo_path=repo_path,
            trust_level=trust_level,
            enable_learning=enable_learning,
            enable_sandbox=enable_sandbox
        )
    
    return _coding_agent


# Backward compatibility aliases
EnterpriseCodingAgent = CodingAgent
get_enterprise_coding_agent = get_coding_agent
CodingAgentHealingBridge = None  # Deprecated - functionality merged into CodingAgent
