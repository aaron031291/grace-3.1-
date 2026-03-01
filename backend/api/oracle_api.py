"""
Oracle API — Training Data Store & Knowledge Audit

The Oracle is where all training data lives. Kimi audits it,
finds what's missing, and feeds gaps back into the ingestion pipeline.

Aggregates:
- Learning examples (with trust scores)
- Learning patterns (extracted knowledge)
- Episodic memory (concrete experiences)
- Procedural memory (learned skills)
- Vector store document stats
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/oracle", tags=["Oracle"])


def _get_db():
    from database.session import SessionLocal
    if SessionLocal is None:
        from database.session import initialize_session_factory
        initialize_session_factory()
        from database.session import SessionLocal as SL
        return SL()
    return SessionLocal()


class AuditRequest(BaseModel):
    focus: Optional[str] = None
    use_kimi: bool = True


class FillGapRequest(BaseModel):
    topic: str
    method: str = "kimi"  # kimi, websearch, study
    context: Optional[str] = None


# ---------------------------------------------------------------------------
# 1. Dashboard — overview of all training data
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def oracle_dashboard():
    """Full training data overview for the Oracle tab."""
    from sqlalchemy import func, text
    db = _get_db()
    try:
        result: Dict[str, Any] = {"timestamp": datetime.utcnow().isoformat()}

        # Learning examples
        try:
            r = db.execute(text("SELECT COUNT(*), AVG(trust_score) FROM learning_examples"))
            row = r.fetchone()
            result["learning_examples"] = {
                "total": row[0] or 0,
                "avg_trust": round(row[1] or 0, 3),
            }
            # By type
            types = db.execute(text(
                "SELECT example_type, COUNT(*), AVG(trust_score) FROM learning_examples GROUP BY example_type ORDER BY COUNT(*) DESC"
            )).fetchall()
            result["learning_examples"]["by_type"] = [
                {"type": t[0], "count": t[1], "avg_trust": round(t[2] or 0, 3)} for t in types
            ]
            # Top sources
            sources = db.execute(text(
                "SELECT source, COUNT(*) FROM learning_examples GROUP BY source ORDER BY COUNT(*) DESC LIMIT 10"
            )).fetchall()
            result["learning_examples"]["top_sources"] = [{"source": s[0], "count": s[1]} for s in sources]
        except Exception:
            result["learning_examples"] = {"total": 0, "avg_trust": 0}

        # Learning patterns
        try:
            r = db.execute(text("SELECT COUNT(*), AVG(trust_score), AVG(success_rate) FROM learning_patterns"))
            row = r.fetchone()
            result["learning_patterns"] = {
                "total": row[0] or 0,
                "avg_trust": round(row[1] or 0, 3),
                "avg_success_rate": round(row[2] or 0, 3),
            }
        except Exception:
            result["learning_patterns"] = {"total": 0}

        # Episodic memory
        try:
            r = db.execute(text("SELECT COUNT(*), AVG(trust_score) FROM episodes"))
            row = r.fetchone()
            result["episodes"] = {"total": row[0] or 0, "avg_trust": round(row[1] or 0, 3)}
        except Exception:
            result["episodes"] = {"total": 0}

        # Procedural memory
        try:
            r = db.execute(text("SELECT COUNT(*), AVG(trust_score), AVG(success_rate) FROM procedures"))
            row = r.fetchone()
            result["procedures"] = {
                "total": row[0] or 0,
                "avg_trust": round(row[1] or 0, 3),
                "avg_success_rate": round(row[2] or 0, 3),
            }
        except Exception:
            result["procedures"] = {"total": 0}

        # Vector store
        try:
            from vector_db.client import get_qdrant_client
            client = get_qdrant_client()
            coll = client.get_collection("documents")
            result["vector_store"] = {
                "collection": "documents",
                "vectors": coll.vectors_count,
                "points": coll.points_count,
            }
        except Exception:
            result["vector_store"] = {"vectors": 0}

        # Documents
        try:
            r = db.execute(text("SELECT COUNT(*), SUM(total_chunks) FROM documents WHERE status = 'completed'"))
            row = r.fetchone()
            result["documents"] = {"total": row[0] or 0, "total_chunks": row[1] or 0}
        except Exception:
            result["documents"] = {"total": 0}

        return result
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 2. Training data listing — learning examples with pagination
# ---------------------------------------------------------------------------

@router.get("/training-data")
async def list_training_data(
    example_type: Optional[str] = None,
    min_trust: float = 0.0,
    sort: str = "newest",
    limit: int = 100,
    offset: int = 0,
):
    """List training data (learning examples)."""
    from sqlalchemy import text
    db = _get_db()
    try:
        conditions = ["1=1"]
        params: Dict[str, Any] = {"lim": limit, "off": offset}

        if example_type:
            conditions.append("example_type = :et")
            params["et"] = example_type
        if min_trust > 0:
            conditions.append("trust_score >= :mt")
            params["mt"] = min_trust

        order = "created_at DESC" if sort == "newest" else "trust_score DESC" if sort == "trust" else "created_at ASC"
        where = " AND ".join(conditions)

        count_r = db.execute(text(f"SELECT COUNT(*) FROM learning_examples WHERE {where}"), params)
        total = count_r.scalar() or 0

        rows = db.execute(text(f"""
            SELECT id, example_type, input_context, expected_output, actual_output,
                   trust_score, source, file_path, created_at
            FROM learning_examples
            WHERE {where}
            ORDER BY {order}
            LIMIT :lim OFFSET :off
        """), params).fetchall()

        examples = []
        for r in rows:
            examples.append({
                "id": r[0], "type": r[1],
                "input": (r[2] or "")[:300], "expected_output": (r[3] or "")[:300],
                "actual_output": (r[4] or "")[:200],
                "trust_score": r[5], "source": r[6], "file_path": r[7],
                "created_at": r[8].isoformat() if r[8] else None,
            })

        return {"total": total, "offset": offset, "limit": limit, "examples": examples}
    finally:
        db.close()


@router.get("/training-data/{example_id}")
async def get_training_example(example_id: int):
    """Get full detail of a training example."""
    from sqlalchemy import text
    db = _get_db()
    try:
        r = db.execute(text(
            "SELECT * FROM learning_examples WHERE id = :eid"
        ), {"eid": example_id}).fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Example not found")

        cols = r._mapping.keys()
        data = {c: r._mapping[c] for c in cols}
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.isoformat()
            elif isinstance(v, bytes):
                data[k] = None
        return data
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. Patterns and procedures
# ---------------------------------------------------------------------------

@router.get("/patterns")
async def list_patterns(limit: int = 50):
    """List learned patterns."""
    from sqlalchemy import text
    db = _get_db()
    try:
        rows = db.execute(text("""
            SELECT id, pattern_name, pattern_type, trust_score, success_rate, created_at
            FROM learning_patterns ORDER BY trust_score DESC LIMIT :lim
        """), {"lim": limit}).fetchall()
        return {"total": len(rows), "patterns": [
            {"id": r[0], "name": r[1], "type": r[2], "trust": r[3], "success_rate": r[4],
             "created_at": r[5].isoformat() if r[5] else None}
            for r in rows
        ]}
    finally:
        db.close()


@router.get("/procedures")
async def list_procedures(limit: int = 50):
    """List learned procedures (skills)."""
    from sqlalchemy import text
    db = _get_db()
    try:
        rows = db.execute(text("""
            SELECT id, name, goal, procedure_type, trust_score, success_rate, usage_count, created_at
            FROM procedures ORDER BY trust_score DESC LIMIT :lim
        """), {"lim": limit}).fetchall()
        return {"total": len(rows), "procedures": [
            {"id": r[0], "name": r[1], "goal": r[2], "type": r[3],
             "trust": r[4], "success_rate": r[5], "usage_count": r[6],
             "created_at": r[7].isoformat() if r[7] else None}
            for r in rows
        ]}
    finally:
        db.close()


@router.get("/episodes")
async def list_episodes(limit: int = 50):
    """List episodic memories (experiences)."""
    from sqlalchemy import text
    db = _get_db()
    try:
        rows = db.execute(text("""
            SELECT id, problem, action, outcome, trust_score, source, created_at
            FROM episodes ORDER BY created_at DESC LIMIT :lim
        """), {"lim": limit}).fetchall()
        return {"total": len(rows), "episodes": [
            {"id": r[0], "problem": (r[1] or "")[:200], "action": (r[2] or "")[:200],
             "outcome": (r[3] or "")[:200], "trust": r[4], "source": r[5],
             "created_at": r[6].isoformat() if r[6] else None}
            for r in rows
        ]}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 4. Kimi Audit — audit training data quality and find gaps
# ---------------------------------------------------------------------------

@router.post("/audit")
async def audit_training_data(request: AuditRequest):
    """
    Kimi audits the training data, finds quality issues,
    identifies gaps, and suggests what to learn next.
    """
    dashboard = await oracle_dashboard()

    focus_text = f"\nFocus area: {request.focus}" if request.focus else ""

    prompt = (
        f"Audit this AI training data store and provide:\n"
        f"1. Quality assessment — are trust scores healthy?\n"
        f"2. Coverage gaps — what topics or skills are missing?\n"
        f"3. Recommendations — what should be learned next?\n"
        f"4. Data quality issues — low-trust data that needs review\n"
        f"5. Actionable items to feed back into the ingestion pipeline\n"
        f"{focus_text}\n\n"
        f"Training Data Summary:\n"
        f"- Learning Examples: {dashboard.get('learning_examples', {}).get('total', 0)} "
        f"(avg trust: {dashboard.get('learning_examples', {}).get('avg_trust', 0)})\n"
        f"- Types: {json.dumps(dashboard.get('learning_examples', {}).get('by_type', []))}\n"
        f"- Sources: {json.dumps(dashboard.get('learning_examples', {}).get('top_sources', []))}\n"
        f"- Patterns: {dashboard.get('learning_patterns', {}).get('total', 0)} "
        f"(avg trust: {dashboard.get('learning_patterns', {}).get('avg_trust', 0)})\n"
        f"- Episodes: {dashboard.get('episodes', {}).get('total', 0)}\n"
        f"- Procedures: {dashboard.get('procedures', {}).get('total', 0)} "
        f"(avg success: {dashboard.get('procedures', {}).get('avg_success_rate', 0)})\n"
        f"- Documents: {dashboard.get('documents', {}).get('total', 0)} "
        f"({dashboard.get('documents', {}).get('total_chunks', 0)} chunks)\n"
        f"- Vectors: {dashboard.get('vector_store', {}).get('vectors', 0)}\n"
    )

    try:
        if request.use_kimi:
            from llm_orchestrator.factory import get_kimi_client
            client = get_kimi_client()
            provider = "kimi"
        else:
            from llm_orchestrator.factory import get_llm_client
            client = get_llm_client()
            provider = "local"

        response = client.generate(
            prompt=prompt,
            system_prompt="You are the Oracle — Grace's training data auditor. Analyse the training data store, identify quality issues and gaps, and recommend what to learn next.",
            temperature=0.3, max_tokens=4096,
        )

        from api._genesis_tracker import track
        track(key_type="ai_response", what=f"Oracle audit{' — ' + request.focus if request.focus else ''}",
              how="POST /api/oracle/audit", tags=["oracle", "audit", provider])

        return {"audit": response, "provider": provider, "dashboard_snapshot": dashboard}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 5. Fill gaps — feed missing knowledge into ingestion pipeline
# ---------------------------------------------------------------------------

@router.post("/fill-gap")
async def fill_knowledge_gap(request: FillGapRequest, background_tasks: BackgroundTasks):
    """
    Fill a knowledge gap by triggering learning.
    Methods: kimi (ask Kimi), websearch (scrape), study (self-study).
    The result gets fed back into the ingestion pipeline.
    """
    from api._genesis_tracker import track

    result = {"topic": request.topic, "method": request.method, "status": "processing"}

    if request.method == "kimi":
        try:
            from llm_orchestrator.factory import get_kimi_client
            client = get_kimi_client()
            context_text = f"\nAdditional context: {request.context}" if request.context else ""
            response = client.generate(
                prompt=f"Research this topic thoroughly and provide comprehensive, structured knowledge that can be used as training data:\n\nTopic: {request.topic}{context_text}",
                system_prompt="You are Grace's Oracle. Generate high-quality training data and knowledge for the given topic. Be comprehensive and structured.",
                temperature=0.3, max_tokens=4096,
            )
            result["knowledge"] = response
            result["status"] = "completed"

            background_tasks.add_task(_ingest_knowledge, request.topic, response)
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "failed"

    elif request.method == "websearch":
        try:
            # Register the search intent in FlashCache for future lookups
            try:
                from cognitive.flash_cache import get_flash_cache
                fc = get_flash_cache()
                kw = fc.extract_keywords(request.topic)
                fc.register(
                    source_uri=f"https://www.google.com/search?q={request.topic.replace(' ', '+')}",
                    source_type="search",
                    source_name=f"Search: {request.topic}",
                    keywords=kw,
                    summary=f"Web search for topic: {request.topic}",
                    trust_score=0.4,
                    ttl_hours=24,
                    metadata={"oracle_topic": request.topic},
                )
            except Exception:
                pass
            result["status"] = "search_initiated"
            result["note"] = "Use the Whitelist tab's web sources to add specific URLs for deep scraping"
        except Exception as e:
            result["error"] = str(e)

    elif request.method == "study":
        background_tasks.add_task(_run_self_study, request.topic)
        result["status"] = "study_queued"

    track(key_type="system", what=f"Oracle gap fill: {request.topic} via {request.method}",
          how="POST /api/oracle/fill-gap",
          input_data={"topic": request.topic, "method": request.method},
          tags=["oracle", "gap_fill", request.method])

    return result


async def _ingest_knowledge(topic: str, knowledge: str):
    """Ingest Kimi-generated knowledge into the learning memory."""
    try:
        db = _get_db()
        from sqlalchemy import text
        db.execute(text("""
            INSERT INTO learning_examples (example_type, input_context, expected_output, trust_score, source, created_at, updated_at)
            VALUES (:et, :ic, :eo, :ts, :src, :now, :now)
        """), {
            "et": "oracle_knowledge",
            "ic": f"Topic: {topic}",
            "eo": knowledge[:10000],
            "ts": 0.7,
            "src": "oracle_kimi",
            "now": datetime.utcnow(),
        })
        db.commit()
        db.close()
        logger.info(f"[ORACLE] Ingested knowledge for topic: {topic}")
    except Exception as e:
        logger.error(f"[ORACLE] Knowledge ingestion failed: {e}")


def _run_self_study(topic: str):
    logger.info(f"[ORACLE] Self-study queued for: {topic}")


# ---------------------------------------------------------------------------
# 6. Trust score distribution
# ---------------------------------------------------------------------------

@router.get("/trust-distribution")
async def trust_distribution():
    """Get trust score distribution across all training data."""
    from sqlalchemy import text
    db = _get_db()
    try:
        buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
        rows = db.execute(text("SELECT trust_score FROM learning_examples")).fetchall()
        for (ts,) in rows:
            if ts < 0.2: buckets["0.0-0.2"] += 1
            elif ts < 0.4: buckets["0.2-0.4"] += 1
            elif ts < 0.6: buckets["0.4-0.6"] += 1
            elif ts < 0.8: buckets["0.6-0.8"] += 1
            else: buckets["0.8-1.0"] += 1

        return {"total": len(rows), "distribution": buckets}
    finally:
        db.close()


@router.post("/search-rag")
async def oracle_rag_search(query: str, limit: int = 10):
    """Search the knowledge base via RAG for training-relevant content."""
    try:
        from retrieval.retriever import DocumentRetriever
        from embedding.embedder import get_embedding_model
        from vector_db.client import get_qdrant_client
        retriever = DocumentRetriever(embedding_model=get_embedding_model(), qdrant_client=get_qdrant_client())
        chunks = retriever.retrieve(query=query, limit=limit, score_threshold=0.3)
        return {"query": query, "results": [
            {"text": c.get("text", "")[:300], "score": c.get("score", 0),
             "source": c.get("metadata", {}).get("filename", "")}
            for c in chunks
        ]}
    except Exception as e:
        return {"query": query, "results": [], "error": str(e)}


@router.post("/feedback")
async def oracle_feedback(prompt: str, output: str, outcome: str, correction: str = ""):
    """Record feedback for learning — closes the loop."""
    from cognitive.pipeline import FeedbackLoop
    FeedbackLoop.record_outcome(genesis_key="", prompt=prompt, output=output, outcome=outcome, correction=correction)
    return {"recorded": True, "outcome": outcome}
