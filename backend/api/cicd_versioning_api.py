"""
CI/CD Version Control API
=========================
REST API for pipeline version control.
Every mutation is tracked with Genesis Keys.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

from genesis.cicd_versioning import (
    get_version_control,
    MutationType,
    PipelineVersion,
    on_pipeline_create,
    on_pipeline_update,
    on_pipeline_delete
)

router = APIRouter(prefix="/api/cicd/versions", tags=["CI/CD Version Control"])


# =============================================================================
# Request/Response Models
# =============================================================================

class VersionResponse(BaseModel):
    """Response model for a pipeline version."""
    version_id: str
    pipeline_id: str
    version_number: int
    mutation_type: str
    genesis_key: str
    timestamp: str
    author: str
    message: str
    config_hash: str
    previous_version: Optional[str]


class VersionHistoryResponse(BaseModel):
    """Response model for version history."""
    pipeline_id: str
    current_version: int
    total_versions: int
    created_at: str
    updated_at: str
    versions: List[VersionResponse]


class RollbackRequest(BaseModel):
    """Request to rollback a pipeline."""
    target_version: int = Field(..., description="Version number to rollback to")
    author: str = Field("system", description="Who is performing the rollback")


class DiffResponse(BaseModel):
    """Response model for version diff."""
    pipeline_id: str
    version_a: int
    version_b: int
    hash_a: str
    hash_b: str
    has_changes: bool
    changes: Dict[str, Any]


# =============================================================================
# Version Control Endpoints
# =============================================================================

@router.get("/{pipeline_id}")
async def get_pipeline_versions(pipeline_id: str, limit: int = 50):
    """
    Get version history for a pipeline.

    Returns all recorded versions with Genesis Keys.
    """
    vc = get_version_control()
    history = vc.get_history(pipeline_id, limit)

    if not history:
        return {
            "pipeline_id": pipeline_id,
            "current_version": 0,
            "total_versions": 0,
            "versions": [],
            "message": "No version history found"
        }

    return {
        "pipeline_id": pipeline_id,
        "current_version": history[0].version_number if history else 0,
        "total_versions": len(history),
        "versions": [
            {
                "version_id": v.version_id,
                "version_number": v.version_number,
                "mutation_type": v.mutation_type.value,
                "genesis_key": v.genesis_key,
                "timestamp": v.timestamp,
                "author": v.author,
                "message": v.message,
                "config_hash": v.config_hash,
                "previous_version": v.previous_version
            }
            for v in history
        ]
    }


@router.get("/{pipeline_id}/{version_number}")
async def get_specific_version(pipeline_id: str, version_number: int):
    """
    Get a specific version of a pipeline.

    Returns full configuration snapshot.
    """
    vc = get_version_control()
    version = vc.get_version(pipeline_id, version_number)

    if not version:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_number} not found for pipeline '{pipeline_id}'"
        )

    return {
        "version_id": version.version_id,
        "pipeline_id": version.pipeline_id,
        "version_number": version.version_number,
        "mutation_type": version.mutation_type.value,
        "genesis_key": version.genesis_key,
        "timestamp": version.timestamp,
        "author": version.author,
        "message": version.message,
        "config_hash": version.config_hash,
        "config": version.config_snapshot,
        "previous_version": version.previous_version,
        "metadata": version.metadata
    }


@router.get("/{pipeline_id}/diff/{version_a}/{version_b}")
async def diff_versions(pipeline_id: str, version_a: int, version_b: int):
    """
    Compare two versions of a pipeline.

    Returns differences between versions.
    """
    vc = get_version_control()
    diff = vc.diff_versions(pipeline_id, version_a, version_b)

    if "error" in diff:
        raise HTTPException(status_code=404, detail=diff["error"])

    return diff


@router.post("/{pipeline_id}/rollback")
async def rollback_pipeline(pipeline_id: str, request: RollbackRequest):
    """
    Rollback a pipeline to a previous version.

    Creates a new version with the old configuration.
    Tracked with Genesis Key.
    """
    vc = get_version_control()

    # Check if target version exists
    target = vc.get_version(pipeline_id, request.target_version)
    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"Version {request.target_version} not found"
        )

    # Perform rollback
    new_version = vc.rollback(pipeline_id, request.target_version, request.author)

    if not new_version:
        raise HTTPException(status_code=500, detail="Rollback failed")

    # Also update the actual pipeline in CI/CD system
    from genesis.cicd import get_cicd
    from genesis.cicd import Pipeline, PipelineStage, StageType

    cicd = get_cicd()
    config = target.config_snapshot

    # Reconstruct pipeline from config
    if "stages" in config:
        stages = []
        for s in config.get("stages", []):
            stage = PipelineStage(
                name=s.get("name", "unnamed"),
                stage_type=StageType(s.get("stage_type", s.get("type", "custom"))),
                commands=s.get("commands", []),
                working_dir=s.get("working_dir"),
                environment=s.get("environment", {}),
                timeout_seconds=s.get("timeout_seconds", 600),
                continue_on_error=s.get("continue_on_error", False),
                depends_on=s.get("depends_on", []),
                artifacts=s.get("artifacts", [])
            )
            stages.append(stage)

        pipeline = Pipeline(
            id=config.get("id", pipeline_id),
            name=config.get("name", pipeline_id),
            description=config.get("description", ""),
            stages=stages,
            triggers=config.get("triggers", ["manual"]),
            branches=config.get("branches", ["*"]),
            environment=config.get("environment", {}),
            timeout_minutes=config.get("timeout_minutes", 60)
        )

        cicd.pipelines[pipeline_id] = pipeline

    return {
        "status": "rolled_back",
        "pipeline_id": pipeline_id,
        "from_version": vc.get_version(pipeline_id).version_number - 1,
        "to_version": request.target_version,
        "new_version": new_version.version_number,
        "genesis_key": new_version.genesis_key,
        "timestamp": new_version.timestamp
    }


@router.get("/{pipeline_id}/export")
async def export_version_history(pipeline_id: str, format: str = "json"):
    """
    Export version history.

    Formats: json, markdown
    """
    vc = get_version_control()
    export = vc.export_history(pipeline_id, format)

    if not export:
        raise HTTPException(status_code=404, detail="No version history found")

    if format == "markdown":
        return {
            "format": "markdown",
            "content": export
        }

    import json
    return json.loads(export)


# =============================================================================
# Cross-Pipeline Endpoints
# =============================================================================

@router.get("/")
async def list_all_versions():
    """
    List version summaries for all pipelines.

    Returns overview of version control status.
    """
    vc = get_version_control()
    histories = vc.get_all_histories()

    summaries = []
    for pipeline_id, history in histories.items():
        summaries.append({
            "pipeline_id": pipeline_id,
            "current_version": history.current_version,
            "total_versions": len(history.versions),
            "created_at": history.created_at,
            "updated_at": history.updated_at,
            "latest_mutation": history.versions[-1].mutation_type.value if history.versions else None,
            "latest_author": history.versions[-1].author if history.versions else None
        })

    return {
        "total_pipelines": len(summaries),
        "pipelines": summaries
    }


@router.get("/genesis-keys")
async def get_version_genesis_keys(pipeline_id: Optional[str] = None, limit: int = 100):
    """
    Get Genesis Keys for version control operations.

    Full audit trail of all pipeline mutations.
    """
    vc = get_version_control()
    keys = vc.get_genesis_keys(pipeline_id)

    return {
        "count": min(len(keys), limit),
        "total": len(keys),
        "keys": keys[:limit]
    }


@router.get("/audit-trail")
async def get_audit_trail(
    pipeline_id: Optional[str] = None,
    mutation_type: Optional[str] = None,
    author: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 100
):
    """
    Get comprehensive audit trail.

    Filter by pipeline, mutation type, author, or time range.
    """
    vc = get_version_control()
    all_versions = []

    for pid, history in vc.get_all_histories().items():
        if pipeline_id and pid != pipeline_id:
            continue

        for v in history.versions:
            # Apply filters
            if mutation_type and v.mutation_type.value != mutation_type:
                continue
            if author and v.author != author:
                continue
            if since:
                version_time = datetime.fromisoformat(v.timestamp.replace("Z", "+00:00"))
                filter_time = datetime.fromisoformat(since.replace("Z", "+00:00"))
                if version_time < filter_time:
                    continue

            all_versions.append({
                "genesis_key": v.genesis_key,
                "pipeline_id": v.pipeline_id,
                "version": v.version_number,
                "mutation_type": v.mutation_type.value,
                "author": v.author,
                "message": v.message,
                "timestamp": v.timestamp,
                "config_hash": v.config_hash
            })

    # Sort by timestamp descending
    all_versions.sort(key=lambda x: x["timestamp"], reverse=True)

    return {
        "count": min(len(all_versions), limit),
        "total": len(all_versions),
        "audit_trail": all_versions[:limit]
    }
