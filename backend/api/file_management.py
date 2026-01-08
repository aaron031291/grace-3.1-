"""
File management API endpoints.
Handles knowledge_base directory operations and file uploads.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
import logging
import os
import json

from file_manager.knowledge_base_manager import KnowledgeBaseManager
from file_manager.file_handler import extract_file_text
from ingestion.service import TextIngestionService
from embedding.embedder import get_embedding_model
from models.database_models import Document
from database.session import initialize_session_factory
from database import connection

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/files", tags=["File Management"])

# Global instances
_kb_manager: Optional[KnowledgeBaseManager] = None
_ingestion_service: Optional[TextIngestionService] = None


def get_db_session():
    """Get a database session, initializing if needed."""
    from database.session import SessionLocal
    if SessionLocal is None:
        initialize_session_factory()
    from database.session import SessionLocal
    return SessionLocal()


def get_kb_manager() -> KnowledgeBaseManager:
    """Get or create knowledge base manager."""
    global _kb_manager
    
    if _kb_manager is None:
        _kb_manager = KnowledgeBaseManager(base_path="knowledge_base")
    
    return _kb_manager


def get_ingestion_service() -> TextIngestionService:
    """Get or create ingestion service."""
    global _ingestion_service
    
    if _ingestion_service is None:
        try:
            print("[FILES] Initializing ingestion service...")
            embedding_model = get_embedding_model()
            print("[FILES] ✓ Got embedding model (singleton)")
            _ingestion_service = TextIngestionService(
                collection_name="documents",
                chunk_size=10024,
                chunk_overlap=50,
                embedding_model=embedding_model,
            )
            print("[FILES] ✓ Ingestion service created successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ingestion service: {e}")
            raise HTTPException(
                status_code=500,
                detail="Ingestion service initialization failed"
            )
    
    return _ingestion_service


# ==================== Pydantic Models ====================

class DirectoryItem(BaseModel):
    """Item in a directory."""
    name: str
    path: str
    type: str  # "file" or "folder"
    size: Optional[int] = None
    extension: Optional[str] = None
    modified: str


class DirectoryStructure(BaseModel):
    """Directory structure response."""
    path: str
    items: List[DirectoryItem]
    total_items: int


class FileUploadResponse(BaseModel):
    """Response for file upload."""
    success: bool
    message: str
    file_path: Optional[str] = None
    document_id: Optional[int] = None  # ID of ingested document if applicable


class FolderCreateResponse(BaseModel):
    """Response for folder creation."""
    success: bool
    message: str


class FileDeleteResponse(BaseModel):
    """Response for file deletion."""
    success: bool
    message: str


# ==================== Endpoints ====================

@router.get("/browse", response_model=DirectoryStructure, summary="Browse knowledge base directory")
async def browse_directory(
    path: str = Query("", description="Directory path relative to knowledge_base root"),
    kb_manager: KnowledgeBaseManager = Depends(get_kb_manager)
) -> DirectoryStructure:
    """
    Browse directory structure in knowledge_base.
    
    Args:
        path: Directory path relative to knowledge_base root
        kb_manager: Knowledge base manager instance
        
    Returns:
        DirectoryStructure with items in the directory
    """
    try:
        structure = kb_manager.get_directory_structure(path)
        
        if "error" in structure:
            raise HTTPException(status_code=404, detail=structure["error"])
        
        return DirectoryStructure(
            path=structure["path"],
            items=[DirectoryItem(**item) for item in structure["items"]],
            total_items=structure["total_items"],
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error browsing directory: {e}")
        raise HTTPException(status_code=500, detail="Failed to browse directory")


@router.post("/create-folder", response_model=FolderCreateResponse, summary="Create new folder")
async def create_folder(
    path: str = Query(..., description="Folder path relative to knowledge_base root"),
    kb_manager: KnowledgeBaseManager = Depends(get_kb_manager)
) -> FolderCreateResponse:
    """
    Create a new folder in knowledge_base.
    
    Args:
        path: Folder path relative to knowledge_base root
        kb_manager: Knowledge base manager instance
        
    Returns:
        FolderCreateResponse with success status
    """
    try:
        success, message = kb_manager.create_folder(path)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return FolderCreateResponse(
            success=True,
            message=message,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating folder: {e}")
        raise HTTPException(status_code=500, detail="Failed to create folder")


@router.post("/upload", response_model=FileUploadResponse, summary="Upload file to knowledge base")
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    folder_path: str = Form("", description="Folder path relative to knowledge_base root"),
    ingest: str = Form("true", description="Whether to ingest the file into vector DB"),
    source_type: str = Form("user_generated", description="Type of source for reliability"),
    kb_manager: KnowledgeBaseManager = Depends(get_kb_manager),
    service: TextIngestionService = Depends(get_ingestion_service)
) -> FileUploadResponse:
    """
    Upload a file to knowledge_base and optionally ingest it.
    
    Supports: TXT, MD, PDF, DOCX, XLSX, and other text-based formats
    
    Args:
        file: File to upload
        folder_path: Target folder path relative to knowledge_base root
        ingest: Whether to ingest file into vector database (string "true"/"false")
        source_type: Type of source for reliability calculation
        kb_manager: Knowledge base manager instance
        service: Ingestion service instance
        
    Returns:
        FileUploadResponse with file path and document ID if ingested
    """
    try:
        # Parse ingest parameter (comes as string from form)
        should_ingest = ingest.lower() in ("true", "1", "yes", "on")
        
        # Read file content
        content = await file.read()
        
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Save file to knowledge_base
        success, message, file_relative_path = kb_manager.save_file(
            file_content=content,
            relative_path=folder_path,
            filename=file.filename or "uploaded_file",
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        document_id = None
        
        # Ingest file if requested
        if should_ingest:
            logger.info(f"[UPLOAD] Starting ingestion for: {file.filename}")
            try:
                # Get absolute file path
                absolute_path = kb_manager.get_file_path(file_relative_path)
                
                if not absolute_path:
                    logger.warning(f"[UPLOAD] Could not get absolute path for: {file_relative_path}")
                    return FileUploadResponse(
                        success=True,
                        message=f"File saved but ingestion skipped: {message}",
                        file_path=file_relative_path,
                        document_id=None,
                    )
                
                logger.info(f"[UPLOAD] Extracting text from: {absolute_path}")
                
                # Extract text from file
                text_content, error = extract_file_text(absolute_path)
                
                if error:
                    logger.warning(f"[UPLOAD] Could not extract text from {file.filename}: {error}")
                    return FileUploadResponse(
                        success=True,
                        message=f"File saved but could not ingest: {error}",
                        file_path=file_relative_path,
                        document_id=None,
                    )
                
                if not text_content.strip():
                    logger.warning(f"[UPLOAD] No text content to ingest for: {file.filename}")
                    return FileUploadResponse(
                        success=True,
                        message="File saved but no text content to ingest",
                        file_path=file_relative_path,
                        document_id=None,
                    )
                
                logger.info(f"[UPLOAD] Extracted {len(text_content)} characters from {file.filename}")
                
                # Ingest the extracted text
                logger.info(f"[UPLOAD] Calling ingest_text_fast for: {file.filename}")
                document_id, ingest_message = service.ingest_text_fast(
                    text_content=text_content,
                    filename=file.filename or "uploaded_file",
                    source="knowledge_base",
                    upload_method="file_upload",
                    source_type=source_type,
                    metadata={
                        "file_path": file_relative_path,
                        "original_filename": file.filename,
                    },
                )
                
                if document_id is None:
                    logger.warning(f"[UPLOAD] Ingestion failed for {file.filename}: {ingest_message}")
                    return FileUploadResponse(
                        success=True,
                        message=f"File saved but ingestion failed: {ingest_message}",
                        file_path=file_relative_path,
                        document_id=None,
                    )
                
                logger.info(f"[UPLOAD] ✓ Successfully ingested {file.filename} with document_id={document_id}")
                
                return FileUploadResponse(
                    success=True,
                    message=f"File uploaded and ingested successfully",
                    file_path=file_relative_path,
                    document_id=document_id,
                )
            
            except Exception as e:
                logger.error(f"[UPLOAD] Error during ingestion of {file.filename}: {e}", exc_info=True)
                # File is saved, but ingestion failed
                return FileUploadResponse(
                    success=True,
                    message=f"File saved but ingestion failed: {str(e)}",
                    file_path=file_relative_path,
                    document_id=None,
                )
        else:
            logger.info(f"[UPLOAD] Ingestion disabled for: {file.filename}")
        
        return FileUploadResponse(
            success=True,
            message=message,
            file_path=file_relative_path,
            document_id=None,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {str(e)}"
        )


@router.delete("/delete", response_model=FileDeleteResponse, summary="Delete file")
async def delete_file(
    file_path: str = Query(..., description="File path relative to knowledge_base root"),
    delete_from_db: bool = Query(True, description="Whether to delete from vector database"),
    kb_manager: KnowledgeBaseManager = Depends(get_kb_manager),
    service: TextIngestionService = Depends(get_ingestion_service)
) -> FileDeleteResponse:
    """
    Delete a file from knowledge_base and optionally from vector database.
    
    Args:
        file_path: File path relative to knowledge_base root
        delete_from_db: Whether to delete embeddings from vector database
        kb_manager: Knowledge base manager instance
        service: Ingestion service instance
        
    Returns:
        FileDeleteResponse with deletion status
    """
    try:
        # Delete from vector database if requested
        if delete_from_db:
            try:
                # Find documents by file_path metadata and delete them
                logger.info(f"Attempting to delete vector embeddings for: {file_path}")
                
                db = get_db_session()
                
                try:
                    # Query all documents that have this file_path in their metadata
                    documents_to_delete = []
                    
                    for doc in db.query(Document).all():
                        if doc.document_metadata:
                            try:
                                metadata = json.loads(doc.document_metadata)
                                user_metadata = metadata.get('user_metadata', {})
                                if user_metadata.get('file_path') == file_path:
                                    documents_to_delete.append(doc.id)
                                    logger.info(f"Found document {doc.id} for deletion: {doc.filename}")
                            except Exception as e:
                                logger.debug(f"Error parsing document metadata: {e}")
                    
                    # Delete each document from vector DB and database
                    for doc_id in documents_to_delete:
                        success, msg = service.delete_document(doc_id)
                        logger.info(f"Deleted document {doc_id}: {msg}")
                    
                    if documents_to_delete:
                        logger.info(f"✓ Deleted {len(documents_to_delete)} document(s) from vector DB")
                    else:
                        logger.info(f"No documents found in vector DB for file: {file_path}")
                
                finally:
                    db.close()
            
            except Exception as e:
                logger.warning(f"Could not delete from vector DB: {e}", exc_info=True)
        
        # Delete from knowledge_base
        success, message = kb_manager.delete_file(file_path)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return FileDeleteResponse(
            success=True,
            message=message,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File deletion error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")


@router.delete("/delete-folder", response_model=FileDeleteResponse, summary="Delete folder")
async def delete_folder(
    folder_path: str = Query(..., description="Folder path relative to knowledge_base root"),
    kb_manager: KnowledgeBaseManager = Depends(get_kb_manager)
) -> FileDeleteResponse:
    """
    Delete a folder and all its contents from knowledge_base.
    
    Args:
        folder_path: Folder path relative to knowledge_base root
        kb_manager: Knowledge base manager instance
        
    Returns:
        FileDeleteResponse with deletion status
    """
    try:
        success, message = kb_manager.delete_folder(folder_path)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return FileDeleteResponse(
            success=True,
            message=message,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Folder deletion error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete folder")
