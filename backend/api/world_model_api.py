"""
World Model API - Bird's Eye View of Grace System

Aggregates state from ALL subsystems: source code, databases, tables,
APIs, chats, folders, knowledge base, vector DB, LLM providers.
Powers the Chat tab's system awareness and Kimi 2.5 analysis.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import logging
import os
import glob as globmod
import psutil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/world-model", tags=["World Model"])


class SystemState(BaseModel):
    timestamp: str
    health: Dict[str, Any]
    subsystems: Dict[str, Any]
    knowledge_base: Dict[str, Any]
    source_code: Dict[str, Any]
    database: Dict[str, Any]
    chats: Dict[str, Any]
    apis: Dict[str, Any]
    active_processes: Dict[str, Any]
    capabilities: List[str]


class WorldModelChatRequest(BaseModel):
    query: str
    include_system_state: bool = True
    include_source_code: bool = False
    source_file_path: Optional[str] = None
    provider: Optional[str] = None


class WorldModelChatResponse(BaseModel):
    response: str
    system_state_snapshot: Optional[Dict[str, Any]] = None
    provider_used: str
    model_used: str


class SourceCodeRequest(BaseModel):
    file_path: str
    use_kimi: bool = False
    instruction: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal helpers – gather data from every subsystem
# ---------------------------------------------------------------------------

def _get_knowledge_base_stats() -> Dict[str, Any]:
    from settings import settings
    kb_path = settings.KNOWLEDGE_BASE_PATH
    stats = {"path": kb_path, "exists": os.path.exists(kb_path)}
    if stats["exists"]:
        total_files = 0
        total_size = 0
        file_types = {}
        directories = 0
        for root, dirs, files in os.walk(kb_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            directories += len(dirs)
            for f in files:
                if f.startswith('.'):
                    continue
                total_files += 1
                fpath = os.path.join(root, f)
                try:
                    total_size += os.path.getsize(fpath)
                except OSError:
                    pass
                ext = os.path.splitext(f)[1].lower()
                file_types[ext] = file_types.get(ext, 0) + 1
        stats["total_files"] = total_files
        stats["total_directories"] = directories
        stats["total_size_mb"] = round(total_size / (1024 * 1024), 2)
        stats["file_types"] = dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10])
    return stats


def _get_source_code_stats() -> Dict[str, Any]:
    """Scan the Grace backend source tree for a high-level overview."""
    backend = Path(__file__).parent.parent
    stats: Dict[str, Any] = {"root": str(backend)}
    py_files: List[str] = []
    total_lines = 0
    for p in backend.rglob("*.py"):
        if any(skip in str(p) for skip in ["venv", "node_modules", "__pycache__", "mcp_repos", ".git"]):
            continue
        rel = str(p.relative_to(backend))
        py_files.append(rel)
        try:
            total_lines += sum(1 for _ in open(p, errors="ignore"))
        except Exception:
            pass
    stats["total_python_files"] = len(py_files)
    stats["total_lines"] = total_lines
    top_dirs = {}
    for f in py_files:
        d = f.split(os.sep)[0]
        top_dirs[d] = top_dirs.get(d, 0) + 1
    stats["modules"] = dict(sorted(top_dirs.items(), key=lambda x: x[1], reverse=True))
    return stats


def _get_llm_status() -> Dict[str, Any]:
    from settings import settings
    status = {
        "primary_provider": settings.LLM_PROVIDER,
        "primary_model": settings.LLM_MODEL or settings.OLLAMA_LLM_DEFAULT,
        "kimi_configured": bool(settings.KIMI_API_KEY),
        "kimi_model": settings.KIMI_MODEL,
    }
    try:
        from llm_orchestrator.factory import get_llm_client
        client = get_llm_client()
        status["primary_available"] = client.is_running()
    except Exception:
        status["primary_available"] = False
    return status


def _get_database_status() -> Dict[str, Any]:
    try:
        from database.connection import DatabaseConnection
        engine = DatabaseConnection.get_engine()
        if engine is None:
            return {"connected": False}
        from sqlalchemy import inspect as sa_inspect, text
        inspector = sa_inspect(engine)
        tables = inspector.get_table_names()
        row_counts = {}
        with engine.connect() as conn:
            for t in tables[:30]:
                try:
                    r = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"'))
                    row_counts[t] = r.scalar()
                except Exception:
                    row_counts[t] = "?"
        return {
            "connected": True,
            "type": str(engine.url.get_backend_name()),
            "tables": tables,
            "table_count": len(tables),
            "row_counts": row_counts,
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}


def _get_qdrant_status() -> Dict[str, Any]:
    try:
        from vector_db.client import get_qdrant_client
        client = get_qdrant_client()
        collections = client.get_collections()
        info = []
        for c in collections.collections:
            try:
                cinfo = client.get_collection(c.name)
                info.append({
                    "name": c.name,
                    "vectors": cinfo.vectors_count,
                    "points": cinfo.points_count,
                })
            except Exception:
                info.append({"name": c.name})
        return {
            "connected": True,
            "collections": info,
            "total_collections": len(info),
        }
    except Exception:
        return {"connected": False, "collections": []}


def _get_system_resources() -> Dict[str, Any]:
    try:
        mem = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_total_gb": round(mem.total / (1024**3), 1),
            "memory_used_gb": round(mem.used / (1024**3), 1),
            "memory_percent": mem.percent,
            "disk_usage_percent": psutil.disk_usage('/').percent,
        }
    except Exception:
        return {}


def _get_chat_stats() -> Dict[str, Any]:
    """Pull chat stats from the database."""
    try:
        from database.connection import DatabaseConnection
        from sqlalchemy import text
        engine = DatabaseConnection.get_engine()
        if engine is None:
            return {"available": False}
        with engine.connect() as conn:
            r = conn.execute(text("SELECT COUNT(*) FROM chats"))
            total_chats = r.scalar()
            r2 = conn.execute(text("SELECT COUNT(*) FROM chat_history"))
            total_messages = r2.scalar()
        return {
            "available": True,
            "total_chats": total_chats,
            "total_messages": total_messages,
        }
    except Exception:
        return {"available": False}


def _get_api_routes() -> Dict[str, Any]:
    """List all registered API routes in the FastAPI app."""
    try:
        from app import app
        routes = []
        for route in app.routes:
            if hasattr(route, "methods"):
                for method in route.methods:
                    if method in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                        routes.append({"method": method, "path": route.path})
        return {"total_routes": len(routes), "routes": routes[:100]}
    except Exception:
        return {"total_routes": 0, "routes": []}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/state")
async def get_system_state():
    """Complete system state – bird's eye view of Grace."""
    kb_stats = _get_knowledge_base_stats()
    llm_status = _get_llm_status()
    db_status = _get_database_status()
    qdrant_status = _get_qdrant_status()
    resources = _get_system_resources()
    source_stats = _get_source_code_stats()
    chat_stats = _get_chat_stats()
    api_info = _get_api_routes()

    subsystems = {
        "llm": llm_status,
        "vector_db": qdrant_status,
        "resources": resources,
    }

    capabilities = ["chat", "rag_retrieval", "file_management", "ingestion",
                     "source_code_access", "database_tables"]
    if llm_status.get("primary_available"):
        capabilities.extend(["cognitive_reasoning", "librarian_ai"])
    if llm_status.get("kimi_configured"):
        capabilities.extend(["kimi_cloud_reasoning", "long_context_analysis"])
    if qdrant_status.get("connected"):
        capabilities.extend(["semantic_search", "vector_retrieval"])

    overall_health = "healthy"
    if not llm_status.get("primary_available"):
        overall_health = "degraded"
    if not db_status.get("connected"):
        overall_health = "critical"

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "health": {
            "overall": overall_health,
            "llm": "up" if llm_status.get("primary_available") else "down",
            "database": "up" if db_status.get("connected") else "down",
            "vector_db": "up" if qdrant_status.get("connected") else "down",
            "kimi_cloud": "configured" if llm_status.get("kimi_configured") else "not_configured",
        },
        "subsystems": subsystems,
        "knowledge_base": kb_stats,
        "source_code": source_stats,
        "database": db_status,
        "chats": chat_stats,
        "apis": api_info,
        "active_processes": {"api_server": "running"},
        "capabilities": capabilities,
    }


