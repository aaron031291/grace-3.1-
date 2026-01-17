"""
API endpoints for NLP file descriptions - making filesystem no-code friendly.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from pathlib import Path

from file_manager.nlp_file_descriptor import NLPFileDescriptor
from file_manager.file_handler import FileHandler
from ollama_client.client import get_ollama_client
from settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nlp-descriptions", tags=["NLP File Descriptions"])


# ==================== Response Models ====================

class FileDescriptionResponse(BaseModel):
    """Response for file description."""
    path: str
    name: str
    type: str
    description: str
    purpose: str
    key_points: List[str]
    technical_level: str
    extension: Optional[str] = None
    file_size: Optional[int] = None
    generated_at: str


class FolderDescriptionResponse(BaseModel):
    """Response for folder description."""
    path: str
    name: str
    description: str
    purpose: str
    file_count: int
    folder_count: int
    main_topics: List[str]
    key_files: List[str]
    generated_at: str


class ProcessingStatusResponse(BaseModel):
    """Response for processing status."""
    status: str  # 'idle', 'processing', 'completed', 'error'
    total: int = 0
    processed: int = 0
    failed: int = 0
    skipped: int = 0
    message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ProcessingStatsResponse(BaseModel):
    """Response for processing statistics."""
    total: int
    processed: int
    failed: int
    skipped: int
    cached: int
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SearchResultsResponse(BaseModel):
    """Response for search results."""
    query: str
    results: List[Dict[str, Any]]
    count: int


# ==================== Global State ====================

# Global descriptor instance
_descriptor: Optional[NLPFileDescriptor] = None
_processing_status = {
    'status': 'idle',
    'total': 0,
    'processed': 0,
    'failed': 0,
    'skipped': 0,
    'message': None,
    'started_at': None,
    'completed_at': None
}


def get_descriptor(root_path: Optional[str] = None) -> NLPFileDescriptor:
    """
    Get or create NLP file descriptor instance.
    
    Args:
        root_path: Root directory to process (default: workspace root)
    """
    global _descriptor
    
    if _descriptor is None:
        if root_path is None:
            # Default to workspace root (parent of backend)
            backend_dir = Path(__file__).parent.parent
            root_path = str(backend_dir.parent)
        
        ollama_client = get_ollama_client()
        file_handler = FileHandler()
        
        _descriptor = NLPFileDescriptor(
            root_path=root_path,
            ollama_client=ollama_client,
            file_handler=file_handler
        )
        logger.info(f"[NLP-API] Initialized descriptor for: {root_path}")
    
    return _descriptor


# ==================== Endpoints ====================

@router.post("/process-all", response_model=ProcessingStatsResponse, summary="Process all files and folders")
async def process_all_files(
    root_path: Optional[str] = Query(None, description="Root directory to process (default: workspace root)"),
    max_workers: int = Query(4, description="Number of parallel workers"),
    force_regenerate: bool = Query(False, description="Force regeneration of all descriptions"),
    background_tasks: BackgroundTasks = None
) -> ProcessingStatsResponse:
    """
    Process all files and folders through NLP to generate natural language descriptions.
    This makes the filesystem "no-code friendly" for non-technical users.
    
    Args:
        root_path: Root directory to process
        max_workers: Number of parallel workers
        force_regenerate: Force regeneration even if cached
        background_tasks: Background tasks handler
    
    Returns:
        ProcessingStatsResponse with statistics
    """
    try:
        descriptor = get_descriptor(root_path)
        
        # Update status
        global _processing_status
        _processing_status = {
            'status': 'processing',
            'total': 0,
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'message': 'Processing started',
            'started_at': datetime.utcnow().isoformat(),
            'completed_at': None
        }
        
        def progress_callback(current: int, total: int, path: str):
            """Update processing status."""
            _processing_status['total'] = total
            _processing_status['processed'] = current
            _processing_status['message'] = f"Processing: {path}"
        
        # Process in background if requested
        if background_tasks:
            def process_task():
                try:
                    stats = descriptor.process_all_files(
                        max_workers=max_workers,
                        force_regenerate=force_regenerate,
                        progress_callback=progress_callback
                    )
                    _processing_status.update({
                        'status': 'completed',
                        'total': stats['total'],
                        'processed': stats['processed'],
                        'failed': stats['failed'],
                        'skipped': stats['skipped'],
                        'message': 'Processing completed',
                        'completed_at': datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.error(f"[NLP-API] Processing error: {e}")
                    _processing_status.update({
                        'status': 'error',
                        'message': str(e),
                        'completed_at': datetime.utcnow().isoformat()
                    })
            
            background_tasks.add_task(process_task)
            
            return ProcessingStatsResponse(
                total=0,
                processed=0,
                failed=0,
                skipped=0,
                cached=len(descriptor.descriptions_cache)
            )
        else:
            # Process synchronously
            stats = descriptor.process_all_files(
                max_workers=max_workers,
                force_regenerate=force_regenerate,
                progress_callback=progress_callback
            )
            
            _processing_status.update({
                'status': 'completed',
                'total': stats['total'],
                'processed': stats['processed'],
                'failed': stats['failed'],
                'skipped': stats['skipped'],
                'message': 'Processing completed',
                'completed_at': datetime.utcnow().isoformat()
            })
            
            return ProcessingStatsResponse(
                total=stats['total'],
                processed=stats['processed'],
                failed=stats['failed'],
                skipped=stats['skipped'],
                cached=stats['cached']
            )
    
    except Exception as e:
        logger.error(f"[NLP-API] Error processing files: {e}", exc_info=True)
        _processing_status.update({
            'status': 'error',
            'message': str(e),
            'completed_at': datetime.utcnow().isoformat()
        })
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/status", response_model=ProcessingStatusResponse, summary="Get processing status")
async def get_processing_status() -> ProcessingStatusResponse:
    """Get current processing status."""
    global _processing_status
    return ProcessingStatusResponse(**_processing_status)


@router.get("/file/{path:path}", response_model=FileDescriptionResponse, summary="Get file description")
async def get_file_description(
    path: str,
    root_path: Optional[str] = Query(None, description="Root directory (default: workspace root)")
) -> FileDescriptionResponse:
    """
    Get natural language description for a specific file.
    
    Args:
        path: Relative path to file
        root_path: Root directory (default: workspace root)
    
    Returns:
        FileDescriptionResponse with description
    """
    try:
        descriptor = get_descriptor(root_path)
        desc = descriptor.get_description(path)
        
        if not desc:
            raise HTTPException(status_code=404, detail=f"Description not found for: {path}")
        
        if desc.get('type') != 'file':
            raise HTTPException(status_code=400, detail=f"Path is not a file: {path}")
        
        return FileDescriptionResponse(
            path=desc['path'],
            name=desc['name'],
            type=desc['type'],
            description=desc['description'],
            purpose=desc['purpose'],
            key_points=desc.get('key_points', []),
            technical_level=desc.get('technical_level', 'intermediate'),
            extension=desc.get('extension'),
            file_size=desc.get('file_size'),
            generated_at=desc.get('generated_at', datetime.utcnow().isoformat())
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[NLP-API] Error getting file description: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folder/{path:path}", response_model=FolderDescriptionResponse, summary="Get folder description")
async def get_folder_description(
    path: str,
    root_path: Optional[str] = Query(None, description="Root directory (default: workspace root)")
) -> FolderDescriptionResponse:
    """
    Get natural language description for a specific folder.
    
    Args:
        path: Relative path to folder
        root_path: Root directory (default: workspace root)
    
    Returns:
        FolderDescriptionResponse with description
    """
    try:
        descriptor = get_descriptor(root_path)
        desc = descriptor.get_description(path)
        
        if not desc:
            raise HTTPException(status_code=404, detail=f"Description not found for: {path}")
        
        if desc.get('type') != 'folder':
            raise HTTPException(status_code=400, detail=f"Path is not a folder: {path}")
        
        return FolderDescriptionResponse(
            path=desc['path'],
            name=desc['name'],
            description=desc['description'],
            purpose=desc['purpose'],
            file_count=desc.get('file_count', 0),
            folder_count=desc.get('folder_count', 0),
            main_topics=desc.get('main_topics', []),
            key_files=desc.get('key_files', []),
            generated_at=desc.get('generated_at', datetime.utcnow().isoformat())
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[NLP-API] Error getting folder description: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all", summary="Get all descriptions")
async def get_all_descriptions(
    root_path: Optional[str] = Query(None, description="Root directory (default: workspace root)")
) -> Dict[str, Any]:
    """
    Get all file and folder descriptions.
    
    Args:
        root_path: Root directory (default: workspace root)
    
    Returns:
        Dictionary mapping paths to descriptions
    """
    try:
        descriptor = get_descriptor(root_path)
        return descriptor.get_all_descriptions()
    
    except Exception as e:
        logger.error(f"[NLP-API] Error getting all descriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=SearchResultsResponse, summary="Search descriptions")
async def search_descriptions(
    query: str = Query(..., description="Search query"),
    root_path: Optional[str] = Query(None, description="Root directory (default: workspace root)")
) -> SearchResultsResponse:
    """
    Search file and folder descriptions by keyword.
    
    Args:
        query: Search query string
        root_path: Root directory (default: workspace root)
    
    Returns:
        SearchResultsResponse with matching descriptions
    """
    try:
        descriptor = get_descriptor(root_path)
        results = descriptor.search_descriptions(query)
        
        return SearchResultsResponse(
            query=query,
            results=results,
            count=len(results)
        )
    
    except Exception as e:
        logger.error(f"[NLP-API] Error searching descriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-file", response_model=FileDescriptionResponse, summary="Process single file")
async def process_single_file(
    path: str = Query(..., description="Relative path to file"),
    root_path: Optional[str] = Query(None, description="Root directory (default: workspace root)")
) -> FileDescriptionResponse:
    """
    Process a single file and generate description.
    
    Args:
        path: Relative path to file
        root_path: Root directory (default: workspace root)
    
    Returns:
        FileDescriptionResponse with description
    """
    try:
        descriptor = get_descriptor(root_path)
        
        # Get absolute path
        file_path = Path(descriptor.root_path) / path
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {path}")
        
        # Process file
        result = descriptor._process_file(file_path)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to process file")
        
        # Save to cache
        descriptor.descriptions_cache[path] = result
        descriptor._save_cache()
        
        return FileDescriptionResponse(
            path=result['path'],
            name=result['name'],
            type=result['type'],
            description=result['description'],
            purpose=result['purpose'],
            key_points=result.get('key_points', []),
            technical_level=result.get('technical_level', 'intermediate'),
            extension=result.get('extension'),
            file_size=result.get('file_size'),
            generated_at=result.get('generated_at', datetime.utcnow().isoformat())
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[NLP-API] Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-folder", response_model=FolderDescriptionResponse, summary="Process single folder")
async def process_single_folder(
    path: str = Query(..., description="Relative path to folder"),
    root_path: Optional[str] = Query(None, description="Root directory (default: workspace root)")
) -> FolderDescriptionResponse:
    """
    Process a single folder and generate description.
    
    Args:
        path: Relative path to folder
        root_path: Root directory (default: workspace root)
    
    Returns:
        FolderDescriptionResponse with description
    """
    try:
        descriptor = get_descriptor(root_path)
        
        # Get absolute path
        folder_path = Path(descriptor.root_path) / path
        
        if not folder_path.exists():
            raise HTTPException(status_code=404, detail=f"Folder not found: {path}")
        
        if not folder_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a folder: {path}")
        
        # Process folder
        result = descriptor._process_folder(folder_path)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to process folder")
        
        # Save to cache
        descriptor.descriptions_cache[path] = result
        descriptor._save_cache()
        
        return FolderDescriptionResponse(
            path=result['path'],
            name=result['name'],
            description=result['description'],
            purpose=result['purpose'],
            file_count=result.get('file_count', 0),
            folder_count=result.get('folder_count', 0),
            main_topics=result.get('main_topics', []),
            key_files=result.get('key_files', []),
            generated_at=result.get('generated_at', datetime.utcnow().isoformat())
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[NLP-API] Error processing folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))
