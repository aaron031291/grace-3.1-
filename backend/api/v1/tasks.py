"""v1/tasks — Tasks, scheduling, TimeSense"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/tasks", tags=["v1 Tasks"])
BASE = "http://localhost:8000"


class TaskSubmit(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    task_type: str = "user_request"

class TaskSchedule(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    scheduled_for: str
    repeat: Optional[str] = None


@router.get("/live")
async def live():
    import requests as req
    return req.get(f"{BASE}/api/tasks-hub/live", timeout=10).json()

@router.get("/active")
async def active():
    import requests as req
    return req.get(f"{BASE}/api/tasks-hub/active", timeout=10).json()

@router.get("/history")
async def history(limit: int = 50):
    import requests as req
    return req.get(f"{BASE}/api/tasks-hub/history?limit={limit}", timeout=10).json()

@router.post("")
async def submit(request: TaskSubmit):
    import requests as req
    return req.post(f"{BASE}/api/tasks-hub/submit", json=request.model_dump(), timeout=10).json()

@router.get("/scheduled")
async def scheduled():
    import requests as req
    return req.get(f"{BASE}/api/tasks-hub/scheduled", timeout=10).json()

@router.post("/scheduled")
async def schedule(request: TaskSchedule):
    import requests as req
    return req.post(f"{BASE}/api/tasks-hub/schedule", json=request.model_dump(), timeout=10).json()

@router.delete("/scheduled/{task_id}")
async def cancel_scheduled(task_id: str):
    import requests as req
    return req.delete(f"{BASE}/api/tasks-hub/scheduled/{task_id}", timeout=10).json()

@router.post("/scheduled/{task_id}/run")
async def run_now(task_id: str):
    import requests as req
    return req.post(f"{BASE}/api/tasks-hub/scheduled/{task_id}/run", timeout=10).json()

@router.get("/time-sense")
async def time_sense():
    import requests as req
    return req.get(f"{BASE}/api/tasks-hub/time-sense", timeout=10).json()
