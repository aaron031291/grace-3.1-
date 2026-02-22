"""
API endpoints for Grace's self-modeling and telemetry system.

Provides endpoints for viewing operation logs, baselines, drift alerts,
and triggering replays.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel, ConfigDict

from database.session import get_session
from models.telemetry_models import (
    OperationLog, PerformanceBaseline, DriftAlert,
    OperationReplay, SystemState, OperationType, OperationStatus
)
from telemetry.telemetry_service import get_telemetry_service
from telemetry.replay_service import get_replay_service

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


# Response models
class OperationLogResponse(BaseModel):
    run_id: str
    operation_type: str
    operation_name: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[float]
    status: str
    error_message: Optional[str]
    cpu_percent: Optional[float]
    memory_mb: Optional[float]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    confidence_score: Optional[float]

    model_config = ConfigDict(from_attributes=True)


class BaselineResponse(BaseModel):
    id: int
    operation_type: str
    operation_name: str
    sample_count: int
    mean_duration_ms: Optional[float]
    median_duration_ms: Optional[float]
    p95_duration_ms: Optional[float]
    success_rate: Optional[float]
    mean_confidence_score: Optional[float]
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)


class DriftAlertResponse(BaseModel):
    id: int
    run_id: str
    operation_type: str
    operation_name: str
    drift_type: str
    baseline_value: Optional[float]
    observed_value: Optional[float]
    deviation_percent: Optional[float]
    severity: str
    acknowledged: bool
    resolved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SystemStateResponse(BaseModel):
    id: int
    created_at: datetime
    ollama_running: bool
    qdrant_connected: bool
    document_count: Optional[int]
    chunk_count: Optional[int]
    vector_count: Optional[int]
    average_confidence_score: Optional[float]
    cpu_percent: Optional[float]
    memory_percent: Optional[float]
    operations_last_24h: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class ReplayResponse(BaseModel):
    id: int
    original_run_id: str
    replay_run_id: str
    replay_reason: Optional[str]
    original_status: Optional[str]
    replay_status: Optional[str]
    outputs_match: Optional[bool]
    insights: Optional[str]
    replayed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OperationStatsResponse(BaseModel):
    total_operations: int
    completed_operations: int
    failed_operations: int
    success_rate: float
    average_duration_ms: float
    total_tokens_processed: int


# Endpoints

@router.get("/operations", response_model=List[OperationLogResponse])
def get_operations(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    operation_type: Optional[OperationType] = None,
    status: Optional[OperationStatus] = None,
    session: Session = Depends(get_session)
):
    """Get recent operations with optional filtering."""
    query = session.query(OperationLog)

    if operation_type:
        query = query.filter(OperationLog.operation_type == operation_type)

    if status:
        query = query.filter(OperationLog.status == status)

    operations = query.order_by(
        desc(OperationLog.started_at)
    ).offset(offset).limit(limit).all()

    return operations


@router.get("/operations/{run_id}", response_model=OperationLogResponse)
def get_operation(
    run_id: str,
    session: Session = Depends(get_session)
):
    """Get a specific operation by run ID."""
    operation = session.query(OperationLog).filter(
        OperationLog.run_id == run_id
    ).first()

    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")

    return operation


@router.get("/baselines", response_model=List[BaselineResponse])
def get_baselines(
    operation_type: Optional[OperationType] = None,
    session: Session = Depends(get_session)
):
    """Get performance baselines for operations."""
    query = session.query(PerformanceBaseline)

    if operation_type:
        query = query.filter(PerformanceBaseline.operation_type == operation_type)

    baselines = query.order_by(
        desc(PerformanceBaseline.last_updated)
    ).all()

    return baselines


@router.get("/drift-alerts", response_model=List[DriftAlertResponse])
def get_drift_alerts(
    resolved: bool = Query(False),
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session)
):
    """Get drift alerts, optionally filtered by resolution status and severity."""
    query = session.query(DriftAlert).filter(
        DriftAlert.resolved == resolved
    )

    if severity:
        query = query.filter(DriftAlert.severity == severity)

    alerts = query.order_by(
        desc(DriftAlert.created_at)
    ).limit(limit).all()

    return alerts


@router.post("/drift-alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    session: Session = Depends(get_session)
):
    """Acknowledge a drift alert."""
    alert = session.query(DriftAlert).filter(DriftAlert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.acknowledged = True
    alert.acknowledged_at = datetime.now()
    session.commit()

    return {"status": "acknowledged", "alert_id": alert_id}


@router.post("/drift-alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    resolution_notes: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Mark a drift alert as resolved."""
    alert = session.query(DriftAlert).filter(DriftAlert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.resolved = True
    alert.resolved_at = datetime.now()
    alert.resolution_notes = resolution_notes
    session.commit()

    return {"status": "resolved", "alert_id": alert_id}


@router.get("/system-state/current", response_model=SystemStateResponse)
def get_current_system_state(session: Session = Depends(get_session)):
    """Get the most recent system state snapshot."""
    state = session.query(SystemState).order_by(
        desc(SystemState.created_at)
    ).first()

    if not state:
        # Create first snapshot
        telemetry = get_telemetry_service(session)
        state = telemetry.capture_system_state()

    return state


@router.post("/system-state/capture", response_model=SystemStateResponse)
def capture_system_state(session: Session = Depends(get_session)):
    """Manually trigger a system state snapshot."""
    telemetry = get_telemetry_service(session)
    state = telemetry.capture_system_state()
    return state


@router.get("/system-state/history", response_model=List[SystemStateResponse])
def get_system_state_history(
    hours: int = Query(24, ge=1, le=168),  # Max 1 week
    session: Session = Depends(get_session)
):
    """Get system state history for the specified time period."""
    since = datetime.now() - timedelta(hours=hours)

    states = session.query(SystemState).filter(
        SystemState.created_at >= since
    ).order_by(desc(SystemState.created_at)).all()

    return states


@router.get("/stats", response_model=OperationStatsResponse)
def get_operation_stats(
    hours: int = Query(24, ge=1, le=168),
    operation_type: Optional[OperationType] = None,
    session: Session = Depends(get_session)
):
    """Get aggregated operation statistics."""
    since = datetime.now() - timedelta(hours=hours)

    query = session.query(OperationLog).filter(
        OperationLog.started_at >= since
    )

    if operation_type:
        query = query.filter(OperationLog.operation_type == operation_type)

    operations = query.all()

    total = len(operations)
    completed = sum(1 for op in operations if op.status == OperationStatus.COMPLETED)
    failed = sum(1 for op in operations if op.status == OperationStatus.FAILED)

    durations = [op.duration_ms for op in operations if op.duration_ms is not None]
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    total_tokens = sum(
        (op.input_tokens or 0) + (op.output_tokens or 0)
        for op in operations
    )

    return OperationStatsResponse(
        total_operations=total,
        completed_operations=completed,
        failed_operations=failed,
        success_rate=completed / total if total > 0 else 0.0,
        average_duration_ms=avg_duration,
        total_tokens_processed=total_tokens
    )


@router.get("/replays", response_model=List[ReplayResponse])
def get_replays(
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session)
):
    """Get operation replay history."""
    replays = session.query(OperationReplay).order_by(
        desc(OperationReplay.replayed_at)
    ).limit(limit).all()

    return replays


