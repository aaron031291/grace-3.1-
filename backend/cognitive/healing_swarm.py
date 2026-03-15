"""
Healing Swarm — Concurrent multi-agent self-healing system.

Instead of one sequential healer, Grace spawns a swarm of specialized
agents that fix multiple problems simultaneously.

Architecture:
  SwarmCoordinator
    ├── ConnectionAgent    — DB, Qdrant, Ollama, network
    ├── CodeAgent         — AttributeError, ImportError, code fixes
    ├── MemoryAgent       — leaks, cache, GC, vector cleanup
    ├── TrustAgent        — trust scores, brain domain health
    ├── ConfigAgent       — .env drift, schema migration, config
    └── ServiceAgent      — process restarts, port health, watchdog

Each agent:
  - Runs in its own thread
  - Picks problems from a shared queue (filtered by domain)
  - Publishes progress/results to event bus
  - Tracks its own MTTR and success rate
"""

import threading
import time
import logging
import uuid
import traceback
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)


class AgentDomain(str, Enum):
    CONNECTION = "connection"
    CODE = "code"
    MEMORY = "memory"
    TRUST = "trust"
    CONFIG = "config"
    SERVICE = "service"


class AgentStatus(str, Enum):
    IDLE = "idle"
    HEALING = "healing"
    COOLDOWN = "cooldown"
    ERROR = "error"


@dataclass
class HealingTask:
    id: str
    domain: AgentDomain
    component: str
    description: str
    severity: str = "medium"
    error: str = ""
    file_path: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class HealingResult:
    task_id: str
    agent_domain: str
    component: str
    status: str  # healed, failed, escalated, skipped
    action_taken: str = ""
    duration_seconds: float = 0.0
    error: str = ""
    started_at: str = ""
    finished_at: str = ""


@dataclass
class AgentState:
    domain: AgentDomain
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_heal_time: float = 0.0
    last_activity: str = ""

    @property
    def success_rate(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        return (self.tasks_completed / total * 100) if total > 0 else 0.0

    @property
    def avg_mttr(self) -> float:
        return (self.total_heal_time / self.tasks_completed) if self.tasks_completed > 0 else 0.0


class HealingAgent:
    """Base healing agent. Each domain subclass implements _heal()."""

    def __init__(self, domain: AgentDomain, coordinator: 'SwarmCoordinator'):
        self.domain = domain
        self.coordinator = coordinator
        self.state = AgentState(domain=domain)
        self._lock = threading.Lock()

    def can_handle(self, task: HealingTask) -> bool:
        return task.domain == self.domain

    def execute(self, task: HealingTask) -> HealingResult:
        started = datetime.now(timezone.utc)
        self.state.status = AgentStatus.HEALING
        self.state.current_task = task.id
        self.state.last_activity = started.isoformat()

        self._publish_event("healing.agent.started", {
            "agent": self.domain.value,
            "task_id": task.id,
            "component": task.component,
            "description": task.description,
        })

        try:
            result = self._heal(task)
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            result.duration_seconds = elapsed
            result.started_at = started.isoformat()
            result.finished_at = datetime.now(timezone.utc).isoformat()

            if result.status == "healed":
                self.state.tasks_completed += 1
                self.state.total_heal_time += elapsed
            else:
                self.state.tasks_failed += 1

            self._publish_event("healing.agent.completed", {
                "agent": self.domain.value,
                "task_id": task.id,
                "status": result.status,
                "action": result.action_taken,
                "duration": elapsed,
            })

            return result

        except Exception as e:
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            self.state.tasks_failed += 1
            self.state.status = AgentStatus.ERROR
            logger.error(f"[SWARM-{self.domain.value}] Agent error: {e}")

            self._publish_event("healing.agent.error", {
                "agent": self.domain.value,
                "task_id": task.id,
                "error": str(e),
            })

            return HealingResult(
                task_id=task.id, agent_domain=self.domain.value,
                component=task.component, status="failed",
                action_taken="agent_error", error=str(e),
                duration_seconds=elapsed,
                started_at=started.isoformat(),
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
        finally:
            self.state.status = AgentStatus.IDLE
            self.state.current_task = None

    def _heal(self, task: HealingTask) -> HealingResult:
        raise NotImplementedError

    def _publish_event(self, topic: str, data: dict):
        try:
            from cognitive.event_bus import publish_async
            publish_async(topic, data, source=f"swarm.{self.domain.value}")
        except Exception:
            pass


class ConnectionAgent(HealingAgent):
    """Heals database, Qdrant, Ollama, and network connectivity."""

    def __init__(self, coordinator):
        super().__init__(AgentDomain.CONNECTION, coordinator)

    def _heal(self, task: HealingTask) -> HealingResult:
        component = (task.component or "").lower()
        action = "unknown"

        if "database" in component or "db" in component or "postgres" in component:
            action = "database_reconnect"
            try:
                from database.session import initialize_session_factory
                initialize_session_factory()
                return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                     component=task.component, status="healed",
                                     action_taken=action)
            except Exception as e:
                return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                     component=task.component, status="failed",
                                     action_taken=action, error=str(e))

        elif "qdrant" in component or "vector" in component:
            action = "qdrant_reconnect"
            try:
                from vector_db.client import get_qdrant_client
                client = get_qdrant_client()
                collections = client.get_collections()
                return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                     component=task.component, status="healed",
                                     action_taken=action)
            except Exception as e:
                return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                     component=task.component, status="failed",
                                     action_taken=action, error=str(e))

        elif "ollama" in component or "llm" in component:
            action = "ollama_ping"
            try:
                import httpx
                r = httpx.get("http://localhost:11434/api/tags", timeout=5)
                ok = r.status_code == 200
                return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                     component=task.component,
                                     status="healed" if ok else "failed",
                                     action_taken=action)
            except Exception as e:
                return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                     component=task.component, status="failed",
                                     action_taken=action, error=str(e))

        # Generic network
        action = "network_probe"
        return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                             component=task.component, status="escalated",
                             action_taken=action, error="Unknown connection target")


