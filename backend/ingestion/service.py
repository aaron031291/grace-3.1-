"""
Text ingestion service for processing documents and storing embeddings.
Handles chunking, embedding generation, and vector storage.
"""

import hashlib
import logging
import json
import re
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime
import numpy as np

from embedding.embedder import EmbeddingModel
from vector_db.client import get_qdrant_client
from confidence_scorer import ConfidenceScorer
from database import session as db_session
from database.session import initialize_session_factory
from models.database_models import Document, DocumentChunk

logger = logging.getLogger(__name__)


class TextChunker:
    """Handles text chunking with semantic and structure-aware strategies."""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 100,
        embedding_model: Optional[EmbeddingModel] = None,
        use_semantic_chunking: bool = True,
        similarity_threshold: float = 0.5,
    ):
        """
        Initialize text chunker with semantic awareness.
        
        Args:
            chunk_size: Target number of characters per chunk
            chunk_overlap: Number of overlapping characters between chunks
            embedding_model: Optional EmbeddingModel for semantic chunking
            use_semantic_chunking: Whether to use embedding-based semantic chunking
            similarity_threshold: Similarity threshold for semantic boundaries (0.0-1.0)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        self.use_semantic_chunking = use_semantic_chunking and embedding_model is not None
        self.similarity_threshold = similarity_threshold
    
    def _split_by_structure(self, text: str) -> List[str]:
        """
        Split text by structural elements (paragraphs, sentences).
        
        Args:
            text: Text to split
            
        Returns:
            List of structural segments
        """
        # First split by double newlines (paragraphs)
        paragraphs = text.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        # If paragraphs are too large, split by sentences
        segments = []
        for paragraph in paragraphs:
            if len(paragraph) > self.chunk_size:
                # Split by sentence-ending punctuation
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                segments.extend([s.strip() for s in sentences if s.strip()])
            else:
                segments.append(paragraph)
        
        return segments
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(dot_product / (norm_a * norm_b))
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def _semantic_chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        Perform semantic chunking using embeddings.
        
        Splits text into chunks based on semantic boundaries detected
        by comparing embeddings of adjacent segments.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of semantic chunks with metadata
        """
        try:
            # First pass: split by structure
            segments = self._split_by_structure(text)
            
            if not segments:
                return [{
                    "text": text,
                    "char_start": 0,
                    "char_end": len(text),
                }]
            
            # Generate embeddings for all segments
            segment_texts = [s for s in segments if len(s.strip()) > 10]  # Skip very short segments
            if not segment_texts:
                return [{
                    "text": text,
                    "char_start": 0,
                    "char_end": len(text),
                }]
            
            embeddings = self.embedding_model.embed_text(segment_texts)
            embeddings = np.array(embeddings)
            
            # Group segments into chunks based on semantic similarity
            chunks = []
            current_chunk = []
            current_length = 0
            current_char_start = 0
            
            for i, segment in enumerate(segment_texts):
                current_chunk.append(segment)
                current_length += len(segment)
                
                # Check if we should end the chunk
                should_split = False
                
                # Condition 1: Size-based split
                if current_length >= self.chunk_size:
                    should_split = True
                
                # Condition 2: Semantic boundary detected
                if (i < len(segment_texts) - 1 and 
                    current_length > self.chunk_size // 2):
                    similarity = self._cosine_similarity(
                        embeddings[i],
                        embeddings[i + 1]
                    )
                    if similarity < self.similarity_threshold:
                        should_split = True
                
                if should_split or i == len(segment_texts) - 1:
                    chunk_text = " ".join(current_chunk)
                    chunk_char_end = current_char_start + len(chunk_text)
                    
                    chunks.append({
                        "text": chunk_text,
                        "char_start": current_char_start,
                        "char_end": chunk_char_end,
                    })
                    
                    # Prepare for next chunk with overlap
                    if i < len(segment_texts) - 1:
                        # Calculate overlap from end of current chunk
                        overlap_text = chunk_text[-self.chunk_overlap:] if len(chunk_text) > self.chunk_overlap else chunk_text
                        current_chunk = [overlap_text]
                        current_length = len(overlap_text)
                        current_char_start = chunk_char_end - self.chunk_overlap
                    else:
                        current_chunk = []
                        current_length = 0
            
            logger.info(f"[CHUNKING] Semantic chunking produced {len(chunks)} chunks from {len(segments)} segments")
            return chunks
        
        except Exception as e:
            logger.warning(f"Semantic chunking failed, falling back to simple chunking: {e}")
            return self._simple_chunk(text)
    
    def _simple_chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        Simple character-based chunking with overlap (fallback).
        
        Args:
            text: Text to chunk
            
        Returns:
            List of chunks
        """
        chunks = []
        
        for start in range(0, len(text), self.chunk_size - self.chunk_overlap):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            
            if chunk_text.strip():  # Skip empty chunks
                chunks.append({
                    "text": chunk_text,
                    "char_start": start,
                    "char_end": end,
                })
        
        logger.info(f"[CHUNKING] Simple chunking produced {len(chunks)} chunks")
        return chunks

    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into chunks using the configured strategy.
        
        Uses embedding-based semantic chunking if available,
        falls back to simple character-based chunking otherwise.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of chunk dictionaries with content and position info
        """
        if self.use_semantic_chunking:
            logger.info("[CHUNKING] Using embedding-based semantic chunking")
            return self._semantic_chunk(text)
        else:
            logger.info("[CHUNKING] Using simple character-based chunking")
            return self._simple_chunk(text)



class TextIngestionService:
    """Service for ingesting text documents into vector database."""
    
    def __init__(
        self,
        collection_name: str = "documents",
        chunk_size: int = 512,
        chunk_overlap: int = 100,
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
        # Pass embedding model to chunker for semantic chunking
        self.chunker = TextChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_model=embedding_model,
            use_semantic_chunking=False,  # Disable semantic chunking by default for speed (100KB file in 3min -> <1s)
            similarity_threshold=0.5,
        )
        self.embedding_model = embedding_model
        self.qdrant_client = get_qdrant_client()
        
        # Initialize confidence scorer
        self.confidence_scorer = ConfidenceScorer(
            embedding_model=embedding_model,
            qdrant_client=self.qdrant_client,
            collection_name=collection_name,
        )
        
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
    
    def ingest_text_fast(
        self,
        text_content: str,
        filename: str,
        source: str = "upload",
        upload_method: str = "ui-upload",
        source_type: str = "user_generated",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[int], str]:
        """
        Fast ingestion without confidence scoring (for quick uploads).
        
        Args:
            text_content: The text content to ingest
            filename: Name of the file/document
            source: Source of the document
            upload_method: How the document was uploaded
            source_type: Type of source
            description: Optional description
            tags: Optional tags
            metadata: Additional metadata
            
        Returns:
            Tuple of (document_id, status_message)
        """
        logger.info(f"[INGEST_FAST] Starting fast ingestion for: {filename}")
        logger.info(f"[INGEST_FAST] Text content length: {len(text_content)} characters")
        logger.info(f"[INGEST_FAST] Metadata: {metadata}")
        
        db = self._get_db_session()
        logger.info(f"[INGEST_FAST] Got database session")
        
        try:
            # Compute hash for deduplication
            logger.info(f"[INGEST_FAST] Computing content hash...")
            content_hash = self.compute_file_hash(text_content)
            logger.info(f"[INGEST_FAST] Content hash: {content_hash}")
            
            # Check if document already exists
            logger.info(f"[INGEST_FAST] Checking for duplicate documents...")
            existing = db.query(Document).filter(
                Document.content_hash == content_hash
            ).first()
            
            if existing:
                logger.warning(f"[INGEST_FAST] Document with hash {content_hash} already exists (ID: {existing.id})")
                return existing.id, "Document already ingested"
            
            logger.info(f"[INGEST_FAST] No duplicates found, proceeding with ingestion")
            
            # Prepare document metadata (without confidence scoring)
            doc_metadata = {
                "user_metadata": metadata or {},
                "original_source": source,
                "upload_timestamp": datetime.utcnow().isoformat(),
                "source_type": source_type,
            }
            
            # Create document record WITHOUT confidence scores for speed
            logger.info(f"[INGEST_FAST] Creating document record...")
            document = Document(
                filename=filename,
                original_filename=filename,
                source=source,
                upload_method=upload_method,
                description=description,
                tags=json.dumps(tags) if tags else None,
                content_hash=content_hash,
                status="processing",
                extracted_text_length=len(text_content),
                document_metadata=json.dumps(doc_metadata),
                # Default confidence scores (not calculated)
                confidence_score=0.5,
                source_reliability=0.5,
                content_quality=0.5,
                consensus_score=0.5,
                recency_score=0.5,
                confidence_metadata=json.dumps({}),
            )
            db.add(document)
            db.flush()  # Get the ID without committing
            document_id = document.id
            
            logger.info(f"[INGEST_FAST] ✓ Created document record with ID: {document_id}")
            
            # Chunk the text
            logger.info(f"[INGEST_FAST] Chunking text with chunk_size=512, overlap=50...")
            chunks = self.chunker.chunk_text(text_content)
            logger.info(f"[INGEST_FAST] ✓ Chunked text into {len(chunks)} chunks")
            
            # Get document creation date for embedding into chunks
            created_at = document.created_at.isoformat() if document.created_at else datetime.utcnow().isoformat()
            
            # Generate embeddings and store chunks
            vector_id_counter = int(f"{document_id}000")
            vectors_to_upsert = []
            
            logger.info(f"[INGEST_FAST] Starting batch embedding generation for {len(chunks)} chunks...")
            
            if not self.embedding_model:
                logger.error("[INGEST_FAST] Embedding model not available!")
                db.rollback()
                return None, "Embedding model not available"
            
            # OPTIMIZATION: Batch embed all chunks at once instead of one at a time
            # This reduces embedding time from ~16s to ~2-3s for 100KB (234 chunks)
            chunk_texts = [chunk["text"] for chunk in chunks]
            with open("embedding_debug.log", "a") as debug_log:
                debug_log.write(f"{chunk_texts}\n")
            logger.debug(f"[INGEST_FAST] Batch embedding {len(chunk_texts)} texts...")
            
            # Use smaller batch size to avoid CUDA OOM errors
            # Fallback: if CUDA fails, automatically reduce batch size and retry
            all_embeddings = None
            batch_size = 32  # Start with smaller batch size for VRAM-constrained systems
            
            try:
                all_embeddings = self.embedding_model.embed_text(chunk_texts, batch_size=batch_size)
                logger.info(f"[INGEST_FAST] ✓ Generated batch embeddings for all {len(chunks)} chunks (batch_size={batch_size})")
            except RuntimeError as e:
                if "out of memory" in str(e).lower() or "cuda" in str(e).lower():
                    logger.warning(f"[INGEST_FAST] ⚠ CUDA OOM with batch_size={batch_size}, reducing batch size...")
                    # Fallback: Embed in smaller batches
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    
                    all_embeddings = []
                    smaller_batch_size = 4  # Much smaller batch
                    for i in range(0, len(chunk_texts), smaller_batch_size):
                        batch = chunk_texts[i:i+smaller_batch_size]
                        logger.debug(f"[INGEST_FAST] Embedding batch {i//smaller_batch_size + 1}...")
                        batch_embeddings = self.embedding_model.embed_text(batch, batch_size=smaller_batch_size)
                        all_embeddings.extend(batch_embeddings)
                    
                    logger.info(f"[INGEST_FAST] ✓ Generated batch embeddings for all {len(chunks)} chunks (fallback batch_size={smaller_batch_size})")
                else:
                    logger.error(f"[INGEST_FAST] Error during embedding: {e}")
                    db.rollback()
                    return None, f"Embedding generation failed: {str(e)}"
            
            # Create vector records and database entries for all chunks
            for chunk_index, chunk in enumerate(chunks):
                chunk_text = chunk["text"]
                embedding_vector = all_embeddings[chunk_index]
                
                # Create vector ID
                vector_id = vector_id_counter + chunk_index
                
                # Prepare chunk metadata with filename, source, and creation date
                chunk_metadata = {
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "filename": filename,
                    "source": source,
                    "confidence_score": 0.5,
                    "created_at": created_at,
                }
                
                # Format as tuple for upsert_vectors
                vectors_to_upsert.append((
                    vector_id,
                    embedding_vector,
                    chunk_metadata,
                ))
                
                # Create database record for chunk
                chunk_record = DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk_index,
                    text_content=chunk_text,
                    embedding_vector_id=str(vector_id),
                    embedding_model="qwen_4b",
                    confidence_score=0.5,
                    chunk_metadata=json.dumps({
                        "source": source,
                        "filename": filename,
                        "created_at": created_at,
                    }),
                )
                db.add(chunk_record)
            
            # Store vectors in Qdrant in batches to avoid timeout
            logger.info(f"[INGEST_FAST] Storing {len(vectors_to_upsert)} vectors in Qdrant...")
            if vectors_to_upsert:
                # OPTIMIZATION: Batch vectors into chunks of 100 to avoid timeouts on large files
                batch_size = 100
                for batch_start in range(0, len(vectors_to_upsert), batch_size):
                    batch_end = min(batch_start + batch_size, len(vectors_to_upsert))
                    batch = vectors_to_upsert[batch_start:batch_end]
                    
                    logger.debug(f"[INGEST_FAST] Upserting batch {batch_start}-{batch_end} ({len(batch)} vectors)...")
                    success = self.qdrant_client.upsert_vectors(
                        collection_name=self.collection_name,
                        vectors=batch,
                    )
                    
                    if not success:
                        logger.error(f"[INGEST_FAST] Failed to store embeddings batch {batch_start}-{batch_end}")
                        db.rollback()
                        return None, f"Failed to store embeddings (batch {batch_start}-{batch_end})"
                
                logger.info(f"[INGEST_FAST] ✓ Successfully stored {len(vectors_to_upsert)} vectors in Qdrant")
            
            # Update document status to completed
            document.status = "completed"
            document.total_chunks = len(chunks)
            
            # Commit transaction
            logger.info(f"[INGEST_FAST] Committing database transaction...")
            db.commit()
            logger.info(f"[INGEST_FAST] ✓✓✓ INGESTION COMPLETE ✓✓✓")
            logger.info(f"[INGEST_FAST] Document {document_id}: {filename}")
            logger.info(f"[INGEST_FAST]   - {len(chunks)} chunks")
            logger.info(f"[INGEST_FAST]   - {len(text_content)} characters")
            logger.info(f"[INGEST_FAST]   - Stored in PostgreSQL + Qdrant")
            
            return document_id, "Document ingested successfully"
        
        except Exception as e:
            logger.error(f"[INGEST_FAST] ✗✗✗ ERROR DURING INGESTION ✗✗✗", exc_info=True)
            logger.error(f"[INGEST_FAST] Error details: {str(e)}")
            db.rollback()
            return None, f"Ingestion failed: {str(e)}"
        finally:
            db.close()
            logger.info(f"[INGEST_FAST] Database session closed")
    
    def ingest_text(
        self,
        text_content: str,
        filename: str,
        source: str = "upload",
        upload_method: str = "ui-upload",
        source_type: str = "user_generated",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[int], str]:
        """
        Ingest text content into database and vector store with automatic confidence scoring.
        
        Confidence score is automatically calculated based on:
        - Source type/reliability
        - Content quality indicators
        - Consensus with existing knowledge
        - Recency of content
        
        Args:
            text_content: The text content to ingest
            filename: Name of the file/document
            source: Source of the document (e.g., 'upload', 'url', 'api')
            upload_method: How the document was uploaded (ui-upload, ui-paste, api, etc.)
            source_type: Type of source for reliability calculation (official_docs, academic_paper, verified_tutorial, trusted_blog, community_qa, user_generated, unverified)
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
            
            # Calculate document-level confidence score
            doc_confidence_data = self.confidence_scorer.calculate_confidence_score(
                text_content=text_content,
                source_type=source_type,
                created_at=datetime.utcnow(),
            )
            
            # Prepare document metadata
            doc_metadata = {
                "user_metadata": metadata or {},
                "original_source": source,
                "upload_timestamp": datetime.utcnow().isoformat(),
                "source_type": source_type,
            }
            
            # Create document record with auto-calculated confidence scores
            document = Document(
                filename=filename,
                original_filename=filename,
                source=source,
                upload_method=upload_method,
                description=description,
                tags=json.dumps(tags) if tags else None,
                content_hash=content_hash,
                status="processing",
                extracted_text_length=len(text_content),
                document_metadata=json.dumps(doc_metadata),
                # Confidence scoring fields
                confidence_score=doc_confidence_data["confidence_score"],
                source_reliability=doc_confidence_data["source_reliability"],
                content_quality=doc_confidence_data["content_quality"],
                consensus_score=doc_confidence_data["consensus_score"],
                recency_score=doc_confidence_data["recency"],
                confidence_metadata=json.dumps(doc_confidence_data),
            )
            db.add(document)
            db.flush()  # Get the ID without committing
            document_id = document.id
            
            # Log contradiction detection at document level
            if doc_confidence_data.get("contradictions_detected"):
                logger.warning(
                    f"Document {document_id} ({filename}): "
                    f"Found {doc_confidence_data.get('contradiction_count', 0)} semantic contradictions. "
                    f"Confidence score reduced accordingly."
                )
            
            logger.info(
                f"Created document record: {document_id} ({filename}), "
                f"upload_method={upload_method}, source_type={source_type}, "
                f"confidence_score={doc_confidence_data['confidence_score']:.3f}"
            )
            
            # Chunk the text
            chunks = self.chunker.chunk_text(text_content)
            logger.info(f"Chunked text into {len(chunks)} chunks")
            
            # Generate embeddings and store chunks
            vector_id_counter = int(f"{document_id}000")  # Create unique IDs
            vectors_to_upsert = []
            chunk_confidence_scores = []
            
            # Collect all chunk texts for consensus calculation
            all_chunk_texts = [chunk["text"] for chunk in chunks]
            
            for chunk_index, chunk in enumerate(chunks):
                chunk_text = chunk["text"]
                
                # Calculate chunk-level confidence score
                chunk_confidence_data = self.confidence_scorer.calculate_confidence_score(
                    text_content=chunk_text,
                    source_type=source_type,
                    created_at=datetime.utcnow(),
                    existing_chunks=all_chunk_texts[:chunk_index] + all_chunk_texts[chunk_index+1:],  # Exclude current chunk
                )
                
                chunk_confidence_scores.append(chunk_confidence_data["confidence_score"])
                
                # Log chunk-level contradictions
                if chunk_confidence_data.get("contradictions_detected"):
                    logger.debug(
                        f"Chunk {chunk_index} in document {document_id}: "
                        f"Found {chunk_confidence_data.get('contradiction_count', 0)} semantic contradictions"
                    )
                
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
                
                # Prepare chunk metadata for Qdrant payload
                chunk_metadata = {
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "filename": filename,
                    "char_start": chunk["char_start"],
                    "char_end": chunk["char_end"],
                    "text": chunk_text,  # Include text for retrieval and contradiction detection
                    "confidence_score": chunk_confidence_data["confidence_score"],  # Trust score for weighted contradictions
                    **(metadata or {})
                }
                
                # Create chunk record with confidence scores
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
                    # Confidence scoring fields
                    confidence_score=chunk_confidence_data["confidence_score"],
                    consensus_similarity_scores=json.dumps(chunk_confidence_data.get("similarity_scores", [])),
                )
                db.add(doc_chunk)
                
                # Prepare vector for Qdrant
                vectors_to_upsert.append((
                    vector_id,
                    embedding_vector,
                    chunk_metadata,
                ))
            
            logger.info(
                f"Calculated confidence scores for {len(chunks)} chunks. "
                f"Average: {np.mean(chunk_confidence_scores):.3f}, "
                f"Min: {np.min(chunk_confidence_scores):.3f}, "
                f"Max: {np.max(chunk_confidence_scores):.3f}"
            )
            
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
        Get document information and chunk list with confidence scores.
        
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
                "upload_method": document.upload_method,
                "confidence_score": document.confidence_score,
                "source_reliability": document.source_reliability,
                "content_quality": document.content_quality,
                "consensus_score": document.consensus_score,
                "recency_score": document.recency_score,
                "description": document.description,
                "tags": json.loads(document.tags) if document.tags else None,
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
                        "confidence_score": c.confidence_score,
                        "consensus_similarities": json.loads(c.consensus_similarity_scores) if c.consensus_similarity_scores else [],
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
                    "confidence_score": doc.confidence_score,
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
