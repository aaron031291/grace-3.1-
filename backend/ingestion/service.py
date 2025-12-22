"""
Text ingestion service for processing documents and storing embeddings.
Handles chunking, embedding generation, and vector storage.
"""

import hashlib
import logging
import json
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

from embedding.embedder import EmbeddingModel
from vector_db.client import get_qdrant_client
from database import session as db_session
from database.session import initialize_session_factory
from models.database_models import Document, DocumentChunk

logger = logging.getLogger(__name__)


class TextChunker:
    """Handles text chunking with configurable strategies."""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ):
        """
        Initialize text chunker.
        
        Args:
            chunk_size: Number of characters per chunk
            chunk_overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into chunks with overlap.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of chunk dictionaries with content and position info
        """
        chunks = []
        
        # Simple character-based chunking with overlap
        for start in range(0, len(text), self.chunk_size - self.chunk_overlap):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            
            if chunk_text.strip():  # Skip empty chunks
                chunks.append({
                    "text": chunk_text,
                    "char_start": start,
                    "char_end": end,
                })
        
        return chunks


class TextIngestionService:
    """Service for ingesting text documents into vector database."""
    
    def __init__(
        self,
        collection_name: str = "documents",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        embedding_model: Optional[EmbeddingModel] = None,
    ):
        """
        Initialize ingestion service.
        
        Args:
            collection_name: Name of Qdrant collection for documents
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            embedding_model: EmbeddingModel instance for generating embeddings
        """
        self.collection_name = collection_name
        self.chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.embedding_model = embedding_model
        self.qdrant_client = get_qdrant_client()
        
        # Initialize Qdrant collection if not exists
        if self.embedding_model:
            embedding_dim = self.embedding_model.get_embedding_dimension()
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vector_size=embedding_dim,
                distance_metric="cosine",
            )
    
    @staticmethod
    def _get_db_session():
        """
        Get a database session, initializing the session factory if needed.
        
        Returns:
            SQLAlchemy Session instance
        """
        if db_session.SessionLocal is None:
            initialize_session_factory()
        return db_session.SessionLocal()
    
    @staticmethod
    def compute_file_hash(content: str) -> str:
        """
        Compute SHA256 hash of content.
        
        Args:
            content: Text content
            
        Returns:
            Hex digest of SHA256 hash
        """
        return hashlib.sha256(content.encode()).hexdigest()
    
    def ingest_text(
        self,
        text_content: str,
        filename: str,
        source: str = "upload",
        upload_method: str = "ui-upload",
        trust_score: float = 0.0,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[int], str]:
        """
        Ingest text content into database and vector store.
        
        Args:
            text_content: The text content to ingest
            filename: Name of the file/document
            source: Source of the document (e.g., 'upload', 'url', 'api')
            upload_method: How the document was uploaded (ui-upload, ui-paste, api, etc.)
            trust_score: Trustworthiness score of the source (0.0-1.0)
            description: Optional description of the document
            tags: Optional list of tags for categorization
            metadata: Additional metadata dictionary
            
        Returns:
            Tuple of (document_id, status_message)
        """
        db = self._get_db_session()
        
        try:
            # Compute hash for deduplication
            content_hash = self.compute_file_hash(text_content)
            
            # Check if document already exists
            existing = db.query(Document).filter(
                Document.content_hash == content_hash
            ).first()
            
            if existing:
                logger.warning(f"Document with hash {content_hash} already exists")
                return existing.id, "Document already ingested"
            
            # Prepare document metadata
            doc_metadata = {
                "user_metadata": metadata or {},
                "original_source": source,
                "upload_timestamp": datetime.utcnow().isoformat(),
            }
            
            # Create document record
            document = Document(
                filename=filename,
                original_filename=filename,
                source=source,
                upload_method=upload_method,
                trust_score=min(max(trust_score, 0.0), 1.0),  # Clamp between 0.0 and 1.0
                description=description,
                tags=json.dumps(tags) if tags else None,
                content_hash=content_hash,
                status="processing",
                extracted_text_length=len(text_content),
                document_metadata=json.dumps(doc_metadata),
            )
            db.add(document)
            db.flush()  # Get the ID without committing
            document_id = document.id
            
            logger.info(f"Created document record: {document_id} ({filename}), upload_method={upload_method}, trust_score={trust_score}")
            
            # Chunk the text
            chunks = self.chunker.chunk_text(text_content)
            logger.info(f"Chunked text into {len(chunks)} chunks")
            
            # Generate embeddings and store chunks
            vector_id_counter = int(f"{document_id}000")  # Create unique IDs
            vectors_to_upsert = []
            
            for chunk_index, chunk in enumerate(chunks):
                chunk_text = chunk["text"]
                
                # Generate embedding
                if self.embedding_model:
                    embeddings = self.embedding_model.embed_text([chunk_text])
                    embedding_vector = embeddings[0]
                else:
                    logger.error("Embedding model not available")
                    db.rollback()
                    return None, "Embedding model not available"
                
                # Create vector ID (unique across system)
                vector_id = vector_id_counter + chunk_index
                
                # Prepare chunk metadata
                chunk_metadata = {
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "filename": filename,
                    "char_start": chunk["char_start"],
                    "char_end": chunk["char_end"],
                    **(metadata or {})
                }
                
                # Create chunk record
                doc_chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk_index,
                    text_content=chunk_text,
                    token_count=len(chunk_text.split()),  # Rough estimate
                    embedding_vector_id=str(vector_id),
                    embedding_model="qwen_4b",
                    char_start=chunk["char_start"],
                    char_end=chunk["char_end"],
                    chunk_metadata=json.dumps(chunk_metadata),
                )
                db.add(doc_chunk)
                
                # Prepare vector for Qdrant
                vectors_to_upsert.append((
                    vector_id,
                    embedding_vector,
                    chunk_metadata,
                ))
            
            # Flush chunk inserts
            db.flush()
            
            # Upsert vectors to Qdrant
            if vectors_to_upsert:
                success = self.qdrant_client.upsert_vectors(
                    collection_name=self.collection_name,
                    vectors=vectors_to_upsert,
                )
                
                if not success:
                    logger.error("Failed to upsert vectors to Qdrant")
                    db.rollback()
                    return None, "Failed to store embeddings"
            
            # Update document status
            document.status = "completed"
            document.total_chunks = len(chunks)
            db.commit()
            
            logger.info(f"✓ Successfully ingested document: {document_id}")
            return document_id, "Document ingested successfully"
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error during ingestion: {e}", exc_info=True)
            return None, f"Ingestion failed: {str(e)}"
        
        finally:
            db.close()
    
    def search_documents(
        self,
        query_text: str,
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar document chunks.
        
        Args:
            query_text: Query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            
        Returns:
            List of matching chunks with metadata
        """
        try:
            if not self.embedding_model:
                logger.error("Embedding model not available")
                return []
            
            # Generate embedding for query
            query_embedding = self.embedding_model.embed_text([query_text])[0]
            
            # Search in Qdrant
            results = self.qdrant_client.search_vectors(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
            )
            
            db = self._get_db_session()
            
            try:
                # Enrich results with chunk content
                enriched_results = []
                for result in results:
                    chunk = db.query(DocumentChunk).filter(
                        DocumentChunk.embedding_vector_id == str(result["id"])
                    ).first()
                    
                    if chunk:
                        enriched_results.append({
                            "vector_id": result["id"],
                            "score": result["score"],
                            "chunk_id": chunk.id,
                            "document_id": chunk.document_id,
                            "chunk_index": chunk.chunk_index,
                            "text": chunk.text_content,
                            "metadata": json.loads(chunk.chunk_metadata) if chunk.chunk_metadata else {},
                        })
                
                return enriched_results
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            return []
    
    def get_document_info(self, document_id: int) -> Optional[Dict[str, Any]]:
        """
        Get document information and chunk list.
        
        Args:
            document_id: ID of the document
            
        Returns:
            Dictionary with document info or None if not found
        """
        db = self._get_db_session()
        
        try:
            document = db.query(Document).filter(
                Document.id == document_id
            ).first()
            
            if not document:
                return None
            
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).order_by(DocumentChunk.chunk_index).all()
            
            return {
                "id": document.id,
                "filename": document.filename,
                "source": document.source,
                "status": document.status,
                "total_chunks": document.total_chunks,
                "text_length": document.extracted_text_length,
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat(),
                "chunks": [
                    {
                        "id": c.id,
                        "index": c.chunk_index,
                        "text_length": len(c.text_content),
                        "vector_id": c.embedding_vector_id,
                    }
                    for c in chunks
                ]
            }
        
        finally:
            db.close()
    
    def list_documents(
        self,
        status: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List documents with optional filtering.
        
        Args:
            status: Filter by status (pending, processing, completed, failed)
            source: Filter by source
            limit: Number of results
            offset: Result offset
            
        Returns:
            List of document summaries
        """
        db = self._get_db_session()
        try:
            query = db.query(Document)
            
            if status:
                query = query.filter(Document.status == status)
            
            if source:
                query = query.filter(Document.source == source)
            
            documents = query.order_by(
                Document.created_at.desc()
            ).limit(limit).offset(offset).all()
            
            return [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "source": doc.source,
                    "upload_method": doc.upload_method,
                    "trust_score": doc.trust_score,
                    "description": doc.description,
                    "tags": json.loads(doc.tags) if doc.tags else None,
                    "status": doc.status,
                    "total_chunks": doc.total_chunks,
                    "text_length": doc.extracted_text_length,
                    "created_at": doc.created_at.isoformat(),
                    "updated_at": doc.updated_at.isoformat(),
                }
                for doc in documents
            ]
        finally:
            db.close()
    
    def delete_document(self, document_id: int) -> Tuple[bool, str]:
        """
        Delete a document and its chunks.
        
        Args:
            document_id: ID of document to delete
            
        Returns:
            Tuple of (success, message)
        """
        db = self._get_db_session()
        
        try:
            document = db.query(Document).filter(
                Document.id == document_id
            ).first()
            
            if not document:
                return False, "Document not found"
            
            # Get all chunks to delete from Qdrant
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).all()
            
            vector_ids = [int(c.embedding_vector_id) for c in chunks if c.embedding_vector_id]
            
            # Delete vectors from Qdrant
            if vector_ids:
                self.qdrant_client.delete_vectors(
                    collection_name=self.collection_name,
                    vector_ids=vector_ids,
                )
            
            # Delete from database
            db.delete(document)
            db.commit()
            
            logger.info(f"✓ Deleted document: {document_id}")
            return True, "Document deleted successfully"
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting document: {e}")
            return False, f"Deletion failed: {str(e)}"
        
        finally:
            db.close()
