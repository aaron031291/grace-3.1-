import asyncio
import uuid
import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/devlab", tags=["Dev Lab Agents"])

from coding_agent import task_queue
from pydantic import BaseModel

class AgentTaskRequest(BaseModel):
    artifact_path: str
    intent: str
    domain: str = "Global"

@router.post("/task")
async def start_agent_task(req: AgentTaskRequest):
    """Spawns a background agent to handle a request from the Context Menu."""
    # Ensure worker thread is running
    task_queue.start_worker()
    
    # Submit real task
    task_id = task_queue.submit(
        task_type="devlab_refactor",
        instructions=req.intent,
        context={"target_file": req.artifact_path, "domain": req.domain},
        priority=3,
        origin="devlab_ui"
    )
    
    return {"task_id": task_id, "status": "pending"}

@router.get("/stream/{task_id}")
async def stream_task_logs(task_id: str):
    """SSE endpoint to stream live python terminal logs to the frontend."""

    async def log_generator():
        yield {"data": f"[SYSTEM] Checking queue for {task_id}..."}
        
        reported_status = None
        while True:
            # Look up task in real queue
            task_status = "unknown"
            for t in task_queue._queue:
                if t["task_id"] == task_id:
                    task_status = t["status"]
                    break
                    
            if task_status != reported_status:
                reported_status = task_status
                yield {"data": f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] Swarm Status Update: {task_status.upper()}"}
                
                if task_status == "running":
                    yield {"data": "[AGENT] Qwen 2.5 Coder has picked up the task and is processing..."}
                elif task_status == "completed":
                    yield {"data": "[VERIFY] Code generated, verified through RAG, and applied to disk successfully. ✅"}
                    yield {"data": f"[END OF STREAM] Status: {task_status}"}
                    break
                elif task_status == "failed":
                    yield {"data": "[ERROR] Agent failed to complete the task or was blocked by the Governance Gate. ❌"}
                    yield {"data": f"[END OF STREAM] Status: {task_status}"}
                    break
                    
            await asyncio.sleep(1.0)

    return EventSourceResponse(log_generator())

@router.get("/swarm")
async def get_active_swarm():
    """Returns the list of active agents for the Dev Tab Swimlane using the real Qwen Task Queue."""
    return {"tasks": task_queue.get_swarm_status()}
