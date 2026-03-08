"""
Learning Memory & Knowledge API — REST endpoints for neighbour-by-neighbour search and auto-ingestion.

These delegate to the Brain (ai) so behaviour is identical; they provide explicit REST routes for:
- Neighbour-by-neighbour (reverse kNN) knowledge gap scan
- Fill gaps from API / web search / FlashCache with auto-ingestion into learning memory
- Learning memory expand (scan + fill in one call)
- List of knowledge-gap sources (for display in Whitelist tab)
- List learning patterns and learning examples from the learning memory DB.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Any, List, Optional
from sqlalchemy.orm import Session

from database.session import get_session

router = APIRouter(prefix="/api/learning-memory", tags=["Learning Memory & Knowledge"])


# Built-in knowledge gap sources — shown in Whitelist "Gap fill" tab
KNOWLEDGE_GAP_SOURCES = [
    {"id": "github", "name": "GitHub", "description": "Repository search (code, docs, readmes)", "url": "https://api.github.com", "setting_key": "GAP_FILL_GITHUB", "icon": "🐙"},
    {"id": "stackoverflow", "name": "Stack Overflow", "description": "Q&A via Stack Exchange API", "url": "https://api.stackexchange.com", "setting_key": "GAP_FILL_STACKOVERFLOW", "icon": "📚"},
    {"id": "arxiv", "name": "arXiv", "description": "Research papers (CS, SE)", "url": "https://arxiv.org", "setting_key": "GAP_FILL_ARXIV", "icon": "📄"},
    {"id": "wikipedia", "name": "Wikipedia", "description": "Concepts, algorithms, standards", "url": "https://en.wikipedia.org", "setting_key": "GAP_FILL_WIKIPEDIA", "icon": "📖"},
    {"id": "hackernews", "name": "Hacker News", "description": "Discussions and tools (Algolia)", "url": "https://hn.algolia.com", "setting_key": "GAP_FILL_HACKERNEWS", "icon": "📰"},
    {"id": "devto", "name": "Dev.to", "description": "Articles by tag", "url": "https://dev.to/api", "setting_key": "GAP_FILL_DEVTO", "icon": "📝"},
    {"id": "pypi", "name": "PyPI", "description": "Python packages", "url": "https://pypi.org", "setting_key": "GAP_FILL_PYPI", "icon": "🐍"},
    {"id": "mdn", "name": "MDN", "description": "Web APIs, JavaScript, CSS, HTML", "url": "https://developer.mozilla.org", "setting_key": "GAP_FILL_MDN", "icon": "🌐"},
    {"id": "semantic_scholar", "name": "Semantic Scholar", "description": "CS/SE research papers", "url": "https://api.semanticscholar.org", "setting_key": "GAP_FILL_SEMANTIC_SCHOLAR", "icon": "🔬"},
    {"id": "npm", "name": "npm", "description": "JavaScript/Node packages", "url": "https://registry.npmjs.org", "setting_key": "GAP_FILL_NPM", "icon": "📦"},
    {"id": "ietf_rfc", "name": "IETF RFC", "description": "Protocols and standards", "url": "https://datatracker.ietf.org", "setting_key": "GAP_FILL_IETF_RFC", "icon": "📋"},
]


@router.get("/knowledge-gap-sources", response_model=dict)
async def get_knowledge_gap_sources():
    """
    List built-in knowledge gap sources (GitHub, Stack Overflow, arXiv, etc.)
    for display in the Whitelist tab. Returns enabled state from settings.
    """
    try:
        from settings import settings
    except Exception:
        settings = None
    out = []
    for s in KNOWLEDGE_GAP_SOURCES:
        enabled = True
        if settings and hasattr(settings, s["setting_key"]):
            enabled = bool(getattr(settings, s["setting_key"], True))
        out.append({
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "url": s["url"],
            "enabled": enabled,
            "icon": s.get("icon", "🔗"),
            "source_type": "gap_fill",
        })
    return {"sources": out}


class FillGapsPayload(BaseModel):
    max_gaps: int = Field(5, ge=1, le=20, description="Max gap topics to fill")
    auto_ingest: bool = Field(True, description="Ingest fetched content into learning memory")


class ExpandPayload(BaseModel):
    max_gaps: int = Field(5, ge=1, le=20, description="Max gap topics to fill after scan")


@router.get("/knowledge-gaps")
async def get_knowledge_gaps():
    """
    Neighbour-by-neighbour search: run reverse kNN gap analysis.
    Returns sparse regions, isolated points, stale clusters, demand gaps.
    """
    from api.brain_api_v2 import call_brain
    result = call_brain("ai", "knowledge_gaps", {})
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("error", "knowledge_gaps failed"))
    return result.get("data", {})


@router.post("/knowledge-gaps/fill")
async def fill_knowledge_gaps(payload: FillGapsPayload = None):
    """
    Auto-ingestion: pull from API, web search, FlashCache and ingest into learning memory.
    Run after a gap scan (or alone to fill from last scan topics).
    """
    from api.brain_api_v2 import call_brain
    pl = payload or FillGapsPayload()
    p = pl.model_dump() if hasattr(pl, "model_dump") else pl.dict()
    result = call_brain("ai", "fill_knowledge_gaps", p)
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("error", "fill_knowledge_gaps failed"))
    return result.get("data", {})


@router.post("/expand")
async def learning_memory_expand(payload: ExpandPayload = None):
    """
    Neighbour-by-neighbour search then auto-ingestion in one call.
    Scans gaps (including learning memory as embedding source), then fills from API/web/FlashCache.
    """
    from api.brain_api_v2 import call_brain
    pl = payload or ExpandPayload()
    p = pl.model_dump() if hasattr(pl, "model_dump") else pl.dict()
    result = call_brain("ai", "learning_memory_expand", p)
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("error", "learning_memory_expand failed"))
    return result.get("data", {})


def _from_json_str(val):
    """Parse stored JSON string to dict or list."""
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            import json as _j
            parsed = _j.loads(val)
            return parsed if isinstance(parsed, (dict, list)) else {"raw": val}
        except Exception:
            return {"raw": val}
    return {"raw": str(val)}


@router.get("/patterns", response_model=dict)
def list_learning_patterns(
    limit: int = Query(100, ge=1, le=500, description="Max patterns to return"),
    pattern_type: Optional[str] = Query(None, description="Filter by pattern_type"),
    session: Session = Depends(get_session),
):
    """
    List learning patterns from the learning memory database.
    Patterns are higher-level abstractions extracted from learning examples.
    """
    try:
        from cognitive.learning_memory import LearningPattern
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import error: {e}")
    try:
        q = session.query(LearningPattern).order_by(LearningPattern.updated_at.desc())
        if pattern_type:
            q = q.filter(LearningPattern.pattern_type == pattern_type)
        rows = q.limit(limit).all()
        out = []
        for p in rows:
            out.append({
                "id": str(p.id) if hasattr(p, "id") else None,
                "created_at": p.created_at.isoformat() if getattr(p, "created_at", None) else None,
                "updated_at": p.updated_at.isoformat() if getattr(p, "updated_at", None) else None,
                "pattern_name": getattr(p, "pattern_name", None),
                "pattern_type": getattr(p, "pattern_type", None),
                "preconditions": _from_json_str(getattr(p, "preconditions", None)),
                "actions": _from_json_str(getattr(p, "actions", None)),
                "expected_outcomes": _from_json_str(getattr(p, "expected_outcomes", None)),
                "trust_score": getattr(p, "trust_score", None),
                "success_rate": getattr(p, "success_rate", None),
                "sample_size": getattr(p, "sample_size", None),
                "supporting_examples": _from_json_str(getattr(p, "supporting_examples", "[]")),
                "times_applied": getattr(p, "times_applied", None),
                "times_succeeded": getattr(p, "times_succeeded", None),
                "times_failed": getattr(p, "times_failed", None),
            })
        return {"patterns": out, "count": len(out)}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/examples", response_model=dict)
def list_learning_examples(
    limit: int = Query(100, ge=1, le=500, description="Max examples to return"),
    example_type: Optional[str] = Query(None, description="Filter by example_type"),
    source: Optional[str] = Query(None, description="Filter by source"),
    session: Session = Depends(get_session),
):
    """
    List learning examples from the learning memory database.
    Examples are concrete experiences Grace has learned from.
    """
    try:
        from cognitive.learning_memory import LearningExample
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import error: {e}")
    try:
        q = session.query(LearningExample).order_by(LearningExample.updated_at.desc())
        if example_type:
            q = q.filter(LearningExample.example_type == example_type)
        if source:
            q = q.filter(LearningExample.source == source)
        rows = q.limit(limit).all()
        out = []
        for e in rows:
            out.append({
                "id": str(e.id) if hasattr(e, "id") else None,
                "created_at": e.created_at.isoformat() if getattr(e, "created_at", None) else None,
                "updated_at": e.updated_at.isoformat() if getattr(e, "updated_at", None) else None,
                "example_type": getattr(e, "example_type", None),
                "input_context": _from_json_str(getattr(e, "input_context", None)),
                "expected_output": _from_json_str(getattr(e, "expected_output", None)),
                "actual_output": _from_json_str(getattr(e, "actual_output", None)),
                "trust_score": getattr(e, "trust_score", None),
                "source": getattr(e, "source", None),
                "times_referenced": getattr(e, "times_referenced", None),
                "times_validated": getattr(e, "times_validated", None),
                "times_invalidated": getattr(e, "times_invalidated", None),
            })
        return {"examples": out, "count": len(out)}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
