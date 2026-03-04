"""
Workspace API — Grace's internal platform management.
=====================================================
Replaces GitHub: version control, CI/CD, project management.
All self-contained, no third-party dependencies.

Endpoints:
  Workspaces:  create, list, get
  VCS:         snapshot, history, diff, rollback, branches
  Pipelines:   run, history, load YAML
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


# ─── Request Models ───

class CreateWorkspaceRequest(BaseModel):
    workspace_id: str = Field(..., description="Unique ID (e.g. 'tommy-ai')")
    name: str = Field(..., description="Display name")
    root_path: str = Field(..., description="Filesystem root for this workspace")
    owner_id: Optional[str] = None
    description: str = ""
    config: Optional[Dict[str, Any]] = None


class SnapshotRequest(BaseModel):
    file_path: str
    content: str
    message: str = ""
    author: str = "grace"
    branch_name: Optional[str] = None


class SnapshotDirectoryRequest(BaseModel):
    directory_path: str = ""
    message: str = ""
    author: str = "grace"
    extensions: Optional[List[str]] = None


class DiffRequest(BaseModel):
    file_path: str
    version_a: int
    version_b: int


class RollbackRequest(BaseModel):
    file_path: str
    target_version: int
    author: str = "grace"


class CreateBranchRequest(BaseModel):
    name: str
    from_branch: str = "main"


class RunPipelineRequest(BaseModel):
    pipeline_name: str
    yaml_path: Optional[str] = None
    stages: Optional[List[Dict[str, Any]]] = None
    trigger: str = "manual"
    triggered_by: str = "grace"
    working_dir: Optional[str] = None
    environment: Optional[Dict[str, str]] = None


# ─── Workspace CRUD ───

@router.post("")
def create_workspace(req: CreateWorkspaceRequest):
    from genesis.internal_vcs import create_workspace
    result = create_workspace(
        workspace_id=req.workspace_id,
        name=req.name,
        root_path=req.root_path,
        owner_id=req.owner_id,
        description=req.description,
        config=req.config,
    )
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.get("")
def get_workspaces():
    from genesis.internal_vcs import list_workspaces
    return {"workspaces": list_workspaces()}


# ─── Version Control ───

@router.post("/{workspace_id}/vcs/snapshot")
def vcs_snapshot(workspace_id: str, req: SnapshotRequest):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    return vcs.snapshot(
        file_path=req.file_path,
        content=req.content,
        message=req.message,
        author=req.author,
        branch_name=req.branch_name,
    )


@router.post("/{workspace_id}/vcs/snapshot-directory")
def vcs_snapshot_directory(workspace_id: str, req: SnapshotDirectoryRequest):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    return vcs.snapshot_directory(
        directory_path=req.directory_path,
        message=req.message,
        author=req.author,
        extensions=req.extensions,
    )


@router.get("/{workspace_id}/vcs/history/{file_path:path}")
def vcs_history(workspace_id: str, file_path: str, branch: Optional[str] = None, limit: int = 50):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    return {"history": vcs.history(file_path, branch_name=branch, limit=limit)}


@router.post("/{workspace_id}/vcs/diff")
def vcs_diff(workspace_id: str, req: DiffRequest):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    return vcs.diff(req.file_path, req.version_a, req.version_b)


@router.post("/{workspace_id}/vcs/rollback")
def vcs_rollback(workspace_id: str, req: RollbackRequest):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    return vcs.rollback(req.file_path, req.target_version, author=req.author)


@router.get("/{workspace_id}/vcs/content/{file_path:path}")
def vcs_get_content(workspace_id: str, file_path: str, version: Optional[int] = None):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    return vcs.get_content(file_path, version=version)


@router.get("/{workspace_id}/vcs/files")
def vcs_list_files(workspace_id: str, branch: Optional[str] = None):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    return {"files": vcs.list_tracked_files(branch_name=branch)}


# ─── Branches ───

@router.post("/{workspace_id}/vcs/branches")
def vcs_create_branch(workspace_id: str, req: CreateBranchRequest):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    result = vcs.create_branch(req.name, from_branch=req.from_branch)
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.get("/{workspace_id}/vcs/branches")
def vcs_list_branches(workspace_id: str):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    return {"branches": vcs.list_branches()}


# ─── Pipelines ───

@router.post("/{workspace_id}/pipelines/run")
async def pipeline_run(workspace_id: str, req: RunPipelineRequest):
    from genesis.internal_pipeline import get_pipeline_runner, PipelineConfig
    runner = get_pipeline_runner(workspace_id)

    if req.yaml_path:
        config = runner.load_pipeline_yaml(req.yaml_path)
    elif req.stages:
        config = PipelineConfig(
            name=req.pipeline_name,
            stages=req.stages,
            working_dir=req.working_dir,
            environment=req.environment or {},
        )
    else:
        raise HTTPException(status_code=400, detail="Provide yaml_path or stages")

    result = await runner.run_pipeline(
        config=config,
        trigger=req.trigger,
        triggered_by=req.triggered_by,
    )
    return result


@router.get("/{workspace_id}/pipelines/history")
def pipeline_history(workspace_id: str, limit: int = 20):
    from genesis.internal_pipeline import get_pipeline_runner
    runner = get_pipeline_runner(workspace_id)
    return {"runs": runner.get_run_history(limit=limit)}
