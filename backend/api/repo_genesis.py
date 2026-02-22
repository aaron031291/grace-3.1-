"""
Repository Genesis Key API.

Endpoints for scanning repo, assigning Genesis Keys, and healing.

Classes:
- `ScanRepoRequest`
- `ScanResponse`
- `DirectoryTreeResponse`
- `FindByKeyResponse`
- `HealFileRequest`
- `HealDirectoryRequest`
- `NavigateToIssueRequest`
- `TrackFileVersionRequest`
- `FileVersionResponse`
- `AutoTrackDirectoryRequest`
- `SymbioticTrackRequest`
- `RollbackRequest`
- `PipelineProcessRequest`
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session

from database.session import get_session
from genesis.repo_scanner import get_repo_scanner, scan_and_save_repo
from genesis.healing_system import get_healing_system
from genesis.file_version_tracker import get_file_version_tracker
from genesis.symbiotic_version_control import get_symbiotic_version_control
from genesis.pipeline_integration import get_data_pipeline

router = APIRouter(prefix="/repo-genesis", tags=["Repository Genesis Keys"])


# ==================== Pydantic Models ====================

class ScanRepoRequest(BaseModel):
    """Request to scan repository."""
    repo_path: Optional[str] = Field(None, description="Path to repository (defaults to grace_3 root)")
    integrate_version_tracking: bool = Field(True, description="Integrate with file version tracking")
    user_id: Optional[str] = Field(None, description="User ID for version tracking")


class ScanResponse(BaseModel):
    """Response from repository scan."""
    scan_timestamp: str
    repo_path: str
    root_genesis_key: str
    total_directories: int
    total_files: int
    total_size_bytes: int
    immutable_memory_path: str


class DirectoryTreeResponse(BaseModel):
    """Response with directory tree."""
    genesis_key: str
    name: str
    path: str
    subdirectories: List[Dict]
    files: List[Dict]


class FindByKeyResponse(BaseModel):
    """Response for finding by Genesis Key."""
    type: str  # "directory" or "file"
    info: Dict


class HealFileRequest(BaseModel):
    """Request to heal a file."""
    file_genesis_key: str = Field(..., description="Genesis Key of file to heal")
    user_id: Optional[str] = Field(None, description="User ID")
    auto_apply: bool = Field(False, description="Whether to auto-apply fixes")


class HealDirectoryRequest(BaseModel):
    """Request to heal a directory."""
    dir_genesis_key: str = Field(..., description="Genesis Key of directory to heal")
    user_id: Optional[str] = Field(None, description="User ID")
    auto_apply: bool = Field(False, description="Whether to auto-apply fixes")
    recursive: bool = Field(True, description="Whether to heal subdirectories")


class NavigateToIssueRequest(BaseModel):
    """Request to navigate to an issue."""
    file_genesis_key: str = Field(..., description="Genesis Key of file")
    issue_line: int = Field(..., description="Line number of issue")


class TrackFileVersionRequest(BaseModel):
    """Request to track a file version."""
    file_genesis_key: str = Field(..., description="FILE-prefix Genesis Key")
    file_path: str = Field(..., description="Path to file")
    user_id: Optional[str] = Field(None, description="User ID")
    version_note: Optional[str] = Field(None, description="Note about this version")
    auto_detect_change: bool = Field(True, description="Auto-detect if file changed")


class FileVersionResponse(BaseModel):
    """Response for file version tracking."""
    file_genesis_key: str
    version_key_id: str
    version_number: int
    changed: bool
    file_hash: str
    timestamp: str


class AutoTrackDirectoryRequest(BaseModel):
    """Request to auto-track directory files."""
    directory_path: str = Field(..., description="Directory to track")
    user_id: Optional[str] = Field(None, description="User ID")
    recursive: bool = Field(True, description="Recurse into subdirectories")
    file_pattern: Optional[str] = Field(None, description="File pattern (e.g., *.py)")


class SymbioticTrackRequest(BaseModel):
    """Request to track file change symbiotically."""
    file_path: str = Field(..., description="Path to file")
    user_id: Optional[str] = Field(None, description="User ID")
    change_description: Optional[str] = Field(None, description="Description of change")
    operation_type: str = Field("modify", description="Operation type (create, modify, delete)")


class RollbackRequest(BaseModel):
    """Request to rollback to a version."""
    file_genesis_key: str = Field(..., description="FILE-prefix Genesis Key")
    version_number: int = Field(..., description="Version to rollback to")
    user_id: Optional[str] = Field(None, description="User ID")


class PipelineProcessRequest(BaseModel):
    """Request to process input through complete pipeline."""
    input_data: Any = Field(..., description="Input data to process")
    input_type: str = Field(..., description="Type of input (user_input, file_change, api_request, etc.)")
    user_id: Optional[str] = Field(None, description="User ID (Genesis ID)")
    file_path: Optional[str] = Field(None, description="File path if applicable")
    description: Optional[str] = Field(None, description="Description of input")


# ==================== Endpoints ====================

@router.post("/scan", response_model=ScanResponse)
async def scan_repository(
    request: ScanRepoRequest = Body(default=ScanRepoRequest()),
    session: Session = Depends(get_session)
):
    """
    Scan entire repository and assign Genesis Keys.

    Assigns Genesis Keys to:
    - All directories
    - All subdirectories
    - All files

    Stores in immutable memory (.genesis_immutable_memory.json)
    Optionally integrates with file version tracking.
    """
    try:
        repo_path = request.repo_path
        if not repo_path:
            # Default to grace_3 root
            import os
            repo_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Scan repository with optional version tracking
        immutable_memory = scan_and_save_repo(
            repo_path=repo_path,
            integrate_version_tracking=request.integrate_version_tracking,
            user_id=request.user_id
        )

        return ScanResponse(
            scan_timestamp=immutable_memory["scan_timestamp"],
            repo_path=immutable_memory["repo_path"],
            root_genesis_key=immutable_memory["root_genesis_key"],
            total_directories=immutable_memory["statistics"]["total_directories"],
            total_files=immutable_memory["statistics"]["total_files"],
            total_size_bytes=immutable_memory["statistics"]["total_size_bytes"],
            immutable_memory_path=os.path.join(repo_path, ".genesis_immutable_memory.json")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tree/{path:path}", response_model=DirectoryTreeResponse)
async def get_directory_tree(
    path: str = "root",
    session: Session = Depends(get_session)
):
    """
    Get directory tree with Genesis Keys.

    Returns hierarchical structure showing all Genesis Keys.
    """
    try:
        scanner = get_repo_scanner()

        # Ensure scanner has data
        if not scanner.immutable_memory:
            raise HTTPException(
                status_code=404,
                detail="No scan data found. Run /repo-genesis/scan first"
            )

        tree = scanner.get_directory_tree(path)

        if not tree:
            raise HTTPException(status_code=404, detail="Directory tree not found")

        return DirectoryTreeResponse(**tree)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/find/{genesis_key}", response_model=FindByKeyResponse)
async def find_by_genesis_key(
    genesis_key: str,
    session: Session = Depends(get_session)
):
    """
    Find directory or file by Genesis Key.

    Searches immutable memory for Genesis Key.
    """
    try:
        scanner = get_repo_scanner()

        if not scanner.immutable_memory:
            raise HTTPException(
                status_code=404,
                detail="No scan data found. Run /repo-genesis/scan first"
            )

        result = scanner.find_by_genesis_key(genesis_key)

        if not result:
            raise HTTPException(status_code=404, detail="Genesis Key not found")

        return FindByKeyResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_scan_statistics(session: Session = Depends(get_session)):
    """Get repository scan statistics."""
    try:
        scanner = get_repo_scanner()

        if not scanner.immutable_memory:
            raise HTTPException(
                status_code=404,
                detail="No scan data found. Run /repo-genesis/scan first"
            )

        return scanner.get_statistics()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/issues")
async def scan_for_issues(
    file_genesis_key: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    Scan for issues using Genesis Keys.

    If file_genesis_key provided, scans that file.
    Otherwise scans all Python/JavaScript files.
    """
    try:
        healing = get_healing_system()

        issues = healing.scan_for_issues(file_genesis_key)

        return {
            "total_issues": len(issues),
            "issues": issues
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/heal/file")
async def heal_file(
    request: HealFileRequest,
    session: Session = Depends(get_session)
):
    """
    Heal a file using its Genesis Key.

    Detects issues and optionally applies fixes.
    """
    try:
        healing = get_healing_system()

        result = healing.heal_file(
            file_genesis_key=request.file_genesis_key,
            user_id=request.user_id,
            auto_apply=request.auto_apply
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/heal/directory")
async def heal_directory(
    request: HealDirectoryRequest,
    session: Session = Depends(get_session)
):
    """
    Heal all files in a directory using Genesis Key.

    Recursively heals subdirectories if requested.
    """
    try:
        healing = get_healing_system()

        result = healing.heal_directory(
            dir_genesis_key=request.dir_genesis_key,
            user_id=request.user_id,
            auto_apply=request.auto_apply,
            recursive=request.recursive
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/navigate")
async def navigate_to_issue(
    request: NavigateToIssueRequest,
    session: Session = Depends(get_session)
):
    """
    Navigate to an issue using Genesis Key.

    Returns file path and context for debugging.
    """
    try:
        healing = get_healing_system()

        result = healing.navigate_to_issue(
            file_genesis_key=request.file_genesis_key,
            issue_line=request.issue_line
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/healing/summary")
async def get_healing_summary(session: Session = Depends(get_session)):
    """Get summary of healing operations."""
    try:
        healing = get_healing_system()

        return healing.get_healing_summary()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/healing/export")
async def export_healing_report(session: Session = Depends(get_session)):
    """Export healing report to JSON."""
    try:
        healing = get_healing_system()

        report_path = healing.export_healing_report()

        return {
            "message": "Healing report exported",
            "report_path": report_path
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/layer1")
async def get_layer1_structure(session: Session = Depends(get_session)):
    """
    Get layer_1 folder structure with Genesis Keys.

    Displays complete layer_1 hierarchy for easy navigation.
    """
    try:
        scanner = get_repo_scanner()

        if not scanner.immutable_memory:
            raise HTTPException(
                status_code=404,
                detail="No scan data found. Run /repo-genesis/scan first"
            )

        # Find layer_1 directory
        layer1_tree = None
        for path, info in scanner.immutable_memory["directories"].items():
            if "layer_1" in path or "layer1" in path:
                tree = scanner.get_directory_tree(path)
                if tree:
                    layer1_tree = tree
                    break

        if not layer1_tree:
            # Try knowledge_base/layer_1
            tree = scanner.get_directory_tree("knowledge_base/layer_1")
            if tree:
                layer1_tree = tree

        if not layer1_tree:
            return {
                "message": "layer_1 folder not found",
                "hint": "Scan may need to be run or layer_1 folder doesn't exist"
            }

        return {
            "layer1_structure": layer1_tree,
            "total_subdirectories": len(layer1_tree.get("subdirectories", [])),
            "total_files": len(layer1_tree.get("files", []))
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== File Version Tracking Endpoints ====================


@router.post("/file/track-version", response_model=FileVersionResponse)
async def track_file_version(
    request: TrackFileVersionRequest,
    session: Session = Depends(get_session)
):
    """
    Track a new version of a file.

    Creates a version Genesis Key linked to the file's Genesis Key.
    Auto-detects if file content has changed since last version.
    """
    try:
        tracker = get_file_version_tracker()

        result = tracker.track_file_version(
            file_genesis_key=request.file_genesis_key,
            file_path=request.file_path,
            user_id=request.user_id,
            version_note=request.version_note,
            auto_detect_change=request.auto_detect_change
        )

        return FileVersionResponse(**result)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{file_genesis_key}/versions")
async def get_file_versions(
    file_genesis_key: str,
    session: Session = Depends(get_session)
):
    """
    Get all versions for a file.

    Returns complete version history with metadata.
    """
    try:
        tracker = get_file_version_tracker()

        versions = tracker.get_file_versions(file_genesis_key)

        if not versions:
            raise HTTPException(
                status_code=404,
                detail=f"No versions found for file: {file_genesis_key}"
            )

        return versions

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{file_genesis_key}/version/{version_number}")
async def get_version_details(
    file_genesis_key: str,
    version_number: int,
    session: Session = Depends(get_session)
):
    """
    Get details for a specific file version.
    """
    try:
        tracker = get_file_version_tracker()

        version = tracker.get_version_details(file_genesis_key, version_number)

        if not version:
            raise HTTPException(
                status_code=404,
                detail=f"Version {version_number} not found for file: {file_genesis_key}"
            )

        return version

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{file_genesis_key}/latest")
async def get_latest_version(
    file_genesis_key: str,
    session: Session = Depends(get_session)
):
    """
    Get the latest version for a file.
    """
    try:
        tracker = get_file_version_tracker()

        latest = tracker.get_latest_version(file_genesis_key)

        if not latest:
            raise HTTPException(
                status_code=404,
                detail=f"No versions found for file: {file_genesis_key}"
            )

        return latest

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{file_genesis_key}/diff")
async def get_version_diff(
    file_genesis_key: str,
    version1: int,
    version2: int,
    session: Session = Depends(get_session)
):
    """
    Get differences between two versions of a file.
    """
    try:
        tracker = get_file_version_tracker()

        diff = tracker.get_version_diff(file_genesis_key, version1, version2)

        if not diff:
            raise HTTPException(
                status_code=404,
                detail=f"Could not compare versions {version1} and {version2}"
            )

        return diff

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/directory/auto-track")
async def auto_track_directory(
    request: AutoTrackDirectoryRequest,
    session: Session = Depends(get_session)
):
    """
    Automatically track all files in a directory.

    Creates versions for all files, optionally recursing into subdirectories.
    Useful for bulk version tracking operations.
    """
    try:
        tracker = get_file_version_tracker()

        result = tracker.auto_track_directory(
            directory_path=request.directory_path,
            user_id=request.user_id,
            recursive=request.recursive,
            file_pattern=request.file_pattern
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/statistics")
async def get_file_tracking_statistics(session: Session = Depends(get_session)):
    """
    Get statistics about file version tracking.

    Returns:
    - Total files tracked
    - Total versions
    - Average versions per file
    """
    try:
        tracker = get_file_version_tracker()

        stats = tracker.get_file_statistics()

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/list-tracked")
async def list_all_tracked_files(session: Session = Depends(get_session)):
    """
    List all files being version tracked.

    Returns complete list with version counts and metadata.
    """
    try:
        tracker = get_file_version_tracker()

        tracked_files = tracker.list_all_tracked_files()

        return {
            "total_files": len(tracked_files),
            "files": tracked_files
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Symbiotic Version Control Endpoints ====================


@router.post("/symbiotic/track-change")
async def symbiotic_track_change(
    request: SymbioticTrackRequest,
    session: Session = Depends(get_session)
):
    """
    Track file change SYMBIOTICALLY.

    This creates BOTH:
    - Genesis Key for the operation
    - Version entry for the file

    They are linked bidirectionally and work as ONE system.
    """
    try:
        symbiotic = get_symbiotic_version_control(session=session)

        result = symbiotic.track_file_change(
            file_path=request.file_path,
            user_id=request.user_id,
            change_description=request.change_description,
            operation_type=request.operation_type
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbiotic/history/{file_genesis_key}")
async def get_symbiotic_history(
    file_genesis_key: str,
    session: Session = Depends(get_session)
):
    """
    Get COMPLETE unified history.

    Returns both Genesis Keys AND versions in one timeline.
    Shows how they're interconnected symbiotically.
    """
    try:
        symbiotic = get_symbiotic_version_control(session=session)

        history = symbiotic.get_complete_history(file_genesis_key)

        return history

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/symbiotic/rollback")
async def symbiotic_rollback(
    request: RollbackRequest,
    session: Session = Depends(get_session)
):
    """
    Rollback to a version - SYMBIOTIC operation.

    Creates:
    1. Genesis Key for the rollback
    2. New version entry (rollback IS a new version)
    3. Links them symbiotically
    """
    try:
        symbiotic = get_symbiotic_version_control(session=session)

        result = symbiotic.rollback_to_version(
            file_genesis_key=request.file_genesis_key,
            version_number=request.version_number,
            user_id=request.user_id
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/symbiotic/watch")
async def symbiotic_watch_file(
    file_path: str = Body(..., embed=True),
    user_id: Optional[str] = Body(None, embed=True),
    session: Session = Depends(get_session)
):
    """
    Start watching a file for changes.

    Any change will automatically create:
    - Genesis Key
    - Version entry
    - Linked symbiotically
    """
    try:
        symbiotic = get_symbiotic_version_control(session=session)

        result = symbiotic.watch_file(
            file_path=file_path,
            user_id=user_id
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbiotic/stats")
async def get_symbiotic_stats(session: Session = Depends(get_session)):
    """
    Get symbiotic integration statistics.

    Shows how Genesis Keys and version control are working together.
    """
    try:
        symbiotic = get_symbiotic_version_control(session=session)

        stats = symbiotic.get_symbiotic_stats()

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Complete Pipeline Endpoints ====================


@router.post("/pipeline/process")
async def process_through_pipeline(
    request: PipelineProcessRequest,
    session: Session = Depends(get_session)
):
    """
    Process input through COMPLETE pipeline.

    Pipeline Flow:
    1. Layer 1 Input → User/system input received
    2. Genesis Key → Universal ID assigned & tracking
    3. Version Control → Changes tracked symbiotically
    4. Librarian → Organized & categorized
    5. Immutable Memory → Permanent snapshot stored
    6. RAG → Indexed for retrieval
    7. World Model → AI can understand & respond
    """
    try:
        pipeline = get_data_pipeline(session=session)

        result = pipeline.process_input(
            input_data=request.input_data,
            input_type=request.input_type,
            user_id=request.user_id,
            file_path=request.file_path,
            description=request.description
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline/stats")
async def get_pipeline_stats(session: Session = Depends(get_session)):
    """
    Get complete pipeline statistics.

    Shows how many inputs have flowed through each stage.
    """
    try:
        pipeline = get_data_pipeline(session=session)

        stats = pipeline.get_pipeline_stats()

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline/verify")
async def verify_pipeline(session: Session = Depends(get_session)):
    """
    Verify that complete pipeline is operational.

    Checks all stages:
    - Layer 1 Input
    - Genesis Key
    - Version Control
    - Librarian
    - Immutable Memory
    - RAG
    - World Model
    """
    try:
        pipeline = get_data_pipeline(session=session)

        verification = pipeline.verify_pipeline()

        return verification

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
