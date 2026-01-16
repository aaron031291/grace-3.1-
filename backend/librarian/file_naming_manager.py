"""
File Naming Manager - Naming Convention Enforcement for Librarian

Handles automatic file renaming based on:
- Content analysis
- Metadata
- Naming conventions
- Duplicate handling

Part of the full file system librarian capabilities.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from models.database_models import Document
from librarian.utils import sanitize_filename, extract_file_extension

logger = logging.getLogger(__name__)


class FileNamingManager:
    """
    File naming and renaming manager.

    Enforces naming conventions and automatically renames files based on:
    - Content analysis
    - Document metadata
    - Standard naming patterns
    - Duplicate detection
    """

    def __init__(
        self,
        db_session: Session,
        knowledge_base_path: str = "backend/knowledge_base",
        naming_convention: str = "sanitized",
        auto_rename: bool = False
    ):
        """
        Initialize file naming manager.

        Args:
            db_session: Database session
            knowledge_base_path: Root path to knowledge base
            naming_convention: Naming convention to enforce
                - "sanitized": Just sanitize invalid characters
                - "date_prefix": YYYY-MM-DD_filename.ext
                - "lowercase": lowercase_with_underscores.ext
                - "kebab_case": kebab-case-filename.ext
                - "descriptive": Generate descriptive names from content
            auto_rename: Enable automatic renaming (default: False)
        """
        self.db = db_session
        self.kb_path = Path(knowledge_base_path)
        self.naming_convention = naming_convention
        self.auto_rename = auto_rename

        logger.info(f"[FILE-NAMING] Initialized (convention={naming_convention}, auto_rename={auto_rename})")

    def suggest_filename(
        self,
        document_id: int,
        based_on: str = "content",
        max_length: int = 100
    ) -> Dict[str, Any]:
        """
        Suggest a better filename for a document.

        Args:
            document_id: Document ID
            based_on: What to base the name on ("content", "tags", "metadata", "current")
            max_length: Maximum filename length

        Returns:
            Dict with suggestion:
            {
                "suggested_filename": str,
                "current_filename": str,
                "confidence": float,
                "reason": str
            }
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found"
                }

            current_filename = document.filename or "unnamed"
            extension = extract_file_extension(current_filename) or ""

            if based_on == "content" and document.content:
                # Generate from content (first line or summary)
                suggested = self._generate_from_content(document.content, extension, max_length)
                confidence = 0.8
                reason = "Based on document content"
            elif based_on == "tags":
                # Generate from tags
                suggested = self._generate_from_tags(document_id, extension, max_length)
                confidence = 0.7
                reason = "Based on document tags"
            elif based_on == "metadata":
                # Generate from metadata
                suggested = self._generate_from_metadata(document, extension, max_length)
                confidence = 0.6
                reason = "Based on document metadata"
            else:
                # Just sanitize current filename
                suggested = self._apply_naming_convention(current_filename)
                confidence = 0.5
                reason = "Applied naming convention to current filename"

            return {
                "success": True,
                "suggested_filename": suggested,
                "current_filename": current_filename,
                "confidence": confidence,
                "reason": reason,
                "needs_rename": suggested != current_filename
            }

        except Exception as e:
            logger.error(f"Error suggesting filename for document {document_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def rename_file(
        self,
        document_id: int,
        new_filename: Optional[str] = None,
        auto_suggest: bool = True
    ) -> Dict[str, Any]:
        """
        Rename a document's file.

        Args:
            document_id: Document ID
            new_filename: Explicit new filename (if None, will suggest)
            auto_suggest: Automatically suggest if new_filename not provided

        Returns:
            Dict with rename result
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found"
                }

            current_path = document.file_path or ""
            current_filename = document.filename or "unnamed"

            # Determine new filename
            if new_filename:
                new_name = self._apply_naming_convention(new_filename)
            elif auto_suggest:
                suggestion = self.suggest_filename(document_id)
                if suggestion.get("success"):
                    new_name = suggestion["suggested_filename"]
                else:
                    new_name = self._apply_naming_convention(current_filename)
            else:
                new_name = self._apply_naming_convention(current_filename)

            # If same, no rename needed
            if new_name == current_filename:
                return {
                    "success": True,
                    "renamed": False,
                    "filename": current_filename,
                    "message": "Filename already follows convention"
                }

            # Build new path
            if current_path:
                current_dir = os.path.dirname(current_path)
                new_path = os.path.join(current_dir, new_name) if current_dir else new_name
            else:
                new_path = new_name

            # Rename file on filesystem
            file_renamed = False
            if current_path:
                current_full = self.kb_path / current_path
                new_full = self.kb_path / new_path

                if current_full.exists() and current_full.is_file():
                    # Check if target exists
                    if new_full.exists():
                        # Generate unique name
                        new_path = self._generate_unique_filename(new_path)
                        new_name = os.path.basename(new_path)
                        new_full = self.kb_path / new_path

                    # Rename file
                    current_full.rename(new_full)
                    file_renamed = True
                    logger.info(f"Renamed file: {current_path} -> {new_path}")

            # Update database
            document.filename = new_name
            document.file_path = new_path
            self.db.commit()

            return {
                "success": True,
                "renamed": True,
                "old_filename": current_filename,
                "new_filename": new_name,
                "old_path": current_path,
                "new_path": new_path,
                "file_renamed": file_renamed
            }

        except Exception as e:
            logger.error(f"Error renaming file for document {document_id}: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_from_content(self, content: str, extension: str, max_length: int) -> str:
        """Generate filename from document content."""
        # Extract first meaningful line (skip empty lines, headers)
        lines = content.split('\n')
        first_line = None

        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            # Skip markdown headers, empty lines, very short lines
            if line and not line.startswith('#') and len(line) > 10:
                first_line = line
                break

        if not first_line:
            first_line = lines[0] if lines else "document"

        # Extract words (alphanumeric)
        words = re.findall(r'\b[a-zA-Z0-9]{3,}\b', first_line.lower())
        if not words:
            words = ["document"]

        # Build filename from first few words
        filename = "_".join(words[:5])  # Max 5 words
        filename = filename[:max_length - len(extension) - 1] if extension else filename[:max_length]

        # Apply naming convention
        filename = self._apply_naming_convention(filename)

        # Add extension
        if extension:
            filename = f"{filename}.{extension}"

        return filename

    def _generate_from_tags(self, document_id: int, extension: str, max_length: int) -> str:
        """Generate filename from document tags."""
        from librarian.tag_manager import TagManager

        tag_manager = TagManager(self.db)
        tags = tag_manager.get_document_tags(document_id)

        # Use primary tags (first 3)
        tag_names = [tag.get("tag_name", "").lower() for tag in tags[:3]]
        if not tag_names:
            return f"document.{extension}" if extension else "document"

        # Combine tags
        filename = "_".join(tag_names)
        filename = filename[:max_length - len(extension) - 1] if extension else filename[:max_length]
        filename = self._apply_naming_convention(filename)

        if extension:
            filename = f"{filename}.{extension}"

        return filename

    def _generate_from_metadata(self, document: Document, extension: str, max_length: int) -> str:
        """Generate filename from document metadata."""
        # Use source or filename hint
        source = (document.source or "").lower()
        if source:
            # Extract meaningful parts
            words = re.findall(r'\b[a-zA-Z0-9]{3,}\b', source)
            if words:
                filename = "_".join(words[:3])
            else:
                filename = "document"
        else:
            filename = "document"

        filename = filename[:max_length - len(extension) - 1] if extension else filename[:max_length]
        filename = self._apply_naming_convention(filename)

        if extension:
            filename = f"{filename}.{extension}"

        return filename

    def _apply_naming_convention(self, filename: str) -> str:
        """Apply naming convention to filename."""
        # Extract extension first
        if '.' in filename:
            name_part, ext = filename.rsplit('.', 1)
            ext = f".{ext}"
        else:
            name_part = filename
            ext = ""

        # Apply convention
        convention = self.naming_convention.lower()

        if convention == "date_prefix":
            # YYYY-MM-DD_filename
            date_prefix = datetime.utcnow().strftime("%Y-%m-%d")
            name_part = f"{date_prefix}_{name_part}"

        elif convention == "lowercase":
            # lowercase_with_underscores
            name_part = re.sub(r'[^a-z0-9_]+', '_', name_part.lower())
            name_part = re.sub(r'_+', '_', name_part).strip('_')

        elif convention == "kebab_case":
            # kebab-case-filename
            name_part = re.sub(r'[^a-z0-9]+', '-', name_part.lower())
            name_part = re.sub(r'-+', '-', name_part).strip('-')

        elif convention == "sanitized":
            # Just sanitize invalid characters
            name_part = sanitize_filename(name_part)

        # Always sanitize for safety
        name_part = sanitize_filename(name_part)

        # Ensure not empty
        if not name_part:
            name_part = "document"

        return f"{name_part}{ext}"

    def _generate_unique_filename(self, file_path: str) -> str:
        """Generate unique filename if target exists (adds number suffix)."""
        if not file_path:
            return "document_1"

        # Split path and extension
        if '.' in file_path:
            name_part, ext = file_path.rsplit('.', 1)
            ext = f".{ext}"
        else:
            name_part = file_path
            ext = ""

        # Try numbered versions
        counter = 1
        while True:
            candidate = f"{name_part}_{counter}{ext}"
            full_path = self.kb_path / candidate
            if not full_path.exists():
                return candidate
            counter += 1

            # Safety limit
            if counter > 1000:
                # Use timestamp as fallback
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                return f"{name_part}_{timestamp}{ext}"

    def batch_rename(
        self,
        document_ids: List[int],
        naming_convention: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Batch rename multiple documents.

        Args:
            document_ids: List of document IDs
            naming_convention: Optional convention override

        Returns:
            Dict with batch rename results
        """
        if naming_convention:
            old_convention = self.naming_convention
            self.naming_convention = naming_convention

        results = []
        success_count = 0

        for doc_id in document_ids:
            result = self.rename_file(doc_id, auto_suggest=True)
            results.append({
                "document_id": doc_id,
                "success": result.get("success", False),
                "renamed": result.get("renamed", False),
                "new_filename": result.get("new_filename")
            })
            if result.get("success"):
                success_count += 1

        if naming_convention:
            self.naming_convention = old_convention

        return {
            "total": len(document_ids),
            "successful": success_count,
            "failed": len(document_ids) - success_count,
            "results": results
        }