@router.post("/chat")
async def world_model_chat(request: WorldModelChatRequest):
    """Chat with Grace using full world model context (all APIs, source, DB, etc.)."""
    from llm_orchestrator.factory import get_llm_client, get_kimi_client
    from settings import settings

    system_state = None
    state_context = ""
    source_context = ""

    if request.include_system_state:
        system_state = await get_system_state()
        state_context = _build_state_context(system_state)

    if request.include_source_code and request.source_file_path:
        source_context = _read_source_file(request.source_file_path)

    provider = request.provider or ("kimi" if settings.KIMI_API_KEY else settings.LLM_PROVIDER)

    system_prompt = (
        "You are Grace, an autonomous AI system with full self-awareness. "
        "You have access to your own source code, all databases and tables, "
        "every API endpoint, the knowledge base, vector store, chat history, "
        "and all subsystems. Provide insightful analysis from a bird's eye "
        "perspective. Be conversational but precise. When discussing code, "
        "reference actual file paths and module names."
    )

    if state_context:
        system_prompt += f"\n\nCurrent system state:\n{state_context}"
    if source_context:
        system_prompt += f"\n\nSource code context:\n{source_context}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.query},
    ]

    try:
        if provider == "kimi":
            client = get_kimi_client()
            model_used = settings.KIMI_MODEL
        else:
            client = get_llm_client()
            model_used = settings.LLM_MODEL or settings.OLLAMA_LLM_DEFAULT

        response_text = client.chat(messages=messages, temperature=0.7)

        from api._genesis_tracker import track
        gk = track(
            key_type="ai_response",
            what=f"World model chat: {request.query[:80]}",
            how="POST /api/world-model/chat",
            input_data={"query": request.query, "provider": provider},
            tags=["world_model", "chat", provider],
        )

        return {
            "response": response_text,
            "system_state_snapshot": system_state,
            "provider_used": provider,
            "model_used": model_used,
            "genesis_key": gk,
        }
    except Exception as e:
        logger.error(f"World model chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/source/tree")
