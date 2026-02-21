"""
Fast Ingestion Pipeline

Ingests files FAST using Ollama embeddings (3s per chunk).
Stores in Qdrant (file-based, no server needed) + SQLite.
Knowledge Compiler runs SEPARATELY in background.

Fast path: File → Chunk → Embed (Ollama) → Qdrant + DB
Slow path: Background → Compile chunks → Facts/procedures/rules

User gets RAG search immediately.
Knowledge store fills over time.
"""

import os
import logging
import hashlib
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FastIngestionPipeline:
    """
    Ingest files fast. Embed with Ollama. Store in Qdrant.

    No heavy model loading. No LLM extraction during ingest.
    RAG works immediately after ingestion.
    """

    def __init__(
        self,
        session: Session,
        qdrant_path: str = None,
        collection_name: str = "documents",
        chunk_size: int = 500,
        chunk_overlap: int = 100,
    ):
        self.session = session
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Ollama embedder (fast, already running)
        from embedding.ollama_embedder import get_ollama_embedder
        self.embedder = get_ollama_embedder()

        # Qdrant file-based (no server needed)
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        qdrant_path = qdrant_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "qdrant_storage"
        )
        self.qdrant = QdrantClient(path=qdrant_path)

        # Create collection if needed
        collections = [c.name for c in self.qdrant.get_collections().collections]
        if collection_name not in collections:
            dim = self.embedder.dimension
            self.qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            logger.info(f"[FAST-INGEST] Created Qdrant collection '{collection_name}' (dim={dim})")

        self._stats = {"files": 0, "chunks": 0, "errors": 0}

    def ingest_file(self, file_path: str, domain: str = None) -> Dict[str, Any]:
        """Ingest a single file. Fast."""
        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            if len(content) < 50:
                return {"status": "skipped", "reason": "too short"}

            filename = os.path.basename(file_path)
            content_hash = hashlib.md5(content[:10000].encode()).hexdigest()

            # Store document record
            from models.database_models import Document, DocumentChunk
            
            existing = self.session.query(Document).filter(
                Document.content_hash == content_hash
            ).first()
            
            if existing:
                return {"status": "skipped", "reason": "already ingested"}

            doc = Document(
                filename=filename,
                original_filename=filename,
                source=domain or "knowledge_base",
                upload_method="fast_ingest",
                content_hash=content_hash,
                status="processing",
                extracted_text_length=len(content),
                confidence_score=0.7,
            )
            self.session.add(doc)
            self.session.flush()
            doc_id = doc.id

            # Chunk the text
            chunks = self._chunk_text(content)

            # Embed and store each chunk
            from qdrant_client.models import PointStruct
            points = []
            chunk_records = []

            for i, chunk_text in enumerate(chunks):
                # Embed with Ollama (fast)
                embedding = self.embedder.embed_text([chunk_text])[0]
                
                vector_id = hashlib.md5(f"{content_hash}:{i}".encode()).hexdigest()

                # Qdrant point
                points.append(PointStruct(
                    id=vector_id,
                    vector=embedding,
                    payload={
                        "text": chunk_text[:1000],
                        "document_id": doc_id,
                        "chunk_index": i,
                        "filename": filename,
                        "domain": domain or "general",
                        "file_path": file_path,
                    },
                ))

                # DB chunk record
                chunk_record = DocumentChunk(
                    document_id=doc_id,
                    chunk_index=i,
                    text_content=chunk_text,
                    char_start=0,
                    char_end=len(chunk_text),
                    embedding_vector_id=vector_id,
                    confidence_score=0.7,
                )
                self.session.add(chunk_record)
                chunk_records.append(chunk_record)

            # Batch upsert to Qdrant
            if points:
                self.qdrant.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )

            doc.status = "completed"
            doc.total_chunks = len(chunks)
            self.session.commit()

            self._stats["files"] += 1
            self._stats["chunks"] += len(chunks)

            return {
                "status": "success",
                "document_id": doc_id,
                "filename": filename,
                "chunks": len(chunks),
                "domain": domain,
            }

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"[FAST-INGEST] Error ingesting {file_path}: {e}")
            self.session.rollback()
            return {"status": "error", "error": str(e)}

    def ingest_directory(self, directory: str, domain: str = None) -> Dict[str, Any]:
        """Ingest all text files in a directory."""
        results = []
        
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('_')]
            dir_domain = domain or os.path.basename(root).replace('_', ' ')
            
            for f in sorted(files):
                if f.startswith('_') or f.startswith('.'):
                    continue
                if not f.endswith(('.txt', '.md')):
                    continue
                    
                path = os.path.join(root, f)
                result = self.ingest_file(path, domain=dir_domain)
                results.append(result)
                
                status = result.get("status", "?")
                if status == "success":
                    chunks = result.get("chunks", 0)
                    logger.info(f"[FAST-INGEST] {f}: {chunks} chunks")

        succeeded = sum(1 for r in results if r["status"] == "success")
        skipped = sum(1 for r in results if r["status"] == "skipped")
        errored = sum(1 for r in results if r["status"] == "error")

        return {
            "total_files": len(results),
            "succeeded": succeeded,
            "skipped": skipped,
            "errors": errored,
            "total_chunks": self._stats["chunks"],
        }

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = re.split(r'\n\n+', text)
        
        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            if len(current_chunk) + len(para) < self.chunk_size:
                current_chunk += "\n\n" + para if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # If no paragraph splits, split by character count
        if not chunks and len(text) > self.chunk_size:
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                chunk = text[i:i + self.chunk_size]
                if chunk.strip():
                    chunks.append(chunk.strip())
        elif not chunks:
            chunks = [text.strip()]

        return [c for c in chunks if len(c) > 20]

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)


def get_fast_ingestion(session: Session) -> FastIngestionPipeline:
    return FastIngestionPipeline(session)
