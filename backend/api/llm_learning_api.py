"""
LLM Learning and Tracking API

REST API endpoints for the LLM interaction tracking, pattern learning,
command routing, and dependency reduction systems.

Endpoints:
- /llm-learning/track         - Record LLM interactions
- /llm-learning/route         - Route tasks via Kimi command router
- /llm-learning/patterns      - View and manage extracted patterns
- /llm-learning/dependency    - View dependency metrics and trends
- /llm-learning/training-data - Export training data for local models
- /llm-learning/progress      - View learning progress
- /llm-learning/coding-tasks  - Track coding task delegation
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from database.session import get_db

from cognitive.llm_interaction_tracker import (
    LLMInteractionTracker,
    get_llm_interaction_tracker,
)
from cognitive.kimi_command_router import (
    KimiCommandRouter,
    get_kimi_command_router,
)
from cognitive.llm_pattern_learner import (
    LLMPatternLearner,
    get_llm_pattern_learner,
)
from cognitive.llm_dependency_reducer import (
    LLMDependencyReducer,
    get_llm_dependency_reducer,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm-learning", tags=["LLM Learning & Tracking"])


# =======================================================================
# REQUEST/RESPONSE MODELS
# =======================================================================

class RecordInteractionRequest(BaseModel):
    """Record an LLM interaction."""
    prompt: str = Field(..., description="Prompt sent to LLM")
    response: str = Field(..., description="LLM's response")
    model_used: str = Field(..., description="Model identifier (e.g., 'kimi', 'deepseek')")
    interaction_type: str = Field(
        default="reasoning",
        description="Type: command_execution, coding_task, reasoning, planning, etc."
    )
    delegation_type: Optional[str] = Field(
        None,
        description="Delegation: kimi_direct, coding_agent, hybrid, grace_autonomous"
    )
    reasoning_chain: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Step-by-step reasoning the LLM performed"
    )
    decision_path: Optional[List[str]] = Field(
        None,
        description="Key decisions made during reasoning"
    )
    alternatives_considered: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Alternative approaches considered"
    )
    outcome: str = Field(default="pending", description="Outcome: success, failure, partial_success")
    confidence_score: float = Field(default=0.0, description="LLM confidence (0-1)")
    duration_ms: float = Field(default=0.0, description="Duration in milliseconds")
    token_count_input: int = Field(default=0, description="Input tokens")
    token_count_output: int = Field(default=0, description="Output tokens")
    context_used: Optional[Dict[str, Any]] = Field(None, description="Context provided to LLM")
    files_referenced: Optional[List[str]] = Field(None, description="Files referenced")
    commands_executed: Optional[List[str]] = Field(None, description="Commands executed")
    error_message: Optional[str] = Field(None, description="Error if any")
    error_type: Optional[str] = Field(None, description="Error classification")
    session_id: Optional[str] = Field(None, description="Session grouping ID")
    parent_interaction_id: Optional[str] = Field(None, description="Parent interaction for chains")
    system_prompt: Optional[str] = Field(None, description="System prompt used")
    genesis_key_id: Optional[str] = Field(None, description="Genesis key link")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class UpdateInteractionRequest(BaseModel):
    """Update an interaction's outcome."""
    outcome: str = Field(..., description="New outcome: success, failure, partial_success")
    quality_score: Optional[float] = Field(None, description="Quality score (0-1)")
    user_feedback: Optional[str] = Field(None, description="Feedback: positive, negative, neutral")
    user_feedback_text: Optional[str] = Field(None, description="Detailed feedback text")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class RouteTaskRequest(BaseModel):
    """Route a task through Kimi command router."""
    user_request: str = Field(..., description="User's natural language request")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    force_route: Optional[str] = Field(
        None,
        description="Force route: kimi_direct, coding_agent, hybrid, grace_autonomous"
    )


class RecordCodingTaskRequest(BaseModel):
    """Record a coding task delegation."""
    task_description: str = Field(..., description="What the coding task is")
    task_type: str = Field(..., description="Type: bug_fix, feature, refactor, testing, etc.")
    interaction_id: Optional[str] = Field(None, description="Related interaction ID")
    delegated_by: str = Field(default="kimi", description="Who delegated")
    delegated_to: str = Field(default="coding_agent", description="Who it was delegated to")
    files_targeted: Optional[List[str]] = Field(None, description="Target files")


class UpdateCodingTaskRequest(BaseModel):
    """Update a coding task with results."""
    outcome: str = Field(..., description="Outcome: success, failure")
    files_created: Optional[List[str]] = Field(None)
    files_modified: Optional[List[str]] = Field(None)
    diff_summary: Optional[str] = Field(None)
    tests_run: bool = Field(default=False)
    tests_passed: int = Field(default=0)
    tests_failed: int = Field(default=0)
    error_message: Optional[str] = Field(None)
    duration_ms: float = Field(default=0.0)
    iterations: int = Field(default=1)
    quality_assessment: Optional[Dict[str, Any]] = Field(None)
    reasoning_used: Optional[List[Dict[str, Any]]] = Field(None)
    patterns_applied: Optional[List[str]] = Field(None)


