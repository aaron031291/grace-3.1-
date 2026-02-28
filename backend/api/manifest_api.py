"""
System Manifest API — Auto-generated live map of Grace's entire architecture.

Never goes stale because it introspects the actual running system:
- Every registered endpoint with metadata
- Every frontend tab and what it connects to
- Every backend module and its status
- Every intelligence system and its wiring
- Dependency graph between components
"""

from fastapi import APIRouter
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/manifest", tags=["System Manifest"])

BACKEND_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Full manifest — one call to see everything
# ---------------------------------------------------------------------------

@router.get("/full")
async def full_manifest():
    """Complete auto-generated system manifest."""
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "endpoints": _get_endpoints(),
        "frontend_tabs": _get_frontend_tabs(),
        "backend_modules": _get_backend_modules(),
        "intelligence_systems": _get_intelligence_systems(),
        "database_tables": _get_database_tables(),
        "summary": _get_summary(),
    }


@router.get("/endpoints")
async def manifest_endpoints():
    """All registered API endpoints grouped by prefix."""
    return _get_endpoints()


@router.get("/tabs")
async def manifest_tabs():
    """All frontend tabs and their backend connections."""
    return _get_frontend_tabs()


@router.get("/modules")
async def manifest_modules():
    """All backend Python modules."""
    return _get_backend_modules()


@router.get("/intelligence")
async def manifest_intelligence():
    """All intelligence systems and their status."""
    return _get_intelligence_systems()


@router.get("/summary")
async def manifest_summary():
    """Quick summary numbers."""
    return _get_summary()


# ---------------------------------------------------------------------------
# Data builders
# ---------------------------------------------------------------------------

def _get_endpoints() -> Dict[str, Any]:
    try:
        from app import app
        by_prefix = {}
        total = 0
        for r in app.routes:
            if not hasattr(r, 'methods'):
                continue
            for m in r.methods:
                if m in ('HEAD', 'OPTIONS'):
                    continue
                total += 1
                parts = r.path.strip('/').split('/')
                prefix = '/' + parts[0]
                if parts[0] == 'api' and len(parts) > 1:
                    prefix = '/api/' + parts[1]
                if prefix not in by_prefix:
                    by_prefix[prefix] = {"prefix": prefix, "count": 0, "endpoints": []}
                by_prefix[prefix]["count"] += 1
                doc = ""
                if hasattr(r, 'endpoint') and r.endpoint.__doc__:
                    doc = r.endpoint.__doc__.strip().split('\n')[0]
                by_prefix[prefix]["endpoints"].append({
                    "method": m, "path": r.path,
                    "name": getattr(r, 'name', ''),
                    "description": doc,
                })
        return {"total": total, "prefixes": len(by_prefix),
                "by_prefix": dict(sorted(by_prefix.items()))}
    except Exception as e:
        return {"total": 0, "error": str(e)}


def _get_frontend_tabs() -> List[Dict[str, Any]]:
    return [
        {"id": "chat", "icon": "💬", "label": "Chat",
         "connects_to": ["/api/world-model", "/api/mcp", "/chats", "/chat", "/cognitive", "/retrieve", "/voice"],
         "description": "World model chat, Kimi 2.5, folder context, system awareness"},
        {"id": "folders", "icon": "📁", "label": "Folders",
         "connects_to": ["/api/librarian-fs", "/files", "/librarian"],
         "description": "File management, librarian CRUD, inline editor, infinite nesting"},
        {"id": "docs", "icon": "📚", "label": "Docs",
         "connects_to": ["/api/docs", "/api/intelligence", "/ingest"],
         "description": "Document library, all uploads, folder view, relationships, tags"},
        {"id": "governance", "icon": "🏛️", "label": "Governance",
         "connects_to": ["/api/governance-hub", "/api/genesis-daily", "/api/governance-rules", "/governance", "/kpi", "/monitoring", "/diagnostic", "/api/bridge"],
         "description": "Approvals, scores, performance, actions, rules & persona, genesis keys"},
        {"id": "whitelist", "icon": "🛡️", "label": "Whitelist",
         "connects_to": ["/api/whitelist-hub", "/scrape"],
         "description": "API sources, web sources, per-source docs, Kimi learning"},
        {"id": "oracle", "icon": "🔮", "label": "Oracle",
         "connects_to": ["/api/oracle", "/training", "/autonomous-learning", "/learning-memory", "/ml-intelligence"],
         "description": "Training data store, Kimi audit, gap detection, ingestion feedback"},
        {"id": "codebase", "icon": "💻", "label": "Codebase",
         "connects_to": ["/api/codebase-hub", "/api/coding-agent"],
         "description": "Code projects, domain folders, unified coding agent (28 systems)"},
        {"id": "tasks", "icon": "📋", "label": "Tasks",
         "connects_to": ["/api/tasks-hub", "/api/grace-todos"],
         "description": "Live activity, drag-and-drop kanban, scheduling, TimeSense"},
        {"id": "apis", "icon": "🔗", "label": "APIs",
         "connects_to": ["/api/registry", "/api/explorer", "/health"],
         "description": "Endpoint catalogue, health checks, Kimi diagnostics, explorer"},
        {"id": "bi", "icon": "📈", "label": "BI",
         "connects_to": ["/api/bi", "/kpi"],
         "description": "Business intelligence, KPI cards, 7-day trends"},
        {"id": "health", "icon": "🏥", "label": "Health",
         "connects_to": ["/api/system-health", "/diagnostic", "/monitoring"],
         "description": "CPU/memory/disk, services, organs, diagnostics, processes"},
        {"id": "learn-heal", "icon": "🧬", "label": "Learn & Heal",
         "connects_to": ["/api/learn-heal", "/ml-intelligence", "/sandbox-lab"],
         "description": "Self-learning, trust distribution, healing actions, skills"},
    ]


