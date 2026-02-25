"""
World Model API - Bird's Eye View of Grace System

Aggregates state from all subsystems to provide a unified view.
Powers the Chat tab's system awareness and the Kimi 2.5 analysis.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import os
import psutil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/world-model", tags=["World Model"])


class SystemState(BaseModel):
    timestamp: str
    health: Dict[str, Any]
    subsystems: Dict[str, Any]
    knowledge_base: Dict[str, Any]
    active_processes: Dict[str, Any]
    capabilities: List[str]


class WorldModelChatRequest(BaseModel):
    query: str
    include_system_state: bool = True
    provider: Optional[str] = None


class WorldModelChatResponse(BaseModel):
    response: str
    system_state_snapshot: Optional[Dict[str, Any]] = None
    provider_used: str
    model_used: str


def _get_knowledge_base_stats() -> Dict[str, Any]:
    """Get knowledge base directory statistics."""
    from settings import settings
    kb_path = settings.KNOWLEDGE_BASE_PATH
    stats = {"path": kb_path, "exists": os.path.exists(kb_path)}

    if stats["exists"]:
        total_files = 0
        total_size = 0
        file_types = {}
        directories = 0
        for root, dirs, files in os.walk(kb_path):
            directories += len(dirs)
            for f in files:
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


def _get_llm_status() -> Dict[str, Any]:
    """Get LLM provider status."""
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
    """Get database status."""
    try:
        from database.connection import DatabaseConnection
        engine = DatabaseConnection.get_engine()
        return {
            "connected": engine is not None,
            "type": str(engine.url.get_backend_name()) if engine else "unknown",
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}


def _get_qdrant_status() -> Dict[str, Any]:
    """Get Qdrant vector DB status."""
    try:
        from vector_db.client import get_qdrant_client
        client = get_qdrant_client()
        collections = client.get_collections()
        return {
            "connected": True,
            "collections": [c.name for c in collections.collections],
            "total_collections": len(collections.collections),
        }
    except Exception:
        return {"connected": False, "collections": []}


def _get_system_resources() -> Dict[str, Any]:
    """Get system resource utilization."""
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


@router.get("/state", response_model=SystemState)
async def get_system_state():
    """Get the complete system state - bird's eye view of Grace."""
    kb_stats = _get_knowledge_base_stats()
    llm_status = _get_llm_status()
    db_status = _get_database_status()
    qdrant_status = _get_qdrant_status()
    resources = _get_system_resources()

    subsystems = {
        "llm": llm_status,
        "database": db_status,
        "vector_db": qdrant_status,
        "resources": resources,
    }

    capabilities = ["chat", "rag_retrieval", "file_management", "ingestion"]
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

    return SystemState(
        timestamp=datetime.utcnow().isoformat(),
        health={
            "overall": overall_health,
            "llm": "up" if llm_status.get("primary_available") else "down",
            "database": "up" if db_status.get("connected") else "down",
            "vector_db": "up" if qdrant_status.get("connected") else "down",
            "kimi_cloud": "configured" if llm_status.get("kimi_configured") else "not_configured",
        },
        subsystems=subsystems,
        knowledge_base=kb_stats,
        active_processes={
            "api_server": "running",
        },
        capabilities=capabilities,
    )


@router.post("/chat", response_model=WorldModelChatResponse)
async def world_model_chat(request: WorldModelChatRequest):
    """
    Chat with Grace about the system using world model context.
    Optionally uses Kimi 2.5 for cloud-powered reasoning.
    """
    from llm_orchestrator.factory import get_llm_client, get_kimi_client
    from settings import settings

    system_state = None
    state_context = ""

    if request.include_system_state:
        state_response = await get_system_state()
        system_state = state_response.model_dump()
        state_context = _build_state_context(system_state)

    provider = request.provider or ("kimi" if settings.KIMI_API_KEY else settings.LLM_PROVIDER)

    system_prompt = (
        "You are Grace, an autonomous AI system with full self-awareness. "
        "You can observe and reason about your own subsystems, health, "
        "knowledge base, and capabilities. Provide insightful analysis "
        "from a bird's eye perspective when asked about your system state. "
        "Be conversational but precise."
    )

    if state_context:
        system_prompt += f"\n\nCurrent system state:\n{state_context}"

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

        return WorldModelChatResponse(
            response=response_text,
            system_state_snapshot=system_state,
            provider_used=provider,
            model_used=model_used,
        )
    except Exception as e:
        logger.error(f"World model chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/subsystems")
async def list_subsystems():
    """List all registered subsystems and their status."""
    return {
        "subsystems": [
            {"name": "Chat Engine", "status": "active", "description": "Multi-model chat with RAG"},
            {"name": "Librarian", "status": "active", "description": "Document organization and tagging"},
            {"name": "RAG Retrieval", "status": "active", "description": "Semantic search and retrieval"},
            {"name": "Cognitive Engine", "status": "active", "description": "OODA loop reasoning"},
            {"name": "File Manager", "status": "active", "description": "Knowledge base CRUD operations"},
            {"name": "Ingestion Pipeline", "status": "active", "description": "Document processing and vectorization"},
            {"name": "Genesis Tracking", "status": "active", "description": "Provenance and lineage tracking"},
            {"name": "Learning System", "status": "active", "description": "Continuous learning and memory"},
            {"name": "Kimi Cloud", "status": "configured" if getattr(__import__('settings', fromlist=['settings']).settings, 'KIMI_API_KEY', '') else "not_configured", "description": "Kimi 2.5 cloud reasoning"},
        ]
    }


def _build_state_context(state: Dict[str, Any]) -> str:
    """Build a readable context string from system state for the LLM."""
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

    if "capabilities" in state:
        lines.append(f"\nActive Capabilities: {', '.join(state['capabilities'])}")

    if "subsystems" in state:
        res = state["subsystems"].get("resources", {})
        if res:
            lines.append(f"\nResources: CPU {res.get('cpu_percent', '?')}%, "
                          f"Memory {res.get('memory_percent', '?')}%")

    return "\n".join(lines)
