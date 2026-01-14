"""
Layer 1 - Universal Input and Communication Layer

Complete autonomous system for bidirectional component communication.

Components:
- Message Bus: Central routing and autonomous action triggering
- Memory Mesh Connector: Learning memory integration
- Genesis Keys Connector: Universal tracking
- RAG Connector: Retrieval-augmented generation
- Ingestion Connector: File processing
- LLM Orchestration Connector: Multi-LLM coordination
"""

import logging

_logger = logging.getLogger(__name__)

# Import message bus components
try:
    from .message_bus import (
        Layer1MessageBus,
        Message,
        MessageType,
        ComponentType,
        AutonomousAction,
        get_message_bus,
        reset_message_bus
    )
except ImportError as e:
    _logger.warning(f"Could not import message_bus: {e}")
    Layer1MessageBus = None
    Message = None
    MessageType = None
    ComponentType = None
    AutonomousAction = None
    get_message_bus = None
    reset_message_bus = None

# Import component connectors
try:
    from .components import (
        MemoryMeshConnector,
        GenesisKeysConnector,
        RAGConnector,
        IngestionConnector,
        LLMOrchestrationConnector,
        VersionControlConnector,
        get_version_control_connector
    )
except ImportError as e:
    _logger.warning(f"Could not import components: {e}")
    MemoryMeshConnector = None
    GenesisKeysConnector = None
    RAGConnector = None
    IngestionConnector = None
    LLMOrchestrationConnector = None
    VersionControlConnector = None
    get_version_control_connector = None

__all__ = [
    # Message Bus
    "Layer1MessageBus",
    "Message",
    "MessageType",
    "ComponentType",
    "AutonomousAction",
    "get_message_bus",
    "reset_message_bus",

    # Connectors
    "MemoryMeshConnector",
    "GenesisKeysConnector",
    "RAGConnector",
    "IngestionConnector",
    "LLMOrchestrationConnector",
    "VersionControlConnector",
    "get_version_control_connector",
]
