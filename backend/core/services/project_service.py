"""Project management service — visual cards, scoped context, mirroring."""

import json
import os
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

PROJECTS_DIR = Path(__file__).parent.parent.parent / "data" / "projects"


def _ensure():
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def _meta_path():
    return PROJECTS_DIR / "projects.json"


def _load_projects() -> list:
    _ensure()
    p = _meta_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return []


def _save_projects(data: list):
    _ensure()
    _meta_path().write_text(json.dumps(data, indent=2, default=str))


def list_projects() -> dict:
    """List all projects as visual cards."""
    projects = _load_projects()
    for p in projects:
        folder = PROJECTS_DIR / p.get("id", "")
        if folder.exists():
            p["file_count"] = sum(1 for _ in folder.rglob("*") if _.is_file())
            p["size_kb"] = round(sum(f.stat().st_size for f in folder.rglob("*") if f.is_file()) / 1024, 1)
        else:
            p["file_count"] = 0
            p["size_kb"] = 0
    return {"projects": projects, "total": len(projects)}


def create_project(name: str, description: str = "", project_type: str = "fullstack") -> dict:
    """Create a new project with standard folder structure."""
    import uuid
    _ensure()
    projects = _load_projects()

    project_id = name.lower().replace(" ", "-").replace(".", "-")[:30]
    project_dir = PROJECTS_DIR / project_id

    if project_dir.exists():
        return {"error": f"Project {project_id} already exists"}

    project_dir.mkdir(parents=True)
    (project_dir / "frontend").mkdir()
    (project_dir / "backend").mkdir()
    (project_dir / "docs").mkdir()
    (project_dir / "tests").mkdir()

    project = {
        "id": project_id,
        "name": name,
        "description": description,
        "type": project_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "language": "python",
        "status": "active",
    }
    projects.append(project)
    _save_projects(projects)

    try:
        from api._genesis_tracker import track
        track(key_type="system_event", what=f"Project created: {name}",
              who="project_service", tags=["project", "created", project_id])
    except Exception:
        pass

    return project


def get_project(project_id: str) -> dict:
    """Get project details + file tree."""
    projects = _load_projects()
    project = next((p for p in projects if p["id"] == project_id), None)
    if not project:
        return {"error": "Project not found"}

    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return {"error": "Project directory not found"}

    def _tree(path, depth=0, max_depth=3):
        if depth >= max_depth:
            return {"name": path.name, "type": "directory", "children": []}
        children = []
        try:
            for item in sorted(path.iterdir()):
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    children.append(_tree(item, depth + 1, max_depth))
                else:
                    children.append({
                        "name": item.name,
                        "type": "file",
                        "path": str(item.relative_to(PROJECTS_DIR)),
                        "size": item.stat().st_size,
                    })
        except PermissionError:
            pass
        return {"name": path.name, "type": "directory", "children": children}

    project["tree"] = _tree(project_dir)
    return project


def get_project_context(project_id: str, max_chars: int = 10000) -> str:
    """Get project context for scoped LLM chat — file summaries."""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return ""

    context_parts = [f"Project: {project_id}"]
    total_chars = 0

    for f in project_dir.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".js", ".ts", ".jsx", ".tsx", ".md", ".json", ".yaml", ".yml", ".txt"):
            try:
                content = f.read_text(errors="ignore")
                rel = str(f.relative_to(project_dir))
                snippet = content[:500]
                part = f"\n--- {rel} ---\n{snippet}"
                if total_chars + len(part) > max_chars:
                    break
                context_parts.append(part)
                total_chars += len(part)
            except Exception:
                pass

    return "\n".join(context_parts)


def write_project_file(project_id: str, file_path: str, content: str) -> dict:
    """Write a file inside a project."""
    target = PROJECTS_DIR / project_id / file_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    try:
        from api._genesis_tracker import track
        track(key_type="code_change", what=f"Project file written: {project_id}/{file_path}",
              who="project_service", file_path=file_path,
              tags=["project", project_id, "file_write"])
    except Exception:
        pass

    return {"saved": True, "path": f"{project_id}/{file_path}"}


def read_project_file(project_id: str, file_path: str) -> dict:
    """Read a file from a project."""
    target = PROJECTS_DIR / project_id / file_path
    if not target.exists():
        return {"error": "File not found"}
    return {"content": target.read_text(errors="ignore"), "path": f"{project_id}/{file_path}",
            "size": target.stat().st_size}
