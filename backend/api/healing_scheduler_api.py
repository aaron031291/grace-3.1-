"""
Healing Scheduler API - REST endpoints for scheduler management.

Provides endpoints for:
- Scheduler status and control
- Healing queue management
- Task submission and monitoring
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/healing-scheduler", tags=["Healing Scheduler"])


class TaskRequest(BaseModel):
    """Request to add a healing task."""
    task_type: str = Field(..., description="Type: heal_anomaly, code_fix, proactive_scan")
    priority: str = Field("medium", description="Priority: critical, high, medium, low, background")
    description: str = Field("", description="Task description")
    file_path: Optional[str] = Field(None, description="File path for file-specific tasks")
    anomaly_data: Optional[dict] = Field(None, description="Anomaly data for healing")


class TaskResponse(BaseModel):
    """Response for a healing task."""
    task_id: str
    task_type: str
    priority: str
    status: str
    description: str
    file_path: Optional[str]
    created_at: str
    retry_count: int


class SchedulerStatusResponse(BaseModel):
    """Scheduler status response."""
    running: bool
    pending_tasks: int
    total_tasks: int
    file_watcher_active: bool
    schedules: dict


class QueueStatsResponse(BaseModel):
    """Queue statistics response."""
    pending: int
    in_progress: int
    completed: int
    failed: int
    retrying: int


def _get_scheduler():
    """Get the healing scheduler."""
    from cognitive.healing_scheduler import get_healing_scheduler
    return get_healing_scheduler()


def _get_priority(priority_str: str):
    """Convert string to HealingPriority."""
    from cognitive.healing_scheduler import HealingPriority
    priority_map = {
        "critical": HealingPriority.CRITICAL,
        "high": HealingPriority.HIGH,
        "medium": HealingPriority.MEDIUM,
        "low": HealingPriority.LOW,
        "background": HealingPriority.BACKGROUND,
    }
    return priority_map.get(priority_str.lower(), HealingPriority.MEDIUM)


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status():
    """Get the healing scheduler status."""
    try:
        scheduler = _get_scheduler()
        status = scheduler.get_status()
        
        return SchedulerStatusResponse(
            running=status["running"],
            pending_tasks=status["pending_tasks"],
            total_tasks=status["total_tasks"],
            file_watcher_active=status["file_watcher_active"],
            schedules=status["schedules"],
        )
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_scheduler():
    """Start the healing scheduler."""
    try:
        scheduler = _get_scheduler()
        scheduler.start()
        return {"success": True, "message": "Scheduler started"}
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_scheduler():
    """Stop the healing scheduler."""
    try:
        scheduler = _get_scheduler()
        scheduler.stop()
        return {"success": True, "message": "Scheduler stopped"}
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Stop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats():
    """Get healing queue statistics."""
    try:
        scheduler = _get_scheduler()
        tasks = scheduler.queue.get_all_tasks()
        
        from cognitive.healing_scheduler import HealingTaskStatus
        
        stats = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0,
            "retrying": 0,
        }
        
        for task in tasks:
            if task.status == HealingTaskStatus.PENDING:
                stats["pending"] += 1
            elif task.status == HealingTaskStatus.IN_PROGRESS:
                stats["in_progress"] += 1
            elif task.status == HealingTaskStatus.COMPLETED:
                stats["completed"] += 1
            elif task.status == HealingTaskStatus.FAILED:
                stats["failed"] += 1
            elif task.status == HealingTaskStatus.RETRYING:
                stats["retrying"] += 1
        
        return QueueStatsResponse(**stats)
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Queue stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue/tasks", response_model=List[TaskResponse])
async def get_queue_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Max tasks to return"),
):
    """Get tasks from the healing queue."""
    try:
        scheduler = _get_scheduler()
        tasks = scheduler.queue.get_all_tasks()
        
        if status:
            from cognitive.healing_scheduler import HealingTaskStatus
            try:
                filter_status = HealingTaskStatus(status)
                tasks = [t for t in tasks if t.status == filter_status]
            except ValueError:
                pass
        
        # Sort by priority and created_at
        tasks = sorted(tasks, key=lambda t: (t.priority.value, t.created_at))[:limit]
        
        return [
            TaskResponse(
                task_id=t.task_id,
                task_type=t.task_type,
                priority=t.priority.name.lower(),
                status=t.status.value,
                description=t.description,
                file_path=t.file_path,
                created_at=t.created_at.isoformat(),
                retry_count=t.retry_count,
            )
            for t in tasks
        ]
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Get tasks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/queue/tasks", response_model=TaskResponse)
async def add_task(request: TaskRequest):
    """Add a task to the healing queue."""
    try:
        scheduler = _get_scheduler()
        priority = _get_priority(request.priority)
        
        task_id = scheduler.add_healing_task(
            task_type=request.task_type,
            priority=priority,
            description=request.description,
            file_path=request.file_path,
            anomaly_data=request.anomaly_data,
        )
        
        # Get the task we just added
        from cognitive.healing_scheduler import HealingTaskStatus
        from datetime import datetime
        
        return TaskResponse(
            task_id=task_id,
            task_type=request.task_type,
            priority=request.priority,
            status=HealingTaskStatus.PENDING.value,
            description=request.description,
            file_path=request.file_path,
            created_at=datetime.now().isoformat(),
            retry_count=0,
        )
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Add task error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/queue/completed")
async def clear_completed_tasks(
    older_than_hours: int = Query(24, description="Clear tasks older than this many hours"),
):
    """Clear completed tasks from the queue."""
    try:
        scheduler = _get_scheduler()
        scheduler.queue.clear_completed(older_than_hours=older_than_hours)
        return {"success": True, "message": f"Cleared completed tasks older than {older_than_hours} hours"}
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Clear completed error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/health-check")
async def trigger_health_check():
    """Manually trigger a health check."""
    try:
        scheduler = _get_scheduler()
        scheduler._run_health_check()
        return {"success": True, "message": "Health check triggered"}
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Trigger health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/proactive-scan")
async def trigger_proactive_scan():
    """Manually trigger a proactive scan."""
    try:
        scheduler = _get_scheduler()
        scheduler._run_proactive_scan()
        return {"success": True, "message": "Proactive scan triggered"}
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Trigger proactive scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/drift-detection")
async def trigger_drift_detection():
    """Manually trigger drift detection."""
    try:
        scheduler = _get_scheduler()
        scheduler._run_drift_detection()
        return {"success": True, "message": "Drift detection triggered"}
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Trigger drift detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Alert Endpoints ====================

class AlertRequest(BaseModel):
    """Request to send an alert."""
    severity: str = Field(..., description="Severity: info, warning, error, critical")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    details: Optional[dict] = Field(None, description="Additional details")


class AlertResponse(BaseModel):
    """Response for an alert."""
    alert_id: str
    severity: str
    title: str
    message: str
    sent: bool
    created_at: str


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(limit: int = Query(50, description="Max alerts to return")):
    """Get recent diagnostic alerts."""
    try:
        scheduler = _get_scheduler()
        alerts = scheduler.get_recent_alerts(limit=limit)
        
        return [
            AlertResponse(
                alert_id=a.alert_id,
                severity=a.severity.value,
                title=a.title,
                message=a.message,
                sent=a.sent,
                created_at=a.created_at.isoformat(),
            )
            for a in alerts
        ]
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Get alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts", response_model=AlertResponse)
async def send_alert(request: AlertRequest):
    """Send a diagnostic alert."""
    try:
        from cognitive.healing_scheduler import AlertSeverity
        
        severity_map = {
            "info": AlertSeverity.INFO,
            "warning": AlertSeverity.WARNING,
            "error": AlertSeverity.ERROR,
            "critical": AlertSeverity.CRITICAL,
        }
        
        severity = severity_map.get(request.severity.lower(), AlertSeverity.INFO)
        
        scheduler = _get_scheduler()
        alert = scheduler.send_alert(
            severity=severity,
            title=request.title,
            message=request.message,
            details=request.details,
            source="api",
        )
        
        if alert:
            return AlertResponse(
                alert_id=alert.alert_id,
                severity=alert.severity.value,
                title=alert.title,
                message=alert.message,
                sent=alert.sent,
                created_at=alert.created_at.isoformat(),
            )
        else:
            raise HTTPException(status_code=400, detail="Alerts are disabled")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Send alert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/channels")
async def get_configured_channels():
    """Get list of configured notification channels."""
    try:
        from diagnostic_machine.notifications import get_notification_manager
        
        manager = get_notification_manager()
        channels = manager.get_configured_channels()
        
        return {
            "configured_channels": channels,
            "available_channels": ["webhook", "slack", "email", "console"],
            "message": f"{len(channels)} channels configured",
        }
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Get channels error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/test")
async def test_alerts():
    """Send a test alert to all configured channels."""
    try:
        scheduler = _get_scheduler()
        
        alert = scheduler.send_alert(
            severity=scheduler.AlertSeverity.INFO if hasattr(scheduler, 'AlertSeverity') else None,
            title="Test Alert",
            message="This is a test alert from the GRACE self-healing system.",
            details={"test": True, "timestamp": datetime.now().isoformat()},
            source="test",
        )
        
        # Fallback if AlertSeverity not accessible
        if alert is None:
            from cognitive.healing_scheduler import AlertSeverity
            alert = scheduler.send_alert(
                severity=AlertSeverity.INFO,
                title="Test Alert", 
                message="This is a test alert from the GRACE self-healing system.",
                details={"test": True},
                source="test",
            )
        
        if alert:
            return {
                "success": True,
                "alert_id": alert.alert_id,
                "sent": alert.sent,
                "message": "Test alert sent" if alert.sent else "Test alert created but delivery may have failed",
            }
        else:
            return {"success": False, "message": "Alerts are disabled"}
            
    except Exception as e:
        logger.error(f"[SCHEDULER-API] Test alert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
