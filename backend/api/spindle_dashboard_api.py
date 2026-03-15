"""
Spindle Dashboard API — WebSocket + REST endpoints for Spindle observability.
Real-time streaming of Spindle events, proofs, gate verdicts, and execution results.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from cognitive.event_bus import subscribe, unsubscribe

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


# ── Blackbox Scanner Endpoints ─────────────────────────────

@router.get("/blackbox/report")
async def get_blackbox_report():
    """Returns the latest blackbox scan report (from projection or local scanner)."""
    try:
        from cognitive.spindle_problems_projection import get_problems_projection
        projection = get_problems_projection()
        report = projection.get_report()
        if report is not None:
            return {"ok": True, "report": report, "source": "projection"}
    except Exception:
        pass
    # Fallback: try local scanner
    try:
        from cognitive.spindle_blackbox_scanner import get_blackbox_scanner
        from dataclasses import asdict
        scanner = get_blackbox_scanner()
        report = scanner.get_latest_report()
        if report is None:
            return {"ok": True, "report": None, "status": "pending", "message": "No scan has run yet"}
        return {"ok": True, "report": asdict(report), "source": "local"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/blackbox/alerts")
async def get_blackbox_alerts(severity: Optional[str] = Query(None, description="Filter by severity: critical, warning, info")):
    """Returns current active alerts, optionally filtered by severity."""
    try:
        from cognitive.spindle_problems_projection import get_problems_projection
        projection = get_problems_projection()
        report = projection.get_report()
        if report is not None:
            alerts = report.get("alerts", [])
            if severity:
                alerts = [a for a in alerts if a.get("severity", "").lower() == severity.lower()]
            return {"ok": True, "alerts": alerts, "count": len(alerts), "source": "projection"}
    except Exception:
        pass
    # Fallback
    try:
        from cognitive.spindle_blackbox_scanner import get_blackbox_scanner
        from dataclasses import asdict
        scanner = get_blackbox_scanner()
        report = scanner.get_latest_report()
        if report is None:
            return {"ok": True, "alerts": [], "count": 0, "message": "No scan has run yet"}
        alerts = report.alerts
        if severity:
            alerts = [a for a in alerts if a.severity.lower() == severity.lower()]
        return {"ok": True, "alerts": [asdict(a) for a in alerts], "count": len(alerts), "source": "local"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/problems")
async def get_problems():
    """Combined problems view: blackbox report + recent autonomous actions."""
    try:
        from cognitive.spindle_problems_projection import get_problems_projection
        projection = get_problems_projection()
        return {"ok": True, **projection.get_problems_summary()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/blackbox/scan")
async def trigger_blackbox_scan():
    """Triggers an immediate blackbox scan and returns the report."""
    try:
        import asyncio
        from cognitive.spindle_blackbox_scanner import get_blackbox_scanner
        from dataclasses import asdict
        scanner = get_blackbox_scanner()
        loop = asyncio.get_running_loop()
        report = await loop.run_in_executor(None, scanner.run_scan)
        scanner.publish_alerts(report)
        return {"ok": True, "report": asdict(report)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/blackbox/alerts/new")
async def get_blackbox_new_alerts():
    """Returns only new alerts from the latest scan (delta from previous)."""
    try:
        from cognitive.spindle_blackbox_scanner import get_blackbox_scanner
        from dataclasses import asdict
        scanner = get_blackbox_scanner()
        new_alerts = scanner.get_alerts()
        return {"ok": True, "alerts": [asdict(a) for a in new_alerts], "count": len(new_alerts)}
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
        if any(topic.startswith(p) for p in ("spindle.", "spindle.blackbox", "audit.spindle", "healing.", "deterministic.")):
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
    finally:
        unsubscribe("*", _handler)
        logger.info("[SPINDLE-WS] Handler unsubscribed")
