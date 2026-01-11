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

from typing import Dict, Any, Optional
import logging
from pathlib import Path
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

# Optional neuro-symbolic connector
try:
    from layer1.components.neuro_symbolic_connector import (
        NeuroSymbolicConnector,
        create_neuro_symbolic_connector
    )
    NEURO_SYMBOLIC_AVAILABLE = True
except ImportError:
    NeuroSymbolicConnector = None
    create_neuro_symbolic_connector = None
    NEURO_SYMBOLIC_AVAILABLE = False

# Optional knowledge base connectors
try:
    from layer1.components.knowledge_base_connector import (
        KnowledgeBaseIngestionConnector,
        create_knowledge_base_ingestion_connector
    )
    from layer1.components.data_integrity_connector import (
        DataIntegrityConnector,
        create_data_integrity_connector
    )
    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError:
    KnowledgeBaseIngestionConnector = None
    create_knowledge_base_ingestion_connector = None
    DataIntegrityConnector = None
    create_data_integrity_connector = None
    KNOWLEDGE_BASE_AVAILABLE = False

from cognitive.memory_mesh_integration import MemoryMeshIntegration
from retrieval.retriever import DocumentRetriever
from ingestion.service import TextIngestionService
from llm_orchestrator.llm_orchestrator import LLMOrchestrator
from embedding.embedder import get_embedding_model

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
        version_control_connector=None,
        neuro_symbolic_connector=None,
        knowledge_base_ingestion_connector=None,
        data_integrity_connector=None,
    ):
        self.message_bus = message_bus
        self.memory_mesh = memory_mesh_connector
        self.genesis_keys = genesis_keys_connector
        self.rag = rag_connector
        self.ingestion = ingestion_connector
        self.llm_orchestration = llm_orchestration_connector
        self.version_control = version_control_connector
        self.neuro_symbolic = neuro_symbolic_connector
        self.knowledge_base_ingestion = knowledge_base_ingestion_connector
        self.data_integrity = data_integrity_connector

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
    ollama_client=None,
    enable_neuro_symbolic: bool = False,
    trust_weight: float = 0.3,
    min_trust_threshold: float = 0.3,
    enable_knowledge_base: bool = False,
    ai_research_path: Optional[str] = None,
    database_path: Optional[str] = None,
) -> Layer1System:
    """
    Initialize complete Layer 1 system.

    Args:
        session: Database session
        kb_path: Path to knowledge base
        vector_db_client: Optional vector DB client
        ollama_client: Optional Ollama client
        enable_neuro_symbolic: Enable neuro-symbolic features (optional)
        trust_weight: Weight of trust in similarity (0-1) if neuro-symbolic enabled
        min_trust_threshold: Minimum trust to include (0-1) if neuro-symbolic enabled
        enable_knowledge_base: Enable knowledge base ingestion and verification (optional)
        ai_research_path: Path to ai_research directory (default: {project_root}/data/ai_research)
        database_path: Path to database file (default: from DatabaseConfig)

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

    # Create embedding model (singleton)
    embedding_model = get_embedding_model()
    logger.info("[LAYER1] ✓ Embedding model loaded")

    # Create retriever (optionally trust-aware)
    if enable_neuro_symbolic and NEURO_SYMBOLIC_AVAILABLE:
        try:
            from retrieval.trust_aware_retriever import get_trust_aware_retriever
            base_retriever = DocumentRetriever(
                collection_name="documents",
                embedding_model=embedding_model
            )
            retriever = get_trust_aware_retriever(
                base_retriever=base_retriever,
                trust_weight=trust_weight,
                min_trust_threshold=min_trust_threshold,
            )
            logger.info("[LAYER1] ✓ Trust-aware RAG retriever initialized")
        except ImportError:
            retriever = DocumentRetriever(
                collection_name="documents",
                embedding_model=embedding_model
            )
            logger.info("[LAYER1] ✓ RAG retriever initialized (trust-aware not available)")
    else:
        retriever = DocumentRetriever(
            collection_name="documents",
            embedding_model=embedding_model
        )
        logger.info("[LAYER1] ✓ RAG retriever initialized")

    # Create ingestion service
    ingestion_service = TextIngestionService(
        collection_name="documents",
        chunk_size=512,
        chunk_overlap=50,
        embedding_model=embedding_model
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

    # Create RAG connector (optionally with trust-aware retrieval)
    rag_connector = RAGConnector(
        retriever=retriever,
        message_bus=message_bus,
        use_trust_aware=enable_neuro_symbolic and NEURO_SYMBOLIC_AVAILABLE,
        trust_weight=trust_weight,
        min_trust_threshold=min_trust_threshold,
    )

    ingestion_connector = IngestionConnector(
        ingestion_service=ingestion_service,
        message_bus=message_bus
    )

    # LLM orchestrator
    llm_orchestrator = LLMOrchestrator(
        session=session,
        embedding_model=embedding_model,
        knowledge_base_path=kb_path
    )
    logger.info("[LAYER1] ✓ LLM orchestrator initialized")
    
    llm_orchestration_connector = LLMOrchestrationConnector(
        llm_orchestrator=llm_orchestrator,
        message_bus=message_bus
    )
    logger.info("[LAYER1] ✓ LLM orchestration connector initialized")

    # Version control connector (symbiotic Genesis Keys + Version Control)
    version_control_connector = get_version_control_connector()
    message_bus.register_component(ComponentType.VERSION_CONTROL, version_control_connector)
    logger.info("[LAYER1] ✓ Version control connector registered")

    # Neuro-symbolic connector (optional)
    neuro_symbolic_connector = None
    if enable_neuro_symbolic and NEURO_SYMBOLIC_AVAILABLE:
        try:
            from ml_intelligence.neuro_symbolic_reasoner import get_neuro_symbolic_reasoner
            from ml_intelligence.rule_storage import get_rule_storage
            from cognitive.learning_memory import LearningMemoryManager
            from pathlib import Path
            
            # Create learning memory manager for rule storage
            learning_memory = LearningMemoryManager(session, Path(kb_path))
            
            # Create neuro-symbolic reasoner
            reasoner = get_neuro_symbolic_reasoner(
                retriever=retriever,
                learning_memory=learning_memory,
                neural_weight=0.5,
                symbolic_weight=0.5,
            )
            
            # Create rule storage
            rule_storage = get_rule_storage(learning_memory)
            
            # Create neuro-symbolic connector
            neuro_symbolic_connector = create_neuro_symbolic_connector(
                reasoner=reasoner,
                rule_storage=rule_storage,
                message_bus=message_bus,
            )
            
            if neuro_symbolic_connector and neuro_symbolic_connector.enabled:
                logger.info("[LAYER1] ✓ Neuro-symbolic connector initialized")
            else:
                logger.info("[LAYER1] ⚠ Neuro-symbolic connector not available")
                neuro_symbolic_connector = None
                
        except Exception as e:
            logger.warning(f"[LAYER1] ⚠ Failed to initialize neuro-symbolic connector: {e}")
            neuro_symbolic_connector = None

    # Knowledge base connectors (optional)
    knowledge_base_ingestion_connector = None
    data_integrity_connector = None
    if enable_knowledge_base and KNOWLEDGE_BASE_AVAILABLE:
        try:
            from database.config import DatabaseConfig
            
            # Get paths
            project_root = Path(kb_path).parent.parent if kb_path else Path.cwd()
            if ai_research_path is None:
                ai_research_path = str(project_root / "data" / "ai_research")
            
            if database_path is None:
                db_config = DatabaseConfig.from_env()
                database_path = db_config.database_path or str(project_root / "data" / "grace.db")
            
            # Create knowledge base ingestion connector
            knowledge_base_ingestion_connector = create_knowledge_base_ingestion_connector(
                ai_research_path=ai_research_path,
                message_bus=message_bus,
                use_trust_aware=enable_neuro_symbolic and NEURO_SYMBOLIC_AVAILABLE,
                trust_weight=trust_weight,
                min_trust_threshold=min_trust_threshold,
            )
            logger.info("[LAYER1] ✓ Knowledge base ingestion connector initialized")
            
            # Create data integrity connector
            data_integrity_connector = create_data_integrity_connector(
                ai_research_path=ai_research_path,
                database_path=database_path,
                message_bus=message_bus,
                enable_trust_scoring=enable_neuro_symbolic and NEURO_SYMBOLIC_AVAILABLE,
            )
            logger.info("[LAYER1] ✓ Data integrity connector initialized")
            
        except Exception as e:
            logger.warning(f"[LAYER1] ⚠ Failed to initialize knowledge base connectors: {e}")
            knowledge_base_ingestion_connector = None
            data_integrity_connector = None

    logger.info("[LAYER1] ✓ All components connected to message bus")

    # 4. Create Layer 1 system
    layer1 = Layer1System(
        message_bus=message_bus,
        memory_mesh_connector=memory_mesh_connector,
        genesis_keys_connector=genesis_keys_connector,
        rag_connector=rag_connector,
        ingestion_connector=ingestion_connector,
        llm_orchestration_connector=llm_orchestration_connector,
        version_control_connector=version_control_connector,
        neuro_symbolic_connector=neuro_symbolic_connector,
        knowledge_base_ingestion_connector=knowledge_base_ingestion_connector,
        data_integrity_connector=data_integrity_connector,
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
