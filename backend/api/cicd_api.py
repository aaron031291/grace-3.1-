"""
Genesis CI/CD API
=================
REST API for the Genesis Key-powered CI/CD pipeline system.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
import hashlib
import hmac
import logging

from genesis.cicd import (
    get_cicd,
    GenesisCICD,
    Pipeline,
    PipelineRun,
    PipelineStage,
    PipelineStatus,
    StageType,
    StageResult,
    GenesisKeyAction
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cicd", tags=["CI/CD"])


# =============================================================================
# Request/Response Models
# =============================================================================

class TriggerPipelineRequest(BaseModel):
    """Request to trigger a pipeline."""
    pipeline_id: str = Field(..., description="Pipeline ID to trigger")
    branch: str = Field("main", description="Git branch")
    commit_sha: Optional[str] = Field(None, description="Git commit SHA")
    commit_message: Optional[str] = Field(None, description="Commit message")
    variables: Optional[Dict[str, str]] = Field(None, description="Environment variables")


class CreatePipelineRequest(BaseModel):
    """Request to create a new pipeline."""
    id: str = Field(..., description="Unique pipeline ID")
    name: str = Field(..., description="Pipeline name")
    description: str = Field("", description="Pipeline description")
    triggers: List[str] = Field(["manual"], description="Trigger types")
    branches: List[str] = Field(["*"], description="Branch filters")
    stages: List[Dict[str, Any]] = Field(..., description="Pipeline stages")
    environment: Optional[Dict[str, str]] = Field(None, description="Global env vars")
    timeout_minutes: int = Field(60, description="Pipeline timeout in minutes")


class StageResultResponse(BaseModel):
    """Response model for stage results."""
    stage_name: str
    status: str
    started_at: str
    completed_at: Optional[str]
    duration_seconds: float
    exit_code: int
    stdout: str
    stderr: str


class PipelineRunResponse(BaseModel):
    """Response model for pipeline runs."""
    id: str
    pipeline_id: str
    pipeline_name: str
    genesis_key: str
    status: str
    trigger: str
    branch: str
    commit_sha: Optional[str]
    commit_message: Optional[str]
    triggered_by: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: float
    stage_results: List[StageResultResponse]
    artifacts: Dict[str, str]


class PipelineResponse(BaseModel):
    """Response model for pipelines."""
    id: str
    name: str
    description: str
    triggers: List[str]
    branches: List[str]
    stage_count: int
    created_at: str


class WebhookPayload(BaseModel):
    """Webhook payload for Git events."""
    event: str = Field(..., description="Event type (push, pull_request)")
    repository: Dict[str, Any] = Field(..., description="Repository info")
    ref: Optional[str] = Field(None, description="Git ref")
    before: Optional[str] = Field(None, description="Before SHA")
    after: Optional[str] = Field(None, description="After SHA")
    commits: Optional[List[Dict[str, Any]]] = Field(None, description="Commits")
    pull_request: Optional[Dict[str, Any]] = Field(None, description="PR info")


# =============================================================================
# Pipeline Endpoints
# =============================================================================

@router.get("/pipelines", response_model=List[PipelineResponse])
async def list_pipelines():
    """
    List all registered pipelines.

    Returns list of available CI/CD pipelines.
    """
    cicd = get_cicd()
    pipelines = cicd.list_pipelines()

    return [
        PipelineResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            triggers=p.triggers,
            branches=p.branches,
            stage_count=len(p.stages),
            created_at=p.created_at
        )
        for p in pipelines
    ]


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """
    Get pipeline details.

    Returns full pipeline configuration including stages.
    """
    cicd = get_cicd()
    pipeline = cicd.get_pipeline(pipeline_id)

    if not pipeline:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")

    return {
        "id": pipeline.id,
        "name": pipeline.name,
        "description": pipeline.description,
        "triggers": pipeline.triggers,
        "branches": pipeline.branches,
        "timeout_minutes": pipeline.timeout_minutes,
        "environment": pipeline.environment,
        "stages": [
            {
                "name": s.name,
                "type": s.stage_type.value,
                "commands": s.commands,
                "working_dir": s.working_dir,
                "timeout_seconds": s.timeout_seconds,
                "continue_on_error": s.continue_on_error,
                "depends_on": s.depends_on,
                "artifacts": s.artifacts
            }
            for s in pipeline.stages
        ],
        "created_at": pipeline.created_at,
        "updated_at": pipeline.updated_at
    }


@router.post("/pipelines")
async def create_pipeline(request: CreatePipelineRequest):
    """
    Create a new pipeline.

    Registers a custom CI/CD pipeline configuration.
    """
    cicd = get_cicd()

    # Check if pipeline already exists
    if cicd.get_pipeline(request.id):
        raise HTTPException(status_code=409, detail=f"Pipeline '{request.id}' already exists")

    # Convert stage dicts to PipelineStage objects
    stages = []
    for stage_data in request.stages:
        stage = PipelineStage(
            name=stage_data.get("name", "unnamed"),
            stage_type=StageType(stage_data.get("type", "custom")),
            commands=stage_data.get("commands", []),
            working_dir=stage_data.get("working_dir"),
            environment=stage_data.get("environment", {}),
            timeout_seconds=stage_data.get("timeout_seconds", 600),
            continue_on_error=stage_data.get("continue_on_error", False),
            depends_on=stage_data.get("depends_on", []),
            artifacts=stage_data.get("artifacts", [])
        )
        stages.append(stage)

    pipeline = Pipeline(
        id=request.id,
        name=request.name,
        description=request.description,
        stages=stages,
        triggers=request.triggers,
        branches=request.branches,
        environment=request.environment or {},
        timeout_minutes=request.timeout_minutes
    )

    cicd.register_pipeline(pipeline)

    return {
        "status": "created",
        "pipeline_id": pipeline.id,
        "name": pipeline.name,
        "stages": len(pipeline.stages)
    }


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str):
    """
    Delete a pipeline.

    Removes a pipeline from the system.
    """
    cicd = get_cicd()

    if pipeline_id not in cicd.pipelines:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")

    # Prevent deletion of default pipelines
    if pipeline_id in ["grace-ci", "grace-quick", "grace-deploy"]:
        raise HTTPException(status_code=403, detail="Cannot delete default pipelines")

    del cicd.pipelines[pipeline_id]

    return {"status": "deleted", "pipeline_id": pipeline_id}


# =============================================================================
# Pipeline Run Endpoints
# =============================================================================

@router.post("/trigger", response_model=PipelineRunResponse)
async def trigger_pipeline(request: TriggerPipelineRequest, background_tasks: BackgroundTasks):
    """
    Trigger a pipeline execution.

    Starts a new pipeline run with the specified configuration.
    Returns immediately with run details (execution happens in background).
    """
    cicd = get_cicd()

    if not cicd.get_pipeline(request.pipeline_id):
        raise HTTPException(status_code=404, detail=f"Pipeline '{request.pipeline_id}' not found")

    run = await cicd.trigger_pipeline(
        pipeline_id=request.pipeline_id,
        trigger="manual",
        branch=request.branch,
        commit_sha=request.commit_sha,
        commit_message=request.commit_message,
        triggered_by="api",
        variables=request.variables
    )

    return _run_to_response(run)


@router.get("/runs", response_model=List[PipelineRunResponse])
async def list_runs(
    pipeline_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """
    List pipeline runs.

    Returns recent pipeline executions with optional filters.
    """
    cicd = get_cicd()

    status_enum = PipelineStatus(status) if status else None
    runs = cicd.list_runs(pipeline_id=pipeline_id, status=status_enum, limit=limit)

    return [_run_to_response(r) for r in runs]


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
async def get_run(run_id: str):
    """
    Get pipeline run details.

    Returns full details of a specific pipeline execution.
    """
    cicd = get_cicd()
    run = cicd.get_run(run_id)

    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    return _run_to_response(run)


@router.get("/runs/{run_id}/logs")
async def get_run_logs(run_id: str):
    """
    Get pipeline run logs.

    Returns combined stdout/stderr from all stages.
    """
    cicd = get_cicd()
    run = cicd.get_run(run_id)

    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    logs = []
    for stage in run.stage_results:
        logs.append(f"\n{'='*60}")
        logs.append(f"Stage: {stage.stage_name}")
        logs.append(f"Status: {stage.status}")
        logs.append(f"Duration: {stage.duration_seconds:.1f}s")
        logs.append(f"{'='*60}")

        if stage.stdout:
            logs.append("\n--- STDOUT ---")
            logs.append(stage.stdout)

        if stage.stderr:
            logs.append("\n--- STDERR ---")
            logs.append(stage.stderr)

    return {
        "run_id": run_id,
        "pipeline": run.pipeline_name,
        "status": run.status.value,
        "logs": "\n".join(logs)
    }


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    """
    Cancel a running pipeline.

    Attempts to cancel a pipeline that is queued or running.
    """
    cicd = get_cicd()

    success = await cicd.cancel_run(run_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel run (not found or already completed)"
        )

    return {"status": "cancelled", "run_id": run_id}


@router.post("/runs/{run_id}/retry")
async def retry_run(run_id: str):
    """
    Retry a failed pipeline run.

    Creates a new run with the same configuration as the specified run.
    """
    cicd = get_cicd()
    original_run = cicd.get_run(run_id)

    if not original_run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    if original_run.status not in [PipelineStatus.FAILED, PipelineStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Can only retry failed or cancelled runs")

    new_run = await cicd.trigger_pipeline(
        pipeline_id=original_run.pipeline_id,
        trigger="retry",
        branch=original_run.branch,
        commit_sha=original_run.commit_sha,
        commit_message=original_run.commit_message,
        triggered_by="retry",
        variables=original_run.metadata.get("variables")
    )

    return _run_to_response(new_run)


# =============================================================================
# Webhook Endpoint
# =============================================================================

@router.post("/webhook")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle Git webhook events.

    Triggers pipelines based on push/PR events.
    Supports GitHub, GitLab, and Bitbucket webhook formats.
    """
    cicd = get_cicd()

    # Parse webhook payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Detect webhook source and extract event info
    event_type = None
    branch = None
    commit_sha = None
    commit_message = None
    repository = None

    # GitHub webhook
    if "X-GitHub-Event" in request.headers:
        event_type = request.headers.get("X-GitHub-Event")

        if event_type == "push":
            ref = payload.get("ref", "")
            branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else None
            commit_sha = payload.get("after")
            commits = payload.get("commits", [])
            commit_message = commits[-1].get("message") if commits else None
            repository = payload.get("repository", {}).get("full_name")

        elif event_type == "pull_request":
            pr = payload.get("pull_request", {})
            branch = pr.get("head", {}).get("ref")
            commit_sha = pr.get("head", {}).get("sha")
            commit_message = pr.get("title")
            repository = payload.get("repository", {}).get("full_name")

    # GitLab webhook
    elif "X-Gitlab-Event" in request.headers:
        event_type = payload.get("object_kind")

        if event_type == "push":
            branch = payload.get("ref", "").replace("refs/heads/", "")
            commit_sha = payload.get("after")
            commits = payload.get("commits", [])
            commit_message = commits[-1].get("message") if commits else None
            repository = payload.get("project", {}).get("path_with_namespace")

        elif event_type == "merge_request":
            mr = payload.get("object_attributes", {})
            branch = mr.get("source_branch")
            commit_sha = mr.get("last_commit", {}).get("id")
            commit_message = mr.get("title")
            repository = payload.get("project", {}).get("path_with_namespace")

    # Generic webhook (custom)
    else:
        event_type = payload.get("event", "push")
        branch = payload.get("branch", "main")
        commit_sha = payload.get("commit_sha")
        commit_message = payload.get("commit_message")
        repository = payload.get("repository")

    if not event_type or not branch:
        raise HTTPException(status_code=400, detail="Could not parse webhook event")

    # Generate Genesis Key for webhook
    cicd._generate_genesis_key(
        GenesisKeyAction.WEBHOOK_RECEIVED,
        {
            "event": event_type,
            "branch": branch,
            "repository": repository,
            "commit_sha": commit_sha
        }
    )

    # Map event type to trigger
    trigger_map = {
        "push": "push",
        "pull_request": "pull_request",
        "merge_request": "pull_request"
    }
    trigger = trigger_map.get(event_type, event_type)

    # Find matching pipelines
    triggered_runs = []
    for pipeline in cicd.list_pipelines():
        # Check if trigger matches
        if trigger not in pipeline.triggers:
            continue

        # Check if branch matches
        branch_match = False
        for pattern in pipeline.branches:
            if pattern == "*":
                branch_match = True
                break
            elif pattern.endswith("*"):
                if branch.startswith(pattern[:-1]):
                    branch_match = True
                    break
            elif pattern == branch:
                branch_match = True
                break

        if not branch_match:
            continue

        # Trigger the pipeline
        run = await cicd.trigger_pipeline(
            pipeline_id=pipeline.id,
            trigger=trigger,
            branch=branch,
            commit_sha=commit_sha,
            commit_message=commit_message,
            triggered_by=f"webhook:{repository}"
        )
        triggered_runs.append({
            "pipeline_id": pipeline.id,
            "run_id": run.id,
            "genesis_key": run.genesis_key
        })

    return {
        "status": "processed",
        "event": event_type,
        "branch": branch,
        "repository": repository,
        "triggered_pipelines": len(triggered_runs),
        "runs": triggered_runs
    }


