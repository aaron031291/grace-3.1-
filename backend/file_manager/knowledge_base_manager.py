"""
Knowledge base file and folder management.
Handles file storage, directory structure, and metadata.
"""

import os
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)
def _track_op(desc, **kw):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event('knowledge_base_manager', desc, **kw)
    except Exception:
        pass



class KnowledgeBaseManager:
    """Manages file storage and directory structure in knowledge_base."""
    
    def __init__(self, base_path: str = "backend/knowledge_base"):
        """
        Initialize knowledge base manager.
        
        Args:
            base_path: Root directory for knowledge base
        """
        self.base_path = Path(base_path)
        self.metadata_file = self.base_path / ".metadata.json"
        self._ensure_base_exists()
    
    def _ensure_base_exists(self):
        """Ensure base directory exists."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize metadata file if it doesn't exist
        if not self.metadata_file.exists():
            self._save_metadata({})
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from file."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading metadata: {e}")
        return {}
    
    def _save_metadata(self, metadata: Dict[str, Any]):
        """Save metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def _get_file_metadata_key(self, relative_path: str) -> str:
        """Get metadata key for a file."""
        return f"files:{relative_path}"
    
    def _get_folder_metadata_key(self, relative_path: str) -> str:
        """Get metadata key for a folder."""
        return f"folders:{relative_path}"
    
    def get_directory_structure(self, relative_path: str = "") -> Dict[str, Any]:
        """
        Get directory structure with metadata.
        
        Args:
            relative_path: Path relative to base_path
            
        Returns:
            Dictionary with directory structure
        """
        try:
            target_path = self.base_path / relative_path if relative_path else self.base_path
            
            if not target_path.exists():
                return {"error": "Path not found", "path": relative_path}
            
            if not target_path.is_dir():
                return {"error": "Path is not a directory", "path": relative_path}
            
            items = []
            
            # List all items in directory
            for item in sorted(target_path.iterdir()):
                if item.name == ".metadata.json":
                    continue
                
                item_relative = str(item.relative_to(self.base_path))
                is_dir = item.is_dir()
                
                item_info = {
                    "name": item.name,
                    "path": item_relative,
                    "type": "folder" if is_dir else "file",
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                }
                
                if not is_dir:
                    item_info["size"] = item.stat().st_size
                    item_info["extension"] = item.suffix
                
                items.append(item_info)
            
            return {
                "path": relative_path or "/",
                "items": items,
                "total_items": len(items),
            }
        
        except Exception as e:
            logger.error(f"Error getting directory structure: {e}")
            return {"error": str(e), "path": relative_path}
    
    def create_folder(self, relative_path: str) -> tuple[bool, str]:
        """
        Create a new folder.
        
        Args:
            relative_path: Path relative to base_path
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if ".." in relative_path or relative_path.startswith("/"):
                return False, "Invalid path"
            
            target_path = self.base_path / relative_path
            
            if target_path.exists():
                return False, "Folder already exists"
            
            target_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Created folder: {relative_path}")
            return True, f"Folder created: {relative_path}"
        
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return False, f"Error creating folder: {str(e)}"
    
    def save_file(
        self,
        file_content: bytes,
        relative_path: str,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, str, Optional[str]]:
        """
        Save a file to the knowledge base.
        
        Args:
            file_content: File content as bytes
            relative_path: Directory path relative to base_path
            filename: Name of the file
            metadata: Optional file metadata
            
        Returns:
            Tuple of (success, message, full_relative_path)
        """
        try:
            if ".." in relative_path or ".." in filename:
                return False, "Invalid path", None
            
            # Create directory if it doesn't exist
            target_dir = self.base_path / relative_path if relative_path else self.base_path
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file
            file_path = target_dir / filename
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Update metadata
            full_relative_path = str(Path(relative_path) / filename) if relative_path else filename
            metadata_dict = self._load_metadata()
            
            file_metadata_key = self._get_file_metadata_key(full_relative_path)
            metadata_dict[file_metadata_key] = {
                "filename": filename,
                "size": len(file_content),
                "created": datetime.utcnow().isoformat(),
                "user_metadata": metadata or {},
            }
            
            self._save_metadata(metadata_dict)
            
            logger.info(f"Saved file: {full_relative_path}")
            return True, f"File saved: {filename}", full_relative_path
        
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return False, f"Error saving file: {str(e)}", None
    
    def delete_file(self, relative_path: str) -> tuple[bool, str]:
        """
        Delete a file from the knowledge base.
        
        Args:
            relative_path: Path relative to base_path
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if ".." in relative_path:
                return False, "Invalid path"
            
            file_path = self.base_path / relative_path
            
            if not file_path.exists():
                return False, "File not found"
            
            if not file_path.is_file():
                return False, "Path is not a file"
            
            file_path.unlink()
            
            # Update metadata
            metadata_dict = self._load_metadata()
            file_metadata_key = self._get_file_metadata_key(relative_path)
            if file_metadata_key in metadata_dict:
                del metadata_dict[file_metadata_key]
            
            self._save_metadata(metadata_dict)
            
            logger.info(f"Deleted file: {relative_path}")
            return True, f"File deleted: {relative_path}"
        
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False, f"Error deleting file: {str(e)}"
    
    def delete_folder(self, relative_path: str) -> tuple[bool, str]:
        """
        Delete a folder and all its contents.
        
        Args:
            relative_path: Path relative to base_path
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if ".." in relative_path or relative_path == "":
                return False, "Cannot delete base directory"
            
            folder_path = self.base_path / relative_path
            
            if not folder_path.exists():
                return False, "Folder not found"
            
            if not folder_path.is_dir():
                return False, "Path is not a folder"
            
            # Remove all files from metadata
            metadata_dict = self._load_metadata()
            keys_to_remove = [
                k for k in metadata_dict.keys()
                if k.startswith(f"files:{relative_path}")
            ]
            for key in keys_to_remove:
                del metadata_dict[key]
            
            self._save_metadata(metadata_dict)
            
            # Delete folder
            shutil.rmtree(folder_path)
            
            logger.info(f"Deleted folder: {relative_path}")
            return True, f"Folder deleted: {relative_path}"
        
        except Exception as e:
            logger.error(f"Error deleting folder: {e}")
            return False, f"Error deleting folder: {str(e)}"
    
    def get_file_path(self, relative_path: str) -> Optional[str]:
        """
        Get absolute file path.
        
        Args:
            relative_path: Path relative to base_path
            
        Returns:
            Absolute path or None if not found
        """
        try:
            file_path = self.base_path / relative_path
            if file_path.exists() and file_path.is_file():
                return str(file_path)
        except Exception as e:
            logger.error(f"Error getting file path: {e}")
        return None
    
    def file_exists(self, relative_path: str) -> bool:
        """Check if file exists."""
        try:
            file_path = self.base_path / relative_path
            return file_path.exists() and file_path.is_file()
        except (OSError, ValueError, TypeError):
            return False
