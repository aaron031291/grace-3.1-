"""
Docs Library API - Central document library managed by the Librarian

Every file uploaded anywhere in the system (Folders, ingestion, API)
gets registered here. The Librarian keeps this library organised.

Two views:
  1. All Documents — flat column list of every document
  2. Folder View  — documents grouped by the folder/domain they belong to
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import hashlib
import json
import logging
import os
import shutil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/docs", tags=["Docs Library"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db():
    """Get a database session."""
    from database.session import SessionLocal
    if SessionLocal is None:
        from database.session import initialize_session_factory
        initialize_session_factory()
        from database.session import SessionLocal as SL
        return SL()
    return SessionLocal()


def _get_kb_path() -> Path:
    from settings import settings
    return Path(settings.KNOWLEDGE_BASE_PATH)


def _safe_json_parse(text: Optional[str], default=None):
    if not text:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def _doc_to_dict(doc) -> Dict[str, Any]:
    """Convert a Document ORM object to a serialisable dict."""
    tags = _safe_json_parse(doc.tags, [])
    meta = _safe_json_parse(doc.document_metadata, {})
    file_path = doc.file_path or meta.get("user_metadata", {}).get("file_path", "")

    folder = ""
    if file_path:
        parts = Path(file_path).parts
        kb = _get_kb_path()
        try:
            rel = Path(file_path).relative_to(kb)
            folder = str(rel.parent) if str(rel.parent) != "." else ""
        except (ValueError, TypeError):
            folder = str(Path(file_path).parent) if len(parts) > 1 else ""

    return {
        "id": doc.id,
        "filename": doc.original_filename or doc.filename,
        "stored_filename": doc.filename,
        "file_path": file_path,
        "folder": folder,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "source": doc.source,
        "status": doc.status,
        "upload_method": doc.upload_method,
        "total_chunks": doc.total_chunks,
        "tags": tags,
        "description": doc.description,
        "confidence_score": doc.confidence_score,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


def _file_extension(name: str) -> str:
    return Path(name).suffix.lower() if name else ""


# ---------------------------------------------------------------------------
# Registration helper — called by every upload path
# ---------------------------------------------------------------------------

def register_document(
    filename: str,
    file_path: str,
    file_size: int = 0,
    source: str = "upload",
    upload_method: str = "librarian",
    mime_type: str = None,
    directory: str = "",
    description: str = "",
    tags: list = None,
    content_hash: str = None,
) -> int:
    """
    Register a document in the library.  Called by any upload endpoint so
    every file ends up in the docs library regardless of where it was uploaded.
    Returns the document id.
    """
    from models.database_models import Document
    db = _get_db()
    try:
        if content_hash:
            existing = db.query(Document).filter(Document.content_hash == content_hash).first()
            if existing:
                return existing.id

        doc = Document(
            filename=filename,
            original_filename=filename,
            file_path=file_path,
            file_size=file_size,
            source=source,
            upload_method=upload_method,
            mime_type=mime_type or _guess_mime(filename),
            status="completed",
            content_hash=content_hash or "",
            tags=json.dumps(tags or []),
            description=description,
            document_metadata=json.dumps({
                "directory": directory,
                "registered_at": datetime.utcnow().isoformat(),
            }),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        logger.info(f"Docs library: registered '{filename}' (id={doc.id}) in folder '{directory}'")
        return doc.id
    except Exception as e:
        db.rollback()
        logger.error(f"Docs library registration failed: {e}")
        raise
    finally:
        db.close()


def _guess_mime(filename: str) -> str:
    ext_map = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".csv": "text/csv",
        ".json": "application/json",
        ".xml": "application/xml",
        ".html": "text/html",
        ".py": "text/x-python",
        ".js": "text/javascript",
        ".yaml": "text/yaml",
        ".yml": "text/yaml",
    }
    ext = _file_extension(filename)
    return ext_map.get(ext, "application/octet-stream")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/all")
async def get_all_documents(
    status: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = Query("newest", pattern="^(newest|oldest|name|size)$"),
    limit: int = 200,
    offset: int = 0,
):
    """
    View 1 — All Documents in a flat column list.
    Supports filtering by status, source, and text search on filename.
    """
    from models.database_models import Document
    db = _get_db()
    try:
        q = db.query(Document)

        if status:
            q = q.filter(Document.status == status)
        if source:
            q = q.filter(Document.source == source)
        if search:
            q = q.filter(Document.filename.ilike(f"%{search}%"))

        total = q.count()

        if sort == "newest":
            q = q.order_by(Document.created_at.desc())
        elif sort == "oldest":
            q = q.order_by(Document.created_at.asc())
        elif sort == "name":
            q = q.order_by(Document.filename.asc())
        elif sort == "size":
            q = q.order_by(Document.file_size.desc())

        docs = q.offset(offset).limit(limit).all()

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "documents": [_doc_to_dict(d) for d in docs],
        }
    finally:
        db.close()


@router.get("/by-folder")
async def get_documents_by_folder():
    """
    View 2 — Documents grouped by the folder/domain they belong to.
    Returns a tree where each folder contains its documents.
    """
    from models.database_models import Document
    db = _get_db()
    try:
        docs = db.query(Document).order_by(Document.created_at.desc()).all()

        folders: Dict[str, list] = {}
        for doc in docs:
            d = _doc_to_dict(doc)
            folder = d["folder"] or "(root)"
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(d)

        folder_list = []
        for folder_name in sorted(folders.keys()):
            items = folders[folder_name]
            total_size = sum(d.get("file_size") or 0 for d in items)
            folder_list.append({
                "folder": folder_name,
                "document_count": len(items),
                "total_size": total_size,
                "documents": items,
            })

        return {
            "total_documents": len(docs),
            "total_folders": len(folder_list),
            "folders": folder_list,
        }
    finally:
        db.close()


@router.get("/folder/{folder_path:path}")
async def get_folder_documents(folder_path: str):
    """Get all documents within a specific folder/domain."""
    from models.database_models import Document
    db = _get_db()
    try:
        docs = db.query(Document).order_by(Document.created_at.desc()).all()

        results = []
        for doc in docs:
            d = _doc_to_dict(doc)
            if d["folder"] == folder_path or d["folder"].startswith(folder_path + "/"):
                results.append(d)

        return {
            "folder": folder_path,
            "total": len(results),
            "documents": results,
        }
    finally:
        db.close()


@router.get("/document/{doc_id}")
async def get_document_detail(doc_id: int):
    """Get full detail for a single document including chunk info."""
    from models.database_models import Document
    db = _get_db()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        result = _doc_to_dict(doc)
        result["chunks"] = [
            {
                "index": c.chunk_index,
                "text": c.text_content[:500] if c.text_content else "",
                "token_count": c.token_count,
            }
            for c in sorted(doc.chunks, key=lambda x: x.chunk_index)[:50]
        ]
        result["total_chunk_count"] = len(doc.chunks)

        if doc.file_path and os.path.exists(doc.file_path):
            result["file_exists_on_disk"] = True
        else:
            kb = _get_kb_path()
            disk_path = kb / (doc.file_path or doc.filename)
            result["file_exists_on_disk"] = disk_path.exists()

        return result
    finally:
        db.close()


@router.delete("/document/{doc_id}")
async def delete_document(doc_id: int, delete_file: bool = False):
    """Delete a document from the library. Optionally remove the file from disk."""
    from models.database_models import Document
    db = _get_db()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        file_deleted = False
        if delete_file and doc.file_path:
            fp = Path(doc.file_path)
            if not fp.is_absolute():
                fp = _get_kb_path() / fp
            if fp.exists():
                fp.unlink()
                file_deleted = True

        db.delete(doc)
        db.commit()
        return {"deleted": True, "id": doc_id, "file_removed": file_deleted}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/upload")
async def upload_to_library(
    file: UploadFile = File(...),
    folder: str = Form(""),
    description: str = Form(""),
    tags: str = Form(""),
):
    """
    Upload a document directly to the docs library.
    The file is saved into the knowledge base under the given folder
    and registered in the library.
    """
    kb = _get_kb_path()
    target_dir = kb / folder if folder else kb
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / file.filename
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        content_hash = hashlib.sha256(content).hexdigest()
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        doc_id = register_document(
            filename=file.filename,
            file_path=str(file_path),
            file_size=len(content),
            source="docs_library",
            upload_method="docs_upload",
            directory=folder,
            description=description,
            tags=tag_list,
            content_hash=content_hash,
        )

        return {
            "uploaded": True,
            "document_id": doc_id,
            "path": str(file_path.relative_to(kb)),
            "folder": folder,
            "name": file.filename,
            "size": len(content),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.get("/stats")
async def get_library_stats():
    """Get aggregate stats about the docs library."""
    from models.database_models import Document
    from sqlalchemy import func
    db = _get_db()
    try:
        total = db.query(func.count(Document.id)).scalar() or 0
        total_size = db.query(func.sum(Document.file_size)).scalar() or 0
        by_status = dict(
            db.query(Document.status, func.count(Document.id))
            .group_by(Document.status).all()
        )
        by_source = dict(
            db.query(Document.source, func.count(Document.id))
            .group_by(Document.source).all()
        )
        by_method = dict(
            db.query(Document.upload_method, func.count(Document.id))
            .group_by(Document.upload_method).all()
        )

        docs = db.query(Document).all()
        folder_set = set()
        for doc in docs:
            d = _doc_to_dict(doc)
            if d["folder"]:
                folder_set.add(d["folder"])

        return {
            "total_documents": total,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0,
            "total_folders": len(folder_set),
            "by_status": by_status,
            "by_source": by_source,
            "by_upload_method": by_method,
        }
    finally:
        db.close()
