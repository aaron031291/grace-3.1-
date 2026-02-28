"""
Business Intelligence API — Analytics dashboard for Grace

Aggregates data across documents, chats, tasks, genesis keys, and
learning to provide business-level insights, trends, and KPIs.
"""

from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/bi", tags=["Business Intelligence"])


def _get_db():
    from database.session import SessionLocal
    if SessionLocal is None:
        from database.session import initialize_session_factory
        initialize_session_factory()
        from database.session import SessionLocal as SL
        return SL()
    return SessionLocal()


@router.get("/dashboard")
async def bi_dashboard():
    """Full business intelligence dashboard."""
    from sqlalchemy import text, func
    db = _get_db()
    try:
        result: Dict[str, Any] = {"timestamp": datetime.utcnow().isoformat()}

        # Document analytics
        try:
            r = db.execute(text("SELECT COUNT(*), SUM(file_size), AVG(confidence_score) FROM documents"))
            row = r.fetchone()
            result["documents"] = {"total": row[0] or 0, "total_size_mb": round((row[1] or 0) / (1024*1024), 2), "avg_confidence": round(row[2] or 0, 3)}

            # Growth: docs this week vs last week
            week_ago = datetime.utcnow() - timedelta(days=7)
            two_weeks = datetime.utcnow() - timedelta(days=14)
            this_week = db.execute(text("SELECT COUNT(*) FROM documents WHERE created_at >= :d"), {"d": week_ago}).scalar() or 0
            last_week = db.execute(text("SELECT COUNT(*) FROM documents WHERE created_at >= :d1 AND created_at < :d2"), {"d1": two_weeks, "d2": week_ago}).scalar() or 0
            result["documents"]["this_week"] = this_week
            result["documents"]["last_week"] = last_week
            result["documents"]["growth"] = "up" if this_week > last_week else "down" if this_week < last_week else "flat"
        except Exception:
            result["documents"] = {"total": 0}

        # Chat analytics
        try:
            r = db.execute(text("SELECT COUNT(*) FROM chats"))
            chats = r.scalar() or 0
            r2 = db.execute(text("SELECT COUNT(*) FROM chat_history"))
            messages = r2.scalar() or 0
            result["chats"] = {"total_chats": chats, "total_messages": messages, "avg_per_chat": round(messages / max(chats, 1), 1)}
        except Exception:
            result["chats"] = {"total_chats": 0}

        # Genesis key analytics
        try:
            r = db.execute(text("SELECT COUNT(*) FROM genesis_key"))
            total_keys = r.scalar() or 0
            today = datetime.utcnow().replace(hour=0, minute=0, second=0)
            today_keys = db.execute(text("SELECT COUNT(*) FROM genesis_key WHERE when_timestamp >= :d"), {"d": today}).scalar() or 0
            errors = db.execute(text("SELECT COUNT(*) FROM genesis_key WHERE is_error = 1")).scalar() or 0
            result["genesis_keys"] = {"total": total_keys, "today": today_keys, "error_rate": round(errors / max(total_keys, 1) * 100, 1)}
        except Exception:
            result["genesis_keys"] = {"total": 0}

        # Learning analytics
        try:
            r = db.execute(text("SELECT COUNT(*), AVG(trust_score) FROM learning_examples"))
            row = r.fetchone()
            result["learning"] = {"examples": row[0] or 0, "avg_trust": round(row[1] or 0, 3)}
            r2 = db.execute(text("SELECT COUNT(*) FROM procedures"))
            result["learning"]["skills"] = r2.scalar() or 0
        except Exception:
            result["learning"] = {"examples": 0}

        # Task analytics
        try:
            from api.grace_todos_api import tasks_store
            statuses = {}
            for t in tasks_store.values():
                s = t.status.value
                statuses[s] = statuses.get(s, 0) + 1
            result["tasks"] = {"total": len(tasks_store), "by_status": statuses}
        except Exception:
            result["tasks"] = {"total": 0}

        # System uptime
        try:
            import psutil, time
            boot = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.utcnow() - boot
            result["uptime"] = {"days": uptime.days, "hours": uptime.seconds // 3600}
        except Exception:
            result["uptime"] = {}

        return result
    finally:
        db.close()


@router.get("/trends")
async def bi_trends():
    """Activity trends over the last 7 days."""
    from sqlalchemy import text
    db = _get_db()
    try:
        days = []
        for i in range(7):
            day = datetime.utcnow().date() - timedelta(days=i)
            day_start = datetime.combine(day, datetime.min.time())
            day_end = day_start + timedelta(days=1)

            keys = 0
            docs = 0
            try:
                keys = db.execute(text("SELECT COUNT(*) FROM genesis_key WHERE when_timestamp >= :s AND when_timestamp < :e"), {"s": day_start, "e": day_end}).scalar() or 0
            except Exception:
                pass
            try:
                docs = db.execute(text("SELECT COUNT(*) FROM documents WHERE created_at >= :s AND created_at < :e"), {"s": day_start, "e": day_end}).scalar() or 0
            except Exception:
                pass

            days.append({"date": day.isoformat(), "genesis_keys": keys, "documents": docs})

        days.reverse()
        return {"days": days}
    finally:
        db.close()


@router.get("/llm-usage")
async def llm_usage_stats():
    """LLM usage statistics — calls, latency, errors, by provider."""
    from llm_orchestrator.governance_wrapper import get_llm_usage_stats
    stats = get_llm_usage_stats()

    # Also pull from DB for historical data
    db = _get_db()
    try:
        from sqlalchemy import text
        try:
            rows = db.execute(text(
                "SELECT provider, COUNT(*), AVG(latency_ms), SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) "
                "FROM llm_usage_stats GROUP BY provider"
            )).fetchall()
            stats["historical"] = {
                r[0]: {"calls": r[1], "avg_latency": round(r[2] or 0, 1), "errors": r[3]}
                for r in rows
            }
        except Exception:
            stats["historical"] = {}

        try:
            today = datetime.utcnow().date()
            today_calls = db.execute(text(
                "SELECT COUNT(*) FROM llm_usage_stats WHERE DATE(created_at) = :d"
            ), {"d": str(today)}).scalar() or 0
            stats["today_calls"] = today_calls
        except Exception:
            stats["today_calls"] = 0
    except Exception:
        pass
    finally:
        db.close()

    return stats


@router.get("/memory-stats")
async def memory_stats():
    """Unified memory statistics across all memory systems."""
    from cognitive.unified_memory import get_unified_memory
    return get_unified_memory().get_stats()


@router.get("/event-log")
async def event_log(limit: int = 50):
    """Recent events from the event bus."""
    from cognitive.event_bus import get_recent_events, get_subscriber_count
    return {
        "events": get_recent_events(limit),
        "subscribers": get_subscriber_count(),
    }