# =======================================================================
# DEPENDENCY INJECTION
# =======================================================================

def get_tracker(db: Session = Depends(get_db)) -> LLMInteractionTracker:
    return get_llm_interaction_tracker(db)


def get_router_instance(db: Session = Depends(get_db)) -> KimiCommandRouter:
    return get_kimi_command_router(db)


def get_learner(db: Session = Depends(get_db)) -> LLMPatternLearner:
    return get_llm_pattern_learner(db)


def get_reducer(db: Session = Depends(get_db)) -> LLMDependencyReducer:
    return get_llm_dependency_reducer(db)


# =======================================================================
# INTERACTION TRACKING ENDPOINTS
# =======================================================================

@router.post("/track")
async def record_interaction(
    request: RecordInteractionRequest,
    tracker: LLMInteractionTracker = Depends(get_tracker),
):
    """
    Record an LLM interaction for learning.

    Every time Kimi or any LLM processes a request, call this endpoint
    to record the full interaction including reasoning chain, outcome,
    and performance metrics.
    """
    try:
        interaction = tracker.record_interaction(
            prompt=request.prompt,
            response=request.response,
            model_used=request.model_used,
            interaction_type=request.interaction_type,
            delegation_type=request.delegation_type,
            reasoning_chain=request.reasoning_chain,
            decision_path=request.decision_path,
            alternatives_considered=request.alternatives_considered,
            outcome=request.outcome,
            confidence_score=request.confidence_score,
            duration_ms=request.duration_ms,
            token_count_input=request.token_count_input,
            token_count_output=request.token_count_output,
            context_used=request.context_used,
            files_referenced=request.files_referenced,
            commands_executed=request.commands_executed,
            error_message=request.error_message,
            error_type=request.error_type,
            session_id=request.session_id,
            parent_interaction_id=request.parent_interaction_id,
            system_prompt=request.system_prompt,
            genesis_key_id=request.genesis_key_id,
            metadata=request.metadata,
        )

        return {
            "interaction_id": interaction.interaction_id,
            "type": interaction.interaction_type.value,
            "outcome": interaction.outcome.value,
            "trust_score": interaction.trust_score,
            "recorded_at": interaction.created_at.isoformat() if interaction.created_at else None,
        }

    except Exception as e:
        logger.error(f"Error recording interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/track/{interaction_id}")
