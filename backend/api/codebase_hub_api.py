"""
Codebase Hub API — Code projects linked to domain folders

Projects live inside knowledge base folders (e.g. green_gardens/mobile_app/).
Full code file CRUD + coding agent interface for AI-driven development.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import json
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/codebase-hub", tags=["Codebase Hub"])


def _get_kb() -> Path:
    from settings import settings
    return Path(settings.KNOWLEDGE_BASE_PATH)


def _safe(rel: str) -> Path:
    kb = _get_kb()
    target = (kb / rel).resolve()
    if not str(target).startswith(str(kb.resolve())):
        raise HTTPException(status_code=400, detail="Path outside knowledge base")
    return target


class ProjectCreate(BaseModel):
    name: str
    domain_folder: str
    description: Optional[str] = ""
    project_type: str = "general"  # general, web, mobile, api, landing_page


class FileWrite(BaseModel):
    path: str
    content: str


class CodingAgentRequest(BaseModel):
    prompt: str
    project_folder: str
    file_context: Optional[str] = None
    use_kimi: bool = False


PROJECTS_META = Path(__file__).parent.parent / "data" / "code_projects.json"


def _load_projects() -> List[Dict]:
    PROJECTS_META.parent.mkdir(parents=True, exist_ok=True)
    if PROJECTS_META.exists():
        try:
            return json.loads(PROJECTS_META.read_text())
        except Exception:
            pass
    return []


def _save_projects(data: List[Dict]):
    PROJECTS_META.parent.mkdir(parents=True, exist_ok=True)
    PROJECTS_META.write_text(json.dumps(data, indent=2, default=str))


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@router.get("/projects")
async def list_projects():
    """List all code projects with their domain folders."""
    return {"projects": _load_projects()}


@router.post("/projects")
async def create_project(request: ProjectCreate):
    """Create a new code project linked to a domain folder."""
    projects = _load_projects()
    kb = _get_kb()
    folder = kb / request.domain_folder / request.name.lower().replace(" ", "_")
    folder.mkdir(parents=True, exist_ok=True)

    project = {
        "id": f"proj-{len(projects) + 1:04d}",
        "name": request.name,
        "domain_folder": request.domain_folder,
        "project_folder": str(folder.relative_to(kb)),
        "project_type": request.project_type,
        "description": request.description,
        "created_at": datetime.utcnow().isoformat(),
        "file_count": 0,
    }
    projects.append(project)
    _save_projects(projects)

    from api._genesis_tracker import track
    track(key_type="file_op", what=f"Project created: {request.name} in {request.domain_folder}",
          file_path=str(folder), tags=["codebase", "project", request.project_type])

    return {"created": True, **project}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project (metadata only, files remain)."""
    projects = _load_projects()
    projects = [p for p in projects if p["id"] != project_id]
    _save_projects(projects)
    return {"deleted": True}


# ---------------------------------------------------------------------------
# File tree for a project
# ---------------------------------------------------------------------------

@router.get("/tree/{project_folder:path}")
async def project_file_tree(project_folder: str, max_depth: int = 20):
    """Get the file tree for a project folder."""
    target = _safe(project_folder)
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)
    kb = _get_kb()

    def _tree(p: Path, depth: int = 0):
        if depth > max_depth:
            return None
        name = p.name
        if name.startswith('.') or name in ('node_modules', '__pycache__', '.git', 'venv'):
            return None
        if p.is_file():
            return {"name": name, "type": "file", "path": str(p.relative_to(kb)), "size": p.stat().st_size}
        children = []
        try:
            for item in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                c = _tree(item, depth + 1)
                if c:
                    children.append(c)
        except PermissionError:
            pass
        return {"name": name or project_folder, "type": "directory", "path": str(p.relative_to(kb)), "children": children}

    return _tree(target)


# ---------------------------------------------------------------------------
# File CRUD
# ---------------------------------------------------------------------------

