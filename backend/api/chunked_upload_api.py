"""
Chunked Upload API — supports files up to 5GB with resumable uploads.

Protocol:
  1. POST /api/upload/initiate   → returns upload_id, chunk_size, total_chunks
  2. POST /api/upload/chunk      → upload one chunk at a time (or in parallel)
  3. POST /api/upload/complete   → reassemble, verify SHA256, register in system
  4. GET  /api/upload/status     → check which chunks have been received (for resume)
  5. DELETE /api/upload/cancel   → abort and clean up

Best practices implemented:
  - 5 MB default chunk size (configurable, good balance for network resilience)
  - Per-chunk SHA256 verification — detects corruption immediately
  - Full-file SHA256 verification on reassembly
  - Resumable — client can query status and only send missing chunks
  - Parallel chunk uploads supported (server is stateless per-chunk)
  - Orphan cleanup — background task removes stale uploads after 24 hours
  - Streaming reassembly — chunks written sequentially, never hold full file in memory
  - Genesis Key tracking on every phase
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
import json
import logging
import os
import shutil
import tempfile
import threading
import time
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload", tags=["Chunked Upload"])

MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5 GB
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024     # 5 MB
MIN_CHUNK_SIZE = 1 * 1024 * 1024         # 1 MB
MAX_CHUNK_SIZE = 50 * 1024 * 1024        # 50 MB
ORPHAN_TTL_HOURS = 24

_upload_sessions: Dict[str, Dict[str, Any]] = {}
_session_lock = threading.Lock()


def _get_temp_dir() -> Path:
    from settings import settings
    base = Path(settings.KNOWLEDGE_BASE_PATH).parent / "data" / "chunk_uploads"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _get_kb_path() -> Path:
    from settings import settings
    return Path(settings.KNOWLEDGE_BASE_PATH)


class UploadInitRequest(BaseModel):
    filename: str
    file_size: int
    chunk_size: Optional[int] = None
    file_hash: Optional[str] = None
    folder: str = ""
    description: str = ""
    tags: Optional[List[str]] = None
    auto_ingest: bool = True
    source: str = "upload"


class UploadCompleteRequest(BaseModel):
    upload_id: str
    file_hash: Optional[str] = None


class UploadCancelRequest(BaseModel):
    upload_id: str


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def _create_session(upload_id: str, data: dict):
    with _session_lock:
        _upload_sessions[upload_id] = data
    _persist_session(upload_id, data)


def _get_session(upload_id: str) -> Optional[dict]:
    with _session_lock:
        session = _upload_sessions.get(upload_id)
    if session:
        return session
    return _load_session(upload_id)


def _update_session(upload_id: str, updates: dict):
    with _session_lock:
        if upload_id in _upload_sessions:
            _upload_sessions[upload_id].update(updates)
            _persist_session(upload_id, _upload_sessions[upload_id])


def _remove_session(upload_id: str):
    with _session_lock:
        _upload_sessions.pop(upload_id, None)
    meta_path = _get_temp_dir() / upload_id / "meta.json"
    if meta_path.exists():
        try:
            meta_path.unlink()
        except Exception:
            pass


def _persist_session(upload_id: str, data: dict):
    chunk_dir = _get_temp_dir() / upload_id
    chunk_dir.mkdir(parents=True, exist_ok=True)
    meta_path = chunk_dir / "meta.json"
    serialisable = {}
    for k, v in data.items():
        if isinstance(v, set):
            serialisable[k] = list(v)
        elif isinstance(v, datetime):
            serialisable[k] = v.isoformat()
        else:
            serialisable[k] = v
    try:
        meta_path.write_text(json.dumps(serialisable, default=str))
    except Exception as e:
        logger.warning(f"Failed to persist session {upload_id}: {e}")


def _load_session(upload_id: str) -> Optional[dict]:
    meta_path = _get_temp_dir() / upload_id / "meta.json"
    if not meta_path.exists():
        return None
    try:
        data = json.loads(meta_path.read_text())
        if "received_chunks" in data and isinstance(data["received_chunks"], list):
            data["received_chunks"] = set(data["received_chunks"])
        with _session_lock:
            _upload_sessions[upload_id] = data
        return data
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/initiate")
async def initiate_upload(req: UploadInitRequest):
    """
    Start a chunked upload session.
    Returns upload_id, chunk_size, and total_chunks the client must send.
    """
    if req.file_size <= 0:
        raise HTTPException(status_code=400, detail="file_size must be positive")
    if req.file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum: {MAX_FILE_SIZE / (1024**3):.0f} GB"
        )

    chunk_size = req.chunk_size or DEFAULT_CHUNK_SIZE
    chunk_size = max(MIN_CHUNK_SIZE, min(chunk_size, MAX_CHUNK_SIZE))
    total_chunks = (req.file_size + chunk_size - 1) // chunk_size

    upload_id = f"up_{uuid.uuid4().hex[:16]}"

    chunk_dir = _get_temp_dir() / upload_id
    chunk_dir.mkdir(parents=True, exist_ok=True)

    session = {
        "upload_id": upload_id,
        "filename": req.filename,
        "file_size": req.file_size,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "file_hash": req.file_hash,
        "folder": req.folder,
        "description": req.description,
        "tags": req.tags or [],
        "auto_ingest": req.auto_ingest,
        "source": req.source,
        "received_chunks": set(),
        "chunk_hashes": {},
        "created_at": datetime.utcnow().isoformat(),
        "status": "in_progress",
    }
    _create_session(upload_id, session)

    try:
        from api._genesis_tracker import track
        track(
            key_type="upload",
            what=f"Chunked upload initiated: {req.filename} ({_fmt_size(req.file_size)})",
            how="POST /api/upload/initiate",
            file_path=req.folder,
            output_data={
                "upload_id": upload_id,
                "file_size": req.file_size,
                "total_chunks": total_chunks,
                "chunk_size": chunk_size,
            },
            tags=["upload", "chunked", "initiate"],
        )
    except Exception:
        pass

    return {
        "upload_id": upload_id,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "file_size": req.file_size,
        "filename": req.filename,
    }


@router.post("/chunk")
async def upload_chunk(
    request: Request,
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk_hash: Optional[str] = Form(None),
    chunk: UploadFile = File(...),
):
    """
    Upload a single chunk. Can be called in parallel for different chunks.
    chunk_hash is the hex SHA256 of the chunk data for integrity verification.
    """
    session = _get_session(upload_id)
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found or expired")
    if session.get("status") != "in_progress":
        raise HTTPException(status_code=409, detail=f"Upload session is '{session.get('status')}', not 'in_progress'")

    total_chunks = session["total_chunks"]
    if chunk_index < 0 or chunk_index >= total_chunks:
        raise HTTPException(
            status_code=400,
            detail=f"chunk_index must be 0..{total_chunks - 1}"
        )

    chunk_data = await chunk.read()

    expected_size = session["chunk_size"]
    is_last = chunk_index == total_chunks - 1
    if is_last:
        remainder = session["file_size"] % expected_size
        expected_size = remainder if remainder > 0 else expected_size

    if len(chunk_data) != expected_size:
        raise HTTPException(
            status_code=400,
            detail=f"Chunk {chunk_index} size mismatch: got {len(chunk_data)}, expected {expected_size}"
        )

    actual_hash = hashlib.sha256(chunk_data).hexdigest()
    if chunk_hash and chunk_hash != actual_hash:
        raise HTTPException(
            status_code=400,
            detail=f"Chunk {chunk_index} hash mismatch: expected {chunk_hash}, got {actual_hash}"
        )

    chunk_dir = _get_temp_dir() / upload_id
    chunk_path = chunk_dir / f"chunk_{chunk_index:06d}"
    chunk_path.write_bytes(chunk_data)

    received = session.get("received_chunks", set())
    if isinstance(received, list):
        received = set(received)
    received.add(chunk_index)

    hashes = session.get("chunk_hashes", {})
    hashes[str(chunk_index)] = actual_hash

    _update_session(upload_id, {
        "received_chunks": received,
        "chunk_hashes": hashes,
    })

    return {
        "upload_id": upload_id,
        "chunk_index": chunk_index,
        "received": True,
        "chunk_hash": actual_hash,
        "chunks_received": len(received),
        "chunks_remaining": total_chunks - len(received),
        "progress_percent": round(len(received) / total_chunks * 100, 1),
    }


@router.get("/status")
async def get_upload_status(upload_id: str):
    """
    Get current upload progress. Useful for resuming interrupted uploads.
    Returns which chunks have been received so the client knows what to re-send.
    """
    session = _get_session(upload_id)
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")

    received = session.get("received_chunks", set())
    if isinstance(received, list):
        received = set(received)
    total = session["total_chunks"]
    missing = sorted(set(range(total)) - received)

    return {
        "upload_id": upload_id,
        "filename": session["filename"],
        "file_size": session["file_size"],
        "total_chunks": total,
        "chunks_received": len(received),
        "chunks_missing": missing,
        "progress_percent": round(len(received) / total * 100, 1) if total else 0,
        "status": session.get("status", "unknown"),
        "created_at": session.get("created_at"),
    }


@router.post("/complete")
async def complete_upload(req: UploadCompleteRequest):
    """
    Reassemble chunks into the final file, verify integrity, register in the system.
    Uses streaming reassembly — never holds the full file in memory.
    """
    session = _get_session(req.upload_id)
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")

    received = session.get("received_chunks", set())
    if isinstance(received, list):
        received = set(received)
    total = session["total_chunks"]
    missing = sorted(set(range(total)) - received)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete: {len(missing)} chunks missing: {missing[:20]}{'...' if len(missing) > 20 else ''}"
        )

    _update_session(req.upload_id, {"status": "assembling"})

    chunk_dir = _get_temp_dir() / req.upload_id
    kb = _get_kb_path()
    folder = session.get("folder", "")
    target_dir = kb / folder if folder else kb
    target_dir.mkdir(parents=True, exist_ok=True)
    final_path = target_dir / session["filename"]

    if final_path.exists():
        stem = final_path.stem
        suffix = final_path.suffix
        counter = 1
        while final_path.exists():
            final_path = target_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    try:
        file_hash = hashlib.sha256()
        total_written = 0

        with open(final_path, "wb") as out:
            for i in range(total):
                chunk_path = chunk_dir / f"chunk_{i:06d}"
                if not chunk_path.exists():
                    raise HTTPException(
                        status_code=500,
                        detail=f"Chunk file {i} missing from disk during assembly"
                    )
                data = chunk_path.read_bytes()
                file_hash.update(data)
                out.write(data)
                total_written += len(data)

        final_hash = file_hash.hexdigest()
        expected_hash = req.file_hash or session.get("file_hash")
        if expected_hash and expected_hash != final_hash:
            final_path.unlink(missing_ok=True)
            _update_session(req.upload_id, {"status": "hash_mismatch"})
            raise HTTPException(
                status_code=400,
                detail=f"File hash mismatch: expected {expected_hash}, got {final_hash}. Upload corrupted."
            )

        if total_written != session["file_size"]:
            final_path.unlink(missing_ok=True)
            _update_session(req.upload_id, {"status": "size_mismatch"})
            raise HTTPException(
                status_code=400,
                detail=f"File size mismatch: expected {session['file_size']}, got {total_written}"
            )

        _update_session(req.upload_id, {"status": "registering"})

        doc_id = None
        try:
            from api.docs_library_api import register_document
            doc_id = register_document(
                filename=session["filename"],
                file_path=str(final_path),
                file_size=total_written,
                source=session.get("source", "upload"),
                upload_method="chunked_upload",
                directory=folder,
                description=session.get("description", ""),
                tags=session.get("tags", []),
                content_hash=final_hash,
            )
        except Exception as e:
            logger.warning(f"Docs library registration skipped: {e}")

        gk = None
        try:
            from api._genesis_tracker import track
            gk = track(
                key_type="upload",
                what=f"Chunked upload completed: {session['filename']} ({_fmt_size(total_written)})",
                where=str(final_path),
                how="POST /api/upload/complete",
                file_path=str(final_path),
                output_data={
                    "upload_id": req.upload_id,
                    "file_size": total_written,
                    "total_chunks": total,
                    "sha256": final_hash,
                    "doc_id": doc_id,
                    "folder": folder,
                },
                tags=["upload", "chunked", "complete"],
            )
        except Exception:
            pass

        ingested = False
        if session.get("auto_ingest", True):
            ingested = _try_ingest(final_path, session["filename"], folder)

        _cleanup_chunks(req.upload_id)
        _update_session(req.upload_id, {"status": "completed"})

        rel_path = str(final_path.relative_to(kb))

        return {
            "completed": True,
            "upload_id": req.upload_id,
            "path": rel_path,
            "filename": session["filename"],
            "file_size": total_written,
            "file_size_display": _fmt_size(total_written),
            "sha256": final_hash,
            "total_chunks": total,
            "document_id": doc_id,
            "folder": folder,
            "ingested": ingested,
            "genesis_key": gk,
        }

    except HTTPException:
        raise
    except Exception as e:
        _update_session(req.upload_id, {"status": "error", "error": str(e)})
        logger.error(f"Chunked upload assembly failed: {e}")
        raise HTTPException(status_code=500, detail=f"Assembly failed: {e}")


@router.delete("/cancel")
async def cancel_upload(upload_id: str):
    """Cancel and clean up an in-progress upload."""
    session = _get_session(upload_id)
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")

    _cleanup_chunks(upload_id)
    _update_session(upload_id, {"status": "cancelled"})

    try:
        from api._genesis_tracker import track
        track(
            key_type="upload",
            what=f"Chunked upload cancelled: {session.get('filename', 'unknown')}",
            how="DELETE /api/upload/cancel",
            tags=["upload", "chunked", "cancel"],
        )
    except Exception:
        pass

    return {"cancelled": True, "upload_id": upload_id}


@router.get("/active")
async def list_active_uploads():
    """List all active (in-progress) upload sessions."""
    _scan_disk_sessions()
    with _session_lock:
        sessions = list(_upload_sessions.values())

    active = []
    for s in sessions:
        if s.get("status") in ("in_progress", "assembling"):
            received = s.get("received_chunks", set())
            if isinstance(received, list):
                received = set(received)
            total = s.get("total_chunks", 1)
            active.append({
                "upload_id": s["upload_id"],
                "filename": s["filename"],
                "file_size": s["file_size"],
                "file_size_display": _fmt_size(s["file_size"]),
                "progress_percent": round(len(received) / total * 100, 1) if total else 0,
                "chunks_received": len(received),
                "total_chunks": total,
                "created_at": s.get("created_at"),
                "status": s.get("status"),
            })

    return {"active_uploads": active, "count": len(active)}


# ---------------------------------------------------------------------------
# Background cleanup
# ---------------------------------------------------------------------------

def cleanup_orphaned_uploads():
    """Remove upload sessions older than ORPHAN_TTL_HOURS."""
    temp_dir = _get_temp_dir()
    if not temp_dir.exists():
        return 0

    cleaned = 0
    cutoff = datetime.utcnow() - timedelta(hours=ORPHAN_TTL_HOURS)

    for entry in temp_dir.iterdir():
        if not entry.is_dir() or not entry.name.startswith("up_"):
            continue
        meta_path = entry / "meta.json"
        try:
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                created = meta.get("created_at", "")
                status = meta.get("status", "")
                if status in ("completed", "cancelled"):
                    shutil.rmtree(entry, ignore_errors=True)
                    cleaned += 1
                    continue
                if created:
                    created_dt = datetime.fromisoformat(created)
                    if created_dt < cutoff:
                        shutil.rmtree(entry, ignore_errors=True)
                        cleaned += 1
                        continue
            else:
                stat = entry.stat()
                if datetime.fromtimestamp(stat.st_mtime) < cutoff:
                    shutil.rmtree(entry, ignore_errors=True)
                    cleaned += 1
        except Exception as e:
            logger.warning(f"Cleanup failed for {entry}: {e}")

    if cleaned:
        logger.info(f"Cleaned up {cleaned} orphaned upload sessions")
    return cleaned


def _scan_disk_sessions():
    """Load any sessions from disk that aren't in memory."""
    temp_dir = _get_temp_dir()
    if not temp_dir.exists():
        return
    for entry in temp_dir.iterdir():
        if entry.is_dir() and entry.name.startswith("up_"):
            uid = entry.name
            with _session_lock:
                if uid not in _upload_sessions:
                    _load_session(uid)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cleanup_chunks(upload_id: str):
    chunk_dir = _get_temp_dir() / upload_id
    if chunk_dir.exists():
        for f in chunk_dir.iterdir():
            if f.name.startswith("chunk_"):
                try:
                    f.unlink()
                except Exception:
                    pass


