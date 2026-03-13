from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict, Any

router = APIRouter(prefix="/api/test/stress", tags=["Stress Testing"])

# Global state for simple asynchronous stress test tracking
_stress_test_status = {
    "is_running": False,
    "last_run": None,
    "results": None
}

def _run_stress_test_background():
    """Background task to run the actual stress test."""
    global _stress_test_status
    _stress_test_status["is_running"] = True
    
    try:
        from cognitive.deep_test_engine import DeepTestEngine
        engine = DeepTestEngine.get_instance()
        results = engine.run_logic_tests()
        
        _stress_test_status["results"] = results
    except Exception as e:
        _stress_test_status["results"] = {"error": str(e)}
    finally:
        _stress_test_status["is_running"] = False
        import datetime
        from datetime import timezone
        _stress_test_status["last_run"] = datetime.datetime.now(timezone.utc).isoformat()

@router.post("/start")
async def start_stress_test(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Start a stress test asynchronously if one isn't already running."""
    global _stress_test_status
    
    if _stress_test_status["is_running"]:
        raise HTTPException(status_code=400, detail="A stress test is already running.")
        
    background_tasks.add_task(_run_stress_test_background)
    return {"message": "Stress test started in background"}

@router.post("/stop")
async def stop_stress_test() -> Dict[str, Any]:
    """Placeholder for stopping a stress test (if engine supports interruption)."""
    global _stress_test_status
    
    if not _stress_test_status["is_running"]:
        return {"message": "No stress test is currently running."}
        
    # DeepTestEngine doesn't natively support async interruption yet, 
    # so we just acknowledge the request.
    return {"message": "Stop requested (may take time to halt current checks)."}

@router.get("/status")
async def get_stress_test_status() -> Dict[str, Any]:
    """Get the current running status and last results of stress testing."""
    return _stress_test_status
