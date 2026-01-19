"""
Retrieval API endpoints for RAG system.
Provides REST endpoints to retrieve and build context from stored documents.
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from retrieval.retriever import DocumentRetriever, get_retriever
from retrieval.cognitive_retriever import CognitiveRetriever
from embedding import EmbeddingModel
from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKeyType
from database.session import get_session
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/retrieve", tags=["Document Retrieval"])

# Global retriever instances
_retriever: Optional[DocumentRetriever] = None
_cognitive_retriever: Optional[CognitiveRetriever] = None


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
            print("[RETRIEVE] [OK] Reusing embedding model from ingestion service")

            _retriever = get_retriever(
                collection_name="documents",
                embedding_model=embedding_model,
            )
            print("[RETRIEVE] [OK] Document retriever created successfully")
        except Exception as e:
            logger.error(f"Failed to initialize retriever: {e}")
            raise HTTPException(
                status_code=500,
                detail="Retriever initialization failed"
            )

    return _retriever


def get_cognitive_retriever() -> CognitiveRetriever:
    """Get or create cognitive retriever instance."""
    global _cognitive_retriever

    if _cognitive_retriever is None:
        try:
            print("[COGNITIVE] Initializing cognitive retriever...")
            # Get base retriever
            base_retriever = get_document_retriever()

            # Wrap with cognitive layer
            _cognitive_retriever = CognitiveRetriever(
                retriever=base_retriever,
                enable_cognitive=True,
                enable_learning=True
            )
            print("[COGNITIVE] [OK] Cognitive retriever created successfully")
            print("[COGNITIVE] [OK] OODA loop enforcement enabled")
            print("[COGNITIVE] [OK] Learning memory integration enabled")
        except Exception as e:
            logger.error(f"Failed to initialize cognitive retriever: {e}")
            raise HTTPException(
                status_code=500,
                detail="Cognitive retriever initialization failed"
            )

    return _cognitive_retriever


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
    
    # Auto-search fields
    auto_search_triggered: bool = False
    auto_search_job_ids: Optional[List[int]] = None
    auto_search_urls: Optional[List[str]] = None
    auto_search_message: Optional[str] = None


class ContextRequest(BaseModel):
    """Request to build context from chunks."""
    chunks: List[dict] = Field(..., description="List of chunk dictionaries")
    max_length: Optional[int] = Field(None, description="Maximum context length")
    include_sources: bool = Field(True, description="Include source attribution")


# ==================== Endpoints ====================

@router.post("/search-cognitive", summary="Cognitive retrieval with OODA loop")
async def retrieve_chunks_cognitive(
    query: str = Query(..., description="Query text"),
    limit: int = Query(5, ge=1, le=100, description="Maximum chunks to retrieve"),
    threshold: float = Query(0.3, ge=0.0, le=1.0, description="Minimum relevance score"),
    keyword_weight: float = Query(0.3, ge=0.0, le=1.0, description="Weight for keyword matching (0-1)"),
    user_id: Optional[str] = Query(None, description="Genesis user ID"),
    genesis_key_id: Optional[str] = Query(None, description="Genesis Key ID"),
    cognitive_retriever: CognitiveRetriever = Depends(get_cognitive_retriever),
    session: Session = Depends(get_session)
) -> dict:
    """
    Retrieve document chunks using Cognitive Engine with OODA loop.

    This endpoint integrates:
    1. **Cognitive Engine** - OODA loop for decision-making
    2. **Ambiguity Tracking** - Identifies and tracks unknowns
    3. **Learning Memory** - Records outcomes for future improvement
    4. **Trust Scoring** - Builds trust in retrieval strategies

    The system:
    - **Observes**: Analyzes query characteristics and ambiguity
    - **Orients**: Determines constraints and available strategies
    - **Decides**: Chooses best retrieval strategy (semantic/hybrid/reranked)
    - **Acts**: Executes retrieval and tracks quality

    Returns enriched results with cognitive metadata including:
    - Decision ID (for tracking)
    - Strategy selected (semantic/hybrid/reranked)
    - Ambiguity level (low/medium/high)
    - Quality score (0-1)
    - OODA phases completed

    Args:
        query: Query text to search for
        limit: Maximum number of chunks to return
        threshold: Minimum similarity score (0-1)
        keyword_weight: Weight for keyword matching (0-1)
        user_id: Genesis user ID (for learning memory)
        genesis_key_id: Genesis Key ID (for tracking)
        cognitive_retriever: CognitiveRetriever instance

    Returns:
        Dict with chunks, context, and cognitive metadata
    """
    try:
        # ✅ GENESIS KEY: Track RAG query
        genesis_service = get_genesis_service(session)
        created_genesis_key = genesis_service.create_key(
            key_type=GenesisKeyType.USER_INPUT,
            what_description=f"RAG query: {query[:100]}",
            who_actor=user_id or "anonymous",
            where_location="cognitive_retrieval_api",
            why_reason="User requested information retrieval",
            how_method="POST /retrieve/search-cognitive",
            input_data={"query": query, "limit": limit, "threshold": threshold},
            context_data={"endpoint": "/retrieve/search-cognitive"},
            session=session
        )
        logger.info(f"✅ Genesis Key created for RAG query: {created_genesis_key.key_id}")

        # Use the created genesis_key_id if not provided
        if not genesis_key_id:
            genesis_key_id = created_genesis_key.key_id

        result = cognitive_retriever.retrieve_with_cognition(
            query=query,
            limit=limit,
            score_threshold=threshold,
            keyword_weight=keyword_weight,
            user_id=user_id,
            genesis_key_id=genesis_key_id
        )

        # Convert chunks to RetrievalChunk objects for consistency
        retrieval_chunks = [
            {
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
                "score": chunk.get("score"),
                "confidence_score": chunk.get("confidence_score"),
                "metadata": chunk.get("metadata")
            }
            for chunk in result["chunks"]
        ]

        return {
            "query": result["query"],
            "chunks": retrieval_chunks,
            "total": result["total"],
            "context": result["context"],
            "cognitive_metadata": result.get("cognitive_metadata", {}),
            "strategy_used": result.get("strategy_used")
        }

    except Exception as e:
        logger.error(f"Cognitive retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cognitive retrieval failed: {str(e)}")


@router.post("/feedback", summary="Provide feedback on retrieval results")
async def provide_retrieval_feedback(
    query: str = Query(..., description="Original query"),
    chunks_used: List[int] = Query(..., description="Chunk IDs that were used"),
    was_helpful: bool = Query(..., description="Whether results were helpful"),
    user_id: Optional[str] = Query(None, description="Genesis user ID"),
    genesis_key_id: Optional[str] = Query(None, description="Genesis Key ID"),
    cognitive_retriever: CognitiveRetriever = Depends(get_cognitive_retriever)
) -> dict:
    """
    Provide feedback on retrieval results to improve learning.

    This creates high-trust learning examples from direct user feedback,
    which helps the system learn which retrieval strategies work best.

    Args:
        query: Original query that was used
        chunks_used: List of chunk IDs that were used in the response
        was_helpful: True if results were helpful, False otherwise
        user_id: Genesis user ID
        genesis_key_id: Genesis Key ID
        cognitive_retriever: CognitiveRetriever instance

    Returns:
        Success confirmation
    """
    try:
        cognitive_retriever.provide_feedback(
            query=query,
            chunks_used=chunks_used,
            was_helpful=was_helpful,
            user_id=user_id,
            genesis_key_id=genesis_key_id
        )

        return {
            "success": True,
            "message": "Feedback recorded successfully",
            "feedback_type": "positive" if was_helpful else "negative"
        }

    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to record feedback")


@router.post("/search", response_model=RetrievalResponse, summary="Retrieve relevant chunks")
async def retrieve_chunks(
    query: str = Query(..., description="Query text"),
    limit: int = Query(5, ge=1, le=100, description="Maximum chunks to retrieve"),
    threshold: float = Query(0.3, ge=0.0, le=1.0, description="Minimum relevance score"),
    keyword_weight: float = Query(0.3, ge=0.0, le=1.0, description="Weight for keyword matching (0-1)"),
    retriever: DocumentRetriever = Depends(get_document_retriever)
) -> RetrievalResponse:
    """
    Retrieve document chunks relevant to a query using hybrid search (semantic + keyword).
    
    Uses keyword boosting to ensure short queries return documents with matching keywords.
    For longer queries, semantic relevance naturally dominates.
    
    Args:
        query: Query text to search for
        limit: Maximum number of chunks to return
        threshold: Minimum similarity score (0-1)
        keyword_weight: Weight for keyword matching (0-1, default 0.3 = 30% keyword, 70% semantic)
        retriever: DocumentRetriever instance
        
    Returns:
        RetrievalResponse with relevant chunks, ranked by combined score
    """
    try:
        chunks = retriever.retrieve_hybrid(
            query=query,
            limit=limit,
            score_threshold=threshold,
            include_metadata=True,
            keyword_weight=keyword_weight,
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


@router.post("/search-semantic", response_model=RetrievalResponse, summary="Retrieve using pure semantic search")
async def retrieve_chunks_semantic(
    query: str = Query(..., description="Query text"),
    limit: int = Query(5, ge=1, le=100, description="Maximum chunks to retrieve"),
    threshold: float = Query(0.3, ge=0.0, le=1.0, description="Minimum relevance score"),
    retriever: DocumentRetriever = Depends(get_document_retriever)
) -> RetrievalResponse:
    """
    Retrieve document chunks using pure semantic search (no keyword boosting).
    
    Best for longer, contextual queries. Use /retrieve/search for hybrid approach.
    
    Args:
        query: Query text to search for
        limit: Maximum number of chunks to return
        threshold: Minimum similarity score (0-1)
        retriever: DocumentRetriever instance
        
    Returns:
        RetrievalResponse with relevant chunks ranked by semantic similarity
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
        logger.error(f"Semantic retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Semantic retrieval failed")


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

