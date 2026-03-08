"""
Async, multi-threading, parallel and background processing — main way of operating.

Use this module throughout the system for:
- run_parallel: run independent sync callables in parallel (thread pool)
- run_background: fire-and-forget (don't block caller)
- run_async: run async coroutines (from sync context via asyncio.run or get_event_loop)

Shared thread pool; optional asyncio integration where needed.
"""

import asyncio
import concurrent.futures
import logging
import os
import threading
from typing import Any, Callable, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Shared pool for parallel and background work
_MAX_WORKERS = int(os.getenv("GRACE_PARALLEL_WORKERS", "12"))
_pool: Optional[concurrent.futures.ThreadPoolExecutor] = None
_pool_lock = threading.Lock()


def get_pool() -> concurrent.futures.ThreadPoolExecutor:
    """Get or create the shared thread pool for parallel/background execution."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = concurrent.futures.ThreadPoolExecutor(
                    max_workers=_MAX_WORKERS,
                    thread_name_prefix="grace-parallel",
                )
    return _pool


def run_parallel(
    callables: List[Callable[[], T]],
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
) -> List[T]:
    """
    Run multiple no-arg callables in parallel. Returns list of results in same order.
    Uses shared thread pool. Default: raise on first exception; set return_exceptions=True to get exceptions as results.
    """
    if not callables:
        return []
    pool = get_pool()
    futures = [pool.submit(fn) for fn in callables]
    results: List[T] = []
    for fut in futures:
        try:
            results.append(fut.result(timeout=timeout))
        except Exception as e:
            if return_exceptions:
                results.append(e)  # type: ignore
            else:
                for f in futures:
                    f.cancel()
                raise e
    return results


def run_background(fn: Callable[[], Any], name: str = "") -> None:
    """
    Schedule fn() to run in the background (fire-and-forget). Caller does not wait.
    Use for cross-triggers, learning, logging, non-blocking side effects.
    """
    pool = get_pool()

    def _run():
        try:
            fn()
        except Exception as e:
            logger.warning("[BACKGROUND] %s failed: %s", name or fn.__name__, e)

    pool.submit(_run)


def run_async(coro) -> Any:
    """Run an async coroutine from sync code (creates or uses event loop)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # We're inside an async context; run in thread so we don't nest
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as one:
        future = one.submit(asyncio.run, coro)
        return future.result()


def run_parallel_async(
    coros: List[Any],
    timeout: Optional[float] = None,
) -> List[Any]:
    """Run multiple coroutines in parallel; returns list of results (from sync context)."""
    async def _gather():
        return await asyncio.gather(*coros, return_exceptions=False)

    try:
        loop = asyncio.get_running_loop()
        # From sync context we'd use asyncio.run; if already in loop we need to schedule
        return run_async(_gather())
    except Exception:
        return asyncio.run(_gather())
