"""
Text ingestion API endpoints.
Provides REST endpoints for uploading and managing documents.
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Query, Depends, Path
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
import logging

from ingestion.service import TextIngestionService
from embedding import get_embedding_model
from vector_db.client import get_qdrant_client

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/ingest", tags=["Document Ingestion"])

# Global ingestion service instance
_ingestion_service: Optional[TextIngestionService] = None


def get_ingestion_service() -> Optional[TextIngestionService]:
    """Get or create ingestion service.

    Returns None if service cannot be initialized (e.g., in test environments
    without embedding models). Endpoints should handle None gracefully.
    """
    global _ingestion_service

    if _ingestion_service is None:
        try:
            print("[INGEST] Initializing ingestion service...")
            # Use singleton instance to avoid loading model multiple times
            embedding_model = get_embedding_model()
            if embedding_model is None:
                logger.warning("Embedding model not available, ingestion service disabled")
                return None
            print("[INGEST] [OK] Got embedding model (singleton)")
            _ingestion_service = TextIngestionService(
                collection_name="documents",
                chunk_size=512,
                chunk_overlap=50,
                embedding_model=embedding_model,
            )
            print("[INGEST] [OK] Ingestion service created successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ingestion service: {e}")
            return None

    return _ingestion_service


# ==================== Pydantic Models ====================

class IngestTextRequest(BaseModel):
    """Request model for text ingestion."""
    text: str = Field(..., description="The text content to ingest")
    filename: str = Field(..., description="Name of the document")
    source: Optional[str] = Field("upload", description="Source of the document")
    upload_method: Optional[str] = Field("ui-paste", description="How the document was uploaded (ui-upload, ui-paste, api, etc.)")
    source_type: Optional[str] = Field("user_generated", description="Type of source for reliability (official_docs, academic_paper, verified_tutorial, trusted_blog, community_qa, user_generated, unverified)")
    description: Optional[str] = Field(None, description="Optional description of the document")
    tags: Optional[List[str]] = Field(None, description="Optional tags for categorization")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class DocumentInfo(BaseModel):
    """Document information response."""
    id: int
    filename: str
    source: str
    upload_method: str
    confidence_score: float
    source_reliability: float
    content_quality: float
    consensus_score: float
    recency_score: float
    description: Optional[str]
    tags: Optional[List[str]]
    status: str
    total_chunks: int
    text_length: int
    created_at: str
    updated_at: str
    chunks: Optional[List[dict]] = None


class DocumentListItem(BaseModel):
    """Document list item."""
    id: int
    filename: str
    source: str
    upload_method: str
    confidence_score: float
    description: Optional[str]
    tags: Optional[List[str]]
    status: str
    total_chunks: int
    text_length: int
    created_at: str


class IngestionResponse(BaseModel):
    """Response for ingestion operation."""
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Operation message")
    document_id: Optional[int] = Field(None, description="ID of ingested document")


class SearchResult(BaseModel):
    """Search result item."""
    vector_id: int
    score: float
    chunk_id: int
    document_id: int
    chunk_index: int
    text: str
    metadata: dict


class SearchResponse(BaseModel):
    """Response for document search."""
    query: str
    results: List[SearchResult]
    total: int


class DocumentListResponse(BaseModel):
    """Response for document listing."""
    documents: List[DocumentListItem]
    total: int


# ==================== Endpoints ====================

@router.post("/text", response_model=IngestionResponse, summary="Ingest text content")
async def ingest_text(
    request: IngestTextRequest,
    service: Optional[TextIngestionService] = Depends(get_ingestion_service)
) -> IngestionResponse:
    """
    Ingest plain text content.

    Chunks the text, generates embeddings, and stores in both SQL database and Qdrant.

    Args:
        request: IngestTextRequest containing text, filename, and metadata
        service: Ingestion service instance

    Returns:
        IngestionResponse with document ID and status
    """
    # Check if service is available
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Ingestion service unavailable. Embedding model may not be configured."
        )

    try:
        print("Ingesting text document...")

        # ── Semantic entity classification (pre-materialization step) ──
        # Classify what kind of entity this data represents BEFORE hitting the DB.
        # This routes to the canonical table/collection and normalizes fields.
        entity_meta = {}
        try:
            from cognitive.semantic_entity_classifier import classify_entity
            classified = classify_entity(
                text=request.text,
                filename=request.filename,
                source_type=request.source_type or "user_generated",
                metadata=request.metadata,
            )
            entity_meta = {
                "entity_type": classified["entity_type"],
                "entity_confidence": classified["confidence"],
                "target_table": classified["db_table"],
                "target_collection": classified["vector_collection"],
                "canonical_fields": classified["canonical_fields"],
            }
            logger.info(
                "[SEMANTIC] Classified '%s' → %s (%.0f%%)",
                request.filename, classified["entity_type"], classified["confidence"] * 100
            )
        except Exception as ce:
            logger.debug("[SEMANTIC] Classification skipped: %s", ce)

        # Merge entity metadata with any user-provided metadata
        merged_metadata = {**(request.metadata or {}), **entity_meta}

        document_id, message = service.ingest_text_fast(
            text_content=request.text,
            filename=request.filename,
            source=request.source,
            upload_method=request.upload_method,
            source_type=request.source_type,
            description=request.description,
            tags=request.tags,
            metadata=merged_metadata,
        )

        if document_id is None:
            try:
                from core.kpi_recorder import record_component_kpi
                record_component_kpi("ingestion", "requests", 1.0, success=False)
            except Exception:
                pass
            raise HTTPException(status_code=400, detail=message)
        
        try:
            from core.kpi_recorder import record_component_kpi
            record_component_kpi("ingestion", "requests", 1.0, success=True)
        except Exception:
            pass
        return IngestionResponse(
            success=True,
            message=message,
            document_id=document_id,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        try:
            from core.kpi_recorder import record_component_kpi
            record_component_kpi("ingestion", "requests", 1.0, success=False)
        except Exception:
            pass
        logger.error(f"Ingestion error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.post("/file", response_model=IngestionResponse, summary="Ingest uploaded file")
async def ingest_file(
    file: UploadFile = File(..., description="Text or document file to ingest (txt, md, pdf, docx, etc.)"),
    source: str = Form("upload", description="Source identifier"),
    source_type: str = Form("user_generated", description="Type of source for reliability (official_docs, academic_paper, verified_tutorial, trusted_blog, community_qa, user_generated, unverified)"),
    metadata: Optional[str] = Form(None, description="JSON metadata"),
    service: TextIngestionService = Depends(get_ingestion_service)
) -> IngestionResponse:
    """
    Ingest a file (text or document).
    
    Supports: TXT, MD, PDF, DOCX, DOC, XLSX, PPTX, etc.
    Automatically handles format-specific text extraction.
    
    Args:
        file: Uploaded file
        source: Source identifier
        source_type: Type of source for reliability calculation
        metadata: Optional JSON metadata
        service: Ingestion service instance
        
    Returns:
        IngestionResponse with document ID and status
    """
    try:
        import json
        import chardet
        import tempfile
        from pathlib import Path
        from file_manager.file_handler import FileHandler
        
        filename = file.filename or "uploaded_file"
        file_ext = Path(filename).suffix.lower()
        
        # Read file content
        content = await file.read()
        
        logger.info(f"[API_FILE_INGEST] Received file: {filename} ({len(content)} bytes)")
        logger.info(f"[API_FILE_INGEST] File extension: {file_ext}")
        
        # For PDFs and other complex formats, save to temp file and extract
        if file_ext in ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt']:
            logger.info(f"[API_FILE_INGEST] Using specialized extractor for {file_ext}")
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name
            
            try:
                # Extract text using FileHandler
                text, error = FileHandler.extract_text(temp_path)
                
                if error:
                    logger.error(f"[API_FILE_INGEST] Extraction failed: {error}")
                    raise HTTPException(status_code=400, detail=f"Failed to extract text: {error}")
                
                logger.info(f"[API_FILE_INGEST] [OK] Extracted {len(text)} characters from {file_ext}")
            
            finally:
                # Clean up temp file
                try:
                    Path(temp_path).unlink()
                except Exception as e:
                    logger.warning(f"Could not delete temp file {temp_path}: {e}")
        
        # For text files, decode directly
        else:
            logger.info(f"[API_FILE_INGEST] Reading as text file")
            
            # Detect and decode with fallback encodings
            try:
                text = content.decode('utf-8')
                logger.info(f"[API_FILE_INGEST] [OK] Decoded as UTF-8")
            except UnicodeDecodeError:
                # Try to detect encoding
                detected = chardet.detect(content)
                encoding = detected.get('encoding') if detected else None
                
                if encoding:
                    try:
                        text = content.decode(encoding)
                        logger.info(f"[API_FILE_INGEST] [OK] Decoded as {encoding}")
                    except (UnicodeDecodeError, LookupError):
                        # Fall back to latin-1 which accepts all byte sequences
                        text = content.decode('latin-1')
                        logger.info(f"[API_FILE_INGEST] [OK] Decoded as latin-1 (fallback)")
                else:
                    # Fall back to latin-1 if detection fails
                    text = content.decode('latin-1')
                    logger.info(f"[API_FILE_INGEST] [OK] Decoded as latin-1 (no detection)")
        
        # Parse metadata if provided
        metadata_dict = None
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid metadata JSON")
        
        logger.info(f"[API_FILE_INGEST] Ingesting {len(text)} characters...")
        
        # Ingest the text
        document_id, message = service.ingest_text_fast(
            text_content=text,
            filename=filename,
            source=source,
            upload_method="ui-upload",
            source_type=source_type,
            metadata=metadata_dict,
        )
        
        if document_id is None:
            logger.error(f"[API_FILE_INGEST] Ingestion failed: {message}")
            try:
                from core.kpi_recorder import record_component_kpi
                record_component_kpi("ingestion", "requests", 1.0, success=False)
            except Exception:
                pass
            raise HTTPException(status_code=400, detail=message)
        
        logger.info(f"[API_FILE_INGEST] [OK] Successfully ingested document {document_id}")
        try:
            from core.kpi_recorder import record_component_kpi
            record_component_kpi("ingestion", "requests", 1.0, success=True)
        except Exception:
            pass
        return IngestionResponse(
            success=True,
            message=message,
            document_id=document_id,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        try:
            from core.kpi_recorder import record_component_kpi
            record_component_kpi("ingestion", "requests", 1.0, success=False)
        except Exception:
            pass
        logger.error(f"[API_FILE_INGEST] File ingestion error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"File ingestion failed: {str(e)}"
        )


@router.get("/documents/{document_id}", response_model=DocumentInfo, summary="Get document info")
async def get_document(
    document_id: int = Path(..., description="Document ID"),
    service: TextIngestionService = Depends(get_ingestion_service)
) -> DocumentInfo:
    """
    Get information about a document and its chunks.
    
    Args:
        document_id: ID of the document
        service: Ingestion service instance
        
    Returns:
        DocumentInfo with document details and chunks
    """
    try:
        doc_info = service.get_document_info(document_id)
        
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentInfo(**doc_info)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")


@router.get("/documents", response_model=DocumentListResponse, summary="List documents")
async def list_documents(
    status: Optional[str] = Query(None, description="Filter by status"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    service: TextIngestionService = Depends(get_ingestion_service)
) -> DocumentListResponse:
    """
    List ingested documents with optional filtering.
    
    Args:
        status: Filter by status (pending, processing, completed, failed)
        source: Filter by source (upload, url, api)
        limit: Maximum number of results
        offset: Result offset for pagination
        service: Ingestion service instance
        
    Returns:
        DocumentListResponse with document list
    """
    try:
        documents = service.list_documents(
            status=status,
            source=source,
            limit=limit,
            offset=offset,
        ) 
        return DocumentListResponse(
            documents=[DocumentListItem(**doc) for doc in documents],
            total=len(documents),
        )
    
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.delete("/documents/{document_id}", response_model=IngestionResponse, summary="Delete document")
async def delete_document(
    document_id: int = Path(..., description="Document ID to delete"),
    service: TextIngestionService = Depends(get_ingestion_service)
) -> IngestionResponse:
    """
    Delete a document and all its chunks.
    
    Args:
        document_id: ID of the document to delete
        service: Ingestion service instance
        
    Returns:
        IngestionResponse with deletion status
    """
    try:
        success, message = service.delete_document(document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=message)
        
        return IngestionResponse(
            success=True,
            message=message,
            document_id=document_id,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.post("/search", response_model=SearchResponse, summary="Search documents")
async def search_documents(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
    threshold: float = Query(0.5, ge=0.0, le=1.0, description="Minimum similarity score"),
    service: TextIngestionService = Depends(get_ingestion_service)
) -> SearchResponse:
    """
    Search for similar document chunks.
    
    Uses semantic search with embeddings.
    
    Args:
        query: Search query text
        limit: Maximum number of results
        threshold: Minimum similarity score (0-1)
        service: Ingestion service instance
        
    Returns:
        SearchResponse with matching chunks
    """
    try:
        results = service.search_documents(
            query_text=query,
            limit=limit,
            score_threshold=threshold,
        )
        
        return SearchResponse(
            query=query,
            results=[SearchResult(**result) for result in results],
            total=len(results),
        )
    
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/status", summary="Get ingestion service status")
async def get_status(
    service: TextIngestionService = Depends(get_ingestion_service)
) -> dict:
    """
    Get status of ingestion service and vector database.
    
    Returns:
        Dictionary with service status information
    """
    try:
        qdrant = get_qdrant_client()
        
        return {
            "ingestion_service": "operational",
            "vector_db_connected": qdrant.is_connected(),
            "collections": qdrant.list_collections(),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {
            "ingestion_service": "error",
            "vector_db_connected": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
