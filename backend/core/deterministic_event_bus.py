"""
Deterministic Event Bus
========================
Event-driven lifecycle with multiple entry points, async triggers,
and non-linear execution paths.

Instead of a linear pipeline (probe → scan → fix → heal), problems
can enter at ANY stage. Like Kafka/RabbitMQ but in-process, integrated
with both the Layer 1 message bus and cognitive event bus.

Entry Points (Topics):
  deterministic.component_registered  → REGISTER stage
  deterministic.probe_failed          → enters at PROBE → SCAN → FIX
  deterministic.problem_detected      → enters at SCAN → FIX
  deterministic.fix_needed            → enters at FIX → REASON → HEAL
  deterministic.heal_needed           → enters at HEAL
  deterministic.verify_needed         → enters at VERIFY → LOOP
  deterministic.code_change           → enters at SCAN (targeted)
  deterministic.service_down          → enters at HEAL (immediate)
  deterministic.genesis_error         → enters at SCAN → FIX

Any component can publish to any topic. The deterministic bus
routes to the correct handler and tracks everything via Genesis.
"""

import logging
import threading
import time
import queue
from collections import defaultdict
from typing import Dict, Any, Callable, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class EntryPoint(str, Enum):
    """Where a problem enters the deterministic lifecycle."""
    REGISTER = "register"
    PROBE = "probe"
    SCAN = "scan"
    FIX = "fix"
    REASON = "reason"
    HEAL = "heal"
    VERIFY = "verify"
    CODE_CHANGE = "code_change"
    SERVICE_DOWN = "service_down"
    GENESIS_ERROR = "genesis_error"


class Priority(int, Enum):
    CRITICAL = 1
    HIGH = 3
    NORMAL = 5
    LOW = 7
    BACKGROUND = 9


@dataclass
class DeterministicTask:
    """A task flowing through the deterministic event bus."""
    task_id: str
    entry_point: str
    component: str
    payload: Dict[str, Any]
    priority: int = Priority.NORMAL
    source: str = "unknown"
    created_at: str = ""
    status: str = "pending"  # pending, processing, completed, failed
    result: Optional[Dict[str, Any]] = None
    genesis_key_id: Optional[str] = None


# Topic → handler mapping
_handlers: Dict[str, List[Callable]] = defaultdict(list)
_task_queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=10000)
_task_log: List[Dict[str, Any]] = []
_log_lock = threading.Lock()
_MAX_LOG = 1000
_worker_running = False
_worker_lock = threading.Lock()


# ═══════════════════════════════════════════════════════════════════
#  TOPICS — All deterministic lifecycle entry points
# ═══════════════════════════════════════════════════════════════════

TOPICS = {
    "deterministic.component_registered": "New component discovered — register + initial probe",
    "deterministic.probe_failed": "Probe found component dead — enter scan → fix chain",
    "deterministic.problem_detected": "Problem detected by any scanner — enter fix chain",
    "deterministic.fix_needed": "Deterministic fix failed — escalate to LLM reasoning",
    "deterministic.heal_needed": "LLM reasoning done — execute healing action",
    "deterministic.verify_needed": "Healing done — verify the fix worked",
    "deterministic.code_change": "Code changed — re-scan the affected component",
    "deterministic.service_down": "Service unreachable — immediate heal attempt",
    "deterministic.genesis_error": "Genesis Key with is_error=True — enter scan",
    "deterministic.lifecycle_complete": "Full lifecycle finished — log and learn",
}


def subscribe(topic: str, handler: Callable):
    """Subscribe a handler to a deterministic topic."""
    _handlers[topic].append(handler)
    logger.debug(f"[DET-BUS] Subscribed to {topic}")


