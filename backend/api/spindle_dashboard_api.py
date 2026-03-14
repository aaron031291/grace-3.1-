"""
Spindle Dashboard API — WebSocket + REST endpoints for Spindle observability.
Real-time streaming of Spindle events, proofs, gate verdicts, and execution results.
"""
import asyncio
import logging
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from cognitive.event_bus import subscribe

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/spindle", tags=["Spindle Dashboard"])


# ── REST Endpoints ─────────────────────────────────────────

@router.get("/dashboard")
async def get_dashboard():
    """Full Spindle dashboard: components, verification stats, audit trail."""
    try:
        from cognitive.spindle_projection import get_spindle_projection
        projection = get_spindle_projection(auto_start=False)
        return {"ok": True, "dashboard": projection.get_dashboard()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/events")
async def get_events(topic: str = None, source_type: str = None, limit: int = 50):
    """Query Spindle events from the persistent event store."""
    try:
        from cognitive.spindle_event_store import get_event_store
        events = get_event_store().query(topic=topic, source_type=source_type, limit=limit)
        return {"ok": True, "events": events, "count": len(events)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/executor/stats")
async def get_executor_stats():
    """Executor statistics: total/success/fail/pending."""
    try:
        from cognitive.spindle_executor import get_spindle_executor
        return {"ok": True, "stats": get_spindle_executor().stats}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/checkpoints")
async def get_checkpoints(limit: int = 20):
    """Recent checkpoint history."""
    try:
        from cognitive.spindle_checkpoint import get_checkpoint_manager
        return {"ok": True, "checkpoints": get_checkpoint_manager().get_recent(limit)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/gate/status")
async def get_gate_status():
    """Gate configuration and last verdict."""
    try:
        from cognitive.physics.spindle_gate import get_spindle_gate
        gate = get_spindle_gate()
        return {
            "ok": True,
            "validators": len(gate._validators),
            "validator_names": [name for name, _ in gate._validators],
            "quorum_ratio": gate.quorum_ratio,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/verify")
async def verify_action(request: Dict[str, Any]):
    """
    Submit an action for full Spindle Gate verification.
    Expects: {natural_language: str, privilege: str, session_context: dict}
    """
    try:
        from cognitive.braille_compiler import NLPCompilerEdge
        compiler = NLPCompilerEdge()
        masks, msg = compiler.process_command(
            natural_language=request.get("natural_language", ""),
            privilege=request.get("privilege", "user"),
            session_context=request.get("session_context", {}),
            use_gate=True,
        )

        proof = getattr(compiler, "_last_proof", None)
        verdict = getattr(compiler, "_last_verdict", None)

        return {
            "ok": True,
            "is_valid": masks is not None,
            "message": msg,
            "proof": proof.to_dict() if proof else None,
            "gate_confidence": verdict.confidence if verdict else None,
            "gate_votes": f"{verdict.votes_for}/{verdict.total_validators}" if verdict else None,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── WebSocket: Real-time Spindle Events ───────────────────

@router.websocket("/ws")
async def spindle_events_websocket(websocket: WebSocket):
    """
    WebSocket for real-time Spindle events.
    Streams: executions, Z3 proofs, gate verdicts, checkpoints, heartbeats.
    """
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    loop = asyncio.get_running_loop()

    def _handler(event):
        topic = getattr(event, "topic", "")
        # Only forward Spindle-related events
        if any(topic.startswith(p) for p in ("spindle.", "audit.spindle", "healing.", "deterministic.")):
            try:
                out = {
                    "topic": topic,
                    "data": getattr(event, "data", {}),
                    "source": getattr(event, "source", "system"),
                    "timestamp": getattr(event, "timestamp", None),
                }
                loop.call_soon_threadsafe(queue.put_nowait, out)
            except asyncio.QueueFull:
                pass  # Drop if consumer is too slow

    subscribe("*", _handler)
    logger.info("[SPINDLE-WS] Client connected")

    try:
        while True:
            data = await queue.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        logger.info("[SPINDLE-WS] Client disconnected")
    except Exception as e:
        logger.error(f"[SPINDLE-WS] Error: {e}")
