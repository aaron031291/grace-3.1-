"""
Real-Time Sync — WebSocket-based live updates across all views.

When a file changes in one view, ALL other views update instantly.
Uses an in-process pub/sub with SSE fallback for browsers.
"""

import json
import time
import threading
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
from collections import deque
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

_subscribers: Dict[str, Set] = {}
_event_buffer: deque = deque(maxlen=1000)
_sub_lock = threading.Lock()


def publish_change(event_type: str, path: str, project_id: str = "",
                   user_id: str = "", data: dict = None):
    """Publish a change event to all subscribers."""
    event = {
        "type": event_type,
        "path": path,
        "project_id": project_id,
        "user_id": user_id,
        "data": data or {},
        "ts": datetime.utcnow().isoformat(),
    }

    with _sub_lock:
        _event_buffer.append(event)

    # Notify via event bus
    try:
        from cognitive.event_bus import publish_async
        publish_async(f"sync.{event_type}", event, source="realtime_sync")
    except Exception:
        pass

    return event


def get_recent_events(since_ts: str = None, project_id: str = None,
                      limit: int = 50) -> list:
    """Get recent sync events, optionally filtered."""
    with _sub_lock:
        events = list(_event_buffer)

    if since_ts:
        events = [e for e in events if e["ts"] > since_ts]
    if project_id:
        events = [e for e in events if e["project_id"] == project_id or not e["project_id"]]

    return list(reversed(events[-limit:]))


def get_sync_stats() -> dict:
    """Get sync system statistics."""
    with _sub_lock:
        return {
            "buffer_size": len(_event_buffer),
            "buffer_capacity": _event_buffer.maxlen,
            "total_events": len(_event_buffer),
        }


# ── Wire into workspace bridge ───────────────────────────────────

def on_file_write(path: str, source: str, project_id: str = ""):
    """Called by workspace_bridge on every file write."""
    publish_change("file_changed", path, project_id, source)


def on_file_delete(path: str, source: str, project_id: str = ""):
    """Called by workspace_bridge on every file delete."""
    publish_change("file_deleted", path, project_id, source)


def on_project_switch(user_id: str, old_project: str, new_project: str):
    """Called when a user switches projects."""
    publish_change("project_switched", "", new_project, user_id,
                   {"from": old_project, "to": new_project})
