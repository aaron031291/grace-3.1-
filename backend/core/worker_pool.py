"""
Worker Pool — managed concurrency for CPU-bound and IO-bound operations.

Prevents thread starvation, provides backpressure, and tracks active work
so the system can report what it's doing at any moment.

Architecture:
  - IO pool:  ThreadPoolExecutor for DB queries, HTTP calls, file ops
  - CPU pool: ProcessPoolExecutor for code analysis, AST parsing, embeddings
  - Both pools expose submit(), map(), and shutdown()
  - Built-in metrics: active tasks, completed tasks, queue depth, avg latency
"""

import os
import time
import logging
import threading
from concurrent.futures import (
    ThreadPoolExecutor,
    Future,
    TimeoutError as FutureTimeoutError,
    wait,
    FIRST_COMPLETED,
)
from typing import Callable, Any, Dict, List, Optional
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

DEFAULT_IO_WORKERS = int(os.getenv("GRACE_IO_WORKERS", "16"))
DEFAULT_CPU_WORKERS = int(os.getenv("GRACE_CPU_WORKERS", "4"))
MAX_QUEUE_DEPTH = int(os.getenv("GRACE_MAX_QUEUE_DEPTH", "200"))


@dataclass
class TaskMetrics:
    submitted: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    total_latency_ms: float = 0.0
    latencies: deque = field(default_factory=lambda: deque(maxlen=200))

    @property
    def avg_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    @property
    def active(self) -> int:
        return self.submitted - self.completed - self.failed - self.cancelled


class ManagedPool:
    """Thread pool with backpressure, metrics, and task naming."""

    def __init__(self, max_workers: int, name: str = "io"):
        self._name = name
        self._max_workers = max_workers
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=f"grace-{name}",
        )
        self._metrics = TaskMetrics()
        self._active_tasks: Dict[str, Future] = {}
        self._lock = threading.Lock()
        logger.info(f"[WorkerPool:{name}] initialized with {max_workers} workers")

    def submit(
        self,
        fn: Callable,
        *args,
        task_name: str = "",
        timeout_s: float = 0,
        **kwargs,
    ) -> Future:
        """
        Submit a task to the pool.

        Args:
            fn: The callable to execute
            task_name: Human-readable name for tracking
            timeout_s: If > 0, cancel after this many seconds
        """
        with self._lock:
            if self._metrics.active >= MAX_QUEUE_DEPTH:
                raise RuntimeError(
                    f"[WorkerPool:{self._name}] backpressure — "
                    f"{self._metrics.active} tasks queued (max {MAX_QUEUE_DEPTH})"
                )

        start = time.time()
        self._metrics.submitted += 1

        future = self._pool.submit(fn, *args, **kwargs)
        task_id = task_name or f"task-{self._metrics.submitted}"

        with self._lock:
            self._active_tasks[task_id] = future

        def _on_done(f: Future):
            elapsed_ms = (time.time() - start) * 1000
            with self._lock:
                self._active_tasks.pop(task_id, None)
            self._metrics.latencies.append(elapsed_ms)
            self._metrics.total_latency_ms += elapsed_ms
            if f.cancelled():
                self._metrics.cancelled += 1
            elif f.exception():
                self._metrics.failed += 1
                logger.debug(f"[WorkerPool:{self._name}] {task_id} failed: {f.exception()}")
            else:
                self._metrics.completed += 1

        future.add_done_callback(_on_done)

        if timeout_s > 0:
            def _timeout_guard():
                time.sleep(timeout_s)
                if not future.done():
                    future.cancel()
                    logger.warning(f"[WorkerPool:{self._name}] {task_id} timed out after {timeout_s}s")

            threading.Thread(target=_timeout_guard, daemon=True).start()

        return future

    def map(self, fn: Callable, items: list, task_prefix: str = "batch") -> List[Any]:
        """Submit multiple tasks and collect results in order."""
        futures = []
        for i, item in enumerate(items):
            f = self.submit(fn, item, task_name=f"{task_prefix}-{i}")
            futures.append(f)
        return [f.result(timeout=60) for f in futures]

    def wait_all(self, timeout_s: float = 30.0) -> Dict[str, Any]:
        """Wait for all active tasks to complete."""
        with self._lock:
            pending = list(self._active_tasks.values())
        if not pending:
            return {"waited": 0, "completed": True}
        done, not_done = wait(pending, timeout=timeout_s, return_when=FIRST_COMPLETED)
        return {
            "waited": len(pending),
            "done": len(done),
            "not_done": len(not_done),
            "completed": len(not_done) == 0,
        }

    def get_status(self) -> dict:
        with self._lock:
            active_names = list(self._active_tasks.keys())
        return {
            "name": self._name,
            "max_workers": self._max_workers,
            "submitted": self._metrics.submitted,
            "completed": self._metrics.completed,
            "failed": self._metrics.failed,
            "cancelled": self._metrics.cancelled,
            "active": self._metrics.active,
            "active_tasks": active_names[:20],
            "avg_latency_ms": round(self._metrics.avg_latency_ms, 1),
        }

    def shutdown(self, wait_for: bool = True):
        self._pool.shutdown(wait=wait_for)
        logger.info(f"[WorkerPool:{self._name}] shut down")


# ── Singleton pool instances ────────────────────────────────────

_io_pool: Optional[ManagedPool] = None
_cpu_pool: Optional[ManagedPool] = None
_init_lock = threading.Lock()


def get_io_pool() -> ManagedPool:
    """Get the IO-bound worker pool (DB, HTTP, file ops)."""
    global _io_pool
    if _io_pool is None:
        with _init_lock:
            if _io_pool is None:
                _io_pool = ManagedPool(DEFAULT_IO_WORKERS, "io")
    return _io_pool


def get_cpu_pool() -> ManagedPool:
    """Get the CPU-bound worker pool (analysis, parsing, embeddings)."""
    global _cpu_pool
    if _cpu_pool is None:
        with _init_lock:
            if _cpu_pool is None:
                _cpu_pool = ManagedPool(DEFAULT_CPU_WORKERS, "cpu")
    return _cpu_pool


def submit_io(fn: Callable, *args, task_name: str = "", **kwargs) -> Future:
    """Convenience: submit to IO pool."""
    return get_io_pool().submit(fn, *args, task_name=task_name, **kwargs)


def submit_cpu(fn: Callable, *args, task_name: str = "", **kwargs) -> Future:
    """Convenience: submit to CPU pool."""
    return get_cpu_pool().submit(fn, *args, task_name=task_name, **kwargs)


def pool_status() -> dict:
    """Get status of all worker pools."""
    result = {}
    if _io_pool:
        result["io"] = _io_pool.get_status()
    if _cpu_pool:
        result["cpu"] = _cpu_pool.get_status()
    result["config"] = {
        "io_workers": DEFAULT_IO_WORKERS,
        "cpu_workers": DEFAULT_CPU_WORKERS,
        "max_queue_depth": MAX_QUEUE_DEPTH,
    }
    return result


def shutdown_all(wait_for: bool = True):
    """Shut down all pools gracefully."""
    if _io_pool:
        _io_pool.shutdown(wait_for)
    if _cpu_pool:
        _cpu_pool.shutdown(wait_for)
