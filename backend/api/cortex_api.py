"""
Cortex API — Lifecycle, health, and feedback correlation endpoints.
"""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cortex", tags=["Lifecycle Cortex"])


@router.get("/snapshot")
async def cortex_snapshot():
    """Full cortex state: subsystems, jobs, feedback chains."""
    try:
        from core.lifecycle_cortex import get_lifecycle_cortex
        cortex = get_lifecycle_cortex()
        return {"ok": True, "snapshot": cortex.get_snapshot()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/health")
async def cortex_health():
    """Unified health snapshot — single source of truth."""
    try:
        from core.lifecycle_cortex import get_lifecycle_cortex
        cortex = get_lifecycle_cortex()
        return {"ok": True, "health": cortex.get_health_snapshot()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/readiness")
async def cortex_readiness():
    """Check which subsystems are ready vs still initializing."""
    try:
        from core.lifecycle_cortex import get_lifecycle_cortex
        cortex = get_lifecycle_cortex()
        readiness = {}
        for name, entry in cortex._subsystems.items():
            readiness[name] = {
                "ready": entry.state.value == "ready",
                "state": entry.state.value,
                "policy": entry.spec.start_policy.value,
            }
        return {"ok": True, "readiness": readiness}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/feedback/incomplete")
async def incomplete_feedback_chains():
    """Find decision chains that haven't completed all stages."""
    try:
        from core.lifecycle_cortex import get_lifecycle_cortex
        cortex = get_lifecycle_cortex()
        return {"ok": True, "incomplete": cortex.get_incomplete_chains()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/jobs")
async def cortex_jobs():
    """Status of all maintenance jobs."""
    try:
        from core.lifecycle_cortex import get_lifecycle_cortex
        cortex = get_lifecycle_cortex()
        jobs = {}
        for name, job in cortex._jobs.items():
            jobs[name] = {
                "interval_s": job.interval_s,
                "requires": list(job.requires),
                "last_run": job.last_run,
                "run_count": job.run_count,
                "running": job.running,
                "last_error": job.last_error,
            }
        return {"ok": True, "jobs": jobs}
    except Exception as e:
        return {"ok": False, "error": str(e)}
