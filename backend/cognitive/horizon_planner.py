"""
Horizon Planner — Long-Term Goal Setting & Reverse Engineering

Grace's strategic brain. Sets goals, reverse-engineers them into executable
milestones, classifies fix complexity, tracks measurable success over 60-day
horizons, and manages dual branches: internal-world fixes + exploration.

Flow:
1. Set a long-term goal (e.g. "30% faster response times")
2. Reverse-engineer into milestones → tasks → experiments
3. Classify each task: quick-fix (1-2 days) vs deep-fix (weeks/months)
4. Run through sandbox mirror — nothing touches production
5. Track measurable outcomes (30%+ improvement required)
6. Two parallel branches:
   a. Internal: fix Grace's own systems, healing loops, bottlenecks
   b. Exploration: research, whitelist data, build new capabilities

Timeline: 60 days default, but smart enough to know when a 2-day fix is enough.
"""

import json
import hashlib
import logging
import time
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

HORIZON_DIR = Path(__file__).parent.parent / "data" / "horizon_plans"


class GoalStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    MEASURING = "measuring"
    ACHIEVED = "achieved"
    FAILED = "failed"
    PAUSED = "paused"


class TaskSize(str, Enum):
    QUICK_FIX = "quick_fix"       # 1-2 days
    SMALL = "small"               # 3-7 days
    MEDIUM = "medium"             # 1-4 weeks
    LARGE = "large"               # 1-2 months
    EPIC = "epic"                 # 2+ months


class BranchType(str, Enum):
    INTERNAL = "internal"         # Fix Grace's own systems
    EXPLORATION = "exploration"   # Research, learning, building new things


@dataclass
class Milestone:
    id: str
    title: str
    description: str
    target_metric: str
    target_value: float
    baseline_value: float = 0.0
    current_value: float = 0.0
    unit: str = "%"
    deadline_days: int = 14
    status: str = "pending"
    tasks: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    @property
    def progress_pct(self) -> float:
        if self.target_value == self.baseline_value:
            return 100.0
        return min(100.0, max(0.0,
            (self.current_value - self.baseline_value) /
            (self.target_value - self.baseline_value) * 100
        ))


@dataclass
class HorizonTask:
    id: str
    milestone_id: str
    title: str
    description: str
    branch: str  # internal or exploration
    size: str  # quick_fix, small, medium, large, epic
    estimated_days: int = 1
    priority: int = 5  # 1=highest, 10=lowest
    status: str = "pending"
    experiment_id: Optional[str] = None
    success_metric: str = ""
    success_threshold: float = 30.0  # 30% improvement minimum
    baseline_value: float = 0.0
    current_value: float = 0.0
    fix_applied: bool = False
    measuring_since: Optional[str] = None
    measurement_days: int = 14
    result: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    consensus_proposal_id: Optional[str] = None


@dataclass
class HorizonGoal:
    id: str
    title: str
    description: str
    target_outcome: str
    measurable_target: str
    target_improvement_pct: float = 30.0
    timeline_days: int = 60
    status: str = GoalStatus.DRAFT
    branch: str = BranchType.INTERNAL
    milestones: List[Milestone] = field(default_factory=list)
    tasks: List[HorizonTask] = field(default_factory=list)
    baseline_metrics: Dict[str, float] = field(default_factory=dict)
    current_metrics: Dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    deadline: Optional[str] = None
    completed_at: Optional[str] = None
    genesis_key_id: Optional[str] = None


# ── Goal Reverse Engineering ──────────────────────────────────────────

