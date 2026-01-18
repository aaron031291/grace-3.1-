"""
Training Center API - REST endpoints for Grace's Intelligence Training Center.

This API provides access to:
- Training status and metrics
- Intelligence reports
- Model snapshots (the "weights")
- Curriculum management
- Training control (start/stop)
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from cognitive.intelligence_training_center import (
    IntelligenceTrainingCenter,
    TrainingTask,
    TrainingDomain,
    TaskDifficulty,
    create_training_center
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/training-center", tags=["Training Center"])

# Global training center instance
_training_center: Optional[IntelligenceTrainingCenter] = None


def get_training_center() -> IntelligenceTrainingCenter:
    """Get or create the training center instance."""
    global _training_center
    if _training_center is None:
        _training_center = create_training_center()
    return _training_center


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class TrainingTaskRequest(BaseModel):
    """Request to create a training task."""
    domain: str = Field(..., description="Training domain (coding, self_healing, reasoning, etc.)")
    objective: str = Field(..., description="What to accomplish")
    description: Optional[str] = None
    difficulty: str = Field("medium", description="Task difficulty")
    constraints: List[str] = Field(default_factory=list)
    input_artifacts: Dict[str, Any] = Field(default_factory=dict)


class CurriculumRequest(BaseModel):
    """Request to generate curriculum."""
    domain: str = Field(..., description="Domain for curriculum")
    count: int = Field(10, description="Number of tasks to generate")


class TrainingControlRequest(BaseModel):
    """Request to control training."""
    action: str = Field(..., description="start or stop")
    domains: Optional[List[str]] = Field(None, description="Domains to train on")


class SnapshotRequest(BaseModel):
    """Request to create a snapshot."""
    reason: str = Field("manual", description="Reason for snapshot")


# =============================================================================
# STATUS ENDPOINTS
# =============================================================================

@router.get("/status")
async def get_training_status():
    """
    Get current training status and metrics.
    
    Returns:
    - is_training: Whether continuous training is active
    - current_model_version: Current "weights" version
    - stats: Training statistics
    - skill_mastery: Per-domain mastery levels
    """
    tc = get_training_center()
    return tc.get_training_status()


@router.get("/intelligence-report")
async def get_intelligence_report():
    """
    Get comprehensive intelligence report.
    
    This shows Grace's current "intelligence" state:
    - Model version
    - Skill mastery by domain
    - Patterns and procedures learned
    - Failure taxonomy
    - Recommendations for improvement
    """
    tc = get_training_center()
    return tc.get_intelligence_report()


@router.get("/snapshot")
async def get_current_snapshot():
    """
    Get current model snapshot (the "weights").
    
    This is Grace's persisted intelligence state.
    """
    tc = get_training_center()
    snapshot = tc.get_current_snapshot()
    return snapshot.to_dict()


@router.post("/snapshot")
async def create_snapshot(request: SnapshotRequest):
    """
    Create a new model snapshot version.
    
    This saves the current state and increments the version.
    """
    tc = get_training_center()
    snapshot = tc.create_new_snapshot(reason=request.reason)
    return {
        "success": True,
        "new_version": snapshot.model_version,
        "created_at": snapshot.created_at.isoformat()
    }


# =============================================================================
# TRAINING CONTROL
# =============================================================================

@router.post("/control")
async def control_training(request: TrainingControlRequest, background_tasks: BackgroundTasks):
    """
    Start or stop continuous training.
    
    Actions:
    - start: Begin continuous training loop
    - stop: Stop continuous training
    """
    tc = get_training_center()
    
    if request.action == "start":
        domains = None
        if request.domains:
            domains = [TrainingDomain(d) for d in request.domains]
        
        background_tasks.add_task(tc.start_continuous_training, domains)
        return {"success": True, "message": "Training started"}
    
    elif request.action == "stop":
        tc.stop_continuous_training()
        return {"success": True, "message": "Training stopped"}
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")


@router.post("/train-single")
async def train_single_task(request: TrainingTaskRequest):
    """
    Run a single training task.
    
    This executes the full training loop:
    OBSERVE → ORIENT → DECIDE → ACT → EVALUATE → LEARN → CONSOLIDATE
    """
    tc = get_training_center()
    
    try:
        domain = TrainingDomain(request.domain)
        difficulty = TaskDifficulty(request.difficulty)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid domain or difficulty: {e}")
    
    task = TrainingTask.create(
        domain=domain,
        objective=request.objective,
        difficulty=difficulty,
        description=request.description or request.objective,
        constraints=request.constraints,
        input_artifacts=request.input_artifacts
    )
    
    try:
        attempt, evaluation, delta = tc.run_training_loop(task)
        
        return {
            "success": True,
            "task_id": task.task_id,
            "attempt_id": attempt.attempt_id,
            "evaluation": {
                "success": evaluation.success,
                "scores": evaluation.scores,
                "regressions": evaluation.regressions
            },
            "learning": {
                "patterns_added": len(delta.patterns_added),
                "mastery_updates": delta.mastery_updates,
                "trust_impact": delta.trust_impact
            }
        }
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CURRICULUM MANAGEMENT
# =============================================================================

@router.post("/curriculum/generate")
async def generate_curriculum(request: CurriculumRequest):
    """
    Generate a curriculum of training tasks.
    
    Creates a mix of difficulties to optimize learning.
    """
    tc = get_training_center()
    
    try:
        domain = TrainingDomain(request.domain)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid domain: {request.domain}")
    
    tasks = tc.generate_curriculum(domain, count=request.count)
    
    return {
        "success": True,
        "tasks_generated": len(tasks),
        "domain": domain.value,
        "task_ids": [t.task_id for t in tasks]
    }


@router.get("/curriculum/queue")
async def get_task_queue():
    """Get current task queue."""
    tc = get_training_center()
    return {
        "queue_size": len(tc._task_queue),
        "tasks": [
            {
                "task_id": t.task_id,
                "domain": t.domain.value,
                "difficulty": t.difficulty.value,
                "objective": t.objective[:100]
            }
            for t in tc._task_queue[:20]
        ]
    }


@router.post("/curriculum/add-task")
async def add_task_to_queue(request: TrainingTaskRequest):
    """Add a custom task to the training queue."""
    tc = get_training_center()
    
    try:
        domain = TrainingDomain(request.domain)
        difficulty = TaskDifficulty(request.difficulty)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    task = TrainingTask.create(
        domain=domain,
        objective=request.objective,
        difficulty=difficulty,
        description=request.description or request.objective,
        constraints=request.constraints,
        input_artifacts=request.input_artifacts
    )
    
    tc.add_task(task)
    
    return {
        "success": True,
        "task_id": task.task_id,
        "queue_position": len(tc._task_queue)
    }


# =============================================================================
# SKILL MASTERY
# =============================================================================

@router.get("/skills")
async def get_skill_mastery():
    """
    Get detailed skill mastery for all domains.
    """
    tc = get_training_center()
    snapshot = tc.get_current_snapshot()
    
    skills = {}
    for domain, mastery in snapshot.skill_mastery.items():
        # Determine mastery level name
        if mastery.level >= 0.9:
            level_name = "Expert"
        elif mastery.level >= 0.7:
            level_name = "Advanced"
        elif mastery.level >= 0.5:
            level_name = "Intermediate"
        elif mastery.level >= 0.3:
            level_name = "Beginner"
        else:
            level_name = "Novice"
        
        skills[domain] = {
            "level": mastery.level,
            "level_name": level_name,
            "attempts": mastery.attempts,
            "successes": mastery.successes,
            "success_rate": mastery.success_rate,
            "last_updated": mastery.last_updated.isoformat() if mastery.last_updated else None
        }
    
    return {
        "skills": skills,
        "strongest_domain": max(skills.items(), key=lambda x: x[1]["level"])[0] if skills else None,
        "weakest_domain": min(skills.items(), key=lambda x: x[1]["level"])[0] if skills else None
    }


@router.get("/skills/{domain}")
async def get_domain_skill(domain: str):
    """Get skill mastery for a specific domain."""
    tc = get_training_center()
    snapshot = tc.get_current_snapshot()
    
    if domain not in snapshot.skill_mastery:
        raise HTTPException(status_code=404, detail=f"Domain not found: {domain}")
    
    mastery = snapshot.skill_mastery[domain]
    
    return {
        "domain": domain,
        "level": mastery.level,
        "attempts": mastery.attempts,
        "successes": mastery.successes,
        "success_rate": mastery.success_rate
    }


# =============================================================================
# PATTERNS AND KNOWLEDGE
# =============================================================================

@router.get("/patterns")
async def get_learned_patterns():
    """
    Get patterns learned by Grace.
    
    Patterns are reusable solutions learned from training.
    """
    tc = get_training_center()
    snapshot = tc.get_current_snapshot()
    
    return {
        "pattern_count": snapshot.pattern_count,
        "average_trust": snapshot.pattern_trust_avg,
        "top_patterns": snapshot.top_patterns[:10]
    }


@router.get("/failure-taxonomy")
async def get_failure_taxonomy():
    """
    Get failure taxonomy - common failure modes.
    
    This helps understand what Grace struggles with.
    """
    tc = get_training_center()
    snapshot = tc.get_current_snapshot()
    
    sorted_failures = sorted(
        snapshot.failure_categories.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    return {
        "failure_categories": dict(sorted_failures),
        "total_failures": sum(snapshot.failure_categories.values()),
        "top_failures": sorted_failures[:5]
    }


# =============================================================================
# DOMAINS INFO
# =============================================================================

@router.get("/domains")
async def get_available_domains():
    """Get available training domains."""
    return {
        "domains": [
            {
                "value": d.value,
                "name": d.name,
                "description": _get_domain_description(d)
            }
            for d in TrainingDomain
        ]
    }


@router.get("/difficulties")
async def get_difficulty_levels():
    """Get available difficulty levels."""
    return {
        "difficulties": [
            {
                "value": d.value,
                "name": d.name,
                "level": i + 1
            }
            for i, d in enumerate(TaskDifficulty)
        ]
    }


def _get_domain_description(domain: TrainingDomain) -> str:
    """Get description for a domain."""
    descriptions = {
        TrainingDomain.CODING: "Code generation and programming tasks",
        TrainingDomain.SELF_HEALING: "Fixing bugs and code issues",
        TrainingDomain.REASONING: "Logical reasoning and problem solving",
        TrainingDomain.KNOWLEDGE: "Knowledge acquisition and application",
        TrainingDomain.SECURITY: "Security analysis and fixes",
        TrainingDomain.PERFORMANCE: "Performance optimization",
        TrainingDomain.ARCHITECTURE: "System design and architecture",
        TrainingDomain.TESTING: "Test generation and verification"
    }
    return descriptions.get(domain, "")
