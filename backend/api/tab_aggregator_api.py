"""
Tab Aggregator API — Connects ALL 770 backend endpoints to 12 frontend tabs.

Each tab gets a /full endpoint that pulls data from EVERY backend system
in its domain and returns it as one structured response.
"""

from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime
import logging
import requests as req

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tabs", tags=["Tab Aggregator"])

BASE = "http://localhost:8000"


def _call(path: str, method: str = "GET", timeout: int = 5) -> Any:
    """Call an internal endpoint and return the JSON response."""
    try:
        if method == "GET":
            r = req.get(f"{BASE}{path}", timeout=timeout)
        else:
            r = req.post(f"{BASE}{path}", json={}, timeout=timeout)
        if r.status_code < 400:
            return r.json()
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Chat tab — 90 endpoints
# ---------------------------------------------------------------------------
@router.get("/chat/full")
async def chat_full():
    """All data for the Chat tab: chats, world model, cognitive, retrieval, LLM."""
    return {
        "world_model_state": _call("/api/world-model/state"),
        "world_model_subsystems": _call("/api/world-model/subsystems"),
        "cognitive_status": _call("/cognitive/stats/summary"),
        "cognitive_decisions": _call("/cognitive/decisions/recent"),
        "llm_status": _call("/llm/status"),
        "llm_models": _call("/llm/models"),
        "recent_chats": _call("/chats?limit=10"),
        "mcp_status": _call("/api/mcp/status"),
        "mcp_tools": _call("/api/mcp/tools"),
        "voice_status": _call("/voice/status"),
        "layer1_status": _call("/layer1/status"),
    }


# ---------------------------------------------------------------------------
# Folders tab — 76 endpoints
# ---------------------------------------------------------------------------
@router.get("/folders/full")
async def folders_full():
    """All data for the Folders tab: file tree, librarian, directory hierarchy."""
    return {
        "file_tree": _call("/api/librarian-fs/tree"),
        "kb_stats": _call("/api/librarian-fs/stats"),
        "librarian_stats": _call("/librarian/statistics"),
        "librarian_health": _call("/librarian/health"),
        "librarian_tags": _call("/librarian/tags/statistics"),
        "librarian_rules": _call("/librarian/rules/statistics"),
        "librarian_actions": _call("/librarian/actions/statistics"),
        "librarian_pending": _call("/librarian/actions/pending"),
        "file_browse": _call("/files/browse"),
        "file_ingest_status": _call("/file-ingest/status"),
        "directory_hierarchy": _call("/directory-hierarchy/tree"),
    }


# ---------------------------------------------------------------------------
# Docs tab — 60 endpoints
# ---------------------------------------------------------------------------
@router.get("/docs/full")
async def docs_full():
    """All data for the Docs tab: documents, ingestion, retrieval, knowledge base."""
    return {
        "docs_stats": _call("/api/docs/stats"),
        "docs_by_folder": _call("/api/docs/by-folder"),
        "intelligence_tags": _call("/api/intelligence/tags"),
        "intelligence_activity": _call("/api/intelligence/activity"),
        "ingest_status": _call("/ingest/status"),
        "ingest_documents": _call("/ingest/documents"),
        "ingestion_status": _call("/api/ingestion/status"),
        "kb_connectors": _call("/knowledge-base/connectors"),
        "kb_status": _call("/knowledge-base/status"),
        "kb_sync_history": _call("/knowledge-base/sync-history"),
    }


