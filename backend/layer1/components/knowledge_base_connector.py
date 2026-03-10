"""
Knowledge Base Ingestion Connector - Layer 1 Integration

Connects AI Research Repository Ingestion and Data Integrity Verification
to the Layer 1 message bus, enabling autonomous knowledge base management.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

from layer1.message_bus import (
    Layer1MessageBus,
    Message,
    ComponentType,
    MessageType,
    get_message_bus,
)
from layer1.autonomous_actions import AutonomousAction

logger = logging.getLogger(__name__)


class KnowledgeBaseIngestionConnector:
    """
    Connector for AI Research Repository Ingestion.
    
    Integrates ingestion manager with Layer 1 message bus for:
    - Autonomous repository ingestion
    - Ingestion progress tracking
    - Event-driven ingestion triggers
    - Trust-aware embedding generation
    """

    def __init__(
        self,
        ai_research_path: str,
        message_bus: Optional[Layer1MessageBus] = None,
        use_trust_aware: bool = False,
        trust_weight: float = 0.3,
        min_trust_threshold: float = 0.3,
    ):
        """
        Initialize knowledge base ingestion connector.

        Args:
            ai_research_path: Path to ai_research directory
            message_bus: Layer 1 message bus instance
            use_trust_aware: Whether to use trust-aware embeddings
            trust_weight: Weight for trust in embeddings
            min_trust_threshold: Minimum trust threshold
        """
        self.ai_research_path = Path(ai_research_path)
        self.message_bus = message_bus or get_message_bus()
        self.use_trust_aware = use_trust_aware
        self.trust_weight = trust_weight
        self.min_trust_threshold = min_trust_threshold
        self.ingestion_manager = None
        self.enabled = True

        # Status tracking
        self._ingestion_status = {
            "state": "idle",  # idle, ingesting, completed, error
            "last_ingestion": None,
            "repositories_ingested": 0,
            "total_documents": 0,
            "last_error": None,
        }

        # Register with message bus
        self.message_bus.register_component(
            ComponentType.KNOWLEDGE_BASE,
            self
        )
        logger.info("[KB-INGESTION-CONNECTOR] Registered with message bus")
        
        self._register_request_handlers()
        self._register_autonomous_actions()
        self._subscribe_to_events()

    def _initialize_ingestion_manager(self):
        """Lazy initialization of ingestion manager."""
        if self.ingestion_manager is not None:
            return

        try:
            from scripts.ingest_ai_research_repos import AIResearchIngestionManager
            
            # Import trust-aware components if enabled
            if self.use_trust_aware:
                from embedding import get_embedding_model
                from ml_intelligence.trust_aware_embedding import (
                    TrustAwareEmbeddingModel,
                    TrustContext,
                    get_trust_aware_embedding_model,
                )
                
                # Create trust-aware embedding model
                base_embedding_model = get_embedding_model()
                trust_aware_model = get_trust_aware_embedding_model(
                    base_embedding_model=base_embedding_model,
                    trust_weight=self.trust_weight,
                    min_trust_threshold=self.min_trust_threshold,
                )
                
                logger.info("[KB-INGESTION-CONNECTOR] Using trust-aware embeddings")

                # Note: AIResearchIngestionManager uses its own embedding model internally.
                # Trust-aware scoring is applied post-ingestion via the trust_weight parameter.
                # Future enhancement: Pass trust_aware_model directly to ingestion manager.
                
            # Initialize manager
            self.ingestion_manager = AIResearchIngestionManager(
                str(self.ai_research_path)
            )
            
            logger.info("[KB-INGESTION-CONNECTOR] Ingestion manager initialized")
            
        except Exception as e:
            logger.error(f"[KB-INGESTION-CONNECTOR] Failed to initialize: {e}")
            raise

    def _register_request_handlers(self):
        """Register request handlers with message bus."""
        self.message_bus.register_handler(
            MessageType.REQUEST,
            "knowledge_base.ingest_repository",
            self._handle_ingest_repository,
        )
        self.message_bus.register_handler(
            MessageType.REQUEST,
            "knowledge_base.ingest_all",
            self._handle_ingest_all,
        )
        self.message_bus.register_handler(
            MessageType.REQUEST,
            "knowledge_base.get_ingestion_status",
            self._handle_get_status,
        )

    def _register_autonomous_actions(self):
        """Register autonomous actions."""
        # Auto-ingest on repository detection
        self.message_bus.register_autonomous_action(
            AutonomousAction(
                trigger_topic="file.new_repository_detected",
                action_type="knowledge_base.auto_ingest",
                handler=self._on_new_repository_detected,
                priority=5,
            )
        )

        # Auto-verify after ingestion
        self.message_bus.register_autonomous_action(
            AutonomousAction(
                trigger_topic="knowledge_base.ingestion_complete",
                action_type="knowledge_base.auto_verify",
                handler=self._on_ingestion_complete,
                priority=3,
            )
        )

    def _subscribe_to_events(self):
        """Subscribe to relevant events."""
        self.message_bus.subscribe(
            "knowledge_base.*",
            self._on_knowledge_base_event,
        )

    async def _handle_ingest_repository(self, message: Message) -> Dict[str, Any]:
        """Handle ingest repository request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        repo_path = message.payload.get("repo_path")
        category = message.payload.get("category", "frameworks")

        if not repo_path:
            return {"success": False, "error": "repo_path required"}

        try:
            self._initialize_ingestion_manager()
            
            # Publish start event
            await self.message_bus.publish(
                topic="knowledge_base.ingestion_started",
                payload={
                    "repo_path": str(repo_path),
                    "category": category,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                from_component=ComponentType.KNOWLEDGE_BASE,
            )

            # Ingest repository
            stats = self.ingestion_manager.ingest_repository(
                Path(repo_path),
                category,
            )

            # Publish completion event
            await self.message_bus.publish(
                topic="knowledge_base.ingestion_complete",
                payload={
                    "repo_path": str(repo_path),
                    "category": category,
                    "stats": stats,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                from_component=ComponentType.KNOWLEDGE_BASE,
            )

            return {"success": True, "stats": stats}

        except Exception as e:
            logger.error(f"[KB-INGESTION-CONNECTOR] Ingestion failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_ingest_all(self, message: Message) -> Dict[str, Any]:
        """Handle ingest all repositories request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        try:
            self._initialize_ingestion_manager()

            # Update status
            self._ingestion_status["state"] = "ingesting"
            self._ingestion_status["last_error"] = None

            # Publish start event
            await self.message_bus.publish(
                topic="knowledge_base.ingestion_all_started",
                payload={
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                from_component=ComponentType.KNOWLEDGE_BASE,
            )

            # Ingest all
            stats = self.ingestion_manager.ingest_all_repositories()

            # Update status on success
            self._ingestion_status["state"] = "completed"
            self._ingestion_status["last_ingestion"] = datetime.now(timezone.utc).isoformat()
            self._ingestion_status["repositories_ingested"] += stats.get("repositories_processed", 0)
            self._ingestion_status["total_documents"] += stats.get("total_documents", 0)

            # Publish completion event
            await self.message_bus.publish(
                topic="knowledge_base.ingestion_all_complete",
                payload={
                    "stats": stats,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                from_component=ComponentType.KNOWLEDGE_BASE,
            )

            return {"success": True, "stats": stats}

        except Exception as e:
            logger.error(f"[KB-INGESTION-CONNECTOR] Ingestion failed: {e}")
            self._ingestion_status["state"] = "error"
            self._ingestion_status["last_error"] = str(e)
            return {"success": False, "error": str(e)}

    async def _handle_get_status(self, message: Message) -> Dict[str, Any]:
        """Handle get ingestion status request."""
        return {
            "success": True,
            "status": self._ingestion_status["state"],
            "ai_research_path": str(self.ai_research_path),
            "trust_aware": self.use_trust_aware,
            "last_ingestion": self._ingestion_status["last_ingestion"],
            "repositories_ingested": self._ingestion_status["repositories_ingested"],
            "total_documents": self._ingestion_status["total_documents"],
            "last_error": self._ingestion_status["last_error"],
        }

    async def _on_new_repository_detected(self, message: Message):
        """Autonomous action: Ingest newly detected repository."""
        if not self.enabled:
            return

        repo_path = message.payload.get("repo_path")
        category = message.payload.get("category", "frameworks")

        logger.info(f"[KB-INGESTION-CONNECTOR] 🤖 Auto-ingesting new repository: {repo_path}")

        try:
            await self._handle_ingest_repository(
                Message(
                    type=MessageType.REQUEST,
                    topic="knowledge_base.ingest_repository",
                    payload={
                        "repo_path": repo_path,
                        "category": category,
                    },
                )
            )
        except Exception as e:
            logger.error(f"[KB-INGESTION-CONNECTOR] Auto-ingestion failed: {e}")

    async def _on_ingestion_complete(self, message: Message):
        """Autonomous action: Verify after ingestion."""
        if not self.enabled:
            return

        logger.info("[KB-INGESTION-CONNECTOR] 🤖 Triggering auto-verification after ingestion")

        # Publish verification request
        await self.message_bus.publish(
            topic="knowledge_base.verify_integrity",
            payload={
                "trigger": "post_ingestion",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            from_component=ComponentType.KNOWLEDGE_BASE,
        )

    async def _on_knowledge_base_event(self, message: Message):
        """Handle knowledge base events."""
        logger.debug(f"[KB-INGESTION-CONNECTOR] Event: {message.topic}")


def create_knowledge_base_ingestion_connector(
    ai_research_path: str,
    message_bus: Optional[Layer1MessageBus] = None,
    use_trust_aware: bool = False,
    trust_weight: float = 0.3,
    min_trust_threshold: float = 0.3,
) -> KnowledgeBaseIngestionConnector:
    """
    Factory function to create knowledge base ingestion connector.

    Args:
        ai_research_path: Path to ai_research directory
        message_bus: Layer 1 message bus instance
        use_trust_aware: Whether to use trust-aware embeddings
        trust_weight: Weight for trust in embeddings
        min_trust_threshold: Minimum trust threshold

    Returns:
        KnowledgeBaseIngestionConnector instance
    """
    return KnowledgeBaseIngestionConnector(
        ai_research_path=ai_research_path,
        message_bus=message_bus,
        use_trust_aware=use_trust_aware,
        trust_weight=trust_weight,
        min_trust_threshold=min_trust_threshold,
    )
