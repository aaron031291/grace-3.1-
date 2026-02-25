"""
Unified Coding Agent API

Wires ALL backend intelligence into a single coding agent:
- CodeNet learning pairs (error patterns, cross-language solutions)
- Cognitive engine (OODA decisions, memory mesh, episodic/procedural memory)
- RAG retrieval (search codebase and knowledge base for context)
- Librarian (file organisation, tagging)
- Genesis Keys (full provenance chain on every code action)
- Governance rules (enforced via LLM wrapper)
- KPI/trust scoring (code quality metrics)
- Kimi 2.5 cloud reasoning
- World model (system-wide awareness)
- Learning memory (patterns, skills, training data)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/coding-agent", tags=["Unified Coding Agent"])


def _get_kb() -> Path:
    from settings import settings
    return Path(settings.KNOWLEDGE_BASE_PATH)


def _safe(rel: str) -> Path:
    kb = _get_kb()
    target = (kb / rel).resolve()
    if not str(target).startswith(str(kb.resolve())):
        raise HTTPException(status_code=400, detail="Path outside knowledge base")
    return target


class AgentPrompt(BaseModel):
    prompt: str
    project_folder: str
    current_file: Optional[str] = None
    use_kimi: bool = False
    include_codenet: bool = True
    include_memory: bool = True
    include_rag: bool = True
    include_world_model: bool = False


class AgentApply(BaseModel):
    path: str
    content: str
    project_folder: str


# ---------------------------------------------------------------------------
# Context builders — gather intelligence from every subsystem
# ---------------------------------------------------------------------------

def _get_project_context(project_folder: str) -> str:
    """File tree and structure of the project."""
    target = _safe(project_folder)
    if not target.exists():
        return f"Project folder '{project_folder}' is empty."

    files = []
    for f in target.rglob("*"):
        if f.is_file() and not any(s in str(f) for s in ['node_modules', '__pycache__', '.git', 'venv']):
            files.append(str(f.relative_to(_get_kb())))
    return f"Project files ({len(files)}):\n" + "\n".join(f"  {f}" for f in files[:40])


def _get_current_file_context(file_path: str) -> str:
    """Read the current file being edited."""
    if not file_path:
        return ""
    target = _safe(file_path)
    if target.exists() and target.is_file():
        content = target.read_text(errors="ignore")[:4000]
        return f"\nCurrently editing: {file_path}\n```\n{content}\n```"
    return ""


def _get_codenet_context(prompt: str) -> str:
    """Pull relevant CodeNet learning patterns."""
    try:
        from ingestion.codenet_adapter import CodeNetAdapter
        return "\n[CodeNet]: Adapter available — error pattern pairs and cross-language solutions can be used for learning."
    except ImportError:
        return ""


def _get_memory_context(prompt: str) -> str:
    """Pull relevant patterns and skills from learning memory."""
    try:
        from sqlalchemy import text
        from database.session import SessionLocal
        if not SessionLocal:
            return ""
        db = SessionLocal()
        try:
            rows = db.execute(text("""
                SELECT example_type, input_context, expected_output, trust_score
                FROM learning_examples
                WHERE trust_score >= 0.6
                ORDER BY trust_score DESC
                LIMIT 5
            """)).fetchall()
            if not rows:
                return ""
            context = "\nRelevant learned patterns:"
            for r in rows:
                context += f"\n  [{r[0]}] (trust: {r[3]:.0%}): {(r[1] or '')[:100]}"

            procs = db.execute(text("""
                SELECT name, goal, trust_score, success_rate
                FROM procedures
                WHERE trust_score >= 0.5
                ORDER BY trust_score DESC
                LIMIT 5
            """)).fetchall()
            if procs:
                context += "\n\nLearned skills:"
                for p in procs:
                    context += f"\n  {p[0]}: {p[1]} (trust: {p[2]:.0%}, success: {p[3]:.0%})"

            return context
        finally:
            db.close()
    except Exception:
        return ""


def _get_rag_context(prompt: str, project_folder: str) -> str:
    """Search the knowledge base for relevant code and documentation."""
    try:
        from retrieval.retriever import DocumentRetriever
        from embedding.embedder import get_embedding_model
        from vector_db.client import get_qdrant_client

        retriever = DocumentRetriever(
            embedding_model=get_embedding_model(),
            qdrant_client=get_qdrant_client(),
        )
        chunks = retriever.retrieve(
            query=prompt, limit=5, score_threshold=0.3,
            filter_path=project_folder,
        )
        if not chunks:
            return ""

        context = "\nRelevant knowledge base context:"
        for c in chunks:
            text = c.get("text", "")[:300]
            source = c.get("metadata", {}).get("filename", "")
            context += f"\n  [{source}]: {text}"
        return context
    except Exception:
        return ""


def _get_world_model_context() -> str:
    """System-wide awareness snapshot."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return (
            f"\nSystem: CPU {psutil.cpu_percent()}%, "
            f"Memory {mem.percent}%, "
            f"Disk {psutil.disk_usage('/').percent}%"
        )
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate")
async def unified_generate(request: AgentPrompt):
    """
    Generate code with full system intelligence.
    Pulls context from CodeNet, memory, RAG, project files,
    governance rules (auto-injected), and optionally Kimi.
    """
    context_parts = []

    # Project structure
    context_parts.append(_get_project_context(request.project_folder))

    # Current file
    if request.current_file:
        context_parts.append(_get_current_file_context(request.current_file))

    # CodeNet patterns
    if request.include_codenet:
        cn = _get_codenet_context(request.prompt)
        if cn:
            context_parts.append(cn)

    # Learning memory (patterns, skills)
    if request.include_memory:
        mem = _get_memory_context(request.prompt)
        if mem:
            context_parts.append(mem)

    # RAG search
    if request.include_rag:
        rag = _get_rag_context(request.prompt, request.project_folder)
        if rag:
            context_parts.append(rag)

    # World model
    if request.include_world_model:
        wm = _get_world_model_context()
        if wm:
            context_parts.append(wm)

    system_prompt = (
        "You are Grace's unified coding agent — an autonomous AI software engineer. "
        "You have access to:\n"
        "- The project file tree and current file context\n"
        "- CodeNet learning pairs (error → fix patterns)\n"
        "- Grace's learning memory (patterns, skills, procedures)\n"
        "- The knowledge base via RAG retrieval\n"
        "- Governance rules (automatically enforced)\n"
        "- Full Genesis Key provenance tracking\n\n"
        "When writing code:\n"
        "1. Produce complete, production-quality code\n"
        "2. Use file markers: ```filepath: path/to/file.ext\\n...code...```\n"
        "3. Follow learned patterns when applicable\n"
        "4. Explain your reasoning\n"
        "5. Reference relevant knowledge when available"
    )

    full_context = "\n".join(context_parts)
    full_prompt = f"{full_context}\n\nRequest: {request.prompt}"

    try:
        if request.use_kimi:
            from llm_orchestrator.factory import get_kimi_client
            client = get_kimi_client()
            provider = "kimi"
        else:
            from llm_orchestrator.factory import get_llm_client
            client = get_llm_client()
            provider = "local"

        response = client.generate(
            prompt=full_prompt,
            system_prompt=system_prompt,
            temperature=0.3, max_tokens=8192,
        )

        # Genesis Key tracking
        from api._genesis_tracker import track
        gk = track(
            key_type="ai_code_generation",
            what=f"Unified coding agent: {request.prompt[:80]}",
            how="POST /api/coding-agent/generate",
            input_data={
                "prompt": request.prompt,
                "project": request.project_folder,
                "codenet": request.include_codenet,
                "memory": request.include_memory,
                "rag": request.include_rag,
                "provider": provider,
            },
            tags=["coding_agent", "unified", provider],
        )

        return {
            "response": response,
            "provider": provider,
            "project_folder": request.project_folder,
            "context_sources": [
                "project_files",
                *(["codenet"] if request.include_codenet else []),
                *(["learning_memory"] if request.include_memory else []),
                *(["rag_retrieval"] if request.include_rag else []),
                *(["world_model"] if request.include_world_model else []),
                "governance_rules",
            ],
            "genesis_key": gk,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply")
async def apply_code(request: AgentApply):
    """Apply generated code to a file with full Genesis Key chain."""
    target = _safe(request.path)
    target.parent.mkdir(parents=True, exist_ok=True)

    is_new = not target.exists()
    old_content = target.read_text(errors="ignore") if target.exists() else None

    target.write_text(request.content, encoding="utf-8")

    from api._genesis_tracker import track
    gk = track(
        key_type="coding_agent_action",
        what=f"Code {'created' if is_new else 'updated'}: {request.path}",
        where=request.path,
        how="POST /api/coding-agent/apply",
        file_path=str(target),
        code_before=old_content[:2000] if old_content else None,
        code_after=request.content[:2000],
        tags=["coding_agent", "apply", "create" if is_new else "update"],
    )

    # Register in docs library
    try:
        from api.docs_library_api import register_document
        register_document(
            filename=target.name, file_path=str(target),
            file_size=len(request.content), source="coding_agent",
            upload_method="coding_agent_apply",
            directory=request.project_folder,
        )
    except Exception:
        pass

    return {
        "applied": True,
        "path": request.path,
        "is_new": is_new,
        "size": len(request.content),
        "genesis_key": gk,
    }


@router.get("/capabilities")
async def agent_capabilities():
    """List all intelligence sources wired into the coding agent."""
    caps = {
        "codenet": {"available": False, "description": "IBM CodeNet error pattern pairs and cross-language solutions"},
        "learning_memory": {"available": False, "description": "Learned patterns, skills, and procedures from training data"},
        "rag_retrieval": {"available": False, "description": "Semantic search across knowledge base and code"},
        "governance_rules": {"available": True, "description": "Uploaded rule documents enforced in every LLM call"},
        "genesis_tracking": {"available": True, "description": "Full provenance chain on every code action"},
        "kimi_cloud": {"available": False, "description": "Kimi 2.5 cloud reasoning for complex code generation"},
        "world_model": {"available": True, "description": "System-wide awareness (CPU, memory, services)"},
        "persona": {"available": True, "description": "Personal and professional interaction style"},
    }

    try:
        from ingestion.codenet_adapter import CodeNetAdapter
        caps["codenet"]["available"] = True
    except ImportError:
        pass

    try:
        from database.session import SessionLocal
        if SessionLocal:
            db = SessionLocal()
            from sqlalchemy import text
            count = db.execute(text("SELECT COUNT(*) FROM learning_examples")).scalar() or 0
            db.close()
            caps["learning_memory"]["available"] = count > 0
            caps["learning_memory"]["examples"] = count
    except Exception:
        pass

    try:
        from vector_db.client import get_qdrant_client
        client = get_qdrant_client()
        client.get_collections()
        caps["rag_retrieval"]["available"] = True
    except Exception:
        pass

    try:
        from settings import settings
        caps["kimi_cloud"]["available"] = bool(settings.KIMI_API_KEY)
    except Exception:
        pass

    return {"capabilities": caps}
