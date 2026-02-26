"""
Oracle Knowledge Explorer — Browse and interact with all knowledge.

Makes the Oracle's training data, patterns, episodes, procedures,
and Magma memory readable and interactive. Not just tables — a
navigable knowledge view.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Explorer"])


def _get_db():
    from database.session import SessionLocal
    if SessionLocal is None:
        from database.session import initialize_session_factory
        initialize_session_factory()
        from database.session import SessionLocal as SL
        return SL()
    return SessionLocal()


@router.get("/overview")
async def knowledge_overview():
    """Full overview of all knowledge in the system."""
    db = _get_db()
    if not db:
        return {"available": False}

    from sqlalchemy import text
    result = {}

    try:
        for table, label in [
            ("learning_examples", "Training Data"),
            ("learning_patterns", "Patterns"),
            ("episodes", "Episodes"),
            ("procedures", "Skills"),
            ("documents", "Documents"),
            ("genesis_key", "Genesis Keys"),
        ]:
            try:
                count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
                result[table] = {"label": label, "count": count}
            except Exception:
                result[table] = {"label": label, "count": 0, "note": "table not found"}

        # Magma stats
        try:
            from cognitive.magma_bridge import get_stats
            result["magma"] = get_stats()
        except Exception:
            result["magma"] = {"available": False}

        return result
    finally:
        db.close()


@router.get("/training-data")
async def browse_training_data(page: int = 1, per_page: int = 20, sort: str = "newest", min_trust: float = 0):
    """Browse training data with pagination."""
    db = _get_db()
    if not db:
        return {"items": [], "total": 0}
    from sqlalchemy import text

    try:
        offset = (page - 1) * per_page
        order = "created_at DESC" if sort == "newest" else "trust_score DESC" if sort == "trust" else "created_at ASC"
        trust_filter = f"WHERE trust_score >= {min_trust}" if min_trust > 0 else ""

        total = db.execute(text(f"SELECT COUNT(*) FROM learning_examples {trust_filter}")).scalar() or 0
        rows = db.execute(text(f"""
            SELECT id, example_type, input_context, expected_output, actual_output,
                   trust_score, source, created_at
            FROM learning_examples {trust_filter}
            ORDER BY {order} LIMIT :lim OFFSET :off
        """), {"lim": per_page, "off": offset}).fetchall()

        return {
            "items": [{"id": r[0], "type": r[1], "input": (r[2] or "")[:300],
                        "expected": (r[3] or "")[:300], "actual": (r[4] or "")[:200],
                        "trust": r[5], "source": r[6],
                        "created": r[7].isoformat() if r[7] else None}
                       for r in rows],
            "total": total, "page": page, "per_page": per_page, "pages": (total + per_page - 1) // per_page,
        }
    finally:
        db.close()


@router.get("/training-data/{item_id}")
async def read_training_item(item_id: int):
    """Read a single training data item in full."""
    db = _get_db()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    from sqlalchemy import text

    try:
        row = db.execute(text("SELECT * FROM learning_examples WHERE id = :id"), {"id": item_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")
        cols = row._mapping.keys()
        data = {}
        for c in cols:
            val = row._mapping[c]
            if isinstance(val, datetime):
                val = val.isoformat()
            elif isinstance(val, bytes):
                val = None
            data[c] = val
        return data
    finally:
        db.close()


@router.get("/episodes")
async def browse_episodes(page: int = 1, per_page: int = 20):
    """Browse episodic memory — concrete past experiences."""
    db = _get_db()
    if not db:
        return {"items": [], "total": 0}
    from sqlalchemy import text

    try:
        offset = (page - 1) * per_page
        total = db.execute(text("SELECT COUNT(*) FROM episodes")).scalar() or 0
        rows = db.execute(text("""
            SELECT id, problem, action, outcome, trust_score, source, created_at
            FROM episodes ORDER BY created_at DESC LIMIT :lim OFFSET :off
        """), {"lim": per_page, "off": offset}).fetchall()

        return {
            "items": [{"id": r[0], "problem": (r[1] or "")[:300], "action": (r[2] or "")[:300],
                        "outcome": (r[3] or "")[:300], "trust": r[4], "source": r[5],
                        "created": r[6].isoformat() if r[6] else None}
                       for r in rows],
            "total": total, "page": page,
        }
    finally:
        db.close()


@router.get("/skills")
async def browse_skills(page: int = 1, per_page: int = 20):
    """Browse procedural memory — learned skills."""
    db = _get_db()
    if not db:
        return {"items": [], "total": 0}
    from sqlalchemy import text

    try:
        offset = (page - 1) * per_page
        total = db.execute(text("SELECT COUNT(*) FROM procedures")).scalar() or 0
        rows = db.execute(text("""
            SELECT id, name, goal, procedure_type, trust_score, success_rate, usage_count, created_at
            FROM procedures ORDER BY trust_score DESC LIMIT :lim OFFSET :off
        """), {"lim": per_page, "off": offset}).fetchall()

        return {
            "items": [{"id": r[0], "name": r[1], "goal": (r[2] or "")[:300],
                        "type": r[3], "trust": r[4], "success_rate": r[5],
                        "usage": r[6], "created": r[7].isoformat() if r[7] else None}
                       for r in rows],
            "total": total, "page": page,
        }
    finally:
        db.close()


@router.get("/patterns")
async def browse_patterns(page: int = 1, per_page: int = 20):
    """Browse learned patterns."""
    db = _get_db()
    if not db:
        return {"items": [], "total": 0}
    from sqlalchemy import text

    try:
        offset = (page - 1) * per_page
        total = db.execute(text("SELECT COUNT(*) FROM learning_patterns")).scalar() or 0
        rows = db.execute(text("""
            SELECT id, pattern_name, pattern_type, trust_score, success_rate, created_at
            FROM learning_patterns ORDER BY trust_score DESC LIMIT :lim OFFSET :off
        """), {"lim": per_page, "off": offset}).fetchall()

        return {
            "items": [{"id": r[0], "name": r[1], "type": r[2], "trust": r[3],
                        "success_rate": r[4], "created": r[5].isoformat() if r[5] else None}
                       for r in rows],
            "total": total, "page": page,
        }
    finally:
        db.close()


@router.get("/magma")
async def browse_magma():
    """Browse Magma memory graph statistics and contents."""
    try:
        from cognitive.magma_bridge import get_stats, query_results
        stats = get_stats()
        # Try to get some sample content
        samples = query_results("recent knowledge", limit=5)
        return {"stats": stats, "samples": [str(s)[:200] for s in samples]}
    except Exception as e:
        return {"stats": {"available": False}, "error": str(e)}


@router.post("/search")
async def search_knowledge(query: str, sources: str = "all", limit: int = 10):
    """Search across all knowledge sources."""
    results = []

    db = _get_db()
    if db:
        from sqlalchemy import text

        if sources in ("all", "training"):
            try:
                rows = db.execute(text(
                    "SELECT 'training' as source, id, input_context as content, trust_score FROM learning_examples "
                    "WHERE input_context LIKE :q ORDER BY trust_score DESC LIMIT :lim"
                ), {"q": f"%{query}%", "lim": limit}).fetchall()
                for r in rows:
                    results.append({"source": r[0], "id": r[1], "content": (r[2] or "")[:300], "trust": r[3]})
            except Exception:
                pass

        if sources in ("all", "episodes"):
            try:
                rows = db.execute(text(
                    "SELECT 'episode' as source, id, problem as content, trust_score FROM episodes "
                    "WHERE problem LIKE :q ORDER BY trust_score DESC LIMIT :lim"
                ), {"q": f"%{query}%", "lim": limit}).fetchall()
                for r in rows:
                    results.append({"source": r[0], "id": r[1], "content": (r[2] or "")[:300], "trust": r[3]})
            except Exception:
                pass

        if sources in ("all", "skills"):
            try:
                rows = db.execute(text(
                    "SELECT 'skill' as source, id, name as content, trust_score FROM procedures "
                    "WHERE name LIKE :q OR goal LIKE :q ORDER BY trust_score DESC LIMIT :lim"
                ), {"q": f"%{query}%", "lim": limit}).fetchall()
                for r in rows:
                    results.append({"source": r[0], "id": r[1], "content": (r[2] or "")[:300], "trust": r[3]})
            except Exception:
                pass

        db.close()

    # Search Magma
    if sources in ("all", "magma"):
        try:
            from cognitive.magma_bridge import query_results as mq
            magma_results = mq(query, limit=limit)
            for r in magma_results:
                results.append({"source": "magma", "content": str(r)[:300], "trust": 70})
        except Exception:
            pass

    return {"query": query, "total": len(results), "results": results}


@router.post("/cycle")
async def run_knowledge_cycle(seed: str, context: str = "", max_depth: int = 3, max_kimi_calls: int = 50):
    """Run a knowledge expansion cycle from a seed."""
    from cognitive.knowledge_cycle import KnowledgeExpansionCycle, CycleConfig
    config = CycleConfig(max_depth=max_depth, max_kimi_calls=max_kimi_calls)
    cycle = KnowledgeExpansionCycle(config)
    result = cycle.run_cycle(seed, context)
    return {
        "cycle_id": result.cycle_id, "seed": result.seed,
        "depth": result.depth, "discovered": result.records_discovered,
        "accepted": result.records_accepted, "rejected": result.records_rejected,
        "human_review": result.records_human_review,
        "gaps": result.gaps_identified, "kimi_calls": result.kimi_calls_used,
        "duration_ms": result.duration_ms, "status": result.status,
    }


@router.get("/cycle/history")
async def cycle_history():
    """Get knowledge expansion cycle history."""
    from cognitive.knowledge_cycle import get_knowledge_cycle
    return {"history": get_knowledge_cycle().get_history()}
