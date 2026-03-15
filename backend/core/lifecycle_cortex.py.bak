"""
Lifecycle Cortex — Grace's Boot Sequencer, Readiness Gate, and Health Unifier.

Solves 5 problems at once:
  1. Dependency-aware startup (topological sort, no more sequential try/except)
  2. Readiness gates (subsystems declare "I need X before I start")
  3. Unified health model (one truth store, not 3 redundant monitors)
  4. Scheduled maintenance jobs (memory consolidation, mesh reconciliation)
  5. Feedback correlation (decision_id across consensus → execute → learn → trust)

Design rules:
  - Cortex COORDINATES, it does not absorb domain behavior
  - Memory merge logic stays in memory modules (registered as jobs)
  - Healing decisions stay in healing modules (subscribe to health events)
  - Consensus/trust math stays in their modules (cortex just correlates events)
  - Imports are lazy (inside factories) to prevent import cycles
"""

import asyncio
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class StartPolicy(str, Enum):
    BLOCKING = "blocking"       # Must be ready before API accepts traffic
    BACKGROUND = "background"   # Start after core boot, non-blocking
    LAZY = "lazy"               # Init on first access only


class LifecycleState(str, Enum):
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class SubsystemSpec:
    """Declaration of a subsystem that the cortex manages."""
    name: str
    factory: Callable[[], Any]
    dependencies: Set[str] = field(default_factory=set)
    ready_check: Optional[Callable[[Any], bool]] = None
    health_check: Optional[Callable[[Any], dict]] = None
    shutdown: Optional[Callable[[Any], None]] = None
    start_policy: StartPolicy = StartPolicy.BLOCKING
    critical: bool = True
    timeout_s: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SubsystemEntry:
    """Runtime state of a managed subsystem."""
    spec: SubsystemSpec
    state: LifecycleState = LifecycleState.REGISTERED
    instance: Any = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    ready_at: Optional[str] = None
    last_health_check: Optional[str] = None
    last_health_result: Optional[dict] = None
    health_ttl_s: float = 60.0  # Health result considered stale after this


@dataclass
class MaintenanceJob:
    """A periodic job managed by the cortex."""
    name: str
    handler: Callable[[], Any]
    requires: Set[str] = field(default_factory=set)
    interval_s: float = 300.0
    overlap_policy: str = "skip"  # "skip" or "queue"
    last_run: Optional[str] = None
    running: bool = False
    run_count: int = 0
    last_error: Optional[str] = None


# =============================================================================
# LIFECYCLE CORTEX
# =============================================================================

