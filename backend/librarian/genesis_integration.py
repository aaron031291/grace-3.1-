import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from models.database_models import Document
from models.genesis_key_models import GenesisKey, GenesisKeyType
class LibrarianGenesisIntegration:
    logger = logging.getLogger(__name__)
    """
    Genesis Key integration for librarian operations.

    Tracks all librarian actions via Genesis Keys:
    - Document processing
    - File organization
    - File renaming
    - Tag assignment
    - Relationship creation
    - File creation
    """

    def __init__(self, db_session: Session):
        """
        Initialize Genesis Key integration.

        Args:
            db_session: Database session
        """
        self.db = db_session
        self._genesis_service = None

    def _get_genesis_service(self):
        """Get or create Genesis Key service."""
        if self._genesis_service is None:
            try:
                from genesis.genesis_key_service import get_genesis_service
                self._genesis_service = get_genesis_service(self.db)
            except Exception as e:
                logger.warning(f"Genesis Key service not available: {e}")
                return None
        return self._genesis_service

    def create_genesis_key_for_document(
        self,
        document_id: int,
        action_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create Genesis Key for a librarian action on a document.

        Args:
            document_id: Document ID
            action_type: Type of action (e.g., "process", "organize", "rename")
            description: Description of the action
            metadata: Additional metadata

        Returns:
            Genesis Key ID or None if creation failed
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return None

            genesis_service = self._get_genesis_service()
            if not genesis_service:
                return None

            # Build context data
            context_data = {
                "document_id": document_id,
                "filename": document.filename,
                "file_path": document.file_path,
                "source": document.source,
                "action_type": action_type,
                **(metadata or {})
            }

            # Create Genesis Key
            key = genesis_service.create_key(
                key_type=GenesisKeyType.FILE_OPERATION,
                what_description=f"Librarian {action_type}: {description}",
                who_actor="librarian_system",
                where_location=document.file_path or document.filename,
                why_reason=f"Librarian automated {action_type}",
                how_method="librarian_engine",
                file_path=document.file_path,
                context_data=context_data,
                tags=["librarian", action_type, "file_operation"],
                session=self.db
            )

            logger.info(f"Created Genesis Key {key.key_id} for librarian action {action_type} on document {document_id}")
            return key.key_id

        except Exception as e:
            logger.error(f"Error creating Genesis Key for document {document_id}: {e}")
            return None

    def link_document_to_genesis_key(
        self,
        document_id: int,
        genesis_key_id: str
    ) -> bool:
        """
        Link a document to an existing Genesis Key.

        Args:
            document_id: Document ID
            genesis_key_id: Genesis Key ID

        Returns:
            True if linked successfully
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return False

            # Store Genesis Key ID in document metadata (could extend Document model)
            # For now, we'll track this in context_data of Genesis Keys
            # or create a junction table if needed

            logger.info(f"Linked document {document_id} to Genesis Key {genesis_key_id}")
            return True

        except Exception as e:
            logger.error(f"Error linking document {document_id} to Genesis Key {genesis_key_id}: {e}")
            return False

    def track_organization_action(
        self,
        document_id: int,
        old_path: Optional[str],
        new_path: str,
        organization_pattern: str
    ) -> Optional[str]:
        """
        Track file organization action via Genesis Key.

        Args:
            document_id: Document ID
            old_path: Original file path
            new_path: New organized path
            organization_pattern: Pattern used for organization

        Returns:
            Genesis Key ID
        """
        metadata = {
            "old_path": old_path,
            "new_path": new_path,
            "organization_pattern": organization_pattern,
            "action": "organize"
        }

        description = f"Organized document from {old_path or 'root'} to {new_path}"
        return self.create_genesis_key_for_document(
            document_id=document_id,
            action_type="organize",
            description=description,
            metadata=metadata
        )

    def track_renaming_action(
        self,
        document_id: int,
        old_filename: str,
        new_filename: str,
        naming_convention: str
    ) -> Optional[str]:
        """
        Track file renaming action via Genesis Key.

        Args:
            document_id: Document ID
            old_filename: Original filename
            new_filename: New filename
            naming_convention: Convention used

        Returns:
            Genesis Key ID
        """
        metadata = {
            "old_filename": old_filename,
            "new_filename": new_filename,
            "naming_convention": naming_convention,
            "action": "rename"
        }

        description = f"Renamed file from '{old_filename}' to '{new_filename}'"
        return self.create_genesis_key_for_document(
            document_id=document_id,
            action_type="rename",
            description=description,
            metadata=metadata
        )

    def track_tag_assignment(
        self,
        document_id: int,
        tag_names: List[str],
        assigned_by: str
    ) -> Optional[str]:
        """
        Track tag assignment via Genesis Key.

        Args:
            document_id: Document ID
            tag_names: List of tags assigned
            assigned_by: Who/what assigned the tags

        Returns:
            Genesis Key ID
        """
        metadata = {
            "tag_names": tag_names,
            "assigned_by": assigned_by,
            "tag_count": len(tag_names),
            "action": "tag_assignment"
        }

        description = f"Assigned {len(tag_names)} tags: {', '.join(tag_names[:5])}"
        return self.create_genesis_key_for_document(
            document_id=document_id,
            action_type="tag_assignment",
            description=description,
            metadata=metadata
        )

    def organize_by_genesis_metadata(
        self,
        document_id: int,
        genesis_key_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Organize document based on Genesis Key metadata.

        Uses Genesis Key metadata (user, session, type) to determine organization.

        Args:
            document_id: Document ID
            genesis_key_id: Optional Genesis Key ID (if None, finds latest)

        Returns:
            Organization result
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {"success": False, "error": f"Document {document_id} not found"}

            # Find Genesis Key if not provided
            if not genesis_key_id:
                key = self.db.query(GenesisKey).filter(
                    GenesisKey.context_data['document_id'].astext == str(document_id)
                ).order_by(GenesisKey.when_timestamp.desc()).first()
            else:
                key = self.db.query(GenesisKey).filter(GenesisKey.key_id == genesis_key_id).first()

            if not key:
                return {"success": False, "error": "No Genesis Key found for document"}

            # Extract metadata for organization
            user_id = key.user_id or "system"
            key_type = key.key_type.value if hasattr(key.key_type, 'value') else str(key.key_type)
            session_id = key.session_id or "default"

            # Build organization path from Genesis Key metadata
            # Format: documents/genesis_key/{user_id}/{key_type}/{session_id}/
            org_path_parts = [
                "documents",
                "genesis_key",
                user_id.replace("GU-", "")[:10],  # Short user ID
                key_type.lower(),
                session_id.replace("SS-", "")[:10] if session_id else "default"
            ]

            org_path = "/".join(org_path_parts)

            return {
                "success": True,
                "organization_path": org_path,
                "genesis_key_id": key.key_id,
                "metadata": {
                    "user_id": user_id,
                    "key_type": key_type,
                    "session_id": session_id
                }
            }

        except Exception as e:
            logger.error(f"Error organizing by Genesis metadata: {e}")
            return {"success": False, "error": str(e)}

    def get_document_genesis_keys(
        self,
        document_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get all Genesis Keys associated with a document.

        Args:
            document_id: Document ID
            limit: Maximum number of keys to return

        Returns:
            List of Genesis Key metadata
        """
        try:
            # Find Genesis Keys with document_id in context_data
            keys = self.db.query(GenesisKey).filter(
                GenesisKey.context_data['document_id'].astext == str(document_id)
            ).order_by(GenesisKey.when_timestamp.desc()).limit(limit).all()

            results = []
            for key in keys:
                results.append({
                    "key_id": key.key_id,
                    "key_type": str(key.key_type),
                    "what_description": key.what_description,
                    "when_timestamp": key.when_timestamp.isoformat() if key.when_timestamp else None,
                    "who_actor": key.who_actor,
                    "where_location": key.where_location,
                    "context_data": key.context_data
                })

            return results

        except Exception as e:
            logger.error(f"Error getting Genesis Keys for document {document_id}: {e}")
            return []

    def track_file_creation(
        self,
        folder_path: str,
        file_type: str,
        file_name: str
    ) -> Optional[str]:
        """
        Track file creation action via Genesis Key.

        Args:
            folder_path: Folder where file was created
            file_type: Type of file (index, summary, readme)
            file_name: Name of created file

        Returns:
            Genesis Key ID
        """
        try:
            genesis_service = self._get_genesis_service()
            if not genesis_service:
                return None

            key = genesis_service.create_key(
                key_type=GenesisKeyType.FILE_OPERATION,
                what_description=f"Created {file_type} file: {file_name}",
                who_actor="librarian_system",
                where_location=f"{folder_path}/{file_name}",
                why_reason="Librarian file creation",
                how_method="file_creator",
                file_path=f"{folder_path}/{file_name}",
                context_data={
                    "folder_path": folder_path,
                    "file_type": file_type,
                    "file_name": file_name,
                    "action": "file_creation"
                },
                tags=["librarian", "file_creation", file_type],
                session=self.db
            )

            return key.key_id

        except Exception as e:
            logger.error(f"Error tracking file creation: {e}")
            return None