def publish(
    topic: str,
    component: str,
    payload: Dict[str, Any] = None,
    priority: int = Priority.NORMAL,
    source: str = "unknown",
    async_exec: bool = True,
) -> str:
    """
    Publish a problem/event to the deterministic bus.

    Problems enter at the appropriate lifecycle stage based on topic.
    If async_exec=True, the task is queued for background processing.
    If async_exec=False, it's processed immediately in the caller's thread.
    """
    task = DeterministicTask(
        task_id=f"DET-{int(time.time() * 1000)}-{threading.current_thread().ident % 1000:03d}",
        entry_point=topic.split(".")[-1] if "." in topic else topic,
        component=component,
        payload=payload or {},
        priority=priority,
        source=source,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    _track_genesis(task, topic)

    if async_exec:
        try:
            _task_queue.put_nowait((priority, time.time(), task))
        except queue.Full:
            logger.warning(f"[DET-BUS] Queue full, dropping task {task.task_id}")
            return task.task_id
        _ensure_worker()
    else:
        _process_task(task, topic)

    # Also bridge to cognitive event bus for cross-system visibility
    try:
        from cognitive.event_bus import publish_async as cog_publish
        cog_publish(topic, {
            "task_id": task.task_id,
            "component": component,
            "entry_point": task.entry_point,
            "priority": priority,
        }, source="deterministic_bus")
    except Exception:
        pass

    return task.task_id


def _process_task(task: DeterministicTask, topic: str):
    """Process a single task — invoke all handlers for the topic."""
    task.status = "processing"
    handlers = list(_handlers.get(topic, []))

    # Also get wildcard handlers
    handlers.extend(_handlers.get("deterministic.*", []))

    results = []
    for handler in handlers:
        try:
            result = handler(task)
            if result:
                results.append(result)
        except Exception as e:
            logger.warning(f"[DET-BUS] Handler error for {topic}: {e}")
            results.append({"error": str(e)[:200]})

    # If no specific handlers, use default routing
    if not handlers:
        result = _default_route(task)
        if result:
            results.append(result)

    task.status = "completed"
    task.result = {"handler_results": results, "handlers_invoked": len(handlers) + (1 if not handlers else 0)}

    with _log_lock:
        _task_log.append(asdict(task))
        if len(_task_log) > _MAX_LOG:
            _task_log[:] = _task_log[-_MAX_LOG:]


def _default_route(task: DeterministicTask) -> Optional[Dict[str, Any]]:
    """
    Default routing when no specific handler is registered.
    Routes based on entry point to the appropriate lifecycle stage.
    """
    entry = task.entry_point

    try:
        from core.deterministic_lifecycle import (
            probe_component, scan_component, fix_deterministic,
            reason_with_llm, heal_component, run_lifecycle,
            _registry, register_component,
        )

        comp = task.component
        if comp not in _registry:
            register_component(comp, comp, file_path=task.payload.get("file_path"))

        if entry in ("component_registered", "probe"):
            probe = probe_component(comp)
            if not probe["alive"]:
                publish("deterministic.problem_detected", comp,
                        {"probe_error": probe.get("error", ""), **task.payload},
                        priority=Priority.HIGH, source="default_route", async_exec=False)
            return probe

        if entry in ("probe_failed", "problem_detected", "scan", "code_change", "genesis_error"):
            scan = scan_component(comp)
            if scan["total_problems"] > 0:
                det_fix = fix_deterministic(comp, scan["problems"])
                if det_fix["unfixed"]:
                    publish("deterministic.fix_needed", comp,
                            {"unfixed": det_fix["unfixed"], **task.payload},
                            priority=Priority.HIGH, source="default_route", async_exec=False)
                return {"scan": scan, "deterministic_fix": det_fix}
            return scan

        if entry == "fix_needed":
            unfixed = task.payload.get("unfixed", [])
            llm = reason_with_llm(comp, unfixed)
            if llm.get("fix_suggestion"):
                publish("deterministic.heal_needed", comp,
                        {"llm_reasoning": llm, "problems": unfixed, **task.payload},
                        priority=Priority.HIGH, source="default_route", async_exec=False)
            return llm

        if entry in ("heal_needed", "service_down"):
            problems = task.payload.get("problems", [{"type": "service_down", "message": str(task.payload)}])
            llm = task.payload.get("llm_reasoning")
            heal = heal_component(comp, problems, llm)
            publish("deterministic.verify_needed", comp,
                    {"healed": heal.get("healed", False), **task.payload},
                    priority=Priority.NORMAL, source="default_route", async_exec=False)
            return heal

        if entry == "verify_needed":
            probe = probe_component(comp)
            if not probe["alive"] and task.payload.get("healed"):
                # Re-enter the lifecycle recursively
                result = run_lifecycle(comp, max_iterations=3)
                return result.to_dict()
            return probe

    except Exception as e:
        logger.error(f"[DET-BUS] Default route error for {entry}/{task.component}: {e}")
        return {"error": str(e)[:200]}

    return None


def _track_genesis(task: DeterministicTask, topic: str):
    """Track the task via Genesis Key."""
    try:
        from api._genesis_tracker import track
        result = track(
            key_type="system_event",
            what=f"[DET-BUS] {topic}: {task.component}",
            who="deterministic_event_bus",
            how=f"entry_point={task.entry_point}",
            output_data={"task_id": task.task_id, "priority": task.priority},
            tags=["deterministic", "event_bus", task.entry_point, task.component],
        )
        if result and hasattr(result, "key_id"):
            task.genesis_key_id = result.key_id
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
#  BACKGROUND WORKER — processes queued tasks by priority
# ═══════════════════════════════════════════════════════════════════

def _ensure_worker():
    """Start the background worker if not already running."""
    global _worker_running
    with _worker_lock:
        if not _worker_running:
            _worker_running = True
            t = threading.Thread(target=_worker_loop, daemon=True)
            t.start()


def _worker_loop():
    """Process tasks from the priority queue."""
    global _worker_running
    while True:
        try:
            priority, ts, task = _task_queue.get(timeout=5)
            topic = f"deterministic.{task.entry_point}"
            _process_task(task, topic)
            _task_queue.task_done()
        except queue.Empty:
            with _worker_lock:
                if _task_queue.empty():
                    _worker_running = False
                    return


# ═══════════════════════════════════════════════════════════════════
#  BRIDGE — Connect to Layer 1 and cognitive event bus
# ═══════════════════════════════════════════════════════════════════

def bridge_to_cognitive_bus():
    """
    Subscribe to existing cognitive event bus topics and route
    relevant events into the deterministic bus.
    """
    try:
        from cognitive.event_bus import subscribe as cog_subscribe

        def _on_genesis_error(event):
            data = event.data or {}
            if data.get("is_error") or data.get("key_type") == "error":
                publish("deterministic.genesis_error",
                        data.get("component", data.get("who_actor", "unknown")),
                        data, priority=Priority.HIGH, source="genesis_bridge")

        def _on_health_changed(event):
            data = event.data or {}
            if data.get("new_status") in ("red", "critical", "dead"):
                publish("deterministic.service_down",
                        data.get("component_id", "unknown"),
                        data, priority=Priority.CRITICAL, source="health_bridge")

        def _on_code_change(event):
            data = event.data or {}
            publish("deterministic.code_change",
                    data.get("component", data.get("file", "unknown")),
                    data, priority=Priority.NORMAL, source="code_bridge")

        def _on_healing_failed(event):
            data = event.data or {}
            publish("deterministic.fix_needed",
                    data.get("component", "unknown"),
                    data, priority=Priority.HIGH, source="healing_bridge")

        cog_subscribe("genesis.error", _on_genesis_error)
        cog_subscribe("genesis.ERROR", _on_genesis_error)
        cog_subscribe("system.health_changed", _on_health_changed)
        cog_subscribe("file.changed", _on_code_change)
        cog_subscribe("healing.failed", _on_healing_failed)

        logger.info("[DET-BUS] Bridged to cognitive event bus")
    except Exception as e:
        logger.debug(f"[DET-BUS] Cognitive bus bridge failed: {e}")


def bridge_to_genesis_realtime():
    """Subscribe to Genesis realtime engine for error key events."""
    try:
        from genesis.realtime import get_realtime_engine
        engine = get_realtime_engine()
        engine.watch("__error__", lambda key_data: publish(
            "deterministic.genesis_error",
            key_data.get("who_actor", "unknown"),
            key_data, priority=Priority.HIGH, source="genesis_realtime",
        ))
        logger.info("[DET-BUS] Bridged to Genesis realtime engine")
    except Exception as e:
        logger.debug(f"[DET-BUS] Genesis realtime bridge failed: {e}")


def initialize_bridges():
    """Initialize all bridges to external event sources."""
    bridge_to_cognitive_bus()
    bridge_to_genesis_realtime()
    logger.info("[DET-BUS] All bridges initialized")


# ═══════════════════════════════════════════════════════════════════
#  ACCESSORS
# ═══════════════════════════════════════════════════════════════════

def get_task_log(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent task log."""
    with _log_lock:
        return list(reversed(_task_log[-limit:]))


def get_bus_stats() -> Dict[str, Any]:
    """Get deterministic event bus statistics."""
    with _log_lock:
        tasks = list(_task_log)

    by_entry = defaultdict(int)
    by_component = defaultdict(int)
    by_status = defaultdict(int)
    for t in tasks:
        by_entry[t.get("entry_point", "unknown")] += 1
        by_component[t.get("component", "unknown")] += 1
        by_status[t.get("status", "unknown")] += 1

    return {
        "total_tasks": len(tasks),
        "queue_size": _task_queue.qsize(),
        "worker_running": _worker_running,
        "topics_registered": len(_handlers),
        "by_entry_point": dict(by_entry),
        "by_component": dict(by_component),
        "by_status": dict(by_status),
        "available_topics": TOPICS,
    }
