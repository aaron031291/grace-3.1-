"""
Magma Bridge — Connects Magma Memory to every system in Grace.

Single integration point that:
- Pipeline queries Magma for context before generation
- Pipeline stores outcomes in Magma after generation
- Immune system stores healing patterns and decisions
- Trust engine queries causal relationships
- Coding agent gets project-relevant memory
- World model includes Magma stats
- Feedback loop stores experiences as patterns/decisions/procedures

This replaces scattered try/except imports with one reliable bridge.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

_magma = None
_available = None


def _get_magma():
    """Get or create Magma singleton. Returns None if unavailable."""
    global _magma, _available
    if _available is False:
        return None
    if _magma is not None:
        return _magma
    try:
        from cognitive.magma.grace_magma_system import get_grace_magma
        _magma = get_grace_magma()
        _available = True
        return _magma
    except Exception as e:
        logger.debug(f"Magma unavailable: {e}")
        _available = False
        return None


def is_available() -> bool:
    return _get_magma() is not None


# ── Query ──────────────────────────────────────────────────────────────

def query_context(query: str, limit: int = 5) -> str:
    """Query Magma for relevant context. Returns text for LLM prompt."""
    m = _get_magma()
    if not m:
        return ""
    try:
        ctx = m.get_context(query, limit=limit)
        return ctx if isinstance(ctx, str) else str(ctx)[:2000]
    except Exception:
        return ""


def query_results(query: str, limit: int = 5) -> List[Dict]:
    """Query Magma for structured results."""
    m = _get_magma()
    if not m:
        return []
    try:
        results = m.query(query, limit=limit)
        return results if isinstance(results, list) else []
    except Exception:
        return []


def query_causal(question: str) -> Optional[str]:
    """Ask Magma WHY something happens — causal reasoning."""
    m = _get_magma()
    if not m:
        return None
    try:
        result = m.why(question)
        return str(result) if result else None
    except Exception:
        return None


# ── Ingest ─────────────────────────────────────────────────────────────

def ingest(content: str, source: str = "system", metadata: Dict = None):
    """Ingest content into Magma memory."""
    m = _get_magma()
    if not m:
        return
    try:
        m.ingest(content, source=source, metadata=metadata or {})
    except Exception:
        pass


def store_pattern(pattern_type: str, description: str, data: Dict = None):
    """Store a pattern (from immune system, pipeline, etc.)."""
    m = _get_magma()
    if not m:
        return
    try:
        m.store_pattern(pattern_type, description, data=data or {})
    except Exception:
        pass


def store_decision(action: str, target: str, rationale: str, data: Dict = None):
    """Store a decision (OODA, healing, governance)."""
    m = _get_magma()
    if not m:
        return
    try:
        m.store_decision(action, target, rationale, data=data or {})
    except Exception:
        pass


def store_procedure(name: str, description: str, steps: List[str] = None):
    """Store a learned procedure (skill)."""
    m = _get_magma()
    if not m:
        return
    try:
        m.store_procedure(name, description, steps=steps or [])
    except Exception:
        pass


# ── Stats ──────────────────────────────────────────────────────────────

def get_stats() -> Dict[str, Any]:
    """Get Magma memory statistics."""
    m = _get_magma()
    if not m:
        return {"available": False}
    try:
        if hasattr(m, 'get_stats'):
            return {"available": True, **m.get_stats()}
        if hasattr(m, 'stats'):
            return {"available": True, **m.stats}
        return {"available": True}
    except Exception:
        return {"available": True, "error": "stats unavailable"}
