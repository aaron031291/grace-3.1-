from fastapi import APIRouter
import datetime
import uuid

router = APIRouter(prefix="/tasks-hub", tags=["Tasks Hub"])

# Mock store for scheduled tasks
scheduled_db = {}
@router.get("/active")
async def get_active_tasks():
    return {"tasks": []}

@router.get("/live")
async def get_live_activity():
    return {
        "activity_count": 0,
        "activities": [],
        "system": {
            "cpu": 0,
            "memory": 0
        }
    }

@router.get("/history")
async def get_history(limit: int = 40):
    return {"history": []}

@router.get("/time-sense")
async def get_time_sense():
    now = datetime.datetime.now()
    return {
        "now": {
            "day_of_week": now.strftime("%A"),
            "period_label": "Day",
            "time": now.strftime("%H:%M:%S"),
            "is_business_hours": 9 <= now.hour < 17
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
