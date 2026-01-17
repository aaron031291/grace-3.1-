import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.database_models import Document
class ContentLifecycleManager:
    logger = logging.getLogger(__name__)
    """
    Content lifecycle management.

    Manages content stages and policies:
    - Automatic archival of old documents
    - Content expiration for temporary files
    - Retention policy enforcement
    - Lifecycle stage transitions
    """

    def __init__(
        self,
        db_session: Session,
        knowledge_base_path: str = "backend/knowledge_base",
        archive_path: str = "documents/archive"
    ):
        """
        Initialize lifecycle manager.

        Args:
            db_session: Database session
            knowledge_base_path: Root path to knowledge base
            archive_path: Path for archived documents
        """
        self.db = db_session
        self.kb_path = Path(knowledge_base_path)
        self.archive_path = archive_path

        logger.info(f"[LIFECYCLE-MANAGER] Initialized (archive_path={archive_path})")

    def archive_old_documents(
        self,
        age_days: int = 365,
        min_confidence: float = 0.0,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Archive documents older than specified age.

        Args:
            age_days: Age threshold in days
            min_confidence: Only archive documents below this confidence
            dry_run: If True, don't actually archive (just report)

        Returns:
            Dict with archival results
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=age_days)

            # Find old documents
            old_documents = self.db.query(Document).filter(
                and_(
                    Document.status == "completed",
                    Document.created_at < cutoff_date,
                    Document.confidence_score < min_confidence
                )
            ).all()

            archived = []
            errors = []

            for doc in old_documents:
                try:
                    # Determine archive location
                    archive_subfolder = self._get_archive_subfolder(doc.created_at)
                    archive_folder = os.path.join(self.archive_path, archive_subfolder)

                    if not dry_run:
                        # Move file to archive
                        if doc.file_path:
                            success = self._move_to_archive(doc, archive_folder)
                            if success:
                                # Update document metadata
                                # Could add archive_path field or use document_metadata
                                archived.append({
                                    "document_id": doc.id,
                                    "filename": doc.filename,
                                    "archive_path": os.path.join(archive_folder, os.path.basename(doc.file_path or doc.filename))
                                })
                            else:
                                errors.append({"document_id": doc.id, "error": "Failed to move file"})
                        else:
                            archived.append({
                                "document_id": doc.id,
                                "filename": doc.filename,
                                "note": "No file path to archive"
                            })
                    else:
                        # Dry run - just report
                        archived.append({
                            "document_id": doc.id,
                            "filename": doc.filename,
                            "would_archive_to": os.path.join(archive_folder, doc.filename)
                        })

                except Exception as e:
                    errors.append({"document_id": doc.id, "error": str(e)})

            return {
                "success": True,
                "dry_run": dry_run,
                "archived_count": len(archived),
                "errors_count": len(errors),
                "archived": archived,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Error archiving old documents: {e}")
            return {
                "success": False,
                "error": str(e),
                "archived_count": 0
            }

    def expire_temporary_documents(
        self,
        expiration_days: int = 30,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Delete or archive temporary documents after expiration.

        Args:
            expiration_days: Days before expiration
            dry_run: If True, don't actually expire (just report)

        Returns:
            Dict with expiration results
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=expiration_days)

            # Find temporary documents (based on source or tags)
            # Could extend Document model with is_temporary flag
            temp_documents = self.db.query(Document).filter(
                and_(
                    Document.status == "completed",
                    Document.created_at < cutoff_date,
                    # Temporary documents might have specific source or tags
                    # This is a simplified check - could be enhanced
                    Document.source.in_(["temporary", "upload"])  # Example
                )
            ).all()

            expired = []
            errors = []

            for doc in temp_documents:
                try:
                    if not dry_run:
                        # Archive rather than delete
                        archive_folder = os.path.join(self.archive_path, "expired")
                        success = self._move_to_archive(doc, archive_folder)
                        
                        if success:
                            expired.append({
                                "document_id": doc.id,
                                "filename": doc.filename,
                                "action": "archived"
                            })
                        else:
                            errors.append({"document_id": doc.id, "error": "Failed to archive"})
                    else:
                        expired.append({
                            "document_id": doc.id,
                            "filename": doc.filename,
                            "would_expire": True
                        })

                except Exception as e:
                    errors.append({"document_id": doc.id, "error": str(e)})

            return {
                "success": True,
                "dry_run": dry_run,
                "expired_count": len(expired),
                "errors_count": len(errors),
                "expired": expired,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Error expiring temporary documents: {e}")
            return {
                "success": False,
                "error": str(e),
                "expired_count": 0
            }

    def apply_retention_policies(
        self,
        policies: List[Dict[str, Any]],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Apply retention policies to documents.

        Policies format:
        [
            {
                "condition": {"source": "temporary", "age_days": 30},
                "action": "archive",
                "target": "archive/temporary"
            },
            {
                "condition": {"confidence_score": {"lt": 0.3}, "age_days": 90},
                "action": "archive",
                "target": "archive/low_confidence"
            }
        ]

        Args:
            policies: List of retention policies
            dry_run: If True, don't actually apply (just report)

        Returns:
            Dict with policy application results
        """
        try:
            results = {
                "success": True,
                "dry_run": dry_run,
                "policies_applied": [],
                "total_affected": 0
            }

            for policy in policies:
                condition = policy.get("condition", {})
                action = policy.get("action", "archive")
                target = policy.get("target", self.archive_path)

                # Build query from condition
                query = self.db.query(Document).filter(Document.status == "completed")
                
                # Apply age condition
                if "age_days" in condition:
                    cutoff_date = datetime.utcnow() - timedelta(days=condition["age_days"])
                    query = query.filter(Document.created_at < cutoff_date)

                # Apply source condition
                if "source" in condition:
                    query = query.filter(Document.source == condition["source"])

                # Apply confidence condition
                if "confidence_score" in condition:
                    conf_condition = condition["confidence_score"]
                    if isinstance(conf_condition, dict):
                        if "lt" in conf_condition:
                            query = query.filter(Document.confidence_score < conf_condition["lt"])
                        elif "gt" in conf_condition:
                            query = query.filter(Document.confidence_score > conf_condition["gt"])

                matching_docs = query.all()

                affected = []
                for doc in matching_docs:
                    if not dry_run and action == "archive":
                        success = self._move_to_archive(doc, target)
                        if success:
                            affected.append(doc.id)

                results["policies_applied"].append({
                    "policy": policy,
                    "documents_affected": len(affected),
                    "document_ids": affected
                })
                results["total_affected"] += len(affected)

            return results

        except Exception as e:
            logger.error(f"Error applying retention policies: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _move_to_archive(self, document: Document, archive_folder: str) -> bool:
        """Move document file to archive folder."""
        try:
            if not document.file_path:
                return False

            source_path = self.kb_path / document.file_path
            if not source_path.exists():
                return False

            # Create archive folder
            archive_full = self.kb_path / archive_folder
            archive_full.mkdir(parents=True, exist_ok=True)

            # Build target path
            filename = os.path.basename(document.file_path)
            target_path = archive_full / filename

            # Handle duplicates
            if target_path.exists():
                # Add timestamp
                base, ext = os.path.splitext(filename)
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"{base}_{timestamp}{ext}"
                target_path = archive_full / filename

            # Move file
            source_path.rename(target_path)

            # Update document path
            document.file_path = os.path.join(archive_folder, filename)
            self.db.commit()

            logger.info(f"Archived document {document.id}: {document.file_path} -> {archive_folder}/{filename}")
            return True

        except Exception as e:
            logger.error(f"Error moving document to archive: {e}")
            self.db.rollback()
            return False

    def _get_archive_subfolder(self, created_at: datetime) -> str:
        """Get archive subfolder based on creation date."""
        # Organize archive by year/month
        return created_at.strftime("%Y/%m") if created_at else "unknown"
