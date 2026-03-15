"""
Librarian File-System API – real filesystem CRUD for the FoldersTab UI.

All operations are sandboxed to the GRACE_DATA_DIR directory (default: data/).
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging
import os
import shutil
import stat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/librarian-fs", tags=["File Manager"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATA_DIR = Path(os.getenv("GRACE_DATA_DIR", "data")).resolve()


def _safe_path(rel: str) -> Path:
    """Resolve *rel* inside DATA_DIR and ensure it doesn't escape."""
    resolved = (DATA_DIR / rel).resolve()
    if not str(resolved).startswith(str(DATA_DIR)):
        raise HTTPException(status_code=403, detail="Path traversal denied")
    return resolved


def _rel(full: Path) -> str:
    """Return the path relative to DATA_DIR using forward-slashes."""
    return full.relative_to(DATA_DIR).as_posix()


def _entry_info(p: Path) -> Dict[str, Any]:
    """Build an info dict for a single filesystem entry."""
    is_dir = p.is_dir()
    info: Dict[str, Any] = {
        "name": p.name,
        "path": _rel(p),
        "type": "directory" if is_dir else "file",
        "is_dir": is_dir,
    }
    if is_dir:
        try:
            info["file_count"] = sum(1 for _ in p.rglob("*") if _.is_file())
        except PermissionError:
            info["file_count"] = 0
        info["size"] = 0
        info["extension"] = None
    else:
        try:
            info["size"] = p.stat().st_size
        except OSError:
            info["size"] = 0
        info["extension"] = p.suffix.lstrip(".") or None
        info["file_count"] = None
    return info


def _build_tree(root: Path) -> Dict[str, Any]:
    """Recursively build a tree structure for *root*."""
    node: Dict[str, Any] = {
        "name": root.name,
        "path": _rel(root) if root != DATA_DIR else "",
        "type": "directory",
        "children": [],
        "size": 0,
        "file_count": 0,
    }
    try:
        entries = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return node

    for entry in entries:
        if entry.is_dir():
            child = _build_tree(entry)
            node["children"].append(child)
            node["size"] += child["size"]
            node["file_count"] += child["file_count"]
        else:
            try:
                sz = entry.stat().st_size
            except OSError:
                sz = 0
            node["children"].append({
                "name": entry.name,
                "path": _rel(entry),
                "type": "file",
                "children": [],
                "size": sz,
                "file_count": 0,
            })
            node["size"] += sz
            node["file_count"] += 1
    return node


# ---------------------------------------------------------------------------
# Pydantic request bodies
# ---------------------------------------------------------------------------

class FileContentBody(BaseModel):
    path: str
    content: str


class FileCreateBody(BaseModel):
    path: str
    directory: Optional[str] = None
    content: Optional[str] = ""


class DirectoryBody(BaseModel):
    path: str


class RenameBody(BaseModel):
    old_path: str
    new_path: str


class MoveBody(BaseModel):
    source_path: str
    destination_dir: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/tree")
async def get_tree():
    """Full recursive file tree."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _build_tree(DATA_DIR)


@router.get("/browse")
async def browse(path: str = ""):
    """List items in a single directory."""
    target = _safe_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")
    items = [_entry_info(p) for p in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))]
    return {"items": items}


@router.get("/file/content")
async def get_file_content(path: str):
    """Read and return file content."""
    target = _safe_path(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"content": content, "size": target.stat().st_size}


@router.put("/file/content")
async def put_file_content(body: FileContentBody):
    """Overwrite file content."""
    target = _safe_path(body.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_text(body.content, encoding="utf-8")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    st = target.stat()
    return {"path": _rel(target), "size": st.st_size, "modified": st.st_mtime}


@router.post("/file/create")
async def create_file_endpoint(body: FileCreateBody):
    """Create a new file."""
    if body.directory:
        full = _safe_path(str(Path(body.directory) / body.path))
    else:
        full = _safe_path(body.path)
    if full.exists():
        raise HTTPException(status_code=409, detail="File already exists")
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(body.content or "", encoding="utf-8")
    return {"path": _rel(full), "name": full.name, "size": full.stat().st_size}


@router.post("/directory")
async def create_directory(body: DirectoryBody):
    """Create a new directory."""
    target = _safe_path(body.path)
    if target.exists():
        raise HTTPException(status_code=409, detail="Directory already exists")
    target.mkdir(parents=True, exist_ok=True)
    return {"path": _rel(target), "name": target.name}


@router.delete("/file")
async def delete_file(path: str):
    """Delete a single file."""
    target = _safe_path(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(target)
    return {"deleted": _rel(target)}


@router.delete("/directory")
async def delete_directory(path: str, force: bool = False):
    """Delete a directory (force=true for recursive)."""
    target = _safe_path(path)
    if not target.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")
    if force:
        shutil.rmtree(target)
    else:
        try:
            target.rmdir()
        except OSError:
            raise HTTPException(status_code=400, detail="Directory not empty; use force=true")
    return {"deleted": _rel(target)}


@router.post("/file/rename")
async def rename_file(body: RenameBody):
    """Rename / move a file or directory."""
    src = _safe_path(body.old_path)
    dst = _safe_path(body.new_path)
    if not src.exists():
        raise HTTPException(status_code=404, detail="Source not found")
    if dst.exists():
        raise HTTPException(status_code=409, detail="Destination already exists")
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.rename(src, dst)
    return {"old_path": _rel(src), "new_path": _rel(dst)}


@router.post("/file/move")
async def move_file(body: MoveBody):
    """Move a file into a different directory."""
    src = _safe_path(body.source_path)
    dst_dir = _safe_path(body.destination_dir)
    if not src.exists():
        raise HTTPException(status_code=404, detail="Source not found")
    dst_dir.mkdir(parents=True, exist_ok=True)
    result = shutil.move(str(src), str(dst_dir / src.name))
    return {"source": _rel(src), "destination": _rel(Path(result).resolve())}


@router.post("/file/upload")
async def upload_file(
    file: UploadFile = File(...),
    directory: str = Form(""),
):
    """Upload a file into the given directory."""
    dst_dir = _safe_path(directory)
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = dst_dir / file.filename
    # Validate final path
    if not str(target.resolve()).startswith(str(DATA_DIR)):
        raise HTTPException(status_code=403, detail="Path traversal denied")
    with open(target, "wb") as f:
        while chunk := await file.read(1024 * 256):
            f.write(chunk)
    return {"path": _rel(target), "name": file.filename, "size": target.stat().st_size}


@router.get("/stats")
async def get_stats():
    """Aggregate stats for the data directory."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    total_files = 0
    total_dirs = 0
    total_size = 0
    for root, dirs, files in os.walk(DATA_DIR):
        total_dirs += len(dirs)
        for fname in files:
            total_files += 1
            try:
                total_size += os.path.getsize(os.path.join(root, fname))
            except OSError:
                pass
    return {
        "total_files": total_files,
        "total_dirs": total_dirs,
        "total_size_bytes": total_size,
    }


@router.get("/search")
async def search_files(q: str = Query("", min_length=1)):
    """Search for files whose name contains the query string."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    q_lower = q.lower()
    results: List[Dict[str, Any]] = []
    for root, _dirs, files in os.walk(DATA_DIR):
        for fname in files:
            if q_lower in fname.lower():
                p = Path(root) / fname
                results.append(_entry_info(p))
                if len(results) >= 200:
                    return {"results": results, "truncated": True}
    return {"results": results, "truncated": False}
