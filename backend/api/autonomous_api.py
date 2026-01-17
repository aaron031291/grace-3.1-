from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
import json
import logging
from genesis.autonomous_engine import get_autonomous_engine, ActionType, ActionPriority, TriggerType, ActionStatus
class QueueActionRequest(BaseModel):
    logger = logging.getLogger(__name__)
    """Request to queue an autonomous action."""
    action_type: str = Field(..., description="Type of action to perform")
    context_data: Optional[Dict[str, Any]] = Field(default=None, description="Context data for the action")
    priority: str = Field(default="normal", description="Action priority")
    trigger_type: str = Field(default="request", description="What triggered this action")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class CreateRuleRequest(BaseModel):
    """Request to create an autonomous rule."""
    name: str = Field(..., description="Rule name")
    trigger_type: str = Field(..., description="Trigger type (event, schedule, condition)")
    trigger_config: Dict[str, Any] = Field(..., description="Trigger configuration")
    action_type: str = Field(..., description="Action type to execute")
    action_config: Optional[Dict[str, Any]] = Field(default=None, description="Action configuration")
    priority: str = Field(default="normal", description="Action priority")
    enabled: bool = Field(default=True, description="Whether rule is enabled")


class EmitEventRequest(BaseModel):
    """Request to emit an event."""
    event_name: str = Field(..., description="Name of the event")
    event_data: Optional[Dict[str, Any]] = Field(default=None, description="Event data")


class ActionResponse(BaseModel):
    """Response for action operations."""
    action_id: str
    action_type: str
    status: str
    priority: str
    trigger_type: str
    genesis_key: str
    queued_at: str
    message: str


class ActionDetailsResponse(BaseModel):
    """Detailed action response."""
    action_id: str
    action_type: str
    status: str
    priority: str
    trigger_type: str
    genesis_key: str
    queued_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    context: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    error: Optional[str]


# =============================================================================
# Action Endpoints
# =============================================================================

@router.post("/queue", response_model=ActionResponse)
async def queue_action(request: QueueActionRequest):
    """
    Queue an autonomous action for execution.

    Actions are processed based on priority:
    - critical: Immediate execution
    - high: Next in queue
    - normal: Standard processing
    - low: When resources available
    - background: Idle processing
    """
    engine = get_autonomous_engine()

    try:
        action_type = ActionType(request.action_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action type: {request.action_type}. Valid types: {[t.value for t in ActionType]}"
        )

    try:
        priority = ActionPriority(request.priority)
    except ValueError:
        priority = ActionPriority.NORMAL

    try:
        trigger_type = TriggerType(request.trigger_type)
    except ValueError:
        trigger_type = TriggerType.REQUEST

    action = await engine.queue_action(
        action_type=action_type,
        context=request.context_data or {},
        priority=priority,
        trigger=trigger_type,
        metadata=request.metadata
    )

    return ActionResponse(
        action_id=action.action_id,
        action_type=action.action_type.value,
        status=action.status.value,
        priority=action.priority.value,
        trigger_type=action.trigger.value,
        genesis_key=action.genesis_key,
        queued_at=action.queued_at,
        message=f"Action {action.action_id} queued successfully"
    )


@router.get("/actions")
async def list_actions(
    status: Optional[str] = None,
    action_type: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100
):
    """
    List autonomous actions.

    Filter by status, type, or priority.
    """
    engine = get_autonomous_engine()

    # Parse filters
    status_filter = ActionStatus(status) if status else None
    type_filter = ActionType(action_type) if action_type else None
    priority_filter = ActionPriority(priority) if priority else None

    actions = engine.list_actions(
        status=status_filter,
        action_type=type_filter,
        priority=priority_filter,
        limit=limit
    )

    return {
        "count": len(actions),
        "actions": [
            {
                "action_id": a.action_id,
                "action_type": a.action_type.value,
                "status": a.status.value,
                "priority": a.priority.value,
                "trigger_type": a.trigger.value,
                "genesis_key": a.genesis_key,
                "queued_at": a.queued_at,
                "started_at": a.started_at,
                "completed_at": a.completed_at
            }
            for a in actions
        ]
    }