def _try_ingest(file_path: Path, filename: str, folder: str) -> bool:
    """Attempt text extraction and ingestion for the uploaded file."""
    try:
        from ingestion.service import TextIngestionService
        from embedding.embedder import get_embedding_model
        from vector_db.client import get_qdrant_client

        text_exts = {'.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx',
                     '.json', '.csv', '.xml', '.html', '.css', '.yaml',
                     '.yml', '.toml', '.cfg', '.ini', '.log', '.rst'}
        if file_path.suffix.lower() not in text_exts:
            if file_path.suffix.lower() == '.pdf':
                try:
                    from ingestion.service import extract_file_text
                    text = extract_file_text(str(file_path))
                    if text and len(text) > 50:
                        embedding_model = get_embedding_model()
                        qdrant = get_qdrant_client()
                        service = TextIngestionService(embedding_model, qdrant)
                        service.ingest_text(
                            text=text,
                            source=filename,
                            metadata={"file_path": str(file_path), "directory": folder}
                        )
                        return True
                except Exception:
                    pass
            return False

        with open(file_path, 'r', errors='ignore') as f:
            text = f.read(200_000)

        if not text or len(text) < 10:
            return False

        embedding_model = get_embedding_model()
        qdrant = get_qdrant_client()
        service = TextIngestionService(embedding_model, qdrant)
        service.ingest_text(
            text=text,
            source=filename,
            metadata={"file_path": str(file_path), "directory": folder}
        )

        try:
            from cognitive.magma_bridge import ingest as magma_ingest
            magma_ingest(f"Document ingested: {filename} in {folder}", source="chunked_upload")
        except Exception:
            pass

        return True
    except Exception as e:
        logger.debug(f"Ingestion skipped for {filename}: {e}")
        return False


def _fmt_size(size_bytes: int) -> str:
    """Format bytes into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"
