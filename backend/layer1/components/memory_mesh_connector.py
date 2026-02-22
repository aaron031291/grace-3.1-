"""
Memory Mesh Connector - Autonomous Learning Memory Integration

Connects the memory mesh to Layer 1 message bus for:
- Automatic Genesis Key linking
- Trust-based episodic/procedural routing
- Cross-component learning coordination

Classes:
- `MemoryMeshConnector`

Key Methods:
- `create_memory_mesh_connector()`
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from layer1.message_bus import (
    Layer1MessageBus,
    ComponentType,
    Message,
    get_message_bus
)
from cognitive.memory_mesh_integration import MemoryMeshIntegration

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound operations
_executor = ThreadPoolExecutor(max_workers=4)


class MemoryMeshConnector:
    """
    Connects Memory Mesh to Layer 1 message bus.

    Autonomous Actions:
    1. New Genesis Key → Auto-link to learning memory
    2. High-trust learning → Auto-create episodic memory
    3. Very high-trust → Auto-create procedural memory
    4. Pattern detected → Notify autonomous learning
    5. New procedure → Notify LLM orchestration for skill use
    """

    def __init__(
        self,
        memory_mesh: MemoryMeshIntegration,
        message_bus: Optional[Layer1MessageBus] = None
    ):
        self.memory_mesh = memory_mesh
        self.message_bus = message_bus or get_message_bus()

        # Register component
        self.message_bus.register_component(
            ComponentType.MEMORY_MESH,
            self.memory_mesh
        )

        logger.info("[MEMORY-MESH-CONNECTOR] Registered with message bus")

        # Set up all autonomous actions
        self._register_autonomous_actions()
        self._register_request_handlers()
        self._subscribe_to_events()

    # ================================================================
    # AUTONOMOUS ACTIONS
    # ================================================================

    def _register_autonomous_actions(self):
        """Register all autonomous actions for memory mesh."""

        # 1. Auto-link new Genesis Keys to learning
        self.message_bus.register_autonomous_action(
            trigger_event="genesis_keys.new_learning_key",
            action=self._on_new_genesis_key,
            component=ComponentType.MEMORY_MESH,
            description="Auto-link new Genesis Key to learning memory"
        )

        # 2. Auto-create episodic memory for high-trust learning
        self.message_bus.register_autonomous_action(
            trigger_event="learning_memory.high_trust_example",
            action=self._on_high_trust_learning,
            component=ComponentType.MEMORY_MESH,
            description="Auto-create episodic memory (trust >= 0.7)",
            conditions=[lambda msg: msg.payload.get("trust_score", 0) >= 0.7]
        )

        # 3. Auto-create procedural memory for very high-trust
        self.message_bus.register_autonomous_action(
            trigger_event="learning_memory.very_high_trust_example",
            action=self._on_very_high_trust_learning,
            component=ComponentType.MEMORY_MESH,
            description="Auto-create procedural memory (trust >= 0.8)",
            conditions=[lambda msg: msg.payload.get("trust_score", 0) >= 0.8]
        )

        # 4. Notify when pattern detected
        self.message_bus.register_autonomous_action(
            trigger_event="memory_mesh.pattern_detected",
            action=self._on_pattern_detected,
            component=ComponentType.MEMORY_MESH,
            description="Notify autonomous learning of new pattern"
        )

        # 5. Proactive learning gap analysis (NEW - Grace-aligned)
        self.message_bus.register_autonomous_action(
            trigger_event="system.daily_analysis",
            action=self._analyze_learning_gaps,
            component=ComponentType.MEMORY_MESH,
            description="Daily proactive learning gap analysis and suggestions"
        )

        # 6. Trust score degradation detection (NEW - self-healing)
        self.message_bus.register_autonomous_action(
            trigger_event="memory_mesh.trust_updated",
            action=self._on_trust_degradation,
            component=ComponentType.MEMORY_MESH,
            description="Detect and respond to trust score degradation",
            conditions=[lambda msg: msg.payload.get("new_trust", 1.0) < msg.payload.get("old_trust", 0.0)]
        )

        logger.info("[MEMORY-MESH-CONNECTOR] ⭐ Registered 6 autonomous actions")

    # ================================================================
    # EVENT HANDLERS (Autonomous)
    # ================================================================

    async def _on_new_genesis_key(self, message: Message):
        """Handle new Genesis Key creation - auto-link to learning."""
        genesis_key_id = message.payload.get("genesis_key_id")
        learning_type = message.payload.get("learning_type")
        user_id = message.payload.get("user_id")

        logger.info(
            f"[MEMORY-MESH-CONNECTOR] 🤖 New Genesis Key: {genesis_key_id} "
            f"(type: {learning_type})"
        )

        # Auto-link will happen when learning is ingested
        # Just log for tracking
        await self.message_bus.publish(
            topic="memory_mesh.genesis_key_linked",
            payload={
                "genesis_key_id": genesis_key_id,
                "learning_type": learning_type,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            },
            from_component=ComponentType.MEMORY_MESH
        )

    async def _on_high_trust_learning(self, message: Message):
        """Handle high-trust learning - auto-create episodic memory."""
        learning_id = message.payload.get("learning_id")
        trust_score = message.payload.get("trust_score")
        genesis_key_id = message.payload.get("genesis_key_id")

        logger.info(
            f"[MEMORY-MESH-CONNECTOR] 🤖 High-trust learning: {learning_id} "
            f"(trust: {trust_score:.2f}) → Creating episodic memory"
        )

        # Episodic memory already auto-created in memory_mesh_integration
        # Notify other components
        await self.message_bus.publish(
            topic="memory_mesh.episodic_created",
            payload={
                "learning_id": learning_id,
                "trust_score": trust_score,
                "genesis_key_id": genesis_key_id,
                "timestamp": datetime.now().isoformat()
            },
            from_component=ComponentType.MEMORY_MESH
        )

    async def _on_very_high_trust_learning(self, message: Message):
        """Handle very high-trust learning - auto-create procedural memory."""
        learning_id = message.payload.get("learning_id")
        trust_score = message.payload.get("trust_score")
        procedure_name = message.payload.get("procedure_name")
        genesis_key_id = message.payload.get("genesis_key_id")

        logger.info(
            f"[MEMORY-MESH-CONNECTOR] 🤖 Very high-trust learning: {learning_id} "
            f"(trust: {trust_score:.2f}) → Creating procedure: {procedure_name}"
        )

        # Procedure already auto-created in memory_mesh_integration
        # Notify LLM orchestration - new skill available
        await self.message_bus.publish(
            topic="memory_mesh.procedure_created",
            payload={
                "learning_id": learning_id,
                "procedure_name": procedure_name,
                "trust_score": trust_score,
                "genesis_key_id": genesis_key_id,
                "timestamp": datetime.now().isoformat()
            },
            from_component=ComponentType.MEMORY_MESH
        )

        # Notify LLM orchestration specifically
        await self.message_bus.send_command(
            to_component=ComponentType.LLM_ORCHESTRATION,
            command="register_new_skill",
            payload={
                "skill_name": procedure_name,
                "procedure_id": message.payload.get("procedure_id"),
                "trust_score": trust_score
            },
            from_component=ComponentType.MEMORY_MESH
        )

    async def _on_pattern_detected(self, message: Message):
        """Handle pattern detection - notify autonomous learning."""
        pattern_id = message.payload.get("pattern_id")
        pattern_type = message.payload.get("pattern_type")
        examples_count = message.payload.get("examples_count")

        logger.info(
            f"[MEMORY-MESH-CONNECTOR] 🤖 Pattern detected: {pattern_type} "
            f"({examples_count} examples)"
        )

        # Notify autonomous learning system
        await self.message_bus.publish(
            topic="autonomous_learning.new_pattern",
            payload={
                "pattern_id": pattern_id,
                "pattern_type": pattern_type,
                "examples_count": examples_count,
                "timestamp": datetime.now().isoformat()
            },
            from_component=ComponentType.MEMORY_MESH
        )

    async def _analyze_learning_gaps(self, message: Message):
        """
        Proactive learning gap analysis (NEW - Grace-aligned).

        Analyzes memory mesh to identify knowledge gaps and suggests
        what Grace should learn next.
        """
        logger.info("[MEMORY-MESH-CONNECTOR] 🤖 Running proactive learning gap analysis")

        try:
            from cognitive.memory_mesh_learner import get_memory_mesh_learner

            # Run analysis in thread pool (CPU-bound)
            loop = asyncio.get_event_loop()
            learner = get_memory_mesh_learner(self.memory_mesh.session)

            suggestions = await loop.run_in_executor(
                _executor,
                learner.get_learning_suggestions
            )

            # Publish suggestions for autonomous learning system
            await self.message_bus.publish(
                topic="autonomous_learning.suggestions",
                payload={
                    "suggestions": suggestions,
                    "top_priorities": suggestions.get("top_priorities", [])[:5],
                    "timestamp": datetime.now().isoformat()
                },
                from_component=ComponentType.MEMORY_MESH
            )

            logger.info(
                f"[MEMORY-MESH-CONNECTOR] ✓ Published {len(suggestions.get('top_priorities', []))} "
                f"learning suggestions"
            )

        except Exception as e:
            logger.error(f"[MEMORY-MESH-CONNECTOR] Error in learning gap analysis: {e}")

    async def _on_trust_degradation(self, message: Message):
        """
        Handle trust score degradation (NEW - self-healing).

        When trust scores drop, automatically trigger re-learning or review.
        """
        learning_id = message.payload.get("learning_id")
        old_trust = message.payload.get("old_trust", 0.0)
        new_trust = message.payload.get("new_trust", 0.0)
        degradation = old_trust - new_trust

        logger.warning(
            f"[MEMORY-MESH-CONNECTOR] ⚠️  Trust degradation detected: "
            f"learning_id={learning_id}, {old_trust:.2f} → {new_trust:.2f} "
            f"(Δ={degradation:.2f})"
        )

        # If significant degradation, trigger review
        if degradation >= 0.2:
            await self.message_bus.publish(
                topic="autonomous_learning.needs_review",
                payload={
                    "learning_id": learning_id,
                    "reason": "significant_trust_degradation",
                    "old_trust": old_trust,
                    "new_trust": new_trust,
                    "degradation": degradation,
                    "suggested_action": "re_study" if new_trust < 0.5 else "validate",
                    "timestamp": datetime.now().isoformat()
                },
                from_component=ComponentType.MEMORY_MESH
            )

    # ================================================================
    # REQUEST HANDLERS
    # ================================================================

    def _register_request_handlers(self):
        """Register request handlers for other components."""

        self.message_bus.register_request_handler(
            component=ComponentType.MEMORY_MESH,
            topic="get_memory_stats",
            handler=self._handle_get_memory_stats
        )

        self.message_bus.register_request_handler(
            component=ComponentType.MEMORY_MESH,
            topic="get_learning_by_genesis_key",
            handler=self._handle_get_learning_by_genesis_key
        )

        self.message_bus.register_request_handler(
            component=ComponentType.MEMORY_MESH,
            topic="get_procedures_for_context",
            handler=self._handle_get_procedures_for_context
        )

        logger.info("[MEMORY-MESH-CONNECTOR] 🔧 Registered 3 request handlers")

    async def _handle_get_memory_stats(self, message: Message) -> Dict[str, Any]:
        """Handle request for memory mesh statistics (ASYNC OPTIMIZED)."""
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(
            _executor,
            self.memory_mesh.get_memory_mesh_stats
        )
        return {"stats": stats}

    async def _handle_get_learning_by_genesis_key(self, message: Message) -> Dict[str, Any]:
        """Handle request for learning by Genesis Key."""
        genesis_key_id = message.payload.get("genesis_key_id")

        # Query learning examples by Genesis Key
        from models.database_models import LearningExample
        learning = self.memory_mesh.session.query(LearningExample).filter(
            LearningExample.genesis_key_id == genesis_key_id
        ).all()

        return {
            "genesis_key_id": genesis_key_id,
            "learning_examples": [
                {
                    "id": ex.id,
                    "experience_type": ex.experience_type,
                    "trust_score": ex.trust_score,
                    "created_at": ex.created_at.isoformat() if ex.created_at else None
                }
                for ex in learning
            ]
        }

    async def _handle_get_procedures_for_context(self, message: Message) -> Dict[str, Any]:
        """Handle request for procedures matching context."""
        context = message.payload.get("context")
        min_trust = message.payload.get("min_trust_score", 0.8)

        # Get procedures from memory mesh
        from models.database_models import Procedure
        procedures = self.memory_mesh.session.query(Procedure).filter(
            Procedure.success_rate >= min_trust
        ).all()

        return {
            "procedures": [
                {
                    "id": proc.id,
                    "name": proc.name,
                    "success_rate": proc.success_rate,
                    "times_used": proc.times_used
                }
                for proc in procedures[:10]  # Top 10
            ]
        }

    # ================================================================
    # SUBSCRIPTIONS
    # ================================================================

    def _subscribe_to_events(self):
        """Subscribe to events from other components."""

        # Listen for ingestion completion
        self.message_bus.subscribe(
            topic="ingestion.file_processed",
            handler=self._on_file_ingested
        )

        # Listen for feedback from RAG
        self.message_bus.subscribe(
            topic="rag.feedback",
            handler=self._on_rag_feedback
        )

        logger.info("[MEMORY-MESH-CONNECTOR] 📡 Subscribed to 2 event topics")

    async def _on_file_ingested(self, message: Message):
        """Handle file ingestion completion - extract learning."""
        file_path = message.payload.get("file_path")
        genesis_key_id = message.payload.get("genesis_key_id")

        logger.info(
            f"[MEMORY-MESH-CONNECTOR] 📄 File ingested: {file_path} "
            f"(Genesis Key: {genesis_key_id})"
        )

        # Could trigger automatic learning extraction
        # For now, just log

    async def _on_rag_feedback(self, message: Message):
        """Handle RAG feedback - update learning memory."""
        query = message.payload.get("query")
        success = message.payload.get("success")
        retrieval_quality = message.payload.get("quality_score")

        logger.info(
            f"[MEMORY-MESH-CONNECTOR] 💬 RAG feedback: success={success}, "
            f"quality={retrieval_quality:.2f}"
        )

        # Record as learning experience
        # This creates autonomous improvement loop
        if success:
            experience_type = "success"
        else:
            experience_type = "failure"

        # Could auto-record this as learning
        # For now, just log for tracking

    # ================================================================
    # PUBLIC API
    # ================================================================

    async def trigger_learning_ingestion(
        self,
        experience_type: str,
        context: Dict[str, Any],
        action_taken: Dict[str, Any],
        outcome: Dict[str, Any],
        user_id: Optional[str] = None,
        genesis_key_id: Optional[str] = None
    ) -> str:
        """
        Trigger learning ingestion with full message bus integration.

        Automatically:
        - Creates Genesis Key if needed
        - Publishes events for high/very-high trust
        - Triggers episodic/procedural creation
        - Notifies other components
        """
        # Ingest learning
        learning_id = self.memory_mesh.ingest_learning_experience(
            experience_type=experience_type,
            context=context,
            action_taken=action_taken,
            outcome=outcome,
            source=f"user_{user_id}" if user_id else "system",
            user_id=user_id,
            genesis_key_id=genesis_key_id
        )

        # Get the created learning example
        from models.database_models import LearningExample
        learning = self.memory_mesh.session.query(LearningExample).get(learning_id)

        if not learning:
            return learning_id

        # Publish learning created event
        await self.message_bus.publish(
            topic="memory_mesh.learning_created",
            payload={
                "learning_id": learning_id,
                "experience_type": experience_type,
                "trust_score": learning.trust_score,
                "genesis_key_id": learning.genesis_key_id,
                "user_id": user_id
            },
            from_component=ComponentType.MEMORY_MESH
        )

        # Trigger high-trust events if applicable
        if learning.trust_score >= 0.7:
            await self.message_bus.publish(
                topic="learning_memory.high_trust_example",
                payload={
                    "learning_id": learning_id,
                    "trust_score": learning.trust_score,
                    "genesis_key_id": learning.genesis_key_id
                },
                from_component=ComponentType.MEMORY_MESH
            )

        if learning.trust_score >= 0.8:
            await self.message_bus.publish(
                topic="learning_memory.very_high_trust_example",
                payload={
                    "learning_id": learning_id,
                    "trust_score": learning.trust_score,
                    "genesis_key_id": learning.genesis_key_id,
                    "procedure_name": context.get("action_type", "unknown_procedure")
                },
                from_component=ComponentType.MEMORY_MESH
            )

        logger.info(
            f"[MEMORY-MESH-CONNECTOR] ✓ Learning ingested: {learning_id} "
            f"(trust: {learning.trust_score:.2f})"
        )

        return learning_id


def create_memory_mesh_connector(
    memory_mesh: MemoryMeshIntegration,
    message_bus: Optional[Layer1MessageBus] = None
) -> MemoryMeshConnector:
    """Create and initialize memory mesh connector."""
    connector = MemoryMeshConnector(memory_mesh, message_bus)
    logger.info("[MEMORY-MESH-CONNECTOR] ✓ Initialized and connected to message bus")
    return connector
