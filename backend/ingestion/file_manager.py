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
                chunk_size=10024,
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
    
    def _get_db_session(self):
        """Get a database session, handling uninitialized SessionLocal."""
        try:
            # Import dynamically to get the latest value
            from database.session import SessionLocal as CurrentSessionLocal
            
            if CurrentSessionLocal is None:
                logger.warning("SessionLocal is not initialized yet")
                return None
            
            # Try to create a session
            session = CurrentSessionLocal()
            return session
        except Exception as e:
            logger.error(f"Error getting database session: {e}")
            return None
    
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
    
    def process_new_file(self, filepath: Path, rel_path: str = None) -> IngestionResult:
        """
        Process a newly created file.
        
        Args:
            filepath: Path to new file (absolute)
            rel_path: Relative path from knowledge base (optional)
            
        Returns:
            IngestionResult
        """
        import time
        start_time = time.time()
        
        # Compute relative path if not provided
        if rel_path is None:
            rel_path = str(filepath.relative_to(self.knowledge_base_path))
        
        file_size_kb = filepath.stat().st_size / 10024
        
        logger.info("="*80)
        logger.info(f"[INGESTION START] NEW FILE")
        logger.info(f"  File: {rel_path}")
        logger.info(f"  Size: {file_size_kb:.1f} KB")
        logger.info(f"  Full path: {filepath}")
        logger.info(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info("="*80)
        
        try:
            # Read file content
            logger.info(f"[INGESTION] Reading file content...")
            content = self._read_file_content(filepath)
            if not content:
                logger.error(f"[INGESTION FAILED] Could not read file content")
                return IngestionResult(
                    success=False,
                    filepath=rel_path,
                    change_type="added",
                    error="Could not read file content",
                )
            
            logger.info(f"[INGESTION] ✓ Read {len(content)} characters")
            logger.info(f"[INGESTION] Extracting text and generating embeddings...")
            
            # Ingest using ingestion service
            filename = filepath.name
            doc_id, message = self.ingestion_service.ingest_text_fast(
                text_content=content,
                filename=filename,
                source=str(self.knowledge_base_path),
                upload_method="file-import",
                source_type="knowledge_base",
                metadata={"file_path": rel_path},
            )
            
            elapsed_time = time.time() - start_time
            
            if doc_id:
                logger.info(f"[INGESTION] ✓ Text extraction and embedding completed")
                logger.info(f"[INGESTION] Document ID: {doc_id}")
                
                # Update database record with file path
                logger.info(f"[INGESTION] Updating document metadata...")
                try:
                    db = self._get_db_session()
                    if db:
                        doc = db.query(Document).filter(Document.id == doc_id).first()
                        if doc:
                            doc.file_path = rel_path
                            db.commit()
                        db.close()
                    logger.info(f"[INGESTION] ✓ Document metadata updated")
                except Exception as e:
                    logger.error(f"[INGESTION] Error updating document file_path: {e}")
                
                # Track file hash using relative path as key
                logger.info(f"[INGESTION] Tracking file state...")
                file_hash = self._compute_file_hash(filepath)
                self.file_states[rel_path] = file_hash
                self._save_state()
                
                # Commit to git
                logger.info(f"[INGESTION] Committing to git...")
                self.git_tracker.add_file(rel_path)
                self.git_tracker.commit_changes(f"Ingested new file: {filename}")
                
                logger.info("="*80)
                logger.info(f"[INGESTION SUCCESS] {rel_path}")
                logger.info(f"  Document ID: {doc_id}")
                logger.info(f"  Processing time: {elapsed_time:.2f} seconds")
                logger.info(f"  Content length: {len(content)} characters")
                logger.info(f"  Message: {message}")
                logger.info(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                logger.info("="*80)
                
                return IngestionResult(
                    success=True,
                    filepath=rel_path,
                    change_type="added",
                    document_id=doc_id,
                    message=message,
                )
            else:
                logger.error(f"[INGESTION FAILED] {rel_path}")
                logger.error(f"  Error: {message}")
                logger.error(f"  Processing time: {elapsed_time:.2f} seconds")
                logger.error(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                logger.error("="*80)
                
                return IngestionResult(
                    success=False,
                    filepath=rel_path,
                    change_type="added",
                    error=message,
                )
        
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error("="*80)
            logger.error(f"[INGESTION EXCEPTION] {rel_path}")
            logger.error(f"  Error: {str(e)}")
            logger.error(f"  Processing time: {elapsed_time:.2f} seconds")
            logger.error(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            logger.error("="*80, exc_info=True)
            
            return IngestionResult(
                success=False,
                filepath=rel_path,
                change_type="added",
                error=str(e),
            )
    
    def process_modified_file(self, filepath: Path, rel_path: str = None) -> IngestionResult:
        """
        Process a modified file (re-ingest with new embeddings).
        
        Args:
            filepath: Path to modified file (absolute)
            rel_path: Relative path from knowledge base (optional)
            
        Returns:
            IngestionResult
        """
        import time
        start_time = time.time()
        
        # Compute relative path if not provided
        if rel_path is None:
            rel_path = str(filepath.relative_to(self.knowledge_base_path))
        
        file_size_kb = filepath.stat().st_size / 10024
        
        logger.info("="*80)
        logger.info(f"[INGESTION START] MODIFIED FILE")
        logger.info(f"  File: {rel_path}")
        logger.info(f"  Size: {file_size_kb:.1f} KB")
        logger.info(f"  Full path: {filepath}")
        logger.info(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info("="*80)
        
        try:
            # Find existing document
            logger.info(f"[INGESTION] Looking up existing document...")
            document = self._find_document_by_path(rel_path)
            if not document:
                logger.warning(f"[INGESTION] Document not found for modified file, treating as new: {filepath}")
                # Treat as new file
                return self.process_new_file(filepath, rel_path)
            
            doc_id = document.id
            logger.info(f"[INGESTION] ✓ Found document {doc_id} for modified file")
            
            # Delete old embeddings
            logger.info(f"[INGESTION] Deleting old embeddings...")
            if not self._delete_document_embeddings(doc_id):
                logger.error(f"[INGESTION] Failed to delete old embeddings")
                return IngestionResult(
                    success=False,
                    filepath=rel_path,
                    change_type="modified",
                    document_id=doc_id,
                    error="Failed to delete old embeddings",
                )
            logger.info(f"[INGESTION] ✓ Old embeddings deleted")
            
            # Read new file content
            logger.info(f"[INGESTION] Reading updated file content...")
            content = self._read_file_content(filepath)
            if not content:
                logger.error(f"[INGESTION] Could not read updated file content")
                return IngestionResult(
                    success=False,
                    filepath=rel_path,
                    change_type="modified",
                    document_id=doc_id,
                    error="Could not read updated file content",
                )
            
            logger.info(f"[INGESTION] ✓ Read {len(content)} characters")
            logger.info(f"[INGESTION] Extracting text and generating new embeddings...")
            
            # Re-ingest with new content
            filename = filepath.name
            
            # Delete and re-create document for clean ingestion
            logger.info(f"[INGESTION] Preparing clean document record...")
            try:
                db = SessionLocal()
                db.delete(document)
                db.commit()
                db.close()
                logger.info(f"[INGESTION] ✓ Old document record removed")
            except Exception as e:
                logger.error(f"[INGESTION] Error deleting document: {e}")
            
            # Ingest as new
            new_doc_id, message = self.ingestion_service.ingest_text_fast(
                text_content=content,
                filename=filename,
                source=str(self.knowledge_base_path),
                upload_method="file-update",
                source_type="knowledge_base",
                metadata={"file_path": rel_path, "updated_from": doc_id},
            )
            
            elapsed_time = time.time() - start_time
            
            if new_doc_id:
                logger.info(f"[INGESTION] ✓ Text extraction and new embeddings completed")
                
                # Update file path
                logger.info(f"[INGESTION] Updating document metadata...")
                try:
                    db = SessionLocal()
                    doc = db.query(Document).filter(Document.id == new_doc_id).first()
                    if doc:
                        doc.file_path = rel_path
                        db.commit()
                    db.close()
                    logger.info(f"[INGESTION] ✓ Document metadata updated")
                except Exception as e:
                    logger.error(f"[INGESTION] Error updating document file_path: {e}")
                
                # Track file hash using relative path as key
                logger.info(f"[INGESTION] Tracking file state...")
                file_hash = self._compute_file_hash(filepath)
                self.file_states[rel_path] = file_hash
                self._save_state()
                
                # Commit to git
                logger.info(f"[INGESTION] Committing to git...")
                self.git_tracker.add_file(rel_path)
                self.git_tracker.commit_changes(f"Updated file: {filename}")
                
                logger.info("="*80)
                logger.info(f"[INGESTION SUCCESS] {rel_path}")
                logger.info(f"  Old Document ID: {doc_id}")
                logger.info(f"  New Document ID: {new_doc_id}")
                logger.info(f"  Processing time: {elapsed_time:.2f} seconds")
                logger.info(f"  Content length: {len(content)} characters")
                logger.info(f"  Message: {message}")
                logger.info(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                logger.info("="*80)
                
                return IngestionResult(
                    success=True,
                    filepath=rel_path,
                    change_type="modified",
                    document_id=new_doc_id,
                    message=f"File updated. Old doc: {doc_id}, New doc: {new_doc_id}",
                )
            else:
                logger.error(f"[INGESTION FAILED] {rel_path}")
                logger.error(f"  Error: {message}")
                logger.error(f"  Processing time: {elapsed_time:.2f} seconds")
                logger.error(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                logger.error("="*80)
                
                return IngestionResult(
                    success=False,
                    filepath=rel_path,
                    change_type="modified",
                    document_id=doc_id,
                    error=message,
                )
        
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error("="*80)
            logger.error(f"[INGESTION EXCEPTION] {rel_path}")
            logger.error(f"  Error: {str(e)}")
            logger.error(f"  Processing time: {elapsed_time:.2f} seconds")
            logger.error(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            logger.error("="*80, exc_info=True)
            
            return IngestionResult(
                success=False,
                filepath=rel_path,
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
        import time
        start_time = time.time()
        
        logger.info("="*80)
        logger.info(f"[INGESTION START] DELETED FILE")
        logger.info(f"  File: {filepath}")
        logger.info(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info("="*80)
        
        try:
            # Find document
            logger.info(f"[INGESTION] Looking up document for deletion...")
            document = self._find_document_by_path(filepath)
            if not document:
                logger.warning(f"[INGESTION] Document not found for deleted file: {filepath}")
                return IngestionResult(
                    success=False,
                    filepath=filepath,
                    change_type="deleted",
                    error="Document not found",
                )
            
            doc_id = document.id
            logger.info(f"[INGESTION] ✓ Found document {doc_id} for deleted file")
            
            logger.info(f"[INGESTION] ✓ Embeddings deleted from vector database")
            
            # Delete database record
            logger.info(f"[INGESTION] Deleting document from database...")
            if not self._delete_document_from_db(doc_id):
                logger.error(f"[INGESTION] Failed to delete document record")
                return IngestionResult(
                    success=False,
                    filepath=filepath,
                    change_type="deleted",
                    document_id=doc_id,
                    error="Failed to delete document record",
                )
            
            logger.info(f"[INGESTION] ✓ Document deleted from database")
            
            # Remove from file states
            logger.info(f"[INGESTION] Updating file tracking state...")
            if filepath in self.file_states:
                del self.file_states[filepath]
            self._save_state()
            
            # Commit to git (remove file from git)
            logger.info(f"[INGESTION] Committing deletion to git...")
            rel_path = Path(filepath).relative_to(self.knowledge_base_path)
            self.git_tracker.remove_file(str(rel_path))
            self.git_tracker.commit_changes(f"Deleted file: {Path(filepath).name}")
            
            elapsed_time = time.time() - start_time
            
            logger.info("="*80)
            logger.info(f"[INGESTION SUCCESS] {filepath}")
            logger.info(f"  Document ID deleted: {doc_id}")
            logger.info(f"  Processing time: {elapsed_time:.2f} seconds")
            logger.info(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            logger.info("="*80)
            
            return IngestionResult(
                success=True,
                filepath=filepath,
                change_type="deleted",
                document_id=doc_id,
                message=f"Deleted document {doc_id} and embeddings",
            )
        
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error("="*80)
            logger.error(f"[INGESTION EXCEPTION] {filepath}")
            logger.error(f"  Error: {str(e)}")
            logger.error(f"  Processing time: {elapsed_time:.2f} seconds")
            logger.error(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            logger.error("="*80, exc_info=True)
            
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
        modified, and deleted files. Also checks database for orphaned
        documents (files that were ingested but no longer exist on disk).
        
        Returns:
            List of IngestionResult for each processed file
        """
        logger.info(f"[SCAN] Scanning knowledge base: {self.knowledge_base_path}")
        import os
        print(f"[DEBUG] Current working directory: {os.getcwd()}")
        print(f"[DEBUG] Knowledge base path: {self.knowledge_base_path}")
        print(f"[DEBUG] Absolute path: {self.knowledge_base_path.resolve()}")
        print(f"[DEBUG] Path exists: {self.knowledge_base_path.exists()}")
        print(f"[DEBUG] Path is directory: {self.knowledge_base_path.is_dir()}")
        if self.knowledge_base_path.exists():
            print(f"[DEBUG] Contents of directory:")
            try:
                for item in self.knowledge_base_path.iterdir():
                    print(f"  - {item.name}")
            except Exception as e:
                print(f"  ERROR reading directory: {e}")
        logger.info(f"[SCAN] Current tracked files: {len(self.file_states)}")
        print(f"\n[DEBUG] Tracked files in state: {list(self.file_states.keys())}")
        
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
        
        logger.info(f"[SCAN] Found {len(current_files)} files on disk")
        for rel_path in sorted(current_files.keys()):
            logger.debug(f"[SCAN]   File: {rel_path}")
        print(f"[DEBUG] Found files on disk: {list(current_files.keys())}")
        
        # Process new and modified files
        for rel_path, filepath in current_files.items():
            file_hash = self._compute_file_hash(filepath)
            old_hash = self.file_states.get(rel_path)
            
            if old_hash is None:
                # New file
                logger.info(f"[SCAN] Detected new file: {rel_path}")
                result = self.process_new_file(filepath, rel_path)
                results.append(result)
                logger.info(f"[SCAN] New file result: success={result.success}, error={result.error}")
            elif old_hash != file_hash:
                # Modified file
                logger.info(f"[SCAN] Detected modified file: {rel_path}")
                result = self.process_modified_file(filepath, rel_path)
                results.append(result)
                logger.info(f"[SCAN] Modified file result: success={result.success}, error={result.error}")
        
        # Process deleted files (from tracked state)
        deleted_files = set(self.file_states.keys()) - set(current_files.keys())
        for rel_path in deleted_files:
            logger.info(f"Detected deleted file: {rel_path}")
            result = self.process_deleted_file(rel_path)
            results.append(result)
        
        # ==================== Handle Orphaned Documents ====================
        # If state file is empty or missing, check database for orphaned documents
        if not self.file_states:
            logger.info("[SCAN] No tracked state found. Checking database for orphaned documents...")
            try:
                # Get a safe database session
                db = self._get_db_session()
                
                if db is None:
                    logger.warning("[SCAN] Could not get database session, skipping orphaned document check")
                    return results
                
                all_documents = db.query(Document).all()
                logger.info(f"[SCAN] Found {len(all_documents)} documents in database")
                
                for doc in all_documents:
                    file_path = doc.file_path
                    if not file_path:
                        logger.debug(f"[SCAN] Document {doc.id} has no file_path, skipping")
                        continue
                    
                    # Check if file exists
                    abs_path = self.knowledge_base_path / file_path
                    if not abs_path.exists():
                        logger.info(f"[SCAN] Found orphaned document: {file_path} (doc_id={doc.id})")
                        result = self.process_deleted_file(file_path)
                        results.append(result)
                    else:
                        # File exists, add to state
                        try:
                            file_hash = self._compute_file_hash(abs_path)
                            self.file_states[file_path] = file_hash
                        except Exception as e:
                            logger.warning(f"[SCAN] Could not hash existing file {file_path}: {e}")
                
                self._save_state()
                db.close()
            except Exception as e:
                logger.error(f"[SCAN] Error checking for orphaned documents: {e}", exc_info=True)
        
        logger.info(f"[SCAN] ✓ Scan complete. Processed {len(results)} changes.")
        return results
    
    def watch_and_process(self, continuous: bool = False, interval: int = 30) -> None:
        """
        Watch directory for changes and process them.
        
        Args:
            continuous: If True, continuously watch for changes
            interval: Time in seconds between scans (default 30 seconds)
        """
        logger.info(f"[WATCH] Starting file watcher for {self.knowledge_base_path}")
        
        if continuous:
            import time
            while True:
                try:
                    self.scan_directory()
                    time.sleep(interval)  # Check every interval seconds
                except Exception as e:
                    logger.error(f"Error in watch loop: {e}")
                    time.sleep(10)
        else:
            self.scan_directory()