def reverse_engineer_goal(
    title: str,
    description: str,
    target_outcome: str,
    target_improvement_pct: float = 30.0,
    timeline_days: int = 60,
    branch: str = BranchType.INTERNAL,
    use_consensus: bool = True,
) -> HorizonGoal:
    """
    Take a high-level goal and reverse-engineer it into milestones and tasks.
    Uses consensus mechanism (Opus + Kimi) if available, falls back to heuristics.
    """
    goal = HorizonGoal(
        id=f"HG-{uuid.uuid4().hex[:12]}",
        title=title,
        description=description,
        target_outcome=target_outcome,
        measurable_target=f"{target_improvement_pct}% improvement in {target_outcome}",
        target_improvement_pct=target_improvement_pct,
        timeline_days=timeline_days,
        branch=branch,
    )

    if use_consensus:
        try:
            milestones, tasks = _consensus_decompose(goal)
            goal.milestones = milestones
            goal.tasks = tasks
        except Exception as e:
            logger.warning(f"Consensus decomposition failed, using heuristic: {e}")
            milestones, tasks = _heuristic_decompose(goal)
            goal.milestones = milestones
            goal.tasks = tasks
    else:
        milestones, tasks = _heuristic_decompose(goal)
        goal.milestones = milestones
        goal.tasks = tasks

    _collect_baselines(goal)
    _save_goal(goal)

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Horizon goal created: {title}",
            how="horizon_planner.reverse_engineer_goal",
            output_data={
                "goal_id": goal.id,
                "milestones": len(goal.milestones),
                "tasks": len(goal.tasks),
                "timeline_days": timeline_days,
                "target_improvement": target_improvement_pct,
                "branch": branch,
            },
            tags=["horizon", "goal", "planning", branch],
        )
    except Exception:
        pass

    return goal


def _consensus_decompose(goal: HorizonGoal) -> Tuple[List[Milestone], List[HorizonTask]]:
    """Use Opus + Kimi to decompose a goal into milestones and tasks."""
    from cognitive.consensus_engine import layer1_deliberate, _check_model_available

    system_prompt = (
        "You are a project planner. Decompose a goal into milestones and tasks.\n"
        "Output ONLY valid JSON with this structure:\n"
        '{"milestones": [{"title": "...", "description": "...", "target_metric": "...", '
        '"target_value": 30, "deadline_days": 14}], '
        '"tasks": [{"title": "...", "description": "...", "milestone_index": 0, '
        '"size": "quick_fix|small|medium|large", "estimated_days": 2, '
        '"priority": 3, "branch": "internal|exploration", '
        '"success_metric": "...", "tags": ["tag1"]}]}\n\n'
        "Rules:\n"
        "- Each milestone must have a measurable target_metric and target_value\n"
        "- Tasks must be classified by size: quick_fix (1-2d), small (3-7d), medium (1-4w), large (1-2m)\n"
        "- Minimum 30% improvement threshold for success\n"
        "- quick_fix tasks need only 2 weeks of measurement\n"
        "- large tasks need 4-8 weeks of measurement\n"
    )

    prompt = (
        f"Goal: {goal.title}\n"
        f"Description: {goal.description}\n"
        f"Target: {goal.target_outcome}\n"
        f"Timeline: {goal.timeline_days} days\n"
        f"Branch focus: {goal.branch}\n"
        f"Required improvement: {goal.target_improvement_pct}%\n"
    )

    models = [m for m in ["opus", "kimi"] if _check_model_available(m)]
    if not models:
        models = ["qwen"]

    responses = layer1_deliberate(prompt, models, system_prompt)

    for r in responses:
        if not r.response or r.error:
            continue
        try:
            text = r.response.strip()
            if "```" in text:
                text = text.split("```")[1] if "```" in text else text
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip().rstrip("`")

            data = json.loads(text)
            milestones = []
            tasks = []

            for i, m in enumerate(data.get("milestones", [])):
                ms = Milestone(
                    id=f"MS-{uuid.uuid4().hex[:8]}",
                    title=m.get("title", f"Milestone {i+1}"),
                    description=m.get("description", ""),
                    target_metric=m.get("target_metric", goal.target_outcome),
                    target_value=float(m.get("target_value", goal.target_improvement_pct)),
                    deadline_days=int(m.get("deadline_days", 14)),
                )
                milestones.append(ms)

            for t in data.get("tasks", []):
                ms_idx = int(t.get("milestone_index", 0))
                ms_id = milestones[ms_idx].id if ms_idx < len(milestones) else (milestones[0].id if milestones else "")
                size = t.get("size", "small")
                est_days = int(t.get("estimated_days", _size_to_days(size)))
                task = HorizonTask(
                    id=f"HT-{uuid.uuid4().hex[:8]}",
                    milestone_id=ms_id,
                    title=t.get("title", ""),
                    description=t.get("description", ""),
                    branch=t.get("branch", goal.branch),
                    size=size,
                    estimated_days=est_days,
                    priority=int(t.get("priority", 5)),
                    success_metric=t.get("success_metric", ""),
                    success_threshold=goal.target_improvement_pct,
                    measurement_days=_size_to_measurement_days(size),
                    tags=t.get("tags", []),
                )
                tasks.append(task)
                if ms_id:
                    for ms in milestones:
                        if ms.id == ms_id:
                            ms.tasks.append(task.id)

            if milestones:
                return milestones, tasks

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.debug(f"Parse failed for {r.model_id}: {e}")
            continue

    return _heuristic_decompose(goal)


