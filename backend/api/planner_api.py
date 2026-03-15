"""
Planner API — wired to LLM through GovernanceAwareLLM + Spindle.

Plan generation uses the governance-wrapped LLM so all governance rules
and persona are injected into every planning response. All actions
tracked via Genesis Keys and published to Spindle event bus.
"""

import uuid
import datetime
import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/planner", tags=["Planner API"])

# In-memory session store
sessions_db = {}


def _emit(topic: str, data: dict):
    try:
        from cognitive.event_bus import publish_async
        publish_async(topic, data, source="planner_api")
    except Exception:
        pass


def _track(what: str, tags: list = None):
    try:
        from api._genesis_tracker import track
        track(key_type="ai_response", what=what, who="planner_api",
              tags=["planner", "plan"] + (tags or []))
    except Exception:
        pass


def _generate_plan_via_llm(goal: str) -> list:
    """Generate plan phases using GovernanceAwareLLM — all rules enforced."""
    try:
        from llm_orchestrator.factory import get_llm_for_task
        client = get_llm_for_task("reason")  # Uses Qwen 3 or fallback
        
        prompt = (
            f"Generate a concise implementation plan for the following goal:\n\n"
            f"Goal: {goal}\n\n"
            f"Return 3-5 phases, each with a title, description, and 2-3 tasks.\n"
            f"Format each phase as:\n"
            f"PHASE: [title]\n"
            f"DESC: [description]\n"
            f"TASK: [task 1]\n"
            f"TASK: [task 2]\n"
        )
        
        response = client.generate(
            prompt=prompt,
            system_prompt="You are Grace's planning engine. Generate actionable, specific plans.",
            temperature=0.3,
            max_tokens=1000,
        )
        
        # Parse response into structured phases
        phases = []
        current_phase = None
        
        if isinstance(response, str):
            for line in response.split("\n"):
                line = line.strip()
                if line.startswith("PHASE:"):
                    if current_phase:
                        phases.append(current_phase)
                    current_phase = {
                        "id": f"PHASE-{len(phases)+1}",
                        "title": line[6:].strip(),
                        "description": "",
                        "status": "pending",
                        "tasks": [],
                    }
                elif line.startswith("DESC:") and current_phase:
                    current_phase["description"] = line[5:].strip()
                elif line.startswith("TASK:") and current_phase:
                    current_phase["tasks"].append({
                        "title": line[5:].strip(),
                        "status": "pending",
                    })
            if current_phase:
                phases.append(current_phase)
        
        # If parsing failed, create a single phase with the raw response
        if not phases:
            phases = [{
                "id": "PHASE-1",
                "title": "Implementation Plan",
                "description": response[:500] if isinstance(response, str) else str(response)[:500],
                "status": "pending",
                "tasks": [{"title": "Execute plan", "status": "pending"}],
            }]
        
        return phases
    except Exception as e:
        logger.warning(f"[PLANNER] LLM plan generation failed: {e}")
        # Fallback: basic plan structure without LLM
        return [{
            "id": "PHASE-1",
            "title": "Initial Setup",
            "description": f"Prepare the environment for: {goal}",
            "status": "pending",
            "tasks": [
                {"title": "Analyze requirements", "status": "pending"},
                {"title": "Set up environment", "status": "pending"},
            ]
        }, {
            "id": "PHASE-2",
            "title": "Implementation",
            "description": f"Execute the core work for: {goal}",
            "status": "pending",
            "tasks": [
                {"title": "Implement core logic", "status": "pending"},
                {"title": "Test and verify", "status": "pending"},
            ]
        }]


@router.get("/sessions")
async def get_sessions():
    """Return all active planning sessions."""
    return {"sessions": list(sessions_db.values())}


@router.post("/generate")
async def generate_plan(payload: dict):
    """Generate a plan using GovernanceAwareLLM — all governance rules applied."""
    sid = f"PLAN-{uuid.uuid4().hex[:8]}"
    goal = payload.get("goal", "Empty Goal")
    
    _track(f"Generate plan: {goal[:60]}", tags=["generate"])
    
    # Generate via LLM with governance wrapper
    phases = _generate_plan_via_llm(goal)
    
    session = {
        "id": sid,
        "goal": goal,
        "status": "completed",
        "progress": 100,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "phases": phases,
    }
    sessions_db[sid] = session
    
    _emit("planner.plan_generated", {
        "session_id": sid, "goal": goal[:100],
        "phases": len(phases),
    })
    
    return session


@router.post("/refine")
async def refine_plan(payload: dict):
    """Refine plan using GovernanceAwareLLM with feedback context."""
    sid = payload.get("sessionId")
    if not sid or sid not in sessions_db:
        return {"error": "Session not found"}
    
    feedback = payload.get("feedback", "")
    session = sessions_db[sid]
    
    _track(f"Refine plan {sid}: {feedback[:40]}", tags=["refine"])
    
    # Generate refinement via LLM
    try:
        from llm_orchestrator.factory import get_llm_for_task
        client = get_llm_for_task("reason")
        
        current_plan = "\n".join([f"- {p['title']}: {p['description']}" for p in session["phases"]])
        prompt = (
            f"Current plan for '{session['goal']}':\n{current_plan}\n\n"
            f"Feedback: {feedback}\n\n"
            f"Generate 1-2 additional phases to address this feedback.\n"
            f"Format: PHASE: [title]\\nDESC: [desc]\\nTASK: [task]"
        )
        
        response = client.generate(prompt=prompt, temperature=0.3, max_tokens=500)
        
        # Parse new phases
        if isinstance(response, str):
            for line in response.split("\n"):
                if line.strip().startswith("PHASE:"):
                    new_phase = {
                        "id": f"PHASE-{len(session['phases'])+1}",
                        "title": line.strip()[6:].strip(),
                        "description": f"Refined from feedback: {feedback[:100]}",
                        "status": "pending",
                        "tasks": [{"title": "Apply feedback", "status": "pending"}],
                    }
                    session["phases"].append(new_phase)
    except Exception as e:
        # Fallback: add generic refinement phase
        session["phases"].append({
            "id": f"PHASE-{len(session['phases'])+1}",
            "title": "Refinement",
            "description": f"Refined from feedback: {feedback}",
            "status": "pending",
            "tasks": [{"title": "Apply feedback", "status": "pending"}],
        })
    
    _emit("planner.plan_refined", {"session_id": sid, "feedback": feedback[:100]})
    return session


@router.get("/session/{sid}")
async def get_session(sid: str):
    """Load specific session details."""
    if sid in sessions_db:
        return sessions_db[sid]
    return {"error": "Not Found"}
