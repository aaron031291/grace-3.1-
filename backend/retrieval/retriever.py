"""
Document retriever module for RAG (Retrieval-Augmented Generation).
Retrieves relevant document chunks based on semantic similarity to queries.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from embedding.embedder import EmbeddingModel
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
        score_threshold: float = 0.3,
        include_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks for a query.
        
        Args:
            query: Query text to search for
            limit: Maximum number of chunks to retrieve
            score_threshold: Minimum similarity score (0-1)
            include_metadata: Whether to include chunk metadata
            
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
            
            # Search in Qdrant
            search_results = self.qdrant_client.search_vectors(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
            )
            
            if not search_results:
                logger.debug(f"No results found for query: {query}")
                return []
            
            # Enrich results with database information
            db = self._get_db_session()
            try:
                enriched_results = []
                for result in search_results:
                    chunk = db.query(DocumentChunk).filter(
                        DocumentChunk.embedding_vector_id == str(result["id"])
                    ).first()
                    
                    if chunk:
                        document = db.query(Document).filter(
                            Document.id == chunk.document_id
                        ).first()
                        
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
                return enriched_results
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Retrieval error for query '{query}': {e}", exc_info=True)
            raise  # Re-raise so caller knows about the failure
    
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
            if hasattr(self.embedding_model, 'unload_model'):
                self.embedding_model.unload_model()
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