def _heuristic_decompose(goal: HorizonGoal) -> Tuple[List[Milestone], List[HorizonTask]]:
    """Fallback decomposition using heuristics based on goal description."""
    milestones = []
    tasks = []

    phases = [
        ("Discovery & Baseline", "Measure current state, identify bottlenecks", 7),
        ("Quick Wins", "Apply quick fixes for immediate improvement", 14),
        ("Deep Optimization", "Implement major architectural improvements", 21),
        ("Validation & Measurement", "Track improvements over measurement period", 14),
    ]

    for i, (title, desc, days) in enumerate(phases):
        ms = Milestone(
            id=f"MS-{uuid.uuid4().hex[:8]}",
            title=title,
            description=desc,
            target_metric=goal.target_outcome,
            target_value=goal.target_improvement_pct * (i + 1) / len(phases),
            deadline_days=days,
        )
        milestones.append(ms)

        if goal.branch == BranchType.INTERNAL:
            task_templates = _internal_task_templates(i)
        else:
            task_templates = _exploration_task_templates(i)

        for t_title, t_desc, size, tags in task_templates:
            task = HorizonTask(
                id=f"HT-{uuid.uuid4().hex[:8]}",
                milestone_id=ms.id,
                title=t_title,
                description=t_desc,
                branch=goal.branch,
                size=size,
                estimated_days=_size_to_days(size),
                success_metric=goal.target_outcome,
                success_threshold=goal.target_improvement_pct,
                measurement_days=_size_to_measurement_days(size),
                tags=tags,
            )
            tasks.append(task)
            ms.tasks.append(task.id)

    return milestones, tasks


def _internal_task_templates(phase: int) -> List[Tuple[str, str, str, List[str]]]:
    """Task templates for internal-world branch."""
    if phase == 0:
        return [
            ("Run integration gap detector", "Find disconnected components", "quick_fix", ["diagnostics"]),
            ("Baseline all system metrics", "Capture current performance", "quick_fix", ["metrics"]),
            ("Run self-healing health check", "Identify broken components", "quick_fix", ["health"]),
        ]
    elif phase == 1:
        return [
            ("Fix broken component connections", "Wire disconnected event bus subscribers", "small", ["integration"]),
            ("Optimize hot loops", "Reduce CPU from polling and tight loops", "quick_fix", ["performance"]),
            ("Fix memory mesh feed", "Ensure genesis keys write to memory mesh", "small", ["memory"]),
        ]
    elif phase == 2:
        return [
            ("Unify sandbox systems", "Merge sandbox_engine and autonomous_sandbox_lab", "medium", ["architecture"]),
            ("Bridge event systems", "Connect Grace OS EventSystem with cognitive event_bus", "medium", ["integration"]),
            ("Unify trust systems", "Bridge TrustScorekeeper and TrustEngine", "large", ["trust"]),
        ]
    else:
        return [
            ("Measure improvement delta", "Compare current vs baseline metrics", "quick_fix", ["measurement"]),
            ("Generate evidence report", "Compile measurable results", "small", ["reporting"]),
        ]


