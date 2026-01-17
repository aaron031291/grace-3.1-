import logging
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

class InputType(str, Enum):
    """Types of input Layer 1 can receive."""
    TEXT = "text"
    VOICE = "voice"
    FILE_CHANGE = "file_change"
    ERROR = "error"
    DIAGNOSTIC = "diagnostic"
    WEBHOOK = "webhook"
    TASK_RESULT = "task_result"
    USER_ACTION = "user_action"


class IntentCategory(str, Enum):
    """Categories of user intent."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"
    EXPLAIN = "explain"
    FIX = "fix"
    TEST = "test"
    BUILD = "build"
    DEPLOY = "deploy"
    LEARN = "learn"
    CONFIGURE = "configure"
    UNKNOWN = "unknown"


class Layer1Intelligence:
    """
    Layer 1: Universal Input/Output Handler

    Connects to Layer1 MessageBus and provides IDE-specific processing.
    All input flows through here for tracking and routing.
    """

    def __init__(
        self,
        session=None,
        repo_path: Optional[Path] = None
    ):
        self.session = session
        self.repo_path = repo_path or Path.cwd()

        # Message bus connection
        self._message_bus = None

        # Input processors
        self._processors: Dict[InputType, callable] = {}

        # Genesis service for tracking
        self._genesis_service = None

        # Metrics
        self.metrics = {
            "inputs_processed": 0,
            "by_type": {}
        }

        logger.info("[LAYER1] Layer 1 Intelligence initialized")

    async def initialize(self):
        """Initialize Layer 1 connections."""
        try:
            # Connect to Layer1 MessageBus
            from layer1.message_bus import get_message_bus
            self._message_bus = get_message_bus()

            # Genesis service
            from genesis.genesis_key_service import GenesisKeyService
            self._genesis_service = GenesisKeyService(
                session=self.session,
                repo_path=str(self.repo_path)
            )

            # Register default processors
            self._register_default_processors()

            logger.info("[LAYER1] Connected to message bus")
            return True

        except Exception as e:
            logger.warning(f"[LAYER1] Initialization warning: {e}")
            return True  # Continue even with warnings

    def _register_default_processors(self):
        """Register default input processors."""
        self._processors[InputType.TEXT] = self._process_text
        self._processors[InputType.VOICE] = self._process_voice
        self._processors[InputType.FILE_CHANGE] = self._process_file_change
        self._processors[InputType.ERROR] = self._process_error
        self._processors[InputType.DIAGNOSTIC] = self._process_diagnostic

    async def process_input(
        self,
        input_text: str,
        input_type: str = "text",
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process input through Layer 1.

        Args:
            input_text: The input content
            input_type: Type of input (text, voice, etc.)
            context: Additional context

        Returns:
            Processed result with intent, entities, and routing info
        """
        context = context or {}

        try:
            input_type_enum = InputType(input_type)
        except ValueError:
            input_type_enum = InputType.TEXT

        # Track input
        self.metrics["inputs_processed"] += 1
        self.metrics["by_type"][input_type] = self.metrics["by_type"].get(input_type, 0) + 1

        # Get processor
        processor = self._processors.get(input_type_enum, self._process_text)

        # Process
        result = await processor(input_text, context)

        # Determine if cognitive processing needed
        result["requires_cognition"] = self._requires_cognition(result)

        # Log via genesis key
        if self._genesis_service:
            from models.genesis_key_models import GenesisKeyType
            self._genesis_service.create_key(
                key_type=GenesisKeyType.INPUT_RECEIVED,
                what_description=f"Layer1 input: {input_type}",
                who_actor="User",
                why_reason="User interaction",
                how_method="Layer1Intelligence.process_input",
                context_data={
                    "input_type": input_type,
                    "intent": result.get("intent"),
                    "requires_cognition": result.get("requires_cognition")
                },
                session=self.session
            )

        return result

    async def _process_text(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process text input."""
        # Extract intent
        intent = self._extract_intent(text)

        # Extract entities
        entities = self._extract_entities(text)

        return {
            "input_type": "text",
            "raw_input": text,
            "intent": intent,
            "entities": entities,
            "confidence": 0.8
        }

    async def _process_voice(self, transcript: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process voice input (already transcribed)."""
        result = await self._process_text(transcript, context)
        result["input_type"] = "voice"
        return result

    async def _process_file_change(self, change_info: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process file change event."""
        return {
            "input_type": "file_change",
            "raw_input": change_info,
            "intent": IntentCategory.UPDATE.value,
            "entities": {"file": change_info},
            "confidence": 1.0
        }

    async def _process_error(self, error_info: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process error event."""
        return {
            "input_type": "error",
            "raw_input": error_info,
            "intent": IntentCategory.FIX.value,
            "entities": {"error": error_info},
            "confidence": 0.9,
            "requires_cognition": True
        }

    async def _process_diagnostic(self, diagnostic: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process diagnostic event."""
        return {
            "input_type": "diagnostic",
            "raw_input": diagnostic,
            "intent": IntentCategory.FIX.value,
            "entities": {"diagnostic": diagnostic},
            "confidence": 0.85
        }

    def _extract_intent(self, text: str) -> str:
        """Extract intent from text."""
        text_lower = text.lower()

        intent_keywords = {
            IntentCategory.CREATE: ["create", "make", "add", "new", "generate"],
            IntentCategory.READ: ["show", "display", "get", "read", "open"],
            IntentCategory.UPDATE: ["update", "modify", "change", "edit"],
            IntentCategory.DELETE: ["delete", "remove", "clear"],
            IntentCategory.SEARCH: ["find", "search", "look", "where"],
            IntentCategory.EXPLAIN: ["explain", "what", "how", "why"],
            IntentCategory.FIX: ["fix", "heal", "repair", "solve", "debug"],
            IntentCategory.TEST: ["test", "verify", "check"],
            IntentCategory.BUILD: ["build", "compile", "package"],
            IntentCategory.DEPLOY: ["deploy", "release", "publish"],
            IntentCategory.LEARN: ["learn", "teach", "train", "remember"],
            IntentCategory.CONFIGURE: ["set", "configure", "setting"]
        }

        for intent, keywords in intent_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return intent.value

        return IntentCategory.UNKNOWN.value

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from text."""
        entities = {}

        # File references
        words = text.split()
        for word in words:
            if any(word.endswith(ext) for ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".css", ".html", ".json"]):
                entities["file"] = word

        # Function/class references
        for i, word in enumerate(words):
            if word in ["function", "def", "class", "method"]:
                if i + 1 < len(words):
                    entities["symbol"] = words[i + 1]

        return entities

    def _requires_cognition(self, result: Dict[str, Any]) -> bool:
        """Determine if input requires cognitive processing."""
        # Complex intents need cognition
        complex_intents = [
            IntentCategory.FIX.value,
            IntentCategory.EXPLAIN.value,
            IntentCategory.CREATE.value
        ]

        if result.get("intent") in complex_intents:
            return True

        # Low confidence needs cognition
        if result.get("confidence", 1.0) < 0.7:
            return True

        return False

    def get_metrics(self) -> Dict[str, Any]:
        """Get Layer 1 metrics."""
        return self.metrics


class Layer2Intelligence:
    """
    Layer 2: Cognitive Processing Engine

    Performs:
    - Deep intent analysis
    - Context-aware reasoning
    - OODA loop decision making
    - Multi-plane code understanding
    """

    def __init__(
        self,
        session=None,
        repo_path: Optional[Path] = None
    ):
        self.session = session
        self.repo_path = repo_path or Path.cwd()

        # Connected systems
        self._reasoner = None
        self._llm_orchestrator = None
        self._genesis_service = None
        self._memory_mesh = None
        self._rag_retriever = None
        self._world_model = None
        self._diagnostic_engine = None
        self._code_analyzer = None
        self._librarian = None
        self._mirror_system = None
        self._confidence_scorer = None
        self._cognitive_engine = None
        self._healing_system = None
        self._timesense = None
        self._clarity_framework = None
        self._failure_learning = None
        self._mutation_tracker = None
        self._self_updater = None
        self._neuro_symbolic_reasoner = None
        self._enterprise_neuro_symbolic = None
        self._enterprise_rag = None
        self._trust_aware_retriever = None
        
        # Layer 1 Message Bus connection (unified communication)
        self._message_bus = None
        self._genesis_keys_connector = None

        # Context memory
        self._context_memory: List[Dict[str, Any]] = []
        self._max_context = 20

        # Metrics
        self.metrics = {
            "cognitive_cycles": 0,
            "decisions_made": 0,
            "insights_generated": 0
        }

        logger.info("[LAYER2] Layer 2 Intelligence initialized")

    async def initialize(self):
        """Initialize Layer 2 systems with all core intelligence connections."""
        try:
            # Connect to Layer 1 Message Bus (unified communication layer) - BIDIRECTIONAL
            try:
                from layer1.message_bus import get_message_bus, ComponentType
                from layer1.message_bus import Message  # Import Message for type hints
                self._message_bus = get_message_bus()
                
                # Register Layer 2 as COGNITIVE_ENGINE component
                self._message_bus.register_component(
                    ComponentType.COGNITIVE_ENGINE,
                    self
                )
                logger.info("[LAYER2] Registered as COGNITIVE_ENGINE component on Layer 1 Message Bus")
                
                # Set up bidirectional communication
                self._register_layer1_request_handlers()
                self._subscribe_to_layer1_events()
                self._register_layer1_autonomous_actions()
                
                # Initialize Genesis Keys Connector through Layer 1
                try:
                    from layer1.components.genesis_keys_connector import create_genesis_keys_connector
                    kb_path = str(self.repo_path / "knowledge_base") if self.repo_path else "knowledge_base"
                    self._genesis_keys_connector = create_genesis_keys_connector(
                        session=self.session,
                        kb_path=kb_path,
                        message_bus=self._message_bus
                    )
                    logger.info("[LAYER2] Genesis Keys Connector initialized via Layer 1")
                except Exception as e:
                    logger.warning(f"[LAYER2] Genesis Keys Connector initialization failed: {e}")
            except Exception as e:
                logger.warning(f"[LAYER2] Layer 1 Message Bus connection failed: {e}")

            # Multi-plane reasoner
            from grace_os.reasoning_planes import MultiPlaneReasoner
            self._reasoner = MultiPlaneReasoner(self.session, self.repo_path)
            await self._reasoner.initialize()

            # LLM orchestrator
            from llm_orchestrator.llm_orchestrator import LLMOrchestrator
            kb_path = str(self.repo_path / "knowledge_base") if self.repo_path else "knowledge_base"
            self._llm_orchestrator = LLMOrchestrator(
                session=self.session,
                knowledge_base_path=kb_path
            )

            # Genesis service (direct access for compatibility, but prefer Layer 1 connector)
            from genesis.genesis_key_service import GenesisKeyService
            self._genesis_service = GenesisKeyService(
                session=self.session,
                repo_path=str(self.repo_path)
            )

            # Memory Mesh Integration (core intelligence)
            try:
                from cognitive.memory_mesh_integration import MemoryMeshIntegration
                kb_path_obj = self.repo_path / "knowledge_base" if self.repo_path else Path("knowledge_base")
                self._memory_mesh = MemoryMeshIntegration(self.session, kb_path_obj)
                logger.info("[LAYER2] Memory Mesh connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Memory Mesh connection failed: {e}")

            # RAG Retriever (core intelligence) - with Enterprise wrapper
            try:
                from retrieval.retriever import DocumentRetriever
                from embedding import get_embedding_model
                from retrieval.enterprise_rag import get_enterprise_rag
                embedding_model = get_embedding_model()
                base_retriever = DocumentRetriever(
                    collection_name="documents",
                    embedding_model=embedding_model
                )
                # Wrap with Enterprise RAG
                self._enterprise_rag = get_enterprise_rag(
                    session=self.session,
                    retriever=base_retriever,
                    cache_size=100
                )
                self._rag_retriever = base_retriever  # Keep base for compatibility
                logger.info("[LAYER2] Enterprise RAG connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Enterprise RAG connection failed: {e}")
                # Fallback to basic RAG
                try:
                    from retrieval.retriever import DocumentRetriever
                    from embedding import get_embedding_model
                    embedding_model = get_embedding_model()
                    self._rag_retriever = DocumentRetriever(
                        collection_name="documents",
                        embedding_model=embedding_model
                    )
                    logger.info("[LAYER2] Basic RAG Retriever connected (fallback)")
                except Exception as e2:
                    logger.warning(f"[LAYER2] Basic RAG Retriever connection failed: {e2}")

            # World Model (core intelligence)
            try:
                from world_model.enterprise_world_model import get_enterprise_world_model
                world_model_path = self.repo_path / ".genesis_world_model.json" if self.repo_path else Path(".genesis_world_model.json")
                self._world_model = get_enterprise_world_model(world_model_path)
                logger.info("[LAYER2] World Model connected")
            except Exception as e:
                logger.warning(f"[LAYER2] World Model connection failed: {e}")

            # Diagnostic Engine (system health analysis)
            try:
                from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
                self._diagnostic_engine = get_diagnostic_engine()
                logger.info("[LAYER2] Diagnostic Engine connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Diagnostic Engine connection failed: {e}")

            # Code Analyzer (code quality analysis)
            try:
                from cognitive.code_analyzer_self_healing import get_code_analyzer_healing
                self._code_analyzer = get_code_analyzer_healing(
                    session=self.session,
                    repo_path=str(self.repo_path)
                )
                logger.info("[LAYER2] Code Analyzer connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Code Analyzer connection failed: {e}")

            # Librarian (document organization)
            try:
                from librarian.enterprise_librarian import get_enterprise_librarian
                kb_path_obj = self.repo_path / "knowledge_base" if self.repo_path else Path("knowledge_base")
                self._librarian = get_enterprise_librarian(self.session, kb_path_obj)
                logger.info("[LAYER2] Librarian connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Librarian connection failed: {e}")

            # Mirror Self-Modeling System (self-reflection)
            try:
                from cognitive.mirror_self_modeling import get_mirror_system
                self._mirror_system = get_mirror_system(session=self.session)
                logger.info("[LAYER2] Mirror Self-Modeling System connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Mirror System connection failed: {e}")

            # Confidence Scorer (confidence assessment)
            try:
                from confidence_scorer.confidence_scorer import ConfidenceScorer
                from embedding import get_embedding_model
                embedding_model = get_embedding_model()
                self._confidence_scorer = ConfidenceScorer(
                    session=self.session,
                    embedding_model=embedding_model
                )
                logger.info("[LAYER2] Confidence Scorer connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Confidence Scorer connection failed: {e}")

            # Cognitive Engine (OODA loop processing)
            try:
                from cognitive.engine import CognitiveEngine
                self._cognitive_engine = CognitiveEngine(enable_strict_mode=False)
                logger.info("[LAYER2] Cognitive Engine connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Cognitive Engine connection failed: {e}")

            # Autonomous Healing System (self-healing)
            try:
                from cognitive.autonomous_healing_system import AutonomousHealingSystem
                self._healing_system = AutonomousHealingSystem(
                    session=self.session,
                    repo_path=self.repo_path
                )
                logger.info("[LAYER2] Autonomous Healing System connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Healing System connection failed: {e}")

            # TimeSense Engine (time estimation and tracking)
            try:
                from timesense.engine import get_timesense_engine
                self._timesense = get_timesense_engine()
                logger.info("[LAYER2] TimeSense Engine connected")
            except Exception as e:
                logger.warning(f"[LAYER2] TimeSense Engine connection failed: {e}")

            # Clarity Framework (ensuring clarity in all actions)
            try:
                from genesis_ide.clarity_framework import ClarityFramework
                self._clarity_framework = ClarityFramework(
                    session=self.session,
                    genesis_service=self._genesis_service
                )
                logger.info("[LAYER2] Clarity Framework connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Clarity Framework connection failed: {e}")

            # Failure Learning System (learning from failures)
            try:
                from genesis_ide.failure_learning import FailureLearningSystem
                from vector_db.qdrant_client import QdrantClient
                vector_db = QdrantClient()
                self._failure_learning = FailureLearningSystem(
                    session=self.session,
                    vector_db=vector_db
                )
                logger.info("[LAYER2] Failure Learning System connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Failure Learning System connection failed: {e}")

            # Mutation Tracker (tracking code changes)
            try:
                from genesis_ide.mutation_tracker import MutationTracker
                from version_control.git_service import GitService
                git_service = GitService(str(self.repo_path)) if self.repo_path else None
                if git_service:
                    self._mutation_tracker = MutationTracker(
                        session=self.session,
                        genesis_service=self._genesis_service,
                        git_service=git_service
                    )
                    logger.info("[LAYER2] Mutation Tracker connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Mutation Tracker connection failed: {e}")

            # Self-Updater (autonomous self-improvement)
            try:
                from genesis_ide.self_updater import SelfUpdater
                self._self_updater = SelfUpdater(
                    session=self.session,
                    repo_path=self.repo_path,
                    genesis_service=self._genesis_service
                )
                logger.info("[LAYER2] Self-Updater connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Self-Updater connection failed: {e}")

            # Neuro-Symbolic Reasoner (unified neural + symbolic reasoning)
            try:
                from ml_intelligence.neuro_symbolic_reasoner import get_neuro_symbolic_reasoner
                from cognitive.learning_memory import LearningMemoryManager
                from pathlib import Path
                
                # Get learning memory for symbolic component
                kb_path_obj = self.repo_path / "knowledge_base" if self.repo_path else Path("knowledge_base")
                learning_memory = LearningMemoryManager(self.session, kb_path_obj)
                
                # Create neuro-symbolic reasoner with RAG retriever
                if self._rag_retriever:
                    self._neuro_symbolic_reasoner = get_neuro_symbolic_reasoner(
                        retriever=self._rag_retriever,
                        learning_memory=learning_memory,
                        neural_weight=0.5,
                        symbolic_weight=0.5
                    )
                    logger.info("[LAYER2] Neuro-Symbolic Reasoner connected")
                    
                    # Wrap with Enterprise Neuro-Symbolic
                    try:
                        from ml_intelligence.enterprise_neuro_symbolic import get_enterprise_neuro_symbolic
                        self._enterprise_neuro_symbolic = get_enterprise_neuro_symbolic(
                            neuro_symbolic_reasoner=self._neuro_symbolic_reasoner,
                            archive_dir=self.repo_path / "archived_neuro_symbolic" if self.repo_path else None,
                            retention_days=90
                        )
                        logger.info("[LAYER2] Enterprise Neuro-Symbolic connected")
                    except Exception as e:
                        logger.warning(f"[LAYER2] Enterprise Neuro-Symbolic wrapper failed: {e}")
            except Exception as e:
                logger.warning(f"[LAYER2] Neuro-Symbolic Reasoner connection failed: {e}")

            # Trust-Aware Retriever (neuro-symbolic retrieval with trust scores)
            try:
                from retrieval.trust_aware_retriever import get_trust_aware_retriever
                if self._rag_retriever:
                    self._trust_aware_retriever = get_trust_aware_retriever(
                        base_retriever=self._rag_retriever,
                        trust_weight=0.3,
                        min_trust_threshold=0.3
                    )
                    logger.info("[LAYER2] Trust-Aware Retriever connected")
            except Exception as e:
                logger.warning(f"[LAYER2] Trust-Aware Retriever connection failed: {e}")

            logger.info("[LAYER2] All core intelligence systems initialized")
            return True

        except Exception as e:
            logger.warning(f"[LAYER2] Initialization warning: {e}")
            return True

    def _register_layer1_request_handlers(self):
        """Register request handlers for Layer 1 message bus (bidirectional)."""
        if not self._message_bus:
            return
        
        try:
            from layer1.message_bus import ComponentType
            
            # Handler for cognitive processing requests
            self._message_bus.register_request_handler(
                component=ComponentType.COGNITIVE_ENGINE,
                topic="process_intent",
                handler=self._handle_process_intent_request
            )
            
            # Handler for status requests
            self._message_bus.register_request_handler(
                component=ComponentType.COGNITIVE_ENGINE,
                topic="get_status",
                handler=self._handle_status_request
            )
            
            # Handler for observation requests
            self._message_bus.register_request_handler(
                component=ComponentType.COGNITIVE_ENGINE,
                topic="observe",
                handler=self._handle_observe_request
            )
            
            logger.info("[LAYER2] Registered 3 request handlers for Layer 1")
        except Exception as e:
            logger.warning(f"[LAYER2] Failed to register Layer 1 request handlers: {e}")

    def _subscribe_to_layer1_events(self):
        """Subscribe to Layer 1 events (bidirectional)."""
        if not self._message_bus:
            return
        
        try:
            # Subscribe to file ingestion events
            self._message_bus.subscribe(
                topic="ingestion.file_processed",
                handler=self._on_file_ingested
            )
            
            # Subscribe to memory mesh updates
            self._message_bus.subscribe(
                topic="memory_mesh.procedure_created",
                handler=self._on_procedure_created
            )
            
            self._message_bus.subscribe(
                topic="memory_mesh.episode_recorded",
                handler=self._on_episode_recorded
            )
            
            # Subscribe to RAG events
            self._message_bus.subscribe(
                topic="rag.query_received",
                handler=self._on_rag_query
            )
            
            # Subscribe to diagnostic events
            self._message_bus.subscribe(
                topic="diagnostic_engine.issue_detected",
                handler=self._on_diagnostic_issue
            )
            
            # Subscribe to librarian events
            self._message_bus.subscribe(
                topic="librarian.document_tagged",
                handler=self._on_document_tagged
            )
            
            logger.info("[LAYER2] Subscribed to 6 Layer 1 event topics")
        except Exception as e:
            logger.warning(f"[LAYER2] Failed to subscribe to Layer 1 events: {e}")

    def _register_layer1_autonomous_actions(self):
        """Register autonomous actions triggered by Layer 1 events."""
        if not self._message_bus:
            return
        
        try:
            from layer1.message_bus import ComponentType
            
            # Auto-process intents from Layer 1 inputs
            self._message_bus.register_autonomous_action(
                trigger_event="layer1.user_input_processed",
                action=self._on_layer1_user_input,
                component=ComponentType.COGNITIVE_ENGINE,
                description="Auto-process Layer 1 user inputs through OODA loop"
            )
            
            logger.info("[LAYER2] Registered 1 autonomous action for Layer 1")
        except Exception as e:
            logger.warning(f"[LAYER2] Failed to register Layer 1 autonomous actions: {e}")

    # ================================================================
    # LAYER 1 REQUEST HANDLERS (Bidirectional - Layer 1 → Layer 2)
    # ================================================================

    async def _handle_process_intent_request(self, message: "Message") -> Dict[str, Any]:
        """Handle request to process intent through Layer 2."""
        intent = message.payload.get("intent", "")
        entities = message.payload.get("entities", {})
        context = message.payload.get("context", {})
        
        # Create Genesis Key for this request
        request_genesis_key = None
        if self._message_bus:
            try:
                from layer1.message_bus import ComponentType
                response = await self._message_bus.request(
                    to_component=ComponentType.GENESIS_KEYS,
                    topic="create_cognitive_key",
                    payload={
                        "key_type": "api_request",
                        "what": f"Layer 2 process_intent request: {intent}",
                        "who": message.payload.get("user_id", "system"),
                        "why": f"Process intent through Layer 2 OODA loop",
                        "how": "Layer 1 → Layer 2 request",
                        "context": {
                            "source": "layer1_request",
                            "intent": intent,
                            "entities": entities
                        }
                    },
                    from_component=ComponentType.COGNITIVE_ENGINE
                )
                if response and response.get("genesis_key_id"):
                    request_genesis_key = response["genesis_key_id"]
            except Exception as e:
                logger.debug(f"[LAYER2] Request Genesis Key creation failed: {e}")
        
        try:
            result = await self.process(intent, entities, context)
            
            # Update Genesis Key with result
            if request_genesis_key and self._message_bus:
                try:
                    from layer1.message_bus import ComponentType
                    await self._message_bus.publish(
                        topic="genesis_keys.update_key",
                        payload={
                            "genesis_key_id": request_genesis_key,
                            "output_data": {
                                "success": True,
                                "decision": result.get("decision", {}),
                                "confidence": result.get("confidence", 0.5)
                            }
                        },
                        from_component=ComponentType.COGNITIVE_ENGINE
                    )
                except Exception as e:
                    logger.debug(f"[LAYER2] Failed to update request Genesis Key: {e}")
            
            return {
                "success": True,
                "result": result,
                "genesis_key_id": request_genesis_key
            }
        except Exception as e:
            logger.error(f"[LAYER2] Process intent request failed: {e}")
            
            # Track error in Genesis Key
            if request_genesis_key and self._message_bus:
                try:
                    from layer1.message_bus import ComponentType
                    await self._message_bus.publish(
                        topic="genesis_keys.update_key",
                        payload={
                            "genesis_key_id": request_genesis_key,
                            "is_error": True,
                            "error_message": str(e),
                            "error_type": type(e).__name__
                        },
                        from_component=ComponentType.COGNITIVE_ENGINE
                    )
                except Exception:
                    pass
            
            return {
                "success": False,
                "error": str(e),
                "genesis_key_id": request_genesis_key
            }

    async def _handle_status_request(self, message: "Message") -> Dict[str, Any]:
        """Handle status request from Layer 1."""
        return {
            "initialized": self._llm_orchestrator is not None,
            "metrics": self.metrics,
            "connected_systems": {
                "llm_orchestrator": self._llm_orchestrator is not None,
                "memory_mesh": self._memory_mesh is not None,
                "message_bus": self._message_bus is not None
            }
        }

    async def _handle_observe_request(self, message: "Message") -> Dict[str, Any]:
        """Handle observe request from Layer 1."""
        intent = message.payload.get("intent", "")
        entities = message.payload.get("entities", {})
        context = message.payload.get("context", {})
        
        try:
            observations = await self._observe(intent, entities, context)
            return {
                "success": True,
                "observations": observations
            }
        except Exception as e:
            logger.error(f"[LAYER2] Observe request failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # ================================================================
    # LAYER 1 EVENT HANDLERS (Bidirectional - Layer 1 → Layer 2)
    # ================================================================

    async def _on_file_ingested(self, message: Message):
        """Handle file ingestion event from Layer 1."""
        file_path = message.payload.get("file_path")
        genesis_key_id = message.payload.get("genesis_key_id")
        
        logger.info(f"[LAYER2] File ingested event: {file_path} (Genesis Key: {genesis_key_id})")
        
        # Could trigger cognitive processing of the file
        # For now, just track it

    async def _on_procedure_created(self, message: "Message"):
        """Handle procedure creation event from Layer 1."""
        procedure_id = message.payload.get("procedure_id")
        procedure_name = message.payload.get("name")
        
        logger.debug(f"[LAYER2] Procedure created: {procedure_name} (ID: {procedure_id})")
        
        # Update internal knowledge of available procedures

    async def _on_episode_recorded(self, message: Message):
        """Handle episode recording event from Layer 1."""
        episode_id = message.payload.get("episode_id")
        
        logger.debug(f"[LAYER2] Episode recorded: {episode_id}")
        
        # Could use this for context in future cognitive cycles

    async def _on_rag_query(self, message: "Message"):
        """Handle RAG query event from Layer 1."""
        query = message.payload.get("query")
        
        logger.debug(f"[LAYER2] RAG query received: {query[:50]}...")
        
        # Could enhance RAG queries with cognitive context

    async def _on_diagnostic_issue(self, message: Message):
        """Handle diagnostic issue event from Layer 1."""
        issue = message.payload.get("issue")
        severity = message.payload.get("severity")
        
        logger.info(f"[LAYER2] Diagnostic issue detected: {issue} (severity: {severity})")
        
        # Could trigger cognitive processing to address the issue
        if severity in ["high", "critical"]:
            # Auto-process critical issues
            try:
                await self.process(
                    intent=f"Fix diagnostic issue: {issue}",
                    entities={"issue": issue, "severity": severity},
                    context={"source": "diagnostic_engine"}
                )
            except Exception as e:
                logger.warning(f"[LAYER2] Auto-processing diagnostic issue failed: {e}")

    async def _on_document_tagged(self, message: "Message"):
        """Handle document tagging event from Layer 1."""
        document_id = message.payload.get("document_id")
        tags = message.payload.get("tags", [])
        
        logger.debug(f"[LAYER2] Document tagged: {document_id} with tags: {tags}")

    async def _on_layer1_user_input(self, message: "Message"):
        """Handle Layer 1 user input event (autonomous action)."""
        user_input = message.payload.get("user_input", "")
        user_id = message.payload.get("user_id", "")
        
        logger.info(f"[LAYER2] Auto-processing Layer 1 user input: {user_input[:50]}...")
        
        # Auto-process through OODA loop
        try:
            await self.process(
                intent=user_input,
                entities={},
                context={"source": "layer1_user_input", "user_id": user_id}
            )
        except Exception as e:
            logger.warning(f"[LAYER2] Auto-processing Layer 1 input failed: {e}")

    async def process(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process through cognitive framework.

        Implements OODA loop:
        - Observe: Gather information
        - Orient: Analyze and understand
        - Decide: Choose action
        - Act: Execute and track
        """
        context = context or {}
        self.metrics["cognitive_cycles"] += 1

        # TimeSense: Estimate cognitive cycle duration
        cycle_start_time = datetime.utcnow()
        
        # Store cycle start time for duration calculation
        context["cycle_start_time"] = cycle_start_time
        if self._timesense:
            try:
                duration_estimate = self._timesense.estimate_duration(
                    operation=f"layer2_cognitive_cycle_{intent}",
                    context={
                        "intent": intent,
                        "entities_count": len(entities),
                        "has_file": "file" in entities
                    }
                )
                context["estimated_duration"] = duration_estimate
            except Exception as e:
                logger.debug(f"[LAYER2] TimeSense estimation failed: {e}")

        # Add to context memory
        self._context_memory.append({
            "intent": intent,
            "entities": entities,
            "timestamp": datetime.utcnow().isoformat()
        })
        if len(self._context_memory) > self._max_context:
            self._context_memory.pop(0)

        # Create Genesis Key for OBSERVE phase (via Layer 1 message bus if available)
        observe_genesis_key = None
        if self._message_bus and self._genesis_keys_connector:
            try:
                from layer1.message_bus import ComponentType, MessageType, Message
                from datetime import datetime
                # Use Layer 1 message bus to create Genesis Key
                request_message = Message(
                    message_id=f"req-{uuid.uuid4().hex[:12]}",
                    message_type=MessageType.REQUEST,
                    from_component=ComponentType.COGNITIVE_ENGINE,  # Layer 2 acts as cognitive engine
                    to_component=ComponentType.GENESIS_KEYS,
                    topic="create_cognitive_key",
                    payload={
                        "key_type": "cognitive_cycle",
                        "what": f"OBSERVE: Gathering intelligence for {intent}",
                        "who": "Layer2Intelligence",
                        "why": f"Observing context for intent: {intent}",
                        "how": "Multi-system intelligence gathering",
                        "context": {"phase": "OBSERVE", "intent": intent, "entities": entities}
                    },
                    timestamp=datetime.utcnow(),
                    requires_response=True
                )
                response = await self._message_bus.request(
                    to_component=ComponentType.GENESIS_KEYS,
                    topic="create_cognitive_key",
                    payload=request_message.payload,
                    from_component=ComponentType.COGNITIVE_ENGINE
                )
                if response and response.get("genesis_key_id"):
                    observe_genesis_key = type('obj', (object,), {'key_id': response["genesis_key_id"]})()
                    logger.debug(f"[LAYER2] OBSERVE Genesis Key created via Layer 1: {observe_genesis_key.key_id}")
            except Exception as e:
                logger.debug(f"[LAYER2] OBSERVE Genesis Key via Layer 1 failed, falling back: {e}")
                # Fallback to direct service
                if self._genesis_service:
                    try:
                        from models.genesis_key_models import GenesisKeyType
                        observe_genesis_key = self._genesis_service.create_key(
                            key_type=GenesisKeyType.SYSTEM_EVENT,
                            what_description=f"OBSERVE: Gathering intelligence for {intent}",
                            who_actor="Layer2Intelligence",
                            why_reason=f"Observing context for intent: {intent}",
                            how_method="Multi-system intelligence gathering",
                            context_data={"phase": "OBSERVE", "intent": intent, "entities": entities},
                            session=self.session
                        )
                    except Exception as e2:
                        logger.debug(f"[LAYER2] OBSERVE Genesis Key fallback failed: {e2}")
        elif self._genesis_service:
            try:
                from models.genesis_key_models import GenesisKeyType
                observe_genesis_key = self._genesis_service.create_key(
                    key_type=GenesisKeyType.SYSTEM_EVENT,
                    what_description=f"OBSERVE: Gathering intelligence for {intent}",
                    who_actor="Layer2Intelligence",
                    why_reason=f"Observing context for intent: {intent}",
                    how_method="Multi-system intelligence gathering",
                    context_data={"phase": "OBSERVE", "intent": intent, "entities": entities},
                    session=self.session
                )
            except Exception as e:
                logger.debug(f"[LAYER2] OBSERVE Genesis Key creation failed: {e}")

        # OBSERVE: Gather relevant information from all intelligence systems
        observations = await self._observe(intent, entities, context)

        # Create Genesis Key for ORIENT phase (via Layer 1 message bus if available)
        orient_genesis_key = None
        if self._message_bus:
            try:
                from layer1.message_bus import ComponentType
                response = await self._message_bus.request(
                    to_component=ComponentType.GENESIS_KEYS,
                    topic="create_cognitive_key",
                    payload={
                        "key_type": "cognitive_cycle",
                        "what": f"ORIENT: Analyzing situation for {intent}",
                        "who": "Layer2Intelligence",
                        "why": f"Analyzing observations for intent: {intent}",
                        "how": "LLM-powered analysis",
                        "context": {
                            "phase": "ORIENT",
                            "intent": intent,
                            "observations_count": len(observations.get("memory_patterns", [])) + len(observations.get("rag_context", []))
                        }
                    },
                    from_component=ComponentType.COGNITIVE_ENGINE
                )
                if response and response.get("genesis_key_id"):
                    orient_genesis_key = type('obj', (object,), {'key_id': response["genesis_key_id"]})()
                    logger.debug(f"[LAYER2] ORIENT Genesis Key created via Layer 1: {orient_genesis_key.key_id}")
            except Exception as e:
                logger.debug(f"[LAYER2] ORIENT Genesis Key via Layer 1 failed, falling back: {e}")
                # Fallback to direct service
                if self._genesis_service:
                    try:
                        from models.genesis_key_models import GenesisKeyType
                        orient_genesis_key = self._genesis_service.create_key(
                            key_type=GenesisKeyType.SYSTEM_EVENT,
                            what_description=f"ORIENT: Analyzing situation for {intent}",
                            who_actor="Layer2Intelligence",
                            why_reason=f"Analyzing observations for intent: {intent}",
                            how_method="LLM-powered analysis",
                            context_data={
                                "phase": "ORIENT",
                                "intent": intent,
                                "observations_count": len(observations.get("memory_patterns", [])) + len(observations.get("rag_context", []))
                            },
                            session=self.session
                        )
                    except Exception as e2:
                        logger.debug(f"[LAYER2] ORIENT Genesis Key fallback failed: {e2}")
        elif self._genesis_service:
            try:
                from models.genesis_key_models import GenesisKeyType
                orient_genesis_key = self._genesis_service.create_key(
                    key_type=GenesisKeyType.SYSTEM_EVENT,
                    what_description=f"ORIENT: Analyzing situation for {intent}",
                    who_actor="Layer2Intelligence",
                    why_reason=f"Analyzing observations for intent: {intent}",
                    how_method="LLM-powered analysis",
                    context_data={
                        "phase": "ORIENT",
                        "intent": intent,
                        "observations_count": len(observations.get("memory_patterns", [])) + len(observations.get("rag_context", []))
                    },
                    session=self.session
                )
            except Exception as e:
                logger.debug(f"[LAYER2] ORIENT Genesis Key creation failed: {e}")

        # ORIENT: Analyze the situation
        orientation = await self._orient(observations, context)

        # Create Genesis Key for DECIDE phase (via Layer 1 message bus if available)
        decide_genesis_key = None
        if self._message_bus:
            try:
                from layer1.message_bus import ComponentType
                response = await self._message_bus.request(
                    to_component=ComponentType.GENESIS_KEYS,
                    topic="create_cognitive_key",
                    payload={
                        "key_type": "cognitive_cycle",
                        "what": f"DECIDE: Making decision for {intent}",
                        "who": "Layer2Intelligence",
                        "why": f"Deciding action for intent: {intent}",
                        "how": "LLM-powered decision making",
                        "context": {
                            "phase": "DECIDE",
                            "intent": intent,
                            "confidence": orientation.get("confidence", 0.5),
                            "concerns_count": len(orientation.get("concerns", [])),
                            "opportunities_count": len(orientation.get("opportunities", []))
                        }
                    },
                    from_component=ComponentType.COGNITIVE_ENGINE
                )
                if response and response.get("genesis_key_id"):
                    decide_genesis_key = type('obj', (object,), {'key_id': response["genesis_key_id"]})()
                    logger.debug(f"[LAYER2] DECIDE Genesis Key created via Layer 1: {decide_genesis_key.key_id}")
            except Exception as e:
                logger.debug(f"[LAYER2] DECIDE Genesis Key via Layer 1 failed, falling back: {e}")
                # Fallback to direct service
                if self._genesis_service:
                    try:
                        from models.genesis_key_models import GenesisKeyType
                        decide_genesis_key = self._genesis_service.create_key(
                            key_type=GenesisKeyType.SYSTEM_EVENT,
                            what_description=f"DECIDE: Making decision for {intent}",
                            who_actor="Layer2Intelligence",
                            why_reason=f"Deciding action for intent: {intent}",
                            how_method="LLM-powered decision making",
                            context_data={
                                "phase": "DECIDE",
                                "intent": intent,
                                "confidence": orientation.get("confidence", 0.5),
                                "concerns_count": len(orientation.get("concerns", [])),
                                "opportunities_count": len(orientation.get("opportunities", []))
                            },
                            session=self.session
                        )
                    except Exception as e2:
                        logger.debug(f"[LAYER2] DECIDE Genesis Key fallback failed: {e2}")
        elif self._genesis_service:
            try:
                from models.genesis_key_models import GenesisKeyType
                decide_genesis_key = self._genesis_service.create_key(
                    key_type=GenesisKeyType.SYSTEM_EVENT,
                    what_description=f"DECIDE: Making decision for {intent}",
                    who_actor="Layer2Intelligence",
                    why_reason=f"Deciding action for intent: {intent}",
                    how_method="LLM-powered decision making",
                    context_data={
                        "phase": "DECIDE",
                        "intent": intent,
                        "confidence": orientation.get("confidence", 0.5),
                        "concerns_count": len(orientation.get("concerns", [])),
                        "opportunities_count": len(orientation.get("opportunities", []))
                    },
                    session=self.session
                )
            except Exception as e:
                logger.debug(f"[LAYER2] DECIDE Genesis Key creation failed: {e}")

        # DECIDE: Choose best action
        decision = await self._decide(orientation)

        # Track decision
        self.metrics["decisions_made"] += 1

        # Create clarity context for this cognitive cycle
        clarity_context = None
        if self._clarity_framework:
            try:
                clarity_context = self._clarity_framework.create_context(
                    what=f"Cognitive processing: {intent}",
                    why=f"Process intent through OODA loop: {intent}",
                    who="Layer2Intelligence",
                    how="OODA Loop (Observe-Orient-Decide-Act)",
                    expected_outcome=f"Decision: {decision.get('action', 'unknown')}"
                )
            except Exception as e:
                logger.warning(f"[LAYER2] Clarity context creation failed: {e}")

        # Calculate cycle duration
        cycle_duration = (datetime.utcnow() - cycle_start_time).total_seconds()
        
        # Log complete cognitive cycle with Genesis Key linking all phases (via Layer 1 message bus if available)
        # This Genesis Key tracks the complete cycle and links to all phase keys
        cycle_genesis_key = None
        if self._message_bus:
            try:
                from layer1.message_bus import ComponentType
                response = await self._message_bus.request(
                    to_component=ComponentType.GENESIS_KEYS,
                    topic="create_cognitive_key",
                    payload={
                        "key_type": "cognitive_cycle",
                        "what": f"Complete cognitive cycle: {intent}",
                        "who": "Layer2Intelligence",
                        "why": f"Complete OODA processing for intent: {intent}",
                        "how": "OODA Loop (Observe-Orient-Decide-Act)",
                        "context": {
                            "intent": intent,
                            "decision": decision,
                            "confidence": orientation.get("confidence", 0.5),
                            "cycle_duration_seconds": cycle_duration,
                            "start_key_id": cycle_start_genesis_key.key_id if cycle_start_genesis_key else None,
                            "observe_key_id": observe_genesis_key.key_id if observe_genesis_key else None,
                            "orient_key_id": orient_genesis_key.key_id if orient_genesis_key else None,
                            "decide_key_id": decide_genesis_key.key_id if decide_genesis_key else None,
                            "observations_sources": len(observations),
                            "orientation_concerns": len(orientation.get("concerns", [])),
                            "orientation_opportunities": len(orientation.get("opportunities", []))
                        }
                    },
                    from_component=ComponentType.COGNITIVE_ENGINE
                )
                if response and response.get("genesis_key_id"):
                    cycle_genesis_key = type('obj', (object,), {'key_id': response["genesis_key_id"]})()
                    logger.debug(f"[LAYER2] Cycle Genesis Key created via Layer 1: {cycle_genesis_key.key_id}")
            except Exception as e:
                logger.debug(f"[LAYER2] Cycle Genesis Key via Layer 1 failed, falling back: {e}")
                # Fallback to direct service
                if self._genesis_service:
                    try:
                        from models.genesis_key_models import GenesisKeyType
                        cycle_genesis_key = self._genesis_service.create_key(
                            key_type=GenesisKeyType.SYSTEM_EVENT,
                            what_description=f"Complete cognitive cycle: {intent}",
                            who_actor="Layer2Intelligence",
                            why_reason=f"Complete OODA processing for intent: {intent}",
                            how_method="OODA Loop (Observe-Orient-Decide-Act)",
                            context_data={
                                "intent": intent,
                                "decision": decision,
                                "confidence": orientation.get("confidence", 0.5),
                                "observe_key_id": observe_genesis_key.key_id if observe_genesis_key else None,
                                "orient_key_id": orient_genesis_key.key_id if orient_genesis_key else None,
                                "decide_key_id": decide_genesis_key.key_id if decide_genesis_key else None
                            },
                            session=self.session
                        )
                    except Exception as e2:
                        logger.warning(f"[LAYER2] Cycle Genesis Key fallback failed: {e2}")
        elif self._genesis_service:
            try:
                from models.genesis_key_models import GenesisKeyType
                cycle_genesis_key = self._genesis_service.create_key(
                    key_type=GenesisKeyType.SYSTEM_EVENT,
                    what_description=f"Complete cognitive cycle: {intent}",
                    who_actor="Layer2Intelligence",
                    why_reason=f"Complete OODA processing for intent: {intent}",
                    how_method="OODA Loop (Observe-Orient-Decide-Act)",
                    context_data={
                        "intent": intent,
                        "decision": decision,
                        "confidence": orientation.get("confidence", 0.5),
                        "observe_key_id": observe_genesis_key.key_id if observe_genesis_key else None,
                        "orient_key_id": orient_genesis_key.key_id if orient_genesis_key else None,
                        "decide_key_id": decide_genesis_key.key_id if decide_genesis_key else None
                    },
                    session=self.session
                )
            except Exception as e:
                logger.warning(f"[LAYER2] Cycle Genesis Key creation failed: {e}")

        # Use Librarian to organize and tag this cognitive cycle (if documents involved)
        if self._librarian and cycle_genesis_key:
            try:
                # Extract file entities for Librarian organization
                file_entities = [e for e in entities if e.get("type") == "file"]
                if file_entities:
                    # Create tags based on intent and decision
                    intent_tags = [word.lower() for word in intent.split() if len(word) > 3][:5]
                    decision_tags = [decision.get("action", "").lower()] if decision.get("action") else []
                    all_tags = list(set(intent_tags + decision_tags))
                    
                    # Use Librarian to tag documents involved in this cycle
                    from librarian.tag_manager import TagManager
                    tag_manager = TagManager(self.session)
                    for file_entity in file_entities[:3]:  # Limit to 3 files
                        try:
                            # Find document by file path
                            from models.database_models import Document
                            file_path = file_entity.get("value", "")
                            if file_path:
                                doc = self.session.query(Document).filter(
                                    Document.file_path.like(f"%{file_path}%")
                                ).first()
                                if doc:
                                    # Assign tags with Genesis Key reference
                                    tag_manager.assign_tags(
                                        document_id=doc.id,
                                        tag_names=all_tags,
                                        assigned_by="layer2_intelligence",
                                        confidence=orientation.get("confidence", 0.5),
                                        metadata={
                                            "genesis_key_id": cycle_genesis_key.key_id,
                                            "intent": intent,
                                            "decision_action": decision.get("action", "")
                                        }
                                    )
                                    logger.debug(f"[LAYER2] Tagged document {doc.id} with tags: {all_tags}")
                        except Exception as e:
                            logger.debug(f"[LAYER2] Librarian tagging failed for file {file_entity.get('value')}: {e}")
            except Exception as e:
                logger.debug(f"[LAYER2] Librarian organization failed: {e}")

        result = {
            "intent": intent,
            "observations": observations,
            "orientation": orientation,
            "decision": decision,
            "confidence": orientation.get("confidence", 0.5),
            "genesis_keys": {
                "cycle_start": cycle_start_genesis_key.key_id if cycle_start_genesis_key else None,
                "observe": observe_genesis_key.key_id if observe_genesis_key else None,
                "orient": orient_genesis_key.key_id if orient_genesis_key else None,
                "decide": decide_genesis_key.key_id if decide_genesis_key else None,
                "complete_cycle": cycle_genesis_key.key_id if cycle_genesis_key else None
            },
            "cycle_duration_seconds": cycle_duration
        }
        
        # Publish cognitive cycle completion event to Layer 1 (bidirectional)
        if self._message_bus:
            try:
                from layer1.message_bus import ComponentType
                await self._message_bus.publish(
                    topic="layer2.cognitive_cycle_completed",
                    payload={
                        "intent": intent,
                        "decision": decision,
                        "confidence": orientation.get("confidence", 0.5),
                        "observations_count": len(observations),
                        "cycle_duration_seconds": cycle_duration,
                        "cycle_genesis_key_id": cycle_genesis_key.key_id if cycle_genesis_key else None,
                        "all_genesis_keys": result.get("genesis_keys", {})
                    },
                    from_component=ComponentType.COGNITIVE_ENGINE,
                    priority=5
                )
                logger.debug("[LAYER2] Published cognitive cycle completion event to Layer 1")
            except Exception as e:
                logger.debug(f"[LAYER2] Failed to publish cognitive cycle event: {e}")

        # Update clarity context with actual outcome
        if clarity_context and self._clarity_framework:
            try:
                actual_outcome = f"Decision: {decision.get('action')}, Confidence: {orientation.get('confidence', 0.5):.2f}"
                evidence = [
                    f"Found {len(observations.get('memory_patterns', []))} memory patterns",
                    f"Retrieved {len(observations.get('rag_context', []))} document contexts",
                    f"Identified {len(orientation.get('concerns', []))} concerns",
                    f"Identified {len(orientation.get('opportunities', []))} opportunities"
                ]
                self._clarity_framework.update_context(
                    context_id=clarity_context.context_id,
                    actual_outcome=actual_outcome,
                    evidence=evidence
                )
                # Verify clarity
                verification = self._clarity_framework.verify_context(clarity_context.context_id)
                result["clarity"] = {
                    "level": verification.get("clarity_level", "unknown"),
                    "verification_status": verification.get("verification_status", "pending"),
                    "rule_results": verification.get("rule_results", [])
                }
            except Exception as e:
                logger.warning(f"[LAYER2] Clarity context update failed: {e}")

        return result

    async def _observe(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """OBSERVE: Gather relevant information from all core intelligence systems."""
        observations = {
            "intent": intent,
            "entities": entities,
            "context_history": self._context_memory[-5:],
            "insights": [],
            "memory_patterns": [],
            "rag_context": [],
            "world_model_context": []
        }

        # 1. Use multi-plane reasoning for observation
        if self._reasoner and entities.get("file"):
            try:
                reasoning = await self._reasoner.reason(
                    query=f"Observe context for: {intent}",
                    target_path=entities.get("file")
                )
                observations["insights"] = reasoning.get("insights", {})
                self.metrics["insights_generated"] += 1
            except Exception as e:
                logger.warning(f"[LAYER2] Reasoning failed: {e}")

        # 2. Retrieve from Memory Mesh (procedural/episodic memory)
        if self._memory_mesh:
            try:
                # Get relevant procedures
                if entities.get("goal") or intent:
                    goal = entities.get("goal") or intent
                    procedure = self._memory_mesh.procedural_repo.find_procedure(
                        goal=goal,
                        context=entities
                    )
                    if procedure:
                        observations["memory_patterns"].append({
                            "type": "procedure",
                            "name": procedure.name,
                            "goal": procedure.goal,
                            "trust_score": procedure.trust_score,
                            "success_rate": procedure.success_rate
                        })

                # Get relevant episodes
                if entities.get("problem") or intent:
                    problem = entities.get("problem") or intent
                    episodes = self._memory_mesh.episodic_buffer.recall_similar(
                        problem=problem,
                        k=3,
                        min_trust=0.6
                    )
                    for episode in episodes:
                        observations["memory_patterns"].append({
                            "type": "episode",
                            "problem": episode.problem[:100],
                            "outcome": episode.outcome,
                            "trust_score": episode.trust_score
                        })
            except Exception as e:
                logger.warning(f"[LAYER2] Memory Mesh retrieval failed: {e}")

        # 3. Retrieve from RAG (document context) - use Enterprise RAG if available
        if self._enterprise_rag:
            try:
                query = f"{intent} {entities.get('goal', '')} {entities.get('problem', '')}".strip()
                if query:
                    # Use Enterprise RAG smart retrieval with caching
                    rag_result = self._enterprise_rag.smart_retrieve(
                        query=query,
                        limit=5,
                        score_threshold=0.3,
                        use_cache=True
                    )
                    observations["rag_context"] = [
                        {
                            "content": result.get("content", "")[:200],
                            "score": result.get("score", 0.0),
                            "metadata": result.get("metadata", {})
                        }
                        for result in rag_result.get("results", [])
                    ]
                    observations["rag_metadata"] = {
                        "cached": rag_result.get("cached", False),
                        "cache_age_seconds": rag_result.get("cache_age_seconds", 0)
                    }
            except Exception as e:
                logger.warning(f"[LAYER2] Enterprise RAG retrieval failed: {e}")
                # Fallback to basic RAG
                if self._rag_retriever:
                    try:
                        query = f"{intent} {entities.get('goal', '')} {entities.get('problem', '')}".strip()
                        if query:
                            rag_results = self._rag_retriever.retrieve(
                                query=query,
                                limit=5,
                                score_threshold=0.3
                            )
                            observations["rag_context"] = [
                                {
                                    "content": result.get("content", "")[:200],
                                    "score": result.get("score", 0.0),
                                    "metadata": result.get("metadata", {})
                                }
                                for result in rag_results
                            ]
                    except Exception as e2:
                        logger.warning(f"[LAYER2] Basic RAG retrieval failed: {e2}")
        elif self._rag_retriever:
            try:
                query = f"{intent} {entities.get('goal', '')} {entities.get('problem', '')}".strip()
                if query:
                    rag_results = self._rag_retriever.retrieve(
                        query=query,
                        limit=5,
                        score_threshold=0.3
                    )
                    observations["rag_context"] = [
                        {
                            "content": result.get("content", "")[:200],
                            "score": result.get("score", 0.0),
                            "metadata": result.get("metadata", {})
                        }
                        for result in rag_results
                    ]
            except Exception as e:
                logger.warning(f"[LAYER2] RAG retrieval failed: {e}")

        # 4. Get context from World Model
        if self._world_model:
            try:
                # Load world model and get recent contexts
                world_model_data = self._world_model.load_world_model()
                if world_model_data and "contexts" in world_model_data:
                    contexts = world_model_data["contexts"]
                    # Get most recent contexts (up to 5)
                    recent_contexts = sorted(
                        contexts,
                        key=lambda x: x.get("integrated_at", ""),
                        reverse=True
                    )[:5]
                    
                    observations["world_model_context"] = [
                        {
                            "genesis_key_id": ctx.get("genesis_key_id", ""),
                            "what": ctx.get("context", {}).get("what", "")[:200],
                            "who": ctx.get("context", {}).get("who", ""),
                            "when": ctx.get("context", {}).get("when", ""),
                            "integrated_at": ctx.get("integrated_at", "")
                        }
                        for ctx in recent_contexts
                    ]
            except Exception as e:
                logger.warning(f"[LAYER2] World Model retrieval failed: {e}")

        # 5. Get system health from Diagnostic Engine
        if self._diagnostic_engine:
            try:
                health_analysis = self._diagnostic_engine.analyze_system_health()
                observations["system_health"] = {
                    "status": health_analysis.get("status", "unknown"),
                    "issues": health_analysis.get("issues", [])[:5],
                    "recommendations": health_analysis.get("recommendations", [])[:3]
                }
            except Exception as e:
                logger.warning(f"[LAYER2] Diagnostic Engine analysis failed: {e}")

        # 6. Get code analysis if file entities present
        if self._code_analyzer and entities.get("file"):
            try:
                file_path = self.repo_path / entities["file"] if self.repo_path else Path(entities["file"])
                if file_path.exists():
                    code_analysis = self._code_analyzer.analyze_file(str(file_path))
                    observations["code_analysis"] = {
                        "complexity": code_analysis.get("complexity", {}),
                        "quality_score": code_analysis.get("quality_score", 0.0),
                        "issues": code_analysis.get("issues", [])[:5]
                    }
            except Exception as e:
                logger.warning(f"[LAYER2] Code analysis failed: {e}")

        # 7. Get document organization from Librarian (enhanced)
        if self._librarian:
            try:
                librarian_stats = self._librarian.get_librarian_analytics()
                observations["librarian_context"] = {
                    "total_documents": librarian_stats.get("priorities", {}).get("total_documents", 0),
                    "top_tags": librarian_stats.get("top_tags", [])[:5],
                    "health_status": librarian_stats.get("health", {}).get("health_status", "unknown")
                }
                
                # Get relevant documents based on intent using Librarian's tag search
                if intent:
                    try:
                        # Extract potential tags from intent
                        intent_words = intent.lower().split()
                        # Search for documents with relevant tags
                        from librarian.tag_manager import TagManager
                        tag_manager = TagManager(self.session)
                        relevant_docs = tag_manager.search_documents_by_tags(
                            tag_names=intent_words[:3],  # Use top 3 words as potential tags
                            match_all=False,
                            limit=5
                        )
                        if relevant_docs:
                            observations["librarian_relevant_docs"] = [
                                {
                                    "document_id": doc.get("id"),
                                    "title": doc.get("title", "")[:100],
                                    "tags": doc.get("tags", [])[:3]
                                }
                                for doc in relevant_docs[:3]
                            ]
                    except Exception as e:
                        logger.debug(f"[LAYER2] Librarian tag search failed: {e}")
            except Exception as e:
                logger.warning(f"[LAYER2] Librarian retrieval failed: {e}")

        # 8. Get self-modeling insights from Mirror System
        if self._mirror_system:
            try:
                self_model = self._mirror_system.build_self_model()
                observations["mirror_insights"] = {
                    "patterns": self_model.get("patterns", [])[:3],
                    "capabilities": self_model.get("capabilities", [])[:3],
                    "limitations": self_model.get("limitations", [])[:3]
                }
            except Exception as e:
                logger.warning(f"[LAYER2] Mirror System analysis failed: {e}")

        # 9. Get clarity metrics from Clarity Framework
        if self._clarity_framework:
            try:
                clarity_metrics = self._clarity_framework.get_metrics()
                clarity_report = self._clarity_framework.generate_clarity_report()
                observations["clarity_context"] = {
                    "average_clarity": clarity_metrics.get("average_clarity", 0.0),
                    "active_contexts": clarity_metrics.get("active_contexts", 0),
                    "completed_contexts": clarity_metrics.get("completed_contexts", 0),
                    "clarity_distribution": clarity_report.get("clarity_distribution", {}),
                    "recommendations": clarity_report.get("recommendations", [])
                }
            except Exception as e:
                logger.warning(f"[LAYER2] Clarity Framework retrieval failed: {e}")

        # 10. Get failure patterns from Failure Learning System
        if self._failure_learning:
            try:
                # Get recent failures and learning status
                recent_failures = self._failure_learning.get_recent_failures(limit=3)
                learning_status = self._failure_learning.get_learning_status()
                observations["failure_patterns"] = [
                    {
                        "failure_type": failure.get("failure_type", "unknown"),
                        "error_message": failure.get("error_message", "")[:200],
                        "resolution_status": failure.get("resolution_status", "unknown")
                    }
                    for failure in recent_failures
                ]
                observations["failure_learning"] = {
                    "failures_recorded": learning_status.get("failures_recorded", 0),
                    "failures_resolved": learning_status.get("failures_resolved", 0),
                    "patterns_learned": learning_status.get("patterns_learned", 0)
                }
            except Exception as e:
                logger.warning(f"[LAYER2] Failure Learning retrieval failed: {e}")

        # 11. Get mutation tracking context
        if self._mutation_tracker:
            try:
                mutation_metrics = self._mutation_tracker.get_metrics()
                recent_mutations = self._mutation_tracker.get_recent_mutations(limit=5)
                observations["mutation_context"] = {
                    "total_mutations": mutation_metrics.get("mutations_tracked", 0),
                    "mutations_reverted": mutation_metrics.get("mutations_reverted", 0),
                    "files_tracked": mutation_metrics.get("files_tracked", 0),
                    "recent_mutations_count": len(recent_mutations)
                }
            except Exception as e:
                logger.warning(f"[LAYER2] Mutation Tracker retrieval failed: {e}")

        # 12. Get neuro-symbolic reasoning (if available)
        if self._neuro_symbolic_reasoner:
            try:
                # Perform neuro-symbolic reasoning on the intent
                reasoning_result = self._neuro_symbolic_reasoner.reason(
                    query=intent,
                    context={"entities": entities},
                    limit=5,
                    include_trace=True
                )
                observations["neuro_symbolic_reasoning"] = {
                    "neural_results_count": len(reasoning_result.neural_results),
                    "symbolic_results_count": len(reasoning_result.symbolic_results),
                    "fused_results_count": len(reasoning_result.fused_results),
                    "neural_confidence": reasoning_result.neural_confidence,
                    "symbolic_confidence": reasoning_result.symbolic_confidence,
                    "fusion_confidence": reasoning_result.fusion_confidence,
                    "top_fused_results": [
                        {
                            "content": result.get("content", "")[:200],
                            "score": result.get("score", 0.0)
                        }
                        for result in reasoning_result.fused_results[:3]
                    ]
                }
                # Track reasoning if Enterprise wrapper available
                if self._enterprise_neuro_symbolic:
                    self._enterprise_neuro_symbolic.track_reasoning(reasoning_result)
            except Exception as e:
                logger.warning(f"[LAYER2] Neuro-Symbolic reasoning failed: {e}")

        # 13. Get Enterprise RAG analytics (if available)
        if self._enterprise_rag:
            try:
                rag_analytics = self._enterprise_rag.get_rag_analytics()
                observations["rag_analytics"] = {
                    "total_queries": rag_analytics.get("query_statistics", {}).get("total_queries", 0),
                    "cache_hit_rate": rag_analytics.get("query_statistics", {}).get("cache_hit_rate", 0.0),
                    "avg_results_per_query": rag_analytics.get("query_statistics", {}).get("avg_results_per_query", 0.0)
                }
            except Exception as e:
                logger.warning(f"[LAYER2] Enterprise RAG analytics failed: {e}")

        # 14. Get Enterprise Neuro-Symbolic analytics (if available)
        if self._enterprise_neuro_symbolic:
            try:
                neuro_symbolic_analytics = self._enterprise_neuro_symbolic.get_neuro_symbolic_analytics()
                observations["neuro_symbolic_analytics"] = {
                    "total_reasonings": neuro_symbolic_analytics.get("reasoning_statistics", {}).get("total_reasonings", 0),
                    "fused_count": neuro_symbolic_analytics.get("reasoning_statistics", {}).get("fused", 0),
                    "avg_fusion_confidence": neuro_symbolic_analytics.get("reasoning_statistics", {}).get("avg_fusion_confidence", 0.0)
                }
            except Exception as e:
                logger.warning(f"[LAYER2] Enterprise Neuro-Symbolic analytics failed: {e}")

        return observations

    async def _orient(
        self,
        observations: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ORIENT: Analyze and understand the situation using LLM intelligence."""
        orientation = {
            "understanding": "",
            "concerns": [],
            "opportunities": [],
            "confidence": 0.5
        }

        # Analyze observations
        insights = observations.get("insights", {})

        # Collect concerns from all planes
        for plane, plane_insights in insights.items():
            for insight in plane_insights:
                if insight.get("type") == "concern":
                    orientation["concerns"].append(insight.get("content"))
                elif insight.get("type") == "suggestion":
                    orientation["opportunities"].append(insight.get("content"))

        # Use LLM Orchestrator for intelligent analysis (Layer 2 Intelligence)
        if self._llm_orchestrator:
            try:
                from llm_orchestrator.multi_llm_client import TaskType
                
                # Build comprehensive analysis prompt with all intelligence sources
                intent = observations.get("intent", "unknown")
                entities = observations.get("entities", {})
                
                # Include Memory Mesh patterns
                memory_patterns = observations.get("memory_patterns", [])
                memory_summary = "\n".join([
                    f"- {p.get('type', 'unknown')}: {p.get('name', p.get('problem', ''))[:100]} (trust: {p.get('trust_score', 0):.2f})"
                    for p in memory_patterns[:5]
                ]) if memory_patterns else "No relevant memory patterns found"
                
                # Include RAG context
                rag_context = observations.get("rag_context", [])
                rag_summary = "\n".join([
                    f"- {r.get('content', '')[:150]} (score: {r.get('score', 0):.2f})"
                    for r in rag_context[:3]
                ]) if rag_context else "No relevant document context found"
                
                # Include World Model context
                world_context = observations.get("world_model_context", [])
                world_summary = "\n".join([
                    f"- {w.get('what', '')[:150]} (who: {w.get('who', 'unknown')})"
                    for w in world_context[:3]
                ]) if world_context else "No relevant world model context found"
                
                # Include system health
                system_health = observations.get("system_health", {})
                health_summary = f"Status: {system_health.get('status', 'unknown')}, Issues: {len(system_health.get('issues', []))}"
                
                # Include code analysis
                code_analysis = observations.get("code_analysis", {})
                code_summary = f"Quality: {code_analysis.get('quality_score', 0):.2f}, Issues: {len(code_analysis.get('issues', []))}" if code_analysis else "No code analysis"
                
                # Include librarian context
                librarian_context = observations.get("librarian_context", {})
                librarian_summary = f"Documents: {librarian_context.get('total_documents', 0)}, Status: {librarian_context.get('health_status', 'unknown')}"
                
                # Include mirror insights
                mirror_insights = observations.get("mirror_insights", {})
                mirror_summary = f"Patterns: {len(mirror_insights.get('patterns', []))}, Capabilities: {len(mirror_insights.get('capabilities', []))}"
                
                # Include clarity context
                clarity_context = observations.get("clarity_context", {})
                clarity_summary = f"Average Clarity: {clarity_context.get('average_clarity', 0):.2f}, Active Contexts: {clarity_context.get('active_contexts', 0)}"
                
                context_summary = json.dumps({
                    "intent": intent,
                    "entities": entities,
                    "insights": insights,
                    "memory_patterns_count": len(memory_patterns),
                    "rag_context_count": len(rag_context),
                    "world_context_count": len(world_context),
                    "system_health": system_health.get("status"),
                    "code_quality": code_analysis.get("quality_score", 0) if code_analysis else None,
                    "librarian_documents": librarian_context.get("total_documents", 0),
                    "mirror_patterns": len(mirror_insights.get("patterns", [])),
                    "average_clarity": clarity_context.get("average_clarity", 0),
                    "concerns_count": len(orientation["concerns"]),
                    "opportunities_count": len(orientation["opportunities"])
                }, indent=2)
                
                analysis_prompt = f"""Analyze this cognitive situation using ALL available intelligence sources and provide orientation:

Primary Context:
{context_summary}

Memory Patterns (from Memory Mesh):
{memory_summary}

Document Context (from RAG):
{rag_summary}

World Model Context:
{world_summary}

System Health (from Diagnostic Engine):
{health_summary}

Code Analysis:
{code_summary}

Librarian Context:
{librarian_summary}

Self-Modeling Insights (from Mirror System):
{mirror_summary}

Clarity Context (from Clarity Framework):
{clarity_summary}

Provide:
1. A clear understanding summary incorporating ALL intelligence sources (memory, RAG, world model, diagnostics, code, librarian, mirror, clarity)
2. Key concerns to address (considering all sources including system health, code quality, and clarity levels)
3. Opportunities to leverage (from all sources including mirror insights and clarity recommendations)
4. Confidence assessment (0.0-1.0) based on quality and quantity of available intelligence from all systems, including clarity levels

Format as JSON with: understanding, concerns (array), opportunities (array), confidence (float)"""

                # Use LLM for intelligent orientation
                llm_result = self._llm_orchestrator.execute_task(
                    prompt=analysis_prompt,
                    task_type=TaskType.REASONING,
                    require_verification=False,  # Internal analysis
                    require_consensus=False,
                    enable_learning=True
                )
                
                if llm_result.success:
                    try:
                        # Parse LLM response
                        import json
                        llm_analysis = json.loads(llm_result.content)
                        
                        # Enhance orientation with LLM intelligence
                        if "understanding" in llm_analysis:
                            orientation["understanding"] = llm_analysis["understanding"]
                        if "concerns" in llm_analysis:
                            orientation["concerns"].extend(llm_analysis["concerns"])
                        if "opportunities" in llm_analysis:
                            orientation["opportunities"].extend(llm_analysis["opportunities"])
                        if "confidence" in llm_analysis:
                            orientation["confidence"] = float(llm_analysis["confidence"])
                    except (json.JSONDecodeError, ValueError, KeyError):
                        # Fallback to rule-based if LLM response invalid
                        logger.warning("[LAYER2] LLM analysis response invalid, using rule-based")
            except Exception as e:
                logger.warning(f"[LAYER2] LLM orientation analysis failed: {e}")

        # Fallback: Calculate confidence if not set by LLM
        if orientation["confidence"] == 0.5:
            if orientation["concerns"]:
                orientation["confidence"] = max(0.3, 0.8 - len(orientation["concerns"]) * 0.1)
            else:
                orientation["confidence"] = 0.85

        # Fallback: Generate understanding summary if not set by LLM
        if not orientation["understanding"]:
            intent = observations.get("intent", "unknown")
            orientation["understanding"] = f"Intent to {intent}. " \
                f"Found {len(orientation['concerns'])} concerns and " \
                f"{len(orientation['opportunities'])} opportunities."

        return orientation

    async def _decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        """DECIDE: Choose the best course of action using LLM intelligence."""
        decision = {
            "action": "proceed",
            "modifications": [],
            "warnings": [],
            "confidence": orientation.get("confidence", 0.5)
        }

        # Use LLM Orchestrator for intelligent decision-making (Layer 2 Intelligence)
        if self._llm_orchestrator:
            try:
                from llm_orchestrator.multi_llm_client import TaskType
                
                # Build decision prompt
                decision_prompt = f"""Based on this cognitive orientation, decide the best course of action:

Understanding: {orientation.get('understanding', '')}
Concerns: {orientation.get('concerns', [])}
Opportunities: {orientation.get('opportunities', [])}
Confidence: {orientation.get('confidence', 0.5)}

Decide:
1. Action: "proceed", "review", or "escalate"
2. Key modifications to apply (if proceeding)
3. Critical warnings to surface (if any)
4. Reasoning for the decision

Format as JSON with: action, modifications (array), warnings (array), reason (string)"""

                # Use LLM for intelligent decision
                llm_result = self._llm_orchestrator.execute_task(
                    prompt=decision_prompt,
                    task_type=TaskType.REASONING,
                    require_verification=False,  # Internal decision
                    require_consensus=False,
                    enable_learning=True
                )
                
                if llm_result.success:
                    try:
                        # Parse LLM response
                        import json
                        llm_decision = json.loads(llm_result.content)
                        
                        # Use LLM decision
                        if "action" in llm_decision:
                            decision["action"] = llm_decision["action"]
                        if "modifications" in llm_decision:
                            decision["modifications"] = llm_decision["modifications"]
                        if "warnings" in llm_decision:
                            decision["warnings"] = llm_decision["warnings"]
                        if "reason" in llm_decision:
                            decision["reason"] = llm_decision["reason"]
                    except (json.JSONDecodeError, ValueError, KeyError):
                        # Fallback to rule-based if LLM response invalid
                        logger.warning("[LAYER2] LLM decision response invalid, using rule-based")
            except Exception as e:
                logger.warning(f"[LAYER2] LLM decision-making failed: {e}")

        # Fallback: Rule-based decision if LLM not available or failed
        if decision["action"] == "proceed" and not decision.get("modifications"):
            # If many concerns, suggest review
            if len(orientation.get("concerns", [])) > 3:
                decision["action"] = "review"
                decision["warnings"] = orientation["concerns"][:3]

            # If low confidence, suggest escalation
            elif orientation.get("confidence", 1.0) < 0.5:
                decision["action"] = "escalate"
                decision["reason"] = "Low confidence in understanding"

            # Otherwise proceed with opportunities
            else:
                decision["action"] = "proceed"
                if orientation.get("opportunities"):
                    decision["modifications"] = orientation["opportunities"][:2]

        return decision

    def get_metrics(self) -> Dict[str, Any]:
        """Get Layer 2 metrics."""
        return self.metrics
