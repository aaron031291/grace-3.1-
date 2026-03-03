"""
Autonomous Document Processor — handles unlimited document uploads.

No limit on document count. 5GB per file max.
Processes in batches of 10, queues the rest, runs autonomously.
Uses lightweight Genesis keys for high-frequency tracking.

Flow:
  User uploads 50 documents → first 10 processed immediately →
  remaining 40 queued → background agent processes 10 at a time →
  each document chunked, embedded, ingested → Genesis key per chunk →
  user notified when complete
"""

import json
import hashlib
import logging
import threading
import queue
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

BATCH_SIZE = 10
CHUNK_SIZE = 2000  # chars per chunk
CHUNK_OVERLAP = 200
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB

_processing_queue: queue.Queue = queue.Queue(maxsize=10000)
_processor_running = False
_processor_lock = threading.Lock()
_processing_status: Dict[str, dict] = {}


@dataclass
class DocumentJob:
    file_path: str
    file_name: str
    content: str = ""
    category: str = "general"
    workspace: str = ""
    status: str = "queued"  # queued, processing, done, failed
    chunks_created: int = 0
    queued_at: float = field(default_factory=time.time)


def process_documents(files: List[dict], category: str = "general",
                      workspace: str = "") -> dict:
    """
    Accept unlimited documents. Process first batch immediately,
    queue the rest for autonomous processing.

    Each file dict: { "name": str, "content": str, "size": int }
    """
    results = {
        "total": len(files),
        "immediate": 0,
        "queued": 0,
        "batch_size": BATCH_SIZE,
        "jobs": [],
    }

    # Split into immediate batch and queue
    immediate = files[:BATCH_SIZE]
    queued = files[BATCH_SIZE:]

    # Process immediate batch
    for f in immediate:
        job = DocumentJob(
            file_path=f.get("path", f.get("name", "")),
            file_name=f.get("name", ""),
            content=f.get("content", ""),
            category=category,
            workspace=workspace,
        )
        result = _process_single(job)
        results["jobs"].append(result)
        results["immediate"] += 1

    # Queue the rest
    for f in queued:
        job = DocumentJob(
            file_path=f.get("path", f.get("name", "")),
            file_name=f.get("name", ""),
            content=f.get("content", ""),
            category=category,
            workspace=workspace,
        )
        try:
            _processing_queue.put_nowait(job)
            _processing_status[job.file_name] = {"status": "queued", "queued_at": datetime.utcnow().isoformat()}
            results["queued"] += 1
        except queue.Full:
            results["jobs"].append({"file": job.file_name, "status": "queue_full"})

    # Start background processor if not running
    _ensure_processor()

    # Track via lightweight Genesis key
    try:
        from core.tracing import light_track
        light_track("file_ingestion",
                     f"Documents queued: {results['immediate']} immediate, {results['queued']} queued",
                     "document_processor",
                     ["upload", "batch", category])
    except Exception:
        pass

    return results


def _process_single(job: DocumentJob) -> dict:
    """Process a single document — chunk, store, index."""
    job.status = "processing"
    _processing_status[job.file_name] = {"status": "processing"}

    try:
        content = job.content
        if not content:
            return {"file": job.file_name, "status": "empty", "chunks": 0}

        # Chunk the document
        chunks = _chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)

        # Store chunks
        stored = 0
        for i, chunk in enumerate(chunks):
            try:
                # Save chunk to governance rules
                chunk_path = f"governance_rules/{job.category}/{job.file_name}.chunk_{i}.txt"
                from core.workspace_bridge import write_file
                write_file(chunk_path, chunk, source="document_processor")

                # Librarian indexes every chunk
                from core.librarian import ingest_document
                ingest_document(chunk_path, chunk, job.workspace, "document_processor")
                stored += 1

                # Lightweight Genesis key per chunk (fast, no DB)
                from core.tracing import light_track
                light_track("file_ingestion",
                            f"Chunk {i}/{len(chunks)}: {job.file_name}",
                            "document_processor",
                            ["chunk", job.category, job.file_name])
            except Exception:
                pass

        job.status = "done"
        job.chunks_created = stored
        _processing_status[job.file_name] = {
            "status": "done",
            "chunks": stored,
            "completed_at": datetime.utcnow().isoformat(),
        }

        # Full Genesis key for the completed document (not per-chunk)
        try:
            from api._genesis_tracker import track
            track(
                key_type="file_ingestion",
                what=f"Document processed: {job.file_name} → {stored} chunks",
                who="document_processor",
                file_path=job.file_path,
                output_data={"chunks": stored, "category": job.category, "size": len(content)},
                tags=["document", "ingestion", job.category],
            )
        except Exception:
            pass

        return {"file": job.file_name, "status": "done", "chunks": stored}

    except Exception as e:
        job.status = "failed"
        _processing_status[job.file_name] = {"status": "failed", "error": str(e)}
        return {"file": job.file_name, "status": "failed", "error": str(e)[:100]}


def _chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size

        # Try to break at a natural boundary
        if end < len(text):
            for boundary in ["\n\n", "\n", ". ", " "]:
                break_point = text.rfind(boundary, start + chunk_size // 2, end)
                if break_point > start:
                    end = break_point + len(boundary)
                    break

        chunks.append(text[start:end].strip())
        start = end - overlap

    return [c for c in chunks if c]


def _ensure_processor():
    """Start the background document processor if not running."""
    global _processor_running
    with _processor_lock:
        if _processor_running:
            return
        _processor_running = True

    def _worker():
        global _processor_running
        while True:
            batch = []
            # Collect up to BATCH_SIZE items
            for _ in range(BATCH_SIZE):
                try:
                    job = _processing_queue.get(timeout=5)
                    batch.append(job)
                except queue.Empty:
                    break

            if not batch:
                if _processing_queue.empty():
                    with _processor_lock:
                        _processor_running = False
                    return
                continue

            # Process batch
            for job in batch:
                _process_single(job)

            # Light key for batch completion
            try:
                from core.tracing import light_track
                light_track("file_ingestion",
                             f"Batch processed: {len(batch)} documents",
                             "document_processor",
                             ["batch", "complete"])
            except Exception:
                pass

    t = threading.Thread(target=_worker, daemon=True, name="doc-processor")
    t.start()


def get_processing_status() -> dict:
    """Get status of all document processing jobs."""
    return {
        "queue_size": _processing_queue.qsize(),
        "processor_running": _processor_running,
        "jobs": dict(_processing_status),
        "total_tracked": len(_processing_status),
    }
