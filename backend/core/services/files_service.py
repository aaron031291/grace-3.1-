"""Files domain service — direct file system operations."""
from pathlib import Path
import os, json, shutil, logging

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