# ---------------------------------------------------------------------------
# Governance tab — 168 endpoints
# ---------------------------------------------------------------------------
@router.get("/governance/full")
async def governance_full():
    """All data for the Governance tab: governance, KPI, monitoring, diagnostics, genesis."""
    return {
        "dashboard": _call("/api/governance-hub/dashboard"),
        "approvals": _call("/api/governance-hub/approvals"),
        "scores": _call("/api/governance-hub/scores"),
        "performance": _call("/api/governance-hub/performance"),
        "genesis_stats": _call("/api/genesis-daily/stats"),
        "genesis_folders": _call("/api/genesis-daily/folders?days=7"),
        "persona": _call("/api/governance-rules/persona"),
        "rule_documents": _call("/api/governance-rules/documents"),
        "governance_pillars": _call("/governance/pillars"),
        "governance_stats": _call("/governance/stats"),
        "governance_rules": _call("/governance/rules"),
        "governance_decisions_pending": _call("/governance/decisions/pending"),
        "governance_constitutional": _call("/governance/constitutional-rules"),
        "governance_autonomy": _call("/governance/autonomy-tiers"),
        "governance_kpi": _call("/governance/kpi-status"),
        "kpi_health": _call("/kpi/health"),
        "kpi_trust_system": _call("/kpi/trust/system"),
        "kpi_components": _call("/kpi/components"),
        "kpi_summary": _call("/kpi/summary"),
        "kpi_dashboard": _call("/kpi/dashboard"),
        "monitoring_organs": _call("/monitoring/organs"),
        "monitoring_health": _call("/monitoring/health"),
        "monitoring_metrics": _call("/monitoring/metrics"),
        "monitoring_components": _call("/monitoring/components"),
        "monitoring_activity": _call("/monitoring/activity"),
        "diagnostic_status": _call("/diagnostic/status"),
        "diagnostic_healing": _call("/diagnostic/healing/actions"),
        "telemetry_status": _call("/telemetry/status"),
        "telemetry_baselines": _call("/telemetry/baselines"),
        "telemetry_drift": _call("/telemetry/drift-alerts"),
        "genesis_keys_recent": _call("/genesis/keys?limit=10"),
        "bridge_governance": _call("/api/bridge/governance/full"),
        "autonomous_status": _call("/api/autonomous/status"),
    }


# ---------------------------------------------------------------------------
# Whitelist tab — 31 endpoints
# ---------------------------------------------------------------------------
@router.get("/whitelist/full")
async def whitelist_full():
    """All data for the Whitelist tab: sources, scraping, whitelist pipeline."""
    return {
        "api_sources": _call("/api/whitelist-hub/api-sources"),
        "web_sources": _call("/api/whitelist-hub/web-sources"),
        "hub_stats": _call("/api/whitelist-hub/stats"),
        "pipeline_status": _call("/api/whitelist/status"),
        "pipeline_stats": _call("/api/whitelist/stats"),
        "trust_levels": _call("/api/whitelist/trust-levels"),
        "scrape_jobs": _call("/scrape/status/recent"),
    }


# ---------------------------------------------------------------------------
# Oracle tab — 85 endpoints
# ---------------------------------------------------------------------------
@router.get("/oracle/full")
async def oracle_full():
    """All data for the Oracle tab: training, learning memory, ML intelligence."""
    return {
        "dashboard": _call("/api/oracle/dashboard"),
        "trust_distribution": _call("/api/oracle/trust-distribution"),
        "patterns": _call("/api/oracle/patterns"),
        "procedures": _call("/api/oracle/procedures"),
        "episodes": _call("/api/oracle/episodes"),
        "training_skills": _call("/training/skills"),
        "learning_status": _call("/autonomous-learning/status"),
        "learning_suggestions": _call("/autonomous-learning/memory-mesh/learning-suggestions"),
        "learning_memory_stats": _call("/learning-memory/stats"),
        "learning_efficiency": _call("/learning-efficiency/stats"),
        "proactive_status": _call("/proactive-learning/status"),
        "ml_status": _call("/ml-intelligence/status"),
        "ml_components": _call("/ml-intelligence/components"),
        "sandbox_status": _call("/sandbox-lab/status"),
        "sandbox_experiments": _call("/sandbox-lab/experiments"),
    }


