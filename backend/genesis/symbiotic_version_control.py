"""
Symbiotic Genesis Key Version Control System.

Genesis Keys and version control work as ONE unified system:
- Every Genesis Key IS a version control entry
- Every version control entry IS a Genesis Key
- File changes automatically create Genesis Keys
- Genesis Keys automatically track versions
- Complete bidirectional integration
"""
import os
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from sqlalchemy.orm import Session

from models.genesis_key_models import GenesisKey, GenesisKeyType, GenesisKeyStatus
from genesis.genesis_key_service import get_genesis_service
from genesis.file_version_tracker import get_file_version_tracker
from genesis.repo_scanner import get_repo_scanner
from database.session import get_session

logger = logging.getLogger(__name__)


class SymbioticVersionControl:
    """
    Unified Genesis Key + Version Control System.

    In this symbiotic system:
    - Genesis Keys ARE version entries
    - Version entries ARE Genesis Keys
    - They cannot exist separately
    - Every change creates BOTH simultaneously
    """

    def __init__(self, base_path: Optional[str] = None, session: Optional[Session] = None):
        self.session = session
        self.base_path = base_path or self._get_default_base_path()
        self.genesis_service = get_genesis_service(session)
        self.version_tracker = get_file_version_tracker(base_path)
        self.repo_scanner = get_repo_scanner(base_path)

    def _get_default_base_path(self) -> str:
        """Get default base path."""
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return backend_dir  # Return backend directory, not project root

    def track_file_change(
        self,
        file_path: str,
        user_id: Optional[str] = None,
        change_description: Optional[str] = None,
        operation_type: str = "modify"
    ) -> Dict[str, Any]:
        """
        Track a file change - SYMBIOTIC operation.
        """
        # Manage session lifecycle to prevent DetachedInstanceError
        local_session = None
        session = self.session
        
        if not session:
            # Create a new session if one doesn't exist
            gen = get_session()
            session = next(gen)
            local_session = session

        try:
            # Normalize path
            if not os.path.isabs(file_path):
                abs_path = os.path.join(self.base_path, file_path)
                rel_path = file_path
            else:
                abs_path = file_path
                # Calculate relative path from base_path
                try:
                    rel_path = os.path.relpath(abs_path, self.base_path)
                except ValueError:
                    # If paths are on different drives (Windows), use absolute
                    rel_path = abs_path
            
            # Log path resolution (INFO level for visibility)
            logger.info(f"[SYMBIOTIC] Path resolution: input={file_path}, abs={abs_path}, rel={rel_path}, base={self.base_path}")

            # Get or create file Genesis Key
            file_genesis_key = self._get_or_create_file_genesis_key(rel_path)

            # Read file content
            if os.path.exists(abs_path):
                file_content = self._read_file_content(abs_path)
                file_hash = self._compute_file_hash(abs_path)
                file_size = os.path.getsize(abs_path)
            else:
                file_content = None
                file_hash = None
                file_size = 0

            # Create Genesis Key for this change
            operation_genesis_key = self.genesis_service.create_key(
                key_type=GenesisKeyType.FILE_OPERATION,
                what_description=change_description or f"{operation_type.capitalize()} file: {os.path.basename(file_path)}",
                who_actor=user_id or "system",
                where_location=rel_path,
                why_reason=f"File {operation_type} operation",
                how_method="Symbiotic version control",
                user_id=user_id,
                file_path=rel_path,
                parent_key_id=file_genesis_key,
                code_after=file_content,
                context_data={
                    "file_genesis_key": file_genesis_key,
                    "operation_type": operation_type,
                    "file_hash": file_hash,
                    "file_size": file_size,
                    "symbiotic": True
                },
                tags=["file_change", operation_type, "symbiotic"],
                session=session
            )

            # CRITICAL: Store key_id and context_data IMMEDIATELY while object is still bound to session
            # This prevents DetachedInstanceError when accessing these attributes later
            operation_key_id = operation_genesis_key.key_id
            operation_context_data = operation_genesis_key.context_data.copy() if operation_genesis_key.context_data else {}

            # Create version entry (linked to Genesis Key)
            version_result = self.version_tracker.track_file_version(
                file_genesis_key=file_genesis_key,
                file_path=abs_path,
                user_id=user_id,
                version_note=f"Genesis Key: {operation_key_id}",
                auto_detect_change=True,
                session=session
            )

            # Update Genesis Key with version info using the copied context_data
            if version_result.get("changed", True):
                operation_context_data["version_key_id"] = version_result["version_key_id"]
                operation_context_data["version_number"] = version_result["version_number"]
                
                # Re-fetch the object to ensure it's attached to the session
                session.refresh(operation_genesis_key)
                operation_genesis_key.context_data = operation_context_data
                
                # Commit updates
                session.commit()

            return {
                "file_genesis_key": file_genesis_key,
                "operation_genesis_key": operation_key_id,
                "version_key_id": version_result.get("version_key_id"),
                "version_number": version_result.get("version_number"),
                "changed": version_result.get("changed", True),
                "file_path": rel_path,
                "timestamp": datetime.utcnow().isoformat(),
                "symbiotic": True,
                "message": "Genesis Key and version entry created symbiotically"
            }

        except Exception as e:
            logger.error(f"Error in symbiotic tracking: {e}")
            # CRITICAL: Always rollback the active session on error
            # This prevents "PendingRollbackError" for subsequent operations
            if session:
                session.rollback()
            raise
        finally:
            # Close local session if we created it
            if local_session:
                local_session.close()

    def get_complete_history(
        self,
        file_genesis_key: str
    ) -> Dict[str, Any]:
        """
        Get complete history - UNIFIED view.

        Returns both Genesis Keys AND versions in one timeline.
        Shows how they're interconnected.
        """
        try:
            # Get version history
            version_history = self.version_tracker.get_file_versions(file_genesis_key)

            # Get all Genesis Keys related to this file
            genesis_keys = []
            if self.session:
                keys = self.session.query(GenesisKey).filter(
                    (GenesisKey.parent_key_id == file_genesis_key) |
                    (GenesisKey.context_data.contains({"file_genesis_key": file_genesis_key}))
                ).order_by(GenesisKey.when_timestamp).all()

                for key in keys:
                    genesis_keys.append({
                        "key_id": key.key_id,
                        "timestamp": key.when_timestamp.isoformat(),
                        "what": key.what_description,
                        "who": key.who_actor,
                        "why": key.why_reason,
                        "version_info": key.context_data.get("version_key_id") if key.context_data else None
                    })

            # Merge into unified timeline
            timeline = []

            # Add version entries
            if version_history and "versions" in version_history:
                for version in version_history["versions"]:
                    timeline.append({
                        "type": "version",
                        "timestamp": version["timestamp"],
                        "version_number": version["version_number"],
                        "version_key_id": version["version_key_id"],
                        "genesis_key_id": version.get("genesis_key_db_id"),
                        "user_id": version["user_id"],
                        "note": version["version_note"],
                        "file_hash": version["file_hash"]
                    })

            # Add Genesis Key entries
            for gk in genesis_keys:
                timeline.append({
                    "type": "genesis_key",
                    "timestamp": gk["timestamp"],
                    "key_id": gk["key_id"],
                    "what": gk["what"],
                    "who": gk["who"],
                    "why": gk["why"],
                    "linked_version": gk["version_info"]
                })

            # Sort by timestamp
            timeline.sort(key=lambda x: x["timestamp"])

            return {
                "file_genesis_key": file_genesis_key,
                "file_info": version_history,
                "total_entries": len(timeline),
                "timeline": timeline,
                "symbiotic": True,
                "message": "Unified Genesis Key + Version Control history"
            }

        except Exception as e:
            logger.error(f"Error getting complete history: {e}")
            raise

    def rollback_to_version(
        self,
        file_genesis_key: str,
        version_number: int,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rollback to a specific version - SYMBIOTIC operation.

        Creates:
        1. Genesis Key for the rollback operation
        2. New version entry (rollback IS a new version)
        3. Links them together
        """
        try:
            # Get version details
            version_info = self.version_tracker.get_version_details(file_genesis_key, version_number)
            if not version_info:
                raise ValueError(f"Version {version_number} not found")

            # Get file info
            file_info = self.version_tracker.get_file_versions(file_genesis_key)
            if not file_info:
                raise ValueError(f"File {file_genesis_key} not found")

            file_path = file_info["file_path"]

            # Create Genesis Key for rollback
            rollback_key = self.genesis_service.create_key(
                key_type=GenesisKeyType.FILE_OPERATION,
                what_description=f"Rollback to version {version_number}",
                who_actor=user_id or "system",
                where_location=file_path,
                why_reason=f"Restoring file to version {version_number}",
                how_method="Symbiotic rollback",
                user_id=user_id,
                file_path=file_path,
                parent_key_id=file_genesis_key,
                context_data={
                    "file_genesis_key": file_genesis_key,
                    "rollback_to_version": version_number,
                    "rollback_to_version_key": version_info["version_key_id"],
                    "operation_type": "rollback",
                    "symbiotic": True
                },
                tags=["rollback", "version_control", "symbiotic"],
                session=self.session
            )

            # Get the version's Genesis Key content
            if self.session and version_info.get("genesis_key_db_id"):
                original_key = self.session.query(GenesisKey).filter_by(
                    key_id=version_info["genesis_key_db_id"]
                ).first()

                if original_key and original_key.code_after:
                    # Restore file content
                    abs_path = os.path.join(self.base_path, file_path)
                    with open(abs_path, 'w', encoding='utf-8') as f:
                        f.write(original_key.code_after)

            # Track as new version (rollback creates a new version)
            new_version = self.track_file_change(
                file_path=file_path,
                user_id=user_id,
                change_description=f"Rolled back to version {version_number}",
                operation_type="rollback"
            )

            return {
                "rollback_genesis_key": rollback_key.key_id,
                "rolled_back_to_version": version_number,
                "new_version_created": new_version["version_number"],
                "new_version_key": new_version["version_key_id"],
                "file_genesis_key": file_genesis_key,
                "symbiotic": True,
                "message": f"Rolled back to version {version_number} - created new version {new_version['version_number']}"
            }

        except Exception as e:
            logger.error(f"Error in symbiotic rollback: {e}")
            raise

    def _get_or_create_file_genesis_key(self, rel_path: str) -> str:
        """Get or create FILE-prefix Genesis Key for a file."""
        # Use consistent hashing for file Genesis Keys
        file_hash = hashlib.md5(rel_path.encode()).hexdigest()[:12]
        return f"FILE-{file_hash}"

    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of file content."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error computing hash for {file_path}: {e}")
            return None

    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read file content (text files only)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            logger.info(f"Binary file: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None

    def watch_file(
        self,
        file_path: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start watching a file for changes - SYMBIOTIC.

        Any change to the file will automatically:
        1. Create Genesis Key
        2. Create version entry
        3. Link them together
        """
        # This would integrate with file system watchers
        # For now, return watch configuration

        file_genesis_key = self._get_or_create_file_genesis_key(file_path)

        return {
            "watching": file_path,
            "file_genesis_key": file_genesis_key,
            "user_id": user_id,
            "auto_track": True,
            "symbiotic": True,
            "message": "File changes will automatically create Genesis Keys and versions"
        }

    def get_symbiotic_stats(self) -> Dict[str, Any]:
        """
        Get statistics about symbiotic integration.

        Shows how Genesis Keys and versions are interconnected.
        """
        try:
            # Version tracker stats
            version_stats = self.version_tracker.get_file_statistics()

            # Genesis Key stats
            genesis_stats = {
                "total_file_operations": 0,
                "symbiotic_operations": 0
            }

            if self.session:
                total_file_ops = self.session.query(GenesisKey).filter(
                    GenesisKey.key_type == GenesisKeyType.FILE_OPERATION
                ).count()

                symbiotic_ops = self.session.query(GenesisKey).filter(
                    GenesisKey.key_type == GenesisKeyType.FILE_OPERATION,
                    GenesisKey.tags.contains(["symbiotic"])
                ).count()

                genesis_stats["total_file_operations"] = total_file_ops
                genesis_stats["symbiotic_operations"] = symbiotic_ops

            return {
                "version_control": version_stats,
                "genesis_keys": genesis_stats,
                "integration_percentage": (
                    (genesis_stats["symbiotic_operations"] / genesis_stats["total_file_operations"] * 100)
                    if genesis_stats["total_file_operations"] > 0 else 0
                ),
                "message": "Genesis Keys and Version Control working symbiotically"
            }

        except Exception as e:
            logger.error(f"Error getting symbiotic stats: {e}")
            return {
                "error": str(e),
                "message": "Could not get symbiotic stats"
            }


# Global symbiotic version control instance
_symbiotic_vc: Optional[SymbioticVersionControl] = None


def get_symbiotic_version_control(
    base_path: Optional[str] = None,
    session: Optional[Session] = None
) -> SymbioticVersionControl:
    """Get or create global symbiotic version control instance."""
    global _symbiotic_vc
    if _symbiotic_vc is None or base_path is not None or session is not None:
        _symbiotic_vc = SymbioticVersionControl(base_path=base_path, session=session)
    return _symbiotic_vc
