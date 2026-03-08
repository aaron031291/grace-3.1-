"""
Central execution registry — lightweight discovery and routing layer.

Registers brains, models, and components. Used for:
- Discovery (list brains, actions, components)
- No forced rewrite of call paths — call_brain and brain_api stay as-is.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BrainEntry:
    """Registered brain with its actions."""
    name: str
    actions: List[str] = field(default_factory=list)
    description: Optional[str] = None


@dataclass
class ComponentEntry:
    """Registered component."""
    name: str
    description: Optional[str] = None
    metrics: List[str] = field(default_factory=list)


class ExecutionRegistry:
    """Central registry of brains, models, components."""

    def __init__(self) -> None:
        self._brains: Dict[str, BrainEntry] = {}
        self._components: Dict[str, ComponentEntry] = {}
        self._models: List[str] = []

    def register_brain(self, name: str, actions: List[str], description: Optional[str] = None) -> None:
        """Register a brain and its actions."""
        self._brains[name] = BrainEntry(name=name, actions=list(actions), description=description)

    def register_component(self, name: str, description: Optional[str] = None,
                          metrics: Optional[List[str]] = None) -> None:
        """Register a component."""
        self._components[name] = ComponentEntry(
            name=name, description=description,
            metrics=list(metrics) if metrics else [],
        )

    def register_model(self, name: str) -> None:
        """Register a model (LLM, embedding, etc.)."""
        if name not in self._models:
            self._models.append(name)

    def list_brains(self) -> List[Dict[str, Any]]:
        """List all registered brains with actions."""
        return [
            {"name": b.name, "actions": b.actions, "description": b.description}
            for b in self._brains.values()
        ]

    def list_components(self) -> List[Dict[str, Any]]:
        """List all registered components."""
        return [
            {"name": c.name, "description": c.description, "metrics": c.metrics}
            for c in self._components.values()
        ]

    def list_models(self) -> List[str]:
        """List registered models."""
        return list(self._models)

    def get_registry(self) -> Dict[str, Any]:
        """Full registry snapshot for inspection."""
        return {
            "brains": self.list_brains(),
            "components": self.list_components(),
            "models": self.list_models(),
        }


_registry: Optional[ExecutionRegistry] = None


def get_registry() -> ExecutionRegistry:
    """Get or create the global registry."""
    global _registry
    if _registry is None:
        _registry = ExecutionRegistry()
    return _registry


def init_registry() -> ExecutionRegistry:
    """
    Initialize registry from known brains, components, models.
    Call at app startup.
    """
    r = get_registry()

    # Register brains from brain_api_v2
    try:
        from api.brain_api_v2 import _chat, _files, _govern, _ai, _system, _data, _tasks, _code
        brains_map = {
            "chat": (_chat, "Chat, consensus, world model"),
            "files": (_files, "Files, docs, filing, categorization"),
            "govern": (_govern, "Governance, approvals, KPIs"),
            "ai": (_ai, "AI pipeline, learning, diagnostics"),
            "system": (_system, "System, runtime, health"),
            "data": (_data, "Data, retrieval, ingestion"),
            "tasks": (_tasks, "Tasks, planning"),
            "code": (_code, "Code, generate, projects"),
        }
        for name, (factory, desc) in brains_map.items():
            handlers = factory() if callable(factory) else factory
            actions = list(handlers.keys()) if isinstance(handlers, dict) else []
            r.register_brain(name, actions, desc)
    except Exception as e:
        logger.debug("Registry: could not load brains: %s", e)

    # Register known components
    for comp, desc in [
        ("rag", "RAG retrieval and chat with context"),
        ("ingestion", "Document ingestion"),
        ("learning", "Learning memory, patterns"),
        ("autonomous_loop", "Autonomous loop"),
        ("brain_orchestrator", "Multi-brain orchestration"),
    ]:
        r.register_component(comp, desc, metrics=["requests", "successes", "failures"])

    return r