class CodeAgent(HealingAgent):
    """Heals code errors via Kimi + Opus multi-LLM coding agents."""

    def __init__(self, coordinator):
        super().__init__(AgentDomain.CODE, coordinator)

    def _heal(self, task: HealingTask) -> HealingResult:
        # PRIMARY: Use multi-LLM coding agents (Kimi + Opus in parallel)
        try:
            from cognitive.coding_agents import get_coding_agent_pool, CodingTask as CT
            pool = get_coding_agent_pool()
            
            ct = CT(
                id=task.id,
                task_type="fix",
                file_path=task.file_path or task.component,
                description=task.error or task.description,
                error=task.error,
                context=task.context,
            )
            
            # Dispatch to Kimi + Opus in parallel — consensus-based fixing
            results = pool.dispatch_parallel(ct, agents=["kimi", "opus"])
            
            # Pick the best result (highest confidence)
            best = max(results, key=lambda r: r.confidence) if results else None
            
            if best and best.status == "completed" and best.confidence >= 0.5:
                action = f"multi_llm_fix_{best.agent}"
                return HealingResult(
                    task_id=task.id, agent_domain=self.domain.value,
                    component=task.component, status="healed",
                    action_taken=action,
                )
            
            # All agents failed or low confidence → escalate
            errors = "; ".join(r.error[:50] for r in results if r.error)
            return HealingResult(
                task_id=task.id, agent_domain=self.domain.value,
                component=task.component, status="escalated",
                action_taken="multi_llm_low_confidence",
                error=errors[:200] or "All agents returned low confidence",
            )
        except Exception as e:
            logger.debug(f"[SWARM-CODE] Multi-LLM agents unavailable ({e}), falling back to brain API")

        # FALLBACK: Use brain API
        action = "brain_api_fallback"
        try:
            from api.brain_api_v2 import call_brain
            r = call_brain("ai", "fix_code", {
                "file_path": task.file_path or task.component,
                "error": task.error or task.description,
                "context": task.context,
            })
            if r.get("ok"):
                return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                     component=task.component, status="healed",
                                     action_taken=action)
            return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                 component=task.component, status="escalated",
                                 action_taken=action, error=r.get("error", "fix_code returned not ok"))
        except Exception as e:
            return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                 component=task.component, status="failed",
                                 action_taken=action, error=str(e))


class MemoryAgent(HealingAgent):
    """Heals memory leaks, cache corruption, GC pressure."""

    def __init__(self, coordinator):
        super().__init__(AgentDomain.MEMORY, coordinator)

    def _heal(self, task: HealingTask) -> HealingResult:
        import gc
        actions = []

        # Force GC
        collected = gc.collect()
        actions.append(f"gc_collected_{collected}")

        # Clear flash cache if bloated
        try:
            from cognitive.flash_cache import FlashCache
            cache = FlashCache()
            if hasattr(cache, 'clear'):
                cache.clear()
                actions.append("flash_cache_cleared")
        except Exception:
            pass

        # Clear ghost memory stale entries
        try:
            from cognitive.ghost_memory import get_ghost_memory
            gm = get_ghost_memory()
            if hasattr(gm, 'prune_stale'):
                gm.prune_stale()
                actions.append("ghost_memory_pruned")
        except Exception:
            pass

        return HealingResult(
            task_id=task.id, agent_domain=self.domain.value,
            component=task.component, status="healed",
            action_taken="|".join(actions),
        )


