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

from .message_bus import (
    Layer1MessageBus,
    Message,
    MessageType,
    ComponentType,
    AutonomousAction,
    get_message_bus,
    reset_message_bus
)

from .components import (
    MemoryMeshConnector,
    GenesisKeysConnector,
    RAGConnector,
    IngestionConnector,
    LLMOrchestrationConnector,
    VersionControlConnector,
    get_version_control_connector
)

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
