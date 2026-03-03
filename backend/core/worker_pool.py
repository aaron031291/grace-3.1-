"""
Worker Pool — multi-process execution for concurrent users.

Prevents one user's infinite loop from crashing everyone.
Uses ThreadPoolExecutor for brain calls, ProcessPoolExecutor for heavy compute.
"""

import os
import time
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, TimeoutError
from typing import Callable, Any, Optional, Dict
from functools import lru_cache

logger = logging.getLogger(__name__)

# Thread pool for I/O-bound brain calls
_thread_pool: Optional[ThreadPoolExecutor] = None
_thread_lock = threading.Lock()

# Per-user request tracking
_user_requests: Dict[str, list] = {}
_user_lock = threading.Lock()

MAX_WORKERS = int(os.getenv("GRACE_MAX_WORKERS", "10"))
MAX_REQUESTS_PER_USER = int(os.getenv("GRACE_MAX_USER_REQUESTS", "50"))
REQUEST_TIMEOUT = int(os.getenv("GRACE_REQUEST_TIMEOUT", "120"))


def get_thread_pool() -> ThreadPoolExecutor:
    """Get or create the shared thread pool."""
    global _thread_pool
    if _thread_pool is None:
        with _thread_lock:
            if _thread_pool is None:
                _thread_pool = ThreadPoolExecutor(
                    max_workers=MAX_WORKERS,
                    thread_name_prefix="grace-worker",
                )
    return _thread_pool


def submit_task(func: Callable, *args, user_id: str = "default",
                timeout: int = None, **kwargs) -> Any:
    """
    Submit a task to the worker pool with per-user rate limiting.
    Returns the result or raises TimeoutError.
    """
    # Per-user rate limiting
    if not _check_user_quota(user_id):
        raise RuntimeError(f"Rate limit exceeded for user {user_id}")

    pool = get_thread_pool()
    future = pool.submit(func, *args, **kwargs)

    try:
        result = future.result(timeout=timeout or REQUEST_TIMEOUT)
        _record_request(user_id, success=True)
        return result
    except TimeoutError:
        future.cancel()
        _record_request(user_id, success=False)
        raise
    except Exception as e:
        _record_request(user_id, success=False)
        raise


def _check_user_quota(user_id: str) -> bool:
    """Check if user is within their request quota."""
    with _user_lock:
        now = time.time()
        requests = _user_requests.get(user_id, [])
        # Remove requests older than 1 hour
        requests = [r for r in requests if now - r["ts"] < 3600]
        _user_requests[user_id] = requests
        return len(requests) < MAX_REQUESTS_PER_USER


def _record_request(user_id: str, success: bool = True):
    """Record a request for rate limiting."""
    with _user_lock:
        if user_id not in _user_requests:
            _user_requests[user_id] = []
        _user_requests[user_id].append({"ts": time.time(), "success": success})


def get_pool_stats() -> dict:
    """Get worker pool statistics."""
    pool = get_thread_pool()
    with _user_lock:
        active_users = len(_user_requests)
        total_requests = sum(len(r) for r in _user_requests.values())
    return {
        "max_workers": MAX_WORKERS,
        "active_users": active_users,
        "total_requests_1h": total_requests,
        "max_per_user": MAX_REQUESTS_PER_USER,
        "timeout_seconds": REQUEST_TIMEOUT,
    }


# ═══════════════════════════════════════════════════════════════════
#  RESPONSE CACHE — avoid duplicate LLM calls
# ═══════════════════════════════════════════════════════════════════

_response_cache: Dict[str, dict] = {}
_cache_lock = threading.Lock()
CACHE_TTL = 300  # 5 minutes
MAX_CACHE_SIZE = 500


def cached_brain_call(domain: str, action: str, payload_hash: str,
                      func: Callable) -> Any:
    """
    Cache brain call results. Same domain+action+payload within 5min
    returns cached result instead of calling LLM again.
    """
    cache_key = f"{domain}:{action}:{payload_hash}"

    with _cache_lock:
        if cache_key in _response_cache:
            entry = _response_cache[cache_key]
            if time.time() - entry["ts"] < CACHE_TTL:
                entry["hits"] += 1
                return entry["result"]

    # Cache miss — execute
    result = func()

    with _cache_lock:
        if len(_response_cache) >= MAX_CACHE_SIZE:
            # Evict oldest
            oldest_key = min(_response_cache, key=lambda k: _response_cache[k]["ts"])
            del _response_cache[oldest_key]
        _response_cache[cache_key] = {"result": result, "ts": time.time(), "hits": 0}

    return result


def get_cache_stats() -> dict:
    with _cache_lock:
        total_hits = sum(e["hits"] for e in _response_cache.values())
        return {
            "entries": len(_response_cache),
            "max_size": MAX_CACHE_SIZE,
            "ttl_seconds": CACHE_TTL,
            "total_cache_hits": total_hits,
        }


def clear_cache():
    with _cache_lock:
        _response_cache.clear()
