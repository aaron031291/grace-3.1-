"""
Layer 1 Component Connectors

Connects all Layer 1 components to the message bus for:
- Bidirectional communication
- Autonomous action triggering
- Cross-component coordination
"""

from .memory_mesh_connector import MemoryMeshConnector
from .genesis_keys_connector import GenesisKeysConnector
from .rag_connector import RAGConnector
from .ingestion_connector import IngestionConnector
from .llm_orchestration_connector import LLMOrchestrationConnector
from .version_control_connector import VersionControlConnector, get_version_control_connector

# Optional neuro-symbolic connector
try:
    from .neuro_symbolic_connector import NeuroSymbolicConnector, create_neuro_symbolic_connector
    NEURO_SYMBOLIC_CONNECTOR_AVAILABLE = True
except ImportError:
    NeuroSymbolicConnector = None
    create_neuro_symbolic_connector = None
    NEURO_SYMBOLIC_CONNECTOR_AVAILABLE = False

# Optional knowledge base connectors
try:
    from .knowledge_base_connector import KnowledgeBaseIngestionConnector, create_knowledge_base_ingestion_connector
    from .data_integrity_connector import DataIntegrityConnector, create_data_integrity_connector
    KNOWLEDGE_BASE_CONNECTORS_AVAILABLE = True
except ImportError:
    KnowledgeBaseIngestionConnector = None
    create_knowledge_base_ingestion_connector = None
    DataIntegrityConnector = None
    create_data_integrity_connector = None
    KNOWLEDGE_BASE_CONNECTORS_AVAILABLE = False

# Optional KPI connector
try:
    from .kpi_connector import KPIConnector, create_kpi_connector
    KPI_CONNECTOR_AVAILABLE = True
except ImportError:
    KPIConnector = None
    create_kpi_connector = None
    KPI_CONNECTOR_AVAILABLE = False

__all__ = [
    "MemoryMeshConnector",
    "GenesisKeysConnector",
    "RAGConnector",
    "IngestionConnector",
    "LLMOrchestrationConnector",
    "VersionControlConnector",
    "get_version_control_connector",
]

# Add neuro-symbolic connector to exports if available
if NEURO_SYMBOLIC_CONNECTOR_AVAILABLE:
    __all__.extend([
        "NeuroSymbolicConnector",
        "create_neuro_symbolic_connector",
    ])

# Add knowledge base connectors to exports if available
if KNOWLEDGE_BASE_CONNECTORS_AVAILABLE:
    __all__.extend([
        "KnowledgeBaseIngestionConnector",
        "create_knowledge_base_ingestion_connector",
        "DataIntegrityConnector",
        "create_data_integrity_connector",
    ])

# Add KPI connector to exports if available
if KPI_CONNECTOR_AVAILABLE:
    __all__.extend([
        "KPIConnector",
        "create_kpi_connector",
    ])
