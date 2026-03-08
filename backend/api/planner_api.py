import uuid
import datetime
import json
import logging
from fastapi import APIRouter
from llm_orchestrator.factory import get_llm_for_task

router = APIRouter(prefix="/api/planner", tags=["Planner API"])
logger = logging.getLogger(__name__)

# Mock store for sessions
sessions_db = {}

@router.get("/sessions")
async def get_sessions():
    """Return a list of active planning sessions."""
    return {"sessions": list(sessions_db.values())}

@router.post("/generate")
async def generate_plan(payload: dict):
    """Accept a goal and begin generating a multi-step engineering plan."""
    sid = f"PLAN-{uuid.uuid4().hex[:8]}"
    goal = payload.get("goal", "Empty Goal")
    
    # 1. Ask the reasoning LLM to structurally break down the task
    reasoning_llm = get_llm_for_task("reason")
    
    prompt = f"""
You are an elite Software Architecture Agent handling an engineering goal: "{goal}"
Break the goal down into 2-5 distinct 'phases'. Every phase should have 1-3 'tasks'.
Return EXCLUSIVELY a raw JSON array matching this exact format, without markdown blocks or backticks:
[
  {{
    "id": "PHASE-1",
    "title": "Phase Name",
    "description": "What this phase does",
    "status": "pending",
    "tasks": [
       {{"title": "Task 1 description", "status": "pending"}}
    ]
  }}
]
"""
    try:
        raw_json_str = reasoning_llm.chat(messages=[{"role": "user", "content": prompt}])
        # Strip markdown if the LLM ignored instructions
        if raw_json_str.strip().startswith("```"):
            raw_json_str = raw_json_str.strip().split("\n", 1)[1].rsplit("\n", 1)[0]
        if raw_json_str.strip().startswith("json"):
            raw_json_str = raw_json_str.strip()[4:]
            
        phases = json.loads(raw_json_str)
    except Exception as e:
        logger.error(f"Planner generation failed: {e}")
        phases = [
            {
                "id": "PHASE-1",
                "title": "Initial Setup",
                "description": f"Prepare the environment for {goal}",
                "status": "pending",
                "tasks": [{"title": "Setup repository", "status": "pending"}]
            }
        ]

    session = {
        "id": sid,
        "goal": goal,
        "status": "completed",
        "progress": 100,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "phases": phases
    }
    sessions_db[sid] = session
    return session

@router.post("/refine")
async def refine_plan(payload: dict):
    """Refine an existing plan session based on human feedback."""
    sid = payload.get("sessionId")
    if not sid or sid not in sessions_db:
        return {"error": "Session not found"}
        
    feedback = payload.get("feedback", "")
    session = sessions_db[sid]
    
    # Send existing phases + feedback to reasoning LLM
    reasoning_llm = get_llm_for_task("reason")
    prompt = f"""
We have an existing engineering plan with these phases:
{json.dumps(session['phases'], indent=2)}

The user provided the following feedback to explicitly adjust the plan: "{feedback}"
Generate ONE additional phase object answering to this feedback.
Return EXCLUSIVELY a raw JSON object (no array, no markdown):
{{
  "id": "PHASE-X",
  "title": "Refinement based on feedback",
  "description": "What this phase does",
  "status": "pending",
  "tasks": [
     {{"title": "Task description", "status": "pending"}}
  ]
}}
"""
    try:
        raw_json_str = reasoning_llm.chat(messages=[{"role": "user", "content": prompt}])
        if raw_json_str.strip().startswith("```"):
            raw_json_str = raw_json_str.strip().split("\n", 1)[1].rsplit("\n", 1)[0]
        if raw_json_str.strip().startswith("json"):
            raw_json_str = raw_json_str.strip()[4:]
            
        new_phase = json.loads(raw_json_str)
        # Ensure ID is unique
        new_phase["id"] = f"PHASE-{len(session['phases']) + 1}"
    except Exception as e:
        logger.error(f"Planner refinement failed: {e}")
        new_phase = {
            "id": f"PHASE-{len(session['phases']) + 1}",
            "title": "Refinement",
            "description": f"Refined from feedback: {feedback}",
            "status": "pending",
            "tasks": [{"title": "Apply feedback", "status": "pending"}]
        }
        
    session["phases"].append(new_phase)
    return session

@router.get("/session/{sid}")
async def get_session(sid: str):
    """Load specific session details."""
    if sid in sessions_db:
        return sessions_db[sid]
    return {"error": "Not Found"}
