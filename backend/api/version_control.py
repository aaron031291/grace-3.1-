"""
Version Control API routes using FastAPI.
Provides endpoints for Git operations and version history.

Classes:
- `CommitInfo`
- `CommitListResponse`
- `FileChange`
- `DiffStats`
- `CommitDiffResponse`
- `TreeNode`
- `TreeStructureResponse`
- `ModuleStats`
- `ModuleStatisticsResponse`
- `RevertResponse`
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from version_control.git_service import GitService
import os

router = APIRouter(prefix="/api/version-control", tags=["Version Control"])

# Initialize Git service for the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_ROOT = os.path.dirname(PROJECT_ROOT)
git_service = GitService(PARENT_ROOT)


# ==================== Pydantic Models ====================

class CommitInfo(BaseModel):
    """Information about a commit."""
    sha: str = Field(..., description="Commit SHA hash")
    message: str = Field(..., description="Commit message")
    author: str = Field(..., description="Author name")
    author_email: str = Field(..., description="Author email")
    committer: str = Field(..., description="Committer name")
    timestamp: str = Field(..., description="Commit timestamp in ISO format")
    parent_shas: List[str] = Field(..., description="Parent commit SHAs")


class CommitListResponse(BaseModel):
    """Response for commit list."""
    commits: List[CommitInfo] = Field(..., description="List of commits")
    total: int = Field(..., description="Total number of commits")


class FileChange(BaseModel):
    """Information about a file change."""
    path: str = Field(..., description="File path")
    status: str = Field(..., description="Change status (added, modified, deleted)")
    additions: int = Field(..., description="Number of lines added")
    deletions: int = Field(..., description="Number of lines deleted")


class DiffStats(BaseModel):
    """Statistics for diff."""
    additions: int = Field(..., description="Total additions")
    deletions: int = Field(..., description="Total deletions")
    files_modified: int = Field(..., description="Number of files modified")


class CommitDiffResponse(BaseModel):
    """Response for commit diff."""
    commit_sha: str = Field(..., description="Commit SHA")
    files_changed: List[FileChange] = Field(..., description="List of file changes")
    stats: DiffStats = Field(..., description="Diff statistics")


class TreeNode(BaseModel):
    """Node in tree structure."""
    type: str = Field(..., description="Type: 'tree' or 'blob'")
    name: Optional[str] = Field(None, description="Node name")
    path: str = Field(..., description="Full path")
    mode: Optional[int] = Field(None, description="File mode")
    children: Optional[List[Dict]] = Field(None, description="Child nodes")


class TreeStructureResponse(BaseModel):
    """Response for tree structure."""
    type: str = Field(..., description="Type: 'tree'")
    path: str = Field(..., description="Path")
    children: List[Dict] = Field(..., description="Children nodes")


class ModuleStats(BaseModel):
    """Statistics for a module."""
    name: str = Field(..., description="Module name")
    is_dir: bool = Field(..., description="Is directory")


class ModuleStatisticsResponse(BaseModel):
    """Response for module statistics."""
    modules: List[ModuleStats] = Field(..., description="List of modules")
    total_commits: int = Field(..., description="Total commits in repo")
    last_commit_date: Optional[str] = Field(None, description="Last commit date")


class RevertResponse(BaseModel):
    """Response for revert operation."""
    success: bool = Field(..., description="Success status")
    message: str = Field(..., description="Status message")
    commit_sha: str = Field(..., description="Reverted commit SHA")


# ==================== Endpoints ====================

@router.get("/commits", response_model=CommitListResponse, tags=["Commits"])
async def get_commits(limit: int = Query(50, ge=1, le=100), skip: int = Query(0, ge=0)):
    """
    Get commit history.
    
    Args:
        limit: Maximum number of commits to retrieve (1-100)
        skip: Number of commits to skip
        
    Returns:
        CommitListResponse: List of commits with metadata
    """
    try:
        commits = git_service.get_commits(limit=limit, skip=skip)
        return CommitListResponse(commits=commits, total=len(commits))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving commits: {str(e)}")


@router.get("/commits/{commit_sha}", response_model=CommitInfo, tags=["Commits"])
async def get_commit_details(commit_sha: str):
    """
    Get detailed information about a specific commit.
    
    Args:
        commit_sha: SHA of the commit
        
    Returns:
        CommitInfo: Detailed commit information
    """
    try:
        commit = git_service.get_commit_details(commit_sha)
        return CommitInfo(**commit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving commit: {str(e)}")


@router.get("/commits/{commit_sha}/diff", response_model=CommitDiffResponse, tags=["Commits"])
async def get_commit_diff(commit_sha: str):
    """
    Get the diff/changes for a specific commit.
    
    Args:
        commit_sha: SHA of the commit
        
    Returns:
        CommitDiffResponse: Detailed diff information
    """
    try:
        diff = git_service.get_commit_diff(commit_sha)
        return CommitDiffResponse(**diff)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving diff: {str(e)}")


@router.get("/diff", tags=["Commits"])
async def get_diff_between_commits(from_sha: str = Query(...), to_sha: str = Query(...)):
    """
    Get the difference between two commits.
    
    Args:
        from_sha: First commit SHA
        to_sha: Second commit SHA
        
    Returns:
        CommitDiffResponse: Detailed diff information
    """
    try:
        diff = git_service.get_diff_between_commits(from_sha, to_sha)
        return CommitDiffResponse(**diff)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving diff: {str(e)}")


@router.get("/files/{file_path}/history", tags=["Files"])
async def get_file_history(file_path: str, limit: int = Query(50, ge=1, le=100)):
    """
    Get commit history for a specific file.
    
    Args:
        file_path: Path to the file
        limit: Maximum number of commits to retrieve
        
    Returns:
        CommitListResponse: Commits affecting the file
    """
    try:
        commits = git_service.get_file_history(file_path, limit=limit)
        return CommitListResponse(commits=commits, total=len(commits))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving file history: {str(e)}")


@router.get("/tree", response_model=TreeStructureResponse, tags=["Tree"])
async def get_tree_structure(commit_sha: Optional[str] = Query(None), path: str = Query("")):
    """
    Get the file tree structure at a specific commit.
    
    Args:
        commit_sha: SHA of the commit (uses HEAD if not specified)
        path: Subdirectory path
        
    Returns:
        TreeStructureResponse: Tree structure with files and directories
    """
    try:
        tree = git_service.get_tree_structure(commit_sha=commit_sha, path=path)
        return TreeStructureResponse(**tree)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tree: {str(e)}")


@router.get("/modules/statistics", response_model=ModuleStatisticsResponse, tags=["Modules"])
async def get_module_statistics():
    """
    Get statistics about modules/directories in the repository.
    
    Returns:
        ModuleStatisticsResponse: Module statistics and metadata
    """
    try:
        stats = git_service.get_module_statistics()
        return ModuleStatisticsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")


@router.post("/revert", response_model=RevertResponse, tags=["Commits"])
async def revert_to_commit(commit_sha: str = Query(...)):
    """
    Revert the working directory to a specific commit.
    
    Args:
        commit_sha: SHA of the commit to revert to
        
    Returns:
        RevertResponse: Result of revert operation
    """
    try:
        result = git_service.revert_to_commit(commit_sha)
        return RevertResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reverting to commit: {str(e)}")