def _exploration_task_templates(phase: int) -> List[Tuple[str, str, str, List[str]]]:
    """Task templates for exploration branch."""
    if phase == 0:
        return [
            ("Scan whitelist sources", "Check what new data is available", "quick_fix", ["research"]),
            ("Review recent research papers", "Find relevant AI/ML advances", "small", ["research"]),
            ("Analyze knowledge base gaps", "Identify topics Grace doesn't know about", "small", ["knowledge"]),
        ]
    elif phase == 1:
        return [
            ("Ingest high-value sources", "Import relevant research and documentation", "small", ["ingestion"]),
            ("Build concept map", "Map relationships between topics", "medium", ["knowledge"]),
        ]
    elif phase == 2:
        return [
            ("Prototype new capability", "Build something from scratch using learned concepts", "large", ["building"]),
            ("Cross-domain synthesis", "Combine knowledge from multiple domains", "medium", ["synthesis"]),
        ]
    else:
        return [
            ("Evaluate new capabilities", "Test what was built, measure effectiveness", "small", ["evaluation"]),
            ("Document learnings", "Create actionable documentation", "quick_fix", ["documentation"]),
        ]


def _size_to_days(size: str) -> int:
    return {"quick_fix": 2, "small": 5, "medium": 14, "large": 30, "epic": 60}.get(size, 7)


def _size_to_measurement_days(size: str) -> int:
    return {"quick_fix": 14, "small": 14, "medium": 21, "large": 30, "epic": 60}.get(size, 14)


# ── Fix Classification ────────────────────────────────────────────────

def classify_fix(
    problem: str,
    component: str = "",
    error_frequency: int = 0,
    system_impact: str = "low",
) -> Dict[str, Any]:
    """
    Classify whether a fix is quick (1-2 days) or needs a longer timeline.
    Returns classification with rationale and recommended measurement period.
    """
    score = 0

    if error_frequency > 100:
        score += 3
    elif error_frequency > 10:
        score += 2
    elif error_frequency > 0:
        score += 1

    impact_scores = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    score += impact_scores.get(system_impact, 1)

    complexity_keywords = {
        "architecture": 3, "refactor": 3, "redesign": 3, "migrate": 3,
        "unify": 2, "bridge": 2, "integrate": 2, "merge": 2,
        "optimize": 1, "fix": 1, "patch": 1, "update": 1,
        "config": 0, "typo": 0, "rename": 0, "toggle": 0,
    }
    for kw, kw_score in complexity_keywords.items():
        if kw in problem.lower():
            score += kw_score
            break

    if score <= 2:
        size = TaskSize.QUICK_FIX
        estimated_days = 2
        measurement_days = 14
    elif score <= 4:
        size = TaskSize.SMALL
        estimated_days = 5
        measurement_days = 14
    elif score <= 6:
        size = TaskSize.MEDIUM
        estimated_days = 14
        measurement_days = 21
    elif score <= 8:
        size = TaskSize.LARGE
        estimated_days = 30
        measurement_days = 30
    else:
        size = TaskSize.EPIC
        estimated_days = 60
        measurement_days = 60

    return {
        "size": size,
        "estimated_days": estimated_days,
        "measurement_days": measurement_days,
        "complexity_score": score,
        "rationale": _classification_rationale(size, score, problem),
        "needs_consensus": score >= 5,
        "needs_sandbox": score >= 3,
        "minimum_improvement_pct": 30,
    }


def _classification_rationale(size: str, score: int, problem: str) -> str:
    if size == TaskSize.QUICK_FIX:
        return f"Simple fix (score {score}). Apply directly, measure for 2 weeks."
    elif size == TaskSize.SMALL:
        return f"Small change (score {score}). Test in sandbox first, 2 weeks measurement."
    elif size == TaskSize.MEDIUM:
        return f"Medium complexity (score {score}). Needs sandbox testing, 3 weeks measurement."
    elif size == TaskSize.LARGE:
        return f"Major change (score {score}). Full consensus + sandbox + 30 day tracking."
    else:
        return f"Epic scope (score {score}). Multi-phase with 60-day measurement cycle."


# ── Baseline Collection ───────────────────────────────────────────────

