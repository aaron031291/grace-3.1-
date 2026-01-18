import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from models.database_models import Document
from librarian.tag_manager import TagManager
from librarian.utils import sanitize_filename, extract_file_extension
logger = logging.getLogger(__name__)

class FileOrganizer:
    """
    Automatic file organization manager.

    Organizes files into folder structures based on categorization:
    - By tag/category: documents/ai/research/
    - By file type: documents/pdf/
    - By date: documents/2025/01/
    - Combined: documents/ai/research/2025/01/

    Supports automatic folder creation and safe file moving.
    """

    def __init__(
        self,
        db_session: Session,
        knowledge_base_path: str = "backend/knowledge_base",
        auto_organize: bool = True,
        organization_pattern: str = "category/type"
    ):
        """
        Initialize file organizer.

        Args:
            db_session: Database session
            knowledge_base_path: Root path to knowledge base
            auto_organize: Enable automatic organization (default: True)
            organization_pattern: Pattern for folder structure
                - "category/type": Organize by category then file type
                - "type/category": Organize by file type then category
                - "date/category": Organize by date then category
                - "category/date": Organize by category then date
        """
        self.db = db_session
        self.kb_path = Path(knowledge_base_path)
        self.auto_organize = auto_organize
        self.organization_pattern = organization_pattern
        self.tag_manager = TagManager(db_session)

        logger.info(f"[FILE-ORGANIZER] Initialized (auto_organize={auto_organize}, pattern={organization_pattern})")

    def organize_document(
        self,
        document_id: int,
        target_folder: Optional[str] = None,
        auto_create_folders: bool = True
    ) -> Dict[str, Any]:
        """
        Organize a document into appropriate folder structure.

        Args:
            document_id: Document ID to organize
            target_folder: Optional explicit target folder (overrides auto-organization)
            auto_create_folders: Automatically create folders if missing (default: True)

        Returns:
            Dict with organization result:
            {
                "success": bool,
                "target_path": str,
                "folder_created": bool,
                "file_moved": bool,
                "organization_path": str
            }
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found"
                }

            # Determine target folder
            if target_folder:
                org_path = target_folder
            else:
                org_path = self._generate_organization_path(document)

            # Create folder structure if needed
            folder_created = False
            if auto_create_folders:
                folder_created = self._ensure_folder_structure(org_path)

            # Move file if necessary
            current_path = document.file_path or ""
            target_file_path = os.path.join(org_path, os.path.basename(current_path) if current_path else document.filename)

            file_moved = False
            if current_path and current_path != target_file_path:
                if self._move_file_safe(current_path, target_file_path):
                    document.file_path = target_file_path
                    self.db.commit()
                    file_moved = True
                    logger.info(f"Moved file: {current_path} -> {target_file_path}")

            return {
                "success": True,
                "target_path": org_path,
                "folder_created": folder_created,
                "file_moved": file_moved,
                "organization_path": org_path
            }

        except Exception as e:
            logger.error(f"Error organizing document {document_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_organization_path(self, document: Document) -> str:
        """
        Generate organization path based on document metadata and organization pattern.

        Args:
            document: Document to organize

        Returns:
            str: Relative path for organization (e.g., "documents/ai/research/")
        """
        # Get document tags
        tags = self.tag_manager.get_document_tags(document.id)
        tag_names = [tag["tag_name"].lower() for tag in tags]

        # Extract file type
        file_type = extract_file_extension(document.filename or "")
        if not file_type:
            file_type = "unknown"

        # Get primary category from tags
        category = self._extract_primary_category(tag_names)

        # Generate path based on pattern
        pattern = self.organization_pattern.lower()

        if pattern == "category/type":
            path_parts = [category or "general", file_type]
        elif pattern == "type/category":
            path_parts = [file_type, category or "general"]
        elif pattern == "date/category":
            date_part = datetime.utcnow().strftime("%Y/%m")
            path_parts = [date_part, category or "general"]
        elif pattern == "category/date":
            date_part = datetime.utcnow().strftime("%Y/%m")
            path_parts = [category or "general", date_part]
        elif pattern == "category/type/date":
            # 3-level: category/type/date
            date_part = datetime.utcnow().strftime("%Y-%m")
            path_parts = [category or "general", file_type, date_part]
        elif pattern == "date/category/type":
            # 3-level: date/category/type
            date_part = datetime.utcnow().strftime("%Y/%m")
            path_parts = [date_part, category or "general", file_type]
        elif pattern == "tags/hierarchy":
            # Multi-level based on tags: tag1/tag2/tag3
            # Use top 3 tags as folder hierarchy
            path_parts = tag_names[:3] if tag_names else [category or "general"]
        elif pattern == "category/tags":
            # Category then tags: category/tag1/tag2
            path_parts = [category or "general"]
            if tag_names:
                path_parts.extend(tag_names[:2])  # Add up to 2 more tag levels
        else:
            # Default: category/type
            path_parts = [category or "general", file_type]

        # Sanitize path parts (flatten date patterns like "2025/01" -> ["2025", "01"])
        sanitized_parts = []
        for part in path_parts:
            # If part contains "/" (like date patterns), split it
            if "/" in part:
                sanitized_parts.extend([sanitize_filename(p) for p in part.split("/")])
            else:
                sanitized_parts.append(sanitize_filename(part))

        # Build full path
        org_path = os.path.join("documents", *sanitized_parts)

        return org_path

    def _extract_primary_category(self, tag_names: List[str]) -> Optional[str]:
        """
        Extract primary category from tag names.

        Common categories:
        - ai, research, code, documentation, tutorial, etc.

        Args:
            tag_names: List of tag names

        Returns:
            Optional[str]: Primary category name or None
        """
        # Priority order for categories
        category_priority = [
            "ai", "research", "code", "documentation",
            "tutorial", "paper", "article", "note",
            "reference", "guide", "manual"
        ]

        tag_set = set(tag_names)

        # Find first matching category
        for category in category_priority:
            if category in tag_set:
                return category

        # Check tag categories from database
        if tag_names:
            # Use first tag as fallback
            return tag_names[0].replace(" ", "_").replace("-", "_")

        return None

    def _ensure_folder_structure(self, relative_path: str) -> bool:
        """
        Ensure folder structure exists.

        Args:
            relative_path: Relative path from knowledge base root

        Returns:
            bool: True if folders were created, False if already existed
        """
        try:
            full_path = self.kb_path / relative_path
            if full_path.exists():
                return False

            full_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created folder structure: {relative_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating folder structure {relative_path}: {e}")
            return False

    def _move_file_safe(self, source_path: str, target_path: str) -> bool:
        """
        Move file safely with error handling.

        Args:
            source_path: Source file path (relative to knowledge base)
            target_path: Target file path (relative to knowledge base)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            source_full = self.kb_path / source_path
            target_full = self.kb_path / target_path

            # Ensure target directory exists
            target_full.parent.mkdir(parents=True, exist_ok=True)

            # Check if source exists
            if not source_full.exists():
                logger.warning(f"Source file does not exist: {source_path}")
                return False

            # Check if target already exists
            if target_full.exists():
                logger.warning(f"Target file already exists: {target_path}")
                # Could implement versioning here (file (1).ext, file (2).ext)
                return False

            # Move file
            source_full.rename(target_full)
            logger.info(f"Moved file: {source_path} -> {target_path}")
            return True

        except Exception as e:
            logger.error(f"Error moving file {source_path} to {target_path}: {e}")
            return False

    def organize_by_tags(
        self,
        document_id: int,
        tag_names: List[str],
        base_path: str = "documents",
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Organize document based on specific tags creating nested subfolders.

        Args:
            document_id: Document ID
            tag_names: List of tags to use for organization (creates nested folders)
            base_path: Base path for organization (default: "documents")
            max_depth: Maximum folder depth (default: 5)

        Returns:
            Dict with organization result

        Example:
            >>> organize_by_tags(123, ["ai", "research", "papers"])
            >>> # Creates: documents/ai/research/papers/document.pdf
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {"success": False, "error": f"Document {document_id} not found"}

            # Build nested path from tags (up to max_depth levels)
            tag_path_parts = [sanitize_filename(tag.lower()) for tag in tag_names[:max_depth]]
            org_path = os.path.join(base_path, *tag_path_parts)

            return self.organize_document(document_id, target_folder=org_path)

        except Exception as e:
            logger.error(f"Error organizing by tags: {e}")
            return {"success": False, "error": str(e)}

    def organize_into_subfolder(
        self,
        document_id: int,
        folder_hierarchy: List[str],
        base_path: str = "documents"
    ) -> Dict[str, Any]:
        """
        Organize document into specific subfolder hierarchy.

        Args:
            document_id: Document ID
            folder_hierarchy: List of folder names creating nested structure
                            e.g., ["ai", "research", "papers"] creates ai/research/papers/
            base_path: Base path for organization (default: "documents")

        Returns:
            Dict with organization result

        Example:
            >>> organize_into_subfolder(123, ["ai", "research", "2025"])
            >>> # Creates: documents/ai/research/2025/document.pdf
        """
        try:
            # Build nested path from hierarchy
            sanitized_parts = [sanitize_filename(part) for part in folder_hierarchy]
            org_path = os.path.join(base_path, *sanitized_parts)

            return self.organize_document(document_id, target_folder=org_path)

        except Exception as e:
            logger.error(f"Error organizing into subfolder: {e}")
            return {"success": False, "error": str(e)}

    def create_index_file(
        self,
        folder_path: str,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create index file for a folder listing all documents.

        Args:
            folder_path: Folder path relative to knowledge base
            documents: List of document metadata dicts

        Returns:
            Dict with creation result
        """
        try:
            full_folder = self.kb_path / folder_path
            index_file = full_folder / "INDEX.md"

            # Generate index content
            lines = [
                f"# Index: {folder_path}",
                f"\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                f"\nTotal Documents: {len(documents)}",
                "\n## Documents\n"
            ]

            for doc in documents:
                filename = doc.get("filename", "unknown")
                file_path = doc.get("file_path", "")
                tags = doc.get("tags", [])
                tag_str = ", ".join([tag.get("tag_name", "") for tag in tags[:5]])

                lines.append(f"- **{filename}**")
                if file_path:
                    lines.append(f"  - Path: `{file_path}`")
                if tag_str:
                    lines.append(f"  - Tags: {tag_str}")
                lines.append("")

            content = "\n".join(lines)

            # Write index file
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Created index file: {index_file}")
            return {
                "success": True,
                "index_path": str(index_file.relative_to(self.kb_path)),
                "documents_count": len(documents)
            }

        except Exception as e:
            logger.error(f"Error creating index file: {e}")
            return {"success": False, "error": str(e)}

    def get_organization_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about file organization.

        Returns:
            Dict with organization statistics
        """
        try:
            documents = self.db.query(Document).filter(
                Document.file_path.isnot(None)
            ).all()

            organized = {}
            for doc in documents:
                if doc.file_path:
                    # Extract organization level (first 2 path components)
                    parts = doc.file_path.split(os.sep)
                    if len(parts) >= 2:
                        org_key = os.sep.join(parts[:2])
                        organized[org_key] = organized.get(org_key, 0) + 1

            return {
                "total_organized": len([d for d in documents if d.file_path and os.sep in d.file_path]),
                "by_organization": organized,
                "total_documents": len(documents)
            }

        except Exception as e:
            logger.error(f"Error getting organization statistics: {e}")
            return {"error": str(e)}
