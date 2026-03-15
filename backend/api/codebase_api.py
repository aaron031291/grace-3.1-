"""
Codebase API — wired to real file system + Genesis tracking + Spindle.

Provides actual file browsing, code search, and git commit history
for the Ops Console and frontend. All actions tracked via governance.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/codebase", tags=["Codebase"])

# Grace project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _emit(topic: str, data: dict):
    try:
        from cognitive.event_bus import publish_async
        publish_async(topic, data, source="codebase_api")
    except Exception:
        pass


def _track(what: str, tags: list = None):
    try:
        from api._genesis_tracker import track
        track(key_type="api_request", what=what, who="codebase_api",
              tags=["codebase", "api"] + (tags or []))
    except Exception:
        pass


def _safe_path(user_path: str) -> Path:
    """Resolve path safely within project root to prevent directory traversal."""
    resolved = (_PROJECT_ROOT / user_path).resolve()
    if not str(resolved).startswith(str(_PROJECT_ROOT)):
        raise HTTPException(403, "Path outside project root")
    return resolved


@router.get("/repositories")
async def list_repositories():
    """List project directories as 'repositories'."""
    _track("GET /codebase/repositories")
    repos = []
    try:
        for d in _PROJECT_ROOT.iterdir():
            if d.is_dir() and not d.name.startswith('.') and d.name not in ('node_modules', '__pycache__', '.git'):
                py_count = len(list(d.rglob("*.py")))
                repos.append({
                    "id": d.name, "name": d.name,
                    "path": str(d.relative_to(_PROJECT_ROOT)),
                    "files": py_count,
                })
    except Exception as e:
        logger.warning(f"[CODEBASE-API] list repos: {e}")
    return {"repositories": repos}


@router.get("/repositories/{rep_id}")
async def get_repository_info(rep_id: str):
    try:
        path = _safe_path(rep_id)
        if not path.is_dir():
            return {"repository": {"id": rep_id, "exists": False}}
        
        py_files = list(path.rglob("*.py"))
        return {"repository": {
            "id": rep_id, "name": rep_id, "path": str(path),
            "file_count": len(py_files), "exists": True,
        }}
    except HTTPException:
        raise
    except Exception as e:
        return {"repository": {"id": rep_id}, "error": str(e)[:200]}


@router.post("/repositories")
async def add_repository(payload: Dict[str, Any]):
    _track("POST /codebase/repositories", tags=["add_repo"])
    _emit("codebase.repository_added", payload)
    return {"status": "ok", "message": "Repository registered"}


@router.get("/search")
async def search_code(query: str = "", path: str = "backend", max_results: int = 20):
    """Search code across the codebase — real grep-like search."""
    _track(f"GET /codebase/search?q={query[:30]}", tags=["search"])
    if not query:
        return {"results": [], "query": query}
    
    results = []
    try:
        search_root = _safe_path(path)
        for py_file in search_root.rglob("*.py"):
            if len(results) >= max_results:
                break
            try:
                content = py_file.read_text(errors="ignore")
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if query.lower() in line.lower():
                        results.append({
                            "file": str(py_file.relative_to(_PROJECT_ROOT)),
                            "line": i + 1,
                            "content": line.strip()[:200],
                        })
                        if len(results) >= max_results:
                            break
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"[CODEBASE-API] search error: {e}")
    
    _emit("codebase.search", {"query": query[:50], "results": len(results)})
    return {"results": results, "query": query, "total": len(results)}


@router.get("/analysis")
async def analyze_codebase():
    """Quick codebase metrics — real file counts."""
    _track("GET /codebase/analysis")
    try:
        backend = _PROJECT_ROOT / "backend"
        metrics = {
            "total_py_files": len(list(backend.rglob("*.py"))) if backend.exists() else 0,
            "api_modules": len(list((backend / "api").glob("*.py"))) if (backend / "api").exists() else 0,
            "cognitive_modules": len(list((backend / "cognitive").glob("*.py"))) if (backend / "cognitive").exists() else 0,
            "core_modules": len(list((backend / "core").glob("*.py"))) if (backend / "core").exists() else 0,
            "test_files": len(list(backend.rglob("test_*.py"))) if backend.exists() else 0,
        }
        total_lines = 0
        for py in list(backend.rglob("*.py"))[:500]:
            try:
                total_lines += len(py.read_text(errors="ignore").split("\n"))
            except Exception:
                pass
        metrics["total_lines"] = total_lines
        return {"status": "ok", "metrics": metrics}
    except Exception as e:
        return {"status": "ok", "metrics": {}, "error": str(e)[:200]}


@router.get("/analysis/metrics")
async def get_code_metrics():
    result = await analyze_codebase()
    return {"metrics": result.get("metrics", {})}


@router.get("/files")
async def list_files(path: str = "/"):
    """List actual files in a directory."""
    try:
        target = _safe_path(path.lstrip("/") or ".")
        if not target.exists():
            return {"files": [], "path": path}
        
        files = []
        for item in sorted(target.iterdir()):
            if item.name.startswith('.') or item.name in ('__pycache__', 'node_modules'):
                continue
            files.append({
                "name": item.name,
                "path": str(item.relative_to(_PROJECT_ROOT)),
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else 0,
            })
        return {"files": files, "path": path}
    except HTTPException:
        raise
    except Exception as e:
        return {"files": [], "path": path, "error": str(e)[:200]}


@router.get("/file")
async def get_file(path: str = "", start_line: int = None, end_line: int = None):
    """Read actual file content with optional line range."""
    if not path:
        raise HTTPException(400, "path required")
    
    try:
        filepath = _safe_path(path)
        if not filepath.is_file():
            raise HTTPException(404, f"File not found: {path}")
        
        content = filepath.read_text(errors="ignore")
        lines = content.split("\n")
        
        if start_line is not None and end_line is not None:
            selected = lines[max(0, start_line-1):end_line]
            return {"path": path, "content": "\n".join(selected),
                    "start_line": start_line, "end_line": end_line,
                    "total_lines": len(lines)}
        
        # Truncate very large files
        if len(content) > 100000:
            content = content[:100000] + "\n... [truncated]"
        
        return {"path": path, "content": content, "total_lines": len(lines)}
    except HTTPException:
        raise
    except Exception as e:
        return {"path": path, "content": "", "error": str(e)[:200]}


@router.get("/commits")
async def get_commits(limit: int = 50):
    """Get real git commits if git is available."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "log", f"--max-count={limit}", "--format=%H|%s|%an|%ai"],
            cwd=str(_PROJECT_ROOT), capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return {"commits": [], "note": "git not available"}
        
        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 3)
            if len(parts) >= 4:
                commits.append({
                    "hash": parts[0][:8], "message": parts[1],
                    "author": parts[2], "date": parts[3],
                })
        return {"commits": commits}
    except Exception as e:
        return {"commits": [], "error": str(e)[:200]}


@router.post("/analysis/file")
async def analyze_file(payload: Dict[str, Any]):
    """Analyze a specific file — dispatches through brain with governance."""
    _track("POST /codebase/analysis/file", tags=["analyze"])
    file_path = payload.get("file_path", "") or payload.get("path", "")
    try:
        from api.brain_api_v2 import call_brain
        result = call_brain("code", "analyze", {"file_path": file_path})
        return {"status": "ok", **result}
    except Exception as e:
        # Fallback: basic static analysis
        try:
            fp = _safe_path(file_path)
            if fp.exists():
                content = fp.read_text(errors="ignore")
                import ast
                tree = ast.parse(content)
                classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                return {"status": "ok", "file": file_path,
                        "classes": classes, "functions": functions,
                        "lines": len(content.split("\n"))}
        except Exception:
            pass
        return {"status": "error", "error": str(e)[:200]}
