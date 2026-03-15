"""
Orchestrator WebSocket API — Real-time system state push.

Replaces polling: the frontend connects once and receives all state
changes as they happen, plus a periodic full snapshot every 10s.
"""

import asyncio
import logging
import time
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orchestrator", tags=["Orchestrator"])

# Track connected clients for metrics
_connected_clients: Set[int] = set()


@router.get("/state")
async def get_orchestrator_state():
    """REST fallback: get current orchestrator state snapshot."""
    try:
        from cognitive.central_orchestrator import get_orchestrator
        orch = get_orchestrator()
        if not orch._initialized:
            orch.initialize()
        return {"ok": True, "state": orch.get_state_snapshot()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/health")
async def get_integration_health():
    """Check all integration points and report broken connections."""
    try:
        from cognitive.central_orchestrator import get_orchestrator
        orch = get_orchestrator()
        return {"ok": True, "health": orch.check_integration_health()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/dashboard")
async def get_orchestrator_dashboard():
    """Full orchestrator dashboard: state + health combined."""
    try:
        from cognitive.central_orchestrator import get_orchestrator
        orch = get_orchestrator()
        if not orch._initialized:
            orch.initialize()
        return {"ok": True, "dashboard": orch.get_dashboard()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Topics that indicate significant state changes worth pushing
STATE_CHANGE_TOPICS = {
    "llm.", "healing.", "trust.", "system.", "consensus.",
    "orchestrator.", "learning.", "genesis.", "layer1.",
    "grace_os.", "file.", "deterministic.", "task.",
    "circuit_breaker.", "hallucination.", "knowledge.",
}


def _is_state_event(topic: str) -> bool:
    """Check if this event topic represents a meaningful state change."""
    return any(topic.startswith(prefix) for prefix in STATE_CHANGE_TOPICS)


@router.websocket("/ws")
async def orchestrator_websocket(websocket: WebSocket):
    """
    Real-time system state WebSocket.

    On connect:
      1. Sends full state snapshot immediately
      2. Streams state-change events as they happen
      3. Sends full state snapshot every 10 seconds

    Message types:
      {"type": "state_snapshot", "state": {...}}
      {"type": "event", "topic": "...", "data": {...}, ...}
      {"type": "connected", "clients": N}
    """
    await websocket.accept()
    client_id = id(websocket)
    _connected_clients.add(client_id)

    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    loop = asyncio.get_running_loop()

    def _safe_put(item):
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            pass

    def _event_handler(event):
        topic = getattr(event, "topic", "unknown")
        if not _is_state_event(topic):
            return
        try:
            out = {
                "type": "event",
                "topic": topic,
                "data": getattr(event, "data", {}),
                "source": getattr(event, "source", "system"),
                "timestamp": getattr(event, "timestamp", None),
            }
            loop.call_soon_threadsafe(_safe_put, out)
        except Exception as e:
            logger.error(f"[ORCH-WS] Event handler error: {e}")

    # Subscribe to cognitive event bus
    from cognitive.event_bus import subscribe, unsubscribe
    subscribe("*", _event_handler)
    logger.info(f"[ORCH-WS] Client {client_id} connected ({len(_connected_clients)} total)")

    # Send initial state snapshot
    try:
        from cognitive.central_orchestrator import get_orchestrator
        orch = get_orchestrator()
        if not orch._initialized:
            orch.initialize()
        snapshot = orch.get_state_snapshot()
        await websocket.send_json({"type": "state_snapshot", "state": snapshot})
    except Exception as e:
        await websocket.send_json({"type": "error", "message": f"Init error: {e}"})

    # Background task: periodic full snapshot every 10s
    async def _snapshot_loop():
        while True:
            await asyncio.sleep(10)
            try:
                from cognitive.central_orchestrator import get_orchestrator
                snapshot = get_orchestrator().get_state_snapshot()
                await websocket.send_json({"type": "state_snapshot", "state": snapshot})
            except Exception:
                break

    snapshot_task = asyncio.create_task(_snapshot_loop())

    try:
        while True:
            # Drain event queue and send to client
            data = await queue.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        logger.info(f"[ORCH-WS] Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"[ORCH-WS] WebSocket error: {e}")
    finally:
        snapshot_task.cancel()
        _connected_clients.discard(client_id)
        unsubscribe("*", _event_handler)
        logger.info(f"[ORCH-WS] Cleaned up ({len(_connected_clients)} clients remain)")
