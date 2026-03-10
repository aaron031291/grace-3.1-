"""
Agentic Runner — Background task spawner for all brain domains.

Allows any brain action to be submitted as a non-blocking agentic task.
Results are stored in-memory (with optional persistence) and polled via task_id.

Usage from any brain:
    spawn_task(brain="deterministic", action="scan", payload={})
    → returns {"task_id": "task_abc123", "status": "queued"}

Then poll:
    get_task(task_id)
    → returns {"task_id": "...", "status": "done", "result": {...}, "elapsed_ms": 1500}
"""

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

TASK_TTL_SECONDS = 3600  # Keep task results for 1 hour


@dataclass
class AgentTask:
    task_id: str
    brain: str
    action: str
    payload: Dict[str, Any]
    status: str = "queued"        # queued | running | done | error
    result: Optional[Any] = None
    error: Optional[str] = None
    queued_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    elapsed_ms: Optional[float] = None


class AgentTaskRunner:
    """
    In-process thread-pool based agentic task runner.
    All brain actions can be dispatched here to run asynchronously.
    """

    def __init__(self, max_workers: int = 4):
        self._tasks: Dict[str, AgentTask] = {}
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(max_workers)

    def spawn(self, brain: str, action: str, payload: Dict[str, Any]) -> str:
        """Spawn a brain action as a background task. Returns task_id."""
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        task = AgentTask(
            task_id=task_id,
            brain=brain,
            action=action,
            payload=payload,
            queued_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._tasks[task_id] = task

        thread = threading.Thread(target=self._run_task, args=(task_id,), daemon=True)
        thread.start()

        logger.info("[Agent] Spawned task %s → %s/%s", task_id, brain, action)
        return task_id

    def _run_task(self, task_id: str):
        """Worker thread: acquires semaphore, calls the brain, stores result."""
        with self._semaphore:
            with self._lock:
                task = self._tasks.get(task_id)
                if not task:
                    return
                task.status = "running"
                task.started_at = datetime.now(timezone.utc).isoformat()

            start = time.time()
            try:
                from api.brain_api_v2 import call_brain
                result = call_brain(task.brain, task.action, task.payload)
                elapsed = (time.time() - start) * 1000
                with self._lock:
                    task.result = result
                    task.status = "done"
                    task.elapsed_ms = round(elapsed, 1)
                    task.completed_at = datetime.now(timezone.utc).isoformat()
                logger.info("[Agent] Task %s done in %.0fms", task_id, elapsed)
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                with self._lock:
                    task.error = str(e)[:500]
                    task.status = "error"
                    task.elapsed_ms = round(elapsed, 1)
                    task.completed_at = datetime.now(timezone.utc).isoformat()
                logger.error("[Agent] Task %s failed: %s", task_id, e)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status and result. Returns None if not found."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            return {
                "task_id": task.task_id,
                "brain": task.brain,
                "action": task.action,
                "status": task.status,
                "result": task.result,
                "error": task.error,
                "queued_at": task.queued_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "elapsed_ms": task.elapsed_ms,
            }

    def list_tasks(self, brain: Optional[str] = None, limit: int = 30) -> list:
        """List recent tasks, optionally filter by brain."""
        with self._lock:
            tasks = list(self._tasks.values())
        if brain:
            tasks = [t for t in tasks if t.brain == brain]
        tasks = sorted(tasks, key=lambda t: t.queued_at, reverse=True)[:limit]
        return [
            {
                "task_id": t.task_id,
                "brain": t.brain,
                "action": t.action,
                "status": t.status,
                "queued_at": t.queued_at,
                "elapsed_ms": t.elapsed_ms,
            }
            for t in tasks
        ]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a queued task. Cannot cancel already-running tasks."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == "queued":
                task.status = "cancelled"
                return True
        return False

    def cleanup_old(self):
        """Remove completed tasks older than TTL."""
        cutoff = time.time() - TASK_TTL_SECONDS
        with self._lock:
            to_delete = []
            for tid, task in self._tasks.items():
                if task.status in ("done", "error", "cancelled") and task.queued_at:
                    try:
                        task_time = datetime.fromisoformat(task.queued_at).timestamp()
                        if task_time < cutoff:
                            to_delete.append(tid)
                    except Exception:
                        pass
            for tid in to_delete:
                del self._tasks[tid]


_runner: Optional[AgentTaskRunner] = None


def get_agent_runner() -> AgentTaskRunner:
    global _runner
    if _runner is None:
        _runner = AgentTaskRunner(max_workers=4)
    return _runner


def spawn_task(brain: str, action: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
    """Public API: spawn a brain action as a background agentic task."""
    task_id = get_agent_runner().spawn(brain, action, payload or {})
    return {"task_id": task_id, "status": "queued", "brain": brain, "action": action}


def get_task(task_id: str) -> Dict[str, Any]:
    """Public API: get task status and result."""
    r = get_agent_runner().get_task(task_id)
    if not r:
        return {"error": "task not found", "task_id": task_id}
    return r


def list_tasks(brain: str = None, limit: int = 30) -> list:
    """Public API: list recent tasks."""
    return get_agent_runner().list_tasks(brain=brain, limit=limit)
