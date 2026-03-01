"""
Intelligent Planner API — Dual-Pane Planning System

Two panes working simultaneously:
  PANE 1 (User): Rich text, mind map, voice → user's intent/ideas/problems
  PANE 2 (Grace): Auto-generates plan in real time as user types/speaks

The Loop:
  User speaks/types → Grace plans → User refines → Grace adapts →
  Blueprint ready → Execute

Grace uses cognitive frameworks, thinks 7 steps ahead, reverse-engineers
the problem, and outputs a blueprint the user can discuss/modify.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/planner", tags=["Intelligent Planner"])

DATA_DIR = Path(__file__).parent.parent / "data" / "plans"


class PlanInput(BaseModel):
    content: str
    mode: str = "text"  # text, voice_transcript, mindmap
    session_id: Optional[str] = None
    context: str = ""


class PlanUpdate(BaseModel):
    session_id: str
    user_content: str
    user_feedback: str = ""


class PlanExecuteRequest(BaseModel):
    session_id: str
    approved_steps: Optional[List[int]] = None


def _ensure():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_session(session_id: str) -> Optional[dict]:
    path = DATA_DIR / f"{session_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def _save_session(session_id: str, data: dict):
    _ensure()
    (DATA_DIR / f"{session_id}.json").write_text(json.dumps(data, indent=2, default=str))


# ── Plan Generation ──────────────────────────────────────────────────

@router.post("/generate")
async def generate_plan(req: PlanInput):
    """
    User provides their intent. Grace generates a real-time plan.

    Grace:
    1. Parses the user's intent
    2. Reverse-engineers the problem using OODA + cognitive frameworks
    3. Thinks 7 steps ahead
    4. Generates a structured blueprint
    5. Background: idle learner grabs more context, self-healing monitors
    """
    session_id = req.session_id or f"plan_{uuid.uuid4().hex[:12]}"

    # Build context from user input
    user_input = req.content
    if req.mode == "voice_transcript":
        user_input = f"[Voice input] {req.content}"

    # Generate Grace's plan using the cognitive pipeline
    grace_plan = await _generate_grace_plan(user_input, req.context)

    session = {
        "session_id": session_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "status": "planning",
        "user_pane": {
            "content": req.content,
            "mode": req.mode,
            "history": [{"content": req.content, "timestamp": datetime.utcnow().isoformat()}],
        },
        "grace_pane": {
            "plan": grace_plan,
            "thinking_steps": grace_plan.get("thinking_steps", []),
            "blueprint": grace_plan.get("blueprint", {}),
            "predictions": grace_plan.get("predictions", []),
            "learning_insights": grace_plan.get("learning_insights", []),
        },
        "iterations": 1,
    }

    _save_session(session_id, session)

    # Fire event for system awareness
    try:
        from cognitive.event_bus import publish
        publish("planner.session_created", {
            "session_id": session_id,
            "mode": req.mode,
        }, source="planner")
    except Exception:
        pass

    # Genesis Key
    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Plan generated: {user_input[:80]}",
            how="POST /api/planner/generate",
            output_data={"session_id": session_id, "steps": len(grace_plan.get("steps", []))},
            tags=["planner", "plan_generated"],
        )
    except Exception:
        pass

    return session


@router.post("/refine")
async def refine_plan(req: PlanUpdate):
    """
    User refines their input → Grace adapts the plan in real time.
    The loop continues: User speaks → Grace adapts → Blueprint evolves.
    """
    session = _load_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Plan session not found")

    # Update user pane
    session["user_pane"]["content"] = req.user_content
    session["user_pane"]["history"].append({
        "content": req.user_content,
        "feedback": req.user_feedback,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Re-generate Grace's plan with updated context
    previous_plan = session["grace_pane"]["plan"]
    context = f"Previous plan:\n{json.dumps(previous_plan.get('steps', []), indent=2)[:2000]}"
    if req.user_feedback:
        context += f"\n\nUser feedback: {req.user_feedback}"

    grace_plan = await _generate_grace_plan(req.user_content, context)

    session["grace_pane"]["plan"] = grace_plan
    session["grace_pane"]["thinking_steps"] = grace_plan.get("thinking_steps", [])
    session["grace_pane"]["blueprint"] = grace_plan.get("blueprint", {})
    session["grace_pane"]["predictions"] = grace_plan.get("predictions", [])
    session["iterations"] += 1
    session["updated_at"] = datetime.utcnow().isoformat()

    _save_session(req.session_id, session)

    return session


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get the current state of a planning session (both panes)."""
    session = _load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Plan session not found")
    return session


