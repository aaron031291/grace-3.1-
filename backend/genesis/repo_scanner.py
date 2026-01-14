"""
Repository Genesis Key Scanner.

Scans the entire repository and assigns Genesis Keys to:
- All directories
- All subdirectories
- All files

Stores in immutable memory for complete tracking.
Integrates with file version tracker for automatic version control.
"""
import os
import uuid
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class RepoScanner:
    """
    Scans repository and assigns Genesis Keys to everything.

    Creates immutable memory snapshot of entire repo structure.
    """

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.immutable_memory = {
            "scan_timestamp": datetime.utcnow().isoformat(),
            "repo_path": repo_path,
            "root_genesis_key": None,
            "directories": {},
            "files": {},
            "statistics": {
                "total_directories": 0,
                "total_files": 0,
                "total_size_bytes": 0
            }
        }

        # Skip patterns
        self.skip_patterns = [
            '__pycache__',
            '.git',
            'node_modules',
            '.venv',
            'venv',
            '.pytest_cache',
            '.mypy_cache',
            'dist',
            'build',
            '*.pyc',
            '.DS_Store'
        ]

    def should_skip(self, path: str) -> bool:
        """Check if path should be skipped."""
        path_str = str(path)
        for pattern in self.skip_patterns:
            if pattern in path_str:
                return True
        return False

    def generate_directory_key(self, path: str) -> str:
        """Generate Genesis Key for directory."""
        # Use path hash for consistency
        path_hash = hashlib.sha256(path.encode()).hexdigest()[:12]
        return f"DIR-{path_hash}"

    def generate_file_key(self, path: str) -> str:
        """Generate Genesis Key for file."""
        # Use path hash for consistency
        path_hash = hashlib.sha256(path.encode()).hexdigest()[:12]
        return f"FILE-{path_hash}"

    def get_file_metadata(self, abs_path: str) -> Dict[str, Any]:
        """Get file metadata."""
        try:
            stat = os.stat(abs_path)
            return {
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "is_executable": os.access(abs_path, os.X_OK)
            }
        except Exception as e:
            logger.error(f"Failed to get metadata for {abs_path}: {e}")
            return {}

    def scan_repository(self) -> Dict[str, Any]:
        """
        Scan entire repository and assign Genesis Keys.

        Returns immutable memory snapshot.
        """
        logger.info(f"Starting repository scan: {self.repo_path}")

        # Scan directory tree
        root_key = self._scan_directory(self.repo_path, "", None)
        self.immutable_memory["root_genesis_key"] = root_key

        # Update statistics
        self.immutable_memory["statistics"]["total_directories"] = len(
            self.immutable_memory["directories"]
        )
        self.immutable_memory["statistics"]["total_files"] = len(
            self.immutable_memory["files"]
        )
        self.immutable_memory["statistics"]["total_size_bytes"] = sum(
            f["size_bytes"]
            for f in self.immutable_memory["files"].values()
            if "size_bytes" in f
        )

        logger.info(
            f"Scan complete: {self.immutable_memory['statistics']['total_directories']} dirs, "
            f"{self.immutable_memory['statistics']['total_files']} files"
        )

        return self.immutable_memory

    def _scan_directory(
        self,
        abs_path: str,
        rel_path: str,
        parent_key: Optional[str]
    ) -> str:
        """Recursively scan directory and assign Genesis Keys."""

        if self.should_skip(abs_path):
            return None

        # Generate Genesis Key for this directory
        dir_key = self.generate_directory_key(rel_path or "root")

        # Get directory info
        dir_name = os.path.basename(abs_path) or "root"
        is_root = (rel_path == "")

        # Store directory info
        dir_info = {
            "genesis_key": dir_key,
            "path": rel_path,
            "absolute_path": abs_path,
            "name": dir_name,
            "parent_genesis_key": parent_key,
            "is_root": is_root,
            "subdirectories": [],
            "files": [],
            "scanned_at": datetime.utcnow().isoformat()
        }

        # Scan contents
        try:
            for item in sorted(os.listdir(abs_path)):
                item_abs = os.path.join(abs_path, item)
                item_rel = os.path.join(rel_path, item) if rel_path else item

                if self.should_skip(item_abs):
                    continue

                if os.path.isdir(item_abs):
                    # Scan subdirectory
                    subdir_key = self._scan_directory(item_abs, item_rel, dir_key)
                    if subdir_key:
                        dir_info["subdirectories"].append(subdir_key)

                elif os.path.isfile(item_abs):
                    # Assign Genesis Key to file
                    file_key = self._scan_file(item_abs, item_rel, dir_key)
                    if file_key:
                        dir_info["files"].append(file_key)

        except PermissionError:
            logger.warning(f"Permission denied: {abs_path}")
        except Exception as e:
            logger.error(f"Error scanning {abs_path}: {e}")

        # Store directory
        self.immutable_memory["directories"][rel_path or "root"] = dir_info

        return dir_key

    def _scan_file(
        self,
        abs_path: str,
        rel_path: str,
        parent_dir_key: str
    ) -> str:
        """Assign Genesis Key to file."""

        # Generate Genesis Key for file
        file_key = self.generate_file_key(rel_path)

        # Get file info
        file_name = os.path.basename(abs_path)
        file_ext = os.path.splitext(file_name)[1]

        # Get metadata
        metadata = self.get_file_metadata(abs_path)

        # Store file info
        file_info = {
            "genesis_key": file_key,
            "path": rel_path,
            "absolute_path": abs_path,
            "name": file_name,
            "extension": file_ext,
            "directory_genesis_key": parent_dir_key,
            "scanned_at": datetime.utcnow().isoformat(),
            **metadata
        }

        self.immutable_memory["files"][rel_path] = file_info

        return file_key

    def save_immutable_memory(self, output_path: Optional[str] = None) -> str:
        """
        Save immutable memory to JSON file.

        This creates a permanent snapshot that cannot be changed.
        """
        if not output_path:
            output_path = os.path.join(
                self.repo_path,
                ".genesis_immutable_memory.json"
            )

        with open(output_path, 'w') as f:
            json.dump(self.immutable_memory, f, indent=2, default=str)

        logger.info(f"Immutable memory saved to: {output_path}")
        return output_path

    def get_directory_tree(self, rel_path: str = "root") -> Optional[Dict]:
        """Get directory tree starting from path."""
        if rel_path not in self.immutable_memory["directories"]:
            return None

        dir_info = self.immutable_memory["directories"][rel_path]

        tree = {
            "genesis_key": dir_info["genesis_key"],
            "name": dir_info["name"],
            "path": dir_info["path"],
            "subdirectories": [],
            "files": []
        }

        # Add subdirectories
        for subdir_key in dir_info["subdirectories"]:
            # Find subdirectory by key
            for path, info in self.immutable_memory["directories"].items():
                if info["genesis_key"] == subdir_key:
                    subtree = self.get_directory_tree(path)
                    if subtree:
                        tree["subdirectories"].append(subtree)
                    break

        # Add files
        for file_key in dir_info["files"]:
            # Find file by key
            for path, info in self.immutable_memory["files"].items():
                if info["genesis_key"] == file_key:
                    tree["files"].append({
                        "genesis_key": info["genesis_key"],
                        "name": info["name"],
                        "path": info["path"],
                        "size_bytes": info.get("size_bytes", 0)
                    })
                    break

        return tree

    def find_by_genesis_key(self, genesis_key: str) -> Optional[Dict]:
        """Find directory or file by Genesis Key."""
        # Check directories
        for path, info in self.immutable_memory["directories"].items():
            if info["genesis_key"] == genesis_key:
                return {"type": "directory", "info": info}

        # Check files
        for path, info in self.immutable_memory["files"].items():
            if info["genesis_key"] == genesis_key:
                return {"type": "file", "info": info}

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get scan statistics."""
        return self.immutable_memory["statistics"]

    def integrate_with_version_tracking(
        self,
        user_id: Optional[str] = None,
        version_note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Integrate scanned files with file version tracker.

        Creates initial versions for all scanned files.
        Links file Genesis Keys with version control.
        """
        try:
            from genesis.file_version_tracker import get_file_version_tracker

            tracker = get_file_version_tracker(base_path=self.repo_path)

            tracked_count = 0
            skipped_count = 0
            error_count = 0

            for file_path, file_info in self.immutable_memory["files"].items():
                try:
                    file_genesis_key = file_info["genesis_key"]
                    abs_path = file_info["absolute_path"]

                    # Track initial version
                    result = tracker.track_file_version(
                        file_genesis_key=file_genesis_key,
                        file_path=abs_path,
                        user_id=user_id or "system",
                        version_note=version_note or "Initial scan version",
                        auto_detect_change=True
                    )

                    if result.get("changed", True):
                        tracked_count += 1
                    else:
                        skipped_count += 1

                except Exception as e:
                    logger.error(f"Error tracking file {file_path}: {e}")
                    error_count += 1

            return {
                "total_files": len(self.immutable_memory["files"]),
                "tracked": tracked_count,
                "skipped": skipped_count,
                "errors": error_count,
                "message": f"Version tracking integrated: {tracked_count} files tracked"
            }

        except Exception as e:
            logger.error(f"Error integrating with version tracking: {e}")
            return {
                "error": str(e),
                "message": "Failed to integrate with version tracking"
            }


def scan_and_save_repo(
    repo_path: str,
    integrate_version_tracking: bool = True,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Scan repository and save immutable memory.

    Args:
        repo_path: Path to repository
        integrate_version_tracking: Whether to integrate with file version tracking
        user_id: User ID for version tracking

    Returns:
        Immutable memory with scan results
    """
    scanner = RepoScanner(repo_path)
    immutable_memory = scanner.scan_repository()
    scanner.save_immutable_memory()

    # Integrate with version tracking if requested
    if integrate_version_tracking:
        tracking_result = scanner.integrate_with_version_tracking(
            user_id=user_id,
            version_note="Initial repository scan"
        )
        immutable_memory["version_tracking"] = tracking_result

    return immutable_memory


# Global scanner instance
_repo_scanner: Optional[RepoScanner] = None


def get_repo_scanner(repo_path: Optional[str] = None) -> RepoScanner:
    """Get or create global repo scanner."""
    global _repo_scanner
    if _repo_scanner is None or repo_path is not None:
        if repo_path is None:
            # Default to grace_3 root
            repo_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _repo_scanner = RepoScanner(repo_path)
    return _repo_scanner