@router.get("/file")
async def read_file(path: str):
    """Read a code file."""
    target = _safe(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        content = target.read_text(errors="ignore")
    except Exception:
        content = target.read_bytes().decode("utf-8", errors="replace")
    ext = target.suffix.lower()
    lang_map = {'.py': 'python', '.js': 'javascript', '.ts': 'typescript', '.jsx': 'jsx',
                '.tsx': 'tsx', '.html': 'html', '.css': 'css', '.json': 'json',
                '.md': 'markdown', '.yaml': 'yaml', '.yml': 'yaml', '.sh': 'bash',
                '.sql': 'sql', '.rs': 'rust', '.go': 'go', '.java': 'java', '.rb': 'ruby'}
    return {
        "path": path, "name": target.name, "content": content,
        "language": lang_map.get(ext, "text"),
        "size": target.stat().st_size,
    }


@router.put("/file")
async def write_file(request: FileWrite):
    """Write/create a code file."""
    target = _safe(request.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(request.content, encoding="utf-8")

    from api._genesis_tracker import track
    track(key_type="code_change", what=f"Code file written: {request.path}",
          file_path=str(target), tags=["codebase", "write"])

    return {"saved": True, "path": request.path, "size": target.stat().st_size}


@router.post("/file/create")
async def create_file(request: FileWrite):
    """Create a new code file."""
    target = _safe(request.path)
    if target.exists():
        raise HTTPException(status_code=409, detail="File already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(request.content, encoding="utf-8")

    from api._genesis_tracker import track
    track(key_type="file_op", what=f"Code file created: {request.path}",
          file_path=str(target), tags=["codebase", "create"])

    kb = _get_kb()
    return {"created": True, "path": str(target.relative_to(kb)), "name": target.name}


@router.delete("/file")
async def delete_file(path: str):
    """Delete a code file."""
    target = _safe(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    target.unlink()

    from api._genesis_tracker import track
    track(key_type="file_op", what=f"Code file deleted: {path}", tags=["codebase", "delete"])

    return {"deleted": True, "path": path}


@router.post("/directory")
async def create_directory(path: str):
    """Create a directory in a project."""
    target = _safe(path)
    target.mkdir(parents=True, exist_ok=True)

    from api._genesis_tracker import track
    track(key_type="file_op", what=f"Directory created: {path}", tags=["codebase", "directory"])

    return {"created": True, "path": path}


# ---------------------------------------------------------------------------
# Coding Agent — AI-driven code generation (like cursor CLI)
# ---------------------------------------------------------------------------

@router.post("/agent/generate")
async def coding_agent_generate(request: CodingAgentRequest):
    """
    Coding agent generates code based on a prompt.
    Understands the project folder context.
    """
    target = _safe(request.project_folder)

    file_list = []
    if target.exists():
        for f in target.rglob("*"):
            if f.is_file() and not any(s in str(f) for s in ['node_modules', '__pycache__', '.git']):
                kb = _get_kb()
                file_list.append(str(f.relative_to(kb)))

    context_parts = [f"Project folder: {request.project_folder}"]
    context_parts.append(f"Files in project ({len(file_list)}):\n" + "\n".join(f"  {f}" for f in file_list[:30]))

    if request.file_context:
        context_parts.append(f"\nCurrent file context:\n{request.file_context[:3000]}")

    system_prompt = (
        "You are Grace's coding agent. You write clean, production-quality code. "
        "When asked to create files, respond with the file path and full content. "
        "Use this format for each file:\n\n"
        "```filepath: path/to/file.ext\n"
        "file content here\n"
        "```\n\n"
        "Always provide complete, working code. Follow best practices for the language."
    )

    full_prompt = "\n\n".join(context_parts) + f"\n\nRequest: {request.prompt}"

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

        from api._genesis_tracker import track
        track(key_type="ai_code_generation", what=f"Coding agent: {request.prompt[:80]}",
              how="POST /api/codebase-hub/agent/generate",
              input_data={"prompt": request.prompt, "folder": request.project_folder},
              tags=["codebase", "agent", provider])

        return {"response": response, "provider": provider, "project_folder": request.project_folder}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/apply")
async def coding_agent_apply(request: FileWrite):
    """Apply coding agent output — write generated code to a file."""
    target = _safe(request.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(request.content, encoding="utf-8")

    from api._genesis_tracker import track
    track(key_type="coding_agent_action", what=f"Agent code applied: {request.path}",
          file_path=str(target), tags=["codebase", "agent", "apply"])

    return {"applied": True, "path": request.path, "size": target.stat().st_size}
