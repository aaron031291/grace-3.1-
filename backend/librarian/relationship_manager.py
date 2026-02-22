"""
RelationshipManager - Document Relationship Detection and Management

Automatically detects and manages relationships between documents including:
- Similarity-based relationships (related content)
- Version relationships (v1, v2, draft, final)
- Citation relationships (references)
- Duplicate detection

Builds a knowledge graph of document relationships.

Classes:
- `RelationshipManager`

Key Methods:
- `detect_relationships()`
- `create_relationship()`
- `save_detected_relationships()`
- `get_document_relationships()`
- `get_dependency_graph()`
- `delete_relationship()`
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime
import re
import logging

from models.librarian_models import DocumentRelationship
from models.database_models import Document, DocumentChunk
from librarian.utils import calculate_similarity_score

logger = logging.getLogger(__name__)


class RelationshipManager:
    """
    Manages document relationships and knowledge graph construction.

    Detects various relationship types:
    - **related**: Similar content (embedding similarity)
    - **version**: Same document, different versions
    - **citation**: One document references another
    - **duplicate**: Very high similarity (>0.95)
    - **prerequisite**: Dependency relationship
    - **supersedes**: Newer replaces older
    - **part_of**: Document is part of collection

    Example:
        >>> from embedding import get_embedding_model
        >>> from vector_db.client import get_qdrant_client
        >>>
        >>> rel_manager = RelationshipManager(
        ...     db_session,
        ...     get_embedding_model(),
        ...     get_qdrant_client()
        ... )
        >>>
        >>> # Detect relationships
        >>> relationships = rel_manager.detect_relationships(document_id=123)
        >>> print(f"Found {len(relationships)} relationships")
    """

    def __init__(
        self,
        db_session: Session,
        embedding_model=None,
        vector_db_client=None
    ):
        """
        Initialize RelationshipManager.

        Args:
            db_session: SQLAlchemy database session
            embedding_model: Embedding model for similarity
            vector_db_client: Qdrant vector DB client
        """
        self.db = db_session
        self.embedding_model = embedding_model
        self.vector_db = vector_db_client

    def detect_relationships(
        self,
        document_id: int,
        max_candidates: int = 20,
        similarity_threshold: float = 0.7,
        detect_versions: bool = True,
        detect_citations: bool = True,
        detect_duplicates: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Detect relationships for a document.

        Args:
            document_id: Document ID to analyze
            max_candidates: Max similar documents to consider
            similarity_threshold: Minimum similarity (0.0-1.0)
            detect_versions: Detect version relationships
            detect_citations: Detect citation relationships
            detect_duplicates: Detect duplicate documents

        Returns:
            List[Dict]: Detected relationships

        Example:
            >>> relationships = rel_manager.detect_relationships(
            ...     document_id=123,
            ...     max_candidates=20,
            ...     similarity_threshold=0.75
            ... )
            >>> for rel in relationships:
            ...     print(f"{rel['type']}: Doc {rel['target_id']} (score: {rel['strength']})")
        """
        document = self.db.query(Document).filter(
            Document.id == document_id
        ).first()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        detected_relationships = []

        # 1. Embedding-based similarity
        if self.embedding_model and self.vector_db:
            similar_docs = self._find_similar_documents(
                document,
                max_candidates=max_candidates,
                threshold=similarity_threshold
            )

            for target_doc, similarity_score in similar_docs:
                # Determine relationship type based on similarity
                if detect_duplicates and similarity_score > 0.95:
                    rel_type = "duplicate"
                else:
                    rel_type = "related"

                detected_relationships.append({
                    "source_id": document_id,
                    "target_id": target_doc.id,
                    "type": rel_type,
                    "strength": similarity_score,
                    "confidence": similarity_score,
                    "detected_by": "embedding",
                    "metadata": {
                        "similarity_score": similarity_score,
                        "target_filename": target_doc.filename
                    }
                })

        # 2. Version detection
        if detect_versions:
            version_rels = self._detect_version_relationships(document)
            detected_relationships.extend(version_rels)

        # 3. Citation detection
        if detect_citations:
            citation_rels = self._detect_citation_relationships(document)
            detected_relationships.extend(citation_rels)

        # Remove duplicates (same source-target-type combo)
        detected_relationships = self._deduplicate_relationships(detected_relationships)

        logger.info(f"Detected {len(detected_relationships)} relationships for document {document_id}")
        return detected_relationships

    def _find_similar_documents(
        self,
        document: Document,
        max_candidates: int = 20,
        threshold: float = 0.7
    ) -> List[Tuple[Document, float]]:
        """
        Find similar documents using embedding similarity.

        Args:
            document: Source document
            max_candidates: Maximum similar documents
            threshold: Minimum similarity score

        Returns:
            List[Tuple[Document, float]]: List of (document, similarity_score)
        """
        if not document.chunks or not self.vector_db or not self.vector_db.is_connected():
            return []

        similar_docs = []

        try:
            # Get first chunk's embedding vector ID
            first_chunk = document.chunks[0]
            if not first_chunk.embedding_vector_id:
                return []

            # For simplicity, use first chunk's embedding to find similar docs
            # In production, you might average all chunk embeddings

            # Search vector database
            # Note: We'll need to get the actual vector, which requires reading from Qdrant
            # For now, we'll use a simpler approach: compare documents with similar filenames
            # or use chunk similarity directly

            # Get all documents (excluding self)
            all_docs = self.db.query(Document).filter(
                Document.id != document.id
            ).limit(100).all()

            # Calculate simple text similarity for each
            for other_doc in all_docs:
                if not other_doc.chunks:
                    continue

                # Calculate similarity based on filename and content
                filename_sim = calculate_similarity_score(
                    document.filename or "",
                    other_doc.filename or ""
                )

                # Sample content similarity
                doc_content = " ".join([c.text_content[:500] for c in document.chunks[:3]])
                other_content = " ".join([c.text_content[:500] for c in other_doc.chunks[:3]])
                content_sim = calculate_similarity_score(doc_content, other_content)

                # Weighted average
                combined_sim = (filename_sim * 0.3 + content_sim * 0.7)

                if combined_sim >= threshold:
                    similar_docs.append((other_doc, combined_sim))

            # Sort by similarity (descending) and limit
            similar_docs.sort(key=lambda x: x[1], reverse=True)
            similar_docs = similar_docs[:max_candidates]

        except Exception as e:
            logger.error(f"Error finding similar documents: {e}")
            return []

        return similar_docs

    def _detect_version_relationships(self, document: Document) -> List[Dict[str, Any]]:
        """
        Detect version relationships (v1, v2, draft, final, etc.).

        Args:
            document: Source document

        Returns:
            List[Dict]: Detected version relationships
        """
        if not document.filename:
            return []

        relationships = []

        # Extract base filename without version indicators
        filename = document.filename
        base_name, version_info = self._extract_version_info(filename)

        if not base_name:
            return []

        # Find documents with similar base name but different versions
        all_docs = self.db.query(Document).filter(
            Document.id != document.id
        ).all()

        for other_doc in all_docs:
            if not other_doc.filename:
                continue

            other_base, other_version = self._extract_version_info(other_doc.filename)

            # Check if base names match (case-insensitive, fuzzy)
            if other_base and self._are_base_names_similar(base_name, other_base):
                # Determine direction (which is newer)
                if version_info and other_version:
                    is_newer = self._is_version_newer(version_info, other_version)
                    rel_type = "version"
                else:
                    # Can't determine version order
                    is_newer = None
                    rel_type = "version"

                relationships.append({
                    "source_id": document.id,
                    "target_id": other_doc.id,
                    "type": rel_type,
                    "strength": 0.8,
                    "confidence": 0.8,
                    "detected_by": "heuristic",
                    "metadata": {
                        "source_version": version_info,
                        "target_version": other_version,
                        "source_is_newer": is_newer
                    }
                })

        return relationships

    def _extract_version_info(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract base name and version info from filename.

        Args:
            filename: Filename to parse

        Returns:
            Tuple[Optional[str], Optional[str]]: (base_name, version_info)

        Example:
            >>> _extract_version_info("report_v2.pdf")
            ('report', 'v2')
            >>> _extract_version_info("draft_final.docx")
            ('', 'final')
        """
        # Remove extension
        name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename

        # Version patterns
        version_patterns = [
            r'_v(\d+)',          # _v1, _v2
            r'_version_?(\d+)',  # _version1, _version_1
            r'_(draft|final|revised?)',  # _draft, _final, _revised
            r'_(\d{4}-\d{2}-\d{2})',  # _2024-01-15
            r'\((\d+)\)',        # (1), (2)
        ]

        for pattern in version_patterns:
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                version = match.group(1)
                base_name = name_without_ext[:match.start()].strip('_- ')
                return base_name, version

        return name_without_ext, None

    def _are_base_names_similar(self, name1: str, name2: str) -> bool:
        """Check if base names are similar enough."""
        if not name1 or not name2:
            return False

        # Simple similarity check
        similarity = calculate_similarity_score(name1.lower(), name2.lower())
        return similarity > 0.7

    def _is_version_newer(self, version1: str, version2: str) -> Optional[bool]:
        """
        Determine if version1 is newer than version2.

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            Optional[bool]: True if version1 is newer, False if older, None if unknown
        """
        # Try numeric comparison
        try:
            v1_num = int(re.sub(r'\D', '', version1))
            v2_num = int(re.sub(r'\D', '', version2))
            return v1_num > v2_num
        except (ValueError, AttributeError):
            pass

        # Try date comparison
        date_pattern = r'(\d{4}-\d{2}-\d{2})'
        match1 = re.search(date_pattern, version1)
        match2 = re.search(date_pattern, version2)
        if match1 and match2:
            return match1.group(1) > match2.group(1)

        # Try draft/final comparison
        status_order = {"draft": 1, "revised": 2, "final": 3}
        v1_lower = version1.lower()
        v2_lower = version2.lower()

        v1_status = next((s for s in status_order if s in v1_lower), None)
        v2_status = next((s for s in status_order if s in v2_lower), None)

        if v1_status and v2_status:
            return status_order[v1_status] > status_order[v2_status]

        return None

    def _detect_citation_relationships(self, document: Document) -> List[Dict[str, Any]]:
        """
        Detect citation relationships (document references another).

        Checks if other document filenames appear in this document's content.

        Args:
            document: Source document

        Returns:
            List[Dict]: Detected citation relationships
        """
        if not document.chunks:
            return []

        relationships = []

        # Get all other documents
        all_docs = self.db.query(Document).filter(
            Document.id != document.id
        ).all()

        # Get content from first few chunks
        content = " ".join([c.text_content for c in document.chunks[:5]]).lower()

        for other_doc in all_docs:
            if not other_doc.filename:
                continue

            # Check if other document's filename (without extension) appears in content
            filename_base = other_doc.filename.rsplit('.', 1)[0].lower()

            if len(filename_base) > 5 and filename_base in content:
                relationships.append({
                    "source_id": document.id,
                    "target_id": other_doc.id,
                    "type": "citation",
                    "strength": 0.75,
                    "confidence": 0.7,
                    "detected_by": "heuristic",
                    "metadata": {
                        "cited_filename": other_doc.filename
                    }
                })

        return relationships

    def _deduplicate_relationships(
        self,
        relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate relationships."""
        seen = set()
        unique_relationships = []

        for rel in relationships:
            key = (rel["source_id"], rel["target_id"], rel["type"])
            if key not in seen:
                seen.add(key)
                unique_relationships.append(rel)

        return unique_relationships

    def create_relationship(
        self,
        source_document_id: int,
        target_document_id: int,
        relationship_type: str,
        confidence: float = 1.0,
        strength: float = 0.5,
        detected_by: str = "user",
        bidirectional: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentRelationship:
        """
        Manually create a relationship between documents.

        Args:
            source_document_id: Source document ID
            target_document_id: Target document ID
            relationship_type: Type (citation, prerequisite, related, etc.)
            confidence: Confidence score (0.0-1.0)
            strength: Relationship strength (0.0-1.0)
            detected_by: Who/what created it
            bidirectional: If True, relationship goes both ways
            metadata: Optional metadata dict

        Returns:
            DocumentRelationship: Created relationship

        Example:
            >>> rel = rel_manager.create_relationship(
            ...     source_document_id=123,
            ...     target_document_id=456,
            ...     relationship_type="prerequisite",
            ...     metadata={"reason": "Must read before"}
            ... )
        """
        # Validate documents exist
        source = self.db.query(Document).filter(Document.id == source_document_id).first()
        target = self.db.query(Document).filter(Document.id == target_document_id).first()

        if not source or not target:
            raise ValueError("Source or target document not found")

        if source_document_id == target_document_id:
            raise ValueError("Cannot create relationship to self")

        # Check if relationship already exists
        existing = self.db.query(DocumentRelationship).filter(
            and_(
                DocumentRelationship.source_document_id == source_document_id,
                DocumentRelationship.target_document_id == target_document_id,
                DocumentRelationship.relationship_type == relationship_type
            )
        ).first()

        if existing:
            logger.warning(f"Relationship already exists: {source_document_id} -> {target_document_id} ({relationship_type})")
            return existing

        # Create relationship
        relationship = DocumentRelationship(
            source_document_id=source_document_id,
            target_document_id=target_document_id,
            relationship_type=relationship_type,
            confidence=confidence,
            strength=strength,
            detected_by=detected_by,
            bidirectional=bidirectional,
            relationship_metadata=metadata
        )

        self.db.add(relationship)
        self.db.commit()
        self.db.refresh(relationship)

        logger.info(f"Created relationship: {source_document_id} -> {target_document_id} ({relationship_type})")
        return relationship

    def save_detected_relationships(
        self,
        relationships: List[Dict[str, Any]],
        skip_existing: bool = True
    ) -> int:
        """
        Save detected relationships to database.

        Args:
            relationships: List of relationship dicts from detect_relationships()
            skip_existing: Skip relationships that already exist

        Returns:
            int: Number of relationships created

        Example:
            >>> rels = rel_manager.detect_relationships(document_id=123)
            >>> count = rel_manager.save_detected_relationships(rels)
            >>> print(f"Saved {count} relationships")
        """
        created_count = 0

        for rel in relationships:
            try:
                # Check if exists
                if skip_existing:
                    existing = self.db.query(DocumentRelationship).filter(
                        and_(
                            DocumentRelationship.source_document_id == rel["source_id"],
                            DocumentRelationship.target_document_id == rel["target_id"],
                            DocumentRelationship.relationship_type == rel["type"]
                        )
                    ).first()

                    if existing:
                        continue

                # Create relationship
                self.create_relationship(
                    source_document_id=rel["source_id"],
                    target_document_id=rel["target_id"],
                    relationship_type=rel["type"],
                    confidence=rel.get("confidence", 0.8),
                    strength=rel.get("strength", 0.5),
                    detected_by=rel.get("detected_by", "auto"),
                    bidirectional=rel.get("bidirectional", False),
                    metadata=rel.get("metadata")
                )

                created_count += 1

            except Exception as e:
                logger.error(f"Failed to save relationship: {e}")
                continue

        logger.info(f"Saved {created_count}/{len(relationships)} relationships")
        return created_count

    def get_document_relationships(
        self,
        document_id: int,
        direction: str = "both"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all relationships for a document.

        Args:
            document_id: Document ID
            direction: "outgoing", "incoming", or "both"

        Returns:
            Dict with "outgoing" and/or "incoming" relationship lists

        Example:
            >>> rels = rel_manager.get_document_relationships(123)
            >>> print(f"Outgoing: {len(rels['outgoing'])}")
            >>> print(f"Incoming: {len(rels['incoming'])}")
        """
        result = {}

        if direction in ("outgoing", "both"):
            outgoing = self.db.query(DocumentRelationship).filter(
                DocumentRelationship.source_document_id == document_id
            ).all()

            result["outgoing"] = [
                {
                    "id": rel.id,
                    "target_document_id": rel.target_document_id,
                    "relationship_type": rel.relationship_type,
                    "confidence": rel.confidence,
                    "strength": rel.strength,
                    "detected_by": rel.detected_by,
                    "bidirectional": rel.bidirectional,
                    "metadata": rel.relationship_metadata,
                    "created_at": rel.created_at.isoformat() if rel.created_at else None
                }
                for rel in outgoing
            ]

        if direction in ("incoming", "both"):
            incoming = self.db.query(DocumentRelationship).filter(
                DocumentRelationship.target_document_id == document_id
            ).all()

            result["incoming"] = [
                {
                    "id": rel.id,
                    "source_document_id": rel.source_document_id,
                    "relationship_type": rel.relationship_type,
                    "confidence": rel.confidence,
                    "strength": rel.strength,
                    "detected_by": rel.detected_by,
                    "bidirectional": rel.bidirectional,
                    "metadata": rel.relationship_metadata,
                    "created_at": rel.created_at.isoformat() if rel.created_at else None
                }
                for rel in incoming
            ]

        return result

    def get_dependency_graph(
        self,
        document_id: int,
        max_depth: int = 3,
        relationship_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get dependency graph for a document.

        Traverses relationships up to max_depth levels.

        Args:
            document_id: Starting document ID
            max_depth: Maximum traversal depth
            relationship_types: Filter by relationship types

        Returns:
            Dict: Graph with nodes and edges

        Example:
            >>> graph = rel_manager.get_dependency_graph(123, max_depth=2)
            >>> print(f"Nodes: {len(graph['nodes'])}")
            >>> print(f"Edges: {len(graph['edges'])}")
        """
        visited = set()
        nodes = {}
        edges = []

        def traverse(doc_id, current_depth):
            if current_depth > max_depth or doc_id in visited:
                return

            visited.add(doc_id)

            # Add node
            doc = self.db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                nodes[doc_id] = {
                    "id": doc_id,
                    "filename": doc.filename,
                    "file_path": doc.file_path,
                    "depth": current_depth
                }

            # Get relationships
            rels = self.get_document_relationships(doc_id, direction="both")

            # Process outgoing
            for rel in rels.get("outgoing", []):
                if relationship_types and rel["relationship_type"] not in relationship_types:
                    continue

                target_id = rel["target_document_id"]
                edges.append({
                    "source": doc_id,
                    "target": target_id,
                    "type": rel["relationship_type"],
                    "strength": rel["strength"]
                })

                traverse(target_id, current_depth + 1)

            # Process incoming
            for rel in rels.get("incoming", []):
                if relationship_types and rel["relationship_type"] not in relationship_types:
                    continue

                source_id = rel["source_document_id"]
                edges.append({
                    "source": source_id,
                    "target": doc_id,
                    "type": rel["relationship_type"],
                    "strength": rel["strength"]
                })

                traverse(source_id, current_depth + 1)

        traverse(document_id, 0)

        return {
            "root_document_id": document_id,
            "nodes": list(nodes.values()),
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }

    def delete_relationship(self, relationship_id: int) -> bool:
        """
        Delete a relationship.

        Args:
            relationship_id: Relationship ID to delete

        Returns:
            bool: True if deleted, False if not found
        """
        relationship = self.db.query(DocumentRelationship).filter(
            DocumentRelationship.id == relationship_id
        ).first()

        if not relationship:
            return False

        self.db.delete(relationship)
        self.db.commit()

        logger.info(f"Deleted relationship {relationship_id}")
        return True
