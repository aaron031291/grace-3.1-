from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
import json
import base64
import logging
from genesis.librarian_pipeline import get_librarian_pipeline, IngestionStatus, ContentType, IngestionRecord, IngestionResult
class IngestFileRequest(BaseModel):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Request to ingest a file from path."""
    file_path: str = Field(..., description="Path to file to ingest")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class IngestDirectoryRequest(BaseModel):
    """Request to ingest a directory."""
    directory_path: str = Field(..., description="Path to directory")
    recursive: bool = Field(default=True, description="Include subdirectories")
    patterns: Optional[List[str]] = Field(default=None, description="File patterns to match")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class IngestContentRequest(BaseModel):
    """Request to ingest raw content."""
    content: str = Field(..., description="Base64 encoded content")
    filename: str = Field(..., description="Filename for the content")
    source: str = Field(default="api", description="Source identifier")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class IngestionResponse(BaseModel):
    """Response for ingestion operations."""
    success: bool
    ingestion_id: str
    genesis_key: str
    status: str
    destination: str
    index_id: Optional[str]
    memory_id: Optional[str]
    duration_ms: int
    message: str


class IngestionRecordResponse(BaseModel):
    """Response for ingestion record."""
    ingestion_id: str
    genesis_key: str
    status: str
    content_type: str
    source: str
    destination: str
    filename: str
    file_size: int
    content_hash: str
    index_id: Optional[str]
    memory_id: Optional[str]
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]
    timeline: List[Dict[str, Any]]
    error: Optional[str]


# =============================================================================
# Ingestion Endpoints
# =============================================================================

@router.post("/file", response_model=IngestionResponse)
async def ingest_file(request: IngestFileRequest):
    """
    Ingest a file from the filesystem.

    The file will be:
    1. Assigned a Genesis Key
    2. Indexed for search
    3. Filed in organized structure
    4. Stored in memory
    """
    pipeline = get_librarian_pipeline()
    result = await pipeline.ingest_file(request.file_path, request.metadata)

    return IngestionResponse(
        success=result.success,
        ingestion_id=result.ingestion_id,
        genesis_key=result.genesis_key,
        status=result.status.value,
        destination=result.destination,
        index_id=result.index_id,
        memory_id=result.memory_id,
        duration_ms=result.duration_ms,
        message=result.message
    )


@router.post("/upload", response_model=IngestionResponse)
async def ingest_upload(
    file: UploadFile = File(...),
    metadata: str = Form(default="{}")
):
    """
    Ingest an uploaded file.

    The file will be processed through the full ingestion pipeline:
    1. RECEIVE - Accept incoming data
    2. GENESIS - Assign Genesis Key for tracking
    3. INDEX - Add to vector index for retrieval
    4. FILE - Create/name files in organized structure
    5. MEMORIZE - Store in learning memory
    """
    pipeline = get_librarian_pipeline()

    # Parse metadata
    try:
        meta = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError:
        meta = {}

    # Read file content
    content = await file.read()

    result = await pipeline.ingest_content(
        content=content,
        filename=file.filename,
        source="upload",
        metadata=meta
    )

    return IngestionResponse(
        success=result.success,
        ingestion_id=result.ingestion_id,
        genesis_key=result.genesis_key,
        status=result.status.value,
        destination=result.destination,
        index_id=result.index_id,
        memory_id=result.memory_id,
        duration_ms=result.duration_ms,
        message=result.message
    )


@router.post("/directory")
async def ingest_directory(request: IngestDirectoryRequest):
    """
    Ingest all files in a directory.

    Processes each file through the full ingestion pipeline.
    Returns summary of all ingestion results.
    """
    pipeline = get_librarian_pipeline()

    result = await pipeline.ingest_directory(
        directory_path=request.directory_path,
        recursive=request.recursive,
        patterns=request.patterns,
        metadata=request.metadata
    )

    return result


@router.post("/content", response_model=IngestionResponse)
async def ingest_content(request: IngestContentRequest):
    """
    Ingest raw content.

    Content should be base64 encoded.
    """
    pipeline = get_librarian_pipeline()

    try:
        content = base64.b64decode(request.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 content: {e}")

    result = await pipeline.ingest_content(
        content=content,
        filename=request.filename,
        source=request.source,
        metadata=request.metadata
    )

    return IngestionResponse(
        success=result.success,
        ingestion_id=result.ingestion_id,
        genesis_key=result.genesis_key,
        status=result.status.value,
        destination=result.destination,
        index_id=result.index_id,
        memory_id=result.memory_id,
        duration_ms=result.duration_ms,
        message=result.message
    )


# =============================================================================
# Status & Tracking Endpoints
# =============================================================================

@router.get("/list")
async def list_ingestions(
    status: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    List ingestion records.

    Filter by status or content type.
    Results are sorted by creation date (newest first).
    """
    pipeline = get_librarian_pipeline()

    # Parse filters
    status_filter = IngestionStatus(status) if status else None
    type_filter = ContentType(content_type) if content_type else None

    records = pipeline.list_ingestions(
        status=status_filter,
        content_type=type_filter,
        limit=limit,
        offset=offset
    )

    return {
        "count": len(records),
        "offset": offset,
        "limit": limit,
        "ingestions": [
            {
                "ingestion_id": r.ingestion_id,
                "genesis_key": r.genesis_key,
                "status": r.status.value,
                "content_type": r.content_type.value,
                "filename": r.filename,
                "file_size": r.file_size,
                "destination": r.destination,
                "created_at": r.created_at,
                "updated_at": r.updated_at
            }
            for r in records
        ]
    }


