"""
Brain Controller — single unified entry point for all domain actions.

Replaces the 8 separate brain endpoints with one intelligent router.
All 95+ actions preserved. One auth check. One error handler.
One Genesis key wrapper.

Usage:
  POST /api/v2/{domain}/{action}
  Body: { ...payload }
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Any, Optional, Dict, List
import logging
import time

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2", tags=["Brain Controller v2"])


class BrainPayload(BaseModel):
    class Config:
        extra = "allow"


@router.post("/{domain}/{action}")
async def brain_dispatch(domain: str, action: str, request: Request):
    """
    Universal brain dispatch.
    POST /api/v2/chat/send { "message": "hello", "chat_id": 1 }
    POST /api/v2/system/runtime {}
    POST /api/v2/ai/consensus { "prompt": "analyze this" }
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    from api.brain_api_v2 import call_brain
    from core.resilience import ErrorBoundary

    start = time.time()
    result = None
    with ErrorBoundary("brain.dispatch", fallback={"ok": False, "error": "Request failed"}):
        result = call_brain(domain, action, body)
    if result is None:
        result = {"ok": False, "error": "Request failed"}
    latency = round((time.time() - start) * 1000, 1)

    if not result.get("ok"):
        try:
            from api._genesis_tracker import track
            track(
                key_type="error",
                what=f"v2/{domain}/{action} failed: {result.get('error', '')}",
                who="brain_controller",
                is_error=True,
                error_message=result.get("error", "")[:200],
                tags=["brain", "v2", domain, action, "error"],
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=400 if "Unknown" in result.get("error", "") else 500,
            detail=result.get("error", "Unknown error"),
        )

    try:
        from api._genesis_tracker import track
        track(
            key_type="api_request",
            what=f"v2/{domain}/{action}",
            who="brain_controller",
            how=f"{domain}.{action}",
            output_data={"ok": True, "latency_ms": latency},
            tags=["brain", "v2", domain, action],
        )
    except Exception:
        pass

    return {
        "ok": True,
        "domain": domain,
        "action": action,
        "data": result.get("data"),
        "latency_ms": latency,
    }


@router.get("/directory")
async def directory():
    """List all domains and actions."""
    from api.brain_api_v2 import BRAIN_DIRECTORY
    d = BRAIN_DIRECTORY
    total = sum(len(b["actions"]) for b in d.values())
    return {
        "domains": d,
        "total_domains": len(d),
        "total_actions": total,
        "usage": "POST /api/v2/{domain}/{action} with payload",
    }