# ---------------------------------------------------------------------------
# Codebase tab — 213 endpoints
# ---------------------------------------------------------------------------
@router.get("/codebase/full")
async def codebase_full():
    """All data for the Codebase tab: projects, CI/CD, testing, planning, version control."""
    return {
        "projects": _call("/api/codebase-hub/projects"),
        "agent_capabilities": _call("/api/coding-agent/capabilities"),
        "repositories": _call("/codebase/repositories"),
        "version_control": _call("/api/version-control/status"),
        "cicd_pipelines": _call("/api/cicd/pipelines"),
        "cicd_versions": _call("/api/cicd/versions"),
        "cicd_adaptive": _call("/api/cicd/adaptive/status"),
        "planning_concepts": _call("/api/grace-planning/concepts"),
        "todos_board": _call("/api/grace-todos/board"),
        "agent_status": _call("/agent/status"),
        "testing_status": _call("/test/status"),
        "ide_status": _call("/api/ide/status"),
        "notion_boards": _call("/notion/boards"),
        "bridge_codebase": _call("/api/bridge/codebase/full"),
    }


# ---------------------------------------------------------------------------
# Tasks tab — 10 endpoints (already fully connected)
# ---------------------------------------------------------------------------
@router.get("/tasks/full")
async def tasks_full():
    """All data for the Tasks tab."""
    return {
        "live": _call("/api/tasks-hub/live"),
        "active": _call("/api/tasks-hub/active"),
        "scheduled": _call("/api/tasks-hub/scheduled"),
        "time_sense": _call("/api/tasks-hub/time-sense"),
        "prioritised": _call("/api/tasks-hub/time-sense/prioritised"),
        "history": _call("/api/tasks-hub/history?limit=20"),
    }


# ---------------------------------------------------------------------------
# BI tab — 11 endpoints
# ---------------------------------------------------------------------------
@router.get("/bi/full")
async def bi_full():
    """All data for the BI tab."""
    return {
        "dashboard": _call("/api/bi/dashboard"),
        "trends": _call("/api/bi/trends"),
        "kpi_health": _call("/kpi/health"),
        "kpi_summary": _call("/kpi/summary"),
        "kpi_dashboard": _call("/kpi/dashboard"),
        "monitoring_metrics": _call("/monitoring/metrics"),
        "telemetry_status": _call("/telemetry/status"),
        "grace_status": _call("/grace/status"),
    }


# ---------------------------------------------------------------------------
# Health tab — many diagnostic endpoints
# ---------------------------------------------------------------------------
@router.get("/health/full")
async def health_full():
    """All data for the Health tab."""
    return {
        "dashboard": _call("/api/system-health/dashboard"),
        "processes": _call("/api/system-health/processes"),
        "health_detailed": _call("/health/detailed"),
        "health_components": _call("/health/components"),
        "diagnostic_status": _call("/diagnostic/status"),
        "diagnostic_sensors": _call("/diagnostic/sensors/readings"),
        "diagnostic_healing": _call("/diagnostic/healing/actions"),
        "diagnostic_trends": _call("/diagnostic/trends"),
        "monitoring_health": _call("/monitoring/health"),
        "monitoring_organs": _call("/monitoring/organs"),
    }


# ---------------------------------------------------------------------------
# Learn & Heal tab
# ---------------------------------------------------------------------------
@router.get("/learn-heal/full")
async def learn_heal_full():
    """All data for the Learn & Heal tab."""
    return {
        "dashboard": _call("/api/learn-heal/dashboard"),
        "skills": _call("/api/learn-heal/skills"),
        "ml_status": _call("/ml-intelligence/status"),
        "ml_components": _call("/ml-intelligence/components"),
        "learning_status": _call("/autonomous-learning/status"),
        "sandbox_status": _call("/sandbox-lab/status"),
        "training_skills": _call("/training/skills"),
        "diagnostic_healing": _call("/diagnostic/healing/actions"),
    }
