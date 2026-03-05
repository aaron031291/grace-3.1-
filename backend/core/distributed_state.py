"""
Distributed State — multi-instance state management.

Uses Redis when available, falls back to in-process dict.
Handles: session state, active projects, user presence,
cross-instance communication.
"""

import json
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

_local_state: Dict[str, str] = {}
_state_lock = threading.Lock()
_redis_client = None
_redis_available = False


def _get_redis():
    """Try to connect to Redis. Falls back to local dict."""
    global _redis_client, _redis_available
    if _redis_client is not None:
        return _redis_client

    try:
        import redis
        import os
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(url, decode_responses=True, socket_timeout=2)
        _redis_client.ping()
        _redis_available = True
        logger.info("Redis connected — distributed state enabled")
        return _redis_client
    except Exception:
        _redis_available = False
        _redis_client = None
        return None


def set_state(key: str, value: Any, ttl: int = 3600) -> bool:
    """Set a state value. Uses Redis if available, local dict otherwise."""
    serialized = json.dumps(value, default=str) if not isinstance(value, str) else value

    r = _get_redis()
    if r:
        try:
            r.setex(f"grace:{key}", ttl, serialized)
            return True
        except Exception:
            pass

    with _state_lock:
        _local_state[key] = serialized
    return True


def get_state(key: str, default: Any = None) -> Any:
    """Get a state value."""
    r = _get_redis()
    if r:
        try:
            val = r.get(f"grace:{key}")
            if val:
                try:
                    return json.loads(val)
                except Exception:
                    return val
        except Exception:
            pass

    with _state_lock:
        val = _local_state.get(key)
    if val:
        try:
            return json.loads(val)
        except Exception:
            return val
    return default


def delete_state(key: str) -> bool:
    """Delete a state value."""
    r = _get_redis()
    if r:
        try:
            r.delete(f"grace:{key}")
        except Exception:
            pass

    with _state_lock:
        _local_state.pop(key, None)
    return True


def set_user_session(user_id: str, session_data: dict):
    """Store user session state (survives hot-swap and restart with Redis)."""
    set_state(f"session:{user_id}", session_data, ttl=86400)


def get_user_session(user_id: str) -> dict:
    """Get user session state."""
    return get_state(f"session:{user_id}", {})


def set_project_state(project_id: str, state_data: dict):
    """Store project-level state."""
    set_state(f"project:{project_id}", state_data, ttl=86400)


def get_project_state(project_id: str) -> dict:
    """Get project-level state."""
    return get_state(f"project:{project_id}", {})


def register_instance(instance_id: str, metadata: dict = None):
    """Register a Grace instance for multi-instance awareness."""
    set_state(f"instance:{instance_id}", {
        "id": instance_id,
        "started_at": datetime.utcnow().isoformat(),
        "metadata": metadata or {},
    }, ttl=300)


def list_instances() -> list:
    """List all active Grace instances."""
    r = _get_redis()
    if r:
        try:
            keys = r.keys("grace:instance:*")
            instances = []
            for key in keys:
                val = r.get(key)
                if val:
                    try:
                        instances.append(json.loads(val))
                    except Exception:
                        pass
            return instances
        except Exception:
            pass
    return [{"id": "local", "started_at": datetime.utcnow().isoformat(), "note": "single instance (no Redis)"}]


def get_distributed_stats() -> dict:
    """Get distributed state statistics."""
    r = _get_redis()
    return {
        "redis_available": _redis_available,
        "redis_url": "connected" if _redis_available else "not configured",
        "local_state_keys": len(_local_state),
        "instances": len(list_instances()),
        "mode": "distributed" if _redis_available else "local",
    }
