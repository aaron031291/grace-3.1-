import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from models.database_models import Document
from librarian.tag_manager import TagManager
class FileCreator:
    logger = logging.getLogger(__name__)
    """
    File creation manager for librarian.

    Creates files based on templates and metadata:
    - Index files for folders
    - Summary files for document collections
    - README files for project structures
    - Metadata files
    """

    def __init__(
        self,
        db_session: Session,
        knowledge_base_path: str = "backend/knowledge_base"
    ):
        """
        Initialize file creator.

        Args:
            db_session: Database session
            knowledge_base_path: Root path to knowledge base
        """
        self.db = db_session
        self.kb_path = Path(knowledge_base_path)
        self.tag_manager = TagManager(db_session)

        logger.info("[FILE-CREATOR] Initialized")

    def create_index_file(
        self,
        folder_path: str,
        document_ids: Optional[List[int]] = None,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Create index file listing all documents in a folder.

        Args:
            folder_path: Folder path relative to knowledge base
            document_ids: Optional list of document IDs (if None, discovers from folder)
            include_metadata: Include document metadata in index

        Returns:
            Dict with creation result
        """
        try:
            # Get documents in folder
            if document_ids:
                documents = self.db.query(Document).filter(
                    Document.id.in_(document_ids)
                ).all()
            else:
                # Find documents in folder
                documents = self.db.query(Document).filter(
                    Document.file_path.like(f"{folder_path}%")
                ).all()

            # Build index content
            lines = [
                f"# Index: {folder_path}",
                f"\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                f"\nTotal Documents: {len(documents)}",
                "\n## Documents\n"
            ]

            for doc in documents:
                filename = doc.filename or "unknown"
                file_path = doc.file_path or ""
                created = doc.created_at.strftime('%Y-%m-%d') if doc.created_at else "unknown"

                lines.append(f"### {filename}")
                if file_path:
                    lines.append(f"- **Path:** `{file_path}`")
                lines.append(f"- **Created:** {created}")

                if include_metadata:
                    # Get tags
                    tags = self.tag_manager.get_document_tags(doc.id)
                    if tags:
                        tag_names = [tag.get("tag_name", "") for tag in tags[:5]]
                        lines.append(f"- **Tags:** {', '.join(tag_names)}")

                # Add excerpt if available
                if doc.content and len(doc.content) > 0:
                    excerpt = doc.content[:200].replace('\n', ' ').strip()
                    lines.append(f"- **Excerpt:** {excerpt}...")

                lines.append("")

            content = "\n".join(lines)

            # Write index file
            full_folder = self.kb_path / folder_path
            full_folder.mkdir(parents=True, exist_ok=True)
            index_file = full_folder / "INDEX.md"

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

    def create_summary_file(
        self,
        folder_path: str,
        document_ids: List[int],
        summary_type: str = "overview"
    ) -> Dict[str, Any]:
        """
        Create summary file for a collection of documents.

        Args:
            folder_path: Folder path relative to knowledge base
            document_ids: List of document IDs to summarize
            summary_type: Type of summary ("overview", "detailed", "tags")

        Returns:
            Dict with creation result
        """
        try:
            documents = self.db.query(Document).filter(
                Document.id.in_(document_ids)
            ).all()

            if not documents:
                return {"success": False, "error": "No documents found"}

            # Build summary based on type
            if summary_type == "tags":
                content = self._generate_tag_summary(documents)
            elif summary_type == "detailed":
                content = self._generate_detailed_summary(documents)
            else:
                content = self._generate_overview_summary(documents)

            # Write summary file
            full_folder = self.kb_path / folder_path
            full_folder.mkdir(parents=True, exist_ok=True)
            summary_file = full_folder / "SUMMARY.md"

            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Created summary file: {summary_file}")
            return {
                "success": True,
                "summary_path": str(summary_file.relative_to(self.kb_path)),
                "documents_count": len(documents)
            }

        except Exception as e:
            logger.error(f"Error creating summary file: {e}")
            return {"success": False, "error": str(e)}

    def create_readme_file(
        self,
        folder_path: str,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create README file for a folder/project.

        Args:
            folder_path: Folder path relative to knowledge base
            title: Optional title for README
            description: Optional description

        Returns:
            Dict with creation result
        """
        try:
            folder_name = os.path.basename(folder_path) or folder_path
            title = title or folder_name.title()

            lines = [
                f"# {title}",
                "",
                description or f"Collection of documents in {folder_path}",
                "",
                f"**Created:** {datetime.utcnow().strftime('%Y-%m-%d')}",
                "",
                "## Contents",
                "",
                "See INDEX.md for a complete list of documents.",
                ""
            ]

            content = "\n".join(lines)

            # Write README file
            full_folder = self.kb_path / folder_path
            full_folder.mkdir(parents=True, exist_ok=True)
            readme_file = full_folder / "README.md"

            # Don't overwrite existing README
            if readme_file.exists():
                return {
                    "success": False,
                    "error": "README.md already exists",
                    "readme_path": str(readme_file.relative_to(self.kb_path))
                }

            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Created README file: {readme_file}")
            return {
                "success": True,
                "readme_path": str(readme_file.relative_to(self.kb_path))
            }

        except Exception as e:
            logger.error(f"Error creating README file: {e}")
            return {"success": False, "error": str(e)}

    def scaffold_folder_structure(
        self,
        base_path: str,
        structure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Scaffold folder structure with README/index files.

        Args:
            base_path: Base folder path
            structure: Nested dict defining folder structure
                {
                    "folder1": {
                        "README.md": "...",
                        "subfolder": {...}
                    }
                }

        Returns:
            Dict with scaffold result
        """
        try:
            created = []
            errors = []

            def create_recursive(current_path: str, current_structure: Dict[str, Any]):
                full_path = self.kb_path / current_path
                full_path.mkdir(parents=True, exist_ok=True)

                for key, value in current_structure.items():
                    item_path = os.path.join(current_path, key)

                    if isinstance(value, dict):
                        # It's a folder - recurse
                        create_recursive(item_path, value)
                    elif isinstance(value, str):
                        # It's a file - create it
                        file_path = full_path / key
                        if not file_path.exists():
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(value)
                            created.append(item_path)
                        else:
                            errors.append(f"File already exists: {item_path}")

            create_recursive(base_path, structure)

            return {
                "success": True,
                "created": created,
                "errors": errors,
                "base_path": base_path
            }

        except Exception as e:
            logger.error(f"Error scaffolding folder structure: {e}")
            return {"success": False, "error": str(e)}

    def _generate_overview_summary(self, documents: List[Document]) -> str:
        """Generate overview summary."""
        lines = [
            "# Document Summary",
            f"\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"\nTotal Documents: {len(documents)}",
            "\n## Overview\n"
        ]

        # Group by extension
        by_ext = {}
        for doc in documents:
            ext = doc.filename.split('.')[-1] if '.' in doc.filename else "unknown"
            by_ext[ext] = by_ext.get(ext, 0) + 1

        lines.append("### By File Type")
        for ext, count in sorted(by_ext.items()):
            lines.append(f"- **{ext}:** {count} files")

        return "\n".join(lines)

    def _generate_tag_summary(self, documents: List[Document]) -> str:
        """Generate tag-based summary."""
        lines = [
            "# Document Summary - By Tags",
            f"\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"\nTotal Documents: {len(documents)}",
            "\n## Tags\n"
        ]

        # Collect all tags
        tag_counts = {}
        for doc in documents:
            tags = self.tag_manager.get_document_tags(doc.id)
            for tag in tags:
                tag_name = tag.get("tag_name", "")
                tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1

        # Sort by count
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

        for tag_name, count in sorted_tags[:20]:  # Top 20 tags
            lines.append(f"- **{tag_name}:** {count} documents")

        return "\n".join(lines)

    def _generate_detailed_summary(self, documents: List[Document]) -> str:
        """Generate detailed summary."""
        lines = [
            "# Detailed Document Summary",
            f"\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"\nTotal Documents: {len(documents)}",
            "\n## Documents\n"
        ]

        for doc in documents:
            filename = doc.filename or "unknown"
            created = doc.created_at.strftime('%Y-%m-%d') if doc.created_at else "unknown"

            lines.append(f"### {filename}")
            lines.append(f"- **Created:** {created}")
            if doc.file_path:
                lines.append(f"- **Path:** `{doc.file_path}`")

            tags = self.tag_manager.get_document_tags(doc.id)
            if tags:
                tag_names = [tag.get("tag_name", "") for tag in tags]
                lines.append(f"- **Tags:** {', '.join(tag_names)}")

            if doc.content:
                excerpt = doc.content[:300].replace('\n', ' ')
                lines.append(f"- **Content:** {excerpt}...")

            lines.append("")

        return "\n".join(lines)