@router.get("/{ingestion_id}", response_model=IngestionRecordResponse)
async def get_ingestion(ingestion_id: str):
    """
    Get details of a specific ingestion.

    Includes full timeline of processing steps.
    """
    pipeline = get_librarian_pipeline()
    record = pipeline.get_ingestion(ingestion_id)

    if not record:
        raise HTTPException(status_code=404, detail=f"Ingestion not found: {ingestion_id}")

    return IngestionRecordResponse(
        ingestion_id=record.ingestion_id,
        genesis_key=record.genesis_key,
        status=record.status.value,
        content_type=record.content_type.value,
        source=record.source,
        destination=record.destination,
        filename=record.filename,
        file_size=record.file_size,
        content_hash=record.content_hash,
        index_id=record.index_id,
        memory_id=record.memory_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
        metadata=record.metadata,
        timeline=record.timeline,
        error=record.error
    )


@router.get("/genesis/{genesis_key}")
async def get_by_genesis_key(genesis_key: str):
    """
    Get ingestions by Genesis Key.

    Returns all ingestions associated with a Genesis Key.
    """
    pipeline = get_librarian_pipeline()
    records = pipeline.get_ingestions_by_genesis_key(genesis_key)

    return {
        "genesis_key": genesis_key,
        "count": len(records),
        "ingestions": [
            {
                "ingestion_id": r.ingestion_id,
                "status": r.status.value,
                "content_type": r.content_type.value,
                "filename": r.filename,
                "destination": r.destination,
                "created_at": r.created_at
            }
            for r in records
        ]
    }


# =============================================================================
# Library Management Endpoints
# =============================================================================

@router.get("/statistics")
async def get_statistics():
    """
    Get library statistics.

    Returns counts by status, type, and recent activity.
    """
    pipeline = get_librarian_pipeline()
    return pipeline.get_statistics()


@router.get("/search")
async def search_library(
    query: str,
    content_type: Optional[str] = None,
    limit: int = 20
):
    """
    Search the library.

    Searches filenames and metadata.
    """
    pipeline = get_librarian_pipeline()

    type_filter = ContentType(content_type) if content_type else None

    results = pipeline.search_library(query, type_filter, limit)

    return {
        "query": query,
        "count": len(results),
        "results": results
    }


@router.get("/stream")
async def stream_ingestions():
    """
    Stream ingestion updates via Server-Sent Events.

    Provides real-time updates as files are ingested.
    Connect to this endpoint to receive live updates in the UI.
    """
    pipeline = get_librarian_pipeline()

    async def event_generator():
        queue = asyncio.Queue()

        def listener(record: IngestionRecord):
            asyncio.create_task(queue.put(record))

        pipeline.add_listener(listener)

        try:
            # Send initial statistics
            stats = pipeline.get_statistics()
            yield f"data: {json.dumps({'type': 'statistics', 'data': stats})}\n\n"

            while True:
                try:
                    record = await asyncio.wait_for(queue.get(), timeout=30.0)

                    event_data = {
                        "type": "ingestion_update",
                        "data": {
                            "ingestion_id": record.ingestion_id,
                            "genesis_key": record.genesis_key,
                            "status": record.status.value,
                            "content_type": record.content_type.value,
                            "filename": record.filename,
                            "destination": record.destination,
                            "updated_at": record.updated_at,
                            "timeline": record.timeline[-1] if record.timeline else None
                        }
                    }

                    yield f"data: {json.dumps(event_data)}\n\n"

                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

        finally:
            pipeline.remove_listener(listener)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


# =============================================================================
# Reference Data Endpoints
# =============================================================================

@router.get("/types")
async def list_content_types():
    """
    List available content types.

    Returns all content type categories.
    """
    return {
        "types": [
            {"value": ct.value, "name": ct.name}
            for ct in ContentType
        ]
    }


@router.get("/statuses")
async def list_statuses():
    """
    List ingestion statuses.

    Returns all possible ingestion states with descriptions.
    """
    status_descriptions = {
        "pending": "Waiting to be processed",
        "receiving": "Receiving data",
        "genesis_assigned": "Genesis Key assigned for tracking",
        "indexing": "Adding to search index",
        "indexed": "Added to search index",
        "filing": "Creating file in library",
        "filed": "File created in library",
        "memorizing": "Storing in learning memory",
        "complete": "Ingestion complete",
        "failed": "Ingestion failed"
    }

    return {
        "statuses": [
            {
                "value": s.value,
                "name": s.name,
                "description": status_descriptions.get(s.value, "")
            }
            for s in IngestionStatus
        ]
    }


# =============================================================================
# Health Endpoint
# =============================================================================

@router.get("/health")
async def ingestion_health():
    """
    Check ingestion pipeline health.

    Returns storage status and recent activity.
    """
    pipeline = get_librarian_pipeline()
    stats = pipeline.get_statistics()

    return {
        "status": "healthy",
        "storage_path": stats["storage_path"],
        "total_ingestions": stats["total_ingestions"],
        "total_size_mb": stats["total_size_mb"],
        "active_ingestions": stats["by_status"].get("pending", 0) +
                           stats["by_status"].get("receiving", 0) +
                           stats["by_status"].get("indexing", 0),
        "completed": stats["by_status"].get("complete", 0),
        "failed": stats["by_status"].get("failed", 0)
    }
