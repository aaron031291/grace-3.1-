"""
File Version Control through Genesis Keys.

Tracks file changes and versions using Genesis Keys:
- Every file gets a FILE-prefix Genesis Key
- Every change to a file creates a new version Genesis Key
- Versions are linked to the original file Genesis Key
- Complete history of all file changes
"""
import os
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session

from models.genesis_key_models import GenesisKey, GenesisKeyType
from genesis.genesis_key_service import get_genesis_service
from database.session import get_session

logger = logging.getLogger(__name__)

def _track_version(desc, **kwargs):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("version_tracker", desc, **kwargs)
    except Exception:
        pass


class FileVersionTracker:
    """
    Tracks file versions through Genesis Keys.

    Structure:
    - FILE-xxxxx (Original file Genesis Key)
      ├─ VER-xxxxx-1 (Version 1)
      ├─ VER-xxxxx-2 (Version 2)
      └─ VER-xxxxx-3 (Version 3)
    """

    def __init__(self, base_path: Optional[str] = None, session: Optional[Session] = None):
        self.session = session
        self.base_path = base_path or self._get_default_base_path()
        self.genesis_service = get_genesis_service(session)

        # Version metadata file
        self.version_metadata_file = os.path.join(self.base_path, ".genesis_file_versions.json")
        self._load_or_create_metadata()

    def _get_default_base_path(self) -> str:
        """Get default base path."""
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return backend_dir

    def _load_or_create_metadata(self):
        """Load or create file version metadata."""
        if os.path.exists(self.version_metadata_file):
            with open(self.version_metadata_file, 'r') as f:
                self.version_metadata = json.load(f)
        else:
            self.version_metadata = {
                "version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "files": {}  # file_genesis_key -> version info
            }
            self._save_metadata()

    def _save_metadata(self):
        """Save file version metadata."""
        with open(self.version_metadata_file, 'w') as f:
            json.dump(self.version_metadata, f, indent=2, default=str)

    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of file content."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def track_file_version(
        self,
        file_genesis_key: str,
        file_path: str,
        user_id: Optional[str] = None,
        version_note: Optional[str] = None,
        auto_detect_change: bool = True,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Track a new version of a file.

        Args:
            file_genesis_key: FILE-prefix Genesis Key for the file
            file_path: Path to the file (relative or absolute)
            user_id: User making the change
            version_note: Note about this version
            auto_detect_change: Whether to auto-detect if file changed

        Returns:
            Version information
        """
        # Manage session lifecycle locally to avoid detached/expired objects
        local_session = session or self.session or next(get_session())
        close_session = session is None and self.session is None
        # Ensure we use a fresh service bound to the active session
        genesis_service = get_genesis_service(local_session)

        # Get absolute path
        if not os.path.isabs(file_path):
            abs_file_path = os.path.join(self.base_path, file_path)
        else:
            abs_file_path = file_path

        # Log path resolution for debugging
        logger.info(f"[VERSION-TRACKER] Path received: file_path={file_path}, is_abs={os.path.isabs(file_path)}, abs_file_path={abs_file_path}, base_path={self.base_path}")

        # If primary path missing, try knowledge_base prefix (scraped files saved there)
        if not os.path.exists(abs_file_path):
            # If the path is absolute and missing knowledge_base, inject it after base_path
            alt_path = None
            base_prefix = os.path.join(self.base_path, "auto_search")
            kb_prefix = os.path.join(self.base_path, "knowledge_base", "auto_search")

            if os.path.isabs(abs_file_path) and abs_file_path.startswith(base_prefix):
                alt_path = abs_file_path.replace(base_prefix, kb_prefix, 1)
            else:
                # If relative, simply prepend knowledge_base
                rel_path = file_path if not os.path.isabs(file_path) else os.path.relpath(file_path, self.base_path)
                alt_path = os.path.join(self.base_path, "knowledge_base", rel_path)

            if alt_path and os.path.exists(alt_path):
                logger.info(f"[VERSION-TRACKER] Fallback path resolved: {alt_path}")
                abs_file_path = alt_path

        if not os.path.exists(abs_file_path):
            # Race condition or path mismatch: file was deleted/mis-located
            logger.warning(f"File vanished before tracking: {abs_file_path}")
            return {
                "changed": False,
                "version_number": 0,
                "version_key_id": None,
                "message": "File not found (vanished)"
            }

        # Initialize file tracking if not exists
        if file_genesis_key not in self.version_metadata["files"]:
            self.version_metadata["files"][file_genesis_key] = {
                "file_genesis_key": file_genesis_key,
                "file_path": file_path,
                "absolute_path": abs_file_path,
                "created_at": datetime.utcnow().isoformat(),
                "version_count": 0,
                "versions": [],
                "last_hash": None
            }

        file_info = self.version_metadata["files"][file_genesis_key]

        # Compute current file hash
        current_hash = self._compute_file_hash(abs_file_path)

        # Check if file actually changed
        if auto_detect_change and file_info["last_hash"] == current_hash:
            logger.info(f"File {file_path} hasn't changed since last version")
            return {
                "file_genesis_key": file_genesis_key,
                "version_number": file_info["version_count"],
                "changed": False,
                "message": "File content unchanged"
            }

        # Increment version number
        file_info["version_count"] += 1
        version_number = file_info["version_count"]

        # Generate version Genesis Key
        version_key_id = f"VER-{file_genesis_key.replace('FILE-', '')}-{version_number}"

        # Read file content
        try:
            with open(abs_file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except UnicodeDecodeError:
            # Binary file
            file_content = None
            logger.info(f"Binary file detected: {file_path}")

        # Get file stats
        file_stats = os.stat(abs_file_path)

        # Create version Genesis Key
        try:
            version_key = genesis_service.create_key(
                key_type=GenesisKeyType.FILE_OPERATION,
                what_description=f"File version {version_number}: {os.path.basename(file_path)}",
                who_actor=user_id or "system",
                where_location=file_path,
                why_reason=version_note or f"File version {version_number} created",
                how_method="File version control system",
                user_id=user_id,
                file_path=file_path,
                parent_key_id=file_genesis_key,  # Link to file Genesis Key
                code_after=file_content,
                context_data={
                    "file_genesis_key": file_genesis_key,
                    "version_number": version_number,
                    "version_key_id": version_key_id,
                    "file_hash": current_hash,
                    "file_size": file_stats.st_size,
                    "modified_time": datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                },
                tags=["file_version", "version_control", version_key_id],
                session=local_session
            )

            # Store key_id immediately to prevent DetachedInstanceError
            try:
                version_key_db_id = version_key.key_id
            except Exception:
                # Defensive refresh in case the object was expired
                local_session.flush()
                local_session.refresh(version_key)
                version_key_db_id = version_key.key_id

            # Store version info
            version_info = {
                "version_number": version_number,
                "version_key_id": version_key_id,
                "genesis_key_db_id": version_key_db_id,
                "timestamp": datetime.utcnow().isoformat(),
                "file_hash": current_hash,
                "file_size": file_stats.st_size,
                "user_id": user_id or "system",
                "version_note": version_note,
                "has_content": file_content is not None
            }

            file_info["versions"].append(version_info)
            file_info["last_hash"] = current_hash
            file_info["last_updated"] = datetime.utcnow().isoformat()

            self._save_metadata()

            # Commit if we own the session
            if close_session:
                local_session.commit()

            logger.info(f"Created version {version_number} for file {file_genesis_key}")

            return {
                "file_genesis_key": file_genesis_key,
                "version_key_id": version_key_id,
                "version_number": version_number,
                "genesis_key_db_id": version_key.key_id,
                "changed": True,
                "file_hash": current_hash,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to create file version: {e}")
            if close_session:
                local_session.rollback()
                local_session.close()
            raise
        finally:
            if close_session:
                local_session.close()

    def get_file_versions(self, file_genesis_key: str) -> Optional[Dict[str, Any]]:
        """Get all versions for a file."""
        return self.version_metadata["files"].get(file_genesis_key)

    def get_version_details(self, file_genesis_key: str, version_number: int) -> Optional[Dict[str, Any]]:
        """Get details for a specific version."""
        file_info = self.version_metadata["files"].get(file_genesis_key)
        if not file_info:
            return None

        for version in file_info["versions"]:
            if version["version_number"] == version_number:
                return version

        return None

    def get_latest_version(self, file_genesis_key: str) -> Optional[Dict[str, Any]]:
        """Get the latest version for a file."""
        file_info = self.version_metadata["files"].get(file_genesis_key)
        if not file_info or not file_info["versions"]:
            return None

        return file_info["versions"][-1]

    def get_version_diff(
        self,
        file_genesis_key: str,
        version1: int,
        version2: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get differences between two versions.

        Returns:
            Dictionary with version comparison info
        """
        v1 = self.get_version_details(file_genesis_key, version1)
        v2 = self.get_version_details(file_genesis_key, version2)

        if not v1 or not v2:
            return None

        return {
            "file_genesis_key": file_genesis_key,
            "version1": version1,
            "version2": version2,
            "hash_changed": v1["file_hash"] != v2["file_hash"],
            "size_diff": v2["file_size"] - v1["file_size"],
            "time_diff": (
                datetime.fromisoformat(v2["timestamp"]) -
                datetime.fromisoformat(v1["timestamp"])
            ).total_seconds(),
            "version1_info": v1,
            "version2_info": v2
        }

    def list_all_tracked_files(self) -> Dict[str, Dict]:
        """List all files being tracked."""
        return self.version_metadata["files"]

    def get_file_statistics(self) -> Dict[str, Any]:
        """Get statistics about tracked files."""
        total_files = len(self.version_metadata["files"])
        total_versions = sum(
            info["version_count"]
            for info in self.version_metadata["files"].values()
        )

        return {
            "total_files_tracked": total_files,
            "total_versions": total_versions,
            "average_versions_per_file": total_versions / total_files if total_files > 0 else 0,
            "created_at": self.version_metadata.get("created_at")
        }

    def auto_track_directory(
        self,
        directory_path: str,
        user_id: Optional[str] = None,
        recursive: bool = True,
        file_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Automatically track all files in a directory.

        Args:
            directory_path: Directory to track
            user_id: User ID
            recursive: Whether to recurse into subdirectories
            file_pattern: Optional glob pattern (e.g., "*.py")

        Returns:
            Summary of tracking operation
        """
        if not os.path.isabs(directory_path):
            abs_dir = os.path.join(self.base_path, directory_path)
        else:
            abs_dir = directory_path

        tracked = []
        skipped = []
        errors = []

        # Get list of files
        if recursive:
            from pathlib import Path
            if file_pattern:
                files = list(Path(abs_dir).rglob(file_pattern))
            else:
                files = [p for p in Path(abs_dir).rglob("*") if p.is_file()]
        else:
            from pathlib import Path
            if file_pattern:
                files = list(Path(abs_dir).glob(file_pattern))
            else:
                files = [p for p in Path(abs_dir).glob("*") if p.is_file()]

        for file_path in files:
            # Skip hidden files and metadata
            if file_path.name.startswith('.') or file_path.name.startswith('__'):
                skipped.append(str(file_path))
                continue

            try:
                # Generate file Genesis Key
                rel_path = os.path.relpath(file_path, self.base_path)
                file_genesis_key = f"FILE-{hashlib.md5(rel_path.encode()).hexdigest()[:12]}"

                # Track version
                result = self.track_file_version(
                    file_genesis_key=file_genesis_key,
                    file_path=str(file_path),
                    user_id=user_id,
                    version_note="Auto-tracked from directory scan"
                )

                if result["changed"]:
                    tracked.append({
                        "file_path": str(file_path),
                        "file_genesis_key": file_genesis_key,
                        "version_number": result["version_number"]
                    })
                else:
                    skipped.append(str(file_path))

            except Exception as e:
                errors.append({
                    "file_path": str(file_path),
                    "error": str(e)
                })
                logger.error(f"Error tracking {file_path}: {e}")

        return {
            "directory": directory_path,
            "total_files_scanned": len(files),
            "tracked": len(tracked),
            "skipped": len(skipped),
            "errors": len(errors),
            "tracked_files": tracked,
            "skipped_files": skipped,
            "error_details": errors
        }


# Global file version tracker instance
_file_version_tracker: Optional[FileVersionTracker] = None


def get_file_version_tracker(base_path: Optional[str] = None) -> FileVersionTracker:
    """Get or create the global file version tracker instance."""
    global _file_version_tracker
    if _file_version_tracker is None or base_path is not None:
        _file_version_tracker = FileVersionTracker(base_path=base_path)
    return _file_version_tracker
