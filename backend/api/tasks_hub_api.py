from fastapi import APIRouter
import datetime
import uuid
import psutil
from coding_agent import task_queue

router = APIRouter(prefix="/tasks-hub", tags=["Tasks Hub"])

# Mock store for scheduled tasks
scheduled_db = {}

@router.get("/active")
async def get_active_tasks():
    # Return real swarm status from the coding agent
    return {"tasks": task_queue.get_swarm_status()}

@router.get("/live")
async def get_live_activity():
    # Get total queued tasks + CPU stats
    queue_status = task_queue.get_status()
    total_active = queue_status.get("by_status", {}).get("running", 0) + queue_status.get("by_status", {}).get("pending", 0)
    
    return {
        "activity_count": total_active,
        "activities": [
            {"id": t["task_id"], "title": t["instructions"][:50], "time": t["updated_at"]}
            for t in task_queue._queue[-10:] if t["status"] in ["running", "completed", "failed"]
        ],
        "system": {
            "cpu": psutil.cpu_percent(),
            "memory": psutil.virtual_memory().percent
        }
    }

@router.get("/history")
async def get_history(limit: int = 40):
    completed = [
        {"id": t["task_id"], "title": t["instructions"][:50], "status": t["status"], "time": t["updated_at"]}
        for t in reversed(task_queue._queue) if t["status"] in ["completed", "failed"]
    ]
    return {"history": completed[:limit]}

@router.get("/time-sense")
async def get_time_sense():
    now = datetime.datetime.now()
    try:
        from cognitive.time_sense import TimeSense
        time_ctx = TimeSense.now_context()
        period_label = time_ctx.get("period", "Day").capitalize()
        is_business = time_ctx.get("is_business_hours", False)
    except:
        period_label = "Day"
        is_business = 9 <= now.hour < 17
        
    return {
        "now": {
            "day_of_week": now.strftime("%A"),
            "period_label": period_label,
            "time": now.strftime("%H:%M:%S"),
            "is_business_hours": is_business
        },
        "activity_pattern": {
            "peak_hour": "14:00",
            "peak_day": "Wednesday"
        },
        "upcoming_tasks": []
    }

@router.post("/submit")
async def submit_task(task: dict):
    return {"status": "success", "message": "Task received"}

@router.get("/scheduled")
async def get_scheduled_tasks():
    return {"tasks": list(scheduled_db.values())}

@router.post("/schedule")
async def schedule_task(payload: dict):
    tid = f"TASK-{uuid.uuid4().hex[:8]}"
    task = {
        "id": tid,
        "title": payload.get("title", "New Task"),
        "status": "scheduled",
        "next_run": (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat()
    }
    scheduled_db[tid] = task
    return task

@router.delete("/scheduled/{id}")
async def delete_scheduled_task(id: str):
    if id in scheduled_db:
        del scheduled_db[id]
    return {"status": "deleted"}

@router.post("/scheduled/{id}/run")
async def run_scheduled_task(id: str):
    if id in scheduled_db:
        scheduled_db[id]["status"] = "running"
        scheduled_db[id]["last_run"] = datetime.datetime.now().isoformat()
    return {"status": "running"}