@router.get("/actions/{action_id}", response_model=ActionDetailsResponse)
async def get_action(action_id: str):
    """
    Get details of a specific action.

    Returns full action information including result or error.
    """
    engine = get_autonomous_engine()
    action = engine.get_action(action_id)

    if not action:
        raise HTTPException(status_code=404, detail=f"Action not found: {action_id}")

    return ActionDetailsResponse(
        action_id=action.action_id,
        action_type=action.action_type.value,
        status=action.status.value,
        priority=action.priority.value,
        trigger_type=action.trigger.value,
        genesis_key=action.genesis_key,
        queued_at=action.queued_at,
        started_at=action.started_at,
        completed_at=action.completed_at,
        context=action.context.data,
        result=action.result,
        error=action.error
    )


@router.delete("/actions/{action_id}")
async def cancel_action(action_id: str):
    """
    Cancel a pending action.

    Only pending actions can be cancelled.
    """
    engine = get_autonomous_engine()
    success = await engine.cancel_action(action_id)

    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel action (not found or already running)")

    return {"success": True, "message": f"Action {action_id} cancelled"}


# =============================================================================
# Rule Endpoints
# =============================================================================

@router.post("/rules")
async def create_rule(request: CreateRuleRequest):
    """
    Create an autonomous rule.

    Rules automatically trigger actions based on events, schedules, or conditions.
    """
    engine = get_autonomous_engine()

    try:
        trigger_type = TriggerType(request.trigger_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trigger type: {request.trigger_type}"
        )

    try:
        action_type = ActionType(request.action_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action type: {request.action_type}"
        )

    try:
        priority = ActionPriority(request.priority)
    except ValueError:
        priority = ActionPriority.NORMAL

    rule_id = engine.add_rule(
        name=request.name,
        trigger_type=trigger_type,
        trigger_config=request.trigger_config,
        action_type=action_type,
        action_config=request.action_config or {},
        priority=priority,
        enabled=request.enabled
    )

    return {
        "success": True,
        "rule_id": rule_id,
        "message": f"Rule '{request.name}' created successfully"
    }


@router.get("/rules")
async def list_rules():
    """
    List all autonomous rules.

    Returns both enabled and disabled rules.
    """
    engine = get_autonomous_engine()
    rules = engine.list_rules()

    return {
        "count": len(rules),
        "rules": rules
    }


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    """
    Get details of a specific rule.
    """
    engine = get_autonomous_engine()
    rule = engine.get_rule(rule_id)

    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    return rule


