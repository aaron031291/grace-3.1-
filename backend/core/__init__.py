"""
Grace Core Module

Provides foundational abstractions:
- BaseComponent: Unified component lifecycle management
- ComponentRegistry: Central component discovery and management
- GraceLoopOutput: Standardized loop output format
"""

from .base_component import (
    BaseComponent,
    ComponentState,
    ComponentRole,
    ComponentManifest,
)
from .registry import (
    ComponentRegistry,
    get_component_registry,
    reset_registry,
)
from .loop_output import (
    GraceLoopOutput,
    ReasoningStep,
    LoopMetadata,
)

__all__ = [
    # Base Component
    "BaseComponent",
    "ComponentState",
    "ComponentRole",
    "ComponentManifest",
    # Registry
    "ComponentRegistry",
    "get_component_registry",
    "reset_registry",
    # Loop Output
    "GraceLoopOutput",
    "ReasoningStep",
    "LoopMetadata",
]
