"""
Built-in Distributed Tracing — trace IDs flow through the entire system.

No OpenTelemetry dependency. Just thread-local context + lightweight keys.

Every request gets a trace_id that propagates:
  brain → service → cognitive → back
  
Plus: lightweight Genesis keys (in-memory ring buffer, batch-flush every 10s).
"""

import time
import hashlib
from datetime import datetime, timezone
import threading
import queue
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
#  TRACE ID — thread-local propagation
# ═══════════════════════════════════════════════════════════════════

_trace_local = threading.local()


def new_trace(path: str = "", name: str = "") -> str:
    """Start a new trace. Returns deterministic trace_id (no random)."""
    bucket = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    seed = f"{path}|{name}|{bucket}|{id(_trace_local)}"
    tid = hashlib.sha256(seed.encode()).hexdigest()[:16]
    _trace_local.trace_id = tid
    _trace_local.spans = []
    _trace_local.start_time = time.time()
    return tid


def get_trace_id() -> str:
    """Get current trace ID."""
    return getattr(_trace_local, "trace_id", None) or new_trace()


def add_span(name: str, data: dict = None):
    """Add a span to the current trace."""
    spans = getattr(_trace_local, "spans", None)
    if spans is None:
        _trace_local.spans = spans = []
    spans.append({
        "name": name,
        "ts": time.time(),
        "data": data or {},
    })


def get_trace() -> dict:
    """Get the full current trace."""
    return {
        "trace_id": get_trace_id(),
        "spans": getattr(_trace_local, "spans", []),
        "duration_ms": round((time.time() - getattr(_trace_local, "start_time", time.time())) * 1000, 1),
    }


# ═══════════════════════════════════════════════════════════════════
#  LIGHTWEIGHT GENESIS KEYS — in-memory ring buffer, batch flush
# ═══════════════════════════════════════════════════════════════════

@dataclass
class LightKey:
    """Minimal Genesis key — 5 fields, no DB write."""
    key_type: str
    what: str
    who: str = "system"
    tags: list = field(default_factory=list)
    trace_id: str = ""
    ts: float = field(default_factory=time.time)


_ring_buffer: deque = deque(maxlen=50000)
_flush_queue: queue.Queue = queue.Queue(maxsize=100000)
_flush_thread_started = False
_flush_lock = threading.Lock()

FLUSH_INTERVAL = 10.0
FLUSH_BATCH_SIZE = 500


def light_track(key_type: str, what: str, who: str = "system",
                tags: list = None) -> None:
    """
    Lightweight Genesis key — NO DB write, NO event bus.
    Just appends to an in-memory ring buffer.
    Batch-flushed to DB every 10 seconds.

    ~100ns per call vs ~5ms for full track().
    """
    key = LightKey(
        key_type=key_type,
        what=what,
        who=who,
        tags=tags or [],
        trace_id=getattr(_trace_local, "trace_id", ""),
    )
    _ring_buffer.append(key)

    try:
        _flush_queue.put_nowait(key)
    except queue.Full:
        pass

    _ensure_flush_thread()


def get_recent_keys(n: int = 100) -> list:
    """Get the N most recent lightweight keys from the ring buffer."""
    keys = list(_ring_buffer)[-n:]
    return [
        {"key_type": k.key_type, "what": k.what, "who": k.who,
         "tags": k.tags, "trace_id": k.trace_id,
         "ts": datetime.fromtimestamp(k.ts).isoformat()}
        for k in reversed(keys)
    ]


def get_buffer_stats() -> dict:
    """Get ring buffer stats."""
    return {
        "buffer_size": len(_ring_buffer),
        "buffer_capacity": _ring_buffer.maxlen,
        "flush_queue_size": _flush_queue.qsize(),
    }


def _ensure_flush_thread():
    """Start the background flush thread if not running."""
    global _flush_thread_started
    if _flush_thread_started:
        return
    with _flush_lock:
        if _flush_thread_started:
            return
        _flush_thread_started = True
        t = threading.Thread(target=_flush_worker, daemon=True, name="genesis-flush")
        t.start()


def _flush_worker():
    """Background thread: batch-flushes lightweight keys to DB."""
    while True:
        batch = []
        deadline = time.time() + FLUSH_INTERVAL

        while time.time() < deadline and len(batch) < FLUSH_BATCH_SIZE:
            try:
                key = _flush_queue.get(timeout=1.0)
                batch.append(key)
            except queue.Empty:
                continue

        if not batch:
            continue

        try:
            from api._genesis_tracker import track
            for key in batch:
                track(
                    key_type=key.key_type,
                    what=key.what,
                    who=key.who,
                    tags=key.tags,
                )
        except Exception as e:
            logger.debug(f"Batch flush error: {e}")


# ═══════════════════════════════════════════════════════════════════
#  AUTO-PROBE ON CODE CHANGE
# ═══════════════════════════════════════════════════════════════════

_auto_probe_registered = False


def register_auto_probe():
    """Subscribe to Genesis key events — auto-probe on code changes."""
    global _auto_probe_registered
    if _auto_probe_registered:
        return
    _auto_probe_registered = True

    try:
        from cognitive.event_bus import subscribe

        def _on_code_change(event):
            # Event bus passes an Event object with .data (dict), not a raw dict
            data = event.data if hasattr(event, "data") else event
            tags = data.get("tags", [])
            key_type = data.get("key_type", "")
            if key_type in ("code_change", "file_op") or "code_change" in tags:
                threading.Thread(
                    target=_run_auto_probe,
                    args=(data,),
                    daemon=True,
                ).start()

        subscribe("genesis.code_change", _on_code_change)
        subscribe("genesis.file_op", _on_code_change)
        subscribe("genesis.key_created", _on_code_change)
        logger.info("Auto-probe registered on code change events")
    except Exception as e:
        logger.debug(f"Auto-probe registration failed: {e}")


def _run_auto_probe(event_data: dict):
    """Run probe + self-test when code changes."""
    try:
        from api.brain_api_v2 import call_brain

        probe_result = call_brain("system", "probe", {})
        health_result = call_brain("system", "problems", {})

        problems = health_result.get("data", {}).get("problems", [])
        probe_ok = probe_result.get("ok", False)

        light_track(
            key_type="system_event",
            what=f"Auto-probe after code change: probe={'ok' if probe_ok else 'fail'}, "
                 f"problems={len(problems)}",
            who="auto_probe",
            tags=["auto-probe", "code-change", "self-test"],
        )

        if problems:
            call_brain("system", "auto_cycle", {})

    except Exception as e:
        logger.debug(f"Auto-probe error: {e}")
