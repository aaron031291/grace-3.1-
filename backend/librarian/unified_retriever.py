import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from models.database_models import Document
from models.librarian_models import DocumentTag, LibrarianTag, DocumentRelationship
from librarian.tag_manager import TagManager
from librarian.relationship_manager import RelationshipManager
class UnifiedRetriever:
    logger = logging.getLogger(__name__)
    """
    Unified document retrieval system.

    Combines multiple retrieval methods:
    - Tag-based search
    - Relationship traversal
    - Metadata filtering
    - Confidence-weighted ranking
    """

    def __init__(
        self,
        db_session: Session,
        relationship_manager: Optional[RelationshipManager] = None
    ):
        """
        Initialize unified retriever.

        Args:
            db_session: Database session
            relationship_manager: Optional relationship manager for relationship queries
        """
        self.db = db_session
        self.tag_manager = TagManager(db_session)
        self.relationship_manager = relationship_manager

        logger.info("[UNIFIED-RETRIEVER] Initialized")

    def retrieve(
        self,
        query: Optional[str] = None,
        tag_names: Optional[List[str]] = None,
        match_all_tags: bool = False,
        relationship_from: Optional[int] = None,
        relationship_types: Optional[List[str]] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        min_confidence: float = 0.0
    ) -> Dict[str, Any]:
        """
        Unified retrieval combining all methods.

        Args:
            query: Optional text query (for future semantic search integration)
            tag_names: Optional list of tags to filter by
            match_all_tags: Require all tags (AND) or any tag (OR)
            relationship_from: Optional document ID to find related documents
            relationship_types: Optional list of relationship types to filter
            metadata_filters: Optional metadata filters (e.g., {"source": "user_generated"})
            limit: Maximum results to return
            min_confidence: Minimum confidence score

        Returns:
            Dict with results:
            {
                "documents": List[Dict],
                "total": int,
                "methods_used": List[str],
                "search_params": Dict
            }
        """
        try:
            methods_used = []
            document_ids = set()

            # Method 1: Tag-based retrieval
            if tag_names:
                tag_results = self.tag_manager.search_documents_by_tags(
                    tag_names=tag_names,
                    match_all=match_all_tags,
                    limit=limit * 2  # Get more for ranking
                )
                document_ids.update(tag_results)
                methods_used.append("tags")

            # Method 2: Relationship-based retrieval
            if relationship_from:
                rel_results = self._retrieve_by_relationships(
                    document_id=relationship_from,
                    relationship_types=relationship_types,
                    limit=limit * 2
                )
                document_ids.update(rel_results)
                methods_used.append("relationships")

            # Method 3: Metadata filters
            if metadata_filters:
                meta_results = self._retrieve_by_metadata(
                    filters=metadata_filters,
                    limit=limit * 2
                )
                document_ids.update(meta_results)
                methods_used.append("metadata")

            # If no filters, get all documents (with limit)
            if not document_ids:
                all_docs = self.db.query(Document.id).filter(
                    Document.status == "completed"
                ).limit(limit * 2).all()
                document_ids = {doc.id for doc in all_docs}
                methods_used.append("all")

            # Get document details with confidence scores
            documents = self._get_documents_with_scores(
                document_ids=list(document_ids),
                tag_names=tag_names,
                relationship_from=relationship_from,
                limit=limit,
                min_confidence=min_confidence
            )

            # Sort by confidence
            documents = sorted(
                documents,
                key=lambda x: x.get("confidence", 0.0),
                reverse=True
            )[:limit]

            return {
                "documents": documents,
                "total": len(documents),
                "methods_used": methods_used,
                "search_params": {
                    "tag_names": tag_names,
                    "match_all_tags": match_all_tags,
                    "relationship_from": relationship_from,
                    "relationship_types": relationship_types,
                    "metadata_filters": metadata_filters,
                    "limit": limit,
                    "min_confidence": min_confidence
                }
            }

        except Exception as e:
            logger.error(f"Error in unified retrieval: {e}")
            return {
                "documents": [],
                "total": 0,
                "error": str(e)
            }

    def _retrieve_by_relationships(
        self,
        document_id: int,
        relationship_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[int]:
        """Retrieve documents related to a given document."""
        try:
            query = self.db.query(DocumentRelationship.target_document_id).filter(
                DocumentRelationship.source_document_id == document_id
            )

            if relationship_types:
                query = query.filter(
                    DocumentRelationship.relationship_type.in_(relationship_types)
                )

            related_ids = [row[0] for row in query.limit(limit).all()]
            return related_ids

        except Exception as e:
            logger.error(f"Error retrieving by relationships: {e}")
            return []

    def _retrieve_by_metadata(
        self,
        filters: Dict[str, Any],
        limit: int = 50
    ) -> List[int]:
        """Retrieve documents matching metadata filters."""
        try:
            query = self.db.query(Document.id).filter(
                Document.status == "completed"
            )

            # Apply filters
            if "source" in filters:
                query = query.filter(Document.source == filters["source"])
            if "source_type" in filters:
                query = query.filter(Document.source_type == filters["source_type"])

            doc_ids = [row[0] for row in query.limit(limit).all()]
            return doc_ids

        except Exception as e:
            logger.error(f"Error retrieving by metadata: {e}")
            return []

    def _get_documents_with_scores(
        self,
        document_ids: List[int],
        tag_names: Optional[List[str]] = None,
        relationship_from: Optional[int] = None,
        limit: int = 50,
        min_confidence: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Get documents with confidence scores."""
        try:
            documents = self.db.query(Document).filter(
                Document.id.in_(document_ids[:limit * 2])
            ).all()

            results = []
            for doc in documents:
                # Calculate confidence score
                confidence = self._calculate_confidence(
                    document=doc,
                    tag_names=tag_names,
                    relationship_from=relationship_from
                )

                if confidence < min_confidence:
                    continue

                # Get tags
                tags = self.tag_manager.get_document_tags(doc.id)

                # Build result
                result = {
                    "id": doc.id,
                    "filename": doc.filename,
                    "file_path": doc.file_path,
                    "source": doc.source,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "tags": tags,
                    "confidence": confidence,
                    "excerpt": doc.content[:200].replace('\n', ' ') if doc.content else None
                }

                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error getting documents with scores: {e}")
            return []

    def _calculate_confidence(
        self,
        document: Document,
        tag_names: Optional[List[str]] = None,
        relationship_from: Optional[int] = None
    ) -> float:
        """Calculate confidence score for a document match."""
        confidence = 0.5  # Base confidence

        # Boost if tags match
        if tag_names:
            doc_tags = self.tag_manager.get_document_tags(document.id)
            doc_tag_names = {tag.get("tag_name", "").lower() for tag in doc_tags}
            query_tag_names = {tag.lower() for tag in tag_names}

            matching_tags = doc_tag_names & query_tag_names
            if matching_tags:
                # Boost confidence based on tag overlap
                tag_boost = len(matching_tags) / len(query_tag_names)
                confidence += tag_boost * 0.3

        # Boost if has relationship
        if relationship_from:
            rel_exists = self.db.query(DocumentRelationship).filter(
                DocumentRelationship.source_document_id == relationship_from,
                DocumentRelationship.target_document_id == document.id
            ).first()
            if rel_exists:
                confidence += 0.2

        # Clamp to [0.0, 1.0]
        return min(1.0, max(0.0, confidence))

    def search_by_path(
        self,
        path_pattern: str,
        recursive: bool = True,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search documents by file path pattern.

        Args:
            path_pattern: Path pattern to match (supports wildcards)
            recursive: Include subdirectories
            limit: Maximum results

        Returns:
            Dict with matching documents
        """
        try:
            # Simple path matching (can be extended with regex)
            if recursive:
                query = self.db.query(Document).filter(
                    Document.file_path.like(f"%{path_pattern}%")
                )
            else:
                query = self.db.query(Document).filter(
                    Document.file_path.like(f"{path_pattern}%")
                )

            documents = query.filter(
                Document.status == "completed"
            ).limit(limit).all()

            results = []
            for doc in documents:
                tags = self.tag_manager.get_document_tags(doc.id)
                results.append({
                    "id": doc.id,
                    "filename": doc.filename,
                    "file_path": doc.file_path,
                    "tags": tags,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None
                })

            return {
                "documents": results,
                "total": len(results),
                "path_pattern": path_pattern
            }

        except Exception as e:
            logger.error(f"Error searching by path: {e}")
            return {
                "documents": [],
                "total": 0,
                "error": str(e)
            }