async def update_interaction(
    interaction_id: str,
    request: UpdateInteractionRequest,
    tracker: LLMInteractionTracker = Depends(get_tracker),
):
    """Update the outcome of a previously recorded interaction."""
    try:
        interaction = tracker.update_interaction_outcome(
            interaction_id=interaction_id,
            outcome=request.outcome,
            quality_score=request.quality_score,
            user_feedback=request.user_feedback,
            user_feedback_text=request.user_feedback_text,
            error_message=request.error_message,
        )

        if not interaction:
            raise HTTPException(status_code=404, detail="Interaction not found")

        return {
            "interaction_id": interaction.interaction_id,
            "outcome": interaction.outcome.value,
            "trust_score": interaction.trust_score,
            "quality_score": interaction.quality_score,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/track/stats")
async def get_interaction_stats(
    time_window_hours: int = Query(default=24, description="Time window in hours"),
    model: Optional[str] = Query(default=None, description="Filter by model"),
    tracker: LLMInteractionTracker = Depends(get_tracker),
):
    """Get LLM interaction statistics."""
    try:
        return tracker.get_interaction_stats(
            time_window_hours=time_window_hours,
            model=model,
        )
    except Exception as e:
        logger.error(f"Error getting interaction stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/track/recent")
async def get_recent_interactions(
    limit: int = Query(default=50, le=200),
    interaction_type: Optional[str] = Query(default=None),
    outcome: Optional[str] = Query(default=None),
    tracker: LLMInteractionTracker = Depends(get_tracker),
):
    """Get recent LLM interactions."""
    try:
        return tracker.get_recent_interactions(
            limit=limit,
            interaction_type=interaction_type,
            outcome=outcome,
        )
    except Exception as e:
        logger.error(f"Error getting recent interactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/track/reasoning-paths")
async def get_reasoning_paths(
    domain: Optional[str] = Query(default=None),
    min_success_rate: float = Query(default=0.0),
    min_times_seen: int = Query(default=1),
    limit: int = Query(default=50, le=200),
    tracker: LLMInteractionTracker = Depends(get_tracker),
):
    """Get recorded reasoning paths."""
    try:
        return tracker.get_reasoning_paths(
            domain=domain,
            min_success_rate=min_success_rate,
            min_times_seen=min_times_seen,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error getting reasoning paths: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# COMMAND ROUTING ENDPOINTS
# =======================================================================

@router.post("/route")
async def route_task(
    request: RouteTaskRequest,
    command_router: KimiCommandRouter = Depends(get_router_instance),
):
    """
    Route a task through the Kimi command router.

    Classifies the request and determines whether it should be:
    - Executed directly by Kimi (commands, reasoning)
    - Delegated to the coding agent (code writing, refactoring)
    - Split between both (hybrid approach)
    - Handled autonomously by Grace (if patterns exist)
    """
    try:
        routed = command_router.classify_and_route(
            user_request=request.user_request,
            context=request.context,
            force_route=request.force_route,
        )

        return {
            "task_id": routed.task_id,
            "route": routed.route.value,
            "task_type": routed.task_type,
            "confidence": routed.classification_confidence,
            "reasoning": routed.reasoning,
            "coding_subtasks": routed.coding_subtasks,
            "command_subtasks": routed.command_subtasks,
        }

    except Exception as e:
        logger.error(f"Error routing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/route/stats")
async def get_routing_stats(
    command_router: KimiCommandRouter = Depends(get_router_instance),
):
    """Get Kimi command routing statistics."""
    try:
        return command_router.get_routing_stats()
    except Exception as e:
        logger.error(f"Error getting routing stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# CODING TASK ENDPOINTS
# =======================================================================

@router.post("/coding-tasks")
async def record_coding_task(
    request: RecordCodingTaskRequest,
    tracker: LLMInteractionTracker = Depends(get_tracker),
):
    """Record a coding task that was delegated from Kimi to the coding agent."""
    try:
        record = tracker.record_coding_task(
            task_description=request.task_description,
            task_type=request.task_type,
            interaction_id=request.interaction_id,
            delegated_by=request.delegated_by,
            delegated_to=request.delegated_to,
            files_targeted=request.files_targeted,
        )

        return {
            "task_id": record.task_id,
            "task_type": record.task_type,
            "delegated_by": record.delegated_by,
            "delegated_to": record.delegated_to,
            "outcome": record.outcome.value,
        }

    except Exception as e:
        logger.error(f"Error recording coding task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/coding-tasks/{task_id}")
async def update_coding_task(
    task_id: str,
    request: UpdateCodingTaskRequest,
    tracker: LLMInteractionTracker = Depends(get_tracker),
):
    """Update a coding task with its results."""
    try:
        record = tracker.update_coding_task(
            task_id=task_id,
            outcome=request.outcome,
            files_created=request.files_created,
            files_modified=request.files_modified,
            diff_summary=request.diff_summary,
            tests_run=request.tests_run,
            tests_passed=request.tests_passed,
            tests_failed=request.tests_failed,
            error_message=request.error_message,
            duration_ms=request.duration_ms,
            iterations=request.iterations,
            quality_assessment=request.quality_assessment,
            reasoning_used=request.reasoning_used,
            patterns_applied=request.patterns_applied,
        )

        if not record:
            raise HTTPException(status_code=404, detail="Coding task not found")

        return {
            "task_id": record.task_id,
            "outcome": record.outcome.value,
            "tests_passed": record.tests_passed,
            "tests_failed": record.tests_failed,
            "duration_ms": record.duration_ms,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating coding task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coding-tasks/stats")
async def get_coding_task_stats(
    time_window_hours: int = Query(default=168, description="Time window in hours (default 1 week)"),
    tracker: LLMInteractionTracker = Depends(get_tracker),
):
    """Get coding task delegation statistics."""
    try:
        return tracker.get_coding_task_stats(time_window_hours=time_window_hours)
    except Exception as e:
        logger.error(f"Error getting coding task stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# PATTERN LEARNING ENDPOINTS
# =======================================================================

@router.post("/patterns/extract")
async def extract_patterns(
    time_window_hours: int = Query(default=168),
    learner: LLMPatternLearner = Depends(get_learner),
):
    """
    Extract patterns from recent LLM interactions.

    Analyzes reasoning paths and interactions to identify recurring
    patterns that can be codified for autonomous handling.
    """
    try:
        patterns = learner.extract_patterns(time_window_hours=time_window_hours)
        return {
            "patterns_extracted": len(patterns),
            "patterns": patterns,
        }
    except Exception as e:
        logger.error(f"Error extracting patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/stats")
async def get_pattern_stats(
    learner: LLMPatternLearner = Depends(get_learner),
):
    """Get statistics about extracted patterns."""
    try:
        return learner.get_pattern_stats()
    except Exception as e:
        logger.error(f"Error getting pattern stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/check-autonomous")
async def check_autonomous_capability(
    request: str = Query(..., description="Request to check"),
    task_type: str = Query(default="general", description="Task type"),
    learner: LLMPatternLearner = Depends(get_learner),
):
    """
    Check if Grace can handle a request autonomously using learned patterns.

    Returns whether the system has sufficient pattern confidence to
    handle this type of request without calling an external LLM.
    """
    try:
        can_handle = learner.can_handle_autonomously(request, task_type)
        return {
            "request": request[:200],
            "task_type": task_type,
            "can_handle_autonomously": can_handle,
        }
    except Exception as e:
        logger.error(f"Error checking autonomous capability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# DEPENDENCY REDUCTION ENDPOINTS
# =======================================================================

@router.get("/dependency/metrics")
async def get_dependency_metrics(
    period_hours: int = Query(default=24, description="Period in hours"),
    reducer: LLMDependencyReducer = Depends(get_reducer),
):
    """
    Get current LLM dependency metrics.

    Shows how much Grace relies on LLMs and where autonomous
    handling is possible.
    """
    try:
        return reducer.calculate_dependency_metrics(period_hours=period_hours)
    except Exception as e:
        logger.error(f"Error getting dependency metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dependency/trend")
async def get_dependency_trend(
    days: int = Query(default=30, description="Number of days"),
    reducer: LLMDependencyReducer = Depends(get_reducer),
):
    """
    Get LLM dependency trend over time.

    Shows whether dependency is increasing or decreasing.
    """
    try:
        return reducer.get_dependency_trend(days=days)
    except Exception as e:
        logger.error(f"Error getting dependency trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dependency/domains")
async def get_domain_autonomy_scores(
    reducer: LLMDependencyReducer = Depends(get_reducer),
):
    """
    Get autonomy scores per domain.

    Shows which domains Grace can handle independently.
    """
    try:
        return reducer.get_domain_autonomy_scores()
    except Exception as e:
        logger.error(f"Error getting domain autonomy scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dependency/recommendations")
async def get_reduction_recommendations(
    reducer: LLMDependencyReducer = Depends(get_reducer),
):
    """
    Get recommendations for reducing LLM dependency.

    Suggests which task types to focus on learning and which
    patterns need more training data.
    """
    try:
        return reducer.get_reduction_recommendations()
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# TRAINING DATA EXPORT
# =======================================================================

@router.get("/training-data/export")
async def export_training_data(
    min_trust_score: float = Query(default=0.7, description="Minimum trust score"),
    task_type: Optional[str] = Query(default=None, description="Task type filter"),
    limit: int = Query(default=1000, le=5000, description="Max examples"),
    format_type: str = Query(
        default="instruction_tuning",
        description="Format: instruction_tuning, chat, raw"
    ),
    reducer: LLMDependencyReducer = Depends(get_reducer),
):
    """
    Export high-quality LLM interaction data for training local models.

    Packages the best interactions into training data that can be used
    to fine-tune a local model, further reducing LLM dependency.
    """
    try:
        return reducer.export_training_data(
            min_trust_score=min_trust_score,
            task_type=task_type,
            limit=limit,
            format_type=format_type,
        )
    except Exception as e:
        logger.error(f"Error exporting training data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# LEARNING PROGRESS
# =======================================================================

@router.get("/progress")
async def get_learning_progress(
    learner: LLMPatternLearner = Depends(get_learner),
):
    """
    Get overall learning progress.

    Shows how much Grace has learned from LLM interactions and how
    close it is to handling various task types autonomously.
    """
    try:
        return learner.get_learning_progress()
    except Exception as e:
        logger.error(f"Error getting learning progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_learning_dashboard(
    tracker: LLMInteractionTracker = Depends(get_tracker),
    learner: LLMPatternLearner = Depends(get_learner),
    reducer: LLMDependencyReducer = Depends(get_reducer),
):
    """
    Get a comprehensive learning dashboard.

    Combines all metrics into a single view showing:
    - Interaction statistics
    - Pattern extraction progress
    - Dependency reduction trend
    - Autonomy readiness
    """
    try:
        interaction_stats = tracker.get_interaction_stats(time_window_hours=24)
        pattern_stats = learner.get_pattern_stats()
        learning_progress = learner.get_learning_progress()
        dependency_trend = reducer.get_dependency_trend(days=7)
        domain_scores = reducer.get_domain_autonomy_scores()
        recommendations = reducer.get_reduction_recommendations()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "interaction_stats_24h": interaction_stats,
            "pattern_stats": pattern_stats,
            "learning_progress": learning_progress,
            "dependency_trend_7d": dependency_trend,
            "domain_autonomy": domain_scores,
            "top_recommendations": recommendations.get("recommendations", [])[:5],
        }

    except Exception as e:
        logger.error(f"Error getting learning dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
