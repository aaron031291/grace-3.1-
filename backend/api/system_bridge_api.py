"""
System Bridge API — connects ALL backend systems to frontend tabs.

Aggregates 190+ disconnected modules into unified endpoints that
each tab can call to get data from every subsystem.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bridge", tags=["System Bridge"])


def _safe_call(fn, default=None):
    try:
        return fn()
    except Exception as e:
        logger.debug(f"Bridge call failed: {e}")
        return default


# ---------------------------------------------------------------------------
# Governance bridge — all governance-adjacent systems
# ---------------------------------------------------------------------------

@router.get("/governance/full")
async def governance_full():
    """All governance-adjacent systems in one call: KPI, telemetry,
    diagnostics, OODA, memory mesh, ML intelligence, healing."""
    result: Dict[str, Any] = {}

    # KPI
    result["kpi"] = _safe_call(lambda: _get_kpi(), {})

    # Cognitive OODA decisions
    result["ooda"] = _safe_call(lambda: _get_ooda(), {})

    # Memory mesh
    result["memory_mesh"] = _safe_call(lambda: _get_memory_mesh(), {})

    # Diagnostic machine
    result["diagnostics"] = _safe_call(lambda: _get_diagnostics(), {})

    # ML intelligence
    result["ml_intelligence"] = _safe_call(lambda: _get_ml_intelligence(), {})

    # Autonomous systems status
    result["autonomous"] = _safe_call(lambda: _get_autonomous(), {})

    # Monitoring / Organs of Grace
    result["monitoring"] = _safe_call(lambda: _get_monitoring(), {})

    # Contradiction detection
    result["contradictions"] = _safe_call(lambda: _get_contradictions(), {})

    return result


# ---------------------------------------------------------------------------
# Codebase bridge — CI/CD, testing, planning, version control
# ---------------------------------------------------------------------------

@router.get("/codebase/full")
async def codebase_full():
    """All codebase-adjacent systems: CI/CD, testing, planning, todos, version control."""
    result: Dict[str, Any] = {}

    # CI/CD pipelines
    result["cicd"] = _safe_call(lambda: _get_cicd(), {})

    # Planning
    result["planning"] = _safe_call(lambda: _get_planning(), {})

    # Todos
    result["todos"] = _safe_call(lambda: _get_todos(), {})

    # Version control
    result["version_control"] = _safe_call(lambda: _get_version_control(), {})

    # Repositories
    result["repositories"] = _safe_call(lambda: _get_repositories(), {})

    return result


# ---------------------------------------------------------------------------
# Docs bridge — ingestion, retrieval, KB connectors
# ---------------------------------------------------------------------------

@router.get("/docs/full")
async def docs_full():
    """All docs-adjacent systems: ingestion pipeline, retrieval stats, KB connectors."""
    result: Dict[str, Any] = {}

    # Ingestion pipeline status
    result["ingestion"] = _safe_call(lambda: _get_ingestion(), {})

    # Retrieval stats
    result["retrieval"] = _safe_call(lambda: _get_retrieval(), {})

    # Librarian stats
    result["librarian"] = _safe_call(lambda: _get_librarian(), {})

    return result


# ---------------------------------------------------------------------------
# Internal data fetchers
# ---------------------------------------------------------------------------

def _get_kpi():
    from kpi.kpi_tracker import get_tracker
    tracker = get_tracker()
    system_trust = tracker.get_system_trust()
    components = tracker.get_all_components()
    comp_data = []
    for c in (components or []):
        try:
            t = tracker.get_component_trust(c)
            comp_data.append({"name": c, "trust": t.get("trust_score", 0) if isinstance(t, dict) else 0})
        except Exception:
            comp_data.append({"name": c, "trust": 0})
    return {
        "system_trust": system_trust if isinstance(system_trust, dict) else {"trust_score": 0},
        "components": comp_data,
    }


def _get_ooda():
    from sqlalchemy import text
    from database.session import SessionLocal
    if not SessionLocal:
        return {"available": False}
    db = SessionLocal()
    try:
        try:
            rows = db.execute(text(
                "SELECT id, decision_type, action_taken, confidence, created_at "
                "FROM cognitive_decisions ORDER BY created_at DESC LIMIT 10"
            )).fetchall()
            return {"recent_decisions": [
                {"id": r[0], "type": r[1], "action": r[2], "confidence": r[3],
                 "created_at": r[4].isoformat() if r[4] else None}
                for r in rows
            ]}
        except Exception:
            return {"recent_decisions": [], "note": "No OODA decisions table"}
    finally:
        db.close()


def _get_memory_mesh():
    from sqlalchemy import text, func
    from database.session import SessionLocal
    if not SessionLocal:
        return {}
    db = SessionLocal()
    try:
        counts = {}
        for table in ["learning_examples", "learning_patterns", "episodes", "procedures"]:
            try:
                r = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                counts[table] = r.scalar() or 0
            except Exception:
                counts[table] = 0
        return counts
    finally:
        db.close()


def _get_diagnostics():
    try:
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine
        engine = DiagnosticEngine()
        status = engine.get_status()
        return status if isinstance(status, dict) else {"status": str(status)}
    except Exception:
        return {"available": False}


def _get_ml_intelligence():
    try:
        from ml_intelligence.integration_orchestrator import MLIntelligenceOrchestrator
        orch = MLIntelligenceOrchestrator()
        return {"available": True, "components": [
            "neural_trust_scorer", "multi_armed_bandit", "meta_learning",
            "uncertainty_quantification", "contrastive_learning",
            "neuro_symbolic_reasoner", "online_learning_pipeline"
        ]}
    except Exception:
        return {"available": False}


def _get_autonomous():
    try:
        from sqlalchemy import text
        from database.session import SessionLocal
        if not SessionLocal:
            return {}
        db = SessionLocal()
        try:
            counts = {}
            for table_status in [
                ("governance_decisions", "pending"),
                ("governance_decisions", "approved"),
            ]:
                try:
                    r = db.execute(text(f"SELECT COUNT(*) FROM {table_status[0]} WHERE status = '{table_status[1]}'"))
                    counts[f"{table_status[0]}_{table_status[1]}"] = r.scalar() or 0
                except Exception:
                    pass
            return counts
        finally:
            db.close()
    except Exception:
        return {}


def _get_monitoring():
    import psutil
    mem = psutil.virtual_memory()
    return {
        "cpu": psutil.cpu_percent(interval=0.1),
        "memory_percent": mem.percent,
        "memory_gb": round(mem.used / (1024**3), 1),
        "disk_percent": psutil.disk_usage('/').percent,
        "organs": [
            {"name": "Self Healing", "progress": 25},
            {"name": "World Model", "progress": 45},
            {"name": "Self Learning", "progress": 35},
            {"name": "Self Governance", "progress": 30},
        ],
    }


def _get_contradictions():
    try:
        from cognitive.contradiction_detector import ContradictionDetector
        detector = ContradictionDetector()
        return {"available": True}
    except Exception:
        return {"available": False}


def _get_cicd():
    return {"available": True, "endpoints": [
        "/api/cicd/pipelines", "/api/cicd/versions",
        "/api/cicd/adaptive", "/api/cicd/autonomous"
    ]}


def _get_planning():
    from sqlalchemy import text
    from database.session import SessionLocal
    if not SessionLocal:
        return {}
    db = SessionLocal()
    try:
        try:
            r = db.execute(text("SELECT COUNT(*) FROM grace_planning_concepts"))
            return {"concepts": r.scalar() or 0}
        except Exception:
            return {"concepts": 0}
    finally:
        db.close()


def _get_todos():
    try:
        from api.grace_todos_api import tasks_store
        return {"active_tasks": len(tasks_store)}
    except Exception:
        return {"active_tasks": 0}


def _get_version_control():
    return {"available": True, "endpoints": [
        "/api/version-control/status", "/api/version-control/commits",
        "/api/version-control/branches"
    ]}


def _get_repositories():
    from sqlalchemy import text
    from database.session import SessionLocal
    if not SessionLocal:
        return {}
    db = SessionLocal()
    try:
        try:
            r = db.execute(text("SELECT COUNT(*) FROM repositories"))
            return {"total": r.scalar() or 0}
        except Exception:
            return {"total": 0}
    finally:
        db.close()


def _get_ingestion():
    from sqlalchemy import text
    from database.session import SessionLocal
    if not SessionLocal:
        return {}
    db = SessionLocal()
    try:
        result = {}
        try:
            r = db.execute(text("SELECT status, COUNT(*) FROM documents GROUP BY status"))
            result["by_status"] = dict(r.fetchall())
        except Exception:
            result["by_status"] = {}
        try:
            r = db.execute(text("SELECT COUNT(*) FROM document_chunks"))
            result["total_chunks"] = r.scalar() or 0
        except Exception:
            result["total_chunks"] = 0
        return result
    finally:
        db.close()


def _get_retrieval():
    try:
        from vector_db.client import get_qdrant_client
        client = get_qdrant_client()
        colls = client.get_collections()
        info = []
        for c in colls.collections:
            try:
                ci = client.get_collection(c.name)
                info.append({"name": c.name, "vectors": ci.vectors_count, "points": ci.points_count})
            except Exception:
                info.append({"name": c.name})
        return {"collections": info}
    except Exception:
        return {"collections": []}


def _get_librarian():
    from sqlalchemy import text
    from database.session import SessionLocal
    if not SessionLocal:
        return {}
    db = SessionLocal()
    try:
        result = {}
        for table in ["document_tags", "document_relationships", "librarian_rules", "librarian_actions"]:
            try:
                r = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                result[table] = r.scalar() or 0
            except Exception:
                result[table] = 0
        return result
    finally:
        db.close()
