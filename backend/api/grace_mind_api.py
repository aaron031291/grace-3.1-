"""
GraceMind API — Unified intelligence endpoints.

/mind/think   — Send any intent through the full intelligence pipeline
/mind/status  — Introspection: what GraceMind knows about itself
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mind", tags=["GraceMind"])


class ThinkRequest(BaseModel):
    intent: str
    payload: Optional[Dict[str, Any]] = {}
    task_type: Optional[str] = None
    source: str = "user"
    skip_ooda: bool = False
    skip_trust: bool = False


@router.post("/think")
def mind_think(req: ThinkRequest):
    """
    Send any intent through the unified GraceMind pipeline.
    All subsystems engaged: OODA → Brains → Trust → Consensus → Memory → Audit.
    """
    from core.grace_mind import get_grace_mind
    mind = get_grace_mind()
    return mind.think(
        intent=req.intent,
        payload=req.payload or {},
        task_type=req.task_type,
        source=req.source,
        skip_ooda=req.skip_ooda,
        skip_trust=req.skip_trust,
    )


@router.get("/status")
def mind_status():
    """GraceMind introspection — subsystem connectivity, trust state, decision count."""
    from core.grace_mind import get_grace_mind
    return get_grace_mind().status()
