"""
Self-Healing & Vector Search API

Endpoints for:
- System health monitoring
- Component status tracking
- Auto-healing triggers
- Vector search across knowledge base and genesis keys
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["Self-Healing & Vector Search"])


class VectorSearchRequest(BaseModel):
    query: str
    collection: str = "documents"
    limit: int = 10
    threshold: Optional[float] = None


class HealRequest(BaseModel):
    component: str


@router.get("/status")
async def get_system_health():
    """Get real-time system health status for all components."""
    from cognitive.self_healing_tracker import get_self_healing_tracker
    tracker = get_self_healing_tracker()
    return tracker.get_system_health()


@router.post("/check")
async def run_health_check():
    """Actively probe all components and return health results."""
    from cognitive.self_healing_tracker import get_self_healing_tracker
    tracker = get_self_healing_tracker()
    results = tracker.run_health_check()
    return {
        "probe_results": results,
        "system_health": tracker.get_system_health(),
    }


@router.post("/heal")
async def trigger_heal(req: HealRequest):
    """Manually trigger healing for a specific component."""
    from cognitive.self_healing_tracker import get_self_healing_tracker
    tracker = get_self_healing_tracker()
    tracker.report_error(req.component, "Manual heal trigger", auto_heal=True)
    health = tracker.get_system_health()
    comp = health["components"].get(req.component, {})
    return {
        "component": req.component,
        "new_status": comp.get("status", "unknown"),
        "healing_attempts": comp.get("healing_attempts", 0),
    }


@router.post("/vector-search")
async def vector_search(req: VectorSearchRequest):
    """
    Vector search across knowledge base, genesis keys, or any Qdrant collection.
    Uses real embeddings when available, falls back to hash-based vectors.
    """
    from cognitive.self_healing_tracker import get_self_healing_tracker
    tracker = get_self_healing_tracker()

    try:
        from vector_db.client import get_qdrant_client
        qdrant = get_qdrant_client()

        if not qdrant.is_connected():
            connected = qdrant.connect()
            if not connected:
                tracker.report_error("vector_search", "Qdrant not connected")
                raise HTTPException(status_code=503, detail="Vector search unavailable: Qdrant not connected")

        tracker.report_healthy("vector_search")

        # Generate query embedding
        query_vector = _get_query_vector(req.query)

        if not query_vector:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")

        results = qdrant.search_vectors(
            collection_name=req.collection,
            query_vector=query_vector,
            limit=req.limit,
            score_threshold=req.threshold,
        )

        tracker.report_healthy("qdrant")

        return {
            "query": req.query,
            "collection": req.collection,
            "results": results,
            "total": len(results),
        }

    except HTTPException:
        raise
    except Exception as e:
        tracker.report_error("vector_search", str(e))
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Vector search failed: {e}")


@router.post("/stress-test")
async def run_stress_test():
    """Run an on-demand stress test cycle — tests all components, heals failures."""
    from cognitive.realtime_diagnostics import run_stress_cycle
    from dataclasses import asdict
    report = run_stress_cycle()
    return asdict(report)


@router.get("/diagnostics")
async def get_diagnostics():
    """Get latest diagnostic report and recent history."""
    from cognitive.realtime_diagnostics import get_latest_report, get_report_history
    from dataclasses import asdict
    latest = get_latest_report()
    history = get_report_history(limit=10)
    return {
        "latest": asdict(latest) if latest else None,
        "history": history,
        "continuous_active": True,
    }


@router.get("/diagnostics/history")
async def get_diagnostics_history(limit: int = 20):
    """Get diagnostic report history."""
    from cognitive.realtime_diagnostics import get_report_history
    return {"reports": get_report_history(limit=limit)}


def _get_query_vector(query: str) -> Optional[list]:
    """Generate embedding for a search query."""
    try:
        from embedding.embedder import get_embedding_model
        model = get_embedding_model()
        embedding = model.embed_text(query, convert_to_numpy=True)
        return embedding.tolist()
    except Exception as e:
        logger.warning(f"Real embedding failed, using hash fallback: {e}")

    try:
        import hashlib
        raw = hashlib.sha384(query.encode()).digest()
        return [b / 255.0 for b in raw]
    except Exception:
        return None
