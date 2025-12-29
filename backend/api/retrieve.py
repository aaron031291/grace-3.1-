"""
Retrieval API endpoints for RAG system.
Provides REST endpoints to retrieve and build context from stored documents.
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from retrieval.retriever import DocumentRetriever, get_retriever
from embedding.embedder import EmbeddingModel

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/retrieve", tags=["Document Retrieval"])

# Global retriever instance
_retriever: Optional[DocumentRetriever] = None


def get_document_retriever() -> DocumentRetriever:
    """Get or create document retriever instance."""
    global _retriever
    
    if _retriever is None:
        try:
            print("[RETRIEVE] Initializing document retriever...")
            # Get the embedding model from the ingestion service
            from api.ingest import get_ingestion_service
            ingest_service = get_ingestion_service()
            
            # Reuse the embedding model from ingestion service
            embedding_model = ingest_service.embedding_model
            print("[RETRIEVE] ✓ Reusing embedding model from ingestion service")
            
            _retriever = get_retriever(
                collection_name="documents",
                embedding_model=embedding_model,
            )
            print("[RETRIEVE] ✓ Document retriever created successfully")
        except Exception as e:
            logger.error(f"Failed to initialize retriever: {e}")
            raise HTTPException(
                status_code=500,
                detail="Retriever initialization failed"
            )
    
    return _retriever


# ==================== Pydantic Models ====================

class RetrievalChunk(BaseModel):
    """Retrieved document chunk."""
    chunk_id: int
    document_id: int
    chunk_index: int
    text: str
    score: Optional[float] = None
    confidence_score: Optional[float] = None
    metadata: Optional[dict] = None


class RetrievalResponse(BaseModel):
    """Response from retrieval endpoints."""
    query: Optional[str] = None
    chunks: List[RetrievalChunk]
    total: int
    context: Optional[str] = None


class ContextRequest(BaseModel):
    """Request to build context from chunks."""
    chunks: List[dict] = Field(..., description="List of chunk dictionaries")
    max_length: Optional[int] = Field(None, description="Maximum context length")
    include_sources: bool = Field(True, description="Include source attribution")


# ==================== Endpoints ====================

@router.post("/search", response_model=RetrievalResponse, summary="Retrieve relevant chunks")
async def retrieve_chunks(
    query: str = Query(..., description="Query text"),
    limit: int = Query(5, ge=1, le=100, description="Maximum chunks to retrieve"),
    threshold: float = Query(0.3, ge=0.0, le=1.0, description="Minimum relevance score"),
    retriever: DocumentRetriever = Depends(get_document_retriever)
) -> RetrievalResponse:
    """
    Retrieve document chunks relevant to a query using semantic search.
    
    Args:
        query: Query text to search for
        limit: Maximum number of chunks to return
        threshold: Minimum similarity score (0-1)
        retriever: DocumentRetriever instance
        
    Returns:
        RetrievalResponse with relevant chunks
    """
    try:
        chunks = retriever.retrieve(
            query=query,
            limit=limit,
            score_threshold=threshold,
            include_metadata=True,
        )
        
        if not chunks:
            return RetrievalResponse(
                query=query,
                chunks=[],
                total=0,
                context=""
            )
        
        # Convert to RetrievalChunk objects
        retrieval_chunks = [
            RetrievalChunk(
                chunk_id=chunk["chunk_id"],
                document_id=chunk["document_id"],
                chunk_index=chunk["chunk_index"],
                text=chunk["text"],
                score=chunk.get("score"),
                confidence_score=chunk.get("confidence_score"),
                metadata=chunk.get("metadata")
            )
            for chunk in chunks
        ]
        
        # Build context string
        context = retriever.build_context(chunks, include_sources=True)
        
        return RetrievalResponse(
            query=query,
            chunks=retrieval_chunks,
            total=len(retrieval_chunks),
            context=context
        )
    
    except Exception as e:
        logger.error(f"Retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Retrieval failed")


@router.get("/document/{document_id}", response_model=RetrievalResponse, summary="Get document chunks")
async def get_document_chunks(
    document_id: int = Path(..., description="Document ID"),
    limit: Optional[int] = Query(None, description="Maximum chunks"),
    retriever: DocumentRetriever = Depends(get_document_retriever)
) -> RetrievalResponse:
    """
    Retrieve all chunks from a specific document.
    
    Args:
        document_id: ID of the document
        limit: Maximum chunks to retrieve (None for all)
        retriever: DocumentRetriever instance
        
    Returns:
        RetrievalResponse with all document chunks
    """
    try:
        chunks = retriever.retrieve_by_document(
            document_id=document_id,
            limit=limit,
        )
        
        if not chunks:
            return RetrievalResponse(
                chunks=[],
                total=0
            )
        
        retrieval_chunks = [
            RetrievalChunk(
                chunk_id=chunk["chunk_id"],
                document_id=chunk["document_id"],
                chunk_index=chunk["chunk_index"],
                text=chunk["text"],
                confidence_score=chunk.get("confidence_score"),
                metadata=chunk.get("metadata")
            )
            for chunk in chunks
        ]
        
        context = retriever.build_context(chunks, include_sources=False)
        
        return RetrievalResponse(
            chunks=retrieval_chunks,
            total=len(retrieval_chunks),
            context=context
        )
    
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document chunks")


@router.get("/source/{source}", response_model=RetrievalResponse, summary="Get chunks by source")
async def get_chunks_by_source(
    source: str = Path(..., description="Source identifier"),
    limit: int = Query(20, ge=1, le=100, description="Maximum chunks"),
    retriever: DocumentRetriever = Depends(get_document_retriever)
) -> RetrievalResponse:
    """
    Retrieve chunks from documents with a specific source.
    
    Args:
        source: Source identifier
        limit: Maximum chunks to retrieve
        retriever: DocumentRetriever instance
        
    Returns:
        RetrievalResponse with matching chunks
    """
    try:
        chunks = retriever.retrieve_by_source(
            source=source,
            limit=limit,
            include_text=True,
        )
        
        if not chunks:
            return RetrievalResponse(
                chunks=[],
                total=0
            )
        
        retrieval_chunks = [
            RetrievalChunk(
                chunk_id=chunk["chunk_id"],
                document_id=chunk["document_id"],
                chunk_index=chunk["chunk_index"],
                text=chunk["text"] or "",
                confidence_score=chunk.get("confidence_score"),
                metadata=chunk.get("metadata")
            )
            for chunk in chunks
        ]
        
        context = retriever.build_context(chunks, include_sources=True)
        
        return RetrievalResponse(
            chunks=retrieval_chunks,
            total=len(retrieval_chunks),
            context=context
        )
    
    except Exception as e:
        logger.error(f"Error retrieving chunks by source '{source}': {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chunks by source")


@router.post("/context", summary="Build context from chunks")
async def build_context(
    request: ContextRequest,
) -> dict:
    """
    Build a formatted context string from retrieved chunks.
    
    Args:
        request: ContextRequest with chunk list and options
        
    Returns:
        Dictionary with formatted context string
    """
    try:
        # Get a retriever instance for context building
        retriever = DocumentRetriever()
        
        context = retriever.build_context(
            chunks=request.chunks,
            max_length=request.max_length,
            include_sources=request.include_sources,
        )
        
        return {
            "success": True,
            "context": context,
            "chunk_count": len(request.chunks),
            "context_length": len(context),
        }
    
    except Exception as e:
        logger.error(f"Error building context: {e}")
        raise HTTPException(status_code=500, detail="Failed to build context")


@router.post("/rerank", response_model=RetrievalResponse, summary="Retrieve and rerank chunks")
async def retrieve_and_rerank(
    query: str = Query(..., description="Query text"),
    limit: int = Query(10, ge=1, le=100, description="Chunks to retrieve"),
    threshold: float = Query(0.2, ge=0.0, le=1.0, description="Minimum score"),
    retriever: DocumentRetriever = Depends(get_document_retriever)
) -> RetrievalResponse:
    """
    Retrieve chunks and apply reranking for better relevance.
    
    Args:
        query: Query text
        limit: Maximum chunks
        threshold: Minimum similarity score
        retriever: DocumentRetriever instance
        
    Returns:
        RetrievalResponse with reranked chunks
    """
    try:
        chunks = retriever.retrieve_and_rank(
            query=query,
            limit=limit,
            score_threshold=threshold,
            rerank=True,
        )
        
        if not chunks:
            return RetrievalResponse(
                query=query,
                chunks=[],
                total=0
            )
        
        retrieval_chunks = [
            RetrievalChunk(
                chunk_id=chunk["chunk_id"],
                document_id=chunk["document_id"],
                chunk_index=chunk["chunk_index"],
                text=chunk["text"],
                score=chunk.get("score"),
                confidence_score=chunk.get("confidence_score"),
                metadata=chunk.get("metadata")
            )
            for chunk in chunks
        ]
        
        context = retriever.build_context(chunks, include_sources=True)
        
        return RetrievalResponse(
            query=query,
            chunks=retrieval_chunks,
            total=len(retrieval_chunks),
            context=context
        )
    
    except Exception as e:
        logger.error(f"Reranking error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Reranking failed")