@router.post("/replays/{run_id}")
def replay_operation(
    run_id: str,
    reason: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    Replay a failed operation.

    Note: This endpoint requires the operation to have stored inputs.
    Not all operations support replay.
    """
    # Get the operation
    operation = session.query(OperationLog).filter(
        OperationLog.run_id == run_id
    ).first()

    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")

    if not operation.metadata or 'inputs' not in operation.metadata:
        raise HTTPException(
            status_code=400,
            detail="Operation does not have stored inputs. Cannot replay."
        )

    # For now, return info about the replay capability
    # Actual replay would require operation-specific handlers
    return {
        "message": "Replay endpoint ready",
        "run_id": run_id,
        "operation_type": operation.operation_type.value,
        "operation_name": operation.operation_name,
        "replayable": True,
        "note": "Implement operation-specific replay handlers to enable full replay"
    }


@router.get("/health")
def telemetry_health(session: Session = Depends(get_session)):
    """Check telemetry system health."""
    # Count recent operations
    recent_ops = session.query(OperationLog).filter(
        OperationLog.started_at >= datetime.now() - timedelta(hours=1)
    ).count()

    # Count baselines
    baselines = session.query(PerformanceBaseline).count()

    # Count unresolved alerts
    unresolved_alerts = session.query(DriftAlert).filter(
        DriftAlert.resolved == False
    ).count()

    return {
        "status": "healthy",
        "recent_operations_1h": recent_ops,
        "baselines_tracked": baselines,
        "unresolved_alerts": unresolved_alerts,
        "timestamp": datetime.now()
    }
