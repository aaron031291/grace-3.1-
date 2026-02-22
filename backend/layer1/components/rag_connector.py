"""
RAG Connector - Retrieval-Augmented Generation Integration

Connects RAG system to Layer 1 message bus for:
- Context-aware retrieval with procedural memory
- Feedback loops to memory mesh
- LLM orchestration for answer generation
"""

from typing import Dict, Any, Optional, List
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
from retrieval.retriever import DocumentRetriever

# Optional trust-aware retriever support
try:
    from retrieval.trust_aware_retriever import TrustAwareDocumentRetriever
    TRUST_AWARE_AVAILABLE = True
except ImportError:
    TrustAwareDocumentRetriever = None
    TRUST_AWARE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound operations (SCALABILITY)
_executor = ThreadPoolExecutor(max_workers=4)


class RAGConnector:
    """
    Connects RAG to Layer 1 message bus.

    Autonomous Actions:
    1. Query received → Auto-retrieve from memory mesh procedures
    2. Retrieval success → Send feedback to memory mesh
    3. Retrieval failure → Request learning from failure
    4. New procedure created → Auto-index for future retrieval
    """

    def __init__(
        self,
        retriever: DocumentRetriever,
        message_bus: Optional[Layer1MessageBus] = None,
        use_trust_aware: bool = False,
        trust_weight: float = 0.3,
        min_trust_threshold: float = 0.3,
    ):
        """
        Initialize RAG connector.
        
        Args:
            retriever: DocumentRetriever or TrustAwareDocumentRetriever instance
            message_bus: Message bus instance
            use_trust_aware: Enable trust-aware retrieval (wraps retriever if True)
            trust_weight: Weight of trust in similarity (0-1) if use_trust_aware=True
            min_trust_threshold: Minimum trust to include (0-1) if use_trust_aware=True
        """
        # Wrap with trust-aware retriever if requested and available
        if use_trust_aware and TRUST_AWARE_AVAILABLE:
            if not isinstance(retriever, TrustAwareDocumentRetriever):
                from retrieval.trust_aware_retriever import get_trust_aware_retriever
                retriever = get_trust_aware_retriever(
                    base_retriever=retriever,
                    trust_weight=trust_weight,
                    min_trust_threshold=min_trust_threshold,
                )
                logger.info("[RAG-CONNECTOR] Enabled trust-aware retrieval")
        
        self.retriever = retriever
        self.use_trust_aware = use_trust_aware and TRUST_AWARE_AVAILABLE
        self.message_bus = message_bus or get_message_bus()

        # Register component
        self.message_bus.register_component(
            ComponentType.RAG,
            self.retriever
        )

        logger.info("[RAG-CONNECTOR] Registered with message bus")

        # Set up autonomous actions
        self._register_autonomous_actions()
        self._register_request_handlers()
        self._subscribe_to_events()

    # ================================================================
    # AUTONOMOUS ACTIONS
    # ================================================================

    def _register_autonomous_actions(self):
        """Register all autonomous actions for RAG."""

        # 1. Auto-enhance retrieval with procedural memory
        self.message_bus.register_autonomous_action(
            trigger_event="rag.query_received",
            action=self._on_query_received,
            component=ComponentType.RAG,
            description="Auto-enhance retrieval with procedural memory"
        )

        # 2. Auto-send feedback on retrieval success
        self.message_bus.register_autonomous_action(
            trigger_event="rag.retrieval_success",
            action=self._on_retrieval_success,
            component=ComponentType.RAG,
            description="Send success feedback to memory mesh"
        )

        # 3. Auto-learn from retrieval failures
        self.message_bus.register_autonomous_action(
            trigger_event="rag.retrieval_failure",
            action=self._on_retrieval_failure,
            component=ComponentType.RAG,
            description="Learn from retrieval failures"
        )

        # 4. Auto-index new procedures
        self.message_bus.register_autonomous_action(
            trigger_event="memory_mesh.procedure_created",
            action=self._on_procedure_created,
            component=ComponentType.RAG,
            description="Auto-index new procedures for retrieval"
        )

        logger.info("[RAG-CONNECTOR] ⭐ Registered 4 autonomous actions")

    # ================================================================
    # EVENT HANDLERS (Autonomous)
    # ================================================================

    async def _on_query_received(self, message: Message):
        """Handle query - auto-enhance with procedural memory."""
        query = message.payload.get("query")
        context = message.payload.get("context", {})

        logger.info(f"[RAG-CONNECTOR] 🤖 Query received: {query[:50]}...")

        # Request relevant procedures from memory mesh
        try:
            response = await self.message_bus.request(
                to_component=ComponentType.MEMORY_MESH,
                topic="get_procedures_for_context",
                payload={
                    "context": context,
                    "min_trust_score": 0.8
                },
                from_component=ComponentType.RAG,
                timeout=5.0
            )

            procedures = response.get("procedures", [])

            if procedures:
                logger.info(
                    f"[RAG-CONNECTOR] ✓ Found {len(procedures)} relevant procedures"
                )

                # Enhance retrieval context with procedures
                await self.message_bus.publish(
                    topic="rag.context_enhanced",
                    payload={
                        "query": query,
                        "procedures_count": len(procedures),
                        "procedures": procedures
                    },
                    from_component=ComponentType.RAG
                )

        except Exception as e:
            logger.error(f"[RAG-CONNECTOR] Failed to get procedures: {e}")

    async def _on_retrieval_success(self, message: Message):
        """Handle retrieval success - send feedback to memory mesh."""
        query = message.payload.get("query")
        results_count = message.payload.get("results_count")
        quality_score = message.payload.get("quality_score", 0.8)

        logger.info(
            f"[RAG-CONNECTOR] 🤖 Retrieval success: {results_count} results "
            f"(quality: {quality_score:.2f})"
        )

        # Send feedback to memory mesh
        await self.message_bus.publish(
            topic="rag.feedback",
            payload={
                "query": query,
                "success": True,
                "quality_score": quality_score,
                "results_count": results_count,
                "timestamp": datetime.now().isoformat()
            },
            from_component=ComponentType.RAG
        )

    async def _on_retrieval_failure(self, message: Message):
        """Handle retrieval failure - learn from it."""
        query = message.payload.get("query")
        reason = message.payload.get("reason", "unknown")

        logger.info(
            f"[RAG-CONNECTOR] 🤖 Retrieval failure: {query[:50]}... "
            f"(reason: {reason})"
        )

        # Send failure feedback to memory mesh
        await self.message_bus.publish(
            topic="rag.feedback",
            payload={
                "query": query,
                "success": False,
                "quality_score": 0.0,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            },
            from_component=ComponentType.RAG
        )

        # Request learning from failure
        await self.message_bus.publish(
            topic="autonomous_learning.retrieval_failure",
            payload={
                "query": query,
                "reason": reason,
                "suggested_action": "improve_indexing"
            },
            from_component=ComponentType.RAG
        )

    async def _on_procedure_created(self, message: Message):
        """Handle new procedure - auto-index for retrieval."""
        procedure_name = message.payload.get("procedure_name")
        procedure_id = message.payload.get("procedure_id")
        trust_score = message.payload.get("trust_score")

        logger.info(
            f"[RAG-CONNECTOR] 🤖 New procedure created: {procedure_name} "
            f"(trust: {trust_score:.2f})"
        )

        # Auto-index procedure (would need actual indexing logic)
        # For now, just log

        await self.message_bus.publish(
            topic="rag.procedure_indexed",
            payload={
                "procedure_id": procedure_id,
                "procedure_name": procedure_name,
                "trust_score": trust_score,
                "timestamp": datetime.now().isoformat()
            },
            from_component=ComponentType.RAG
        )

    # ================================================================
    # REQUEST HANDLERS
    # ================================================================

    def _register_request_handlers(self):
        """Register request handlers for other components."""

        self.message_bus.register_request_handler(
            component=ComponentType.RAG,
            topic="retrieve",
            handler=self._handle_retrieve
        )

        self.message_bus.register_request_handler(
            component=ComponentType.RAG,
            topic="retrieve_with_context",
            handler=self._handle_retrieve_with_context
        )

        logger.info("[RAG-CONNECTOR] 🔧 Registered 2 request handlers")

    async def _handle_retrieve(self, message: Message) -> Dict[str, Any]:
        """Handle retrieval request."""
        query = message.payload.get("query")
        top_k = message.payload.get("top_k", 5)
        use_trust_weighting = message.payload.get("use_trust_weighting", self.use_trust_aware)

        # Perform retrieval asynchronously (SCALABILITY) with trust-aware support
        loop = asyncio.get_event_loop()
        if self.use_trust_aware and use_trust_weighting:
            # Use trust-aware retrieval
            results = await loop.run_in_executor(
                _executor,
                lambda: self.retriever.retrieve(
                    query=query,
                    limit=top_k,
                    use_trust_weighting=True
                )
            )
        else:
            # Use standard retrieval
            results = await loop.run_in_executor(
                _executor,
                lambda: self.retriever.retrieve(query=query, limit=top_k)
            )

        # Send success/failure event
        if results:
            await self.message_bus.publish(
                topic="rag.retrieval_success",
                payload={
                    "query": query,
                    "results_count": len(results),
                    "quality_score": 0.8  # Simplified
                },
                from_component=ComponentType.RAG
            )
        else:
            await self.message_bus.publish(
                topic="rag.retrieval_failure",
                payload={
                    "query": query,
                    "reason": "no_results"
                },
                from_component=ComponentType.RAG
            )

        # Build results with trust information if available
        formatted_results = []
        for r in results:
            result_item = {
                "id": r.get("chunk_id"),
                "content": r.get("text", ""),
                "score": r.get("score", 0.0)
            }
            
            # Add trust information if available
            if self.use_trust_aware:
                result_item["trust_score"] = r.get("trust_score", r.get("confidence_score", 0.5))
                result_item["trust_weighted_score"] = r.get("trust_weighted_score", r.get("score", 0.0))
            
            formatted_results.append(result_item)
        
        return {
            "results": formatted_results,
            "trust_aware": self.use_trust_aware and use_trust_weighting
        }

    async def _handle_retrieve_with_context(self, message: Message) -> Dict[str, Any]:
        """Handle retrieval with procedural context."""
        query = message.payload.get("query")
        top_k = message.payload.get("top_k", 5)
        use_trust_weighting = message.payload.get("use_trust_weighting", self.use_trust_aware)

        # Trigger query received event (will auto-enhance with procedures)
        await self.message_bus.publish(
            topic="rag.query_received",
            payload={
                "query": query,
                "context": {}
            },
            from_component=ComponentType.RAG
        )

        # Perform retrieval asynchronously (SCALABILITY) with trust-aware support
        loop = asyncio.get_event_loop()
        if self.use_trust_aware and use_trust_weighting:
            results = await loop.run_in_executor(
                _executor,
                lambda: self.retriever.retrieve(
                    query=query,
                    limit=top_k,
                    use_trust_weighting=True
                )
            )
        else:
            results = await loop.run_in_executor(
                _executor,
                lambda: self.retriever.retrieve(query=query, limit=top_k)
            )

        # Build results with trust information if available
        formatted_results = []
        for r in results:
            result_item = {
                "id": r.get("chunk_id"),
                "content": r.get("text", ""),
                "score": r.get("score", 0.0)
            }

            # Add trust information if available
            if self.use_trust_aware:
                result_item["trust_score"] = r.get("trust_score", r.get("confidence_score", 0.5))
                result_item["trust_weighted_score"] = r.get("trust_weighted_score", r.get("score", 0.0))

            formatted_results.append(result_item)

        return {
            "results": formatted_results,
            "enhanced_with_procedures": True,
            "trust_aware": self.use_trust_aware and use_trust_weighting
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

        logger.info("[RAG-CONNECTOR] 📡 Subscribed to 1 event topic")

    async def _on_file_ingested(self, message: Message):
        """Handle file ingestion - auto-index for retrieval."""
        file_path = message.payload.get("file_path")
        document_id = message.payload.get("document_id")

        logger.info(
            f"[RAG-CONNECTOR] 📄 File ingested: {file_path} "
            f"(doc_id: {document_id})"
        )

        # Document already indexed during ingestion
        # Just log for tracking


def create_rag_connector(
    retriever: DocumentRetriever,
    message_bus: Optional[Layer1MessageBus] = None,
    use_trust_aware: bool = False,
    trust_weight: float = 0.3,
    min_trust_threshold: float = 0.3,
) -> RAGConnector:
    """
    Create and initialize RAG connector.
    
    Args:
        retriever: DocumentRetriever instance
        message_bus: Message bus instance
        use_trust_aware: Enable trust-aware retrieval
        trust_weight: Weight of trust in similarity (0-1)
        min_trust_threshold: Minimum trust to include (0-1)
    """
    connector = RAGConnector(
        retriever=retriever,
        message_bus=message_bus,
        use_trust_aware=use_trust_aware,
        trust_weight=trust_weight,
        min_trust_threshold=min_trust_threshold,
    )
    logger.info("[RAG-CONNECTOR] ✓ Initialized and connected to message bus")
    return connector