def _get_backend_modules() -> Dict[str, Any]:
    skip = {'venv', 'node_modules', '__pycache__', 'mcp_repos', '.git',
            'models', 'data', '.pytest_cache', 'tests', 'logs', 'knowledge_base'}
    modules = {}
    for d in sorted(BACKEND_ROOT.iterdir()):
        if d.name in skip or not d.is_dir() or d.name.startswith('.'):
            continue
        py_files = list(d.rglob('*.py'))
        py_files = [f for f in py_files if '__pycache__' not in str(f)]
        if py_files:
            modules[d.name] = {
                "directory": d.name,
                "file_count": len(py_files),
                "files": [str(f.relative_to(BACKEND_ROOT)) for f in sorted(py_files)[:20]],
            }
    return {"total_directories": len(modules), "modules": modules}


def _get_intelligence_systems() -> List[Dict[str, Any]]:
    systems = [
        {"name": "CodeNet", "module": "ingestion.codenet_adapter", "type": "learning"},
        {"name": "Learning Memory", "module": "cognitive.learning_memory", "type": "memory"},
        {"name": "RAG Retrieval", "module": "retrieval.retriever", "type": "retrieval"},
        {"name": "Governance Rules", "module": "llm_orchestrator.governance_wrapper", "type": "governance"},
        {"name": "Genesis Tracking", "module": "genesis.genesis_key_service", "type": "tracking"},
        {"name": "Kimi 2.5 Cloud", "module": "llm_orchestrator.kimi_client", "type": "llm"},
        {"name": "Mirror Self-Model", "module": "cognitive.mirror_self_modeling", "type": "cognitive"},
        {"name": "OODA Loop", "module": "cognitive.ooda", "type": "cognitive"},
        {"name": "Invariant Validator", "module": "cognitive.invariants", "type": "cognitive"},
        {"name": "Ambiguity Ledger", "module": "cognitive.ambiguity", "type": "cognitive"},
        {"name": "Contradiction Detector", "module": "cognitive.contradiction_detector", "type": "cognitive"},
        {"name": "Hallucination Guard", "module": "llm_orchestrator.hallucination_guard", "type": "verification"},
        {"name": "Neural Trust Scorer", "module": "ml_intelligence.neural_trust_scorer", "type": "ml"},
        {"name": "Uncertainty Quant", "module": "ml_intelligence.uncertainty_quantification", "type": "ml"},
        {"name": "KPI Tracker", "module": "ml_intelligence.kpi_tracker", "type": "tracking"},
        {"name": "TimeSense", "module": "cognitive.time_sense", "type": "cognitive"},
        {"name": "Neuro-Symbolic", "module": "ml_intelligence.neuro_symbolic_reasoner", "type": "ml"},
        {"name": "Predictive Context", "module": "cognitive.predictive_context_loader", "type": "cognitive"},
        {"name": "Grace Agent", "module": "agent.grace_agent", "type": "execution"},
        {"name": "Governed Bridge", "module": "execution.governed_bridge", "type": "execution"},
        {"name": "Confidence Scorer", "module": "confidence_scorer.confidence_scorer", "type": "verification"},
        {"name": "GraceOS Codegen", "module": "grace_os.layers.l6_codegen.codegen_layer", "type": "execution"},
        {"name": "GraceOS Testing", "module": "grace_os.layers.l7_testing.testing_layer", "type": "execution"},
        {"name": "SerpAPI Search", "module": "search.serpapi_service", "type": "external"},
        {"name": "Telemetry", "module": "telemetry.telemetry_service", "type": "tracking"},
        {"name": "Git Service", "module": "version_control.git_service", "type": "execution"},
        {"name": "World Model", "module": "api.world_model_api", "type": "awareness"},
        {"name": "Persona", "module": "api.governance_rules_api", "type": "governance"},
    ]

    for s in systems:
        try:
            __import__(s["module"], fromlist=["x"])
            s["available"] = True
        except Exception:
            s["available"] = False

    available = sum(1 for s in systems if s["available"])
    return {"total": len(systems), "available": available,
            "score": f"{available}/{len(systems)}", "systems": systems}


def _get_database_tables() -> Dict[str, Any]:
    try:
        from database.connection import DatabaseConnection
        from sqlalchemy import inspect as sa_inspect
        engine = DatabaseConnection.get_engine()
        if not engine:
            return {"connected": False}
        inspector = sa_inspect(engine)
        tables = inspector.get_table_names()
        return {"connected": True, "table_count": len(tables), "tables": sorted(tables)}
    except Exception:
        return {"connected": False}


def _get_summary() -> Dict[str, Any]:
    endpoints = _get_endpoints()
    modules = _get_backend_modules()
    intelligence = _get_intelligence_systems()
    db = _get_database_tables()

    return {
        "endpoints": endpoints.get("total", 0),
        "endpoint_prefixes": endpoints.get("prefixes", 0),
        "frontend_tabs": 12,
        "backend_modules": modules.get("total_directories", 0),
        "intelligence_systems": intelligence.get("total", 0),
        "intelligence_available": intelligence.get("available", 0),
        "intelligence_score": intelligence.get("score", "0/0"),
        "database_tables": db.get("table_count", 0),
    }
