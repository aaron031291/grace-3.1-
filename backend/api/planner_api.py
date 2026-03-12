import uuid
import datetime
from fastapi import APIRouter

router = APIRouter(prefix="/api/planner", tags=["Planner API"])

# Mock store for sessions
sessions_db = {}

@router.get("/sessions")
async def get_sessions():
    """Return a list of active planning sessions."""
    return {"sessions": list(sessions_db.values())}

@router.post("/generate")
async def generate_plan(payload: dict):
    """Accept a goal and begin generating a plan."""
    sid = f"PLAN-{uuid.uuid4().hex[:8]}"
    goal = payload.get("goal", "Empty Goal")
    session = {
        "id": sid,
        "goal": goal,
        "status": "completed",
        "progress": 100,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "phases": [
            {
                "id": "PHASE-1",
                "title": "Initial Setup",
                "description": f"Prepare the environment for {goal}",
                "status": "pending",
                "tasks": [{"title": "Setup repository", "status": "pending"}]
            }
        ]

    }
    sessions_db[sid] = session
    return session

@router.post("/refine")
async def refine_plan(payload: dict):
    """Refine an existing plan session."""
    sid = payload.get("sessionId")
    if not sid or sid not in sessions_db:
        return {"error": "Session not found"}
    feedback = payload.get("feedback", "")
    session = sessions_db[sid]
    session["phases"].append({
        "id": f"PHASE-{len(session['phases']) + 1}",
        "title": "Refinement",
        "description": f"Refined from feedback: {feedback}",
        "status": "pending",
        "tasks": [{"title": "Apply feedback", "status": "pending"}]
    })
    return session

@router.get("/session/{sid}")
async def get_session(sid: str):
    """Load specific session details."""
    if sid in sessions_db:
        return sessions_db[sid]
    return {"error": "Not Found"}
