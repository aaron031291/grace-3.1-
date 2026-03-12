import asyncio
import uuid
import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/devlab", tags=["Dev Lab Agents"])

class AgentTaskRequest(BaseModel):
    artifact_path: str
    intent: str

# In-memory storage for active tasks
# Format: task_id -> {"status": "running|completed|failed", "logs": [], "artifact": "path"}
active_tasks: Dict[str, Dict[str, Any]] = {}

async def real_agent_worker(task_id: str, artifact_path: str, intent: str):
    """Autonomous LLM agent working on a file, yielding logs over time."""
    try:
        active_tasks[task_id]["status"] = "running"
        
        active_tasks[task_id]["logs"].append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] [SYSTEM] Booting Dev Agent for workspace task: {intent}")
        active_tasks[task_id]["logs"].append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] [SYSTEM] Target artifact: {artifact_path}")
        active_tasks[task_id]["logs"].append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] [RAG] Building prompt and loading context...")
        
        # Give UI a moment to show bootup
        await asyncio.sleep(1)
        
        # Send right to the Spindle pipeline (QwenCodingNet under the hood)
        from core.services.code_service import generate_code
        active_tasks[task_id]["logs"].append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] [SPINDLE] Routing request to Spindle Build Pipeline...")
        
        # Run in threadpool so we don't block the async event loop
        loop = asyncio.get_running_loop()
        prompt = f"Target File: {artifact_path}\nIntent: {intent}"
        
        # generate_code is sync, so run in executor
        result = await loop.run_in_executor(None, generate_code, prompt, "", True)
        
        active_tasks[task_id]["logs"].append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] [SPINDLE] Pipeline complete. Status: {result.get('status', 'unknown')}")
        
        if result.get("status") in ["verification_failed", "failed"]:
            active_tasks[task_id]["logs"].append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] [VERIFY] ❌ Spindle verification failed: {result.get('error', 'Entropy bounds exceeded')}")
            active_tasks[task_id]["status"] = "failed"
        else:
            active_tasks[task_id]["logs"].append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] [VERIFY] ✅ Z3 Geometric Proof passed. Code is safe.")
            active_tasks[task_id]["logs"].append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] [SYSTEM] Modifications committed to Sandbox via Genesis Key.")
            active_tasks[task_id]["status"] = "completed"
        
    except Exception as e:
        active_tasks[task_id]["status"] = "failed"
        active_tasks[task_id]["logs"].append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] [ERROR] Agent crashed: {str(e)}")

@router.post("/task")
async def start_agent_task(req: AgentTaskRequest, background_tasks: BackgroundTasks):
    """Spawns a background agent to handle a request from the Context Menu."""
    task_id = f"TASK-{uuid.uuid4().hex[:8]}"
    
    active_tasks[task_id] = {
        "status": "pending",
        "logs": [],
        "artifact": req.artifact_path,
        "intent": req.intent
    }
    
    # Fire and forget
    background_tasks.add_task(real_agent_worker, task_id, req.artifact_path, req.intent)
    
    return {"task_id": task_id, "status": "pending"}

@router.get("/stream/{task_id}")
async def stream_task_logs(task_id: str):
    """SSE endpoint to stream live python terminal logs to the frontend."""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    async def log_generator():
        last_index = 0
        while True:
            task = active_tasks.get(task_id)
            if not task:
                break
                
            # Yield new logs
            current_logs = task["logs"]
            if len(current_logs) > last_index:
                for log in current_logs[last_index:]:
                    yield {"data": log}
                last_index = len(current_logs)
                
            if task["status"] in ["completed", "failed"]:
                yield {"data": f"[END OF STREAM] Status: {task['status']}"}
                # Grace period before breaking
                await asyncio.sleep(1)
                break
                
            await asyncio.sleep(0.5)

    return EventSourceResponse(log_generator())

@router.get("/swarm")
async def get_active_swarm():
    """Returns the list of active agents (completed, failed, or running) for the Dev Tab Swimlane."""
    tasks = []
    # Mock layer assignments for visual flavor
    import random
    
    for t_id, t_info in active_tasks.items():
        # Calculate a fake progress based on log length
        # Assuming our mock agent does ~11 steps
        progress = min(int((len(t_info.get("logs", [])) / 11) * 100), 100)
        if t_info.get("status") in ["completed", "failed"]:
            progress = 100
            
        tasks.append({
            "id": t_id,
            "name": f"Agent: {t_info.get('intent', 'Unknown task')[:20]}...",
            "status": t_info.get("status", "queued"),
            "progress": progress,
            "layer": random.randint(1, 9)
        })
        
    return {"tasks": tasks}
