"""
Tasks Hub API — Real-time system activity + user task submission + scheduling

Shows what Grace is doing right now, lets users suggest tasks,
and supports scheduled tasks for later execution.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks-hub", tags=["Tasks Hub"])

SCHEDULED_FILE = None


def _sched_path():
    from pathlib import Path
    p = Path(__file__).parent.parent / "data" / "scheduled_tasks.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_scheduled() -> List[Dict]:
    p = _sched_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return []


def _save_scheduled(data: List[Dict]):
    _sched_path().write_text(json.dumps(data, indent=2, default=str))


def _get_db():
    from database.session import SessionLocal
    if SessionLocal is None:
        from database.session import initialize_session_factory
        initialize_session_factory()
        from database.session import SessionLocal as SL
        return SL()
    return SessionLocal()


class TaskSubmit(BaseModel):
    title: str
    description: Optional[str] = ""
    priority: str = "medium"  # low, medium, high, critical
    task_type: str = "user_request"  # user_request, learning, healing, ingestion, analysis


class TaskSchedule(BaseModel):
    title: str
    description: Optional[str] = ""
    priority: str = "medium"
    task_type: str = "user_request"
    scheduled_for: str  # ISO datetime
    repeat: Optional[str] = None  # once, daily, weekly, monthly


# ---------------------------------------------------------------------------
# 1. Real-time activity — what Grace is doing right now
# ---------------------------------------------------------------------------

@router.get("/live")
async def get_live_activity():
    """Real-time view of what Grace is doing in the background."""
    from sqlalchemy import text

    result: Dict[str, Any] = {"timestamp": datetime.utcnow().isoformat(), "activities": []}

    db = _get_db()
    try:
        # Recent genesis keys (last 5 minutes = live activity)
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        try:
            rows = db.execute(text("""
                SELECT key_id, key_type, what_description, who_actor, when_timestamp, file_path, tags
                FROM genesis_key
                WHERE when_timestamp >= :cutoff
                ORDER BY when_timestamp DESC
                LIMIT 30
            """), {"cutoff": cutoff}).fetchall()

            for r in rows:
                tags = r[6]
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except Exception:
                        tags = []
                result["activities"].append({
                    "id": r[0],
                    "type": r[1].value if hasattr(r[1], 'value') else str(r[1]),
                    "what": r[2],
                    "who": r[3],
                    "timestamp": r[4].isoformat() if r[4] else None,
                    "file_path": r[5],
                    "tags": tags or [],
                    "source": "genesis_key",
                })
        except Exception:
            pass

        # Active tasks from todos
        try:
            from api.grace_todos_api import tasks_store
            for tid, task in tasks_store.items():
                if task.status.value in ("running", "queued", "scheduled"):
                    result["activities"].append({
                        "id": tid,
                        "type": "task",
                        "what": task.title,
                        "who": "grace",
                        "timestamp": task.created_at.isoformat() if task.created_at else None,
                        "status": task.status.value,
                        "progress": task.progress_percent,
                        "source": "task_store",
                    })
        except Exception:
            pass

        # System metrics snapshot
        try:
            import psutil
            result["system"] = {
                "cpu": psutil.cpu_percent(interval=0.1),
                "memory": psutil.virtual_memory().percent,
            }
        except Exception:
            pass

        result["activity_count"] = len(result["activities"])

    finally:
        db.close()

    return result


@router.get("/history")
async def get_task_history(limit: int = 50):
    """Recent task history — completed and failed tasks."""
    from sqlalchemy import text
    db = _get_db()
    try:
        # Recent genesis keys (broader window)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        try:
            rows = db.execute(text("""
                SELECT key_id, key_type, what_description, who_actor, when_timestamp, is_error
                FROM genesis_key
                WHERE when_timestamp >= :cutoff
                ORDER BY when_timestamp DESC
                LIMIT :lim
            """), {"cutoff": cutoff, "lim": limit}).fetchall()

            return {"total": len(rows), "history": [
                {
                    "id": r[0],
                    "type": r[1].value if hasattr(r[1], 'value') else str(r[1]),
                    "what": r[2], "who": r[3],
                    "timestamp": r[4].isoformat() if r[4] else None,
                    "is_error": r[5],
                }
                for r in rows
            ]}
        except Exception:
            return {"total": 0, "history": []}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 2. Submit a task — user suggests what Grace should do
# ---------------------------------------------------------------------------

@router.post("/submit")
async def submit_task(request: TaskSubmit, background_tasks: BackgroundTasks):
    """Submit a task for Grace to work on. Links throughout the system."""
    try:
        from api.grace_todos_api import GraceTask, TaskStatus, TaskPriority, TaskType, tasks_store

        priority_map = {"low": TaskPriority.LOW, "medium": TaskPriority.MEDIUM,
                        "high": TaskPriority.HIGH, "critical": TaskPriority.CRITICAL}
        type_map = {"user_request": TaskType.USER_REQUEST, "learning": TaskType.LEARNING,
                    "healing": TaskType.HEALING, "ingestion": TaskType.INGESTION,
                    "analysis": TaskType.ANALYSIS}

        task = GraceTask(
            title=request.title,
            description=request.description,
            genesis_key_id=f"task-{uuid.uuid4().hex[:8]}",
            priority=priority_map.get(request.priority, TaskPriority.MEDIUM),
            task_type=type_map.get(request.task_type, TaskType.USER_REQUEST),
            status=TaskStatus.QUEUED,
        )
        tasks_store[task.genesis_key_id] = task

        from api._genesis_tracker import track
        track(key_type="system",
              what=f"Task submitted: {request.title}",
              how="POST /api/tasks-hub/submit",
              input_data={"title": request.title, "type": request.task_type, "priority": request.priority},
              tags=["task", "submit", request.task_type])

        return {
            "submitted": True,
            "task_id": task.genesis_key_id,
            "title": request.title,
            "status": "queued",
            "priority": request.priority,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_tasks():
    """Get all active (non-completed) tasks."""
    try:
        from api.grace_todos_api import tasks_store
        active = []
        for tid, task in tasks_store.items():
            active.append({
                "id": tid,
                "title": task.title,
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority.value,
                "type": task.task_type.value,
                "progress": task.progress_percent,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            })
        active.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["priority"], 4))
        return {"total": len(active), "tasks": active}
    except Exception:
        return {"total": 0, "tasks": []}


# ---------------------------------------------------------------------------
# 3. Scheduled tasks — run later
# ---------------------------------------------------------------------------

@router.get("/scheduled")
async def get_scheduled_tasks():
    """Get all scheduled tasks."""
    tasks = _load_scheduled()
    now = datetime.utcnow().isoformat()
    for t in tasks:
        if t["status"] == "scheduled" and t["scheduled_for"] <= now:
            t["status"] = "overdue"
    return {"total": len(tasks), "tasks": tasks}


@router.post("/schedule")
async def schedule_task(request: TaskSchedule):
    """Schedule a task for later execution."""
    tasks = _load_scheduled()

    task = {
        "id": f"sched-{uuid.uuid4().hex[:8]}",
        "title": request.title,
        "description": request.description,
        "priority": request.priority,
        "task_type": request.task_type,
        "scheduled_for": request.scheduled_for,
        "repeat": request.repeat,
        "status": "scheduled",
        "created_at": datetime.utcnow().isoformat(),
    }
    tasks.append(task)
    _save_scheduled(tasks)

    from api._genesis_tracker import track
    track(key_type="system",
          what=f"Task scheduled: {request.title} for {request.scheduled_for}",
          how="POST /api/tasks-hub/schedule",
          tags=["task", "schedule", request.task_type])

    return {"scheduled": True, **task}


@router.delete("/scheduled/{task_id}")
async def delete_scheduled_task(task_id: str):
    """Cancel a scheduled task."""
    tasks = _load_scheduled()
    tasks = [t for t in tasks if t["id"] != task_id]
    _save_scheduled(tasks)
    return {"deleted": True, "id": task_id}


@router.post("/scheduled/{task_id}/run")
async def run_scheduled_now(task_id: str, background_tasks: BackgroundTasks):
    """Execute a scheduled task immediately."""
    tasks = _load_scheduled()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task["status"] = "running"
    _save_scheduled(tasks)

    submit_req = TaskSubmit(title=task["title"], description=task.get("description", ""),
                            priority=task.get("priority", "medium"), task_type=task.get("task_type", "user_request"))
    result = await submit_task(submit_req, background_tasks)
    return {**result, "scheduled_id": task_id}