async def source_code_tree():
    """Get the Grace backend source code tree structure."""
    backend = Path(__file__).parent.parent
    skip_dirs = {"venv", "node_modules", "__pycache__", "mcp_repos", ".git",
                 "models", "data", ".pytest_cache", ".mypy_cache"}

    def _tree(p: Path, depth: int = 0, max_depth: int = 4):
        if depth > max_depth:
            return None
        name = p.name
        if name in skip_dirs or name.startswith('.'):
            return None
        if p.is_file():
            return {"name": name, "type": "file", "path": str(p.relative_to(backend))}
        children = []
        try:
            for item in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                child = _tree(item, depth + 1, max_depth)
                if child:
                    children.append(child)
        except PermissionError:
            pass
        return {"name": name or "backend", "type": "directory", "children": children}

    return _tree(backend)


@router.get("/source/file")
async def read_source_file(path: str = Query(..., description="Relative path from backend root")):
    """Read a source code file from the Grace backend."""
    content = _read_source_file(path)
    if content.startswith("[Error"):
        raise HTTPException(status_code=404, detail=content)
    return {"path": path, "content": content, "lines": content.count('\n') + 1}


@router.post("/source/analyze")
async def analyze_source_code(request: SourceCodeRequest):
    """Analyze a source code file with AI (optionally Kimi 2.5)."""
    content = _read_source_file(request.file_path)
    if content.startswith("[Error"):
        raise HTTPException(status_code=404, detail=content)

    instruction = request.instruction or "Analyze this source code file and explain its purpose, key functions, dependencies, and how it fits in the Grace system architecture."

    try:
        if request.use_kimi:
            from llm_orchestrator.factory import get_kimi_client
            client = get_kimi_client()
        else:
            from llm_orchestrator.factory import get_llm_client
            client = get_llm_client()

        prompt = f"{instruction}\n\nFile: {request.file_path}\n```python\n{content[:8000]}\n```"
        response = client.generate(prompt=prompt, temperature=0.3, max_tokens=4096)

        from api._genesis_tracker import track
        track(key_type="ai_response", what=f"Source code analysis: {request.file_path}", where=request.file_path, how="POST /api/world-model/source/analyze", file_path=request.file_path, tags=["source_analysis", "ai"])

        return {"file_path": request.file_path, "analysis": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/tables")
async def get_database_tables():
    """Get all database tables with their schemas and row counts."""
    return _get_database_status()


@router.get("/database/table/{table_name}")
async def get_table_sample(table_name: str, limit: int = 20):
    """Get a sample of rows from a database table."""
    try:
        from database.connection import DatabaseConnection
        from sqlalchemy import text
        engine = DatabaseConnection.get_engine()
        if engine is None:
            raise HTTPException(status_code=503, detail="Database not connected")
        with engine.connect() as conn:
            result = conn.execute(text(f'SELECT * FROM "{table_name}" LIMIT {min(limit, 100)}'))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            count_r = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            total = count_r.scalar()
        return {"table": table_name, "columns": columns, "total_rows": total, "rows": rows}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/apis")
async def get_all_api_routes():
    """Get all registered API routes."""
    return _get_api_routes()


@router.get("/subsystems")
async def list_subsystems():
    """List all registered subsystems and their live status."""
    from settings import settings

    db = _get_database_status()
    vdb = _get_qdrant_status()
    llm = _get_llm_status()

    return {
        "subsystems": [
            {"name": "Chat Engine", "status": "active", "description": "Multi-model chat with RAG", "type": "core"},
            {"name": "Librarian", "status": "active", "description": "Document organization, tagging, auto-filing", "type": "core"},
            {"name": "RAG Retrieval", "status": "active" if vdb.get("connected") else "degraded", "description": "Semantic search and retrieval", "type": "core"},
            {"name": "Cognitive Engine", "status": "active", "description": "OODA loop reasoning", "type": "intelligence"},
            {"name": "File Manager", "status": "active", "description": "Knowledge base CRUD, infinite nesting", "type": "core"},
            {"name": "Ingestion Pipeline", "status": "active", "description": "Document processing and vectorization", "type": "data"},
            {"name": "Source Code Access", "status": "active", "description": "Read and analyze Grace's own source code", "type": "meta"},
            {"name": "Database", "status": "active" if db.get("connected") else "down", "description": f"{db.get('table_count', 0)} tables", "type": "data"},
            {"name": "Vector DB (Qdrant)", "status": "active" if vdb.get("connected") else "down", "description": f"{vdb.get('total_collections', 0)} collections", "type": "data"},
            {"name": "Genesis Tracking", "status": "active", "description": "Provenance and lineage tracking", "type": "governance"},
            {"name": "Learning System", "status": "active", "description": "Continuous learning and memory", "type": "intelligence"},
            {"name": "Kimi 2.5 Cloud", "status": "configured" if settings.KIMI_API_KEY else "not_configured", "description": "Moonshot AI cloud reasoning", "type": "cloud"},
            {"name": "LLM Provider", "status": "active" if llm.get("primary_available") else "down", "description": f"{llm.get('primary_provider', '?')} / {llm.get('primary_model', '?')}", "type": "core"},
        ]
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_source_file(relative_path: str) -> str:
    """Safely read a source file from the backend tree."""
    backend = Path(__file__).parent.parent
    target = (backend / relative_path).resolve()
    if not str(target).startswith(str(backend.resolve())):
        return "[Error: path outside backend directory]"
    if not target.exists():
        return f"[Error: file not found: {relative_path}]"
    if not target.is_file():
        return "[Error: not a file]"
    try:
        return target.read_text(errors="ignore")[:50000]
    except Exception as e:
        return f"[Error reading file: {e}]"


def _build_state_context(state: Dict[str, Any]) -> str:
    lines = []
    if "health" in state:
        lines.append("Health Status:")
        for k, v in state["health"].items():
            lines.append(f"  {k}: {v}")

    if "knowledge_base" in state:
        kb = state["knowledge_base"]
        lines.append(f"\nKnowledge Base: {kb.get('total_files', 0)} files, "
                      f"{kb.get('total_directories', 0)} directories, "
                      f"{kb.get('total_size_mb', 0)} MB")

    if "source_code" in state:
        sc = state["source_code"]
        lines.append(f"\nSource Code: {sc.get('total_python_files', 0)} Python files, "
                      f"{sc.get('total_lines', 0)} lines")
        if sc.get("modules"):
            lines.append(f"  Modules: {', '.join(f'{k}({v})' for k, v in list(sc['modules'].items())[:10])}")

    if "database" in state:
        db = state["database"]
        lines.append(f"\nDatabase: {'connected' if db.get('connected') else 'disconnected'}, "
                      f"{db.get('table_count', 0)} tables")
        if db.get("row_counts"):
            for t, c in list(db["row_counts"].items())[:10]:
                lines.append(f"  {t}: {c} rows")

    if "chats" in state:
        ch = state["chats"]
        lines.append(f"\nChats: {ch.get('total_chats', 0)} conversations, "
                      f"{ch.get('total_messages', 0)} messages")

    if "apis" in state:
        lines.append(f"\nAPIs: {state['apis'].get('total_routes', 0)} registered endpoints")

    if "capabilities" in state:
        lines.append(f"\nCapabilities: {', '.join(state['capabilities'])}")

    if "subsystems" in state:
        res = state["subsystems"].get("resources", {})
        if res:
            lines.append(f"\nResources: CPU {res.get('cpu_percent', '?')}%, "
                          f"Memory {res.get('memory_percent', '?')}%")

    return "\n".join(lines)
