from fastapi import APIRouter
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bi", tags=["Business Intelligence"])


@router.get("/llm-usage")
async def get_llm_usage() -> Dict[str, Any]:
    """Return LLM usage statistics."""
    return {
        "total_calls": 0,
        "by_provider": {},
        "avg_latency_ms": 0.0,
        "error_rate": 0.0,
    }


@router.get("/memory-stats")
async def get_memory_stats() -> Dict[str, Any]:
    """Return memory subsystem statistics."""
    return {
        "total_memories": 0,
        "by_type": {},
        "storage_mb": 0.0,
    }


@router.get("/event-log")
async def get_event_log() -> List[Dict[str, Any]]:
    """Return recent event log entries."""
    return []
