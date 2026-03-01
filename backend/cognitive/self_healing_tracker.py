"""
Self-Healing Tracker — Real-time monitoring of what's broken and working.

Connected to Genesis Keys for tracking every state change.
Uses vector search for finding related issues and solutions.

Tracks:
- Component health status (healthy, degraded, broken)
- Error patterns and frequencies
- Automatic fix attempts and their outcomes
- Healing history for learning
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ComponentHealth:
    """Health state of a single component."""
    name: str
    status: str = "healthy"  # healthy, degraded, broken, healing
    last_check: Optional[str] = None
    last_error: Optional[str] = None
    error_count: int = 0
    success_count: int = 0
    uptime_ratio: float = 1.0
    healing_attempts: int = 0
    last_healed: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SelfHealingTracker:
    """
    Real-time tracker for system health — knows what's broken, what's working,
    and attempts automatic healing through the consensus mechanism.
    """

    def __init__(self):
        self._components: Dict[str, ComponentHealth] = {}
        self._error_log: List[Dict[str, Any]] = []
        self._healing_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._max_error_log = 1000
        self._initialized = False

    def initialize(self):
        """Register core components for tracking."""
        if self._initialized:
            return

        core_components = [
            "consensus_engine", "genesis_keys", "memory_mesh",
            "vector_search", "librarian", "embedding_model",
            "qdrant", "database", "file_watcher", "trust_engine",
            "event_bus", "patch_consensus", "file_health_monitor",
        ]
        for name in core_components:
            self._components[name] = ComponentHealth(name=name)

        self._initialized = True
        logger.info("[SELF-HEAL] Tracker initialized with %d components", len(core_components))

    def report_healthy(self, component: str, metadata: Optional[Dict] = None):
        """Report a component as healthy."""
        with self._lock:
            if component not in self._components:
                self._components[component] = ComponentHealth(name=component)

            comp = self._components[component]
            comp.status = "healthy"
            comp.success_count += 1
            comp.last_check = datetime.utcnow().isoformat()
            total = comp.success_count + comp.error_count
            comp.uptime_ratio = comp.success_count / total if total > 0 else 1.0
            if metadata:
                comp.metadata.update(metadata)

    def report_error(self, component: str, error: str, auto_heal: bool = True):
        """
        Report a component error. Optionally triggers auto-heal.
        Writes to genesis key for tracking.
        """
        with self._lock:
            if component not in self._components:
                self._components[component] = ComponentHealth(name=component)

            comp = self._components[component]
            comp.error_count += 1
            comp.last_error = error
            comp.last_check = datetime.utcnow().isoformat()
            total = comp.success_count + comp.error_count
            comp.uptime_ratio = comp.success_count / total if total > 0 else 0.0

            if comp.uptime_ratio < 0.5:
                comp.status = "broken"
            elif comp.uptime_ratio < 0.8:
                comp.status = "degraded"

            self._error_log.append({
                "component": component,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
                "error_count": comp.error_count,
            })
            if len(self._error_log) > self._max_error_log:
                self._error_log = self._error_log[-self._max_error_log:]

        # Track via genesis
        try:
            from api._genesis_tracker import track
            track(
                key_type="error",
                what=f"Component error: {component} — {error[:200]}",
                where=component,
                is_error=True,
                error_type="component_error",
                error_message=error[:500],
                output_data={
                    "component": component,
                    "error_count": comp.error_count,
                    "uptime_ratio": comp.uptime_ratio,
                    "status": comp.status,
                },
                tags=["self_healing", "error", component],
            )
        except Exception:
            pass

        if auto_heal and comp.status in ("broken", "degraded"):
            self._attempt_heal(component, error)

    def _attempt_heal(self, component: str, error: str):
        """Attempt automatic healing of a broken component."""
        comp = self._components.get(component)
        if not comp:
            return

        comp.status = "healing"
        comp.healing_attempts += 1

        heal_result = {"component": component, "attempt": comp.healing_attempts, "actions": []}

        try:
            if component == "qdrant":
                from vector_db.client import get_qdrant_client
                client = get_qdrant_client(force_new=True)
                if client.is_connected():
                    heal_result["actions"].append("reconnected_qdrant")
                    comp.status = "healthy"

            elif component == "database":
                from database.session import initialize_session_factory
                initialize_session_factory()
                heal_result["actions"].append("reinitialized_db_session")
                comp.status = "healthy"

            elif component == "embedding_model":
                from embedding.embedder import get_embedding_model
                model = get_embedding_model(reset=True)
                if model:
                    heal_result["actions"].append("reloaded_embedding_model")
                    comp.status = "healthy"

            elif component == "memory_mesh":
                heal_result["actions"].append("queued_mesh_reconnect")
                comp.status = "degraded"

            elif component == "vector_search":
                from vector_db.client import get_qdrant_client
                client = get_qdrant_client(force_new=True)
                if client.connect():
                    heal_result["actions"].append("reconnected_vector_search")
                    comp.status = "healthy"

            else:
                heal_result["actions"].append("no_auto_heal_available")
                comp.status = "degraded"

        except Exception as e:
            heal_result["error"] = str(e)
            comp.status = "broken"

        comp.last_healed = datetime.utcnow().isoformat()

        self._healing_log.append({
            **heal_result,
            "timestamp": datetime.utcnow().isoformat(),
            "new_status": comp.status,
        })

        try:
            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"Self-heal attempt: {component} → {comp.status}",
                where=component,
                how="self_healing_tracker",
                output_data=heal_result,
                tags=["self_healing", "heal_attempt", component, comp.status],
            )
        except Exception:
            pass

        # Feed healing outcome into learning memory so Grace learns from healing
        try:
            from database.session import get_session
            from cognitive.memory_mesh_integration import MemoryMeshIntegration
            from pathlib import Path
            import json as _json

            learn_sess = next(get_session())
            mesh = MemoryMeshIntegration(
                session=learn_sess,
                knowledge_base_path=Path("knowledge_base"),
            )
            mesh.ingest_learning_experience(
                experience_type="success" if comp.status == "healthy" else "failure",
                context=_json.dumps({"component": component, "error": error[:500]}),
                action_taken=_json.dumps(heal_result),
                outcome=_json.dumps({"new_status": comp.status, "healed": comp.status == "healthy"}),
                source="self_healing_tracker",
            )
            learn_sess.close()
        except Exception:
            pass

    def get_system_health(self) -> Dict[str, Any]:
        """Get complete system health overview."""
        self.initialize()

        with self._lock:
            components = {}
            broken = []
            degraded = []
            healthy = []

            for name, comp in self._components.items():
                components[name] = {
                    "status": comp.status,
                    "uptime_ratio": round(comp.uptime_ratio, 3),
                    "error_count": comp.error_count,
                    "success_count": comp.success_count,
                    "last_check": comp.last_check,
                    "last_error": comp.last_error,
                    "healing_attempts": comp.healing_attempts,
                }

                if comp.status == "broken":
                    broken.append(name)
                elif comp.status == "degraded":
                    degraded.append(name)
                else:
                    healthy.append(name)

            overall = "healthy"
            if broken:
                overall = "critical"
            elif degraded:
                overall = "degraded"

            return {
                "overall_status": overall,
                "components": components,
                "broken": broken,
                "degraded": degraded,
                "healthy": healthy,
                "total_components": len(self._components),
                "recent_errors": self._error_log[-20:],
                "recent_healing": self._healing_log[-10:],
                "timestamp": datetime.utcnow().isoformat(),
            }

    def run_health_check(self) -> Dict[str, Any]:
        """Actively probe all registered components."""
        self.initialize()
        results = {}

        # Check Qdrant
        try:
            from vector_db.client import get_qdrant_client
            client = get_qdrant_client()
            if client.is_connected():
                self.report_healthy("qdrant", {"collections": client.list_collections()})
                self.report_healthy("vector_search")
                results["qdrant"] = "healthy"
            else:
                self.report_error("qdrant", "Not connected")
                self.report_error("vector_search", "Qdrant not connected")
                results["qdrant"] = "broken"
        except Exception as e:
            self.report_error("qdrant", str(e))
            results["qdrant"] = f"error: {e}"

        # Check Database
        try:
            from database.session import get_session
            sess = next(get_session())
            sess.execute("SELECT 1")
            sess.close()
            self.report_healthy("database")
            results["database"] = "healthy"
        except Exception as e:
            self.report_error("database", str(e))
            results["database"] = f"error: {e}"

        # Check Embedding Model
        try:
            from embedding.embedder import get_embedding_model
            model = get_embedding_model()
            if model and model.model is not None:
                self.report_healthy("embedding_model", {
                    "dimension": model.get_embedding_dimension(),
                    "device": model.device,
                })
                results["embedding_model"] = "healthy"
            else:
                self.report_error("embedding_model", "Model not loaded")
                results["embedding_model"] = "not loaded"
        except Exception as e:
            self.report_error("embedding_model", str(e))
            results["embedding_model"] = f"error: {e}"

        # Check Genesis Keys
        try:
            from genesis.genesis_key_service import get_genesis_service
            service = get_genesis_service()
            self.report_healthy("genesis_keys")
            results["genesis_keys"] = "healthy"
        except Exception as e:
            self.report_error("genesis_keys", str(e))
            results["genesis_keys"] = f"error: {e}"

        # Check Memory Mesh
        try:
            from database.session import get_session
            from cognitive.memory_mesh_integration import MemoryMeshIntegration
            from pathlib import Path
            sess = next(get_session())
            kb = Path("knowledge_base")
            mesh = MemoryMeshIntegration(session=sess, knowledge_base_path=kb)
            stats = mesh.get_memory_mesh_stats()
            self.report_healthy("memory_mesh", stats)
            results["memory_mesh"] = "healthy"
            sess.close()
        except Exception as e:
            self.report_error("memory_mesh", str(e))
            results["memory_mesh"] = f"error: {e}"

        return results


_tracker = None


def get_self_healing_tracker() -> SelfHealingTracker:
    """Get the singleton self-healing tracker."""
    global _tracker
    if _tracker is None:
        _tracker = SelfHealingTracker()
        _tracker.initialize()
    return _tracker