@router.put("/rules/{rule_id}/enable")
async def enable_rule(rule_id: str):
    """
    Enable an autonomous rule.
    """
    engine = get_autonomous_engine()
    success = engine.enable_rule(rule_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    return {"success": True, "message": f"Rule {rule_id} enabled"}


@router.put("/rules/{rule_id}/disable")
async def disable_rule(rule_id: str):
    """
    Disable an autonomous rule.
    """
    engine = get_autonomous_engine()
    success = engine.disable_rule(rule_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    return {"success": True, "message": f"Rule {rule_id} disabled"}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """
    Delete an autonomous rule.
    """
    engine = get_autonomous_engine()
    success = engine.delete_rule(rule_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    return {"success": True, "message": f"Rule {rule_id} deleted"}


# =============================================================================
# Event Endpoints
# =============================================================================

@router.post("/events/emit")
async def emit_event(request: EmitEventRequest):
    """
    Emit an event to trigger autonomous actions.

    Events can trigger rules configured to listen for specific event names.
    """
    engine = get_autonomous_engine()

    triggered = await engine.emit_event(
        event_name=request.event_name,
        data=request.event_data or {}
    )

    return {
        "success": True,
        "event_name": request.event_name,
        "actions_triggered": triggered,
        "message": f"Event '{request.event_name}' emitted, triggered {triggered} action(s)"
    }


@router.get("/events/types")
async def list_event_types():
    """
    List common event types.

    These are predefined events that can trigger actions.
    """
    return {
        "event_types": [
            {"name": "file_created", "description": "A new file was created"},
            {"name": "file_modified", "description": "A file was modified"},
            {"name": "file_deleted", "description": "A file was deleted"},
            {"name": "error_detected", "description": "An error was detected"},
            {"name": "threshold_exceeded", "description": "A threshold was exceeded"},
            {"name": "schedule_tick", "description": "Scheduled event tick"},
            {"name": "health_check_failed", "description": "Health check failed"},
            {"name": "new_data_available", "description": "New data is available for processing"},
            {"name": "memory_stored", "description": "Memory was stored"},
            {"name": "pattern_detected", "description": "A pattern was detected"},
            {"name": "user_request", "description": "User requested an action"},
            {"name": "pipeline_completed", "description": "CI/CD pipeline completed"},
            {"name": "pipeline_failed", "description": "CI/CD pipeline failed"}
        ]
    }


# =============================================================================
# Engine Control Endpoints
# =============================================================================

@router.post("/engine/start")
async def start_engine(background_tasks: BackgroundTasks):
    """
    Start the autonomous engine.

    Begins processing queued actions and listening for events.
    """
    engine = get_autonomous_engine()

    if engine.running:
        return {"status": "already_running", "message": "Engine is already running"}

    background_tasks.add_task(engine.start)

    return {"status": "starting", "message": "Autonomous engine starting"}


@router.post("/engine/stop")
async def stop_engine():
    """
    Stop the autonomous engine.

    Stops processing new actions (current action will complete).
    """
    engine = get_autonomous_engine()

    if not engine.running:
        return {"status": "already_stopped", "message": "Engine is not running"}

    await engine.stop()

    return {"status": "stopped", "message": "Autonomous engine stopped"}


@router.get("/engine/status")
async def get_engine_status():
    """
    Get autonomous engine status.

    Returns running state, queue size, and statistics.
    """
    engine = get_autonomous_engine()
    status = engine.get_status()

    return status


# =============================================================================
# Reference Data Endpoints
# =============================================================================

@router.get("/action-types")
async def list_action_types():
    """
    List available action types.

    These are the autonomous actions GRACE can perform.
    """
    descriptions = {
        "ingest_file": "Ingest a single file into the library",
        "ingest_directory": "Ingest all files from a directory",
        "run_pipeline": "Execute a CI/CD pipeline",
        "health_check": "Perform system health check",
        "cleanup": "Clean up temporary files and resources",
        "backup": "Create a backup of data",
        "index_rebuild": "Rebuild search indices",
        "memory_consolidate": "Consolidate learning memory",
        "pattern_learn": "Learn patterns from data",
        "generate_report": "Generate a status report",
        "notify": "Send a notification",
        "custom": "Custom action with handler"
    }

    return {
        "action_types": [
            {"value": at.value, "name": at.name, "description": descriptions.get(at.value, "")}
            for at in ActionType
        ]
    }


@router.get("/priorities")
async def list_priorities():
    """
    List action priorities.

    Higher priority actions are processed first.
    """
    return {
        "priorities": [
            {"value": "critical", "weight": 100, "description": "Immediate execution"},
            {"value": "high", "weight": 75, "description": "High priority, next in queue"},
            {"value": "normal", "weight": 50, "description": "Standard priority"},
            {"value": "low", "weight": 25, "description": "Low priority, when resources available"},
            {"value": "background", "weight": 10, "description": "Background, idle processing"}
        ]
    }


@router.get("/trigger-types")
async def list_trigger_types():
    """
    List trigger types.

    These define what can trigger an autonomous action.
    """
    return {
        "trigger_types": [
            {"value": "event", "description": "Triggered by an event"},
            {"value": "schedule", "description": "Triggered on a schedule"},
            {"value": "condition", "description": "Triggered when a condition is met"},
            {"value": "request", "description": "Triggered by an API request"},
            {"value": "self", "description": "Self-triggered by GRACE"}
        ]
    }


# =============================================================================
# Health Endpoint
# =============================================================================

@router.get("/health")
async def autonomous_health():
    """
    Check autonomous engine health.

    Returns engine status and queue information.
    """
    engine = get_autonomous_engine()
    status = engine.get_status()

    health_status = "healthy" if status.get("running", False) else "stopped"

    return {
        "status": health_status,
        "engine_running": status.get("running", False),
        "queue_size": status.get("queue_size", 0),
        "active_rules": status.get("active_rules", 0),
        "total_processed": status.get("total_processed", 0),
        "total_failed": status.get("total_failed", 0)
    }
