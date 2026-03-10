"""
Central Orchestrator — Grace's Cognitive Operating System

The "central nervous system" that coordinates all autonomous systems.
Every cognitive module feeds into and draws from this orchestrator.

Responsibilities:
  - Global state awareness (what every system is doing right now)
  - Task distribution (route work to the right cognitive module)
  - Conflict resolution (when systems produce contradictory outputs)
  - Priority management (what gets processed first)
  - Integration health monitoring (detect broken connections)
  - Cross-system state synchronization

Architecture:
  All systems → Event Bus → Central Orchestrator → Decisions → Systems
"""

import logging
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SystemState:
    """Global state container — single source of truth for the entire system."""

    def __init__(self):
        self.components: Dict[str, Dict[str, Any]] = {}
        self.active_tasks: List[Dict[str, Any]] = []
        self.last_sync: str = ""
        self._lock = threading.Lock()

    def update(self, component: str, state: Dict[str, Any]):
        with self._lock:
            if component not in self.components:
                self.components[component] = {}
            self.components[component].update(state)
            self.components[component]["last_updated"] = datetime.now(timezone.utc).isoformat()

    def get(self, component: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self.components.get(component, {}))

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self.components.items()}

    def add_task(self, task: Dict[str, Any]):
        with self._lock:
            self.active_tasks.append(task)
            if len(self.active_tasks) > 100:
                self.active_tasks = self.active_tasks[-100:]

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.active_tasks)