def _collect_baselines(goal: HorizonGoal):
    """Collect current system metrics as baseline for the goal."""
    try:
        from cognitive.self_healing_tracker import get_self_healing_tracker
        tracker = get_self_healing_tracker()
        health = tracker.get_system_health()
        goal.baseline_metrics["healthy_components"] = len(health.get("healthy", []))
        goal.baseline_metrics["broken_components"] = len(health.get("broken", []))
        goal.baseline_metrics["degraded_components"] = len(health.get("degraded", []))
        goal.baseline_metrics["total_components"] = health.get("total_components", 0)
    except Exception:
        pass

    try:
        from cognitive.memory_mesh_metrics import get_performance_metrics
        metrics = get_performance_metrics()
        if metrics:
            all_metrics = metrics.get_all_metrics() if hasattr(metrics, 'get_all_metrics') else {}
            goal.baseline_metrics["avg_query_latency_ms"] = all_metrics.get("avg_query_latency_ms", 0)
            goal.baseline_metrics["cache_hit_rate"] = all_metrics.get("cache_hit_rate", 0)
    except Exception:
        pass

    try:
        from cognitive.trust_engine import get_trust_engine
        te = get_trust_engine()
        trust = te.get_system_trust()
        if isinstance(trust, dict):
            goal.baseline_metrics["system_trust"] = trust.get("score", 0.7)
        elif isinstance(trust, (int, float)):
            goal.baseline_metrics["system_trust"] = float(trust)
    except Exception:
        pass

    goal.current_metrics = dict(goal.baseline_metrics)


def collect_current_metrics(goal_id: str) -> Dict[str, float]:
    """Collect current metrics and update the goal."""
    goal = load_goal(goal_id)
    if not goal:
        return {}
    _collect_baselines(goal)
    metrics = dict(goal.baseline_metrics)
    goal.current_metrics = metrics
    _save_goal(goal)
    return metrics


# ── Goal Lifecycle ────────────────────────────────────────────────────

def activate_goal(goal_id: str) -> Optional[HorizonGoal]:
    """Activate a goal and start the timeline."""
    goal = load_goal(goal_id)
    if not goal:
        return None

    goal.status = GoalStatus.ACTIVE
    goal.started_at = datetime.utcnow().isoformat()
    goal.deadline = (datetime.utcnow() + timedelta(days=goal.timeline_days)).isoformat()
    _save_goal(goal)

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Horizon goal activated: {goal.title} ({goal.timeline_days}d)",
            how="horizon_planner.activate_goal",
            output_data={"goal_id": goal.id, "deadline": goal.deadline},
            tags=["horizon", "goal", "activated"],
        )
    except Exception:
        pass

    return goal


def update_task_status(
    goal_id: str, task_id: str,
    status: str, current_value: float = None,
    result: str = None,
) -> Optional[HorizonTask]:
    """Update a task's status and optionally its measurement value."""
    goal = load_goal(goal_id)
    if not goal:
        return None

    for task in goal.tasks:
        if task.id == task_id:
            task.status = status
            if current_value is not None:
                task.current_value = current_value
            if result:
                task.result = result
            if status == "measuring" and not task.measuring_since:
                task.measuring_since = datetime.utcnow().isoformat()
            if status in ("completed", "achieved", "failed"):
                task.completed_at = datetime.utcnow().isoformat()
            _save_goal(goal)
            return task

    return None


