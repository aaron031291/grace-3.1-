"""
Layer 1 Component Connectors

Connects all Layer 1 components to the message bus for:
- Bidirectional communication
- Autonomous action triggering
- Cross-component coordination
"""

import logging

_logger = logging.getLogger(__name__)

# Core connector imports with graceful fallbacks
try:
    from .memory_mesh_connector import MemoryMeshConnector
except ImportError as e:
    _logger.warning(f"Could not import MemoryMeshConnector: {e}")
    MemoryMeshConnector = None

try:
    from .genesis_keys_connector import GenesisKeysConnector
except ImportError as e:
    _logger.warning(f"Could not import GenesisKeysConnector: {e}")
    GenesisKeysConnector = None

try:
    from .rag_connector import RAGConnector
except ImportError as e:
    _logger.warning(f"Could not import RAGConnector: {e}")
    RAGConnector = None

try:
    from .ingestion_connector import IngestionConnector
except ImportError as e:
    _logger.warning(f"Could not import IngestionConnector: {e}")
    IngestionConnector = None

try:
    from .llm_orchestration_connector import LLMOrchestrationConnector
except ImportError as e:
    _logger.warning(f"Could not import LLMOrchestrationConnector: {e}")
    LLMOrchestrationConnector = None

try:
    from .version_control_connector import VersionControlConnector, get_version_control_connector
except ImportError as e:
    _logger.warning(f"Could not import VersionControlConnector: {e}")
    VersionControlConnector = None
    get_version_control_connector = None

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

# Ask Grace connector
try:
    from .ask_grace_connector import AskGraceConnector, get_ask_grace_connector
    ASK_GRACE_CONNECTOR_AVAILABLE = True
except ImportError:
    AskGraceConnector = None
    get_ask_grace_connector = None
    ASK_GRACE_CONNECTOR_AVAILABLE = False

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

# Add Ask Grace connector to exports if available
if ASK_GRACE_CONNECTOR_AVAILABLE:
    __all__.extend([
        "AskGraceConnector",
        "get_ask_grace_connector",
    ])
