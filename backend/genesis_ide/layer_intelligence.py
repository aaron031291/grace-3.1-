"""
Layer 1/2 Intelligence for Genesis IDE
=======================================

Layer 1: Universal Input/Output
- Receives all input (text, voice, file changes, events)
- Routes to appropriate processors
- Formats output for IDE display

Layer 2: Cognitive Processing
- Intent understanding
- Context-aware reasoning
- Decision making with OODA loop
- Multi-plane analysis
"""

import logging
import asyncio
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
        """Initialize Layer 2 systems."""
        try:
            # Multi-plane reasoner
            from grace_os.reasoning_planes import MultiPlaneReasoner
            self._reasoner = MultiPlaneReasoner(self.session, self.repo_path)
            await self._reasoner.initialize()

            # LLM orchestrator
            from llm_orchestrator.llm_orchestrator import LLMOrchestrator
            self._llm_orchestrator = LLMOrchestrator(session=self.session)

            # Genesis service
            from genesis.genesis_key_service import GenesisKeyService
            self._genesis_service = GenesisKeyService(
                session=self.session,
                repo_path=str(self.repo_path)
            )

            logger.info("[LAYER2] Cognitive systems initialized")
            return True

        except Exception as e:
            logger.warning(f"[LAYER2] Initialization warning: {e}")
            return True

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

        # Add to context memory
        self._context_memory.append({
            "intent": intent,
            "entities": entities,
            "timestamp": datetime.utcnow().isoformat()
        })
        if len(self._context_memory) > self._max_context:
            self._context_memory.pop(0)

        # OBSERVE: Gather relevant information
        observations = await self._observe(intent, entities, context)

        # ORIENT: Analyze the situation
        orientation = await self._orient(observations, context)

        # DECIDE: Choose best action
        decision = await self._decide(orientation)

        # Track decision
        self.metrics["decisions_made"] += 1

        # Log cognitive cycle
        if self._genesis_service:
            from models.genesis_key_models import GenesisKeyType
            self._genesis_service.create_key(
                key_type=GenesisKeyType.COGNITIVE_CYCLE,
                what_description=f"Cognitive processing: {intent}",
                who_actor="Layer2Intelligence",
                why_reason=f"Processing intent: {intent}",
                how_method="OODA Loop",
                context_data={
                    "intent": intent,
                    "decision": decision,
                    "confidence": orientation.get("confidence", 0.5)
                },
                session=self.session
            )

        return {
            "intent": intent,
            "observations": observations,
            "orientation": orientation,
            "decision": decision,
            "confidence": orientation.get("confidence", 0.5)
        }

    async def _observe(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """OBSERVE: Gather relevant information."""
        observations = {
            "intent": intent,
            "entities": entities,
            "context_history": self._context_memory[-5:],
            "insights": []
        }

        # Use multi-plane reasoning for observation
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

        return observations

    async def _orient(
        self,
        observations: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ORIENT: Analyze and understand the situation."""
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

        # Calculate confidence
        if orientation["concerns"]:
            orientation["confidence"] = max(0.3, 0.8 - len(orientation["concerns"]) * 0.1)
        else:
            orientation["confidence"] = 0.85

        # Generate understanding summary
        intent = observations.get("intent", "unknown")
        orientation["understanding"] = f"Intent to {intent}. " \
            f"Found {len(orientation['concerns'])} concerns and " \
            f"{len(orientation['opportunities'])} opportunities."

        return orientation

    async def _decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        """DECIDE: Choose the best course of action."""
        decision = {
            "action": "proceed",
            "modifications": [],
            "warnings": [],
            "confidence": orientation.get("confidence", 0.5)
        }

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
