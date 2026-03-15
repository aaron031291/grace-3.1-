"""
Coding Agent Governance API
────────────────────────────────────────────
HITL governance tab for accepting/rejecting coding agent output.
Shows code with health status, Genesis keys, and one-click autofix.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, List
import logging
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coding-agent/governance", tags=["Coding Agent Governance"])


class ReviewDecision(BaseModel):
    task_id: str
    decision: str  # "accept" or "reject"
    reason: Optional[str] = None


class AutofixRequest(BaseModel):
    task_id: str
    file_path: str
    patch_code: str


class RollbackRequest(BaseModel):
    file_path: str
    snapshot_id: Optional[str] = None


@router.get("/status")
async def get_pool_status():
    """Get coding agent pool status — active jobs, limits, agent health."""
    try:
        from cognitive.coding_agents import get_coding_agent_pool
        pool = get_coding_agent_pool()
        return {"ok": True, "data": pool.get_status()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/pending")
async def get_pending_reviews(limit: int = Query(default=20, ge=1, le=100)):
    """Get coding agent results awaiting human review."""
    try:
        from cognitive.coding_agents import get_coding_agent_pool
        pool = get_coding_agent_pool()
        with pool._lock:
            recent = list(pool._results[-limit:])

        items = []
        for r in recent:
            # Determine health status
            health = "healthy"
            if r.status == "failed":
                health = "broken"
            elif r.confidence < 0.6:
                health = "warning"

            items.append({
                "task_id": r.task_id,
                "agent": r.agent,
                "status": r.status,
                "confidence": r.confidence,
                "health": health,
                "patch": r.patch[:2000] if r.patch else None,
                "analysis": r.analysis[:500] if r.analysis else None,
                "error": r.error[:200] if r.error else None,
                "duration_s": r.duration_s,
                "genesis_key": getattr(r, 'genesis_key', None),
            })

        return {"ok": True, "items": items, "count": len(items)}
    except Exception as e:
        return {"ok": False, "items": [], "error": str(e)}


@router.post("/review")
async def submit_review(decision: ReviewDecision):
    """Accept or reject a coding agent result."""
    try:
        from api._genesis_tracker import track
        gk = track(
            key_type="coding_agent_action",
            what=f"HITL review: {decision.decision} task {decision.task_id}",
            who="human_reviewer",
            output_data={
                "task_id": decision.task_id,
                "decision": decision.decision,
                "reason": decision.reason,
            },
            tags=["hitl", "coding_agent", "review", decision.decision],
        )

        if decision.decision == "accept":
            # Emit acceptance event for Spindle tracking
            try:
                from cognitive.event_bus import publish_async
                publish_async("coding_agent.hitl.accepted", {
                    "task_id": decision.task_id,
                    "genesis_key": str(gk) if gk else None,
                }, source="hitl_governance")
            except Exception:
                pass

        return {
            "ok": True,
            "decision": decision.decision,
            "task_id": decision.task_id,
            "genesis_key": str(gk) if gk else None,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/autofix")
async def trigger_autofix(req: AutofixRequest):
    """One-click autofix — run the patch through sandbox, apply if safe."""
    try:
        from cognitive.sandbox_repair_engine import get_sandbox_repair_engine
        engine = get_sandbox_repair_engine()
        verdict = engine.evaluate(req.file_path, req.patch_code)

        applied = False
        if verdict.passed:
            # Apply via environment routing with Genesis tracking
            try:
                from core.environment import route_file_write
                route_file_write(
                    req.file_path, req.patch_code,
                    source="hitl_autofix",
                )
                applied = True
            except Exception:
                # Fallback direct write
                from core.services.code_service import apply_code
                apply_code(req.file_path, req.patch_code)
                applied = True

            # Track with Genesis
            try:
                from api._genesis_tracker import track
                track(
                    key_type="coding_agent_action",
                    what=f"Autofix applied: {req.file_path}",
                    who="hitl_autofix",
                    file_path=req.file_path,
                    tags=["autofix", "hitl", "coding_agent"],
                )
            except Exception:
                pass

        return {
            "ok": True,
            "passed": verdict.passed,
            "applied": applied,
            "verdict": {
                "syntax_valid": verdict.syntax_valid,
                "static_clean": verdict.static_clean,
                "tests_passed": verdict.tests_passed,
                "rejection_reason": verdict.rejection_reason,
            },
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/health")
async def get_code_health():
    """Quick health check of recent coding agent output — how many healthy vs broken."""
    try:
        from cognitive.coding_agents import get_coding_agent_pool
        pool = get_coding_agent_pool()
        with pool._lock:
            recent = list(pool._results[-50:])

        healthy = sum(1 for r in recent if r.status == "completed" and r.confidence >= 0.6)
        warning = sum(1 for r in recent if r.status == "completed" and r.confidence < 0.6)
        broken = sum(1 for r in recent if r.status == "failed")

        return {
            "ok": True,
            "healthy": healthy,
            "warning": warning,
            "broken": broken,
            "total": len(recent),
            "active_jobs": pool._active_jobs,
            "max_jobs": pool.MAX_CONCURRENT_JOBS,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/rollback")
async def rollback_change(req: RollbackRequest):
    """Rollback a file to its pre-agent-fix state."""
    try:
        if req.snapshot_id:
            # Try safety snapshot rollback first
            try:
                from core.safety import rollback_to
                rollback_to(req.snapshot_id)
                return {"ok": True, "method": "safety_snapshot", "file": req.file_path}
            except Exception:
                pass
            # Try Genesis version rollback
            try:
                from genesis.symbiotic_version_control import get_symbiotic_version_control
                svc = get_symbiotic_version_control()
                result = svc.rollback_to_version(req.file_path, req.snapshot_id)
                return {"ok": True, "method": "genesis_version", "result": result}
            except Exception as e:
                return {"ok": False, "error": f"Rollback failed: {e}"}
        else:
            # Rollback to previous version via user undo stack
            try:
                from core.user_features import undo
                undo(req.file_path)
                return {"ok": True, "method": "undo_stack", "file": req.file_path}
            except Exception as e:
                return {"ok": False, "error": f"Undo failed: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/run-hardening")
async def run_hardening():
    """Launch all 20 hardening tasks in a background thread."""
    import threading

    def _run():
        try:
            from scripts.hardening_tasks import dispatch_all
            dispatch_all()
        except Exception as e:
            logger.error(f"[HARDENING] Failed: {e}")

    t = threading.Thread(target=_run, daemon=True, name="hardening-dispatch")
    t.start()

    return {
        "ok": True,
        "message": "Hardening tasks dispatched — 20 tasks across Kimi & Opus (max 5 concurrent). Watch the live feed.",
        "tasks": 20,
    }
