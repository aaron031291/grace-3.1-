"""
Grace API v1 — Clean resource-based REST API

10 resource endpoints replacing 440:
  /api/v1/chats        — Chat, world model, cognitive, MCP
  /api/v1/files        — Folders, librarian, file CRUD
  /api/v1/documents    — Docs library, ingestion, retrieval
  /api/v1/governance   — Approvals, scores, rules, persona, genesis keys
  /api/v1/sources      — Whitelist API + web sources
  /api/v1/training     — Oracle, learning memory, skills
  /api/v1/projects     — Codebase, coding agent
  /api/v1/tasks        — Tasks, scheduling, TimeSense
  /api/v1/system       — Health, BI, APIs, manifest
  /api/v1/agent        — Unified coding agent

Same intelligence. Same 28 systems. Same governance. Clean routing.
"""

from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")


def register_v1(app):
    """Register all v1 resource routers."""
    from .chats import router as chats_router
    from .files import router as files_router
    from .documents import router as documents_router
    from .governance import router as governance_router
    from .sources import router as sources_router
    from .training import router as training_router
    from .projects import router as projects_router
    from .tasks import router as tasks_router
    from .system import router as system_router
    from .agent import router as agent_router

    app.include_router(chats_router)
    app.include_router(files_router)
    app.include_router(documents_router)
    app.include_router(governance_router)
    app.include_router(sources_router)
    app.include_router(training_router)
    app.include_router(projects_router)
    app.include_router(tasks_router)
    app.include_router(system_router)
    app.include_router(agent_router)

    from api.agent_rules_api import router as agent_rules_router
    app.include_router(agent_rules_router)
