"""
Document retriever module for RAG (Retrieval-Augmented Generation).
Retrieves relevant document chunks based on semantic similarity to queries.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from embedding import EmbeddingModel
from vector_db.client import get_qdrant_client
from database import session as db_session
from models.database_models import Document, DocumentChunk

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Retrieves relevant document chunks for query context."""
    
    def __init__(
        self,
        collection_name: str = "documents",
        embedding_model: Optional[EmbeddingModel] = None,
    ):
        """
        Initialize document retriever.
        
        Args:
            collection_name: Name of Qdrant collection
            embedding_model: EmbeddingModel instance for generating query embeddings
                            If None, will NOT create a new instance (must be provided)
        """
        self.collection_name = collection_name
        if embedding_model is None:
            raise ValueError("embedding_model is required - must be provided as an instance")
        self.embedding_model = embedding_model
        self.qdrant_client = get_qdrant_client()
    
    def retrieve(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.5,
        include_metadata: bool = True,
        filter_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks for a query.
        
        Args:
            query: Query text to search for
            limit: Maximum number of chunks to retrieve
            score_threshold: Minimum similarity score (0-1)
            include_metadata: Whether to include chunk metadata
            filter_path: Optional path prefix to filter results (e.g., "forensic/auto_search/")
            
        Returns:
            List of relevant chunks with scores and metadata
            
        Raises:
            Exception: If embedding generation fails
        """
        try:
            if not query or not query.strip():
                logger.warning("Empty query provided")
                return []
            
            # Generate embedding for query with retry logic
            try:
                query_embedding = self.embedding_model.embed_text([query])[0]
            except RuntimeError as e:
                # Check if it's a CUDA out of memory error
                if "CUDA out of memory" in str(e) or "out of memory" in str(e).lower():
                    logger.error(f"CUDA Out of Memory - falling back to CPU inference")
                    # Force switch to CPU
                    self.embedding_model.device = 'cpu'
                    if hasattr(self.embedding_model.model, 'to'):
                        self.embedding_model.model.to('cpu')
                    # Retry with CPU
                    query_embedding = self.embedding_model.embed_text([query])[0]
                else:
                    raise
            
            # Build Qdrant filter if path is specified
            qdrant_filter = None
            if filter_path:
                from qdrant_client.models import Filter, FieldCondition, MatchText
                qdrant_filter = Filter(
                    must=[
                        FieldCondition(
                            key="file_path",
                            match=MatchText(text=filter_path)
                        )
                    ]
                )
                logger.debug(f"Applying path filter: {filter_path}")
            
            # Search in Qdrant
            search_results = self.qdrant_client.search_vectors(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=qdrant_filter,
            )
            
            if not search_results:
                logger.debug(f"No results found for query: {query}")
                return []
            
            # Enrich results with database information (OPTIMIZED: Single JOIN query)
            db = self._get_db_session()
            try:
                # Extract all vector IDs from search results
                vector_ids = [str(result["id"]) for result in search_results]

                # Single query with JOIN to get chunks and documents together
                chunks_with_docs = db.query(DocumentChunk, Document).outerjoin(
                    Document, DocumentChunk.document_id == Document.id
                ).filter(
                    DocumentChunk.embedding_vector_id.in_(vector_ids)
                ).all()

                # Build lookup map for fast access
                chunk_map = {
                    chunk.embedding_vector_id: (chunk, doc)
                    for chunk, doc in chunks_with_docs
                }

                # Preserve original order from search results
                enriched_results = []
                for result in search_results:
                    vector_id = str(result["id"])

                    if vector_id in chunk_map:
                        chunk, document = chunk_map[vector_id]

                        result_dict = {
                            "vector_id": result["id"],
                            "score": result["score"],
                            "chunk_id": chunk.id,
                            "document_id": chunk.document_id,
                            "chunk_index": chunk.chunk_index,
                            "text": chunk.text_content,
                            "confidence_score": chunk.confidence_score,
                        }

                        if include_metadata:
                            result_dict["metadata"] = {
                                "document_id": chunk.document_id,
                                "filename": document.filename if document else "Unknown",
                                "file_path": document.file_path if document else None,
                                "source": document.source if document else "Unknown",
                                "upload_method": document.upload_method if document else "Unknown",
                                "chunk_index": chunk.chunk_index,
                                "char_start": chunk.char_start,
                                "char_end": chunk.char_end,
                                "confidence_score": chunk.confidence_score,
                                "document_confidence_score": document.confidence_score if document else 0.5,
                                "created_at": document.created_at.isoformat() if document and document.created_at else None,
                                "description": document.description if document else None,
                            }

                        enriched_results.append(result_dict)
                
                logger.info(f"Retrieved {len(enriched_results)} chunks for query: {query}")

                try:
                    from api._genesis_tracker import track
                    track(
                        key_type="ai_response",
                        what=f"RAG retrieval: {len(enriched_results)} chunks for '{query[:60]}'",
                        who="retriever.retrieve",
                        how="qdrant_vector_search",
                        input_data={"query": query[:200], "limit": limit, "threshold": score_threshold},
                        output_data={"chunks_found": len(enriched_results), "top_score": enriched_results[0]["score"] if enriched_results else 0},
                        tags=["rag", "retrieval", "search"],
                    )
                except Exception:
                    pass

                return enriched_results
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Retrieval error for query '{query}': {e}", exc_info=True)
            try:
                from api._genesis_tracker import track
                track(
                    key_type="error",
                    what=f"RAG retrieval failed: {query[:60]}",
                    who="retriever.retrieve",
                    is_error=True,
                    error_type=type(e).__name__,
                    error_message=str(e)[:200],
                    tags=["rag", "retrieval", "error"],
                )
            except Exception:
                pass
            raise
    
    def retrieve_hybrid(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.3,
        include_metadata: bool = True,
        keyword_weight: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval combining semantic search + keyword matching.
        
        For short queries, keyword matching helps ensure relevant documents.
        For longer queries, semantic search dominates.
        
        Args:
            query: Query text to search for
            limit: Maximum number of chunks to retrieve
            score_threshold: Minimum similarity score (0-1)
            include_metadata: Whether to include chunk metadata
            keyword_weight: Weight for keyword matching (0-1)
            
        Returns:
            List of relevant chunks with combined scores
        """
        try:
            # Get semantic search results first
            semantic_results = self.retrieve(
                query=query,
                limit=limit * 3,  # Get more to re-rank
                score_threshold=0,  # No threshold yet
                include_metadata=include_metadata
            )
            
            if not semantic_results:
                return []
            
            # Extract keywords from query (words > 3 chars, case-insensitive)
            query_keywords = [
                word.lower() for word in query.split() 
                if len(word) > 2
            ]
            
            # Boost scores for documents containing query keywords
            for result in semantic_results:
                chunk_text = result["text"].lower()
                keyword_matches = sum(1 for keyword in query_keywords if keyword in chunk_text)
                
                # Calculate keyword score (0-1)
                if query_keywords:
                    keyword_score = min(1.0, keyword_matches / len(query_keywords))
                else:
                    keyword_score = 0.0
                
                # Combine scores: semantic + keyword boost
                original_score = result["score"]
                combined_score = (original_score * (1 - keyword_weight)) + (keyword_score * keyword_weight)
                result["score"] = combined_score
                result["keyword_matches"] = keyword_matches
            
            # Re-sort by combined score
            semantic_results.sort(key=lambda x: x["score"], reverse=True)
            
            # Apply threshold and limit
            final_results = [
                r for r in semantic_results 
                if r["score"] >= score_threshold
            ][:limit]
            
            logger.info(f"Hybrid retrieval: {len(final_results)} chunks for query: {query}")
            return final_results
        
        except Exception as e:
            logger.error(f"Hybrid retrieval error for query '{query}': {e}", exc_info=True)
            # Fall back to regular retrieve
            return self.retrieve(
                query=query,
                limit=limit,
                score_threshold=score_threshold,
                include_metadata=include_metadata
            )
    
    def retrieve_by_document(
        self,
        document_id: int,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks from a specific document.
        
        Args:
            document_id: ID of the document
            limit: Maximum number of chunks (None for all)
            
        Returns:
            List of chunks from the document
        """
        try:
            db = self._get_db_session()
            try:
                query = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document_id
                ).order_by(DocumentChunk.chunk_index)
                
                if limit:
                    query = query.limit(limit)
                
                chunks = query.all()
                
                if not chunks:
                    logger.debug(f"No chunks found for document {document_id}")
                    return []
                
                document = db.query(Document).filter(
                    Document.id == document_id
                ).first()
                
                return [
                    {
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text_content,
                        "metadata": {
                            "filename": document.filename if document else "Unknown",
                            "source": document.source if document else "Unknown",
                            "char_start": chunk.char_start,
                            "char_end": chunk.char_end,
                        }
                    }
                    for chunk in chunks
                ]
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Error retrieving chunks for document {document_id}: {e}")
            return []
    
    def retrieve_by_source(
        self,
        source: str,
        limit: int = 20,
        include_text: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve chunks from documents with a specific source.
        
        Args:
            source: Source identifier
            limit: Maximum number of chunks
            include_text: Whether to include chunk text
            
        Returns:
            List of chunks from matching documents
        """
        try:
            db = self._get_db_session()
            try:
                # Find documents with matching source
                documents = db.query(Document).filter(
                    Document.source == source
                ).all()
                
                if not documents:
                    logger.debug(f"No documents found with source: {source}")
                    return []
                
                document_ids = [doc.id for doc in documents]
                
                # Get chunks from these documents
                query = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id.in_(document_ids)
                ).order_by(
                    DocumentChunk.document_id,
                    DocumentChunk.chunk_index
                ).limit(limit)
                
                chunks = query.all()
                
                # Map documents by ID for quick lookup
                doc_map = {doc.id: doc for doc in documents}
                
                return [
                    {
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text_content if include_text else None,
                        "metadata": {
                            "filename": doc_map[chunk.document_id].filename,
                            "source": source,
                            "char_start": chunk.char_start,
                            "char_end": chunk.char_end,
                        }
                    }
                    for chunk in chunks
                ]
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Error retrieving chunks by source '{source}': {e}")
            return []
    
    def build_context(
        self,
        chunks: List[Dict[str, Any]],
        max_length: Optional[int] = None,
        include_sources: bool = True,
    ) -> str:
        """
        Build a context string from retrieved chunks.
        
        Args:
            chunks: List of chunk dictionaries from retrieve()
            max_length: Maximum length of context string (None for unlimited)
            include_sources: Whether to include source attribution
            
        Returns:
            Formatted context string suitable for LLM input
        """
        if not chunks:
            return ""
        
        context_parts = []
        total_length = 0
        
        for i, chunk in enumerate(chunks, 1):
            text = chunk.get("text", "")
            if not text:
                continue
            
            # Format chunk with optional source attribution
            if include_sources:
                metadata = chunk.get("metadata", {})
                filename = metadata.get("filename", "Unknown")
                score = chunk.get("score")
                score_str = f" (relevance: {score:.2%})" if score else ""
                header = f"[Document {i}: {filename}{score_str}]\n"
            else:
                header = f"[Document {i}]\n"
            
            formatted_chunk = header + text.strip()
            
            # Check length constraint
            if max_length:
                combined_length = total_length + len(formatted_chunk) + 2
                if combined_length > max_length:
                    logger.debug(
                        f"Context length limit reached. "
                        f"Included {len(context_parts)} out of {len(chunks)} chunks."
                    )
                    break
                total_length = combined_length
            
            context_parts.append(formatted_chunk)
        
        return "\n\n".join(context_parts)
    
    @staticmethod
    def _get_db_session():
        """Get a database session, initializing if needed."""
        from database.session import initialize_session_factory
        
        if db_session.SessionLocal is None:
            initialize_session_factory()
        return db_session.SessionLocal()
    
    def close(self):
        """Clean up resources."""
        try:
            emb = getattr(self, 'embedding_model', None)
            if emb is not None and hasattr(emb, 'unload_model'):
                emb.unload_model()
        except Exception as e:
            logger.warning(f"Error closing retriever: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.close()


def get_retriever(
    collection_name: str = "documents",
    embedding_model: Optional[EmbeddingModel] = None,
) -> DocumentRetriever:
    """
    Factory function to get a DocumentRetriever instance.
    
    Args:
        collection_name: Name of Qdrant collection
        embedding_model: EmbeddingModel instance (optional)
        
    Returns:
        Initialized DocumentRetriever instance
    """
    return DocumentRetriever(
        collection_name=collection_name,
        embedding_model=embedding_model,
    )
