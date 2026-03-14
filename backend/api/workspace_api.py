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


class MergeRequest(BaseModel):
    source_branch: str
    target_branch: str = "main"
    message: str = ""
    author: str = "grace"


class CreateTaskRequest(BaseModel):
    title: str
    description: str = ""
    task_type: str = "task"
    priority: str = "medium"
    assignee: str = "grace"
    labels: Optional[List[str]] = None
    related_files: Optional[List[str]] = None


class UpdateTaskRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    labels: Optional[List[str]] = None
    description: Optional[str] = None


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


# ─── Merge (async) ───

@router.post("/{workspace_id}/vcs/merge")
async def api_vcs_merge(workspace_id: str, req: MergeRequest):
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(workspace_id)
    result = await vcs.merge(
        source_branch=req.source_branch, target_branch=req.target_branch,
        author=req.author, message=req.message,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await _track("code_change",
                 f"Merge {req.source_branch} → {req.target_branch}: "
                 f"{result.get('total_merged', 0)} files, {result.get('total_conflicts', 0)} conflicts",
                 workspace_id)
    await _publish_vcs_event(workspace_id, "branch_merged", {
        "source_branch": req.source_branch, "target_branch": req.target_branch,
        "merge_id": result.get("merge_id"), "status": result.get("status"),
    })
    return result


@router.get("/{workspace_id}/vcs/merges")
async def api_vcs_list_merges(workspace_id: str, status: Optional[str] = None,
                               limit: int = 20):
    from database.session import session_scope
    from models.workspace_models import MergeRequest as MergeRequestModel, Workspace
    try:
        with session_scope() as session:
            ws = session.query(Workspace).filter_by(workspace_id=workspace_id).first()
            if not ws:
                raise HTTPException(status_code=404, detail="Workspace not found")
            q = session.query(MergeRequestModel).filter_by(workspace_id=ws.id)
            if status:
                q = q.filter_by(status=status)
            merges = q.order_by(MergeRequestModel.created_at.desc()).limit(limit).all()
            return {"merges": [m.to_dict() for m in merges]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Tasks / Issues (async) ───

@router.post("/{workspace_id}/tasks")
async def api_create_task(workspace_id: str, req: CreateTaskRequest):
    import uuid
    from database.session import session_scope
    from models.workspace_models import WorkspaceTask, Workspace
    try:
        with session_scope() as session:
            ws = session.query(Workspace).filter_by(workspace_id=workspace_id).first()
            if not ws:
                raise HTTPException(status_code=404, detail="Workspace not found")
            task_id = f"TASK-{uuid.uuid4().hex[:12]}"
            task = WorkspaceTask(
                workspace_id=ws.id, task_id=task_id,
                title=req.title, description=req.description,
                task_type=req.task_type, priority=req.priority,
                assignee=req.assignee, labels=req.labels or [],
                related_files=req.related_files or [],
            )
            session.add(task)
            session.flush()
            await _track("task_created", f"Task: {req.title}", workspace_id)
            await _publish_vcs_event(workspace_id, "task_created", {
                "task_id": task_id, "title": req.title, "priority": req.priority,
            })
            return task.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/tasks")
async def api_list_tasks(workspace_id: str, status: Optional[str] = None,
                          priority: Optional[str] = None, limit: int = 50):
    from database.session import session_scope
    from models.workspace_models import WorkspaceTask, Workspace
    try:
        with session_scope() as session:
            ws = session.query(Workspace).filter_by(workspace_id=workspace_id).first()
            if not ws:
                raise HTTPException(status_code=404, detail="Workspace not found")
            q = session.query(WorkspaceTask).filter_by(workspace_id=ws.id)
            if status:
                q = q.filter_by(status=status)
            if priority:
                q = q.filter_by(priority=priority)
            tasks = q.order_by(WorkspaceTask.created_at.desc()).limit(limit).all()
            return {"tasks": [t.to_dict() for t in tasks], "total": len(tasks)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/tasks/{task_id}")
async def api_get_task(workspace_id: str, task_id: str):
    from database.session import session_scope
    from models.workspace_models import WorkspaceTask, Workspace
    try:
        with session_scope() as session:
            ws = session.query(Workspace).filter_by(workspace_id=workspace_id).first()
            if not ws:
                raise HTTPException(status_code=404, detail="Workspace not found")
            task = session.query(WorkspaceTask).filter_by(
                workspace_id=ws.id, task_id=task_id
            ).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            return task.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{workspace_id}/tasks/{task_id}")
async def api_update_task(workspace_id: str, task_id: str, req: UpdateTaskRequest):
    from datetime import datetime, timezone
    from database.session import session_scope
    from models.workspace_models import WorkspaceTask, Workspace
    try:
        with session_scope() as session:
            ws = session.query(Workspace).filter_by(workspace_id=workspace_id).first()
            if not ws:
                raise HTTPException(status_code=404, detail="Workspace not found")
            task = session.query(WorkspaceTask).filter_by(
                workspace_id=ws.id, task_id=task_id
            ).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            if req.status is not None:
                old_status = task.status
                task.status = req.status
                if req.status == "in_progress" and not task.started_at:
                    task.started_at = datetime.now(timezone.utc)
                if req.status in ("done", "closed") and not task.completed_at:
                    task.completed_at = datetime.now(timezone.utc)
            if req.priority is not None:
                task.priority = req.priority
            if req.assignee is not None:
                task.assignee = req.assignee
            if req.labels is not None:
                task.labels = req.labels
            if req.description is not None:
                task.description = req.description
            task.updated_at = datetime.now(timezone.utc)
            session.flush()
            await _track("task_updated", f"Task {task_id}: {task.status}", workspace_id)
            return task.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
