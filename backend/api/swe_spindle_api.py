"""
api/swe_spindle_api.py
─────────────────────────────────────────────────────────────────────
SWE → Spindle Bridge API  (Phase 4)

Endpoints for monitoring and controlling the SWE→Spindle bridge
that translates high-trust LearningExamples into deterministic
Braille/Spindle execution paths.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spindle/swe-bridge", tags=["SWE-Spindle Bridge"])


@router.get("/status")
async def get_bridge_status():
    """Get SWE→Spindle bridge status, stats, and LLM bypass ratio."""
    try:
        from cognitive.swe_spindle_bridge import get_swe_spindle_bridge
        return get_swe_spindle_bridge().get_stats()
    except Exception as e:
        logger.warning("[SWE-BRIDGE-API] Status fetch failed: %s", e)
        return {"running": False, "error": str(e)}


@router.get("/history")
async def get_translation_history(limit: int = Query(default=50, ge=1, le=200)):
    """Get recent translation history."""
    try:
        from cognitive.swe_spindle_bridge import get_swe_spindle_bridge
        history = get_swe_spindle_bridge().get_translation_history(limit=limit)
        return {"translations": history, "count": len(history)}
    except Exception as e:
        logger.warning("[SWE-BRIDGE-API] History fetch failed: %s", e)
        return {"translations": [], "count": 0, "error": str(e)}


class ProcessRequest(BaseModel):
    example_id: int


@router.post("/process")
async def process_single_example(request: ProcessRequest):
    """Manually translate a single LearningExample by ID."""
    try:
        from cognitive.swe_spindle_bridge import get_swe_spindle_bridge
        result = get_swe_spindle_bridge().process_example(request.example_id)
        if result is None:
            return {"status": "not_found", "example_id": request.example_id}
        return {
            "status": "valid" if result.is_valid else "rejected",
            "example_id": result.example_id,
            "token_count": result.token_count,
            "pattern_hash": result.pattern_hash,
            "error": result.validation_error,
        }
    except Exception as e:
        logger.warning("[SWE-BRIDGE-API] Process failed: %s", e)
        return {"status": "error", "error": str(e)}


@router.post("/cycle")
async def force_cycle():
    """Force a full scan → translate → register cycle."""
    try:
        from cognitive.swe_spindle_bridge import get_swe_spindle_bridge
        return get_swe_spindle_bridge().force_cycle()
    except Exception as e:
        logger.warning("[SWE-BRIDGE-API] Cycle failed: %s", e)
        return {"status": "error", "error": str(e)}


@router.post("/start")
async def start_bridge():
    """Start the SWE→Spindle bridge background loop."""
    try:
        from cognitive.swe_spindle_bridge import get_swe_spindle_bridge
        started = get_swe_spindle_bridge().start()
        return {"status": "started" if started else "already_running"}
    except Exception as e:
        logger.warning("[SWE-BRIDGE-API] Start failed: %s", e)
        return {"status": "error", "error": str(e)}


@router.post("/stop")
async def stop_bridge():
    """Stop the SWE→Spindle bridge background loop."""
    try:
        from cognitive.swe_spindle_bridge import get_swe_spindle_bridge
        get_swe_spindle_bridge().stop()
        return {"status": "stopped"}
    except Exception as e:
        logger.warning("[SWE-BRIDGE-API] Stop failed: %s", e)
        return {"status": "error", "error": str(e)}
