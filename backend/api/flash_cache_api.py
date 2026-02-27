"""
FlashCache API — Reference-Based Intelligent Caching

Instead of downloading full content, stores source URIs + metadata (keywords,
summaries, trust scores) and streams content on demand from the original source.

Endpoints:
  POST   /api/flash-cache/register     — register a source reference
  GET    /api/flash-cache/lookup       — keyword-based fast lookup
  GET    /api/flash-cache/search       — full-text search across all fields
  GET    /api/flash-cache/stream/{id}  — fetch content from source on demand
  GET    /api/flash-cache/validate/{id}— check if source is still accessible
  GET    /api/flash-cache/predict      — predict keywords related to a topic
  GET    /api/flash-cache/entry/{id}   — get entry metadata
  DELETE /api/flash-cache/entry/{id}   — remove an entry
  PATCH  /api/flash-cache/trust/{id}   — adjust trust score
  GET    /api/flash-cache/stats        — cache statistics
  POST   /api/flash-cache/bulk-register— register multiple sources at once
  POST   /api/flash-cache/extract-keywords — extract keywords from text
  POST   /api/flash-cache/cleanup      — remove stale unreachable entries
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/flash-cache", tags=["FlashCache"])


class RegisterRequest(BaseModel):
    source_uri: str
    source_type: str = "web"  # web, api, search, internal, document
    source_name: str = ""
    keywords: Optional[List[str]] = None
    summary: str = ""
    headers: Optional[Dict[str, str]] = None
    auth_type: str = "none"  # none, bearer, api_key, basic
    trust_score: float = 0.5
    ttl_hours: int = 72
    metadata: Optional[Dict[str, Any]] = None
    auto_extract_keywords: bool = True


class BulkRegisterRequest(BaseModel):
    entries: List[RegisterRequest]


class TrustUpdateRequest(BaseModel):
    delta: float  # positive to increase, negative to decrease


class ExtractKeywordsRequest(BaseModel):
    text: str
    max_keywords: int = 20


def _get_cache():
    from cognitive.flash_cache import get_flash_cache
    return get_flash_cache()


# ── Registration ──────────────────────────────────────────────────────

@router.post("/register")
async def register_source(req: RegisterRequest):
    """
    Register a source reference in the flash cache.
    Only stores the URI + metadata — no content is downloaded.
    If auto_extract_keywords is True, keywords are extracted from the summary.
    """
    cache = _get_cache()

    keywords = req.keywords or []
    if req.auto_extract_keywords and req.summary:
        extracted = cache.extract_keywords(req.summary)
        keywords = list(set(keywords + extracted))

    entry_id = cache.register(
        source_uri=req.source_uri,
        source_type=req.source_type,
        source_name=req.source_name,
        keywords=keywords,
        summary=req.summary,
        content_hash="",
        headers=req.headers,
        auth_type=req.auth_type,
        trust_score=req.trust_score,
        ttl_hours=req.ttl_hours,
        metadata=req.metadata,
    )

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"FlashCache registered: {req.source_name or req.source_uri[:60]}",
            how="POST /api/flash-cache/register",
            output_data={"entry_id": entry_id, "type": req.source_type, "keywords": keywords[:10]},
            tags=["flash_cache", "register", req.source_type],
        )
    except Exception:
        pass

    return {
        "registered": True,
        "entry_id": entry_id,
        "keywords": keywords,
        "source_type": req.source_type,
    }


@router.post("/bulk-register")
async def bulk_register(req: BulkRegisterRequest):
    """Register multiple sources at once."""
    cache = _get_cache()
    results = []
    for entry in req.entries:
        keywords = entry.keywords or []
        if entry.auto_extract_keywords and entry.summary:
            extracted = cache.extract_keywords(entry.summary)
            keywords = list(set(keywords + extracted))

        eid = cache.register(
            source_uri=entry.source_uri,
            source_type=entry.source_type,
            source_name=entry.source_name,
            keywords=keywords,
            summary=entry.summary,
            headers=entry.headers,
            auth_type=entry.auth_type,
            trust_score=entry.trust_score,
            ttl_hours=entry.ttl_hours,
            metadata=entry.metadata,
        )
        results.append({"entry_id": eid, "source_uri": entry.source_uri})

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"FlashCache bulk registered: {len(results)} sources",
            how="POST /api/flash-cache/bulk-register",
            tags=["flash_cache", "bulk_register"],
        )
    except Exception:
        pass

    return {"registered": len(results), "entries": results}


# ── Lookup & Search ───────────────────────────────────────────────────

@router.get("/lookup")
async def lookup(
    keyword: Optional[str] = None,
    keywords: Optional[str] = None,
    source_type: Optional[str] = None,
    min_trust: float = 0.0,
    limit: int = 50,
):
    """
    Fast keyword lookup. Returns matching entries WITHOUT downloading content.
    Pass comma-separated keywords for multi-keyword search.
    """
    cache = _get_cache()
    kw_list = []
    if keywords:
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    results = cache.lookup(
        keyword=keyword,
        keywords=kw_list if kw_list else None,
        source_type=source_type,
        min_trust=min_trust,
        limit=limit,
    )

    # Serialise sets/non-JSON types
    for r in results:
        if isinstance(r.get("keywords"), (set, list)):
            r["keywords"] = list(r["keywords"]) if isinstance(r["keywords"], set) else r["keywords"]

    return {"count": len(results), "results": results}


@router.get("/search")
async def search_cache(
    q: str,
    source_type: Optional[str] = None,
    min_trust: float = 0.0,
    limit: int = 50,
):
    """
    Full-text search across keywords, summaries, and source names.
    More flexible than lookup — splits query into tokens.
    """
    cache = _get_cache()
    results = cache.search(q, source_type=source_type, min_trust=min_trust, limit=limit)

    for r in results:
        if isinstance(r.get("keywords"), (set, list)):
            r["keywords"] = list(r["keywords"]) if isinstance(r["keywords"], set) else r["keywords"]

    return {"query": q, "count": len(results), "results": results}


# ── On-Demand Content Streaming ───────────────────────────────────────

@router.get("/stream/{entry_id}")
async def stream_content(entry_id: str, timeout: int = 30):
    """
    Fetch content from the original source ON DEMAND.
    This is the only time actual data is downloaded.
    Updates access count, checks for changes since last fetch.
    """
    cache = _get_cache()
    result = cache.stream_content(entry_id, timeout=timeout)

    if "error" in result and "not found" in result["error"].lower():
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/validate/{entry_id}")
async def validate_entry(entry_id: str):
    """
    Check if source is still accessible without downloading content.
    Uses HEAD request — fast and cheap.
    """
    cache = _get_cache()
    return cache.validate(entry_id)


# ── Prediction & Discovery ────────────────────────────────────────────

@router.get("/predict")
async def predict_keywords(topic: str, depth: int = 2):
    """
    Pre-emptive keyword discovery. Given a topic, find related keywords
    across the cache that the user might need next.

    Uses keyword co-occurrence analysis across cached entries.
    """
    cache = _get_cache()
    predictions = cache.predict_keywords(topic, depth=depth)
    return {
        "topic": topic,
        "depth": depth,
        "predictions": predictions,
        "count": len(predictions),
    }


@router.post("/extract-keywords")
async def extract_keywords(req: ExtractKeywordsRequest):
    """Extract keywords from arbitrary text. Useful for indexing."""
    cache = _get_cache()
    keywords = cache.extract_keywords(req.text, max_keywords=req.max_keywords)
    return {"keywords": keywords, "count": len(keywords)}


# ── Entry Management ──────────────────────────────────────────────────

@router.get("/entry/{entry_id}")
async def get_entry(entry_id: str):
    """Get full metadata for a cached entry."""
    cache = _get_cache()
    entry = cache._get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    d = entry.to_dict()
    if isinstance(d.get("keywords"), (set,)):
        d["keywords"] = list(d["keywords"])
    return d


@router.delete("/entry/{entry_id}")
async def delete_entry(entry_id: str):
    """Remove an entry from the cache."""
    cache = _get_cache()
    cache.remove(entry_id)

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"FlashCache entry removed: {entry_id}",
            how="DELETE /api/flash-cache/entry",
            tags=["flash_cache", "delete"],
        )
    except Exception:
        pass

    return {"deleted": True, "entry_id": entry_id}


@router.patch("/trust/{entry_id}")
async def update_trust(entry_id: str, req: TrustUpdateRequest):
    """Adjust trust score for an entry. Positive delta increases, negative decreases."""
    cache = _get_cache()
    entry = cache._get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    old_trust = entry.trust_score
    cache.update_trust(entry_id, req.delta)
    new_entry = cache._get_entry(entry_id)

    return {
        "entry_id": entry_id,
        "old_trust": old_trust,
        "new_trust": new_entry.trust_score if new_entry else old_trust + req.delta,
        "delta": req.delta,
    }


# ── Stats & Maintenance ──────────────────────────────────────────────

@router.get("/stats")
async def cache_stats():
    """Get comprehensive cache statistics."""
    cache = _get_cache()
    return cache.stats()


@router.post("/cleanup")
async def cleanup_stale(max_age_hours: Optional[int] = None):
    """Remove stale unreachable entries. Returns count of entries removed."""
    cache = _get_cache()
    removed = cache.cleanup_stale(max_age_hours=max_age_hours)

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"FlashCache cleanup: removed {removed} stale entries",
            how="POST /api/flash-cache/cleanup",
            tags=["flash_cache", "cleanup"],
        )
    except Exception:
        pass

    return {"removed": removed}
