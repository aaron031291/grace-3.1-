import os
import uuid
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from models.genesis_key_models import GenesisKey, GenesisKeyType, GenesisKeyStatus
from genesis.genesis_key_service import get_genesis_service
from database.session import get_session
class DirectoryGenesisKey:
    logger = logging.getLogger(__name__)
    """
    Manages Genesis Keys for directory hierarchies.

    Structure:
    - Root directory: DIR-xxxxxx (Genesis Key)
      - Subdirectory 1: DIR-yyyyyy (Genesis Key)
        - file1.txt (version controlled)
        - file2.txt (version controlled)
      - Subdirectory 2: DIR-zzzzzz (Genesis Key)
        - Subdirectory 2.1: DIR-aaaaaa (Genesis Key)
          - file3.txt (version controlled)
    """

    def __init__(self, base_path: Optional[str] = None, session: Optional[Session] = None):
        self.session = session
        self.base_path = base_path or self._get_default_base_path()
        self.genesis_service = get_genesis_service(session)

        # Metadata file to store directory Genesis Keys (use Path for portability)
        self.metadata_file = str(Path(self.base_path) / ".genesis_directory_keys.json")
        self._ensure_base_path()
        self._load_or_create_metadata()

    def _get_default_base_path(self) -> str:
        """Get default base path (knowledge_base) - portable path handling."""
        backend_dir = Path(__file__).parent.parent
        return str(backend_dir / "knowledge_base")

    def _ensure_base_path(self):
        """Ensure base path exists."""
        Path(self.base_path).mkdir(parents=True, exist_ok=True)

    def _load_or_create_metadata(self):
        """Load or create directory Genesis Keys metadata."""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                self.directory_keys = json.load(f)
        else:
            self.directory_keys = {
                "version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "root_genesis_key": None,
                "directories": {}
            }
            self._save_metadata()

    def _save_metadata(self):
        """Save directory Genesis Keys metadata."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.directory_keys, f, indent=2, default=str)

    def generate_directory_key(self) -> str:
        """Generate a unique directory Genesis Key."""
        return f"DIR-{uuid.uuid4().hex[:12]}"

    def create_directory_genesis_key(
        self,
        directory_path: str,
        parent_genesis_key: Optional[str] = None,
        user_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Genesis Key for a directory.

        Args:
            directory_path: Path to the directory (relative to base_path)
            parent_genesis_key: Genesis Key of parent directory
            user_id: User who created the directory
            description: Optional description

        Returns:
            Dictionary with directory Genesis Key information
        """
        # Get absolute path
        abs_path = os.path.join(self.base_path, directory_path)

        # Check if directory already has a Genesis Key
        if directory_path in self.directory_keys["directories"]:
            logger.info(f"Directory {directory_path} already has Genesis Key")
            return self.directory_keys["directories"][directory_path]

        # Generate Genesis Key for this directory
        dir_genesis_key = self.generate_directory_key()

        # Create directory if it doesn't exist
        Path(abs_path).mkdir(parents=True, exist_ok=True)

        # Get directory information
        dir_name = os.path.basename(directory_path) or "root"
        is_root = (directory_path == "" or directory_path == ".")

        # Create Genesis Key entry in database
        try:
            key = self.genesis_service.create_key(
                key_type=GenesisKeyType.FILE_OPERATION,
                what_description=description or f"Created directory: {dir_name}",
                who_actor=user_id or "system",
                where_location=directory_path,
                why_reason=f"Directory Genesis Key assignment",
                how_method="Directory hierarchy system",
                user_id=user_id,
                file_path=directory_path,
                parent_key_id=parent_genesis_key,
                context_data={
                    "directory_genesis_key": dir_genesis_key,
                    "is_root": is_root,
                    "parent_genesis_key": parent_genesis_key,
                    "absolute_path": abs_path
                },
                tags=["directory", "genesis_key", "hierarchy"],
                session=self.session
            )
        except Exception as e:
            logger.error(f"Failed to create Genesis Key in database: {e}")

        # Store in metadata
        dir_info = {
            "genesis_key": dir_genesis_key,
            "path": directory_path,
            "absolute_path": abs_path,
            "name": dir_name,
            "parent_genesis_key": parent_genesis_key,
            "created_at": datetime.utcnow().isoformat(),
            "is_root": is_root,
            "subdirectories": [],
            "files": [],
            "version_count": 0
        }

        self.directory_keys["directories"][directory_path] = dir_info

        # If root directory, set root Genesis Key
        if is_root:
            self.directory_keys["root_genesis_key"] = dir_genesis_key

        self._save_metadata()

        # Create README in directory
        self._create_directory_readme(abs_path, dir_info)

        logger.info(f"Created Genesis Key {dir_genesis_key} for directory {directory_path}")
        return dir_info

    def _create_directory_readme(self, abs_path: str, dir_info: Dict):
        """Create README in directory with Genesis Key info."""
        readme_path = os.path.join(abs_path, ".genesis_key_info.md")

        content = f"""# Directory Genesis Key

**Genesis Key:** `{dir_info['genesis_key']}`
**Directory:** `{dir_info['name']}`
**Created:** {dir_info['created_at']}

## Hierarchy

- **Parent Genesis Key:** {dir_info['parent_genesis_key'] or 'None (Root)'}
- **Is Root:** {dir_info['is_root']}

## Purpose

This directory is uniquely identified by its Genesis Key. All files within this directory
are version-controlled under this Genesis Key hierarchy.

## Structure

- Each subdirectory has its own Genesis Key
- Files are version-controlled within their directory
- Complete hierarchy tracking from root to leaf

## Version Control

All changes to files in this directory are tracked with:
- What: File operation (create, update, delete)
- Where: File path within this directory
- When: Timestamp
- Why: Reason for change
- Who: User making change
- How: Method used

Genesis Key: {dir_info['genesis_key']}
"""

        with open(readme_path, 'w') as f:
            f.write(content)

    def create_hierarchy(
        self,
        root_path: str = "",
        user_id: Optional[str] = None,
        scan_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Create Genesis Key hierarchy for a directory tree.

        Args:
            root_path: Root directory path (relative to base_path)
            user_id: User creating the hierarchy
            scan_existing: Whether to scan existing directories

        Returns:
            Hierarchy structure with Genesis Keys
        """
        # Create root Genesis Key
        root_info = self.create_directory_genesis_key(
            directory_path=root_path,
            parent_genesis_key=None,
            user_id=user_id,
            description=f"Root directory Genesis Key"
        )

        if scan_existing:
            # Scan and create Genesis Keys for existing subdirectories
            abs_root = os.path.join(self.base_path, root_path)
            self._scan_and_create_keys(abs_root, root_path, root_info["genesis_key"], user_id)

        return self.get_directory_tree(root_path)

    def _scan_and_create_keys(
        self,
        abs_path: str,
        rel_path: str,
        parent_key: str,
        user_id: Optional[str]
    ):
        """Recursively scan and create Genesis Keys for directories."""
        try:
            for item in os.listdir(abs_path):
                # Skip hidden files and metadata
                if item.startswith('.') or item.startswith('__'):
                    continue

                item_abs = os.path.join(abs_path, item)
                item_rel = os.path.join(rel_path, item)

                if os.path.isdir(item_abs):
                    # Create Genesis Key for subdirectory
                    sub_info = self.create_directory_genesis_key(
                        directory_path=item_rel,
                        parent_genesis_key=parent_key,
                        user_id=user_id,
                        description=f"Subdirectory Genesis Key: {item}"
                    )

                    # Add to parent's subdirectories
                    if rel_path in self.directory_keys["directories"]:
                        if sub_info["genesis_key"] not in self.directory_keys["directories"][rel_path]["subdirectories"]:
                            self.directory_keys["directories"][rel_path]["subdirectories"].append(
                                sub_info["genesis_key"]
                            )
                            self._save_metadata()

                    # Recursively process subdirectories
                    self._scan_and_create_keys(item_abs, item_rel, sub_info["genesis_key"], user_id)

                elif os.path.isfile(item_abs):
                    # Track file in directory
                    if rel_path in self.directory_keys["directories"]:
                        file_info = {
                            "name": item,
                            "path": item_rel,
                            "added_at": datetime.utcnow().isoformat()
                        }
                        if file_info not in self.directory_keys["directories"][rel_path]["files"]:
                            self.directory_keys["directories"][rel_path]["files"].append(file_info)
                            self._save_metadata()

        except Exception as e:
            logger.error(f"Error scanning {abs_path}: {e}")

    def get_directory_genesis_key(self, directory_path: str) -> Optional[str]:
        """Get Genesis Key for a directory."""
        if directory_path in self.directory_keys["directories"]:
            return self.directory_keys["directories"][directory_path]["genesis_key"]
        return None

    def get_directory_info(self, directory_path: str) -> Optional[Dict]:
        """Get full information for a directory."""
        return self.directory_keys["directories"].get(directory_path)

    def get_directory_tree(self, root_path: str = "") -> Dict[str, Any]:
        """
        Get directory tree with Genesis Keys.

        Returns hierarchical structure with all Genesis Keys.
        """
        if root_path not in self.directory_keys["directories"]:
            return None

        root_info = self.directory_keys["directories"][root_path]

        tree = {
            "genesis_key": root_info["genesis_key"],
            "name": root_info["name"],
            "path": root_info["path"],
            "is_root": root_info["is_root"],
            "created_at": root_info["created_at"],
            "parent_genesis_key": root_info["parent_genesis_key"],
            "subdirectories": [],
            "files": root_info["files"],
            "file_count": len(root_info["files"]),
            "subdirectory_count": len(root_info["subdirectories"])
        }

        # Recursively build subdirectory trees
        for subdir_key in root_info["subdirectories"]:
            # Find subdirectory path by Genesis Key
            for path, info in self.directory_keys["directories"].items():
                if info["genesis_key"] == subdir_key:
                    subtree = self.get_directory_tree(path)
                    if subtree:
                        tree["subdirectories"].append(subtree)
                    break

        return tree

    def add_file_version(
        self,
        directory_path: str,
        file_name: str,
        user_id: Optional[str] = None,
        version_note: Optional[str] = None,
        file_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a file version under a directory's Genesis Key.

        Args:
            directory_path: Directory containing the file
            file_name: Name of the file
            user_id: User making the change
            version_note: Note about this version
            file_content: Optional file content snapshot

        Returns:
            Version information
        """
        # Get directory Genesis Key
        dir_key = self.get_directory_genesis_key(directory_path)
        if not dir_key:
            raise ValueError(f"No Genesis Key found for directory: {directory_path}")

        file_path = os.path.join(directory_path, file_name)
        abs_file_path = os.path.join(self.base_path, file_path)

        # Increment version count for directory
        if directory_path in self.directory_keys["directories"]:
            self.directory_keys["directories"][directory_path]["version_count"] += 1
            version_number = self.directory_keys["directories"][directory_path]["version_count"]
            self._save_metadata()
        else:
            version_number = 1

        # Create version Genesis Key
        try:
            version_key = self.genesis_service.create_key(
                key_type=GenesisKeyType.FILE_OPERATION,
                what_description=f"File version: {file_name} (v{version_number})",
                who_actor=user_id or "system",
                where_location=file_path,
                why_reason=version_note or "File version created",
                how_method="Directory hierarchy version control",
                user_id=user_id,
                file_path=file_path,
                parent_key_id=dir_key,  # Link to directory Genesis Key
                code_after=file_content,
                context_data={
                    "directory_genesis_key": dir_key,
                    "version_number": version_number,
                    "file_name": file_name,
                    "file_size": os.path.getsize(abs_file_path) if os.path.exists(abs_file_path) else None
                },
                tags=["file_version", "version_control", "hierarchy"],
                session=self.session
            )

            return {
                "version_key": version_key.key_id,
                "version_number": version_number,
                "directory_genesis_key": dir_key,
                "file_path": file_path,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to create file version: {e}")
            raise

    def get_all_directory_keys(self) -> Dict[str, Dict]:
        """Get all directory Genesis Keys."""
        return self.directory_keys["directories"]

    def get_hierarchy_statistics(self) -> Dict[str, Any]:
        """Get statistics about the directory hierarchy."""
        total_dirs = len(self.directory_keys["directories"])
        total_files = sum(
            len(info["files"])
            for info in self.directory_keys["directories"].values()
        )
        total_versions = sum(
            info["version_count"]
            for info in self.directory_keys["directories"].values()
        )

        return {
            "total_directories": total_dirs,
            "total_files": total_files,
            "total_versions": total_versions,
            "root_genesis_key": self.directory_keys.get("root_genesis_key"),
            "created_at": self.directory_keys.get("created_at")
        }


# Global directory hierarchy instance
_directory_hierarchy: Optional[DirectoryGenesisKey] = None


def get_directory_hierarchy(base_path: Optional[str] = None) -> DirectoryGenesisKey:
    """Get or create the global directory hierarchy instance."""
    global _directory_hierarchy
    if _directory_hierarchy is None or base_path is not None:
        _directory_hierarchy = DirectoryGenesisKey(base_path=base_path)
    return _directory_hierarchy
