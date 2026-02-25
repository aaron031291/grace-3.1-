"""
Librarian Autonomous File Management API

Provides autonomous file organization capabilities:
- Auto-create directory structures based on content analysis
- Move/organize files into appropriate categories
- Full CRUD operations on the knowledge base
- Kimi 2.5 integration for document reasoning
- Rename, move, categorize files with AI assistance
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import shutil
import json
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/librarian-fs", tags=["Librarian File System"])


class DirectoryCreateRequest(BaseModel):
    path: str
    auto_organize: bool = False


class FileRenameRequest(BaseModel):
    old_path: str
    new_path: str


class FileMoveRequest(BaseModel):
    source_path: str
    destination_dir: str


class AutoOrganizeRequest(BaseModel):
    path: Optional[str] = ""
    use_kimi: bool = False
    dry_run: bool = True


class FileSaveRequest(BaseModel):
    path: str
    content: str


class FileCreateRequest(BaseModel):
    path: str
    content: str = ""
    directory: str = ""


class FileAnalyzeRequest(BaseModel):
    file_path: str
    use_kimi: bool = False


class DirectoryStructureResponse(BaseModel):
    path: str
    name: str
    type: str  # "file" or "directory"
    size: Optional[int] = None
    modified: Optional[str] = None
    children: Optional[List[Any]] = None
    file_count: Optional[int] = None


def _get_kb_path() -> Path:
    from settings import settings
    return Path(settings.KNOWLEDGE_BASE_PATH)


def _resolve_safe_path(relative_path: str) -> Path:
    """Resolve a path ensuring it stays within the knowledge base."""
    kb = _get_kb_path()
    target = (kb / relative_path).resolve()
    if not str(target).startswith(str(kb.resolve())):
        raise HTTPException(status_code=400, detail="Path must be within knowledge base")
    return target


def _read_file_preview(file_path: Path, max_chars: int = 3000) -> str:
    """Read a preview of file content for analysis."""
    try:
        if file_path.suffix.lower() in ['.txt', '.md', '.py', '.js', '.json', '.csv', '.html', '.xml', '.yml', '.yaml', '.toml', '.cfg', '.ini', '.log', '.rst']:
            with open(file_path, 'r', errors='ignore') as f:
                return f.read(max_chars)
        return f"[Binary file: {file_path.suffix}, size: {file_path.stat().st_size} bytes]"
    except Exception:
        return "[Unable to read file]"


def _build_tree(dir_path: Path, kb_root: Path, depth: int = 0, max_depth: int = 50) -> Dict[str, Any]:
    """Build directory tree structure."""
    rel = str(dir_path.relative_to(kb_root))
    if rel == ".":
        rel = ""

    result = {
        "path": rel,
        "name": dir_path.name or "knowledge_base",
        "type": "directory",
        "children": [],
        "file_count": 0,
    }

    if depth >= max_depth:
        return result

    try:
        items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        for item in items:
            if item.name.startswith('.'):
                continue
            if item.is_dir():
                child = _build_tree(item, kb_root, depth + 1, max_depth)
                result["children"].append(child)
                result["file_count"] += child.get("file_count", 0)
            else:
                stat = item.stat()
                result["children"].append({
                    "path": str(item.relative_to(kb_root)),
                    "name": item.name,
                    "type": "file",
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
                result["file_count"] += 1
    except PermissionError:
        pass

    return result


@router.get("/tree")
async def get_directory_tree(max_depth: int = 50):
    """Get the full knowledge base directory tree."""
    kb = _get_kb_path()
    if not kb.exists():
        kb.mkdir(parents=True, exist_ok=True)
    return _build_tree(kb, kb, max_depth=max_depth)


@router.get("/browse")
async def browse_directory(path: str = ""):
    """Browse a specific directory in the knowledge base."""
    target = _resolve_safe_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    kb = _get_kb_path()
    items = []
    for item in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if item.name.startswith('.'):
            continue
        rel = str(item.relative_to(kb))
        if item.is_dir():
            file_count = sum(1 for _ in item.rglob('*') if _.is_file() and not _.name.startswith('.'))
            items.append({
                "path": rel,
                "name": item.name,
                "type": "directory",
                "file_count": file_count,
            })
        else:
            stat = item.stat()
            items.append({
                "path": rel,
                "name": item.name,
                "type": "file",
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": item.suffix.lower(),
            })

    return {
        "current_path": path,
        "parent_path": str(Path(path).parent) if path else None,
        "items": items,
        "total_items": len(items),
    }


@router.post("/directory")
async def create_directory(request: DirectoryCreateRequest):
    """Create a new directory (or nested directory structure)."""
    target = _resolve_safe_path(request.path)
    try:
        target.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {target}")
        return {"created": True, "path": request.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create directory: {e}")


@router.delete("/directory")
async def delete_directory(path: str, force: bool = False):
    """Delete a directory. Use force=True to delete non-empty directories."""
    target = _resolve_safe_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    try:
        if force:
            shutil.rmtree(target)
        else:
            if any(target.iterdir()):
                raise HTTPException(status_code=400, detail="Directory not empty. Use force=true to delete.")
            target.rmdir()
        return {"deleted": True, "path": path}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {e}")


@router.post("/file/upload")
async def upload_file(
    file: UploadFile = File(...),
    directory: str = Form(""),
    auto_ingest: bool = Form(True),
):
    """Upload a file to a specific directory and optionally ingest it."""
    target_dir = _resolve_safe_path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / file.filename
    try:
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)

        result = {
            "uploaded": True,
            "path": str(file_path.relative_to(_get_kb_path())),
            "size": len(content),
            "name": file.filename,
        }

        try:
            import hashlib as _hl
            from api.docs_library_api import register_document
            _hash = _hl.sha256(content).hexdigest()
            doc_id = register_document(
                filename=file.filename,
                file_path=str(file_path),
                file_size=len(content),
                source="knowledge_base",
                upload_method="librarian_upload",
                directory=directory,
                content_hash=_hash,
            )
            result["library_doc_id"] = doc_id
        except Exception as _reg_err:
            logger.warning(f"Docs library registration skipped: {_reg_err}")

        if auto_ingest:
            try:
                from ingestion.service import TextIngestionService
                from embedding.embedder import get_embedding_model
                from vector_db.client import get_qdrant_client
                embedding_model = get_embedding_model()
                qdrant = get_qdrant_client()
                service = TextIngestionService(embedding_model, qdrant)
                text = _read_file_preview(file_path, max_chars=100000)
                if text and not text.startswith("[Binary"):
                    ingest_result = service.ingest_text(
                        text=text,
                        source=file.filename,
                        metadata={"file_path": str(file_path), "directory": directory}
                    )
                    result["ingested"] = True
                    result["document_id"] = getattr(ingest_result, 'document_id', None)
            except Exception as e:
                result["ingested"] = False
                result["ingest_error"] = str(e)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.delete("/file")
async def delete_file(path: str):
    """Delete a file from the knowledge base."""
    target = _resolve_safe_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not target.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    try:
        target.unlink()
        return {"deleted": True, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")


@router.post("/file/rename")
async def rename_file(request: FileRenameRequest):
    """Rename a file or directory."""
    source = _resolve_safe_path(request.old_path)
    dest = _resolve_safe_path(request.new_path)

    if not source.exists():
        raise HTTPException(status_code=404, detail="Source not found")
    if dest.exists():
        raise HTTPException(status_code=409, detail="Destination already exists")

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        source.rename(dest)
        return {"renamed": True, "old_path": request.old_path, "new_path": request.new_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rename failed: {e}")


@router.post("/file/move")
async def move_file(request: FileMoveRequest):
    """Move a file to a different directory."""
    source = _resolve_safe_path(request.source_path)
    dest_dir = _resolve_safe_path(request.destination_dir)

    if not source.exists():
        raise HTTPException(status_code=404, detail="Source file not found")

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / source.name

    try:
        shutil.move(str(source), str(dest))
        kb = _get_kb_path()
        return {
            "moved": True,
            "old_path": request.source_path,
            "new_path": str(dest.relative_to(kb)),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Move failed: {e}")


@router.get("/file/content")
async def get_file_content(path: str, max_chars: int = 50000):
    """Read file content (text files only)."""
    target = _resolve_safe_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not target.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    content = _read_file_preview(target, max_chars=max_chars)
    stat = target.stat()

    return {
        "path": path,
        "name": target.name,
        "content": content,
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "extension": target.suffix.lower(),
    }


@router.put("/file/content")
async def save_file_content(request: FileSaveRequest):
    """Save (overwrite) file content. Used by the inline document editor."""
    target = _resolve_safe_path(request.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not target.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    try:
        target.write_text(request.content, encoding="utf-8")
        stat = target.stat()
        return {
            "saved": True,
            "path": request.path,
            "name": target.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save failed: {e}")


@router.post("/file/create")
async def create_new_file(request: FileCreateRequest):
    """Create a new file with optional initial content."""
    file_path = request.path
    if request.directory:
        file_path = f"{request.directory}/{request.path}" if request.directory else request.path

    target = _resolve_safe_path(file_path)
    if target.exists():
        raise HTTPException(status_code=409, detail="File already exists")

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(request.content, encoding="utf-8")
        kb = _get_kb_path()
        stat = target.stat()
        return {
            "created": True,
            "path": str(target.relative_to(kb)),
            "name": target.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Create failed: {e}")


@router.post("/analyze")
async def analyze_file(request: FileAnalyzeRequest):
    """
    Analyze a file using AI to determine its category, topics, and
    suggested organization. Optionally uses Kimi 2.5 for deeper reasoning.
    """
    target = _resolve_safe_path(request.file_path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    content = _read_file_preview(target, max_chars=5000)

    try:
        if request.use_kimi:
            from llm_orchestrator.factory import get_kimi_client
            client = get_kimi_client()
        else:
            from llm_orchestrator.factory import get_llm_client
            client = get_llm_client()

        prompt = (
            f"Analyze this file and provide a JSON response with:\n"
            f"- category: the broad category (e.g., 'documentation', 'code', 'data', 'report', 'research')\n"
            f"- topics: list of topics covered\n"
            f"- suggested_directory: where this should be organized in a knowledge base\n"
            f"- summary: brief 1-2 sentence summary\n"
            f"- tags: list of relevant tags\n\n"
            f"File: {target.name}\n"
            f"Content preview:\n{content}\n\n"
            f"Respond ONLY with valid JSON."
        )

        response = client.generate(prompt=prompt, temperature=0.3, max_tokens=1024)

        try:
            analysis = json.loads(response.strip().strip('```json').strip('```'))
        except json.JSONDecodeError:
            analysis = {
                "category": "uncategorized",
                "topics": [],
                "suggested_directory": "",
                "summary": response[:200],
                "tags": [],
                "raw_response": response,
            }

        analysis["file_path"] = request.file_path
        analysis["file_name"] = target.name
        analysis["provider"] = "kimi" if request.use_kimi else "default"

        return analysis
    except Exception as e:
        logger.error(f"File analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/auto-organize")
async def auto_organize(request: AutoOrganizeRequest):
    """
    Autonomously organize files in the knowledge base.
    The librarian analyzes unorganized files and creates appropriate
    directory structures, then moves files to their correct locations.
    """
    kb = _get_kb_path()
    target = _resolve_safe_path(request.path) if request.path else kb

    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    files_to_organize = []
    for item in target.iterdir():
        if item.is_file() and not item.name.startswith('.'):
            files_to_organize.append(item)

    if not files_to_organize:
        return {"message": "No files to organize", "actions": []}

    actions = []

    for file_path in files_to_organize[:20]:
        content = _read_file_preview(file_path, max_chars=2000)
        ext = file_path.suffix.lower()

        suggested_dir = _suggest_directory(file_path.name, content, ext)

        if suggested_dir:
            dest_path = kb / suggested_dir
            actions.append({
                "action": "move",
                "source": str(file_path.relative_to(kb)),
                "destination": suggested_dir,
                "file_name": file_path.name,
                "reason": f"File type '{ext}' and content suggest '{suggested_dir}'",
            })

            if not request.dry_run:
                try:
                    dest_path.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(dest_path / file_path.name))
                    actions[-1]["executed"] = True
                except Exception as e:
                    actions[-1]["executed"] = False
                    actions[-1]["error"] = str(e)

    return {
        "dry_run": request.dry_run,
        "files_analyzed": len(files_to_organize),
        "actions_proposed": len(actions),
        "actions": actions,
    }


def _suggest_directory(filename: str, content: str, extension: str) -> Optional[str]:
    """Suggest a directory based on file characteristics."""
    ext_map = {
        '.py': 'code/python',
        '.js': 'code/javascript',
        '.ts': 'code/typescript',
        '.jsx': 'code/react',
        '.tsx': 'code/react',
        '.css': 'code/styles',
        '.html': 'code/web',
        '.md': 'documentation',
        '.rst': 'documentation',
        '.txt': 'documents',
        '.pdf': 'documents/pdf',
        '.csv': 'data/csv',
        '.json': 'data/json',
        '.xml': 'data/xml',
        '.yml': 'configuration',
        '.yaml': 'configuration',
        '.toml': 'configuration',
        '.ini': 'configuration',
        '.cfg': 'configuration',
        '.log': 'logs',
        '.png': 'media/images',
        '.jpg': 'media/images',
        '.jpeg': 'media/images',
        '.gif': 'media/images',
        '.svg': 'media/images',
        '.mp3': 'media/audio',
        '.wav': 'media/audio',
        '.mp4': 'media/video',
    }

    name_lower = filename.lower()
    if 'readme' in name_lower:
        return 'documentation'
    if 'report' in name_lower:
        return 'reports'
    if 'test' in name_lower:
        return 'tests'
    if 'config' in name_lower or 'settings' in name_lower:
        return 'configuration'

    return ext_map.get(extension)


@router.get("/stats")
async def get_knowledge_base_stats():
    """Get detailed statistics about the knowledge base."""
    kb = _get_kb_path()
    if not kb.exists():
        return {"exists": False}

    total_files = 0
    total_dirs = 0
    total_size = 0
    file_types = {}
    top_dirs = {}

    for root, dirs, files in os.walk(kb):
        rel_root = str(Path(root).relative_to(kb))
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        total_dirs += len(dirs)
        for f in files:
            if f.startswith('.'):
                continue
            total_files += 1
            fpath = os.path.join(root, f)
            try:
                total_size += os.path.getsize(fpath)
            except OSError:
                pass
            ext = os.path.splitext(f)[1].lower() or '(none)'
            file_types[ext] = file_types.get(ext, 0) + 1
            top_dir = rel_root.split(os.sep)[0] if rel_root != '.' else '(root)'
            top_dirs[top_dir] = top_dirs.get(top_dir, 0) + 1

    return {
        "exists": True,
        "total_files": total_files,
        "total_directories": total_dirs,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "file_types": dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True)),
        "top_level_distribution": dict(sorted(top_dirs.items(), key=lambda x: x[1], reverse=True)),
    }
