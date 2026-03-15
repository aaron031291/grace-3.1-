"""
Healing Swarm API — REST endpoints for the concurrent healing swarm.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/api/healing-swarm", tags=["Healing Swarm"])


class SwarmProblem(BaseModel):
    component: str
    description: str = ""
    error: str = ""
    severity: str = "medium"
    file_path: str = ""
    context: dict = {}


class SwarmBatchRequest(BaseModel):
    problems: List[SwarmProblem]


@router.get("/status")
async def get_swarm_status():
    """Full swarm status: agent states, active tasks, recent results."""
    try:
        from cognitive.healing_swarm import get_healing_swarm
        swarm = get_healing_swarm()
        return {"ok": True, **swarm.get_status()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/submit")
async def submit_problem(problem: SwarmProblem):
    """Submit a single problem for concurrent healing."""
    try:
        from cognitive.healing_swarm import get_healing_swarm
        swarm = get_healing_swarm()
        task_id = swarm.submit(problem.model_dump())
        return {"ok": True, "task_id": task_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/submit-batch")
async def submit_batch(req: SwarmBatchRequest):
    """Submit multiple problems — all heal concurrently."""
    try:
        from cognitive.healing_swarm import get_healing_swarm
        swarm = get_healing_swarm()
        task_ids = swarm.submit_batch([p.model_dump() for p in req.problems])
        return {"ok": True, "task_ids": task_ids, "dispatched": len(task_ids)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/heal-all")
async def heal_all_detected():
    """Detect all current problems and dispatch swarm agents to fix them all at once."""
    try:
        from cognitive.healing_swarm import get_healing_swarm
        swarm = get_healing_swarm()
        problems = []

        # Check Qdrant
        try:
            from vector_db.client import get_qdrant_client
            get_qdrant_client().get_collections()
        except Exception as e:
            problems.append({"component": "qdrant", "description": "Qdrant not responding", "error": str(e), "severity": "high"})

        # Check database
        try:
            from database.session import session_scope
            with session_scope() as s:
                s.execute("SELECT 1" if hasattr(s, 'execute') else None)
        except Exception as e:
            problems.append({"component": "database", "description": "Database connection failed", "error": str(e), "severity": "high"})

        # Check Ollama
        try:
            import httpx
            r = httpx.get("http://localhost:11434/api/tags", timeout=3)
            if r.status_code != 200:
                problems.append({"component": "ollama", "description": "Ollama not responding", "severity": "medium"})
        except Exception as e:
            problems.append({"component": "ollama", "description": "Ollama unreachable", "error": str(e), "severity": "medium"})

        # Check brain domains trust
        try:
            from ml_intelligence.kpi_tracker import get_kpi_tracker
            tracker = get_kpi_tracker()
            health = tracker.get_system_health()
            for name, info in health.get("components", {}).items():
                trust = info.get("trust_score", 0)
                if trust < 0.3:
                    problems.append({"component": name, "description": f"Trust critically low: {trust}", "severity": "high"})
        except Exception:
            pass

        # Check memory
        try:
            import psutil
            mem = psutil.virtual_memory()
            if mem.percent > 90:
                problems.append({"component": "memory", "description": f"Memory at {mem.percent}%", "severity": "critical"})
        except Exception:
            pass

        if not problems:
            return {"ok": True, "message": "No problems detected", "dispatched": 0}

        task_ids = swarm.submit_batch(problems)
        return {"ok": True, "problems_found": len(problems), "dispatched": len(task_ids), "task_ids": task_ids}
    except Exception as e:
        return {"ok": False, "error": str(e)}
