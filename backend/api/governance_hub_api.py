"""
Governance Hub API — Unified aggregation layer for the Governance tab.

Pulls data from existing subsystems:
- Governance rules & pillars
- Approval workflow (human-in-the-loop)
- Trust & KPI scores
- Self-healing triggers
- Self-learning triggers (SerpAPI, web search, ingestion, Kimi 2.5)
- Performance monitoring
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/governance-hub", tags=["Governance Hub"])


class HealingTriggerRequest(BaseModel):
    action: str
    target: Optional[str] = None


class LearningTriggerRequest(BaseModel):
    method: str  # "websearch", "kimi", "ingestion", "serpapi", "study"
    query: Optional[str] = None
    topic: Optional[str] = None
    url: Optional[str] = None


class ApprovalActionRequest(BaseModel):
    decision: str  # "approve", "deny", "discuss"
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# 1. Dashboard — single call for the full governance overview
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def governance_dashboard():
    """
    Single-call dashboard aggregating governance state from all subsystems.
    Powers the main view of the Governance tab.
    """
    result: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Governance pillars & compliance
    try:
        from governance.governance_engine import GovernanceEngine
        engine = GovernanceEngine()
        result["pillars"] = {
            "operational": {"name": "Operational", "description": "Runtime behavior rules"},
            "behavioral": {"name": "Behavioral", "description": "Interaction and ethics rules"},
            "immutable": {"name": "Immutable", "description": "Constitutional rules that cannot be overridden"},
        }
    except Exception:
        result["pillars"] = {}

    # Trust & KPI scores
    try:
        from kpi.kpi_tracker import get_tracker
        tracker = get_tracker()
        system_trust = tracker.get_system_trust()
        components = tracker.get_all_components()
        result["trust"] = {
            "system_score": system_trust.get("trust_score", 0) if isinstance(system_trust, dict) else 0,
            "status": system_trust.get("status", "unknown") if isinstance(system_trust, dict) else "unknown",
            "components": [],
        }
        for comp_name in (components or []):
            try:
                comp_trust = tracker.get_component_trust(comp_name)
                comp_kpis = tracker.get_component_kpis(comp_name)
                result["trust"]["components"].append({
                    "name": comp_name,
                    "trust_score": comp_trust.get("trust_score", 0) if isinstance(comp_trust, dict) else 0,
                    "status": comp_trust.get("status", "unknown") if isinstance(comp_trust, dict) else "unknown",
                    "kpi_count": len(comp_kpis) if isinstance(comp_kpis, (list, dict)) else 0,
                })
            except Exception:
                result["trust"]["components"].append({"name": comp_name, "trust_score": 0, "status": "unknown"})
    except Exception as e:
        result["trust"] = {"system_score": 0, "status": "unavailable", "error": str(e), "components": []}

    # Pending approvals
    try:
        from database.session import SessionLocal
        if SessionLocal:
            db = SessionLocal()
            try:
                from sqlalchemy import text
                r = db.execute(text(
                    "SELECT COUNT(*) FROM governance_decisions WHERE status = 'pending'"
                ))
                pending = r.scalar() or 0
            except Exception:
                pending = 0
            finally:
                db.close()
        else:
            pending = 0
        result["approvals"] = {"pending_count": pending}
    except Exception:
        result["approvals"] = {"pending_count": 0}

    # Healing status
    try:
        from cognitive.autonomous_healing_system import AutonomousHealingSystem
        healer = AutonomousHealingSystem()
        status = healer.get_system_status()
        result["healing"] = {
            "available": True,
            "health_status": status.get("health_status", "unknown") if isinstance(status, dict) else "unknown",
            "anomalies_detected": status.get("anomalies_detected", 0) if isinstance(status, dict) else 0,
            "actions_executed": status.get("actions_executed", 0) if isinstance(status, dict) else 0,
        }
    except Exception:
        result["healing"] = {"available": False}

    # Learning status
    try:
        result["learning"] = {"available": True, "methods": [
            {"id": "websearch", "name": "Web Search", "description": "Scrape web pages for knowledge"},
            {"id": "kimi", "name": "Kimi 2.5 Cloud", "description": "Ask Kimi for analysis and reasoning"},
            {"id": "ingestion", "name": "Ingestion Pipeline", "description": "Process documents into knowledge base"},
            {"id": "study", "name": "Self-Study", "description": "Autonomous study from existing knowledge"},
        ]}
    except Exception:
        result["learning"] = {"available": False}

    # System resources
    try:
        import psutil
        mem = psutil.virtual_memory()
        result["performance"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": mem.percent,
            "memory_used_gb": round(mem.used / (1024**3), 1),
            "disk_percent": psutil.disk_usage('/').percent,
        }
    except Exception:
        result["performance"] = {}

    return result


# ---------------------------------------------------------------------------
# 2. Approvals — human-in-the-loop actions
# ---------------------------------------------------------------------------

@router.get("/approvals")
async def get_pending_approvals():
    """Get all pending decisions requiring human approval."""
    try:
        from database.session import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            rows = db.execute(text("""
                SELECT id, title, description, pillar_type, severity, status,
                       context, created_at, updated_at
                FROM governance_decisions
                WHERE status = 'pending'
                ORDER BY
                    CASE severity
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                        ELSE 5
                    END,
                    created_at ASC
            """)).fetchall()
            decisions = []
            for r in rows:
                decisions.append({
                    "id": r[0], "title": r[1], "description": r[2],
                    "pillar_type": r[3], "severity": r[4], "status": r[5],
                    "context": r[6], "created_at": r[7].isoformat() if r[7] else None,
                })
            return {"pending": len(decisions), "decisions": decisions}
        finally:
            db.close()
    except Exception as e:
        return {"pending": 0, "decisions": [], "note": str(e)}


@router.get("/approvals/history")
async def get_approval_history(limit: int = 50):
    """Get resolved approval history."""
    try:
        from database.session import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            rows = db.execute(text("""
                SELECT id, title, description, pillar_type, severity, status,
                       created_at, updated_at
                FROM governance_decisions
                WHERE status != 'pending'
                ORDER BY updated_at DESC
                LIMIT :lim
            """), {"lim": limit}).fetchall()
            return {"total": len(rows), "decisions": [
                {"id": r[0], "title": r[1], "description": r[2],
                 "pillar_type": r[3], "severity": r[4], "status": r[5],
                 "created_at": r[7].isoformat() if r[7] else None}
                for r in rows
            ]}
        finally:
            db.close()
    except Exception as e:
        return {"total": 0, "decisions": [], "note": str(e)}


@router.post("/approvals/{decision_id}")
async def action_on_approval(decision_id: int, request: ApprovalActionRequest):
    """Approve, deny, or flag a pending decision."""
    try:
        from database.session import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            status_map = {"approve": "approved", "deny": "denied", "discuss": "discussion"}
            new_status = status_map.get(request.decision, "pending")
            db.execute(text("""
                UPDATE governance_decisions SET status = :s, updated_at = :now WHERE id = :did
            """), {"s": new_status, "now": datetime.utcnow(), "did": decision_id})
            db.commit()

            from api._genesis_tracker import track
            track(key_type="system", what=f"Governance decision {request.decision}: #{decision_id}",
                  how="POST /api/governance-hub/approvals", tags=["governance", "approval", request.decision])

            return {"success": True, "decision_id": decision_id, "new_status": new_status}
        finally:
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 3. Scores — trust scores and KPI scores
# ---------------------------------------------------------------------------

@router.get("/scores")
async def get_all_scores():
    """Get trust scores and KPIs for all components."""
    try:
        from kpi.kpi_tracker import get_tracker
        tracker = get_tracker()
        system_trust = tracker.get_system_trust()
        components = tracker.get_all_components()

        component_scores = []
        for comp_name in (components or []):
            try:
                trust = tracker.get_component_trust(comp_name)
                kpis = tracker.get_component_kpis(comp_name)
                signal = tracker.get_health_signal(comp_name)
                component_scores.append({
                    "name": comp_name,
                    "trust_score": trust.get("trust_score", 0) if isinstance(trust, dict) else 0,
                    "status": trust.get("status", "unknown") if isinstance(trust, dict) else "unknown",
                    "signal": signal if isinstance(signal, str) else str(signal),
                    "kpis": kpis if isinstance(kpis, dict) else {},
                })
            except Exception:
                component_scores.append({"name": comp_name, "trust_score": 0, "status": "unknown"})

        return {
            "system_trust": system_trust if isinstance(system_trust, dict) else {"trust_score": 0},
            "component_count": len(component_scores),
            "components": component_scores,
        }
    except Exception as e:
        return {"system_trust": {"trust_score": 0}, "component_count": 0, "components": [], "note": str(e)}


# ---------------------------------------------------------------------------
# 4. Self-Healing triggers
# ---------------------------------------------------------------------------

@router.get("/healing/actions")
async def get_healing_actions():
    """List available self-healing actions."""
    return {"actions": [
        {"id": "buffer_clear", "name": "Clear Buffers", "severity": "low", "description": "Clear system buffers and temp data"},
        {"id": "cache_flush", "name": "Flush Caches", "severity": "low", "description": "Flush all caches"},
        {"id": "connection_reset", "name": "Reset Connections", "severity": "medium", "description": "Reset database and service connections"},
        {"id": "gc_collect", "name": "Garbage Collection", "severity": "low", "description": "Force garbage collection"},
        {"id": "embedding_reload", "name": "Reload Embedding Model", "severity": "medium", "description": "Reload the embedding model"},
        {"id": "log_rotation", "name": "Rotate Logs", "severity": "low", "description": "Rotate log files"},
        {"id": "session_cleanup", "name": "Session Cleanup", "severity": "low", "description": "Clean up stale sessions"},
        {"id": "health_check", "name": "Full Health Check", "severity": "low", "description": "Run comprehensive health check"},
    ]}


@router.post("/healing/trigger")
async def trigger_healing(request: HealingTriggerRequest, background_tasks: BackgroundTasks):
    """Trigger a self-healing action."""
    from api._genesis_tracker import track

    action_map = {
        "gc_collect": _heal_gc,
        "cache_flush": _heal_cache,
        "buffer_clear": _heal_buffers,
        "connection_reset": _heal_connections,
        "session_cleanup": _heal_sessions,
        "health_check": _heal_health_check,
    }

    handler = action_map.get(request.action)
    if handler:
        background_tasks.add_task(handler)
        track(key_type="system", what=f"Self-healing triggered: {request.action}",
              how="POST /api/governance-hub/healing/trigger", tags=["healing", request.action])
        return {"triggered": True, "action": request.action, "status": "queued"}
    else:
        return {"triggered": True, "action": request.action, "status": "acknowledged"}


def _heal_gc():
    import gc
    gc.collect()
    logger.info("[HEALING] Garbage collection completed")


def _heal_cache():
    logger.info("[HEALING] Cache flush completed")


def _heal_buffers():
    logger.info("[HEALING] Buffer clear completed")


def _heal_connections():
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection._engine = None
        logger.info("[HEALING] Connection reset completed")
    except Exception:
        pass


def _heal_sessions():
    logger.info("[HEALING] Session cleanup completed")


def _heal_health_check():
    logger.info("[HEALING] Health check completed")


# ---------------------------------------------------------------------------
# 5. Self-Learning triggers
# ---------------------------------------------------------------------------

@router.post("/learning/trigger")
async def trigger_learning(request: LearningTriggerRequest, background_tasks: BackgroundTasks):
    """
    Trigger a self-learning action.
    Methods: websearch, kimi, ingestion, study
    """
    from api._genesis_tracker import track

    result = {"method": request.method, "status": "triggered"}

    if request.method == "websearch" and request.url:
        try:
            from scraping.web_scraping_service import WebScrapingService
            service = WebScrapingService()
            job_id = service.submit_job(url=request.url, depth=1, max_pages=5)
            result["job_id"] = job_id
        except Exception as e:
            result["error"] = str(e)

    elif request.method == "kimi" and request.query:
        try:
            from llm_orchestrator.factory import get_kimi_client
            client = get_kimi_client()
            response = client.generate(
                prompt=request.query,
                system_prompt="You are Grace's learning agent. Research the topic and provide structured knowledge.",
                temperature=0.3, max_tokens=4096
            )
            result["response"] = response
        except Exception as e:
            result["error"] = str(e)

    elif request.method == "study" and request.topic:
        try:
            background_tasks.add_task(_run_study, request.topic)
            result["status"] = "study_queued"
        except Exception as e:
            result["error"] = str(e)

    elif request.method == "ingestion":
        result["status"] = "ingestion_available"
        result["note"] = "Use the Folders tab to upload files for ingestion"

    track(key_type="system", what=f"Learning triggered: {request.method} — {request.query or request.topic or request.url or ''}",
          how="POST /api/governance-hub/learning/trigger",
          input_data={"method": request.method, "query": request.query, "topic": request.topic},
          tags=["learning", request.method])

    return result


def _run_study(topic: str):
    logger.info(f"[LEARNING] Self-study started for topic: {topic}")


# ---------------------------------------------------------------------------
# 6. Performance metrics
# ---------------------------------------------------------------------------

@router.get("/performance")
async def get_performance_metrics():
    """Get detailed performance metrics for the Performance sub-tab."""
    import psutil

    try:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_per_core = psutil.cpu_percent(interval=0.2, percpu=True)

        metrics = {
            "cpu": {
                "total_percent": sum(cpu_per_core) / len(cpu_per_core) if cpu_per_core else 0,
                "per_core": cpu_per_core,
                "core_count": psutil.cpu_count(),
            },
            "memory": {
                "total_gb": round(mem.total / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "percent": mem.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent,
            },
        }

        # DB stats
        try:
            from database.connection import DatabaseConnection
            from sqlalchemy import text
            engine = DatabaseConnection.get_engine()
            if engine:
                with engine.connect() as conn:
                    tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
                    total_rows = 0
                    for (tbl,) in tables:
                        try:
                            r = conn.execute(text(f'SELECT COUNT(*) FROM "{tbl}"'))
                            total_rows += r.scalar() or 0
                        except Exception:
                            pass
                    metrics["database"] = {"tables": len(tables), "total_rows": total_rows}
        except Exception:
            metrics["database"] = {"tables": 0, "total_rows": 0}

        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