def check_goal_progress(goal_id: str) -> Dict[str, Any]:
    """Check overall goal progress including all milestones and tasks."""
    goal = load_goal(goal_id)
    if not goal:
        return {"error": "Goal not found"}

    total_tasks = len(goal.tasks)
    completed_tasks = sum(1 for t in goal.tasks if t.status in ("completed", "achieved"))
    measuring_tasks = sum(1 for t in goal.tasks if t.status == "measuring")
    failed_tasks = sum(1 for t in goal.tasks if t.status == "failed")

    _collect_baselines(goal)

    improvements = {}
    for metric, baseline in goal.baseline_metrics.items():
        current = goal.current_metrics.get(metric, baseline)
        if baseline > 0:
            delta = ((current - baseline) / baseline) * 100
            improvements[metric] = {
                "baseline": baseline,
                "current": current,
                "delta_pct": round(delta, 2),
                "meets_target": abs(delta) >= goal.target_improvement_pct,
            }

    days_elapsed = 0
    days_remaining = goal.timeline_days
    if goal.started_at:
        started = datetime.fromisoformat(goal.started_at)
        days_elapsed = (datetime.utcnow() - started).days
        days_remaining = max(0, goal.timeline_days - days_elapsed)

    _save_goal(goal)

    return {
        "goal_id": goal.id,
        "title": goal.title,
        "status": goal.status,
        "branch": goal.branch,
        "timeline": {
            "total_days": goal.timeline_days,
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "started_at": goal.started_at,
            "deadline": goal.deadline,
        },
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "measuring": measuring_tasks,
            "failed": failed_tasks,
            "pending": total_tasks - completed_tasks - measuring_tasks - failed_tasks,
            "completion_pct": round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0,
        },
        "milestones": [
            {
                "id": ms.id,
                "title": ms.title,
                "progress_pct": ms.progress_pct,
                "status": ms.status,
                "target": f"{ms.target_value}{ms.unit}",
            }
            for ms in goal.milestones
        ],
        "improvements": improvements,
        "target_improvement_pct": goal.target_improvement_pct,
        "overall_on_track": completed_tasks > 0 or days_elapsed < goal.timeline_days * 0.2,
    }


# ── Persistence ───────────────────────────────────────────────────────

def _save_goal(goal: HorizonGoal):
    HORIZON_DIR.mkdir(parents=True, exist_ok=True)
    path = HORIZON_DIR / f"{goal.id}.json"
    data = {
        "id": goal.id,
        "title": goal.title,
        "description": goal.description,
        "target_outcome": goal.target_outcome,
        "measurable_target": goal.measurable_target,
        "target_improvement_pct": goal.target_improvement_pct,
        "timeline_days": goal.timeline_days,
        "status": goal.status,
        "branch": goal.branch,
        "milestones": [asdict(ms) for ms in goal.milestones],
        "tasks": [asdict(t) for t in goal.tasks],
        "baseline_metrics": goal.baseline_metrics,
        "current_metrics": goal.current_metrics,
        "created_at": goal.created_at,
        "started_at": goal.started_at,
        "deadline": goal.deadline,
        "completed_at": goal.completed_at,
        "genesis_key_id": goal.genesis_key_id,
    }
    path.write_text(json.dumps(data, indent=2, default=str))


def load_goal(goal_id: str) -> Optional[HorizonGoal]:
    path = HORIZON_DIR / f"{goal_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    goal = HorizonGoal(
        id=data["id"],
        title=data["title"],
        description=data["description"],
        target_outcome=data["target_outcome"],
        measurable_target=data.get("measurable_target", ""),
        target_improvement_pct=data.get("target_improvement_pct", 30.0),
        timeline_days=data.get("timeline_days", 60),
        status=data.get("status", GoalStatus.DRAFT),
        branch=data.get("branch", BranchType.INTERNAL),
        baseline_metrics=data.get("baseline_metrics", {}),
        current_metrics=data.get("current_metrics", {}),
        created_at=data.get("created_at", ""),
        started_at=data.get("started_at"),
        deadline=data.get("deadline"),
        completed_at=data.get("completed_at"),
        genesis_key_id=data.get("genesis_key_id"),
    )
    goal.milestones = [Milestone(**m) for m in data.get("milestones", [])]
    goal.tasks = [HorizonTask(**t) for t in data.get("tasks", [])]
    return goal


def list_goals(status: Optional[str] = None) -> List[Dict[str, Any]]:
    HORIZON_DIR.mkdir(parents=True, exist_ok=True)
    goals = []
    for path in sorted(HORIZON_DIR.glob("HG-*.json"), reverse=True):
        try:
            data = json.loads(path.read_text())
            if status is None or data.get("status") == status:
                goals.append({
                    "id": data["id"],
                    "title": data["title"],
                    "status": data.get("status", "draft"),
                    "branch": data.get("branch", "internal"),
                    "timeline_days": data.get("timeline_days", 60),
                    "milestones": len(data.get("milestones", [])),
                    "tasks": len(data.get("tasks", [])),
                    "created_at": data.get("created_at", ""),
                    "target_improvement_pct": data.get("target_improvement_pct", 30),
                })
        except Exception:
            continue
    return goals
