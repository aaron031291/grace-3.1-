"""
Git-based ingestion file manager for tracking knowledge base files.
Monitors backend/knowledge_base for changes and triggers appropriate ingestion actions.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, field
import hashlib

from ingestion.service import TextIngestionService
from embedding.embedder import EmbeddingModel, get_embedding_model
from vector_db.client import get_qdrant_client
from database.session import SessionLocal
from models.database_models import Document, DocumentChunk

logger = logging.getLogger(__name__)


@dataclass
class FileChange:
    """Represents a change to a file in the knowledge base."""
    filepath: str
    change_type: str  # 'added', 'modified', 'deleted'
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    content: Optional[str] = None


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""
    success: bool
    filepath: str
    change_type: str
    document_id: Optional[int] = None
    message: str = ""
    error: Optional[str] = None


class GitFileTracker:
    """Tracks files in a directory using git."""
    
    def __init__(self, repo_path: str):
        """
        Initialize git file tracker.
        
        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = Path(repo_path)
        self.git_dir = self.repo_path / ".git"
        
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
    
    def _run_git_command(self, command: List[str]) -> Tuple[str, int]:
        """
        Run a git command in the repository.
        
        Args:
            command: Git command as list of strings
            
        Returns:
            Tuple of (output, return_code)
        """
        try:
            result = subprocess.run(
                ["git"] + command,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout.strip(), result.returncode
        except subprocess.TimeoutExpired:
            logger.error(f"Git command timed out: {' '.join(command)}")
            return "", 1
        except Exception as e:
            logger.error(f"Error running git command: {e}")
            return "", 1
    
    def initialize_git(self) -> bool:
        """
        Initialize git repository if not already initialized.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self.git_dir.exists():
            logger.info(f"Git repository already exists at {self.repo_path}")
            return True
        
        try:
            output, code = self._run_git_command(["init"])
            if code == 0:
                logger.info(f"✓ Initialized git repository at {self.repo_path}")
                # Set git config
                self._run_git_command(["config", "user.email", "ingestion@grace.local"])
                self._run_git_command(["config", "user.name", "Grace Ingestion Manager"])
                return True
            else:
                logger.error(f"Failed to initialize git repository: {output}")
                return False
        except Exception as e:
            logger.error(f"Error initializing git repository: {e}")
            return False
    
    def get_file_hash(self, filepath: str) -> Optional[str]:
        """
        Get the git tree hash of a file.
        
        Args:
            filepath: Path to file relative to repo
            
        Returns:
            Git object hash or None if file not found
        """
        try:
            output, code = self._run_git_command(["hash-object", filepath])
            if code == 0 and output:
                return output
            return None
        except Exception as e:
            logger.error(f"Error getting file hash: {e}")
            return None
    
    def get_staged_changes(self) -> List[FileChange]:
        """
        Get staged changes in the repository.
        
        Returns:
            List of FileChange objects for staged changes
        """
        changes = []
        try:
            # Get staged changes with status
            output, code = self._run_git_command([
                "diff-index", "--cached", "--diff-filter=ACMDU", "HEAD"
            ])
            
            if code != 0:
                # If HEAD doesn't exist yet, use empty tree
                output, code = self._run_git_command([
                    "diff-index", "--cached", "--diff-filter=ACMDU", 
                    "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # Empty tree hash
                ])
            
            for line in output.split('\n'):
                if not line.strip():
                    continue
                
                parts = line.split('\t')
                if len(parts) >= 2:
                    filepath = parts[-1]
                    change_info = parts[0].split()
                    
                    if len(change_info) >= 5:
                        change_type_char = change_info[4]
                        change_type = self._map_git_change_type(change_type_char)
                        
                        changes.append(FileChange(
                            filepath=filepath,
                            change_type=change_type,
                            new_hash=change_info[3] if change_type != 'deleted' else None,
                            old_hash=change_info[2] if change_type in ['modified', 'deleted'] else None,
                        ))
        except Exception as e:
            logger.error(f"Error getting staged changes: {e}")
        
        return changes
    
    def get_untracked_files(self) -> List[str]:
        """
        Get list of untracked files in the repository.
        
        Returns:
            List of file paths
        """
        try:
            output, code = self._run_git_command(["ls-files", "--others", "--exclude-standard"])
            if code == 0:
                return [f for f in output.split('\n') if f.strip()]
            return []
        except Exception as e:
            logger.error(f"Error getting untracked files: {e}")
            return []
    
    def add_file(self, filepath: str) -> bool:
        """
        Stage a file for commit.
        
        Args:
            filepath: Path to file relative to repo
            
        Returns:
            bool: True if successful
        """
        try:
            _, code = self._run_git_command(["add", filepath])
            return code == 0
        except Exception as e:
            logger.error(f"Error adding file to git: {e}")
            return False
    
    def remove_file(self, filepath: str) -> bool:
        """
        Remove a file from git tracking.
        
        Args:
            filepath: Path to file relative to repo
            
        Returns:
            bool: True if successful
        """
        try:
            _, code = self._run_git_command(["rm", "--cached", filepath])
            return code == 0
        except Exception as e:
            logger.error(f"Error removing file from git: {e}")
            return False
    
    def commit_changes(self, message: str) -> bool:
        """
        Commit staged changes.
        
        Args:
            message: Commit message
            
        Returns:
            bool: True if successful
        """
        try:
            _, code = self._run_git_command(["commit", "-m", message])
            return code == 0
        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            return False
    
    @staticmethod
    def _map_git_change_type(char: str) -> str:
        """Map git change type character to readable format."""
        mapping = {
            'A': 'added',
            'M': 'modified',
            'D': 'deleted',
            'C': 'copied',
            'R': 'renamed',
        }
        return mapping.get(char, 'unknown')


class IngestionFileManager:
    """
    Manages file-based document ingestion using git tracking.
    
    Monitors a directory for file changes and triggers appropriate
    ingestion, update, or deletion operations.
    """
    
    def __init__(
        self,
        knowledge_base_path: str,
        embedding_model: Optional[EmbeddingModel] = None,
        ingestion_service: Optional[TextIngestionService] = None,
    ):
        """
        Initialize ingestion file manager.
        
        Args:
            knowledge_base_path: Path to knowledge base directory
            embedding_model: Optional EmbeddingModel instance
            ingestion_service: Optional TextIngestionService instance
        """
        self.knowledge_base_path = Path(knowledge_base_path)
        self.git_tracker = GitFileTracker(str(self.knowledge_base_path))
        
        # Initialize or get embedding model
        self.embedding_model = embedding_model or get_embedding_model()
        
        # Initialize or get ingestion service
        if ingestion_service is None:
            self.ingestion_service = TextIngestionService(
                collection_name="documents",
                chunk_size=512,
                chunk_overlap=50,
                embedding_model=self.embedding_model,
            )
        else:
            self.ingestion_service = ingestion_service
        
        self.qdrant_client = get_qdrant_client()
        self.state_file = self.knowledge_base_path / ".ingestion_state.json"
        self._load_state()
    
    def _load_state(self) -> None:
        """Load previously tracked file hashes."""
        self.file_states: Dict[str, str] = {}
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    self.file_states = json.load(f)
                logger.info(f"Loaded ingestion state: {len(self.file_states)} files")
            except Exception as e:
                logger.error(f"Error loading state file: {e}")
                self.file_states = {}
    
    def _save_state(self) -> None:
        """Save tracked file hashes to state file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.file_states, f, indent=2)
            logger.debug(f"Saved ingestion state: {len(self.file_states)} files")
        except Exception as e:
            logger.error(f"Error saving state file: {e}")
    
    def _compute_file_hash(self, filepath: Path) -> str:
        """
        Compute SHA256 hash of file content.
        
        Args:
            filepath: Path to file
            
        Returns:
            Hex digest of SHA256 hash
        """
        try:
            with open(filepath, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error computing file hash: {e}")
            return ""
    
    def _read_file_content(self, filepath: Path) -> Optional[str]:
        """
        Read file content safely.
        
        Args:
            filepath: Path to file
            
        Returns:
            File content or None if unreadable
        """
        try:
            # Try UTF-8 first
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                # Fall back to latin-1 (always works)
                with open(filepath, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Could not read file {filepath}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return None
    
    def _is_ingestionable_file(self, filepath: Path) -> bool:
        """
        Check if file should be ingested.
        
        Args:
            filepath: Path to file
            
        Returns:
            bool: True if file should be ingested
        """
        # Skip metadata and git files
        if filepath.name.startswith('.'):
            return False
        
        # Skip directories
        if filepath.is_dir():
            return False
        
        # Supported file extensions
        supported_extensions = {
            '.txt', '.md', '.pdf', '.docx', '.doc',
            '.json', '.yaml', '.yml', '.xml', '.html',
            '.py', '.js', '.ts', '.java', '.cpp', '.c',
        }
        
        return filepath.suffix.lower() in supported_extensions
    
    def _find_document_by_path(self, filepath: str) -> Optional[Document]:
        """
        Find document record by file path.
        
        Args:
            filepath: File path
            
        Returns:
            Document record or None
        """
        try:
            db = SessionLocal()
            # Search by file_path or filename
            doc = db.query(Document).filter(
                (Document.file_path == str(filepath)) |
                (Document.filename == filepath) |
                (Document.filename == str(Path(filepath).name))
            ).first()
            db.close()
            return doc
        except Exception as e:
            logger.error(f"Error finding document: {e}")
            return None
    
    def _delete_document_embeddings(self, document_id: int) -> bool:
        """
        Delete all embeddings and chunks for a document.
        
        Args:
            document_id: ID of document
            
        Returns:
            bool: True if successful
        """
        try:
            db = SessionLocal()
            
            # Get all chunks for document
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).all()
            
            # Delete from Qdrant
            vector_ids = [
                int(chunk.embedding_vector_id) 
                for chunk in chunks 
                if chunk.embedding_vector_id
            ]
            
            if vector_ids:
                logger.info(f"Deleting {len(vector_ids)} vectors from Qdrant")
                self.qdrant_client.delete_vectors(
                    collection_name=self.ingestion_service.collection_name,
                    vector_ids=vector_ids,
                )
            
            # Delete from database
            for chunk in chunks:
                db.delete(chunk)
            
            db.commit()
            logger.info(f"✓ Deleted embeddings for document {document_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting embeddings: {e}")
            return False
        finally:
            db.close()
    
    def _delete_document_from_db(self, document_id: int) -> bool:
        """
        Delete document record from database.
        
        Args:
            document_id: ID of document
            
        Returns:
            bool: True if successful
        """
        try:
            db = SessionLocal()
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                db.delete(doc)
                db.commit()
                logger.info(f"✓ Deleted document record {document_id} from database")
                return True
            db.close()
            return False
        except Exception as e:
            logger.error(f"Error deleting document from database: {e}")
            return False
        finally:
            db.close()
    
    def process_new_file(self, filepath: Path) -> IngestionResult:
        """
        Process a newly created file.
        
        Args:
            filepath: Path to new file
            
        Returns:
            IngestionResult
        """
        logger.info(f"[NEW FILE] Processing: {filepath}")
        
        try:
            # Read file content
            content = self._read_file_content(filepath)
            if not content:
                return IngestionResult(
                    success=False,
                    filepath=str(filepath),
                    change_type="added",
                    error="Could not read file content",
                )
            
            # Ingest using ingestion service
            filename = filepath.name
            doc_id, message = self.ingestion_service.ingest_text_fast(
                text_content=content,
                filename=filename,
                source=str(self.knowledge_base_path),
                upload_method="file-import",
                source_type="knowledge_base",
                metadata={"file_path": str(filepath)},
            )
            
            if doc_id:
                # Update database record with file path
                try:
                    db = SessionLocal()
                    doc = db.query(Document).filter(Document.id == doc_id).first()
                    if doc:
                        doc.file_path = str(filepath)
                        db.commit()
                    db.close()
                except Exception as e:
                    logger.error(f"Error updating document file_path: {e}")
                
                # Track file hash
                file_hash = self._compute_file_hash(filepath)
                self.file_states[str(filepath)] = file_hash
                self._save_state()
                
                # Commit to git
                rel_path = filepath.relative_to(self.knowledge_base_path)
                self.git_tracker.add_file(str(rel_path))
                self.git_tracker.commit_changes(f"Ingested new file: {filename}")
                
                return IngestionResult(
                    success=True,
                    filepath=str(filepath),
                    change_type="added",
                    document_id=doc_id,
                    message=message,
                )
            else:
                return IngestionResult(
                    success=False,
                    filepath=str(filepath),
                    change_type="added",
                    error=message,
                )
        
        except Exception as e:
            logger.error(f"Error processing new file: {e}", exc_info=True)
            return IngestionResult(
                success=False,
                filepath=str(filepath),
                change_type="added",
                error=str(e),
            )
    
    def process_modified_file(self, filepath: Path) -> IngestionResult:
        """
        Process a modified file (re-ingest with new embeddings).
        
        Args:
            filepath: Path to modified file
            
        Returns:
            IngestionResult
        """
        logger.info(f"[MODIFIED FILE] Processing: {filepath}")
        
        try:
            # Find existing document
            document = self._find_document_by_path(str(filepath))
            if not document:
                logger.warning(f"Document not found for modified file: {filepath}")
                # Treat as new file
                return self.process_new_file(filepath)
            
            doc_id = document.id
            logger.info(f"Found document {doc_id} for modified file")
            
            # Delete old embeddings
            if not self._delete_document_embeddings(doc_id):
                return IngestionResult(
                    success=False,
                    filepath=str(filepath),
                    change_type="modified",
                    document_id=doc_id,
                    error="Failed to delete old embeddings",
                )
            
            # Read new file content
            content = self._read_file_content(filepath)
            if not content:
                return IngestionResult(
                    success=False,
                    filepath=str(filepath),
                    change_type="modified",
                    document_id=doc_id,
                    error="Could not read updated file content",
                )
            
            # Re-ingest with new content
            filename = filepath.name
            
            # Delete and re-create document for clean ingestion
            try:
                db = SessionLocal()
                db.delete(document)
                db.commit()
                db.close()
            except Exception as e:
                logger.error(f"Error deleting document: {e}")
            
            # Ingest as new
            new_doc_id, message = self.ingestion_service.ingest_text_fast(
                text_content=content,
                filename=filename,
                source=str(self.knowledge_base_path),
                upload_method="file-update",
                source_type="knowledge_base",
                metadata={"file_path": str(filepath), "updated_from": doc_id},
            )
            
            if new_doc_id:
                # Update file path
                try:
                    db = SessionLocal()
                    doc = db.query(Document).filter(Document.id == new_doc_id).first()
                    if doc:
                        doc.file_path = str(filepath)
                        db.commit()
                    db.close()
                except Exception as e:
                    logger.error(f"Error updating document file_path: {e}")
                
                # Track file hash
                file_hash = self._compute_file_hash(filepath)
                self.file_states[str(filepath)] = file_hash
                self._save_state()
                
                # Commit to git
                rel_path = filepath.relative_to(self.knowledge_base_path)
                self.git_tracker.add_file(str(rel_path))
                self.git_tracker.commit_changes(f"Updated file: {filename}")
                
                return IngestionResult(
                    success=True,
                    filepath=str(filepath),
                    change_type="modified",
                    document_id=new_doc_id,
                    message=f"File updated. Old doc: {doc_id}, New doc: {new_doc_id}",
                )
            else:
                return IngestionResult(
                    success=False,
                    filepath=str(filepath),
                    change_type="modified",
                    document_id=doc_id,
                    error=message,
                )
        
        except Exception as e:
            logger.error(f"Error processing modified file: {e}", exc_info=True)
            return IngestionResult(
                success=False,
                filepath=str(filepath),
                change_type="modified",
                error=str(e),
            )
    
    def process_deleted_file(self, filepath: str) -> IngestionResult:
        """
        Process a deleted file (remove embeddings and metadata).
        
        Args:
            filepath: Path to deleted file
            
        Returns:
            IngestionResult
        """
        logger.info(f"[DELETED FILE] Processing: {filepath}")
        
        try:
            # Find document
            document = self._find_document_by_path(filepath)
            if not document:
                logger.warning(f"Document not found for deleted file: {filepath}")
                return IngestionResult(
                    success=False,
                    filepath=filepath,
                    change_type="deleted",
                    error="Document not found",
                )
            
            doc_id = document.id
            logger.info(f"Found document {doc_id} for deleted file")
            
            # Delete embeddings
            if not self._delete_document_embeddings(doc_id):
                return IngestionResult(
                    success=False,
                    filepath=filepath,
                    change_type="deleted",
                    document_id=doc_id,
                    error="Failed to delete embeddings",
                )
            
            # Delete database record
            if not self._delete_document_from_db(doc_id):
                return IngestionResult(
                    success=False,
                    filepath=filepath,
                    change_type="deleted",
                    document_id=doc_id,
                    error="Failed to delete document record",
                )
            
            # Remove from file states
            if filepath in self.file_states:
                del self.file_states[filepath]
            self._save_state()
            
            # Commit to git (remove file from git)
            rel_path = Path(filepath).relative_to(self.knowledge_base_path)
            self.git_tracker.remove_file(str(rel_path))
            self.git_tracker.commit_changes(f"Deleted file: {Path(filepath).name}")
            
            return IngestionResult(
                success=True,
                filepath=filepath,
                change_type="deleted",
                document_id=doc_id,
                message=f"Deleted document {doc_id} and embeddings",
            )
        
        except Exception as e:
            logger.error(f"Error processing deleted file: {e}", exc_info=True)
            return IngestionResult(
                success=False,
                filepath=filepath,
                change_type="deleted",
                error=str(e),
            )
    
    def scan_directory(self) -> List[IngestionResult]:
        """
        Scan knowledge base directory for changes and process them.
        
        Compares current files with tracked state and processes new,
        modified, and deleted files.
        
        Returns:
            List of IngestionResult for each processed file
        """
        logger.info(f"[SCAN] Scanning knowledge base: {self.knowledge_base_path}")
        
        results = []
        
        # Initialize git if needed
        self.git_tracker.initialize_git()
        
        # Get current files
        current_files: Dict[str, Path] = {}
        for filepath in self.knowledge_base_path.rglob("*"):
            if not self._is_ingestionable_file(filepath):
                continue
            
            rel_path = str(filepath.relative_to(self.knowledge_base_path))
            current_files[rel_path] = filepath
        
        # Process new and modified files
        for rel_path, filepath in current_files.items():
            file_hash = self._compute_file_hash(filepath)
            old_hash = self.file_states.get(rel_path)
            
            if old_hash is None:
                # New file
                logger.info(f"Detected new file: {rel_path}")
                result = self.process_new_file(filepath)
                results.append(result)
            elif old_hash != file_hash:
                # Modified file
                logger.info(f"Detected modified file: {rel_path}")
                result = self.process_modified_file(filepath)
                results.append(result)
        
        # Process deleted files
        deleted_files = set(self.file_states.keys()) - set(current_files.keys())
        for rel_path in deleted_files:
            logger.info(f"Detected deleted file: {rel_path}")
            result = self.process_deleted_file(rel_path)
            results.append(result)
        
        logger.info(f"[SCAN] ✓ Scan complete. Processed {len(results)} changes.")
        return results
    
    def watch_and_process(self, continuous: bool = False) -> None:
        """
        Watch directory for changes and process them.
        
        Args:
            continuous: If True, continuously watch for changes
        """
        logger.info(f"[WATCH] Starting file watcher for {self.knowledge_base_path}")
        
        if continuous:
            import time
            while True:
                try:
                    self.scan_directory()
                    time.sleep(5)  # Check every 5 seconds
                except Exception as e:
                    logger.error(f"Error in watch loop: {e}")
                    time.sleep(10)
        else:
            self.scan_directory()
