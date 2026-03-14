"""
api/sandbox_repair_api.py
─────────────────────────────────────────────────────────────────────
Sandbox Repair Engine API  (Phase 3.3)

Endpoints for monitoring and manually triggering sandbox patch evaluation.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repair/sandbox", tags=["Sandbox Repair"])


class EvaluateRequest(BaseModel):
    target_file: str
    patch_code: str
    run_tests: bool = True
    test_file: str = None


@router.get("/status")
async def get_status():
    """Get sandbox repair engine statistics."""
    try:
        from cognitive.sandbox_repair_engine import get_sandbox_repair_engine
        return get_sandbox_repair_engine().get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/history")
async def get_history(limit: int = Query(default=50, ge=1, le=100)):
    """Get recent sandbox evaluation history."""
    try:
        from cognitive.sandbox_repair_engine import get_sandbox_repair_engine
        history = get_sandbox_repair_engine().get_history(limit=limit)
        return {"evaluations": history, "count": len(history)}
    except Exception as e:
        return {"evaluations": [], "error": str(e)}


@router.post("/evaluate")
async def evaluate_patch(request: EvaluateRequest):
    """Manually evaluate a patch in the sandbox."""
    try:
        from cognitive.sandbox_repair_engine import get_sandbox_repair_engine
        engine = get_sandbox_repair_engine()
        verdict = engine.evaluate(
            target_file=request.target_file,
            patch_code=request.patch_code,
            run_tests=request.run_tests,
            test_file=request.test_file,
        )
        return verdict.to_dict()
    except Exception as e:
        logger.warning("[SANDBOX-REPAIR-API] Evaluate failed: %s", e)
        return {"passed": False, "rejection_reason": str(e)}
