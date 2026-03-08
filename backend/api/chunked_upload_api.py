"""
Chunked Upload API - Handles large file uploads in streaming chunks.
Integrates directly with docs_library_api.py to register assembled files.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel
from typing import Optional, Dict, List, Set, Any
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json
import logging
import os
import shutil
import threading
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload", tags=["Chunked Uploads"])

# --- Constants aligned with test_chunked_upload.py ---
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5 GB
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024      # 5 MB
MIN_CHUNK_SIZE = 1 * 1024 * 1024          # 1 MB
MAX_CHUNK_SIZE = 50 * 1024 * 1024         # 50 MB
ORPHAN_TTL_HOURS = 24

# --- In-Memory Session State ---
# Structure: { upload_id: { ...session_data... } }
_upload_sessions: Dict[str, Any] = {}
_session_lock = threading.Lock()

def _get_temp_dir() -> Path:
    from settings import settings
    # Ensure temporary upload directory exists
    temp_dir = Path(settings.KNOWLEDGE_BASE_PATH) / ".temp_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir

def _fmt_size(b: int) -> str:
    """Format bytes into human-readable string (used by tests)."""
    if not b:
        return "0 B"
    if b < 1024:
        return f"{b} B"
    k = 1024
    for s in ['KB', 'MB', 'GB']:
        if b < k * 1024 or s == 'GB':
            if s == 'KB' or s == 'MB':
                return f"{b / k:.1f} {s}"
            return f"{b / k:.2f} {s}"
        k *= 1024
    return f"{b / k:.2f} GB"

def _create_session(uid: str, data: dict):
    """Create a new session in memory and on disk."""
    with _session_lock:
        _upload_sessions[uid] = data
    
    # Persist to disk
    chunk_dir = _get_temp_dir() / uid
    chunk_dir.mkdir(parents=True, exist_ok=True)
    
    # convert sets to list for disk JSON
    disk_data = data.copy()
    if isinstance(disk_data.get("received_chunks"), set):
        disk_data["received_chunks"] = list(disk_data["received_chunks"])
        
    (chunk_dir / "meta.json").write_text(json.dumps(disk_data))

def _get_session(uid: str) -> Optional[dict]:
    """Retrieve session from memory, fallback to disk."""
    with _session_lock:
        if uid in _upload_sessions:
            session = _upload_sessions[uid]
            # Ensure received_chunks is a set in memory
            if isinstance(session.get("received_chunks"), list):
                session["received_chunks"] = set(session["received_chunks"])
            return session
            
    # Load from disk if not in memory
    meta_file = _get_temp_dir() / uid / "meta.json"
    if meta_file.exists():
        try:
            data = json.loads(meta_file.read_text())
            if isinstance(data.get("received_chunks"), list):
                data["received_chunks"] = set(data["received_chunks"])
            with _session_lock:
                _upload_sessions[uid] = data
            return data
        except json.JSONDecodeError:
            pass
    return None

def _update_session(uid: str, updates: dict):
    """Update active session in memory and disk."""
    session = _get_session(uid)
    if not session:
        return
        
    with _session_lock:
        session.update(updates)
        _upload_sessions[uid] = session
        
    # Persist
    chunk_dir = _get_temp_dir() / uid
    if chunk_dir.exists():
        disk_data = session.copy()
        if isinstance(disk_data.get("received_chunks"), set):
            disk_data["received_chunks"] = list(disk_data["received_chunks"])
        (chunk_dir / "meta.json").write_text(json.dumps(disk_data))

def _remove_session(uid: str):
    """Remove session from memory tracking."""
    with _session_lock:
        _upload_sessions.pop(uid, None)

def _cleanup_chunks(uid: str):
    """Remove temporary chunk files and directory."""
    chunk_dir = _get_temp_dir() / uid
    if chunk_dir.exists():
        shutil.rmtree(chunk_dir, ignore_errors=True)

def cleanup_orphaned_uploads() -> int:
    """Clear out sessions older than ORPHAN_TTL_HOURS. Returns exact count cleaned."""
    temp_dir = _get_temp_dir()
    if not temp_dir.exists():
        return 0
        
    cutoff_time = datetime.utcnow() - timedelta(hours=ORPHAN_TTL_HOURS)
    cleaned_count = 0
    
    for entry in temp_dir.iterdir():
        if not entry.is_dir():
            continue
            
        uid = entry.name
        meta_file = entry / "meta.json"
        
        should_delete = False
        
        if meta_file.exists():
            try:
                data = json.loads(meta_file.read_text())
                if data.get("status") == "completed":
                    should_delete = True
                else:
                    # Check age
                    created_at_str = data.get("created_at")
                    if created_at_str:
                        # Some basic parsing
                        try:
                            # Use basic datetime parse to handle isoformat
                            from dateutil.parser import parse
                            created_at = parse(created_at_str)
                            # make naive to compare with cutoff
                            created_at = created_at.replace(tzinfo=None)
                            if created_at < cutoff_time:
                                should_delete = True
                        except BaseException:
                            pass
            except json.JSONDecodeError:
                should_delete = True
        else:
            # Orphaned directory with no metadata
            try:
                # Check dir modified time instead
                mtime = datetime.utcfromtimestamp(entry.stat().st_mtime)
                if mtime < cutoff_time:
                    should_delete = True
            except OSError:
                pass
                
        if should_delete:
            shutil.rmtree(entry, ignore_errors=True)
            _remove_session(uid)
            cleaned_count += 1
            
    return cleaned_count


# --- Pydantic Routes ---

class InitiateUploadRequest(BaseModel):
    filename: str
    file_size: int
    folder: str = ""
    auto_ingest: bool = True
    source: str = "docs_library"

@router.post("/initiate")
async def initiate_upload(req: InitiateUploadRequest):
    """Start a new chunked upload session."""
    if req.file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File exceeds max size of {_fmt_size(MAX_FILE_SIZE)}")
        
    # Calculate chunk size
    # Try default, but clamp based on total count to avoid tiny chunks or too many chunks
    chunk_size = DEFAULT_CHUNK_SIZE
    total_chunks = (req.file_size + chunk_size - 1) // chunk_size
    
    # Clamp chunk size bounds
    chunk_size = max(MIN_CHUNK_SIZE, min(chunk_size, MAX_CHUNK_SIZE))
    total_chunks = (req.file_size + chunk_size - 1) // chunk_size

    uid = f"upload_{int(time.time() * 1000)}_{hashlib.md5(req.filename.encode()).hexdigest()[:8]}"
    
    _create_session(uid, {
        "upload_id": uid,
        "filename": req.filename,
        "file_size": req.file_size,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "folder": req.folder,
        "auto_ingest": req.auto_ingest,
        "source": req.source,
        "received_chunks": set(),
        "chunk_hashes": {},
        "status": "in_progress",
        "created_at": datetime.utcnow().isoformat()
    })
    
    return {
        "upload_id": uid,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "status": "in_progress"
    }

@router.post("/chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk_hash: str = Form(...),
    chunk: UploadFile = File(...)
):
    """Receive and save a single chunk."""
    session = _get_session(upload_id)
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
        
    if session["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Session is no longer accepting chunks")

    chunk_dir = _get_temp_dir() / upload_id
    if not chunk_dir.exists():
        raise HTTPException(status_code=404, detail="Upload directory missing")
        
    chunk_data = await chunk.read()
    
    # Verify hash
    actual_hash = hashlib.sha256(chunk_data).hexdigest()
    if actual_hash != chunk_hash:
        raise HTTPException(status_code=400, detail="Chunk hash mismatch")
        
    # Write
    chunk_path = chunk_dir / f"chunk_{chunk_index:06d}"
    chunk_path.write_bytes(chunk_data)
    
    # Update Session
    received = session.get("received_chunks", set())
    if isinstance(received, list):
        received = set(received)
    received.add(chunk_index)
    
    hashes = session.get("chunk_hashes", {})
    hashes[str(chunk_index)] = actual_hash
    
    _update_session(upload_id, {"received_chunks": received, "chunk_hashes": hashes})
    
    return {"status": "ok", "uploaded": len(received), "total": session["total_chunks"]}


class CompleteUploadRequest(BaseModel):
    upload_id: str

@router.post("/complete")
async def complete_upload(req: CompleteUploadRequest):
    """Assemble all chunks and register file in docs library."""
    session = _get_session(req.upload_id)
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
        
    received = session.get("received_chunks", set())
    if isinstance(received, list):
        received = set(received)
        
    if len(received) < session["total_chunks"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Missing chunks. Found {len(received)} of {session['total_chunks']}"
        )
        
    _update_session(req.upload_id, {"status": "assembling"})
    
    try:
        from settings import settings
        kb_path = Path(settings.KNOWLEDGE_BASE_PATH)
        folder = session.get("folder", "")
        target_dir = kb_path / folder if folder else kb_path
        target_dir.mkdir(parents=True, exist_ok=True)
        
        final_path = target_dir / session["filename"]
        chunk_dir = _get_temp_dir() / req.upload_id
        
        file_hash = hashlib.sha256()
        total_size = 0
        
        # Assemble
        with open(final_path, "wb") as f_out:
            for i in range(session["total_chunks"]):
                chunk_path = chunk_dir / f"chunk_{i:06d}"
                if not chunk_path.exists():
                    raise HTTPException(status_code=500, detail=f"Missing chunk {i} on disk")
                    
                data = chunk_path.read_bytes()
                f_out.write(data)
                file_hash.update(data)
                total_size += len(data)
                
        # Register into Docs Library
        from api.docs_library_api import register_document
        doc_id = register_document(
            filename=session["filename"],
            file_path=str(final_path),
            file_size=total_size,
            source=session.get("source", "docs_library_chunked"),
            upload_method="chunked",
            directory=folder,
            description=f"Chunked assembled file: {req.upload_id}",
            content_hash=file_hash.hexdigest()
        )
        
        # Cleanup temp chunks
        _update_session(req.upload_id, {
            "status": "completed", 
            "file_hash": file_hash.hexdigest()
        })
        _cleanup_chunks(req.upload_id)
        
        return {
            "status": "success",
            "document_id": doc_id,
            "path": str(final_path.relative_to(kb_path)),
            "size": total_size
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assemble chunks for {req.upload_id}: {e}")
        _update_session(req.upload_id, {"status": "failed_assembly"})
        raise HTTPException(status_code=500, detail=str(e))
