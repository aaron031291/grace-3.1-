"""
api/self_mirror_api.py
Self-Mirroring Telemetry API (Phase 3.4)
"""

from fastapi import APIRouter, Query
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry/mirror", tags=["Self-Mirror"])


@router.get("/latest")
async def get_latest_snapshot():
    """Get the most recent mirror snapshot."""
    try:
        from telemetry.self_mirror import get_self_mirror
        latest = get_self_mirror().get_latest()
        return latest or {"status": "no_snapshots_yet"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/history")
async def get_mirror_history(limit: int = Query(default=60, ge=1, le=120)):
    """Get recent mirror snapshot history."""
    try:
        from telemetry.self_mirror import get_self_mirror
        history = get_self_mirror().get_history(limit=limit)
        return {"snapshots": history, "count": len(history)}
    except Exception as e:
        return {"snapshots": [], "error": str(e)}


@router.get("/status")
async def get_mirror_status():
    """Get self-mirror service status."""
    try:
        from telemetry.self_mirror import get_self_mirror
        return get_self_mirror().get_stats()
    except Exception as e:
        return {"running": False, "error": str(e)}


@router.post("/start")
async def start_mirror():
    """Start the self-mirror loop."""
    try:
        from telemetry.self_mirror import get_self_mirror
        started = get_self_mirror().start()
        return {"status": "started" if started else "already_running"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/stop")
async def stop_mirror():
    """Stop the self-mirror loop."""
    try:
        from telemetry.self_mirror import get_self_mirror
        get_self_mirror().stop()
        return {"status": "stopped"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
