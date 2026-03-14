"""
api/governance_healing_api.py
─────────────────────────────────────────────────────────────────────
Governance → Self-Healing Bridge API  (Phase 3.1)

Endpoints for monitoring and controlling the governance healing bridge
that automatically triggers self-healing when trust drops below thresholds.
"""

from fastapi import APIRouter, Query
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/governance/healing", tags=["Governance Healing"])


@router.get("/status")
async def get_healing_bridge_status():
    """Get governance healing bridge status, thresholds, and recent activity."""
    try:
        from cognitive.governance_healing_bridge import get_governance_healing_bridge
        bridge = get_governance_healing_bridge()
        return bridge.get_status()
    except Exception as e:
        logger.warning("[GOV-HEAL-API] Status fetch failed: %s", e)
        return {"running": False, "error": str(e)}


@router.get("/history")
async def get_healing_trigger_history(limit: int = Query(default=50, ge=1, le=200)):
    """Get recent governance healing trigger history."""
    try:
        from cognitive.governance_healing_bridge import get_governance_healing_bridge
        bridge = get_governance_healing_bridge()
        return {"triggers": bridge.get_trigger_history(limit=limit), "count": len(bridge.get_trigger_history(limit=limit))}
    except Exception as e:
        logger.warning("[GOV-HEAL-API] History fetch failed: %s", e)
        return {"triggers": [], "count": 0, "error": str(e)}


@router.post("/evaluate")
async def force_evaluation():
    """Manually trigger a governance healing evaluation cycle."""
    try:
        from cognitive.governance_healing_bridge import get_governance_healing_bridge
        bridge = get_governance_healing_bridge()
        result = bridge.force_evaluate()
        return result
    except Exception as e:
        logger.warning("[GOV-HEAL-API] Force evaluate failed: %s", e)
        return {"status": "error", "error": str(e)}


@router.post("/start")
async def start_healing_bridge():
    """Start the governance healing bridge if not already running."""
    try:
        from cognitive.governance_healing_bridge import get_governance_healing_bridge
        bridge = get_governance_healing_bridge()
        started = bridge.start()
        return {"status": "started" if started else "already_running"}
    except Exception as e:
        logger.warning("[GOV-HEAL-API] Start failed: %s", e)
        return {"status": "error", "error": str(e)}


@router.post("/stop")
async def stop_healing_bridge():
    """Stop the governance healing bridge."""
    try:
        from cognitive.governance_healing_bridge import get_governance_healing_bridge
        bridge = get_governance_healing_bridge()
        bridge.stop()
        return {"status": "stopped"}
    except Exception as e:
        logger.warning("[GOV-HEAL-API] Stop failed: %s", e)
        return {"status": "error", "error": str(e)}
