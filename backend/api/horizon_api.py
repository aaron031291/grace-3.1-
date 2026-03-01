"""
Horizon API — Long-Term Goals, Sandbox Mirror, Integration Gaps

The one-stop shop for Grace's strategic planning and self-improvement:
- Set long-term goals with reverse-engineered milestones
- Mirror Grace's full system into a sandbox
- Run diagnostics, experiments, learning cycles
- Detect integration gaps
- Track measurable progress (30%+ improvement targets)
- Dual branches: internal fixes + exploration
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/horizon", tags=["Horizon Planner & Sandbox"])


# ── Models ────────────────────────────────────────────────────────────

class GoalRequest(BaseModel):
    title: str
    description: str
    target_outcome: str
    target_improvement_pct: float = 30.0
    timeline_days: int = 60
    branch: str = "internal"
    use_consensus: bool = True


class TaskUpdateRequest(BaseModel):
    goal_id: str
    task_id: str
    status: str
    current_value: Optional[float] = None
    result: Optional[str] = None


class SandboxRequest(BaseModel):
    goal_id: Optional[str] = None
    branch: str = "internal"


class ExperimentRequest(BaseModel):
    session_id: Optional[str] = None
    task: str
    use_consensus: bool = True


class LearningRequest(BaseModel):
    session_id: Optional[str] = None
    focus: str = "internal"


class FixClassifyRequest(BaseModel):
    problem: str
    component: str = ""
    error_frequency: int = 0
    system_impact: str = "low"


# ── Goal Endpoints ────────────────────────────────────────────────────

@router.post("/goals")
async def create_goal(req: GoalRequest):
    """
    Create a long-term goal and reverse-engineer it into milestones + tasks.
    Uses consensus (Opus + Kimi) to decompose, falls back to heuristics.
    """
    from cognitive.horizon_planner import reverse_engineer_goal
    try:
        goal = reverse_engineer_goal(
            title=req.title,
            description=req.description,
            target_outcome=req.target_outcome,
            target_improvement_pct=req.target_improvement_pct,
            timeline_days=req.timeline_days,
            branch=req.branch,
            use_consensus=req.use_consensus,
        )
        return {
            "goal_id": goal.id,
            "title": goal.title,
            "milestones": len(goal.milestones),
            "tasks": len(goal.tasks),
            "timeline_days": goal.timeline_days,
            "target": goal.measurable_target,
            "branch": goal.branch,
            "baseline_metrics": goal.baseline_metrics,
            "task_breakdown": {
                t.size: sum(1 for x in goal.tasks if x.size == t.size)
                for t in goal.tasks
            },
        }
    except Exception as e:
        logger.error(f"Goal creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goals")
async def list_goals(status: Optional[str] = None):
    """List all horizon goals."""
    from cognitive.horizon_planner import list_goals
    return {"goals": list_goals(status=status)}


@router.get("/goals/{goal_id}")
async def get_goal(goal_id: str):
    """Get full goal details including milestones and tasks."""
    from cognitive.horizon_planner import load_goal
    goal = load_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    from dataclasses import asdict
    return asdict(goal)


@router.post("/goals/{goal_id}/activate")
async def activate_goal(goal_id: str):
    """Activate a goal and start the timeline clock."""
    from cognitive.horizon_planner import activate_goal
    goal = activate_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {
        "goal_id": goal.id,
        "status": goal.status,
        "started_at": goal.started_at,
        "deadline": goal.deadline,
    }


@router.get("/goals/{goal_id}/progress")
async def check_progress(goal_id: str):
    """Check goal progress with measurable improvements."""
    from cognitive.horizon_planner import check_goal_progress
    return check_goal_progress(goal_id)


@router.post("/goals/task-update")
async def update_task(req: TaskUpdateRequest):
    """Update a task's status and measurement value."""
    from cognitive.horizon_planner import update_task_status
    task = update_task_status(
        req.goal_id, req.task_id,
        req.status, req.current_value, req.result,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Goal or task not found")
    from dataclasses import asdict
    return asdict(task)


# ── Fix Classification ────────────────────────────────────────────────

@router.post("/classify-fix")
async def classify_fix(req: FixClassifyRequest):
    """
    Classify whether a problem needs a quick fix (1-2 days) or a longer timeline.
    Returns size, estimated days, measurement period, and whether consensus is needed.
    """
    from cognitive.horizon_planner import classify_fix as _classify
    return _classify(
        problem=req.problem,
        component=req.component,
        error_frequency=req.error_frequency,
        system_impact=req.system_impact,
    )


# ── Sandbox Mirror ────────────────────────────────────────────────────

@router.post("/sandbox/create")
async def create_sandbox(req: SandboxRequest):
    """
    Create a sandbox mirror session. Mirrors Grace's full backend:
    diagnostics, memory mesh, self-healing, genesis keys — the whole shebang.
    """
    from cognitive.sandbox_mirror import get_sandbox_mirror
    mirror = get_sandbox_mirror()
    session = mirror.create_session(goal_id=req.goal_id, branch=req.branch)
    return {
        "session_id": session.id,
        "components_mirrored": len(session.components_mirrored),
        "health_baseline": session.health_baseline.get("overall_status", "unknown"),
        "branch": session.branch,
    }


@router.post("/sandbox/diagnostics")
async def run_diagnostics(session_id: Optional[str] = None):
    """Run full diagnostics in the sandbox."""
    from cognitive.sandbox_mirror import get_sandbox_mirror
    mirror = get_sandbox_mirror()
    return mirror.run_diagnostics(session_id)


@router.post("/sandbox/experiment")
async def run_experiment(req: ExperimentRequest):
    """Run an experiment in the sandbox using consensus mechanism."""
    from cognitive.sandbox_mirror import get_sandbox_mirror
    mirror = get_sandbox_mirror()
    return mirror.run_experiment(
        session_id=req.session_id,
        task_description=req.task,
        use_consensus=req.use_consensus,
    )


@router.post("/sandbox/learn")
async def run_learning(req: LearningRequest):
    """Run a learning cycle in the sandbox (internal fixes or exploration)."""
    from cognitive.sandbox_mirror import get_sandbox_mirror
    mirror = get_sandbox_mirror()
    return mirror.run_learning_cycle(session_id=req.session_id, focus=req.focus)


@router.get("/sandbox/sessions")
async def list_sessions(limit: int = 20):
    """List sandbox sessions."""
    from cognitive.sandbox_mirror import get_sandbox_mirror
    mirror = get_sandbox_mirror()
    return {"sessions": mirror.list_sessions(limit=limit)}


@router.get("/sandbox/{session_id}")
async def get_session(session_id: str):
    """Get sandbox session summary."""
    from cognitive.sandbox_mirror import get_sandbox_mirror
    mirror = get_sandbox_mirror()
    return mirror.get_session_summary(session_id)


@router.post("/sandbox/{session_id}/close")
async def close_session(session_id: str):
    """Close a sandbox session and get the final report."""
    from cognitive.sandbox_mirror import get_sandbox_mirror
    mirror = get_sandbox_mirror()
    return mirror.close_session(session_id)


# ── Integration Gaps ──────────────────────────────────────────────────

@router.get("/gaps")
async def get_integration_gaps():
    """Detect all integration gaps in the system."""
    from cognitive.integration_gap_detector import get_gap_summary
    return get_gap_summary()


@router.get("/gaps/unregistered-apis")
async def get_unregistered_apis():
    """Find API files that exist but aren't registered in app.py."""
    from cognitive.integration_gap_detector import detect_unregistered_apis
    gaps = detect_unregistered_apis()
    return {"gaps": gaps, "total": len(gaps)}


@router.get("/gaps/event-bus")
async def get_event_bus_gaps():
    """Find event topics published without subscribers."""
    from cognitive.integration_gap_detector import detect_event_bus_gaps
    gaps = detect_event_bus_gaps()
    return {"gaps": gaps, "total": len(gaps)}


# ── Forensic Audit ────────────────────────────────────────────────────

@router.get("/forensic-audit")
async def run_forensic_audit():
    """
    Run a deep forensic audit of all Grace systems.
    Returns the truth about what's connected vs ghost code.
    No hallucinations — just real import tests and schema checks.
    """
    from cognitive.forensic_audit import run_full_audit
    return run_full_audit()


@router.get("/verify")
async def run_verification():
    """
    Run integration verification tests.
    Every claim is TESTED — imports, schemas, function signatures.
    Returns pass/fail rate with evidence for each test.
    """
    from cognitive.integration_verifier import run_integration_tests
    return run_integration_tests()
