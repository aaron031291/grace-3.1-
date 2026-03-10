import asyncio
import uuid
import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/sandbox", tags=["Sandbox Engine"])

active_experiments: Dict[str, Dict[str, Any]] = {}

class SandboxExperimentRequest(BaseModel):
    hypothesis: str
    target_sources: List[str]
    domain: str = "Global"

async def mock_sandbox_worker(experiment_id: str, hypothesis: str, target_sources: List[str]):
    """Simulates querying the Whitelist sources in a read-only dry-run."""
    try:
        active_experiments[experiment_id]["status"] = "running"
        
        steps = [
            f"[SANDBOX] Booting Isolated Inference Engine...",
            f"[SANDBOX] Hypothesis: \"{hypothesis}\"",
            f"[ROUTING] Targeting {len(target_sources)} Whitelist sources...",
        ]
        for src in target_sources:
             steps.append(f"[FETCHING] Reading data from {src} (Read-Only)...")
             
        steps.extend([
            f"[ANALYSIS] Synthesizing external RAG context...",
            f"[ANALYSIS] Found 4 verified data points matching hypothesis.",
            f"[SYSTEM] Compiling Sandbox Discovery Report.",
            f"[SYSTEM] ⚠️ WARNING: These findings exist ONLY in the Sandbox overlay. They have not been committed to Magma Memory.",
            f"[SYSTEM] Experiment complete. Awaiting Human Promotion."
        ])
        
        for step in steps:
            await asyncio.sleep(1.2)
            log_entry = f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')}] {step}"
            active_experiments[experiment_id]["logs"].append(log_entry)
            
        active_experiments[experiment_id]["status"] = "completed"
        
    except Exception as e:
        active_experiments[experiment_id]["status"] = "failed"
        active_experiments[experiment_id]["logs"].append(f"[ERROR] Sandbox crashed: {str(e)}")

@router.post("/experiment")
async def start_sandbox_experiment(req: SandboxExperimentRequest, background_tasks: BackgroundTasks):
    """Spawns an isolated experiment."""
    exp_id = f"EXP-{uuid.uuid4().hex[:8]}"
    
    active_experiments[exp_id] = {
        "status": "pending",
        "logs": [],
        "hypothesis": req.hypothesis
    }
    
    background_tasks.add_task(mock_sandbox_worker, exp_id, req.hypothesis, req.target_sources)
    return {"experiment_id": exp_id, "status": "pending"}

@router.get("/stream/{experiment_id}")
async def stream_experiment_logs(experiment_id: str):
    """SSE endpoint to stream sandbox logs to the UI."""
    if experiment_id not in active_experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")

    async def log_generator():
        last_index = 0
        while True:
            exp = active_experiments.get(experiment_id)
            if not exp:
                break
                
            current_logs = exp["logs"]
            if len(current_logs) > last_index:
                for log in current_logs[last_index:]:
                    yield {"data": log}
                last_index = len(current_logs)
                
            if exp["status"] in ["completed", "failed"]:
                yield {"data": f"[END OF STREAM] Status: {exp['status']}"}
                await asyncio.sleep(1)
                break
                
            await asyncio.sleep(0.5)

    return EventSourceResponse(log_generator())
