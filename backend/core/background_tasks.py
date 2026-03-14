"""
Background task runner Ã¢â‚¬â€ opt-in async/thread coordination.

Components submit long-running jobs here. No forced rewrite of call paths.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any, Optional
from queue import Queue
import atexit

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound or blocking work
_pool: Optional[ThreadPoolExecutor] = None
_pool_lock = threading.Lock()
_pool_size = 4

# Simple job queue (runs in background thread)
_queue: Optional[Queue] = None
_worker_thread: Optional[threading.Thread] = None
_worker_stop = threading.Event()


def _worker() -> None:
    """Background worker that processes queued jobs."""
    while not _worker_stop.is_set():
        try:
            job = _get_queue().get(timeout=0.5)
            if job is None:
                continue
            fn, args, kwargs = job
            try:
                fn(*args, **kwargs)
            except Exception as e:
                logger.warning("Background task failed: %s", e)
        except Exception:
            pass


def _get_pool() -> ThreadPoolExecutor:
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = ThreadPoolExecutor(max_workers=_pool_size, thread_name_prefix="grace_bg")
        return _pool


def _get_queue() -> Queue:
    global _queue, _worker_thread
    if _queue is None:
        from queue import Queue as Q
        _queue = Q()
        _worker_thread = threading.Thread(target=_worker, daemon=True)
        _worker_thread.start()
    return _queue


def submit_background(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """
    Submit a task to run in the background (fire-and-forget).
    Use for long-running work: ingestion, healing, diagnostics.
    """
    _get_queue().put((fn, args, kwargs))


def submit_thread_pool(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Submit a task to the thread pool and return a Future.
    Use when you need to await or check completion.
    """
    return _get_pool().submit(fn, *args, **kwargs)


def shutdown() -> None:
    """Shutdown background workers (call on app exit)."""
    global _worker_stop, _pool
    _worker_stop.set()
    if _pool:
        _pool.shutdown(wait=False)


atexit.register(shutdown)