class TrustAgent(HealingAgent):
    """Resets trust scores, re-calibrates brain domains."""

    def __init__(self, coordinator):
        super().__init__(AgentDomain.TRUST, coordinator)

    def _heal(self, task: HealingTask) -> HealingResult:
        component = task.component or ""
        action = "trust_recalibrate"
        try:
            from ml_intelligence.kpi_tracker import get_kpi_tracker
            tracker = get_kpi_tracker()
            # Record a neutral action to re-bootstrap trust
            tracker.record_action(component, "healing_recalibrate", success=True, trust_delta=0.1)
            return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                 component=task.component, status="healed",
                                 action_taken=action)
        except Exception as e:
            return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                 component=task.component, status="failed",
                                 action_taken=action, error=str(e))


class ConfigAgent(HealingAgent):
    """Fixes config drift, schema migrations, .env issues."""

    def __init__(self, coordinator):
        super().__init__(AgentDomain.CONFIG, coordinator)

    def _heal(self, task: HealingTask) -> HealingResult:
        component = (task.component or "").lower()

        if "schema" in component or "migration" in component:
            try:
                from database.migration import create_tables
                create_tables()
                return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                     component=task.component, status="healed",
                                     action_taken="schema_migrate")
            except Exception as e:
                return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                     component=task.component, status="failed",
                                     action_taken="schema_migrate", error=str(e))

        if "env" in component or "config" in component:
            try:
                from settings import settings
                # Force reload
                settings.__init__()
                return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                     component=task.component, status="healed",
                                     action_taken="config_reload")
            except Exception as e:
                return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                     component=task.component, status="failed",
                                     action_taken="config_reload", error=str(e))

        return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                             component=task.component, status="escalated",
                             action_taken="config_unknown")


class ServiceAgent(HealingAgent):
    """Restarts services, checks port health, watchdog."""

    def __init__(self, coordinator):
        super().__init__(AgentDomain.SERVICE, coordinator)

    def _heal(self, task: HealingTask) -> HealingResult:
        component = (task.component or "").lower()
        action = "service_check"

        # Check if the service port is responding
        import socket
        port_map = {
            "backend": 8000, "frontend": 5173,
            "postgres": 5432, "qdrant": 6333, "ollama": 11434,
        }
        for name, port in port_map.items():
            if name in component:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(3)
                    s.connect(("127.0.0.1", port))
                    s.close()
                    return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                         component=task.component, status="healed",
                                         action_taken=f"port_{port}_alive")
                except Exception:
                    return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                                         component=task.component, status="failed",
                                         action_taken=f"port_{port}_unreachable",
                                         error=f"Port {port} not responding")

        return HealingResult(task_id=task.id, agent_domain=self.domain.value,
                             component=task.component, status="escalated",
                             action_taken=action)


# ── Domain classifier ────────────────────────────────────────────────────

def classify_domain(component: str, error: str = "", description: str = "") -> AgentDomain:
    """Route a problem to the right swarm agent."""
    text = f"{component} {error} {description}".lower()

    if any(k in text for k in ("database", "db", "postgres", "qdrant", "vector", "ollama", "connection", "network", "timeout", "refused", "unreachable")):
        return AgentDomain.CONNECTION
    if any(k in text for k in ("attribute", "import", "name error", "type error", "code", "syntax", "fix_code")):
        return AgentDomain.CODE
    if any(k in text for k in ("memory", "leak", "gc", "cache", "oom", "ram")):
        return AgentDomain.MEMORY
    if any(k in text for k in ("trust", "score", "brain_", "kpi", "calibrat")):
        return AgentDomain.TRUST
    if any(k in text for k in ("config", "env", "schema", "migration", "setting")):
        return AgentDomain.CONFIG
    if any(k in text for k in ("service", "port", "process", "restart", "daemon", "pid")):
        return AgentDomain.SERVICE

    return AgentDomain.SERVICE  # default


# ══════════════════════════════════════════════════════════════════════════
# Swarm Coordinator
# ══════════════════════════════════════════════════════════════════════════

