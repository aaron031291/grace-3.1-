import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.database_models import Document
logger = logging.getLogger(__name__)

class ContentIntegrityVerifier:
    """
    Content integrity verification system.

    Verifies documents using SHA-256 hashing:
    - Compare file hash with stored hash
    - Detect corruption or tampering
    - Batch verification
    - Integrity reporting
    """

    def __init__(
        self,
        db_session: Session,
        knowledge_base_path: str = "backend/knowledge_base"
    ):
        """
        Initialize integrity verifier.

        Args:
            db_session: Database session
            knowledge_base_path: Root path to knowledge base
        """
        self.db = db_session
        self.kb_path = Path(knowledge_base_path)

        logger.info("[INTEGRITY-VERIFIER] Initialized")

    def verify_document_integrity(
        self,
        document_id: int,
        recompute_hash: bool = True
    ) -> Dict[str, Any]:
        """
        Verify integrity of a single document.

        Args:
            document_id: Document ID
            recompute_hash: Recompute hash from file (default: True)

        Returns:
            Dict with verification result
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found"
                }

            stored_hash = document.content_hash

            if not stored_hash:
                return {
                    "success": False,
                    "error": "No stored hash for document",
                    "document_id": document_id
                }

            # Get file path
            if not document.file_path:
                return {
                    "success": False,
                    "error": "No file path for document",
                    "document_id": document_id
                }

            file_path = self.kb_path / document.file_path

            if not file_path.exists():
                return {
                    "success": False,
                    "error": "File does not exist",
                    "document_id": document_id,
                    "file_path": document.file_path
                }

            # Recompute hash if requested
            if recompute_hash:
                computed_hash = self._compute_file_hash(file_path)
            else:
                computed_hash = stored_hash

            # Compare hashes
            hash_match = computed_hash == stored_hash

            result = {
                "success": True,
                "document_id": document_id,
                "filename": document.filename,
                "file_path": document.file_path,
                "stored_hash": stored_hash,
                "computed_hash": computed_hash if recompute_hash else "not_computed",
                "hash_match": hash_match,
                "integrity_status": "valid" if hash_match else "corrupted",
                "file_exists": file_path.exists(),
                "file_size": file_path.stat().st_size if file_path.exists() else 0
            }

            if not hash_match:
                logger.warning(f"Integrity check failed for document {document_id}: hash mismatch")
                result["warning"] = "File hash does not match stored hash - possible corruption or modification"

            return result

        except Exception as e:
            logger.error(f"Error verifying document integrity: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }

    def batch_verify_integrity(
        self,
        limit: int = 1000,
        document_ids: Optional[List[int]] = None,
        recompute_all: bool = True
    ) -> Dict[str, Any]:
        """
        Verify integrity of multiple documents.

        Args:
            limit: Maximum documents to verify
            document_ids: Optional list of specific document IDs
            recompute_all: Recompute all hashes

        Returns:
            Dict with batch verification results
        """
        try:
            # Get documents to verify
            if document_ids:
                query = self.db.query(Document).filter(
                    Document.id.in_(document_ids),
                    Document.status == "completed"
                )
            else:
                query = self.db.query(Document).filter(
                    Document.status == "completed",
                    Document.content_hash.isnot(None)
                )

            documents = query.limit(limit).all()

            results = {
                "total_checked": 0,
                "valid": [],
                "corrupted": [],
                "missing_files": [],
                "errors": [],
                "summary": {}
            }

            for doc in documents:
                result = self.verify_document_integrity(doc.id, recompute_hash=recompute_all)
                results["total_checked"] += 1

                if result.get("success"):
                    if result.get("hash_match"):
                        results["valid"].append({
                            "document_id": doc.id,
                            "filename": doc.filename
                        })
                    elif not result.get("file_exists"):
                        results["missing_files"].append({
                            "document_id": doc.id,
                            "filename": doc.filename,
                            "file_path": doc.file_path
                        })
                    else:
                        results["corrupted"].append({
                            "document_id": doc.id,
                            "filename": doc.filename,
                            "file_path": doc.file_path,
                            "stored_hash": result.get("stored_hash"),
                            "computed_hash": result.get("computed_hash")
                        })
                else:
                    results["errors"].append({
                        "document_id": doc.id,
                        "error": result.get("error")
                    })

            # Summary
            results["summary"] = {
                "total": results["total_checked"],
                "valid_count": len(results["valid"]),
                "corrupted_count": len(results["corrupted"]),
                "missing_count": len(results["missing_files"]),
                "error_count": len(results["errors"]),
                "validity_rate": len(results["valid"]) / results["total_checked"] if results["total_checked"] > 0 else 0
            }

            return results

        except Exception as e:
            logger.error(f"Error in batch integrity verification: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_checked": 0
            }

    def detect_corruption(
        self,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Scan for corrupted or modified files.

        Args:
            limit: Maximum documents to scan

        Returns:
            Dict with corruption detection results
        """
        return self.batch_verify_integrity(limit=limit, recompute_all=True)

    def revalidate_hashes(
        self,
        document_ids: Optional[List[int]] = None,
        update_database: bool = False
    ) -> Dict[str, Any]:
        """
        Recompute and validate all document hashes.

        Args:
            document_ids: Optional list of document IDs (if None, all documents)
            update_database: Update database with recomputed hashes

        Returns:
            Dict with revalidation results
        """
        try:
            if document_ids:
                documents = self.db.query(Document).filter(Document.id.in_(document_ids)).all()
            else:
                documents = self.db.query(Document).filter(
                    Document.status == "completed"
                ).all()

            results = {
                "total": len(documents),
                "revalidated": [],
                "errors": [],
                "updated_database": update_database
            }

            for doc in documents:
                if not doc.file_path:
                    continue

                file_path = self.kb_path / doc.file_path
                if not file_path.exists():
                    results["errors"].append({
                        "document_id": doc.id,
                        "error": "File not found"
                    })
                    continue

                try:
                    # Recompute hash
                    new_hash = self._compute_file_hash(file_path)
                    
                    if update_database:
                        doc.content_hash = new_hash
                        self.db.commit()

                    results["revalidated"].append({
                        "document_id": doc.id,
                        "filename": doc.filename,
                        "old_hash": doc.content_hash,
                        "new_hash": new_hash,
                        "hash_changed": doc.content_hash != new_hash if doc.content_hash else True
                    })

                except Exception as e:
                    results["errors"].append({
                        "document_id": doc.id,
                        "error": str(e)
                    })

            if update_database:
                self.db.commit()

            return results

        except Exception as e:
            logger.error(f"Error revalidating hashes: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error computing hash for {file_path}: {e}")
            raise
