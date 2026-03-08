"""Files domain service — direct file system operations and agentic filing (brain + Qwen/librarian)."""
from pathlib import Path
import os
import json
import shutil
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

def _kb():
    from settings import settings
    return Path(settings.KNOWLEDGE_BASE_PATH)

def _safe(rel):
    kb = _kb()
    target = (kb / rel).resolve()
    if not str(target).startswith(str(kb.resolve())):
        raise ValueError("Path traversal blocked")
    return target

def tree(p=None, max_depth=3):
    kb = _kb()
    root = _safe(p) if p else kb
    root.mkdir(parents=True, exist_ok=True)
    def _b(d, depth=0):
        r = {"path": str(d.relative_to(kb)), "name": d.name or "knowledge_base", "type": "directory", "children": []}
        if depth >= max_depth: return r
        try:
            for item in sorted(d.iterdir()):
                if item.name.startswith("."): continue
                if item.is_dir(): r["children"].append(_b(item, depth+1))
                else: r["children"].append({"path": str(item.relative_to(kb)), "name": item.name, "type": "file", "size": item.stat().st_size})
        except PermissionError: pass
        return r
    return _b(root)

def browse(path=""):
    target = _safe(path) if path else _kb()
    if not target.exists(): return {"error": "Not found"}
    items = []
    for item in sorted(target.iterdir()):
        if item.name.startswith("."): continue
        items.append({"name": item.name, "type": "directory" if item.is_dir() else "file",
                       "path": str(item.relative_to(_kb())), "size": item.stat().st_size if item.is_file() else 0})
    return {"path": path, "items": items, "total": len(items)}

def read(path):
    target = _safe(path)
    if not target.exists(): return {"error": "Not found"}
    try:
        content = target.read_text(errors="ignore")[:50000]
        return {"path": path, "content": content, "size": target.stat().st_size}
    except Exception as e:
        return {"error": str(e)}

def write(path, content):
    target = _safe(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": path, "size": target.stat().st_size, "saved": True}

def create(path, content="", directory=None):
    if directory: path = f"{directory}/{path}"
    target = _safe(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": path, "created": True}

def delete(path):
    target = _safe(path)
    if not target.exists(): return {"error": "Not found"}
    target.unlink()
    return {"path": path, "deleted": True}

def search(query, limit=10):
    """Simple file content search."""
    results = []
    for f in _kb().rglob("*"):
        if f.is_file() and f.suffix in (".txt", ".md", ".py", ".json", ".yaml"):
            try:
                content = f.read_text(errors="ignore")
                if query.lower() in content.lower():
                    results.append({"path": str(f.relative_to(_kb())), "name": f.name})
                    if len(results) >= limit: break
            except Exception: pass
    return {"query": query, "results": results, "total": len(results)}

def stats():
    kb = _kb()
    total_files, total_size, by_ext = 0, 0, {}
    for f in kb.rglob("*"):
        if f.is_file():
            total_files += 1
            total_size += f.stat().st_size
            ext = f.suffix.lower() or "none"
            by_ext[ext] = by_ext.get(ext, 0) + 1
    return {"total_files": total_files, "total_size_mb": round(total_size / 1048576, 2), "by_extension": by_ext}

def docs_all():
    """List all documents from the docs library."""
    try:
        from api.docs_library_api import _list_all_documents
        return _list_all_documents()
    except Exception:
        return {"documents": []}


def _call_brain(brain: str, action: str, payload: dict) -> dict:
    """Call brain from files service (agentic path)."""
    from api.brain_api_v2 import call_brain
    return call_brain(brain, action, payload or {})


def save_file_agentic(p: Dict[str, Any]) -> dict:
    """
    Save file then run librarian process and agentic filing (correct subfolder, categorization).
    Payload: path, content, project_id (optional). Triggers data/librarian_process and files/filing.
    """
    path = p.get("path", "")
    content = p.get("content", "")
    project_id = p.get("project_id", "")
    if not path:
        return {"ok": False, "error": "path required"}
    out = write(path, content)
    if out.get("error"):
        return out
    r1 = _call_brain("data", "librarian_process", {"path": path, "content": content, "project_id": project_id})
    r2 = _call_brain("files", "filing", {"path": path})
    return {
        "path": path,
        "saved": True,
        "size": out.get("size"),
        "librarian": r1.get("data") if r1.get("ok") else None,
        "filing": r2.get("data") if r2.get("ok") else None,
    }


def place_in_folder(p: Dict[str, Any]) -> dict:
    """
    Place file in the correct subfolder (agentic: librarian suggests or use target_folder).
    Payload: path, target_folder (optional; if missing, librarian suggests).
    """
    return _call_brain("data", "librarian_organise_file", {
        "path": p.get("path", ""),
        "target_folder": p.get("target_folder"),
    }).get("data", {})


def create_doc(p: Dict[str, Any]) -> dict:
    """
    Create a document: suggest or use folder, write content, then process and categorize.
    Payload: path (or name), content, folder (optional), project_id (optional).
    """
    path = p.get("path", p.get("name", "untitled.md"))
    content = p.get("content", "")
    folder = p.get("folder", "")
    project_id = p.get("project_id", "")
    if folder:
        path = f"{folder.rstrip('/')}/{path}" if folder else path
    out = create(path, content, directory=None)
    if out.get("error"):
        return out
    r1 = _call_brain("data", "librarian_process", {"path": path, "content": content, "project_id": project_id})
    r2 = _call_brain("files", "filing", {"path": path})
    return {
        "path": path,
        "created": True,
        "librarian": r1.get("data") if r1.get("ok") else None,
        "filing": r2.get("data") if r2.get("ok") else None,
    }


def create_report(p: Dict[str, Any]) -> dict:
    """
    Create a report (e.g. daily summary), place in reports folder, and register with librarian.
    Payload: title, report_type (optional), content (optional); or generate_daily_report if no content.
    """
    from datetime import datetime
    title = p.get("title", "report")
    report_type = p.get("report_type", "daily")
    content = p.get("content")
    if content is None:
        try:
            from core.reports import generate_daily_report
            data = generate_daily_report(p.get("hours", 24))
            content = json.dumps(data, indent=2, default=str)
        except Exception as e:
            content = f'{{ "error": "{e}", "generated_at": "{datetime.utcnow().isoformat()}" }}'
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:80]
    path = f"reports/{report_type}/{safe_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.json"
    out = create(path, content, directory=None)
    if out.get("error"):
        return out
    _call_brain("data", "librarian_process", {"path": path, "content": content, "project_id": "reports"})
    return {"path": path, "created": True, "report_type": report_type}


def categorize(p: Dict[str, Any]) -> dict:
    """Run librarian categorization for a path (tags, category, purpose)."""
    return _call_brain("data", "librarian_categorize", {"path": p.get("path", "")}).get("data", {})


def filing(p: Dict[str, Any]) -> dict:
    """
    Agentic filing: suggest or move file to correct subfolder via librarian (Qwen-backed).
    Payload: path. Calls data/librarian_organise_file.
    """
    return _call_brain("data", "librarian_organise_file", {"path": p.get("path", "")}).get("data", {})
