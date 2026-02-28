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
from pydantic import BaseModel as _BaseModel

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

    from api.export_api import router as export_router
    app.include_router(export_router)

    from api.oracle_explorer_api import router as oracle_explorer_router
    app.include_router(oracle_explorer_router)

    # Autonomous librarian endpoints
    from fastapi import APIRouter as _AR
    librarian_auto = _AR(prefix="/api/v1/librarian", tags=["Autonomous Librarian"])

    @librarian_auto.get("/status")
    async def librarian_status():
        from cognitive.librarian_autonomous import get_autonomous_librarian
        return get_autonomous_librarian().get_status()

    @librarian_auto.post("/organise-all")
    async def librarian_organise_all(dry_run: bool = True):
        from cognitive.librarian_autonomous import get_autonomous_librarian
        return get_autonomous_librarian().organise_all(dry_run=dry_run)

    @librarian_auto.post("/ensure-taxonomy")
    async def librarian_ensure_taxonomy():
        from cognitive.librarian_autonomous import get_autonomous_librarian
        return get_autonomous_librarian().ensure_taxonomy()

    @librarian_auto.post("/organise")
    async def librarian_organise_file(file_path: str):
        from cognitive.librarian_autonomous import get_autonomous_librarian
        return get_autonomous_librarian().organise_file(file_path)

    app.include_router(librarian_auto)

    # HUNTER assimilator endpoints
    hunter_router = _AR(prefix="/api/v1/hunter", tags=["HUNTER Assimilator"])

    class _HunterRequest(_BaseModel):
        code: str
        description: str = ""
        project_folder: str = ""

    @hunter_router.post("/assimilate")
    async def hunter_assimilate(request: _HunterRequest):
        from cognitive.hunter_assimilator import get_hunter
        result = get_hunter().assimilate(request.code, request.description, request.project_folder)
        return {
            "request_id": result.request_id, "status": result.status,
            "files_created": result.files_created, "schemas_detected": result.schemas_detected,
            "issues_found": result.issues_found, "issues_fixed": result.issues_fixed,
            "trust_score": result.trust_score, "handshake_sent": result.handshake_sent,
            "steps": [{"step": s.get("step"), "success": not s.get("error")} for s in result.steps],
            "genesis_key": result.genesis_key,
        }

    @hunter_router.get("/history")
    async def hunter_history():
        from cognitive.hunter_assimilator import get_hunter
        return {"history": get_hunter().get_history()}

    app.include_router(hunter_router)

    # System Registry endpoints
    registry_router = _AR(prefix="/api/v1/registry", tags=["System Registry"])

    @registry_router.get("/all")
    async def registry_all():
        from cognitive.system_registry import get_system_registry
        reg = get_system_registry()
        health = reg.check_health()
        return {"health": health, "components": reg.get_all()}

    @registry_router.get("/by-category")
    async def registry_by_category():
        from cognitive.system_registry import get_system_registry
        return get_system_registry().get_by_category()

    @registry_router.get("/health")
    async def registry_health():
        from cognitive.system_registry import get_system_registry
        return get_system_registry().check_health()

    @registry_router.get("/status/{status}")
    async def registry_by_status(status: str):
        from cognitive.system_registry import get_system_registry
        return {"components": get_system_registry().get_by_status(status)}

    @registry_router.get("/new")
    async def registry_new_components():
        from cognitive.system_registry import get_system_registry
        all_comps = get_system_registry().get_all()
        return {"components": [c for c in all_comps if c["is_new"]]}

    app.include_router(registry_router)

    from api.domain_api import router as domain_router
    app.include_router(domain_router)

    # Auto-Research endpoints
    research_router = _AR(prefix="/api/v1/research", tags=["Auto Research"])

    @research_router.post("/analyse")
    async def analyse_folder(folder_path: str):
        from cognitive.auto_research import get_auto_research
        return get_auto_research().analyse_folder(folder_path)

    @research_router.post("/run")
    async def run_research(folder_path: str, depth: int = 1, max_queries: int = 10):
        from cognitive.auto_research import get_auto_research
        return get_auto_research().run_research_cycle(folder_path, depth, max_queries)

    @research_router.get("/history")
    async def research_history():
        from cognitive.auto_research import get_auto_research
        return {"history": get_auto_research().get_history()}

    app.include_router(research_router)

    # File Generator endpoints
    gen_router = _AR(prefix="/api/v1/generate", tags=["File Generator"])

    class _GenRequest(_BaseModel):
        prompt: str
        filename: str
        folder: str = ""
        use_kimi: bool = True

    @gen_router.post("/file")
    async def generate_file(request: _GenRequest):
        from cognitive.file_generator import get_file_generator
        return get_file_generator().generate(
            prompt=request.prompt, filename=request.filename,
            folder=request.folder, use_kimi=request.use_kimi,
        )

    app.include_router(gen_router)
