"""
Layer 1 Initialization - Complete System Setup

Initializes all Layer 1 components and connects them to the message bus
for autonomous bidirectional communication.

Usage:
    from backend.layer1.initialize import initialize_layer1

    layer1 = initialize_layer1(
        session=db_session,
        kb_path="/path/to/knowledge_base"
    )

    # All components now communicate autonomously!
"""

from typing import Dict, Any
import logging
from sqlalchemy.orm import Session

from layer1.message_bus import get_message_bus, Layer1MessageBus, ComponentType
from layer1.components import (
    MemoryMeshConnector,
    GenesisKeysConnector,
    RAGConnector,
    IngestionConnector,
    LLMOrchestrationConnector
)
from layer1.components.version_control_connector import get_version_control_connector

from cognitive.memory_mesh_integration import MemoryMeshIntegration
from retrieval.retriever import DocumentRetriever
from ingestion.service import TextIngestionService

logger = logging.getLogger(__name__)


class Layer1System:
    """
    Complete Layer 1 system with all components connected.

    Provides autonomous:
    - Learning memory with trust scoring
    - Genesis Key tracking
    - RAG retrieval with procedural memory
    - File ingestion with automatic indexing
    - Multi-LLM orchestration with skill awareness
    - Symbiotic version control (Genesis Keys + File Versions)
    """

    def __init__(
        self,
        message_bus: Layer1MessageBus,
        memory_mesh_connector: MemoryMeshConnector,
        genesis_keys_connector: GenesisKeysConnector,
        rag_connector: RAGConnector,
        ingestion_connector: IngestionConnector,
        llm_orchestration_connector: LLMOrchestrationConnector,
        version_control_connector=None
    ):
        self.message_bus = message_bus
        self.memory_mesh = memory_mesh_connector
        self.genesis_keys = genesis_keys_connector
        self.rag = rag_connector
        self.ingestion = ingestion_connector
        self.llm_orchestration = llm_orchestration_connector
        self.version_control = version_control_connector

        logger.info("[LAYER1] ✓ System initialized with all components")

    def get_stats(self) -> Dict[str, Any]:
        """Get complete Layer 1 system statistics."""
        return self.message_bus.get_stats()

    def get_autonomous_actions(self) -> list:
        """Get all registered autonomous actions."""
        return self.message_bus.get_autonomous_actions()


def initialize_layer1(
    session: Session,
    kb_path: str,
    vector_db_client=None,
    ollama_client=None
) -> Layer1System:
    """
    Initialize complete Layer 1 system.

    Args:
        session: Database session
        kb_path: Path to knowledge base
        vector_db_client: Optional vector DB client
        ollama_client: Optional Ollama client

    Returns:
        Fully initialized Layer 1 system
    """
    logger.info("[LAYER1] 🚀 Initializing Layer 1 system...")

    # 1. Create message bus
    message_bus = get_message_bus()
    logger.info("[LAYER1] ✓ Message bus created")

    # 2. Initialize core services
    memory_mesh = MemoryMeshIntegration(session, kb_path)
    logger.info("[LAYER1] ✓ Memory mesh initialized")

    # Create retriever (simplified - would use actual instances)
    from backend.vector_db.client import get_vector_db_client
    from backend.database.session import get_db

    if vector_db_client is None:
        vector_db_client = get_vector_db_client()

    retriever = HybridRetriever(
        session=session,
        vector_db_client=vector_db_client
    )
    logger.info("[LAYER1] ✓ RAG retriever initialized")

    ingestion_service = IngestionService(
        session=session,
        kb_path=kb_path,
        vector_db_client=vector_db_client
    )
    logger.info("[LAYER1] ✓ Ingestion service initialized")

    # 3. Create and connect all components
    memory_mesh_connector = MemoryMeshConnector(
        memory_mesh=memory_mesh,
        message_bus=message_bus
    )

    genesis_keys_connector = GenesisKeysConnector(
        session=session,
        kb_path=kb_path,
        message_bus=message_bus
    )

    rag_connector = RAGConnector(
        retriever=retriever,
        message_bus=message_bus
    )

    ingestion_connector = IngestionConnector(
        ingestion_service=ingestion_service,
        message_bus=message_bus
    )

    # LLM orchestrator (simplified)
    llm_orchestrator = {}  # Would be actual orchestrator
    llm_orchestration_connector = LLMOrchestrationConnector(
        llm_orchestrator=llm_orchestrator,
        message_bus=message_bus
    )

    # Version control connector (symbiotic Genesis Keys + Version Control)
    version_control_connector = get_version_control_connector()
    message_bus.register_component(ComponentType.VERSION_CONTROL, version_control_connector)
    logger.info("[LAYER1] ✓ Version control connector registered")

    logger.info("[LAYER1] ✓ All components connected to message bus")

    # 4. Create Layer 1 system
    layer1 = Layer1System(
        message_bus=message_bus,
        memory_mesh_connector=memory_mesh_connector,
        genesis_keys_connector=genesis_keys_connector,
        rag_connector=rag_connector,
        ingestion_connector=ingestion_connector,
        llm_orchestration_connector=llm_orchestration_connector,
        version_control_connector=version_control_connector
    )

    # 5. Log statistics
    stats = layer1.get_stats()
    autonomous_actions = layer1.get_autonomous_actions()

    logger.info(
        f"[LAYER1] 🎉 System ready!\n"
        f"  - Components: {stats['registered_components']}\n"
        f"  - Autonomous actions: {len(autonomous_actions)}\n"
        f"  - Request handlers: {sum(len(h) for h in stats.get('request_handlers', {}).values())}\n"
        f"  - Subscriptions: {sum(stats.get('subscribers', {}).values())}"
    )

    return layer1


def get_layer1_stats() -> Dict[str, Any]:
    """Get Layer 1 system statistics."""
    message_bus = get_message_bus()
    return message_bus.get_stats()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from backend.database.session import get_db

    # Initialize system
    session = next(get_db())
    kb_path = "backend/knowledge_base"

    layer1 = initialize_layer1(session, kb_path)

    # Show stats
    stats = layer1.get_stats()
    print("\n=== Layer 1 Statistics ===")
    print(f"Components: {stats['registered_components']}")
    print(f"Total messages: {stats['total_messages']}")
    print(f"Autonomous actions: {stats['autonomous_actions']}")

    # Show autonomous actions
    actions = layer1.get_autonomous_actions()
    print("\n=== Autonomous Actions ===")
    for action in actions:
        print(f"  - {action['component']}: {action['description']}")