class LifecycleCortex:
    """
    Grace's boot sequencer, readiness gate, and health unifier.

    Usage:
        cortex = get_lifecycle_cortex()

        cortex.register(SubsystemSpec(
            name="database",
            factory=lambda: initialize_db(),
            ready_check=lambda db: db.is_connected(),
            health_check=lambda db: {"connected": db.is_connected()},
        ))

        cortex.register(SubsystemSpec(
            name="llm",
            factory=lambda: get_llm_client(),
            dependencies={"database"},
            start_policy=StartPolicy.BACKGROUND,
        ))

        # Boot core systems
        cortex.start_blocking()

        # Boot background systems
        cortex.start_background()

        # Access managed instances
        db = cortex.get("database")

        # Wait for a dependency
        cortex.wait_ready("llm", timeout=30)
    """

    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._subsystems: Dict[str, SubsystemEntry] = {}
        self._jobs: Dict[str, MaintenanceJob] = {}
        self._lock = threading.RLock()
        self._ready_events: Dict[str, threading.Event] = {}
        self._job_thread: Optional[threading.Thread] = None
        self._shutdown_flag = threading.Event()

        # Feedback correlation: track decision chains
        self._decision_chains: Dict[str, Dict[str, Any]] = {}
        self._max_chains = 500

    @classmethod
    def get_instance(cls) -> "LifecycleCortex":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # =========================================================================
    # REGISTRATION
    # =========================================================================

    def register(self, spec: SubsystemSpec) -> None:
        """Register a subsystem spec. Must be called before start_*."""
        with self._lock:
            if spec.name in self._subsystems:
                logger.warning(f"[CORTEX] Already registered: {spec.name}")
                return

            self._subsystems[spec.name] = SubsystemEntry(spec=spec)
            self._ready_events[spec.name] = threading.Event()

            logger.info(
                f"[CORTEX] Registered: {spec.name} "
                f"(deps={spec.dependencies or 'none'}, policy={spec.start_policy.value})"
            )

    def register_job(
        self,
        name: str,
        handler: Callable,
        requires: Set[str] = None,
        interval_s: float = 300.0,
        overlap_policy: str = "skip",
    ) -> None:
        """Register a periodic maintenance job."""
        with self._lock:
            self._jobs[name] = MaintenanceJob(
                name=name,
                handler=handler,
                requires=requires or set(),
                interval_s=interval_s,
                overlap_policy=overlap_policy,
            )
            logger.info(f"[CORTEX] Job registered: {name} (every {interval_s}s)")

    # =========================================================================
    # STARTUP
    # =========================================================================

    def start_blocking(self) -> Dict[str, str]:
        """Start all BLOCKING subsystems in dependency order. Returns status map."""
        return self._start_by_policy(StartPolicy.BLOCKING)

    def start_background(self) -> None:
        """Start BACKGROUND subsystems in a daemon thread, then start job scheduler."""
        def _bg():
            self._start_by_policy(StartPolicy.BACKGROUND)
            self._start_job_scheduler()

        t = threading.Thread(target=_bg, daemon=True, name="cortex-background")
        t.start()

    def _start_by_policy(self, policy: StartPolicy) -> Dict[str, str]:
        """Start subsystems matching a policy in dependency order."""
        targets = [
            name for name, entry in self._subsystems.items()
            if entry.spec.start_policy == policy
        ]

        ordered = self._topo_sort(targets)
        results = {}

        for name in ordered:
            result = self._start_one(name)
            results[name] = result

        return results

    def _start_one(self, name: str) -> str:
        """Initialize a single subsystem, waiting for its dependencies."""
        entry = self._subsystems.get(name)
        if not entry:
            return "not_found"

        if entry.state in (LifecycleState.READY, LifecycleState.INITIALIZING):
            return entry.state.value

        # Wait for dependencies
        for dep in entry.spec.dependencies:
            if dep not in self._subsystems:
                logger.warning(f"[CORTEX] {name}: unknown dependency '{dep}', skipping wait")
                continue
            if not self.wait_ready(dep, timeout=entry.spec.timeout_s):
                msg = f"Dependency '{dep}' not ready within {entry.spec.timeout_s}s"
                logger.error(f"[CORTEX] {name}: {msg}")
                entry.state = LifecycleState.FAILED
                entry.error = msg
                self._publish_lifecycle_event(name, "failed", {"error": msg})
                return "dependency_timeout"

        # Initialize
        entry.state = LifecycleState.INITIALIZING
        entry.started_at = datetime.now(timezone.utc).isoformat()

        try:
            entry.instance = entry.spec.factory()

            # Run ready check if provided
            if entry.spec.ready_check:
                if not entry.spec.ready_check(entry.instance):
                    entry.state = LifecycleState.DEGRADED
                    entry.error = "ready_check returned False"
                    self._publish_lifecycle_event(name, "degraded", {"reason": "ready_check_false"})
                    return "degraded"

            entry.state = LifecycleState.READY
            entry.ready_at = datetime.now(timezone.utc).isoformat()
            entry.error = None

            # Signal readiness
            event = self._ready_events.get(name)
            if event:
                event.set()

            self._publish_lifecycle_event(name, "ready", {})
            logger.info(f"[CORTEX] ✓ {name} ready")
            return "ready"

        except Exception as e:
            entry.state = LifecycleState.FAILED
            entry.error = str(e)[:500]
            self._publish_lifecycle_event(name, "failed", {"error": str(e)[:500]})

            if entry.spec.critical:
                logger.error(f"[CORTEX] ✗ {name} FAILED (critical): {e}")
            else:
                logger.warning(f"[CORTEX] ✗ {name} failed (non-critical): {e}")

            return "failed"

    # =========================================================================
    # READINESS GATES
    # =========================================================================

    def is_ready(self, name: str) -> bool:
        """Check if a subsystem is ready (non-blocking)."""
        entry = self._subsystems.get(name)
        return entry is not None and entry.state == LifecycleState.READY

    def wait_ready(self, name: str, timeout: float = 30.0) -> bool:
        """Block until a subsystem is ready, or timeout."""
        event = self._ready_events.get(name)
        if event is None:
            return False
        return event.wait(timeout=timeout)

    async def await_ready(self, name: str, timeout: float = 30.0) -> bool:
        """Async readiness gate."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.wait_ready, name, timeout)

    def get(self, name: str) -> Any:
        """Get a managed subsystem instance. Initializes LAZY subsystems on first access."""
        entry = self._subsystems.get(name)
        if entry is None:
            return None

        if entry.state == LifecycleState.REGISTERED and entry.spec.start_policy == StartPolicy.LAZY:
            self._start_one(name)

        return entry.instance

    # =========================================================================
    # UNIFIED HEALTH
    # =========================================================================

    def run_health_checks(self) -> Dict[str, dict]:
        """Run health checks for all registered subsystems. Returns per-subsystem results."""
        results = {}
        now = datetime.now(timezone.utc)

        for name, entry in self._subsystems.items():
            if entry.spec.health_check and entry.instance is not None:
                try:
                    result = entry.spec.health_check(entry.instance)
                    entry.last_health_check = now.isoformat()
                    entry.last_health_result = result
                    results[name] = {
                        "status": entry.state.value,
                        "health": result,
                        "checked_at": now.isoformat(),
                        "stale": False,
                    }
                except Exception as e:
                    entry.last_health_check = now.isoformat()
                    entry.last_health_result = {"error": str(e)[:200]}
                    entry.state = LifecycleState.DEGRADED
                    results[name] = {
                        "status": "degraded",
                        "health": {"error": str(e)[:200]},
                        "checked_at": now.isoformat(),
                        "stale": False,
                    }
            else:
                # No health check or no instance — report state only
                stale = False
                if entry.last_health_check:
                    age = (now - datetime.fromisoformat(entry.last_health_check)).total_seconds()
                    stale = age > entry.health_ttl_s

                results[name] = {
                    "status": entry.state.value,
                    "health": entry.last_health_result,
                    "checked_at": entry.last_health_check,
                    "stale": stale,
                }

        return results

    def get_health_snapshot(self) -> Dict[str, Any]:
        """Compact health snapshot — the single source of truth for system health."""
        health = self.run_health_checks()

        counts = defaultdict(int)
        for info in health.values():
            counts[info["status"]] += 1

        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "total": len(health),
            "ready": counts.get("ready", 0),
            "degraded": counts.get("degraded", 0),
            "failed": counts.get("failed", 0),
            "initializing": counts.get("initializing", 0),
            "registered": counts.get("registered", 0),
            "subsystems": health,
        }

    # =========================================================================
    # SCHEDULED MAINTENANCE JOBS
    # =========================================================================

    def _start_job_scheduler(self):
        """Start the background job scheduler."""
        if self._job_thread and self._job_thread.is_alive():
            return

        def _scheduler_loop():
            logger.info(f"[CORTEX] Job scheduler started ({len(self._jobs)} jobs)")
            while not self._shutdown_flag.is_set():
                now = time.time()
                for name, job in list(self._jobs.items()):
                    # Check if it's time to run
                    if job.last_run:
                        elapsed = now - datetime.fromisoformat(job.last_run).timestamp()
                        if elapsed < job.interval_s:
                            continue

                    # Check overlap policy
                    if job.running and job.overlap_policy == "skip":
                        continue

                    # Check dependencies
                    deps_ready = all(self.is_ready(dep) for dep in job.requires)
                    if not deps_ready:
                        continue

                    # Run job
                    job.running = True
                    try:
                        job.handler()
                        job.run_count += 1
                        job.last_error = None
                    except Exception as e:
                        job.last_error = str(e)[:300]
                        logger.warning(f"[CORTEX] Job '{name}' failed: {e}")
                    finally:
                        job.running = False
                        job.last_run = datetime.now(timezone.utc).isoformat()

                self._shutdown_flag.wait(timeout=15)  # Check every 15s

        self._job_thread = threading.Thread(
            target=_scheduler_loop, daemon=True, name="cortex-jobs"
        )
        self._job_thread.start()

    # =========================================================================
    # FEEDBACK CORRELATION
    # =========================================================================

    def open_decision_chain(self, decision_id: str, data: Dict[str, Any]) -> None:
        """Start tracking a decision through consensus → execute → learn → trust."""
        with self._lock:
            self._decision_chains[decision_id] = {
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "stages": {"consensus": data},
                "status": "open",
            }
            # Evict oldest if over limit
            if len(self._decision_chains) > self._max_chains:
                oldest = next(iter(self._decision_chains))
                del self._decision_chains[oldest]

    def update_decision_chain(self, decision_id: str, stage: str, data: Dict[str, Any]) -> None:
        """Record a stage completion (execution, learning, trust_update)."""
        with self._lock:
            chain = self._decision_chains.get(decision_id)
            if chain is None:
                # Late arrival — create a partial chain
                chain = {
                    "opened_at": datetime.now(timezone.utc).isoformat(),
                    "stages": {},
                    "status": "partial",
                }
                self._decision_chains[decision_id] = chain

            chain["stages"][stage] = {
                **data,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }

            # Check if chain is complete
            expected = {"consensus", "execution", "learning", "trust_update"}
            if expected.issubset(chain["stages"].keys()):
                chain["status"] = "complete"
                self._publish_lifecycle_event("feedback_loop", "chain_complete", {
                    "decision_id": decision_id,
                    "stages": list(chain["stages"].keys()),
                })

    def get_incomplete_chains(self) -> List[Dict[str, Any]]:
        """Find decision chains that haven't completed all stages."""
        with self._lock:
            incomplete = []
            for did, chain in self._decision_chains.items():
                if chain["status"] != "complete":
                    incomplete.append({
                        "decision_id": did,
                        "status": chain["status"],
                        "stages": list(chain["stages"].keys()),
                        "opened_at": chain["opened_at"],
                    })
            return incomplete

    # =========================================================================
    # STATE SNAPSHOT
    # =========================================================================

    def get_snapshot(self) -> Dict[str, Any]:
        """Full cortex state snapshot."""
        subsystems = {}
        for name, entry in self._subsystems.items():
            subsystems[name] = {
                "state": entry.state.value,
                "policy": entry.spec.start_policy.value,
                "critical": entry.spec.critical,
                "dependencies": list(entry.spec.dependencies),
                "started_at": entry.started_at,
                "ready_at": entry.ready_at,
                "error": entry.error,
            }

        jobs = {}
        for name, job in self._jobs.items():
            jobs[name] = {
                "interval_s": job.interval_s,
                "requires": list(job.requires),
                "last_run": job.last_run,
                "run_count": job.run_count,
                "running": job.running,
                "last_error": job.last_error,
            }

        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "subsystems": subsystems,
            "jobs": jobs,
            "incomplete_chains": len(self.get_incomplete_chains()),
        }

    # =========================================================================
    # SHUTDOWN
    # =========================================================================

    def shutdown(self) -> None:
        """Graceful shutdown of all subsystems in reverse dependency order."""
        self._shutdown_flag.set()
        logger.info("[CORTEX] Shutting down...")

        # Reverse order
        all_names = list(self._subsystems.keys())
        ordered = self._topo_sort(all_names)
        ordered.reverse()

        for name in ordered:
            entry = self._subsystems.get(name)
            if entry and entry.instance and entry.spec.shutdown:
                try:
                    entry.spec.shutdown(entry.instance)
                    entry.state = LifecycleState.STOPPED
                    logger.info(f"[CORTEX] Stopped: {name}")
                except Exception as e:
                    logger.warning(f"[CORTEX] Shutdown error for {name}: {e}")

    # =========================================================================
    # INTERNALS
    # =========================================================================

    def _topo_sort(self, names: List[str]) -> List[str]:
        """Topological sort with cycle detection."""
        name_set = set(names)
        visited = set()
        temp_mark = set()
        result = []

        def visit(n):
            if n in temp_mark:
                raise ValueError(f"Circular dependency detected involving '{n}'")
            if n in visited:
                return
            temp_mark.add(n)

            entry = self._subsystems.get(n)
            if entry:
                for dep in entry.spec.dependencies:
                    if dep in name_set:
                        visit(dep)
                    elif dep in self._subsystems:
                        # Dependency exists but wasn't in our target set — still visit
                        visit(dep)

            temp_mark.discard(n)
            visited.add(n)
            result.append(n)

        for name in names:
            if name not in visited:
                try:
                    visit(name)
                except ValueError as e:
                    logger.error(f"[CORTEX] {e}")
                    # Still add it — log error but don't deadlock
                    if name not in visited:
                        visited.add(name)
                        result.append(name)

        return result

    def _publish_lifecycle_event(self, subsystem: str, event_type: str, data: dict):
        """Publish lifecycle events to the cognitive event bus."""
        try:
            from cognitive.event_bus import publish_async
            publish_async(f"lifecycle.{event_type}", {
                "subsystem": subsystem,
                **data,
            }, source="lifecycle_cortex")
        except Exception:
            pass


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

def get_lifecycle_cortex() -> LifecycleCortex:
    """Get the singleton Lifecycle Cortex instance."""
    return LifecycleCortex.get_instance()