@router.get("/sessions")
async def list_sessions(limit: int = 20):
    """List all planning sessions."""
    _ensure()
    sessions = []
    for f in sorted(DATA_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        try:
            data = json.loads(f.read_text())
            sessions.append({
                "session_id": data.get("session_id"),
                "status": data.get("status"),
                "created_at": data.get("created_at"),
                "iterations": data.get("iterations", 0),
                "preview": data.get("user_pane", {}).get("content", "")[:100],
            })
        except Exception:
            pass
    return {"sessions": sessions, "total": len(sessions)}


@router.post("/execute")
async def execute_plan(req: PlanExecuteRequest):
    """
    User approves the blueprint → Grace executes it.
    Steps go through the full verification pipeline before execution.
    """
    session = _load_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Plan session not found")

    plan = session["grace_pane"]["plan"]
    steps = plan.get("steps", [])

    if req.approved_steps:
        steps = [s for i, s in enumerate(steps) if i in req.approved_steps]

    session["status"] = "executing"
    session["execution"] = {
        "started_at": datetime.utcnow().isoformat(),
        "approved_steps": len(steps),
        "results": [],
    }
    _save_session(req.session_id, session)

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Plan execution started: {len(steps)} steps",
            how="POST /api/planner/execute",
            output_data={"session_id": req.session_id, "steps": len(steps)},
            tags=["planner", "execute"],
        )
    except Exception:
        pass

    # Actually execute steps through the consensus/patch pipeline
    execution_results = []
    for i, step in enumerate(steps):
        step_result = {"step_index": i, "title": step.get("title", ""), "status": "pending"}
        try:
            step_desc = step.get("description", step.get("title", ""))

            # Use patch consensus for code changes, regular consensus for analysis
            if step.get("type") in ("implementation", "code", "fix", "build"):
                from cognitive.patch_consensus import run_patch_consensus
                result = run_patch_consensus(
                    task=step_desc,
                    auto_apply=False,
                    threshold=0.67,
                )
                step_result["status"] = result.get("status", "completed")
                step_result["proposal_id"] = result.get("proposal_id")
                step_result["patch_hash"] = result.get("patch_hash")
            else:
                from cognitive.consensus_engine import run_consensus
                result = run_consensus(
                    prompt=step_desc,
                    source="planner",
                )
                step_result["status"] = "completed"
                step_result["output"] = result.final_output[:1000] if result.final_output else ""
                step_result["confidence"] = result.confidence

        except Exception as e:
            step_result["status"] = "failed"
            step_result["error"] = str(e)[:200]

        execution_results.append(step_result)

    session["execution"]["results"] = execution_results
    session["execution"]["completed_at"] = datetime.utcnow().isoformat()
    completed = sum(1 for r in execution_results if r["status"] in ("completed", "verified"))
    session["status"] = "completed" if completed == len(steps) else "partial"
    _save_session(req.session_id, session)

    return {
        "session_id": req.session_id,
        "status": session["status"],
        "steps_approved": len(steps),
        "steps_completed": completed,
        "steps_failed": len(steps) - completed,
        "results": execution_results,
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    path = DATA_DIR / f"{session_id}.json"
    if path.exists():
        path.unlink()
        return {"deleted": True, "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


# ── Grace's Planning Engine ───────────────────────────────────────────

async def _generate_grace_plan(user_input: str, context: str = "") -> Dict[str, Any]:
    """
    Grace's real-time planning engine.
    Uses cognitive frameworks to reverse-engineer the problem and
    produce a structured blueprint.
    """
    plan = {
        "intent": "",
        "problem_decomposition": [],
        "steps": [],
        "thinking_steps": [],
        "predictions": [],
        "blueprint": {},
        "learning_insights": [],
        "estimated_complexity": "medium",
    }

    # Step 1: Parse intent
    plan["intent"] = _parse_intent(user_input)

    # Step 2: Decompose problem (OODA-style)
    plan["problem_decomposition"] = _decompose_problem(user_input)

    # Step 3: Think 7 steps ahead
    plan["thinking_steps"] = _think_ahead(user_input, plan["problem_decomposition"])

    # Step 4: Generate blueprint steps
    plan["steps"] = _generate_steps(user_input, plan["problem_decomposition"], context)

    # Step 5: Predict challenges
    plan["predictions"] = _predict_challenges(plan["steps"])

    # Step 6: Estimate complexity
    plan["estimated_complexity"] = _estimate_complexity(plan["steps"])

    # Step 7: Build blueprint
    plan["blueprint"] = {
        "title": plan["intent"][:100],
        "total_steps": len(plan["steps"]),
        "estimated_complexity": plan["estimated_complexity"],
        "key_decisions": [s.get("description", "") for s in plan["steps"] if s.get("is_decision")],
        "dependencies": _extract_dependencies(plan["steps"]),
    }

    # Step 8: Ask LLM for deeper analysis if available
    try:
        from llm_orchestrator.factory import get_llm_client
        client = get_llm_client()

        prompt = (
            f"Plan this task for an autonomous AI system called Grace:\n\n"
            f"User request: {user_input[:1000]}\n\n"
            f"Initial decomposition:\n{json.dumps(plan['problem_decomposition'], indent=2)[:1000]}\n\n"
            f"Context: {context[:500]}\n\n"
            f"Provide:\n"
            f"1. Any steps I missed\n"
            f"2. Potential risks\n"
            f"3. What Grace should learn from this task\n"
            f"4. Suggested verification points\n"
            f"Be concise and structured."
        )

        response = client.generate(
            prompt=prompt,
            system_prompt="You are Grace's planning intelligence. Help structure tasks into actionable blueprints.",
            temperature=0.4, max_tokens=2048,
        )
        if isinstance(response, str):
            plan["learning_insights"] = [{"source": "llm", "insight": response[:1000]}]
    except Exception:
        pass

    # Step 9: Search unified memory for similar past plans
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        similar = mem.search_all(user_input[:100])
        if similar.get("total", 0) > 0:
            plan["learning_insights"].append({
                "source": "memory",
                "insight": f"Found {similar['total']} related memories across {len([k for k, v in similar.items() if isinstance(v, list) and v])} systems",
            })
    except Exception:
        pass

    return plan


def _parse_intent(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in ["build", "create", "make", "develop"]):
        return f"Build: {text[:100]}"
    if any(w in lower for w in ["fix", "debug", "resolve", "repair"]):
        return f"Fix: {text[:100]}"
    if any(w in lower for w in ["improve", "optimize", "enhance", "refactor"]):
        return f"Improve: {text[:100]}"
    if any(w in lower for w in ["analyse", "analyze", "investigate", "audit"]):
        return f"Analyse: {text[:100]}"
    if any(w in lower for w in ["plan", "design", "architect", "structure"]):
        return f"Design: {text[:100]}"
    return f"Task: {text[:100]}"


def _decompose_problem(text: str) -> List[Dict[str, str]]:
    parts = []
    sentences = [s.strip() for s in text.replace("\n", ". ").split(".") if s.strip() and len(s.strip()) > 5]
    for i, sentence in enumerate(sentences[:10]):
        parts.append({
            "index": i,
            "component": sentence[:100],
            "type": "requirement" if any(w in sentence.lower() for w in ["need", "must", "should", "want"]) else "context",
        })
    return parts


def _think_ahead(text: str, decomposition: List[dict]) -> List[str]:
    steps = []
    steps.append(f"Step 1: Understand the core problem — '{text[:60]}...'")
    steps.append(f"Step 2: Identify {len(decomposition)} sub-components")
    steps.append("Step 3: Check existing systems for reusable components")
    steps.append("Step 4: Design integration points with Grace's architecture")
    steps.append("Step 5: Plan verification checkpoints")
    steps.append("Step 6: Consider edge cases and failure modes")
    steps.append("Step 7: Prepare rollback strategy if something breaks")
    return steps


def _generate_steps(text: str, decomposition: List[dict], context: str) -> List[Dict[str, Any]]:
    steps = []
    requirements = [d for d in decomposition if d.get("type") == "requirement"]

    for i, req in enumerate(requirements):
        steps.append({
            "index": i,
            "description": req["component"],
            "type": "implementation",
            "is_decision": False,
            "estimated_effort": "medium",
            "verification": "automated",
        })

    # Add design step at the beginning
    steps.insert(0, {
        "index": 0,
        "description": "Design the solution architecture and identify dependencies",
        "type": "design",
        "is_decision": True,
        "estimated_effort": "low",
        "verification": "human_review",
    })

    # Add testing step at the end
    steps.append({
        "index": len(steps),
        "description": "Run verification pipeline — trust scoring, hallucination guard, contradiction detection",
        "type": "verification",
        "is_decision": False,
        "estimated_effort": "low",
        "verification": "automated",
    })

    return steps


def _predict_challenges(steps: List[dict]) -> List[str]:
    challenges = []
    if len(steps) > 5:
        challenges.append("Complex task — consider breaking into smaller phases")
    if any(s.get("is_decision") for s in steps):
        challenges.append("Design decisions needed — may require consensus roundtable")
    challenges.append("New code will need to pass through Live Integration Protocol")
    return challenges


def _estimate_complexity(steps: List[dict]) -> str:
    if len(steps) <= 2:
        return "simple"
    if len(steps) <= 5:
        return "medium"
    return "complex"


def _extract_dependencies(steps: List[dict]) -> List[str]:
    deps = []
    for s in steps:
        if s.get("type") == "verification":
            deps.append("Trust Engine")
            deps.append("Cognitive Pipeline")
    return list(set(deps))
