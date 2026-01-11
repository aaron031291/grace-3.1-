"""
Directory Hierarchy API with Genesis Keys.

Provides endpoints for managing directory hierarchies where:
- Every directory has a unique Genesis Key (DIR-prefix)
- Subdirectories inherit from parent
- Files are version-controlled within directories
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session

from database.session import get_session
from genesis.directory_hierarchy import get_directory_hierarchy

router = APIRouter(prefix="/directory-hierarchy", tags=["Directory Hierarchy"])


# ==================== Pydantic Models ====================

class CreateDirectoryRequest(BaseModel):
    """Request to create a directory with Genesis Key."""
    directory_path: str = Field(..., description="Path to directory (relative to knowledge_base)")
    parent_genesis_key: Optional[str] = Field(None, description="Parent directory Genesis Key")
    user_id: Optional[str] = Field(None, description="User creating directory")
    description: Optional[str] = Field(None, description="Directory description")


class DirectoryInfoResponse(BaseModel):
    """Response with directory Genesis Key information."""
    genesis_key: str
    path: str
    name: str
    parent_genesis_key: Optional[str]
    created_at: str
    is_root: bool
    subdirectories: List[str]
    files: List[Dict]
    version_count: int


class CreateHierarchyRequest(BaseModel):
    """Request to create directory hierarchy."""
    root_path: str = Field(default="", description="Root directory path")
    user_id: Optional[str] = Field(None, description="User ID")
    scan_existing: bool = Field(default=True, description="Scan existing directories")


class DirectoryTreeResponse(BaseModel):
    """Response with directory tree structure."""
    genesis_key: str
    name: str
    path: str
    is_root: bool
    created_at: str
    parent_genesis_key: Optional[str]
    subdirectories: List[Dict]
    files: List[Dict]
    file_count: int
    subdirectory_count: int


class AddFileVersionRequest(BaseModel):
    """Request to add file version."""
    directory_path: str = Field(..., description="Directory containing file")
    file_name: str = Field(..., description="File name")
    user_id: Optional[str] = Field(None, description="User ID")
    version_note: Optional[str] = Field(None, description="Version note")
    file_content: Optional[str] = Field(None, description="File content snapshot")


class FileVersionResponse(BaseModel):
    """Response for file version."""
    version_key: str
    version_number: int
    directory_genesis_key: str
    file_path: str
    timestamp: str


class HierarchyStatsResponse(BaseModel):
    """Response with hierarchy statistics."""
    total_directories: int
    total_files: int
    total_versions: int
    root_genesis_key: Optional[str]
    created_at: Optional[str]


# ==================== Endpoints ====================

@router.post("/directories", response_model=DirectoryInfoResponse)
async def create_directory_with_genesis_key(
    request: CreateDirectoryRequest,
    session: Session = Depends(get_session)
):
    """
    Create a directory with a unique Genesis Key.

    Every directory gets:
    - Unique Genesis Key (DIR-prefix)
    - Link to parent Genesis Key
    - README with Genesis Key info
    - Version control for files
    """
    try:
        hierarchy = get_directory_hierarchy()

        dir_info = hierarchy.create_directory_genesis_key(
            directory_path=request.directory_path,
            parent_genesis_key=request.parent_genesis_key,
            user_id=request.user_id,
            description=request.description
        )

        return DirectoryInfoResponse(**dir_info)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hierarchies", response_model=DirectoryTreeResponse)
async def create_directory_hierarchy(
    request: CreateHierarchyRequest,
    session: Session = Depends(get_session)
):
    """
    Create complete directory hierarchy with Genesis Keys.

    Scans directory tree and assigns Genesis Keys to:
    - Root directory
    - All subdirectories
    - Tracks all files

    Returns complete tree structure with Genesis Keys.
    """
    try:
        hierarchy = get_directory_hierarchy()

        tree = hierarchy.create_hierarchy(
            root_path=request.root_path,
            user_id=request.user_id,
            scan_existing=request.scan_existing
        )

        return DirectoryTreeResponse(**tree)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/directories/{directory_path:path}", response_model=DirectoryInfoResponse)
async def get_directory_info(
    directory_path: str,
    session: Session = Depends(get_session)
):
    """Get information for a specific directory."""
    try:
        hierarchy = get_directory_hierarchy()

        dir_info = hierarchy.get_directory_info(directory_path)

        if not dir_info:
            raise HTTPException(status_code=404, detail="Directory not found")

        return DirectoryInfoResponse(**dir_info)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/directories/{directory_path:path}/genesis-key")
async def get_directory_genesis_key(
    directory_path: str,
    session: Session = Depends(get_session)
):
    """Get Genesis Key for a directory."""
    try:
        hierarchy = get_directory_hierarchy()

        genesis_key = hierarchy.get_directory_genesis_key(directory_path)

        if not genesis_key:
            raise HTTPException(status_code=404, detail="Directory not found")

        return {"directory_path": directory_path, "genesis_key": genesis_key}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trees/{root_path:path}", response_model=DirectoryTreeResponse)
async def get_directory_tree(
    root_path: str = "",
    session: Session = Depends(get_session)
):
    """
    Get directory tree with all Genesis Keys.

    Returns hierarchical structure showing:
    - Each directory's Genesis Key
    - Parent-child relationships
    - Files in each directory
    - Subdirectory counts
    """
    try:
        hierarchy = get_directory_hierarchy()

        tree = hierarchy.get_directory_tree(root_path)

        if not tree:
            raise HTTPException(status_code=404, detail="Directory tree not found")

        return DirectoryTreeResponse(**tree)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/versions", response_model=FileVersionResponse)
async def add_file_version(
    request: AddFileVersionRequest,
    session: Session = Depends(get_session)
):
    """
    Add a file version under a directory's Genesis Key.

    Files are version-controlled within their directory:
    - Linked to directory Genesis Key
    - Version number tracked
    - Complete history maintained
    """
    try:
        hierarchy = get_directory_hierarchy()

        version_info = hierarchy.add_file_version(
            directory_path=request.directory_path,
            file_name=request.file_name,
            user_id=request.user_id,
            version_note=request.version_note,
            file_content=request.file_content
        )

        return FileVersionResponse(**version_info)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/directories", response_model=Dict[str, DirectoryInfoResponse])
async def list_all_directories(session: Session = Depends(get_session)):
    """List all directories with their Genesis Keys."""
    try:
        hierarchy = get_directory_hierarchy()

        all_dirs = hierarchy.get_all_directory_keys()

        return {
            path: DirectoryInfoResponse(**info)
            for path, info in all_dirs.items()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=HierarchyStatsResponse)
async def get_hierarchy_statistics(session: Session = Depends(get_session)):
    """Get statistics about the directory hierarchy."""
    try:
        hierarchy = get_directory_hierarchy()

        stats = hierarchy.get_hierarchy_statistics()

        return HierarchyStatsResponse(**stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/initialize")
async def initialize_knowledge_base_hierarchy(
    user_id: Optional[str] = Body(None, embed=True),
    session: Session = Depends(get_session)
):
    """
    Initialize Genesis Key hierarchy for knowledge_base.

    Creates Genesis Keys for:
    - knowledge_base/ (root)
    - layer_1/ subdirectory
    - genesis_key/ subdirectory
    - All other existing directories
    """
    try:
        hierarchy = get_directory_hierarchy()

        # Create root hierarchy
        root_tree = hierarchy.create_hierarchy(
            root_path="",
            user_id=user_id or "system",
            scan_existing=True
        )

        # Get statistics
        stats = hierarchy.get_hierarchy_statistics()

        return {
            "message": "Knowledge base hierarchy initialized",
            "root_genesis_key": stats["root_genesis_key"],
            "total_directories": stats["total_directories"],
            "total_files": stats["total_files"],
            "tree": root_tree
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