@router.post("/directory-search", response_model=RetrievalResponse, summary="Search documents in a directory")
async def retrieve_directory_chunks(
    query: str = Query(..., description="Query text"),
    directory_path: str = Query("", description="Directory path relative to knowledge_base root"),
    limit: int = Query(5, ge=1, le=100, description="Maximum chunks to retrieve"),
    threshold: float = Query(0.3, ge=0.0, le=1.0, description="Minimum relevance score"),
    retriever: DocumentRetriever = Depends(get_document_retriever)
) -> RetrievalResponse:
    """
    Retrieve document chunks from files in a specific directory.
    
    Only documents whose file_path starts with the specified directory_path
    will be included in the search results.
    
    Args:
        query: Query text to search for
        directory_path: Directory path (relative to knowledge_base root)
        limit: Maximum number of chunks to return
        threshold: Minimum similarity score (0-1)
        retriever: DocumentRetriever instance
        
    Returns:
        RetrievalResponse with chunks from specified directory
        
    Raises:
        HTTPException: 404 if no documents found in directory
    """
    try:
        # Get all chunks for the query first
        all_chunks = retriever.retrieve(
            query=query,
            limit=limit * 3,  # Get more to filter
            score_threshold=threshold * 0.8,  # Slightly lower threshold to get more candidates
            include_metadata=True,
        )
        
        if not all_chunks:
            raise HTTPException(
                status_code=404,
                detail=f"No documents found matching query in directory: {directory_path or 'root'}"
            )
        
        # Filter chunks by directory path
        filtered_chunks = []
        for chunk in all_chunks:
            # Check if the document's file_path starts with the target directory
            file_path = chunk.get("metadata", {}).get("file_path", "")
            # Normalize file_path to forward slashes for cross-platform compatibility
            file_path = file_path.replace("\\", "/") if file_path else ""
            
            # Normalize paths for comparison
            target_dir = directory_path.rstrip("/").rstrip("\\").replace("\\", "/") if directory_path else ""
            
            # Check if file is in the directory
            if target_dir == "":
                # Root directory - include all files with no subdirectory prefix
                if "/" not in file_path:
                    filtered_chunks.append(chunk)
            else:
                # Check if file_path starts with directory
                if file_path.startswith(target_dir + "/") or file_path == target_dir:
                    filtered_chunks.append(chunk)
        
        # Sort by score and limit
        filtered_chunks = sorted(
            filtered_chunks,
            key=lambda x: x.get("score", 0),
            reverse=True
        )[:limit]
        
        if not filtered_chunks:
            raise HTTPException(
                status_code=404,
                detail=f"No documents found in directory: {directory_path or 'root'}"
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
            for chunk in filtered_chunks
        ]
        
        # Build context string
        context = retriever.build_context(filtered_chunks, include_sources=True)
        
        return RetrievalResponse(
            query=query,
            chunks=retrieval_chunks,
            total=len(retrieval_chunks),
            context=context
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Directory retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Directory retrieval failed")

@router.post("/search-with-auto", response_model=RetrievalResponse, summary="Retrieve with auto-search fallback")
async def retrieve_with_auto_search(
    query: str = Query(..., description="Query text to search for"),
    limit: int = Query(5, description="Maximum number of chunks to return"),
    threshold: float = Query(0.3, description="Minimum similarity score (0-1)"),
    enable_auto_search: bool = Query(True, description="Enable auto-search fallback"),
    folder_path: Optional[str] = Query(None, description="Folder path for scoped search"),
    retriever: DocumentRetriever = Depends(get_document_retriever)
) -> RetrievalResponse:
    """
    Retrieve document chunks with automatic web search fallback.
    
    If no results are found in the vector database and auto-search is enabled,
    this endpoint will automatically:
    1. Search Google using SerpAPI
    2. Scrape top 3 results
    3. Save to knowledge_base for auto-ingestion
    4. Return job IDs for tracking
    
    Args:
        query: Query text to search for
        limit: Maximum number of chunks to return
        threshold: Minimum similarity score (0-1)
        enable_auto_search: Whether to trigger auto-search on no results
        retriever: DocumentRetriever instance
        
    Returns:
        RetrievalResponse with chunks or auto-search info
    """
    try:
        # First, try normal retrieval
        chunks = retriever.retrieve(
            query=query,
            limit=limit,
            score_threshold=threshold,
            include_metadata=True,
        )
        
        # If we have results, return them
        if chunks:
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
        
        # No results found - trigger auto-search if enabled
        if enable_auto_search:
            try:
                from settings import settings
                from search.auto_search import AutoSearchService
                
                # Check if SerpAPI is enabled
                if not settings.SERPAPI_ENABLED or not settings.SERPAPI_KEY:
                    logger.warning("[AUTO-SEARCH] SerpAPI not enabled or no API key configured")
                    return RetrievalResponse(
                        query=query,
                        chunks=[],
                        total=0,
                        context="",
                        auto_search_triggered=False,
                        auto_search_message="Auto-search not available (SerpAPI not configured)"
                    )
                
                logger.info(f"[AUTO-SEARCH] No results found for query: {query}. Triggering auto-search...")
                
                # Initialize auto-search service
                auto_search = AutoSearchService(settings.SERPAPI_KEY)
                
                # Search and scrape
                result = await auto_search.search_and_scrape(
                    query=query,
                    max_urls=settings.SERPAPI_MAX_RESULTS,
                    folder_path=folder_path
                )
                
                if result["success"]:
                    return RetrievalResponse(
                        query=query,
                        chunks=[],
                        total=0,
                        context="",
                        auto_search_triggered=True,
                        auto_search_job_ids=result["job_ids"],
                        auto_search_urls=result["urls"],
                        auto_search_message=f"No results found. Searching the web and scraping {len(result['urls'])} websites. Check back in 30-60 seconds."
                    )
                else:
                    return RetrievalResponse(
                        query=query,
                        chunks=[],
                        total=0,
                        context="",
                        auto_search_triggered=False,
                        auto_search_message=f"Auto-search failed: {result['message']}"
                    )
            
            except Exception as e:
                logger.error(f"[AUTO-SEARCH] Error: {e}", exc_info=True)
                return RetrievalResponse(
                    query=query,
                    chunks=[],
                    total=0,
                    context="",
                    auto_search_triggered=False,
                    auto_search_message=f"Auto-search error: {str(e)}"
                )
        
        # Auto-search disabled, return empty results
        return RetrievalResponse(
            query=query,
            chunks=[],
            total=0,
            context=""
        )
    
    except Exception as e:
        logger.error(f"Retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Retrieval failed")
