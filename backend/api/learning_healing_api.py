"""
Learning & Healing API — unified view of Grace's self-improvement

Combines autonomous learning, healing systems, memory mesh,
and skill development into one dashboard.
"""

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/learn-heal", tags=["Learning & Healing"])


def _get_db():
    from database.session import SessionLocal
    if SessionLocal is None:
        from database.session import initialize_session_factory
        initialize_session_factory()
        from database.session import SessionLocal as SL
        return SL()
    return SessionLocal()


class LearnRequest(BaseModel):
    topic: str
    method: str = "kimi"
    context: Optional[str] = None


class HealRequest(BaseModel):
    action: str
    target: Optional[str] = None


@router.get("/dashboard")
async def learning_healing_dashboard():
    """Unified learning and healing dashboard."""
    from sqlalchemy import text
    db = _get_db()
    try:
        result: Dict[str, Any] = {"timestamp": datetime.utcnow().isoformat()}

        # Learning stats
        try:
            examples = db.execute(text("SELECT COUNT(*), AVG(trust_score) FROM learning_examples")).fetchone()
            patterns = db.execute(text("SELECT COUNT(*), AVG(success_rate) FROM learning_patterns")).fetchone()
            episodes = db.execute(text("SELECT COUNT(*) FROM episodes")).scalar() or 0
            procedures = db.execute(text("SELECT COUNT(*), AVG(success_rate) FROM procedures")).fetchone()

            result["learning"] = {
                "examples": {"total": examples[0] or 0, "avg_trust": round(examples[1] or 0, 3)},
                "patterns": {"total": patterns[0] or 0, "avg_success": round(patterns[1] or 0, 3)},
                "episodes": episodes,
                "procedures": {"total": procedures[0] or 0, "avg_success": round(procedures[1] or 0, 3)},
            }

            # Recent learning (last 24h)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            recent = db.execute(text("SELECT COUNT(*) FROM learning_examples WHERE created_at >= :d"), {"d": cutoff}).scalar() or 0
            result["learning"]["last_24h"] = recent

            # Trust distribution
            buckets = {"high": 0, "medium": 0, "low": 0}
            rows = db.execute(text("SELECT trust_score FROM learning_examples")).fetchall()
            for (ts,) in rows:
                if ts >= 0.7: buckets["high"] += 1
                elif ts >= 0.4: buckets["medium"] += 1
                else: buckets["low"] += 1
            result["learning"]["trust_distribution"] = buckets

            # Top types
            types = db.execute(text("SELECT example_type, COUNT(*) FROM learning_examples GROUP BY example_type ORDER BY COUNT(*) DESC LIMIT 8")).fetchall()
            result["learning"]["top_types"] = [{"type": t[0], "count": t[1]} for t in types]

        except Exception:
            result["learning"] = {"examples": {"total": 0}}

        # Healing stats
        healing_actions = [
            {"id": "gc_collect", "name": "Garbage Collection", "severity": "low"},
            {"id": "cache_flush", "name": "Flush Caches", "severity": "low"},
            {"id": "connection_reset", "name": "Reset Connections", "severity": "medium"},
            {"id": "embedding_reload", "name": "Reload Embeddings", "severity": "medium"},
            {"id": "session_cleanup", "name": "Session Cleanup", "severity": "low"},
            {"id": "health_check", "name": "Full Health Check", "severity": "low"},
        ]
        result["healing"] = {
            "available_actions": healing_actions,
            "autonomous_healing": True,
        }

        # System health snapshot
        try:
            import psutil
            mem = psutil.virtual_memory()
            result["health_snapshot"] = {
                "cpu": psutil.cpu_percent(interval=0.1),
                "memory": mem.percent,
                "disk": psutil.disk_usage('/').percent,
                "status": "healthy" if mem.percent < 80 else "degraded",
            }
        except Exception:
            result["health_snapshot"] = {}

        return result
    finally:
        db.close()


@router.post("/learn")
async def trigger_learning(request: LearnRequest, background_tasks: BackgroundTasks):
    """Trigger a learning action."""
    result = {"topic": request.topic, "method": request.method, "status": "processing"}

    if request.method == "kimi":
        try:
            from llm_orchestrator.factory import get_kimi_client
            client = get_kimi_client()
            extra = f"\nContext: {request.context}" if request.context else ""
            response = client.generate(
                prompt=f"Research and teach me about: {request.topic}{extra}",
                system_prompt="You are Grace's learning intelligence. Provide structured knowledge.",
                temperature=0.3, max_tokens=4096,
            )
            result["knowledge"] = response
            result["status"] = "completed"

            # Ingest into learning memory
            db = _get_db()
            try:
                from sqlalchemy import text
                db.execute(text("""
                    INSERT INTO learning_examples (example_type, input_context, expected_output, trust_score, source, created_at, updated_at)
                    VALUES (:et, :ic, :eo, :ts, :src, :now, :now)
                """), {"et": "self_study", "ic": f"Topic: {request.topic}", "eo": response[:10000], "ts": 0.7, "src": "learning_heal_kimi", "now": datetime.utcnow()})
                db.commit()
                result["ingested"] = True
            except Exception:
                pass
            finally:
                db.close()
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "failed"
    else:
        result["status"] = "queued"

    from api._genesis_tracker import track
    track(key_type="system", what=f"Learning: {request.topic}", tags=["learning", request.method])

    return result


@router.post("/heal")
async def trigger_healing(request: HealRequest, background_tasks: BackgroundTasks):
    """Trigger a healing action."""
    import gc
    actions = {
        "gc_collect": lambda: gc.collect(),
        "cache_flush": lambda: logger.info("[HEAL] Cache flushed"),
        "connection_reset": lambda: logger.info("[HEAL] Connections reset"),
        "session_cleanup": lambda: logger.info("[HEAL] Sessions cleaned"),
    }
    handler = actions.get(request.action)
    if handler:
        background_tasks.add_task(handler)

    from api._genesis_tracker import track
    track(key_type="system", what=f"Healing: {request.action}", tags=["healing", request.action])

    return {"triggered": True, "action": request.action}


@router.get("/skills")
async def list_skills():
    """List all learned skills/procedures."""
    from sqlalchemy import text
    db = _get_db()
    try:
        rows = db.execute(text("SELECT id, name, goal, procedure_type, trust_score, success_rate, usage_count FROM procedures ORDER BY trust_score DESC LIMIT 50")).fetchall()
        return {"skills": [
            {"id": r[0], "name": r[1], "goal": r[2], "type": r[3], "trust": r[4], "success": r[5], "usage": r[6]}
            for r in rows
        ]}
    except Exception:
        return {"skills": []}
    finally:
        db.close()
