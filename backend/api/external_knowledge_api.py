"""
api/external_knowledge_api.py
─────────────────────────────────────────────────────────────────────
External Knowledge Pull API  (Phase 3.2)

Endpoints for monitoring and controlling the external knowledge
pipeline that autonomously detects knowledge gaps and fills them
from GitHub, StackOverflow, arXiv, and other sources.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge/external", tags=["External Knowledge"])


class TopicRequest(BaseModel):
    topic: str


@router.get("/status")
async def get_pipeline_status():
    """Get external knowledge pipeline status and statistics."""
    try:
        from cognitive.external_knowledge_pipeline import get_external_knowledge_pipeline
        return get_external_knowledge_pipeline().get_status()
    except Exception as e:
        logger.warning("[EXT-KNOWLEDGE-API] Status fetch failed: %s", e)
        return {"running": False, "error": str(e)}


@router.get("/history")
async def get_fetch_history(limit: int = Query(default=50, ge=1, le=300)):
    """Get recent external knowledge fetch history."""
    try:
        from cognitive.external_knowledge_pipeline import get_external_knowledge_pipeline
        pipeline = get_external_knowledge_pipeline()
        history = pipeline.get_fetch_history(limit=limit)
        return {"fetches": history, "count": len(history)}
    except Exception as e:
        logger.warning("[EXT-KNOWLEDGE-API] History fetch failed: %s", e)
        return {"fetches": [], "count": 0, "error": str(e)}


@router.post("/pull")
async def pull_topic(request: TopicRequest):
    """Manually pull external knowledge for a specific topic."""
    try:
        from cognitive.external_knowledge_pipeline import get_external_knowledge_pipeline
        result = get_external_knowledge_pipeline().pull_topic(request.topic)
        return result
    except Exception as e:
        logger.warning("[EXT-KNOWLEDGE-API] Pull failed: %s", e)
        return {"topic": request.topic, "error": str(e)}


@router.post("/cycle")
async def force_cycle():
    """Force a full gap-detect + fetch + ingest cycle."""
    try:
        from cognitive.external_knowledge_pipeline import get_external_knowledge_pipeline
        return get_external_knowledge_pipeline().force_cycle()
    except Exception as e:
        logger.warning("[EXT-KNOWLEDGE-API] Cycle failed: %s", e)
        return {"status": "error", "error": str(e)}


@router.post("/start")
async def start_pipeline():
    """Start the external knowledge pipeline."""
    try:
        from cognitive.external_knowledge_pipeline import get_external_knowledge_pipeline
        pipeline = get_external_knowledge_pipeline()
        started = pipeline.start()
        return {"status": "started" if started else "already_running"}
    except Exception as e:
        logger.warning("[EXT-KNOWLEDGE-API] Start failed: %s", e)
        return {"status": "error", "error": str(e)}


@router.post("/stop")
async def stop_pipeline():
    """Stop the external knowledge pipeline."""
    try:
        from cognitive.external_knowledge_pipeline import get_external_knowledge_pipeline
        get_external_knowledge_pipeline().stop()
        return {"status": "stopped"}
    except Exception as e:
        logger.warning("[EXT-KNOWLEDGE-API] Stop failed: %s", e)
        return {"status": "error", "error": str(e)}


@router.get("/sources")
async def get_source_reliability():
    """List all external sources with their reliability weights."""
    try:
        from cognitive.external_knowledge_pipeline import SOURCE_RELIABILITY
        return {
            "sources": [
                {"name": name, "reliability": weight}
                for name, weight in sorted(SOURCE_RELIABILITY.items(), key=lambda x: -x[1])
            ]
        }
    except Exception as e:
        return {"sources": [], "error": str(e)}