# =============================================================================
# Genesis Key Endpoints
# =============================================================================

@router.get("/genesis-keys")
async def list_genesis_keys(run_id: Optional[str] = None):
    """
    List Genesis Keys for CI/CD operations.

    Returns tracking keys generated during pipeline executions.
    """
    cicd = get_cicd()
    keys = cicd.get_genesis_keys(run_id)

    return {
        "count": len(keys),
        "keys": [
            {
                "key": k,
                "action": v["action"],
                "timestamp": v["timestamp"],
                "metadata": v["metadata"]
            }
            for k, v in keys.items()
        ]
    }


# =============================================================================
# Status Endpoint
# =============================================================================

@router.get("/status")
async def get_cicd_status():
    """
    Get CI/CD system status.

    Returns current state of the pipeline system.
    """
    cicd = get_cicd()

    runs = cicd.list_runs(limit=100)

    status_counts = {}
    for run in runs:
        status = run.status.value
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "status": "running" if cicd._running else "stopped",
        "pipelines_registered": len(cicd.pipelines),
        "active_runs": len(cicd.active_runs),
        "total_runs": len(cicd.runs),
        "genesis_keys_generated": len(cicd.genesis_keys),
        "run_stats": status_counts,
        "queued_runs": cicd.run_queue.qsize()
    }


# =============================================================================
# Helper Functions
# =============================================================================

def _run_to_response(run: PipelineRun) -> PipelineRunResponse:
    """Convert PipelineRun to response model."""
    return PipelineRunResponse(
        id=run.id,
        pipeline_id=run.pipeline_id,
        pipeline_name=run.pipeline_name,
        genesis_key=run.genesis_key,
        status=run.status.value,
        trigger=run.trigger,
        branch=run.branch,
        commit_sha=run.commit_sha,
        commit_message=run.commit_message,
        triggered_by=run.triggered_by,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_seconds=run.duration_seconds,
        stage_results=[
            StageResultResponse(
                stage_name=s.stage_name,
                status=s.status.value,
                started_at=s.started_at,
                completed_at=s.completed_at,
                duration_seconds=s.duration_seconds,
                exit_code=s.exit_code,
                stdout=s.stdout[-2000:] if s.stdout else "",  # Truncate for response
                stderr=s.stderr[-2000:] if s.stderr else ""
            )
            for s in run.stage_results
        ],
        artifacts=run.artifacts
    )
