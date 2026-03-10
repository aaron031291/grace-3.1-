"""
TagManager - Tag Lifecycle Management

Handles creation, assignment, removal, and search of tags for documents.
Implements flat tag system where documents can have multiple tags.
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timezone
import logging

from models.librarian_models import LibrarianTag, DocumentTag
from models.database_models import Document
from librarian.utils import (
    normalize_tag_name,
    validate_tag_name,
    validate_hex_color,
    generate_default_color,
    deduplicate_list
)

logger = logging.getLogger(__name__)


class TagManager:
    """
    Manages tag lifecycle operations for the Librarian System.

    Responsibilities:
    - Create and manage tag definitions
    - Assign/remove tags from documents
    - Search documents by tags
    - Track tag usage statistics
    - Validate tag names and properties

    Example:
        >>> from database.session import SessionLocal
        >>> tag_manager = TagManager(SessionLocal())
        >>>
        >>> # Create or get tag
        >>> tag = tag_manager.get_or_create_tag("ai", description="Artificial Intelligence")
        >>>
        >>> # Assign tags to document
        >>> tag_manager.assign_tags(document_id=123, tag_names=["ai", "research"])
        >>>
        >>> # Search documents by tags
        >>> docs = tag_manager.search_documents_by_tags(["ai", "research"], match_all=True)
    """

    def __init__(self, db_session: Session):
        """
        Initialize TagManager.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def get_or_create_tag(
        self,
        name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        color: Optional[str] = None
    ) -> LibrarianTag:
        """
        Get existing tag or create new one if it doesn't exist.

        Args:
            name: Tag name (will be normalized to lowercase)
            description: Optional description
            category: Optional category (e.g., "ai", "research", "code")
            color: Optional hex color (e.g., "#3B82F6")

        Returns:
            LibrarianTag: Tag instance

        Raises:
            ValueError: If tag name is invalid or color format is wrong

        Example:
            >>> tag = tag_manager.get_or_create_tag(
            ...     "ai",
            ...     description="Artificial Intelligence topics",
            ...     category="technology",
            ...     color="#3B82F6"
            ... )
        """
        # Validate and normalize tag name
        if not validate_tag_name(name):
            raise ValueError(f"Invalid tag name: '{name}'. Must contain only alphanumeric characters, spaces, hyphens, and underscores.")

        normalized_name = normalize_tag_name(name)

        # Validate color if provided
        if color and not validate_hex_color(color):
            raise ValueError(f"Invalid color format: '{color}'. Must be hex format like #3B82F6")

        # Check if tag already exists
        existing_tag = self.db.query(LibrarianTag).filter(
            LibrarianTag.name == normalized_name
        ).first()

        if existing_tag:
            # Update fields if provided and different
            updated = False
            if description and existing_tag.description != description:
                existing_tag.description = description
                updated = True
            if category and existing_tag.category != category:
                existing_tag.category = category
                updated = True
            if color and existing_tag.color != color:
                existing_tag.color = color
                updated = True

            if updated:
                existing_tag.updated_at = datetime.now(timezone.utc)
                self.db.commit()
                logger.info(f"Updated tag: {normalized_name}")

            return existing_tag

        # Create new tag
        new_tag = LibrarianTag(
            name=normalized_name,
            description=description,
            category=category,
            color=color or generate_default_color(normalized_name),
            usage_count=0
        )

        self.db.add(new_tag)
        self.db.commit()
        self.db.refresh(new_tag)

        logger.info(f"Created new tag: {normalized_name}")
        return new_tag

    def assign_tags(
        self,
        document_id: int,
        tag_names: List[str],
        assigned_by: str = "auto",
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentTag]:
        """
        Assign multiple tags to a document.

        Creates tags if they don't exist. Skips tags already assigned.
        Updates usage_count for each tag.

        Args:
            document_id: Document ID
            tag_names: List of tag names to assign
            assigned_by: Who assigned the tags ("auto", "user", "ai", "rule")
            confidence: Confidence in tag assignment (0.0-1.0)
            metadata: Optional metadata (e.g., {"rule_id": 5, "ai_reasoning": "..."})

        Returns:
            List[DocumentTag]: List of document-tag assignments

        Raises:
            ValueError: If document doesn't exist

        Example:
            >>> assignments = tag_manager.assign_tags(
            ...     document_id=123,
            ...     tag_names=["ai", "research", "technical"],
            ...     assigned_by="rule",
            ...     confidence=0.95,
            ...     metadata={"rule_id": 5}
            ... )
        """
        # Verify document exists
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Deduplicate and normalize tag names
        unique_tag_names = deduplicate_list([normalize_tag_name(name) for name in tag_names])

        assignments = []

        for tag_name in unique_tag_names:
            try:
                # Get or create tag
                tag = self.get_or_create_tag(tag_name)

                # Check if assignment already exists
                existing_assignment = self.db.query(DocumentTag).filter(
                    and_(
                        DocumentTag.document_id == document_id,
                        DocumentTag.tag_id == tag.id
                    )
                ).first()

                if existing_assignment:
                    logger.debug(f"Tag '{tag_name}' already assigned to document {document_id}")
                    assignments.append(existing_assignment)
                    continue

                # Create new assignment
                assignment = DocumentTag(
                    document_id=document_id,
                    tag_id=tag.id,
                    assigned_by=assigned_by,
                    confidence=confidence,
                    assigned_at=datetime.now(timezone.utc),
                    assignment_metadata=metadata
                )

                self.db.add(assignment)

                # Increment tag usage count
                tag.usage_count += 1
                tag.updated_at = datetime.now(timezone.utc)

                assignments.append(assignment)
                logger.info(f"Assigned tag '{tag_name}' to document {document_id} (by: {assigned_by}, confidence: {confidence})")

            except ValueError as e:
                logger.warning(f"Failed to assign tag '{tag_name}': {e}")
                continue

        self.db.commit()
        return assignments

    def remove_tag(self, document_id: int, tag_name: str) -> bool:
        """
        Remove a tag from a document.

        Args:
            document_id: Document ID
            tag_name: Tag name to remove

        Returns:
            bool: True if removed, False if not found

        Example:
            >>> success = tag_manager.remove_tag(123, "deprecated")
        """
        normalized_name = normalize_tag_name(tag_name)

        # Find tag
        tag = self.db.query(LibrarianTag).filter(
            LibrarianTag.name == normalized_name
        ).first()

        if not tag:
            logger.warning(f"Tag '{tag_name}' not found")
            return False

        # Find and delete assignment
        assignment = self.db.query(DocumentTag).filter(
            and_(
                DocumentTag.document_id == document_id,
                DocumentTag.tag_id == tag.id
            )
        ).first()

        if not assignment:
            logger.warning(f"Tag '{tag_name}' not assigned to document {document_id}")
            return False

        self.db.delete(assignment)

        # Decrement usage count
        if tag.usage_count > 0:
            tag.usage_count -= 1
            tag.updated_at = datetime.now(timezone.utc)

        self.db.commit()

        logger.info(f"Removed tag '{tag_name}' from document {document_id}")
        return True

    def get_document_tags(self, document_id: int) -> List[Dict[str, Any]]:
        """
        Get all tags assigned to a document.

        Args:
            document_id: Document ID

        Returns:
            List[Dict]: List of tag dictionaries with metadata

        Example:
            >>> tags = tag_manager.get_document_tags(123)
            >>> for tag in tags:
            ...     print(f"{tag['name']}: {tag['confidence']}")
        """
        assignments = self.db.query(DocumentTag, LibrarianTag).join(
            LibrarianTag, DocumentTag.tag_id == LibrarianTag.id
        ).filter(
            DocumentTag.document_id == document_id
        ).all()

        return [
            {
                "id": tag.id,
                "name": tag.name,
                "description": tag.description,
                "color": tag.color,
                "category": tag.category,
                "assigned_by": assignment.assigned_by,
                "confidence": assignment.confidence,
                "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None
            }
            for assignment, tag in assignments
        ]

    def search_documents_by_tags(
        self,
        tag_names: List[str],
        match_all: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search documents by tags.

        Args:
            tag_names: List of tag names to search for
            match_all: If True, documents must have ALL tags (AND logic).
                      If False, documents need ANY tag (OR logic)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List[Dict]: List of documents with their tags

        Example:
            >>> # Find documents with AI OR research
            >>> docs = tag_manager.search_documents_by_tags(["ai", "research"], match_all=False)
            >>>
            >>> # Find documents with AI AND research
            >>> docs = tag_manager.search_documents_by_tags(["ai", "research"], match_all=True)
        """
        if not tag_names:
            return []

        # Normalize tag names
        normalized_names = [normalize_tag_name(name) for name in tag_names]

        # Get tag IDs
        tags = self.db.query(LibrarianTag).filter(
            LibrarianTag.name.in_(normalized_names)
        ).all()

        if not tags:
            return []

        tag_ids = [tag.id for tag in tags]

        if match_all:
            # AND logic: Find documents that have ALL specified tags
            # Use GROUP BY and HAVING COUNT
            query = self.db.query(Document).join(
                DocumentTag, Document.id == DocumentTag.document_id
            ).filter(
                DocumentTag.tag_id.in_(tag_ids)
            ).group_by(Document.id).having(
                func.count(DocumentTag.tag_id.distinct()) == len(tag_ids)
            )
        else:
            # OR logic: Find documents that have ANY of the specified tags
            query = self.db.query(Document).join(
                DocumentTag, Document.id == DocumentTag.document_id
            ).filter(
                DocumentTag.tag_id.in_(tag_ids)
            ).distinct()

        # Apply limit and offset
        query = query.limit(limit).offset(offset)

        documents = query.all()

        # Enrich with tag information
        results = []
        for doc in documents:
            doc_tags = self.get_document_tags(doc.id)
            results.append({
                "id": doc.id,
                "filename": doc.filename,
                "file_path": doc.file_path,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "tags": doc_tags,
                "tag_count": len(doc_tags)
            })

        return results

    def get_tag_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about tag usage.

        Returns:
            Dict: Statistics including total tags, most used, by category, etc.

        Example:
            >>> stats = tag_manager.get_tag_statistics()
            >>> print(f"Total tags: {stats['total_tags']}")
            >>> print(f"Most used: {stats['most_used'][0]['name']}")
        """
        total_tags = self.db.query(func.count(LibrarianTag.id)).scalar()

        # Get most used tags (top 10)
        most_used = self.db.query(LibrarianTag).order_by(
            LibrarianTag.usage_count.desc()
        ).limit(10).all()

        # Get tags by category
        categories = self.db.query(
            LibrarianTag.category,
            func.count(LibrarianTag.id)
        ).filter(
            LibrarianTag.category.isnot(None)
        ).group_by(LibrarianTag.category).all()

        # Get recently created tags
        recent_tags = self.db.query(LibrarianTag).order_by(
            LibrarianTag.created_at.desc()
        ).limit(10).all()

        return {
            "total_tags": total_tags,
            "most_used": [
                {
                    "id": tag.id,
                    "name": tag.name,
                    "usage_count": tag.usage_count,
                    "color": tag.color
                }
                for tag in most_used
            ],
            "by_category": {
                category: count for category, count in categories
            },
            "recent_tags": [
                {
                    "id": tag.id,
                    "name": tag.name,
                    "created_at": tag.created_at.isoformat() if tag.created_at else None
                }
                for tag in recent_tags
            ]
        }

    def delete_tag(self, tag_name: str, force: bool = False) -> bool:
        """
        Delete a tag and optionally its assignments.

        Args:
            tag_name: Tag name to delete
            force: If True, delete even if tag has assignments.
                   If False, only delete unused tags.

        Returns:
            bool: True if deleted, False if not found or has assignments

        Example:
            >>> # Delete unused tag
            >>> tag_manager.delete_tag("obsolete")
            >>>
            >>> # Force delete tag and all assignments
            >>> tag_manager.delete_tag("deprecated", force=True)
        """
        normalized_name = normalize_tag_name(tag_name)

        tag = self.db.query(LibrarianTag).filter(
            LibrarianTag.name == normalized_name
        ).first()

        if not tag:
            logger.warning(f"Tag '{tag_name}' not found")
            return False

        if not force and tag.usage_count > 0:
            logger.warning(f"Tag '{tag_name}' has {tag.usage_count} assignments. Use force=True to delete.")
            return False

        # Delete all assignments if force=True
        if force:
            self.db.query(DocumentTag).filter(
                DocumentTag.tag_id == tag.id
            ).delete()

        # Delete tag
        self.db.delete(tag)
        self.db.commit()

        logger.info(f"Deleted tag '{tag_name}' (force={force})")
        return True

    def update_tag(
        self,
        tag_name: str,
        new_name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        color: Optional[str] = None
    ) -> Optional[LibrarianTag]:
        """
        Update tag properties.

        Args:
            tag_name: Current tag name
            new_name: Optional new name
            description: Optional new description
            category: Optional new category
            color: Optional new color

        Returns:
            Optional[LibrarianTag]: Updated tag or None if not found

        Example:
            >>> tag = tag_manager.update_tag(
            ...     "ai",
            ...     description="Artificial Intelligence and Machine Learning",
            ...     color="#FF5733"
            ... )
        """
        normalized_name = normalize_tag_name(tag_name)

        tag = self.db.query(LibrarianTag).filter(
            LibrarianTag.name == normalized_name
        ).first()

        if not tag:
            logger.warning(f"Tag '{tag_name}' not found")
            return None

        # Update fields
        if new_name:
            if not validate_tag_name(new_name):
                raise ValueError(f"Invalid new tag name: '{new_name}'")
            tag.name = normalize_tag_name(new_name)

        if description is not None:
            tag.description = description

        if category is not None:
            tag.category = category

        if color:
            if not validate_hex_color(color):
                raise ValueError(f"Invalid color format: '{color}'")
            tag.color = color

        tag.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(tag)

        logger.info(f"Updated tag '{tag_name}'")
        return tag

    def list_all_tags(
        self,
        category: Optional[str] = None,
        min_usage: int = 0,
        sort_by: str = "name",
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List all tags with optional filtering and sorting.

        Args:
            category: Filter by category
            min_usage: Minimum usage count
            sort_by: Sort field ("name", "usage_count", "created_at")
            limit: Maximum number of results

        Returns:
            List[Dict]: List of tag dictionaries

        Example:
            >>> # Get all AI tags
            >>> ai_tags = tag_manager.list_all_tags(category="ai")
            >>>
            >>> # Get top used tags
            >>> popular = tag_manager.list_all_tags(sort_by="usage_count", limit=20)
        """
        query = self.db.query(LibrarianTag)

        # Apply filters
        if category:
            query = query.filter(LibrarianTag.category == category)

        if min_usage > 0:
            query = query.filter(LibrarianTag.usage_count >= min_usage)

        # Apply sorting
        if sort_by == "usage_count":
            query = query.order_by(LibrarianTag.usage_count.desc())
        elif sort_by == "created_at":
            query = query.order_by(LibrarianTag.created_at.desc())
        else:  # Default to name
            query = query.order_by(LibrarianTag.name)

        # Apply limit
        if limit:
            query = query.limit(limit)

        tags = query.all()

        return [
            {
                "id": tag.id,
                "name": tag.name,
                "description": tag.description,
                "color": tag.color,
                "category": tag.category,
                "usage_count": tag.usage_count,
                "created_at": tag.created_at.isoformat() if tag.created_at else None
            }
            for tag in tags
        ]
