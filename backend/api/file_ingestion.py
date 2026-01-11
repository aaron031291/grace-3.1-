"""
API endpoints for file-based ingestion management.
Provides REST endpoints to trigger and monitor file-based ingestion.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import logging

from ingestion.file_manager import IngestionFileManager, IngestionResult
from api.ingest import get_ingestion_service
from embedding.embedder import get_embedding_model
from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKeyType
from database.session import get_session
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/file-ingest", tags=["File-Based Ingestion"])

# Global file manager instance
_file_manager: Optional[IngestionFileManager] = None


def get_file_manager() -> IngestionFileManager:
    """Get or create file ingestion manager."""
    global _file_manager
    
    if _file_manager is None:
        try:
            from pathlib import Path
            import os
            logger.info("[FILE_INGEST] Initializing file ingestion manager...")
            ingestion_service = get_ingestion_service()
            embedding_model = get_embedding_model()
            
            # Use absolute path to knowledge base
            kb_path = Path(os.path.dirname(__file__)).parent / "knowledge_base"
            
            _file_manager = IngestionFileManager(
                knowledge_base_path=kb_path,
                embedding_model=embedding_model,
                ingestion_service=ingestion_service,
            )
            logger.info(f"[FILE_INGEST] [OK] File manager initialized with path: {kb_path}")
        except Exception as e:
            logger.error(f"Failed to initialize file manager: {e}")
            raise HTTPException(
                status_code=500,
                detail="File manager initialization failed"
            )
    
    return _file_manager


# ==================== Pydantic Models ====================

class FileIngestionResultItem(BaseModel):
    """Result of a file ingestion operation."""
    success: bool
    filepath: str
    change_type: str  # 'added', 'modified', 'deleted'
    document_id: Optional[int] = None
    message: str = ""
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ScanResults(BaseModel):
    """Results from scanning knowledge base."""
    total_processed: int
    successful: int
    failed: int
    results: List[FileIngestionResultItem]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class FileManagerStatus(BaseModel):
    """Status of file manager."""
    initialized: bool
    knowledge_base_path: str
    tracked_files: int
    git_initialized: bool
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ==================== Endpoints ====================

@router.get("/status", response_model=FileManagerStatus)
async def get_status(file_manager: IngestionFileManager = Depends(get_file_manager)):
    """Get file manager status."""
    try:
        git_dir = file_manager.knowledge_base_path / ".git"
        return FileManagerStatus(
            initialized=True,
            knowledge_base_path=str(file_manager.knowledge_base_path),
            tracked_files=len(file_manager.file_states),
            git_initialized=git_dir.exists(),
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan", response_model=ScanResults)
async def scan_knowledge_base(
    file_manager: IngestionFileManager = Depends(get_file_manager),
    session: Session = Depends(get_session)
):
    """
    Scan knowledge base for file changes and process them.

    - New files: Trigger ingestion
    - Modified files: Delete old embeddings and re-ingest
    - Deleted files: Remove embeddings and metadata
    """
    try:
        logger.info("[API] Starting knowledge base scan")

        # ✅ GENESIS KEY: Track file ingestion request
        genesis_service = get_genesis_service(session)
        genesis_key = genesis_service.create_key(
            key_type=GenesisKeyType.USER_INPUT,
            what_description="File ingestion scan requested",
            who_actor="system",
            where_location="file_ingestion_api",
            why_reason="User triggered knowledge base file scan",
            how_method="POST /file-ingest/scan",
            context_data={"endpoint": "/file-ingest/scan"},
            session=session
        )
        logger.info(f"✅ Genesis Key created for file scan: {genesis_key.key_id}")

        results = file_manager.scan_directory()
        
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        
        return ScanResults(
            total_processed=len(results),
            successful=successful,
            failed=failed,
            results=[
                FileIngestionResultItem(
                    success=r.success,
                    filepath=r.filepath,
                    change_type=r.change_type,
                    document_id=r.document_id,
                    message=r.message,
                    error=r.error,
                )
                for r in results
            ],
        )
    
    except Exception as e:
        logger.error(f"Error scanning knowledge base: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan-background", response_model=dict)
async def scan_knowledge_base_background(
    background_tasks: BackgroundTasks,
    file_manager: IngestionFileManager = Depends(get_file_manager),
):
    """
    Scan knowledge base for file changes in background.
    
    Returns immediately with a task ID. Results are logged asynchronously.
    """
    try:
        logger.info("[API] Starting background knowledge base scan")
        
        def scan_task():
            try:
                results = file_manager.scan_directory()
                logger.info(f"[OK] Background scan completed: {len(results)} changes processed")
                for result in results:
                    status = "[OK]" if result.success else "[FAIL]"
                    logger.info(f"  {status} {result.change_type}: {result.filepath}")
            except Exception as e:
                logger.error(f"[FAIL] Error in background scan: {e}", exc_info=True)
        
        background_tasks.add_task(scan_task)
        
        return {
            "status": "Background scan started",
            "knowledge_base_path": str(file_manager.knowledge_base_path),
        }
    
    except Exception as e:
        logger.error(f"Error starting background scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/initialize-git")
async def initialize_git(
    file_manager: IngestionFileManager = Depends(get_file_manager),
):
    """Initialize git repository for knowledge base tracking."""
    try:
        logger.info("[API] Initializing git repository")
        success = file_manager.git_tracker.initialize_git()
        
        if success:
            return {
                "status": "success",
                "message": "Git repository initialized",
                "path": str(file_manager.knowledge_base_path),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize git repository"
            )
    
    except Exception as e:
        logger.error(f"Error initializing git: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tracked-files")
async def get_tracked_files(
    file_manager: IngestionFileManager = Depends(get_file_manager),
):
    """Get list of tracked files and their hashes."""
    try:
        return {
            "count": len(file_manager.file_states),
            "files": [
                {
                    "filepath": filepath,
                    "hash": hash_val,
                }
                for filepath, hash_val in sorted(file_manager.file_states.items())
            ],
        }
    
    except Exception as e:
        logger.error(f"Error getting tracked files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-tracking")
async def clear_tracking_state(
    file_manager: IngestionFileManager = Depends(get_file_manager),
):
    """Clear file tracking state (reset all tracked hashes)."""
    try:
        logger.info("[API] Clearing file tracking state")
        old_count = len(file_manager.file_states)
        file_manager.file_states.clear()
        file_manager._save_state()
        
        return {
            "status": "success",
            "message": "Tracking state cleared",
            "cleared_count": old_count,
        }
    
    except Exception as e:
        logger.error(f"Error clearing tracking state: {e}")
        raise HTTPException(status_code=500, detail=str(e))
