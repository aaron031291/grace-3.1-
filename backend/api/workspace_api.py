"""
Workspace API — Grace's internal platform management.
=====================================================
Replaces GitHub: version control, CI/CD, project management.
All self-contained, no third-party dependencies.
Fully async from macro to micro level.

Endpoints:
  Workspaces:  create, list, get
  VCS:         snapshot, history, diff, rollback, branches
  Pipelines:   run, history, load YAML
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])
logger = logging.getLogger(__name__)


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


# ─── Genesis tracking helper ───

async def _track(key_type: str, what: str, workspace_id: str, **extra):
    try:
        from api._genesis_tracker import track
        track(key_type=key_type, what=what,
              who=f"workspace.{workspace_id}",
              tags=["workspace", workspace_id, key_type], **extra)
    except Exception:
        pass


# ─── Workspace CRUD (async) ───

@router.post("")
async def api_create_workspace(req: CreateWorkspaceRequest):
    from genesis.internal_vcs import create_workspace
    result = await create_workspace(
        workspace_id=req.workspace_id, name=req.name,
        root_path=req.root_path, owner_id=req.owner_id,
        description=req.description, config=req.config,
    )
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    await _track("system_event", f"Workspace created: {req.workspace_id}", req.workspace_id)
    return result


@router.get("")
async def api_list_workspaces():
    from genesis.internal_vcs import list_workspaces
    return {"workspaces": await list_workspaces()}


# ─── Version Control (async) ───

@router.post("/{workspace_id}/vcs/snapshot")
async def api_vcs_snapshot(workspace_id: str, req: SnapshotRequest):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    result = await vcs.snapshot(
        file_path=req.file_path, content=req.content,
        message=req.message, author=req.author, branch_name=req.branch_name,
    )
    if result.get("status") == "created":
        await _track("code_change", f"VCS snapshot: {req.file_path} v{result.get('version')}",
                     workspace_id, file_path=req.file_path)
        await _publish_vcs_event(workspace_id, "file_versioned", {
            "file_path": req.file_path, "version": result.get("version"),
            "author": req.author,
        })
    return result


@router.post("/{workspace_id}/vcs/snapshot-directory")
async def api_vcs_snapshot_directory(workspace_id: str, req: SnapshotDirectoryRequest):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    result = await vcs.snapshot_directory(
        directory_path=req.directory_path, message=req.message,
        author=req.author, extensions=req.extensions,
    )
    await _track("system_event",
                 f"Directory snapshot: {req.directory_path} ({result.get('created', 0)} new)",
                 workspace_id)
    return result


@router.get("/{workspace_id}/vcs/history/{file_path:path}")
async def api_vcs_history(workspace_id: str, file_path: str,
                          branch: Optional[str] = None, limit: int = 50):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    return {"history": await vcs.history(file_path, branch_name=branch, limit=limit)}


@router.post("/{workspace_id}/vcs/diff")
async def api_vcs_diff(workspace_id: str, req: DiffRequest):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    return await vcs.diff(req.file_path, req.version_a, req.version_b)


@router.post("/{workspace_id}/vcs/rollback")
async def api_vcs_rollback(workspace_id: str, req: RollbackRequest):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    result = await vcs.rollback(req.file_path, req.target_version, author=req.author)
    await _track("code_change",
                 f"VCS rollback: {req.file_path} → v{req.target_version}",
                 workspace_id, file_path=req.file_path)
    return result


@router.get("/{workspace_id}/vcs/content/{file_path:path}")
async def api_vcs_get_content(workspace_id: str, file_path: str,
                              version: Optional[int] = None):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    return await vcs.get_content(file_path, version=version)


@router.get("/{workspace_id}/vcs/files")
async def api_vcs_list_files(workspace_id: str, branch: Optional[str] = None):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    return {"files": await vcs.list_tracked_files(branch_name=branch)}


# ─── Branches (async) ───

@router.post("/{workspace_id}/vcs/branches")
async def api_vcs_create_branch(workspace_id: str, req: CreateBranchRequest):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    result = await vcs.create_branch(req.name, from_branch=req.from_branch)
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    await _track("system_event", f"Branch created: {req.name}", workspace_id)
    return result


@router.get("/{workspace_id}/vcs/branches")
async def api_vcs_list_branches(workspace_id: str):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    return {"branches": await vcs.list_branches()}


# ─── Pipelines (async) ───

@router.post("/{workspace_id}/pipelines/run")
async def api_pipeline_run(workspace_id: str, req: RunPipelineRequest):
    from genesis.internal_pipeline import get_pipeline_runner, PipelineConfig
    runner = get_pipeline_runner(workspace_id)

    if req.yaml_path:
        config = runner.load_pipeline_yaml(req.yaml_path)
    elif req.stages:
        config = PipelineConfig(
            name=req.pipeline_name, stages=req.stages,
            working_dir=req.working_dir, environment=req.environment or {},
        )
    else:
        raise HTTPException(status_code=400, detail="Provide yaml_path or stages")

    result = await runner.run_pipeline(
        config=config, trigger=req.trigger, triggered_by=req.triggered_by,
    )
    await _track("system_event",
                 f"Pipeline {req.pipeline_name}: {result.get('status')}",
                 workspace_id)
    await _publish_vcs_event(workspace_id, "pipeline_completed", {
        "pipeline": req.pipeline_name, "status": result.get("status"),
        "run_id": result.get("run_id"),
    })
    return result


@router.get("/{workspace_id}/pipelines/history")
async def api_pipeline_history(workspace_id: str, limit: int = 20):
    from genesis.internal_pipeline import get_pipeline_runner
    runner = get_pipeline_runner(workspace_id)
    return {"runs": runner.get_run_history(limit=limit)}


# ─── Layer 1 message bus bridge (async) ───

async def _publish_vcs_event(workspace_id: str, event_type: str, payload: Dict[str, Any]):
    """Publish workspace events to Layer 1 message bus for cross-system integration."""
    try:
        from layer1.message_bus import get_message_bus, ComponentType
        bus = get_message_bus()
        if bus:
            await bus.publish(
                topic=f"workspace.{event_type}",
                payload={"workspace_id": workspace_id, **payload},
                from_component=ComponentType.VERSION_CONTROL,
            )
    except Exception:
        pass