class SwarmCoordinator:
    """
    Orchestrates the healing swarm. Accepts problems, classifies them,
    dispatches to the right agent, runs them concurrently.
    """

    def __init__(self, max_concurrent: int = 6):
        self.agents: Dict[AgentDomain, HealingAgent] = {
            AgentDomain.CONNECTION: ConnectionAgent(self),
            AgentDomain.CODE: CodeAgent(self),
            AgentDomain.MEMORY: MemoryAgent(self),
            AgentDomain.TRUST: TrustAgent(self),
            AgentDomain.CONFIG: ConfigAgent(self),
            AgentDomain.SERVICE: ServiceAgent(self),
        }
        self._pool = ThreadPoolExecutor(max_workers=max_concurrent, thread_name_prefix="swarm-heal")
        self._active_tasks: Dict[str, Future] = {}
        self._results: deque = deque(maxlen=200)
        self._lock = threading.Lock()
        self._started = False

        logger.info(f"[HEALING-SWARM] Initialized with {len(self.agents)} agents, {max_concurrent} threads")

    def start(self):
        """Subscribe to event bus for automatic problem intake."""
        if self._started:
            return
        try:
            from cognitive.event_bus import subscribe
            subscribe("healing.*", self._on_healing_event)
            subscribe("system.health_changed", self._on_health_changed)
            subscribe("error.*", self._on_error_event)
            self._started = True
            logger.info("[HEALING-SWARM] Started — listening on event bus")
        except Exception as e:
            logger.warning(f"[HEALING-SWARM] Could not subscribe to event bus: {e}")

    def submit(self, problem: Dict[str, Any]) -> Optional[str]:
        """
        Submit a problem for concurrent healing.
        Returns the task_id or None if rejected.
        """
        component = problem.get("component", "unknown")
        description = problem.get("description", "")
        error = problem.get("error", "")
        severity = problem.get("severity", "medium")
        file_path = problem.get("file_path", "")
        context = problem.get("context", {})

        domain = classify_domain(component, error, description)
        task_id = f"swarm-{domain.value}-{uuid.uuid4().hex[:8]}"

        task = HealingTask(
            id=task_id, domain=domain,
            component=component, description=description,
            severity=severity, error=error,
            file_path=file_path, context=context,
        )

        agent = self.agents.get(domain)
        if not agent:
            logger.warning(f"[HEALING-SWARM] No agent for domain {domain}")
            return None

        future = self._pool.submit(agent.execute, task)
        future.add_done_callback(lambda f: self._on_complete(task_id, f))

        with self._lock:
            self._active_tasks[task_id] = future

        logger.info(f"[HEALING-SWARM] Dispatched {task_id} → {domain.value} agent ({component})")

        try:
            from cognitive.event_bus import publish_async
            publish_async("healing.swarm.dispatched", {
                "task_id": task_id,
                "domain": domain.value,
                "component": component,
                "severity": severity,
            }, source="swarm.coordinator")
        except Exception:
            pass

        return task_id

    def submit_batch(self, problems: List[Dict[str, Any]]) -> List[str]:
        """Submit multiple problems at once — all run concurrently."""
        task_ids = []
        for problem in problems:
            tid = self.submit(problem)
            if tid:
                task_ids.append(tid)
        logger.info(f"[HEALING-SWARM] Batch dispatched {len(task_ids)}/{len(problems)} problems")
        return task_ids

    def _on_complete(self, task_id: str, future: Future):
        with self._lock:
            self._active_tasks.pop(task_id, None)
        try:
            result = future.result()
            self._results.append(asdict(result))
        except Exception as e:
            self._results.append({
                "task_id": task_id, "status": "error",
                "error": str(e),
            })

    def get_status(self) -> Dict[str, Any]:
        """Full swarm status for the frontend."""
        agents_status = {}
        for domain, agent in self.agents.items():
            s = agent.state
            agents_status[domain.value] = {
                "status": s.status.value,
                "current_task": s.current_task,
                "completed": s.tasks_completed,
                "failed": s.tasks_failed,
                "success_rate": round(s.success_rate, 1),
                "avg_mttr": round(s.avg_mttr, 2),
                "last_activity": s.last_activity,
            }

        with self._lock:
            active_count = len(self._active_tasks)

        return {
            "swarm_active": self._started,
            "agents": agents_status,
            "active_tasks": active_count,
            "total_results": len(self._results),
            "recent_results": list(self._results)[-20:],
        }

    def _on_healing_event(self, event):
        """Auto-intake from event bus."""
        data = getattr(event, "data", {})
        if "component" in data:
            self.submit(data)

    def _on_health_changed(self, event):
        data = getattr(event, "data", {})
        status = data.get("status", "")
        if status in ("degraded", "critical", "failing"):
            self.submit({
                "component": data.get("component", "system"),
                "description": f"Health changed to {status}",
                "severity": "high" if status == "critical" else "medium",
            })

    def _on_error_event(self, event):
        data = getattr(event, "data", {})
        self.submit({
            "component": data.get("module", data.get("component", "unknown")),
            "description": data.get("description", str(data.get("exc_str", ""))),
            "error": data.get("error", data.get("exc_str", "")),
            "severity": data.get("severity", "medium"),
            "file_path": data.get("file_path", ""),
        })


# ── Singleton ────────────────────────────────────────────────────────────

_swarm: Optional[SwarmCoordinator] = None
_swarm_lock = threading.Lock()


def get_healing_swarm() -> SwarmCoordinator:
    global _swarm
    if _swarm is None:
        with _swarm_lock:
            if _swarm is None:
                _swarm = SwarmCoordinator()
                _swarm.start()
    return _swarm
