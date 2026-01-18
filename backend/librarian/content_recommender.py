import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models.database_models import Document
from models.librarian_models import DocumentTag, LibrarianTag, DocumentRelationship
from librarian.tag_manager import TagManager
from librarian.relationship_manager import RelationshipManager
logger = logging.getLogger(__name__)

class ContentRecommender:
    """
    Content recommendation engine.

    Provides intelligent recommendations for:
    - Related documents
    - Similar content
    - Trending documents
    - Personalized suggestions
    """

    def __init__(
        self,
        db_session: Session,
        relationship_manager: Optional[RelationshipManager] = None
    ):
        """
        Initialize content recommender.

        Args:
            db_session: Database session
            relationship_manager: Optional relationship manager for relationship-based recommendations
        """
        self.db = db_session
        self.tag_manager = TagManager(db_session)
        self.relationship_manager = relationship_manager

        logger.info("[CONTENT-RECOMMENDER] Initialized")

    def recommend_related(
        self,
        document_id: int,
        limit: int = 10,
        min_score: float = 0.3
    ) -> Dict[str, Any]:
        """
        Recommend related documents based on multiple factors.

        Combines:
        - Tag similarity
        - Relationship graph
        - Content metadata similarity

        Args:
            document_id: Source document ID
            limit: Maximum recommendations
            min_score: Minimum recommendation score

        Returns:
            Dict with recommended documents and scores
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {
                    "document_id": document_id,
                    "recommendations": [],
                    "total": 0,
                    "error": "Document not found"
                }

            # Get document tags
            doc_tags = self.tag_manager.get_document_tags(document_id)
            tag_names = [tag.get("tag_name", "") for tag in doc_tags]
            tag_ids = {tag.get("tag_id") for tag in doc_tags}

            # Build recommendation scores
            recommendations = {}

            # Method 1: Tag-based recommendations
            if tag_ids:
                tag_recommendations = self._recommend_by_tags(tag_ids, document_id, limit * 2)
                for doc_id, score in tag_recommendations.items():
                    recommendations[doc_id] = recommendations.get(doc_id, 0) + (score * 0.5)

            # Method 2: Relationship-based recommendations
            if self.relationship_manager:
                rel_recommendations = self._recommend_by_relationships(document_id, limit * 2)
                for doc_id, score in rel_recommendations.items():
                    recommendations[doc_id] = recommendations.get(doc_id, 0) + (score * 0.3)

            # Method 3: Metadata similarity
            meta_recommendations = self._recommend_by_metadata(document, limit * 2)
            for doc_id, score in meta_recommendations.items():
                recommendations[doc_id] = recommendations.get(doc_id, 0) + (score * 0.2)

            # Sort by score and filter
            sorted_recommendations = sorted(
                recommendations.items(),
                key=lambda x: x[1],
                reverse=True
            )

            # Filter by min_score and limit
            filtered = [
                (doc_id, score) for doc_id, score in sorted_recommendations
                if score >= min_score
            ][:limit]

            # Get document details
            doc_ids = [doc_id for doc_id, _ in filtered]
            documents = self.db.query(Document).filter(Document.id.in_(doc_ids)).all()
            
            # Build response
            doc_map = {doc.id: doc for doc in documents}
            recommendations_list = []
            for doc_id, score in filtered:
                if doc_id in doc_map:
                    doc = doc_map[doc_id]
                    doc_tags = self.tag_manager.get_document_tags(doc_id)
                    recommendations_list.append({
                        "document_id": doc_id,
                        "filename": doc.filename,
                        "file_path": doc.file_path,
                        "score": score,
                        "tags": doc_tags,
                        "reason": self._get_recommendation_reason(doc_id, document_id, score)
                    })

            return {
                "document_id": document_id,
                "recommendations": recommendations_list,
                "total": len(recommendations_list)
            }

        except Exception as e:
            logger.error(f"Error recommending related documents: {e}")
            return {
                "document_id": document_id,
                "recommendations": [],
                "total": 0,
                "error": str(e)
            }

    def recommend_by_tags(
        self,
        tag_names: List[str],
        limit: int = 10,
        match_all: bool = False
    ) -> Dict[str, Any]:
        """
        Recommend documents based on tags.

        Args:
            tag_names: List of tags to match
            limit: Maximum recommendations
            match_all: Require all tags (AND) or any tag (OR)

        Returns:
            Dict with recommended documents
        """
        try:
            # Get documents with matching tags
            if match_all:
                # Documents with ALL tags
                doc_ids = self.tag_manager.search_documents_by_tags(
                    tag_names=tag_names,
                    match_all=True,
                    limit=limit
                )
            else:
                # Documents with ANY tag
                doc_ids = self.tag_manager.search_documents_by_tags(
                    tag_names=tag_names,
                    match_all=False,
                    limit=limit * 2
                )

            # Get documents
            documents = self.db.query(Document).filter(
                Document.id.in_(doc_ids),
                Document.status == "completed"
            ).limit(limit).all()

            # Build response with scores
            recommendations = []
            for doc in documents:
                doc_tags = self.tag_manager.get_document_tags(doc.id)
                doc_tag_names = {tag.get("tag_name", "") for tag in doc_tags}
                query_tag_names = set(tag_names)

                # Calculate tag overlap score
                overlap = len(doc_tag_names & query_tag_names)
                score = overlap / len(query_tag_names) if query_tag_names else 0.0

                recommendations.append({
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "file_path": doc.file_path,
                    "score": score,
                    "tags": doc_tags,
                    "matched_tags": list(doc_tag_names & query_tag_names)
                })

            return {
                "tag_names": tag_names,
                "recommendations": recommendations,
                "total": len(recommendations)
            }

        except Exception as e:
            logger.error(f"Error recommending by tags: {e}")
            return {
                "tag_names": tag_names,
                "recommendations": [],
                "total": 0,
                "error": str(e)
            }

    def recommend_trending(
        self,
        days: int = 7,
        limit: int = 10,
        min_confidence: float = 0.5
    ) -> Dict[str, Any]:
        """
        Get trending documents (recently created or updated).

        Args:
            days: Number of days to look back
            limit: Maximum recommendations
            min_confidence: Minimum confidence score

        Returns:
            Dict with trending documents
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Get recent documents with high confidence
            documents = self.db.query(Document).filter(
                Document.status == "completed",
                Document.confidence_score >= min_confidence,
                Document.created_at >= cutoff_date
            ).order_by(
                desc(Document.created_at),
                desc(Document.confidence_score)
            ).limit(limit).all()

            recommendations = []
            for doc in documents:
                doc_tags = self.tag_manager.get_document_tags(doc.id)
                
                # Calculate trending score (recency + confidence)
                days_old = (datetime.utcnow() - doc.created_at).days if doc.created_at else days
                recency_score = max(0, 1.0 - (days_old / days))
                trending_score = (recency_score * 0.6) + (doc.confidence_score * 0.4)

                recommendations.append({
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "file_path": doc.file_path,
                    "trending_score": trending_score,
                    "confidence_score": doc.confidence_score,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "tags": doc_tags
                })

            return {
                "days": days,
                "recommendations": recommendations,
                "total": len(recommendations)
            }

        except Exception as e:
            logger.error(f"Error getting trending documents: {e}")
            return {
                "days": days,
                "recommendations": [],
                "total": 0,
                "error": str(e)
            }

    def _recommend_by_tags(
        self,
        tag_ids: set,
        exclude_document_id: int,
        limit: int
    ) -> Dict[int, float]:
        """Get recommendation scores based on tag overlap."""
        try:
            # Find documents with overlapping tags
            overlapping = self.db.query(
                DocumentTag.document_id,
                func.count(DocumentTag.tag_id).label('tag_overlap')
            ).filter(
                DocumentTag.tag_id.in_(tag_ids),
                DocumentTag.document_id != exclude_document_id
            ).group_by(DocumentTag.document_id).limit(limit).all()

            scores = {}
            for doc_id, overlap_count in overlapping:
                score = overlap_count / len(tag_ids) if tag_ids else 0.0
                scores[doc_id] = score

            return scores

        except Exception as e:
            logger.error(f"Error in tag-based recommendation: {e}")
            return {}

    def _recommend_by_relationships(
        self,
        document_id: int,
        limit: int
    ) -> Dict[int, float]:
        """Get recommendation scores based on relationships."""
        try:
            # Get related documents
            relationships = self.db.query(DocumentRelationship).filter(
                DocumentRelationship.source_document_id == document_id
            ).limit(limit).all()

            scores = {}
            for rel in relationships:
                # Score based on relationship type and confidence
                type_scores = {
                    "citation": 0.9,
                    "prerequisite": 0.8,
                    "related": 0.7,
                    "version": 0.6,
                    "duplicate": 0.5
                }
                base_score = type_scores.get(rel.relationship_type, 0.5)
                final_score = base_score * rel.confidence
                scores[rel.target_document_id] = final_score

            return scores

        except Exception as e:
            logger.error(f"Error in relationship-based recommendation: {e}")
            return {}

    def _recommend_by_metadata(
        self,
        document: Document,
        limit: int
    ) -> Dict[int, float]:
        """Get recommendation scores based on metadata similarity."""
        try:
            # Find documents with similar source/type
            similar = self.db.query(Document).filter(
                Document.id != document.id,
                Document.status == "completed",
                Document.source == document.source
            ).limit(limit).all()

            scores = {}
            for doc in similar:
                # Simple similarity based on source match
                score = 0.3 if doc.source == document.source else 0.1
                
                # Boost if same file type
                if doc.filename and document.filename:
                    doc_ext = doc.filename.split('.')[-1] if '.' in doc.filename else ""
                    orig_ext = document.filename.split('.')[-1] if '.' in document.filename else ""
                    if doc_ext == orig_ext:
                        score += 0.2

                scores[doc.id] = score

            return scores

        except Exception as e:
            logger.error(f"Error in metadata-based recommendation: {e}")
            return {}

    def _get_recommendation_reason(
        self,
        recommended_doc_id: int,
        source_doc_id: int,
        score: float
    ) -> str:
        """Generate human-readable reason for recommendation."""
        reasons = []
        
        # Check tag overlap
        source_tags = {tag.get("tag_name") for tag in self.tag_manager.get_document_tags(source_doc_id)}
        rec_tags = {tag.get("tag_name") for tag in self.tag_manager.get_document_tags(recommended_doc_id)}
        common_tags = source_tags & rec_tags
        
        if common_tags:
            reasons.append(f"Shared tags: {', '.join(list(common_tags)[:3])}")
        
        # Check relationships
        if self.relationship_manager:
            rels = self.relationship_manager.get_document_relationships(source_doc_id)
            related_ids = {rel.get("target_document_id") for rel in rels.get("outgoing", [])}
            if recommended_doc_id in related_ids:
                reasons.append("Related document")
        
        if not reasons:
            reasons.append("Similar content")
        
        return "; ".join(reasons[:2])  # Max 2 reasons
