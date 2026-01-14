"""
Repository Access Layer - Read-Only Access to GRACE Systems

Provides LLMs with read-only access to:
- Source code repository (file tree, contents)
- Genesis Keys (universal tracking)
- Librarian (semantic organization)
- Immutable Memory (episodic, procedural, patterns)
- RAG System (document retrieval)
- World Model (system state)
- Mesh Memory (learning memory, episodes, procedures)
- Ingestion Data (training data, learning examples)

All access is READ-ONLY and logged for audit.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import json

from database import session as db_session
from models.database_models import Document, DocumentChunk
from models.genesis_key_models import GenesisKey
from models.librarian_models import LibrarianTag, DocumentRelationship
from cognitive.learning_memory import LearningExample, LearningPattern
from vector_db.client import get_qdrant_client
from embedding import EmbeddingModel
from retrieval.retriever import DocumentRetriever

logger = logging.getLogger(__name__)


class RepositoryAccessLayer:
    """
    Provides LLMs with read-only access to GRACE systems.

    All operations are non-mutating and logged.
    """

    def __init__(
        self,
        session: Optional[Session] = None,
        knowledge_base_path: Optional[Path] = None,
        embedding_model: Optional[EmbeddingModel] = None
    ):
        """
        Initialize repository access layer.

        Args:
            session: Database session
            knowledge_base_path: Path to knowledge base
            embedding_model: Embedding model for semantic search
        """
        self.session = session
        self.kb_path = knowledge_base_path or Path("backend/knowledge_base")
        self.embedding_model = embedding_model
        self.qdrant_client = get_qdrant_client()

        # Initialize retriever if embedding model provided
        self.retriever = None
        if embedding_model:
            self.retriever = DocumentRetriever(embedding_model=embedding_model)

        # Access log
        self.access_log: List[Dict[str, Any]] = []

    def _log_access(self, operation: str, details: Dict[str, Any]):
        """Log read access for audit trail."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "details": details
        }
        self.access_log.append(log_entry)
        logger.debug(f"[READ-ONLY ACCESS] {operation}: {details}")

    # ===================================================================
    # SOURCE CODE REPOSITORY ACCESS
    # ===================================================================

    def get_file_tree(
        self,
        root_path: Optional[str] = None,
        max_depth: int = 5,
        exclude_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get repository file tree structure.

        Args:
            root_path: Root path (default: current directory)
            max_depth: Maximum depth to traverse
            exclude_patterns: Patterns to exclude (e.g., ['__pycache__', '.git'])

        Returns:
            File tree structure
        """
        self._log_access("get_file_tree", {"root_path": root_path, "max_depth": max_depth})

        root = Path(root_path or ".")
        exclude = exclude_patterns or ['__pycache__', '.git', 'node_modules', 'venv', '.venv']

        def build_tree(path: Path, depth: int = 0) -> Dict[str, Any]:
            if depth > max_depth:
                return {"truncated": True}

            if not path.exists():
                return {}

            result = {
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "path": str(path)
            }

            if path.is_dir():
                children = []
                try:
                    for child in sorted(path.iterdir()):
                        if not any(pattern in child.name for pattern in exclude):
                            child_tree = build_tree(child, depth + 1)
                            if child_tree:
                                children.append(child_tree)
                    result["children"] = children
                except PermissionError:
                    result["error"] = "Permission denied"

            return result

        return build_tree(root)

    def read_file(
        self,
        file_path: str,
        max_lines: Optional[int] = None,
        line_range: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """
        Read file contents (read-only).

        Args:
            file_path: Path to file
            max_lines: Maximum lines to read
            line_range: (start, end) line numbers

        Returns:
            File contents and metadata
        """
        self._log_access("read_file", {"file_path": file_path, "max_lines": max_lines})

        path = Path(file_path)

        if not path.exists():
            return {"error": "File not found", "path": file_path}

        if not path.is_file():
            return {"error": "Path is not a file", "path": file_path}

        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # Apply line range
            if line_range:
                start, end = line_range
                lines = lines[start:end]
            elif max_lines:
                lines = lines[:max_lines]

            return {
                "path": file_path,
                "content": ''.join(lines),
                "line_count": len(lines),
                "size_bytes": path.stat().st_size,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat()
            }

        except Exception as e:
            return {"error": str(e), "path": file_path}

    def search_code(
        self,
        pattern: str,
        file_pattern: str = "*.py",
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search for code pattern in repository.

        Args:
            pattern: Search pattern (regex)
            file_pattern: File glob pattern
            max_results: Maximum results

        Returns:
            List of matches with context
        """
        self._log_access("search_code", {"pattern": pattern, "file_pattern": file_pattern})

        import re
        from pathlib import Path

        results = []
        root = Path(".")

        try:
            pattern_re = re.compile(pattern, re.IGNORECASE)

            for file_path in root.rglob(file_pattern):
                if len(results) >= max_results:
                    break

                if any(excluded in str(file_path) for excluded in ['__pycache__', '.git', 'venv']):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern_re.search(line):
                                results.append({
                                    "file": str(file_path),
                                    "line": line_num,
                                    "content": line.strip(),
                                    "match": pattern
                                })
                                if len(results) >= max_results:
                                    break
                except:
                    continue

        except Exception as e:
            logger.error(f"Error searching code: {e}")

        return results

    # ===================================================================
    # GENESIS KEYS ACCESS
    # ===================================================================

    def get_genesis_key(self, genesis_key_id: str) -> Optional[Dict[str, Any]]:
        """Get Genesis Key by ID."""
        self._log_access("get_genesis_key", {"genesis_key_id": genesis_key_id})

        if not self.session:
            return None

        from models.genesis_key_models import GenesisKey

        key = self.session.query(GenesisKey).filter(
            GenesisKey.genesis_key_id == genesis_key_id
        ).first()

        if not key:
            return None

        return {
            "genesis_key_id": key.genesis_key_id,
            "entity_type": key.entity_type,
            "source_path": key.source_path,
            "parent_key_id": key.parent_key_id,
            "immutable_hash": key.immutable_hash,
            "version_tag": key.version_tag,
            "semantic_tags": key.semantic_tags,
            "relationships": key.relationships,
            "created_at": key.created_at.isoformat() if key.created_at else None
        }

    def search_genesis_keys(
        self,
        entity_type: Optional[str] = None,
        semantic_tags: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search Genesis Keys."""
        self._log_access("search_genesis_keys", {
            "entity_type": entity_type,
            "semantic_tags": semantic_tags
        })

        if not self.session:
            return []

        from models.genesis_key_models import GenesisKey

        query = self.session.query(GenesisKey)

        if entity_type:
            query = query.filter(GenesisKey.entity_type == entity_type)

        keys = query.limit(limit).all()

        return [
            {
                "genesis_key_id": key.genesis_key_id,
                "entity_type": key.entity_type,
                "source_path": key.source_path,
                "semantic_tags": key.semantic_tags,
                "created_at": key.created_at.isoformat() if key.created_at else None
            }
            for key in keys
        ]

    # ===================================================================
    # LIBRARIAN ACCESS
    # ===================================================================

    def get_librarian_tags(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get Librarian tags."""
        self._log_access("get_librarian_tags", {"limit": limit})

        if not self.session:
            return []

        tags = self.session.query(LibrarianTag).limit(limit).all()

        return [
            {
                "id": tag.id,
                "genesis_key_id": tag.genesis_key_id,
                "tag_type": tag.tag_type,
                "tag_value": tag.tag_value,
                "confidence_score": tag.confidence_score,
                "created_at": tag.created_at.isoformat() if tag.created_at else None
            }
            for tag in tags
        ]

    def get_librarian_relationships(self, genesis_key_id: str) -> List[Dict[str, Any]]:
        """Get Librarian relationships for a Genesis Key."""
        self._log_access("get_librarian_relationships", {"genesis_key_id": genesis_key_id})

        if not self.session:
            return []

        relationships = self.session.query(DocumentRelationship).filter(
            (DocumentRelationship.source_key_id == genesis_key_id) |
            (DocumentRelationship.target_key_id == genesis_key_id)
        ).all()

        return [
            {
                "id": rel.id,
                "source_key_id": rel.source_key_id,
                "target_key_id": rel.target_key_id,
                "relationship_type": rel.relationship_type,
                "confidence_score": rel.confidence_score,
                "created_at": rel.created_at.isoformat() if rel.created_at else None
            }
            for rel in relationships
        ]

    # ===================================================================
    # RAG SYSTEM ACCESS
    # ===================================================================

    def rag_query(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Query RAG system for relevant documents."""
        self._log_access("rag_query", {"query": query, "limit": limit})

        if not self.retriever:
            logger.warning("Retriever not initialized")
            return []

        try:
            results = self.retriever.retrieve(
                query=query,
                limit=limit,
                score_threshold=score_threshold
            )
            return results
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            return []

    def get_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        self._log_access("get_document", {"document_id": document_id})

        if not self.session:
            return None

        doc = self.session.query(Document).filter(Document.id == document_id).first()

        if not doc:
            return None

        return {
            "id": doc.id,
            "filename": doc.filename,
            "file_path": doc.file_path,
            "source": doc.source,
            "file_type": doc.file_type,
            "description": doc.description,
            "confidence_score": doc.confidence_score,
            "created_at": doc.created_at.isoformat() if doc.created_at else None
        }

    def get_document_chunks(self, document_id: int) -> List[Dict[str, Any]]:
        """Get all chunks for a document."""
        self._log_access("get_document_chunks", {"document_id": document_id})

        if not self.session:
            return []

        chunks = self.session.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()

        return [
            {
                "id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "text_content": chunk.text_content,
                "confidence_score": chunk.confidence_score,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end
            }
            for chunk in chunks
        ]

    # ===================================================================
    # LEARNING MEMORY ACCESS
    # ===================================================================

    def get_learning_examples(
        self,
        min_trust_score: float = 0.7,
        example_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get learning examples (training data)."""
        self._log_access("get_learning_examples", {
            "min_trust_score": min_trust_score,
            "example_type": example_type,
            "limit": limit
        })

        if not self.session:
            return []

        query = self.session.query(LearningExample).filter(
            LearningExample.trust_score >= min_trust_score
        )

        if example_type:
            query = query.filter(LearningExample.example_type == example_type)

        examples = query.order_by(
            LearningExample.trust_score.desc()
        ).limit(limit).all()

        return [
            {
                "id": str(ex.id),
                "example_type": ex.example_type,
                "input_context": ex.input_context,
                "expected_output": ex.expected_output,
                "actual_output": ex.actual_output,
                "trust_score": ex.trust_score,
                "source": ex.source,
                "times_validated": ex.times_validated,
                "times_invalidated": ex.times_invalidated,
                "created_at": ex.created_at.isoformat() if ex.created_at else None
            }
            for ex in examples
        ]

    def get_learning_patterns(
        self,
        min_trust_score: float = 0.7,
        pattern_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get learned patterns."""
        self._log_access("get_learning_patterns", {
            "min_trust_score": min_trust_score,
            "pattern_type": pattern_type
        })

        if not self.session:
            return []

        query = self.session.query(LearningPattern).filter(
            LearningPattern.trust_score >= min_trust_score
        )

        if pattern_type:
            query = query.filter(LearningPattern.pattern_type == pattern_type)

        patterns = query.all()

        return [
            {
                "id": str(pattern.id),
                "pattern_name": pattern.pattern_name,
                "pattern_type": pattern.pattern_type,
                "preconditions": pattern.preconditions,
                "actions": pattern.actions,
                "expected_outcomes": pattern.expected_outcomes,
                "trust_score": pattern.trust_score,
                "success_rate": pattern.success_rate,
                "sample_size": pattern.sample_size,
                "times_applied": pattern.times_applied,
                "times_succeeded": pattern.times_succeeded,
                "times_failed": pattern.times_failed
            }
            for pattern in patterns
        ]

    # ===================================================================
    # WORLD MODEL ACCESS (System State)
    # ===================================================================

    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics."""
        self._log_access("get_system_stats", {})

        if not self.session:
            return {}

        from sqlalchemy import func

        stats = {
            "documents": {
                "total": self.session.query(func.count(Document.id)).scalar() or 0,
                "avg_confidence": self.session.query(func.avg(Document.confidence_score)).scalar() or 0.0
            },
            "chunks": {
                "total": self.session.query(func.count(DocumentChunk.id)).scalar() or 0
            },
            "learning_examples": {
                "total": self.session.query(func.count(LearningExample.id)).scalar() or 0,
                "avg_trust": self.session.query(func.avg(LearningExample.trust_score)).scalar() or 0.0
            },
            "genesis_keys": {
                "total": self.session.query(func.count(GenesisKey.id)).scalar() or 0
            },
            "timestamp": datetime.now().isoformat()
        }

        return stats

    # ===================================================================
    # ACCESS LOG RETRIEVAL
    # ===================================================================

    def get_access_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent access log entries."""
        return self.access_log[-limit:]

    def clear_access_log(self):
        """Clear access log."""
        self.access_log.clear()


# Global instance
_repo_access: Optional[RepositoryAccessLayer] = None


def get_repo_access(
    session: Optional[Session] = None,
    embedding_model: Optional[EmbeddingModel] = None
) -> RepositoryAccessLayer:
    """Get or create global repository access instance."""
    global _repo_access
    if _repo_access is None or session is not None or embedding_model is not None:
        _repo_access = RepositoryAccessLayer(
            session=session,
            embedding_model=embedding_model
        )
    return _repo_access
