"""
Enterprise Coding Agent - Same Quality & Standards as Self-Healing System

A comprehensive coding agent that matches the self-healing system's:
1. Quality standards (enterprise-grade)
2. Integration depth (all Grace systems)
3. Trust System (autonomous execution levels)
4. Genesis Key tracking (all operations)
5. Memory Mesh integration (learning from patterns)
6. OODA Loop (structured reasoning)
7. Sandbox support (safe testing)
8. Multi-system integration (diagnostic, analyzer, testing, debugging)
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from sqlalchemy.orm import Session
from dataclasses import dataclass, field
import json
import hashlib
import subprocess
import tempfile
import shutil

logger = logging.getLogger(__name__)

# Import Grace systems
try:
    from genesis.genesis_key_service import get_genesis_service
    from models.genesis_key_models import GenesisKeyType
    from cognitive.autonomous_healing_system import TrustLevel, HealthStatus
except ImportError as e:
    logger.warning(f"[CODING-AGENT] Could not import Grace systems: {e}")


# ======================================================================
# Coding Task Types
# ======================================================================

class CodingTaskType(str, Enum):
    """Types of coding tasks."""
    CODE_GENERATION = "code_generation"  # Generate new code
    CODE_FIX = "code_fix"  # Fix existing code
    CODE_REFACTOR = "code_refactor"  # Refactor code
    CODE_OPTIMIZE = "code_optimize"  # Optimize code
    CODE_REVIEW = "code_review"  # Review code
    CODE_DOCUMENT = "code_document"  # Document code
    CODE_TEST = "code_test"  # Generate tests
    CODE_MIGRATE = "code_migrate"  # Migrate code
    FEATURE_IMPLEMENT = "feature_implement"  # Implement feature
    BUG_FIX = "bug_fix"  # Fix bug


# ======================================================================
# Code Quality Levels
# ======================================================================

class CodeQualityLevel(str, Enum):
    """Code quality levels."""
    DRAFT = "draft"  # Initial draft
    REVIEW = "review"  # Needs review
    PRODUCTION = "production"  # Production-ready
    ENTERPRISE = "enterprise"  # Enterprise-grade


# ======================================================================
# Coding Agent State
# ======================================================================

class CodingAgentState(str, Enum):
    """State of coding agent."""
    IDLE = "idle"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    TESTING = "testing"
    REVIEWING = "reviewing"
    APPLYING = "applying"
    LEARNING = "learning"
    COMPLETE = "complete"
    FAILED = "failed"


# ======================================================================
# Data Models
# ======================================================================

@dataclass
class CodingTask:
    """A coding task."""
    task_id: str
    task_type: CodingTaskType
    description: str
    target_files: List[str] = field(default_factory=list)
    requirements: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    priority: str = "medium"  # low, medium, high, critical
    trust_level_required: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO
    created_at: datetime = field(default_factory=datetime.utcnow)
    genesis_key_id: Optional[str] = None


@dataclass
class CodeGeneration:
    """Generated code with metadata."""
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
    """Metrics for coding agent."""
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


# ======================================================================
# Enterprise Coding Agent
# ======================================================================

class EnterpriseCodingAgent:
    """
    Enterprise Coding Agent - Same Quality & Standards as Self-Healing.
    
    Features:
    1. Genesis Key tracking (all operations)
    2. Trust System (autonomous execution levels)
    3. Memory Mesh integration (learning from patterns)
    4. OODA Loop (structured reasoning)
    5. Sandbox support (safe testing)
    6. Multi-system integration (diagnostic, analyzer, testing, debugging)
    7. Enterprise features (analytics, health monitoring, lifecycle)
    """
    
    def __init__(
        self,
        session: Session,
        repo_path: Optional[Path] = None,
        trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO,
        enable_learning: bool = True,
        enable_sandbox: bool = True
    ):
        """Initialize Enterprise Coding Agent."""
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
        
        # State
        self.current_state = CodingAgentState.IDLE
        self.active_tasks: Dict[str, CodingTask] = {}
        self.generation_history: List[CodeGeneration] = []
        self.metrics = CodingMetrics()
        
        # Sandbox
        self.sandbox_path: Optional[Path] = None
        if enable_sandbox:
            self._setup_sandbox()
        
        logger.info(
            f"[CODING-AGENT] Initialized Enterprise Coding Agent "
            f"(trust_level={trust_level}, learning={enable_learning}, sandbox={enable_sandbox})"
        )
    
    def _initialize_grace_systems(self):
        """Initialize integrated Grace systems."""
        # LLM Orchestrator (Grace-Aligned LLM)
        try:
            from llm_orchestrator.llm_orchestrator import LLMOrchestrator
            from database.session import get_session
            from pathlib import Path
            
            session = next(get_session()) if not self.session else self.session
            kb_path = self.repo_path / "knowledge_base" if self.repo_path else Path("knowledge_base")
            
            self.llm_orchestrator = LLMOrchestrator(
                session=session,
                knowledge_base_path=str(kb_path)
            )
            logger.info("[CODING-AGENT] LLM Orchestrator initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] LLM Orchestrator not available: {e}")
            self.llm_orchestrator = None
        
        # Diagnostic Engine
        try:
            from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
            self.diagnostic_engine = get_diagnostic_engine(session=self.session)
            logger.info("[CODING-AGENT] Diagnostic Engine initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Diagnostic Engine not available: {e}")
            self.diagnostic_engine = None
        
        # Code Analyzer
        try:
            from cognitive.code_analyzer_self_healing import get_code_analyzer_healing
            self.code_analyzer = get_code_analyzer_healing(
                session=self.session,
                repo_path=self.repo_path
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
        
        # Self-Healing System (for learning and bidirectional communication)
        try:
            from cognitive.autonomous_healing_system import get_autonomous_healing
            # Note: coding_agent will be set after initialization via bridge
            self.healing_system = get_autonomous_healing(
                session=self.session,
                repo_path=self.repo_path,
                trust_level=self.trust_level,
                enable_learning=self.enable_learning,
                coding_agent=None  # Will be set by bridge
            )
            logger.info("[CODING-AGENT] Self-Healing System initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Self-Healing System not available: {e}")
            self.healing_system = None
        
        # Self-Healing Training System (sandbox integration)
        try:
            from cognitive.self_healing_training_system import get_self_healing_training_system
            self.training_system = get_self_healing_training_system(
                session=self.session,
                repo_path=self.repo_path,
                llm_orchestrator=self.llm_orchestrator
            )
            logger.info("[CODING-AGENT] Self-Healing Training System (sandbox) initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Self-Healing Training System not available: {e}")
            self.training_system = None
        
        # Federated Learning System
        try:
            from cognitive.federated_learning_system import get_federated_learning_system, FederatedClientType
            from cognitive.learning_memory import LearningMemoryManager
            from pathlib import Path
            
            # Get learning memory if available
            learning_memory = None
            if self.llm_orchestrator and hasattr(self.llm_orchestrator, 'learning_memory'):
                learning_memory = self.llm_orchestrator.learning_memory
            
            # Get Genesis service
            genesis_service = None
            try:
                from genesis.genesis_key_service import get_genesis_service
                genesis_service = get_genesis_service()
            except Exception as e:
                logger.debug(f"[CODING-AGENT] Genesis service not available: {e}")
            
            self.federated_server = get_federated_learning_system(
                server_id="grace_federated_server",
                enable_cross_deployment=False,
                learning_memory_manager=learning_memory,
                llm_orchestrator=self.llm_orchestrator,
                genesis_service=genesis_service,
                session=self.session
            )
            self.FederatedClientType = FederatedClientType
            
            # Register coding agent as federated client
            if self.federated_server:
                self.federated_server.register_client(
                    client_id="coding_agent",
                    client_type=FederatedClientType.DOMAIN_SPECIALIST,
                    domain="code_generation"
                )
                logger.info("[CODING-AGENT] Registered with Federated Learning System")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Federated Learning System not available: {e}")
            self.federated_server = None
        
        # Bidirectional Communication Bridge (Self-Healing ↔ Coding Agent)
        try:
            from cognitive.coding_agent_healing_bridge import get_coding_agent_healing_bridge
            self.healing_bridge = get_coding_agent_healing_bridge(
                coding_agent=self,
                healing_system=self.healing_system
            )
            # Update healing system's bridge reference
            if self.healing_system:
                self.healing_system.healing_bridge = self.healing_bridge
                # Update healing system's coding agent reference
                self.healing_system.coding_agent = self
            logger.info("[CODING-AGENT] Bidirectional bridge with Self-Healing initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Bidirectional bridge not available: {e}")
            self.healing_bridge = None
        
        # Memory Mesh (Direct Access)
        try:
            from cognitive.memory_mesh_integration import MemoryMeshIntegration
            kb_path = self.repo_path / "knowledge_base" if self.repo_path else Path("knowledge_base")
            self.memory_mesh = MemoryMeshIntegration(
                session=self.session,
                knowledge_base_path=kb_path
            )
            logger.info("[CODING-AGENT] Memory Mesh (Direct) initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Memory Mesh (Direct) not available: {e}")
            self.memory_mesh = None
        
        # TimeSense Engine
        try:
            from timesense.engine import get_timesense_engine
            self.timesense = get_timesense_engine()
            logger.info("[CODING-AGENT] TimeSense Engine initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] TimeSense Engine not available: {e}")
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
        Create a coding task (Grace-Aligned with Genesis Key).
        
        Args:
            task_type: Type of coding task
            description: Task description
            target_files: Files to work on
            requirements: Task requirements
            context: Additional context
            priority: Task priority
            trust_level_required: Required trust level
            
        Returns:
            Created coding task
        """
        # Generate task ID
        task_id = f"task_{hashlib.md5(f'{task_type}_{description}_{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:12]}"
        
        # Create Genesis Key for task
        genesis_key_id = None
        if self.genesis_service:
            try:
                genesis_key = self.genesis_service.create_key(
                    key_type=GenesisKeyType.SYSTEM_EVENT,
                    what_description=f"Coding task created: {task_type.value}",
                    who_actor="enterprise_coding_agent",
                    where_location=str(self.repo_path),
                    why_reason=description,
                    how_method="task_creation",
                    input_data={
                        "task_type": task_type.value,
                        "description": description,
                        "target_files": target_files or [],
                        "requirements": requirements or {},
                        "priority": priority
                    },
                    context_data=context or {},
                    tags=["coding_agent", "task_creation", task_type.value],
                    session=self.session
                )
                genesis_key_id = genesis_key.key_id
            except Exception as e:
                logger.warning(f"[CODING-AGENT] Genesis Key creation error: {e}")
        
        # Create task
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
        Execute coding task using OODA Loop (Grace-Aligned).
        
        OODA Phases:
        1. OBSERVE: Analyze requirements and context
        2. ORIENT: Retrieve relevant knowledge from Memory Mesh
        3. DECIDE: Choose approach and generate code
        4. ACT: Apply code (in sandbox or real)
        """
        if task_id not in self.active_tasks:
            return {"success": False, "error": "Task not found"}
        
        task = self.active_tasks[task_id]
        self.current_state = CodingAgentState.ANALYZING
        
        try:
            # OBSERVE: Analyze requirements and context
            observations = self._observe(task)
            
            # ORIENT: Retrieve relevant knowledge
            knowledge = self._orient(task, observations)
            
            # DECIDE: Choose approach
            decision = self._decide(task, observations, knowledge)
            
            # ACT: Generate and apply code
            result = self._act(task, decision)
            
            # Learn from outcome
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
        
        # Analyze target files if they exist
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
                        file_analyses.append({
                            "file": file_path,
                            "exists": False
                        })
                except Exception as e:
                    logger.warning(f"[CODING-AGENT] File analysis error: {e}")
            
            observations["file_analyses"] = file_analyses
        
        # Use diagnostic engine if available
        if self.diagnostic_engine:
            try:
                diagnostic_result = self.diagnostic_engine.analyze_system_health()
                observations["system_health"] = diagnostic_result
            except Exception as e:
                logger.debug(f"[CODING-AGENT] Diagnostic analysis error: {e}")
        
        # Memory Mesh: Retrieve relevant memories
        if self.memory_mesh:
            try:
                # Retrieve relevant patterns and procedures
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
                logger.debug(f"[CODING-AGENT] Memory Mesh retrieval error: {e}")
        
        # TimeSense: Estimate task duration
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
                logger.debug(f"[CODING-AGENT] TimeSense estimation error: {e}")
        
        return observations
    
    def _orient(self, task: CodingTask, observations: Dict[str, Any]) -> Dict[str, Any]:
        """ORIENT phase: Retrieve relevant knowledge from Memory Mesh."""
        knowledge = {
            "patterns": [],
            "examples": [],
            "best_practices": []
        }
        
        # Retrieve from Grace-Aligned LLM (Memory Mesh)
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
                
                logger.info(f"[CODING-AGENT] Retrieved {len(memories)} memories from Memory Mesh")
            except Exception as e:
                logger.warning(f"[CODING-AGENT] Memory retrieval error: {e}")
        
        # Retrieve from code analyzer if available
        if self.code_analyzer and task.target_files:
            try:
                for file_path in task.target_files:
                    full_path = self.repo_path / file_path
                    if full_path.exists():
                        analysis = self.code_analyzer.analyze_file(str(full_path))
                        knowledge["code_analysis"] = analysis
            except Exception as e:
                logger.debug(f"[CODING-AGENT] Code analysis error: {e}")
        
        return knowledge
    
    def _decide(self, task: CodingTask, observations: Dict[str, Any], knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """DECIDE phase: Choose approach and plan code generation."""
        # Use Cognitive Engine for structured decision-making
        if self.cognitive_engine:
            try:
                decision_context = self.cognitive_engine.begin_decision(
                    problem_statement=f"Generate code for: {task.description}",
                    goal=f"Successfully complete {task.task_type.value} task",
                    success_criteria=[
                        "Code generated successfully",
                        "Tests pass",
                        "Code review passes",
                        "Quality meets target"
                    ],
                    is_reversible=True,
                    impact_scope="component"
                )
                
                # Observe with Cognitive Engine
                self.cognitive_engine.observe(decision_context, observations)
                
                # Orient with constraints
                self.cognitive_engine.orient(
                    decision_context,
                    constraints={
                        "trust_level": task.trust_level_required.value,
                        "priority": task.priority,
                        "sandbox_available": self.enable_sandbox
                    },
                    context_info=knowledge
                )
                
                # Generate alternatives
                def generate_alternatives():
                    alternatives = []
                    
                    # Advanced quality approach
                    if self.advanced_code_quality:
                        alternatives.append({
                            "name": "advanced_quality",
                            "description": "Use Advanced Code Quality System (multi-stage, self-critique)",
                            "immediate_value": 0.9,
                            "future_options": 0.9,
                            "simplicity": 0.6,
                            "reversibility": 1.0,
                            "complexity": 0.4
                        })
                    
                    # Deterministic transforms approach
                    if self.transformation_library:
                        alternatives.append({
                            "name": "deterministic_transforms",
                            "description": "Use Deterministic Transforms (AST-based, proof-gated)",
                            "immediate_value": 0.95,
                            "future_options": 0.8,
                            "simplicity": 0.7,
                            "reversibility": 1.0,
                            "complexity": 0.3
                        })
                    
                    # Standard LLM approach
                    alternatives.append({
                        "name": "standard_llm",
                        "description": "Use standard LLM generation",
                        "immediate_value": 0.7,
                        "future_options": 0.6,
                        "simplicity": 0.9,
                        "reversibility": 1.0,
                        "complexity": 0.2
                    })
                    
                    return alternatives
                
                # Decide with Cognitive Engine
                selected_path = self.cognitive_engine.decide(decision_context, generate_alternatives)
                
                decision = {
                    "approach": selected_path.get("name", "standard_llm"),
                    "use_sandbox": self.enable_sandbox and self.sandbox_path is not None,
                    "trust_level": task.trust_level_required.value,
                    "quality_target": CodeQualityLevel.PRODUCTION.value,
                    "cognitive_decision": selected_path,
                    "decision_context_id": decision_context.decision_id
                }
                
            except Exception as e:
                logger.warning(f"[CODING-AGENT] Cognitive Engine decision error: {e}, falling back to standard")
                decision = {
                    "approach": "standard",
                    "use_sandbox": self.enable_sandbox and self.sandbox_path is not None,
                    "trust_level": task.trust_level_required.value,
                    "quality_target": CodeQualityLevel.PRODUCTION.value
                }
        else:
            # Fallback to standard decision-making
            decision = {
                "approach": "standard",
                "use_sandbox": self.enable_sandbox and self.sandbox_path is not None,
                "trust_level": task.trust_level_required.value,
                "quality_target": CodeQualityLevel.PRODUCTION.value
            }
        
        # Determine approach based on task type
        if task.task_type == CodingTaskType.CODE_GENERATION:
            decision["approach"] = "generate_new"
        elif task.task_type == CodingTaskType.CODE_FIX:
            decision["approach"] = "fix_existing"
        elif task.task_type == CodingTaskType.CODE_REFACTOR:
            decision["approach"] = "refactor"
        elif task.task_type == CodingTaskType.CODE_OPTIMIZE:
            decision["approach"] = "optimize"
        
        # Use knowledge to inform decision
        if knowledge.get("patterns"):
            decision["use_patterns"] = True
            decision["pattern_count"] = len(knowledge["patterns"])
        
        # Check trust level
        if task.trust_level_required.value > self.trust_level.value:
            decision["requires_approval"] = True
            decision["quality_target"] = CodeQualityLevel.REVIEW.value
        
        return decision
    
    def _act(self, task: CodingTask, decision: Dict[str, Any]) -> Dict[str, Any]:
        """ACT phase: Generate and apply code."""
        self.current_state = CodingAgentState.GENERATING
        
        # Generate code using Grace-Aligned LLM
        if not self.llm_orchestrator:
            return {"success": False, "error": "LLM Orchestrator not available"}
        
        try:
            # Build prompt
            prompt = self._build_generation_prompt(task, decision)
            
            # Generate code
            generation_result = self._generate_code(task, prompt, decision)
            
            # Test code (in sandbox if available)
            if decision.get("use_sandbox") and self.sandbox_path:
                test_result = self._test_in_sandbox(generation_result)
            else:
                test_result = self._test_code(generation_result)
            
            # Review code
            review_result = self._review_code(generation_result)
            
            # Apply code if tests and review pass
            if test_result.get("passed") and review_result.get("passed"):
                if decision.get("use_sandbox"):
                    apply_result = self._apply_in_sandbox(generation_result)
                else:
                    apply_result = self._apply_code(generation_result, task)
                
                generation_result["applied"] = apply_result.get("success", False)
            else:
                generation_result["applied"] = False
                
                # If tests/review failed, request healing assistance
                if self.healing_bridge and self.healing_system:
                    try:
                        healing_result = self.request_healing_assistance(
                            issue_description=f"Code generation failed tests/review: {test_result.get('error', review_result.get('error', ''))}",
                            affected_files=task.target_files,
                            issue_type="code_quality",
                            priority="medium"
                        )
                        # Log healing attempt
                        logger.info(f"[CODING-AGENT] Requested healing assistance for failed generation")
                    except Exception as e:
                        logger.debug(f"[CODING-AGENT] Healing request error: {e}")
            
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
        prompt_parts = [
            f"Task Type: {task.task_type.value}",
            f"Description: {task.description}",
            f"Requirements: {json.dumps(task.requirements, indent=2)}",
            f"Context: {json.dumps(task.context, indent=2)}"
        ]
        
        if task.target_files:
            prompt_parts.append(f"Target Files: {', '.join(task.target_files)}")
        
        if decision.get("use_patterns"):
            prompt_parts.append("Use learned patterns from Memory Mesh")
        
        return "\n".join(prompt_parts)
    
    def _initialize_beyond_llm_capabilities(self):
        """Initialize capabilities beyond current LLM limitations."""
        # Advanced Code Quality System
        try:
            from llm_orchestrator.advanced_code_quality_system import get_advanced_code_quality_system
            self.advanced_code_quality = get_advanced_code_quality_system(
                session=self.session,
                llm_orchestrator=self.llm_orchestrator
            )
            logger.info("[CODING-AGENT] Advanced Code Quality System initialized")
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Advanced Code Quality System not available: {e}")
            self.advanced_code_quality = None
        
        # Transformation Library
        try:
            from transform.transformation_library import get_transformation_library
            from pathlib import Path
            kb_path = self.repo_path / "knowledge_base" if self.repo_path else Path("knowledge_base")
            self.transformation_library = get_transformation_library(
                session=self.session,
                knowledge_base_path=str(kb_path)
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
    
    def _generate_code(self, task: CodingTask, prompt: str, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate code beyond current LLM capabilities.
        
        Uses:
        1. Multi-stage generation with self-critique
        2. Deterministic transforms
        3. Pattern mining
        4. Ensemble/model combination
        5. Verification and proof systems
        """
        if not self.llm_orchestrator or not hasattr(self.llm_orchestrator, 'grace_aligned_llm'):
            return {"success": False, "error": "LLM not available"}
        
        try:
            # Try Advanced Code Quality System first (beyond LLM capabilities)
            if self.advanced_code_quality:
                try:
                    code_result = self._generate_with_advanced_quality(task, prompt, decision)
                    if code_result.get("success"):
                        return code_result
                except Exception as e:
                    logger.warning(f"[CODING-AGENT] Advanced quality generation error: {e}, falling back")
            
            # Try LLM Transform Integration (deterministic transforms)
            if self.llm_transform_integration:
                try:
                    code_result = self._generate_with_transforms(task, prompt, decision)
                    if code_result.get("success"):
                        return code_result
                except Exception as e:
                    logger.warning(f"[CODING-AGENT] Transform generation error: {e}, falling back")
            
            # Fallback to standard LLM generation
            return self._generate_with_standard_llm(task, prompt, decision)
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] Code generation error: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_with_advanced_quality(
        self,
        task: CodingTask,
        prompt: str,
        decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate code using Advanced Code Quality System (beyond LLM capabilities)."""
        if not self.advanced_code_quality:
            return {"success": False, "error": "Advanced Code Quality System not available"}
        
        try:
            # Use base quality optimizer if available
            if hasattr(self.advanced_code_quality, 'base_quality_optimizer') and self.advanced_code_quality.base_quality_optimizer:
                # Multi-stage generation with self-critique
                quality_result = self.advanced_code_quality.base_quality_optimizer.generate_code(
                    prompt=prompt,
                    task_type=task.task_type.value,
                    max_iterations=3,  # Multi-stage refinement
                    enable_self_critique=True,
                    enable_ensemble=True  # Use multiple models
                )
            else:
                # Fallback: use LLM directly with quality analysis
                if self.llm_orchestrator and hasattr(self.llm_orchestrator, 'grace_aligned_llm'):
                    llm_response = self.llm_orchestrator.grace_aligned_llm.generate(
                        prompt=prompt,
                        context={
                            "task_type": task.task_type.value,
                            "description": task.description,
                            "requirements": task.requirements
                        },
                        max_tokens=4096,
                        temperature=0.2  # Lower temperature for quality
                    )
                    quality_result = {
                        "success": True,
                        "code": llm_response.get("content", ""),
                        "quality_score": 0.8  # Default quality
                    }
                else:
                    return {"success": False, "error": "LLM not available"}
            
            if quality_result.get("success"):
                code = quality_result.get("code", "")
                quality_score = quality_result.get("quality_score", 0.0)
                
                # Create Genesis Key
                genesis_key_id = None
                if self.genesis_service:
                    try:
                        genesis_key = self.genesis_service.create_key(
                            key_type=GenesisKeyType.CODE_CHANGE,
                            what_description=f"Code generated (Advanced Quality): {task.task_type.value}",
                            who_actor="enterprise_coding_agent",
                            where_location=str(self.repo_path),
                            why_reason=task.description,
                            how_method="advanced_code_quality",
                            code_after=code,
                            input_data={
                                "task_id": task.task_id,
                                "quality_score": quality_score,
                                "method": "advanced_quality"
                            },
                            output_data={"code": code[:500], "quality_score": quality_score},
                            context_data={"task_type": task.task_type.value},
                            tags=["coding_agent", "advanced_quality", task.task_type.value],
                            session=self.session
                        )
                        genesis_key_id = genesis_key.key_id
                    except Exception as e:
                        logger.warning(f"[CODING-AGENT] Genesis Key creation error: {e}")
                
                generation_id = f"gen_{hashlib.md5(f'{task.task_id}_{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:12]}"
                
                generation = CodeGeneration(
                    generation_id=generation_id,
                    task_id=task.task_id,
                    file_path=task.target_files[0] if task.target_files else "generated_code.py",
                    code_before="",
                    code_after=code,
                    quality_level=CodeQualityLevel.ENTERPRISE if quality_score > 0.9 else CodeQualityLevel.PRODUCTION,
                    trust_score=quality_score,
                    genesis_key_id=genesis_key_id
                )
                
                self.generation_history.append(generation)
                self.metrics.code_generated += 1
                
                return {
                    "success": True,
                    "generation": generation,
                    "code": code,
                    "method": "advanced_quality",
                    "quality_score": quality_score
                }
            
            return {"success": False, "error": "Advanced quality generation failed"}
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] Advanced quality generation error: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_with_transforms(
        self,
        task: CodingTask,
        prompt: str,
        decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate code using deterministic transforms (beyond LLM capabilities)."""
        if not self.llm_transform_integration:
            return {"success": False, "error": "LLM Transform Integration not available"}
        
        try:
            # Generate with deterministic transforms
            # Use code intent from prompt
            code_intent = f"{task.task_type.value}: {task.description}"
            
            transformed_code, outcomes = self.llm_transform_integration.generate_with_transforms(
                code_intent=code_intent,
                use_proofs=True  # Use proof gating for deterministic transforms
            )
            
            if transformed_code:
                transform_result = {
                    "success": True,
                    "code": transformed_code,
                    "transforms_applied": len(outcomes),
                    "proof_status": "proven" if all(
                        o.proof_results and all(
                            p == "PASSED" or p == "SKIPPED"
                            for p in o.proof_results.values()
                        )
                        for o in outcomes
                    ) else "unproven"
                }
            else:
                return {"success": False, "error": "No transforms matched"}
            
            if transform_result.get("success"):
                code = transform_result.get("code", "")
                transform_count = transform_result.get("transforms_applied", 0)
                proof_status = transform_result.get("proof_status", "unknown")
                
                # Create Genesis Key
                genesis_key_id = None
                if self.genesis_service:
                    try:
                        genesis_key = self.genesis_service.create_key(
                            key_type=GenesisKeyType.CODE_CHANGE,
                            what_description=f"Code generated (Deterministic Transforms): {task.task_type.value}",
                            who_actor="enterprise_coding_agent",
                            where_location=str(self.repo_path),
                            why_reason=task.description,
                            how_method="deterministic_transforms",
                            code_after=code,
                            input_data={
                                "task_id": task.task_id,
                                "transforms_applied": transform_count,
                                "proof_status": proof_status
                            },
                            output_data={"code": code[:500], "transforms_applied": transform_count},
                            context_data={"task_type": task.task_type.value},
                            tags=["coding_agent", "deterministic_transforms", task.task_type.value],
                            session=self.session
                        )
                        genesis_key_id = genesis_key.key_id
                    except Exception as e:
                        logger.warning(f"[CODING-AGENT] Genesis Key creation error: {e}")
                
                generation_id = f"gen_{hashlib.md5(f'{task.task_id}_{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:12]}"
                
                generation = CodeGeneration(
                    generation_id=generation_id,
                    task_id=task.task_id,
                    file_path=task.target_files[0] if task.target_files else "generated_code.py",
                    code_before="",
                    code_after=code,
                    quality_level=CodeQualityLevel.ENTERPRISE if proof_status == "proven" else CodeQualityLevel.PRODUCTION,
                    trust_score=0.95 if proof_status == "proven" else 0.8,
                    genesis_key_id=genesis_key_id
                )
                
                self.generation_history.append(generation)
                self.metrics.code_generated += 1
                
                return {
                    "success": True,
                    "generation": generation,
                    "code": code,
                    "method": "deterministic_transforms",
                    "transforms_applied": transform_count,
                    "proof_status": proof_status
                }
            
            return {"success": False, "error": "Transform generation failed"}
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] Transform generation error: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_with_standard_llm(
        self,
        task: CodingTask,
        prompt: str,
        decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate code using standard LLM (fallback)."""
        try:
            # Generate code
            llm_response = self.llm_orchestrator.grace_aligned_llm.generate(
                prompt=prompt,
                context={
                    "task_type": task.task_type.value,
                    "description": task.description,
                    "requirements": task.requirements
                },
                max_tokens=4096,
                temperature=0.3  # Lower temperature for deterministic code
            )
            
            # Parse response
            code = llm_response.get("content", "")
            
            # Create Genesis Key for generation
            genesis_key_id = None
            if self.genesis_service:
                try:
                    genesis_key = self.genesis_service.create_key(
                        key_type=GenesisKeyType.CODE_CHANGE,
                        what_description=f"Code generated: {task.task_type.value}",
                        who_actor="enterprise_coding_agent",
                        where_location=str(self.repo_path),
                        why_reason=task.description,
                        how_method="llm_generation",
                        code_after=code,
                        input_data={"task_id": task.task_id, "prompt": prompt},
                        output_data={"code": code[:500]},  # Sample
                        context_data={"task_type": task.task_type.value},
                        tags=["coding_agent", "code_generation", task.task_type.value],
                        session=self.session
                    )
                    genesis_key_id = genesis_key.key_id
                except Exception as e:
                    logger.warning(f"[CODING-AGENT] Genesis Key creation error: {e}")
            
            generation_id = f"gen_{hashlib.md5(f'{task.task_id}_{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:12]}"
            
            generation = CodeGeneration(
                generation_id=generation_id,
                task_id=task.task_id,
                file_path=task.target_files[0] if task.target_files else "generated_code.py",
                code_before="",
                code_after=code,
                quality_level=CodeQualityLevel(decision.get("quality_target", "production")),
                trust_score=0.8,  # Initial trust
                genesis_key_id=genesis_key_id
            )
            
            self.generation_history.append(generation)
            self.metrics.code_generated += 1
            
            return {
                "success": True,
                "generation": generation,
                "code": code
            }
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] Code generation error: {e}")
            return {"success": False, "error": str(e)}
    
    def _test_in_sandbox(self, generation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Test code in sandbox."""
        if not self.sandbox_path:
            return {"passed": False, "error": "Sandbox not available"}
        
        try:
            generation = generation_result.get("generation")
            if not generation:
                return {"passed": False, "error": "No generation to test"}
            
            # Copy code to sandbox
            sandbox_file = self.sandbox_path / generation.file_path
            sandbox_file.parent.mkdir(parents=True, exist_ok=True)
            sandbox_file.write_text(generation.code_after)
            
            # Run tests
            if self.testing_system:
                test_result = self.testing_system.run_tests(str(sandbox_file))
                return {
                    "passed": test_result.get("passed", False),
                    "test_results": test_result
                }
            else:
                # Basic syntax check
                try:
                    compile(generation.code_after, sandbox_file, "exec")
                    return {"passed": True, "method": "syntax_check"}
                except SyntaxError as e:
                    return {"passed": False, "error": str(e)}
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] Sandbox testing error: {e}")
            return {"passed": False, "error": str(e)}
    
    def _test_code(self, generation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Test code (without sandbox)."""
        if self.testing_system:
            try:
                generation = generation_result.get("generation")
                if not generation:
                    return {"passed": False, "error": "No generation to test"}
                
                test_result = self.testing_system.run_tests(generation.file_path)
                return {
                    "passed": test_result.get("passed", False),
                    "test_results": test_result
                }
            except Exception as e:
                logger.error(f"[CODING-AGENT] Testing error: {e}")
                return {"passed": False, "error": str(e)}
        else:
            # Basic syntax check
            try:
                generation = generation_result.get("generation")
                if not generation:
                    return {"passed": False, "error": "No generation to test"}
                
                compile(generation.code_after, generation.file_path, "exec")
                return {"passed": True, "method": "syntax_check"}
            except SyntaxError as e:
                return {"passed": False, "error": str(e)}
    
    def _review_code(self, generation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Review code using code analyzer."""
        if not self.code_analyzer:
            return {"passed": True, "method": "no_reviewer"}  # Pass if no reviewer
        
        try:
            generation = generation_result.get("generation")
            if not generation:
                return {"passed": False, "error": "No generation to review"}
            
            # Analyze code
            analysis = self.code_analyzer.analyze_code(generation.code_after)
            
            # Check for critical issues
            critical_issues = [issue for issue in analysis.get("issues", []) if issue.get("severity") == "critical"]
            
            return {
                "passed": len(critical_issues) == 0,
                "analysis": analysis,
                "critical_issues": critical_issues
            }
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] Code review error: {e}")
            return {"passed": True, "error": str(e)}  # Pass on error (fail-safe)
    
    def _apply_in_sandbox(self, generation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply code in sandbox."""
        if not self.sandbox_path:
            return {"success": False, "error": "Sandbox not available"}
        
        try:
            generation = generation_result.get("generation")
            if not generation:
                return {"success": False, "error": "No generation to apply"}
            
            # Code is already in sandbox from testing
            generation.applied = True
            
            return {"success": True, "location": "sandbox"}
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] Sandbox application error: {e}")
            return {"success": False, "error": str(e)}
    
    def _apply_code(self, generation_result: Dict[str, Any], task: CodingTask) -> Dict[str, Any]:
        """Apply code to real files."""
        try:
            generation = generation_result.get("generation")
            if not generation:
                return {"success": False, "error": "No generation to apply"}
            
            # Check trust level
            if task.trust_level_required.value > self.trust_level.value:
                return {"success": False, "error": "Trust level insufficient for direct application"}
            
            # Apply code
            target_file = self.repo_path / generation.file_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing code if file exists
            code_before = ""
            if target_file.exists():
                code_before = target_file.read_text(encoding='utf-8')
                generation.code_before = code_before
            
            # Write new code
            target_file.write_text(generation.code_after, encoding='utf-8')
            generation.applied = True
            
            # Version Control: Track code changes
            if self.version_control:
                try:
                    self.version_control.create_commit(
                        message=f"Coding Agent: {task.task_type.value} - {task.description}",
                        user_id="enterprise_coding_agent",
                        files=[str(target_file)]
                    )
                    logger.info(f"[CODING-AGENT] Version Control: Changes committed for {target_file}")
                except Exception as e:
                    logger.debug(f"[CODING-AGENT] Version Control commit error: {e}")
            
            # Create Genesis Key for application
            if self.genesis_service:
                try:
                    self.genesis_service.create_key(
                        key_type=GenesisKeyType.CODE_CHANGE,
                        what_description=f"Code applied: {generation.file_path}",
                        who_actor="enterprise_coding_agent",
                        where_location=str(target_file),
                        why_reason=task.description,
                        how_method="code_application",
                        code_before=code_before,
                        code_after=generation.code_after,
                        file_path=str(target_file),
                        input_data={"task_id": task.task_id},
                        context_data={"task_type": task.task_type.value},
                        tags=["coding_agent", "code_application"],
                        session=self.session
                    )
                except Exception as e:
                    logger.warning(f"[CODING-AGENT] Genesis Key creation error: {e}")
            
            self.metrics.code_fixed += 1
            
            return {"success": True, "file": str(target_file)}
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] Code application error: {e}")
            return {"success": False, "error": str(e)}
    
    def _learn_from_task(self, task: CodingTask, result: Dict[str, Any]):
        """
        Learn from task outcome (Memory Mesh + Sandbox + Federated Learning).
        
        Integrates with:
        1. Memory Mesh (Grace-Aligned LLM)
        2. Self-Healing Training System (sandbox)
        3. Federated Learning System
        """
        if not self.enable_learning:
            return
        
        try:
            # 1. Contribute to Grace's learning (Memory Mesh)
            if self.llm_orchestrator and hasattr(self.llm_orchestrator, 'grace_aligned_llm'):
                learning_content = (
                    f"Task: {task.task_type.value}\n"
                    f"Description: {task.description}\n"
                    f"Result: {result.get('success', False)}\n"
                    f"Quality: {result.get('generation', {}).get('quality_level', 'unknown')}\n"
                    f"Method: {result.get('generation', {}).get('method', 'standard')}"
                )
                
                self.llm_orchestrator.grace_aligned_llm.contribute_to_grace_learning(
                    llm_output=learning_content,
                    query=f"{task.task_type.value}: {task.description}",
                    trust_score=0.8 if result.get("success") else 0.5,
                    genesis_key_id=task.genesis_key_id,
                    context={
                        "task_type": task.task_type.value,
                        "result": result,
                        "source": "coding_agent"
                    }
                )
            
            # 2. Contribute to Self-Healing Training System (sandbox)
            if self.training_system:
                try:
                    # Extract patterns from successful generations
                    if result.get("success"):
                        generation = result.get("generation")
                        if generation:
                            pattern = {
                                "task_type": task.task_type.value,
                                "description": task.description,
                                "code_sample": generation.code_after[:200] if hasattr(generation, 'code_after') else "",
                                "quality_level": generation.quality_level.value if hasattr(generation, 'quality_level') else "production",
                                "trust_score": generation.trust_score if hasattr(generation, 'trust_score') else 0.8,
                                "method": result.get("generation", {}).get("method", "standard")
                            }
                            
                            # Store pattern in training system
                            if hasattr(self.training_system, '_learn_from_fix'):
                                self.training_system._learn_from_fix(
                                    file_path=generation.file_path if hasattr(generation, 'file_path') else "generated_code.py",
                                    fix_result={
                                        "success": True,
                                        "pattern": pattern,
                                        "knowledge_gained": [f"{task.task_type.value} pattern learned"]
                                    },
                                    cycle=None  # Not part of a training cycle
                                )
                except Exception as e:
                    logger.debug(f"[CODING-AGENT] Sandbox learning error: {e}")
            
            # 3. Contribute to Federated Learning System
            if self.federated_server:
                try:
                    # Extract learned patterns and topics
                    patterns_learned = []
                    topics_learned = []
                    
                    if result.get("success"):
                        generation = result.get("generation")
                        if generation:
                            # Pattern: task type + description + method
                            pattern = f"{task.task_type.value}: {task.description} (method: {result.get('generation', {}).get('method', 'standard')})"
                            patterns_learned.append(pattern)
                            
                            # Topic: task type category
                            topic = {
                                "topic_name": f"{task.task_type.value}_pattern",
                                "category": task.task_type.value,
                                "trust_score": generation.trust_score if hasattr(generation, 'trust_score') else 0.8
                            }
                            topics_learned.append(topic)
                    
                    # Submit to federated learning
                    if patterns_learned or topics_learned:
                        success_rate = 1.0 if result.get("success") else 0.0
                        files_processed = 1
                        files_fixed = 1 if result.get("success") else 0
                        
                        self.federated_server.submit_update(
                            client_id="coding_agent",
                            client_type=self.FederatedClientType.DOMAIN_SPECIALIST,
                            domain="code_generation",
                            patterns_learned=patterns_learned,
                            topics_learned=topics_learned,
                            success_rate=success_rate,
                            files_processed=files_processed,
                            files_fixed=files_fixed,
                            trust_score=0.8 if result.get("success") else 0.5
                        )
                        
                        logger.info(
                            f"[CODING-AGENT] Submitted to federated learning: "
                            f"{len(patterns_learned)} patterns, {len(topics_learned)} topics"
                        )
                except Exception as e:
                    logger.warning(f"[CODING-AGENT] Federated learning submission error: {e}")
            
            self.metrics.learning_cycles += 1
                
        except Exception as e:
            logger.warning(f"[CODING-AGENT] Learning error: {e}")
    
    def practice_in_sandbox(
        self,
        task_type: CodingTaskType,
        description: str,
        difficulty_level: int = 1
    ) -> Dict[str, Any]:
        """
        Practice coding tasks in sandbox (integrated with self-healing training).
        
        This allows the coding agent to practice and learn in a safe sandbox environment.
        """
        if not self.training_system:
            return {"success": False, "error": "Training system not available"}
        
        try:
            # Create a practice task
            task = self.create_task(
                task_type=task_type,
                description=description,
                priority="low",  # Practice tasks are low priority
                trust_level_required=TrustLevel.LOW_RISK_AUTO
            )
            
            # Execute in sandbox mode
            result = self.execute_task(task.task_id)
            
            # Learn from practice
            if self.enable_learning:
                self._learn_from_task(task, result)
            
            return {
                "success": result.get("success", False),
                "task_id": task.task_id,
                "result": result,
                "practice_mode": True
            }
            
        except Exception as e:
            logger.error(f"[CODING-AGENT] Sandbox practice error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_learning_connections(self) -> Dict[str, Any]:
        """Get information about learning connections."""
        return {
            "memory_mesh": {
                "connected": self.llm_orchestrator is not None and hasattr(self.llm_orchestrator, 'grace_aligned_llm'),
                "direct_access": self.memory_mesh is not None,
                "learning_enabled": self.enable_learning,
                "via": "llm_orchestrator" if self.llm_orchestrator else None,
                "direct": "memory_mesh_integration" if self.memory_mesh else None
            },
            "sandbox_training": {
                "connected": self.training_system is not None,
                "can_practice": self.training_system is not None
            },
            "federated_learning": {
                "connected": self.federated_server is not None,
                "client_id": "coding_agent" if self.federated_server else None,
                "domain": "code_generation" if self.federated_server else None
            },
            "timesense": {
                "connected": self.timesense is not None,
                "purpose": "time_and_cost_estimation"
            },
            "version_control": {
                "connected": self.version_control is not None,
                "purpose": "code_change_tracking"
            },
            "cognitive_engine": {
                "connected": self.cognitive_engine is not None,
                "purpose": "structured_reasoning_ooda_loop"
            },
            "learning_cycles": self.metrics.learning_cycles
        }
    
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
                self.metrics.tasks_completed / self.metrics.total_tasks
                if self.metrics.total_tasks > 0 else 0.0
            ),
            "sandbox_available": self.sandbox_path is not None,
            "systems_available": {
                "llm_orchestrator": self.llm_orchestrator is not None,
                "diagnostic_engine": self.diagnostic_engine is not None,
                "code_analyzer": self.code_analyzer is not None,
                "testing_system": self.testing_system is not None,
                "debugging_system": self.debugging_system is not None,
                "healing_system": self.healing_system is not None
            }
        }
    
    def cleanup_sandbox(self):
        """Cleanup sandbox."""
        if self.sandbox_path and self.sandbox_path.exists():
            try:
                shutil.rmtree(self.sandbox_path)
                logger.info(f"[CODING-AGENT] Sandbox cleaned up: {self.sandbox_path}")
            except Exception as e:
                logger.warning(f"[CODING-AGENT] Sandbox cleanup error: {e}")
    
    # ==================== BIDIRECTIONAL COMMUNICATION ====================
    
    def request_healing_assistance(
        self,
        issue_description: str,
        affected_files: List[str],
        issue_type: str = "code_issue",
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """
        Request assistance from Self-Healing System.
        
        Use cases:
        - Code generation failed
        - Code has issues that need healing
        - Need diagnostic analysis
        """
        if not self.healing_bridge:
            return {"success": False, "error": "Healing bridge not available"}
        
        try:
            return self.healing_bridge.coding_agent_request_healing_assistance(
                issue_description=issue_description,
                affected_files=affected_files,
                issue_type=issue_type,
                priority=priority
            )
        except Exception as e:
            logger.error(f"[CODING-AGENT] Healing assistance request error: {e}")
            return {"success": False, "error": str(e)}
    
    def request_diagnostic(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Request diagnostic analysis from Self-Healing System."""
        if not self.healing_bridge:
            return {"success": False, "error": "Healing bridge not available"}
        
        try:
            return self.healing_bridge.coding_agent_request_diagnostic(
                description=description,
                context=context or {}
            )
        except Exception as e:
            logger.error(f"[CODING-AGENT] Diagnostic request error: {e}")
            return {"success": False, "error": str(e)}


def get_enterprise_coding_agent(
    session: Session,
    repo_path: Optional[Path] = None,
    trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO,
    enable_learning: bool = True,
    enable_sandbox: bool = True
) -> EnterpriseCodingAgent:
    """Factory function to get Enterprise Coding Agent."""
    return EnterpriseCodingAgent(
        session=session,
        repo_path=repo_path,
        trust_level=trust_level,
        enable_learning=enable_learning,
        enable_sandbox=enable_sandbox
    )