class CentralOrchestrator:
    """
    Grace's Cognitive Operating System.
    Coordinates all autonomous systems into unified intelligence.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.state = SystemState()
        self._initialized = False
        self._event_handlers_registered = False

    @classmethod
    def get_instance(cls) -> "CentralOrchestrator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self):
        """Wire up event bus subscriptions for all systems."""
        if self._event_handlers_registered:
            return

        try:
            from cognitive.event_bus import subscribe

            subscribe("llm.called", self._on_llm_called)
            subscribe("llm.failed", self._on_llm_failed)
            subscribe("healing.*", self._on_healing_event)
            subscribe("trust.*", self._on_trust_event)
            subscribe("file.*", self._on_file_event)
            subscribe("learning.*", self._on_learning_event)
            subscribe("consensus.*", self._on_consensus_event)
            subscribe("genesis.key_created", self._on_genesis_event)

            self._event_handlers_registered = True
            logger.info("[ORCHESTRATOR] Event bus subscriptions registered")
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Event bus setup failed: {e}")

        self._sync_initial_state()
        self._initialized = True

    # ── Event Handlers ────────────────────────────────────────────────

    def _on_llm_called(self, event):
        self.state.update("llm", {
            "last_call": event.timestamp,
            "provider": event.data.get("provider", "unknown"),
            "status": "active",
        })

    def _on_llm_failed(self, event):
        self.state.update("llm", {
            "last_error": event.timestamp,
            "error": event.data.get("error", ""),
            "status": "error",
        })

    def _on_healing_event(self, event):
        self.state.update("immune_system", {
            "last_event": event.topic,
            "timestamp": event.timestamp,
            "data": event.data,
        })

    def _on_trust_event(self, event):
        self.state.update("trust_engine", {
            "last_update": event.timestamp,
            "component": event.data.get("component", ""),
            "score": event.data.get("score", 0),
        })

    def _on_file_event(self, event):
        self.state.update("file_system", {
            "last_event": event.topic,
            "timestamp": event.timestamp,
        })

    def _on_learning_event(self, event):
        self.state.update("learning", {
            "last_event": event.topic,
            "timestamp": event.timestamp,
        })

    def _on_consensus_event(self, event):
        self.state.update("consensus", {
            "last_run": event.timestamp,
            "models": event.data.get("models", []),
        })

    def _on_genesis_event(self, event):
        count = self.state.get("genesis").get("total_keys", 0) + 1
        self.state.update("genesis", {
            "total_keys": count,
            "last_key": event.timestamp,
        })

    # ── State Synchronization ─────────────────────────────────────────

    def _sync_initial_state(self):
        """Pull initial state from all systems."""
        # Trust Engine
        try:
            from cognitive.trust_engine import get_trust_engine
            te = get_trust_engine()
            dashboard = te.get_dashboard()
            self.state.update("trust_engine", {
                "overall_trust": dashboard.get("overall_trust", 0),
                "component_count": dashboard.get("component_count", 0),
                "status": "active",
            })
        except Exception:
            self.state.update("trust_engine", {"status": "unavailable"})

        # Flash Cache
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            stats = fc.stats()
            self.state.update("flash_cache", {
                "entries": stats.get("total_entries", 0),
                "keywords": stats.get("unique_keywords", 0),
                "status": "active",
            })
        except Exception:
            self.state.update("flash_cache", {"status": "unavailable"})

        # Unified Memory
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            stats = mem.get_stats()
            total = sum(v.get("count", 0) for v in stats.values() if isinstance(v, dict))
            self.state.update("memory", {
                "total_entries": total,
                "systems": list(stats.keys()),
                "status": "active",
            })
        except Exception:
            self.state.update("memory", {"status": "unavailable"})

        # LLM Usage
        try:
            from llm_orchestrator.governance_wrapper import get_llm_usage_stats
            stats = get_llm_usage_stats()
            self.state.update("llm", {
                "total_calls": stats.get("total_calls", 0),
                "avg_latency": stats.get("avg_latency_ms", 0),
                "status": "active",
            })
        except Exception:
            self.state.update("llm", {"status": "unavailable"})

        # Consensus Engine
        try:
            from cognitive.consensus_engine import get_available_models
            models = get_available_models()
            available = [m for m in models if m["available"]]
            self.state.update("consensus", {
                "available_models": len(available),
                "model_names": [m["name"] for m in available],
                "status": "active",
            })
        except Exception:
            self.state.update("consensus", {"status": "unavailable"})

        self.state.last_sync = datetime.now(timezone.utc).isoformat()

    def sync_state(self) -> Dict[str, Any]:
        """Force a full state sync and return the result."""
        self._sync_initial_state()
        return self.get_global_state()

    # ── Decision & Routing ────────────────────────────────────────────

    def route_task(self, task_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a task to the appropriate cognitive module.
        The orchestrator decides which system handles what.
        """
        routing_table = {
            "code_generation": "pipeline",
            "file_organization": "librarian",
            "knowledge_expansion": "knowledge_cycle",
            "healing": "immune_system",
            "consensus_needed": "consensus_engine",
            "learning": "idle_learner",
            "code_integration": "hunter",
            "document_analysis": "flash_cache",
        }

        target = routing_table.get(task_type, "pipeline")

        self.state.add_task({
            "type": task_type,
            "target": target,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_keys": list(data.keys()),
        })

        # Publish event
        try:
            from cognitive.event_bus import publish
            publish(f"task.routed", {
                "type": task_type,
                "target": target,
            }, source="orchestrator")
        except Exception:
            pass

        return {"routed_to": target, "task_type": task_type}

    def check_integration_health(self) -> Dict[str, Any]:
        """
        Check all integration points and report broken connections.
        This is the integration health monitor Opus identified as missing.
        """
        checks = {}

        integrations = [
            ("pipeline", "cognitive.pipeline", "CognitivePipeline"),
            ("consensus", "cognitive.consensus_engine", "run_consensus"),
            ("flash_cache", "cognitive.flash_cache", "get_flash_cache"),
            ("event_bus", "cognitive.event_bus", "publish"),
            ("unified_memory", "cognitive.unified_memory", "get_unified_memory"),
            ("trust_engine", "cognitive.trust_engine", "get_trust_engine"),
            ("immune_system", "cognitive.immune_system", "GraceImmuneSystem"),
            ("librarian", "cognitive.librarian_autonomous", "AutonomousLibrarian"),
            ("mirror", "cognitive.mirror_self_modeling", "MirrorSelfModelingSystem"),
            ("knowledge_cycle", "cognitive.knowledge_cycle", "KnowledgeCycle"),
            ("model_updater", "cognitive.model_updater", "check_all_models"),
            ("magma", "cognitive.magma_bridge", "query_context"),
            ("idle_learner", "cognitive.idle_learner", "IdleLearner"),
            ("hunter", "cognitive.hunter_assimilator", "HunterAssimilator"),
            ("file_generator", "cognitive.file_generator", "FileGenerator"),
        ]

        healthy = 0
        broken = 0
        for name, module_path, attr_name in integrations:
            try:
                mod = __import__(module_path, fromlist=[attr_name])
                obj = getattr(mod, attr_name)
                checks[name] = {"status": "healthy", "importable": True, "callable": callable(obj)}
                healthy += 1
            except Exception as e:
                checks[name] = {"status": "broken", "error": str(e)}
                broken += 1

        return {
            "total": len(integrations),
            "healthy": healthy,
            "broken": broken,
            "health_percent": round(healthy / len(integrations) * 100, 1),
            "checks": checks,
        }

    # ── Global State Access ───────────────────────────────────────────

    def get_global_state(self) -> Dict[str, Any]:
        """Get the complete global state — everything Grace knows about herself."""
        return {
            "components": self.state.get_all(),
            "active_tasks": self.state.get_active_tasks(),
            "last_sync": self.state.last_sync,
            "initialized": self._initialized,
            "event_bus_connected": self._event_handlers_registered,
        }

    def get_dashboard(self) -> Dict[str, Any]:
        """High-level dashboard for the orchestrator."""
        global_state = self.get_global_state()
        health = self.check_integration_health()

        active_count = sum(
            1 for c in global_state["components"].values()
            if c.get("status") == "active"
        )
        total = len(global_state["components"])

        return {
            "system_status": "healthy" if health["health_percent"] >= 80 else "degraded",
            "integration_health": health["health_percent"],
            "active_components": active_count,
            "total_components": total,
            "integration_checks": health,
            "global_state": global_state,
        }


def get_orchestrator() -> CentralOrchestrator:
    return CentralOrchestrator.get_instance()
