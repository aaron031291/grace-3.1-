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

# Auth dependency for sensitive endpoints
try:
    from security.auth import get_optional_user
except ImportError:
    async def get_optional_user():
        return None

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
from cognitive.kimi_tool_executor import (
    KimiToolExecutor,
    get_kimi_tool_executor,
    TOOL_REGISTRY,
)
from cognitive.kimi_brain import (
    KimiBrain,
    get_kimi_brain,
)
from cognitive.grace_verified_executor import (
    GraceVerifiedExecutor,
    get_grace_verified_executor,
)
from cognitive.grace_verification_engine import (
    GraceVerificationEngine,
    get_grace_verification_engine,
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
            "timestamp": datetime.now().isoformat(),
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


# =======================================================================
# KIMI TOOL EXECUTOR ENDPOINTS
# =======================================================================

class ToolCallRequest(BaseModel):
    """Request to execute a tool via Kimi."""
    tool_id: str = Field(..., description="Tool ID from the tool registry")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    reasoning: str = Field(default="", description="Why Kimi is calling this tool")
    session_id: Optional[str] = Field(None, description="Session grouping ID")


class ParallelToolCallRequest(BaseModel):
    """Request to execute multiple tools in parallel."""
    calls: List[Dict[str, Any]] = Field(
        ...,
        description="List of tool calls: [{tool_id, parameters, reasoning}]"
    )
    session_id: Optional[str] = Field(None, description="Session grouping ID")


def get_tool_executor(db: Session = Depends(get_db)) -> KimiToolExecutor:
    return get_kimi_tool_executor(db)


@router.get("/tools")
async def list_available_tools(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    include_high_risk: bool = Query(default=True, description="Include high-risk tools"),
    executor: KimiToolExecutor = Depends(get_tool_executor),
):
    """
    List all tools Kimi can execute.

    Returns the complete tool registry organized by category.
    Kimi uses this to know what tools are available for execution.
    """
    try:
        tools = executor.list_tools(
            category=category,
            include_high_risk=include_high_risk,
        )
        categories = executor.list_categories()

        return {
            "total_tools": len(tools),
            "categories": categories,
            "tools": tools,
        }

    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools/{tool_id}")
async def get_tool_schema(
    tool_id: str,
    executor: KimiToolExecutor = Depends(get_tool_executor),
):
    """
    Get the full schema for a specific tool.

    Returns parameter definitions, risk level, and execution details.
    """
    schema = executor.get_tool_schema(tool_id)
    if not schema:
        raise HTTPException(
            status_code=404,
            detail=f"Tool not found: {tool_id}. Use /llm-learning/tools to see available tools."
        )
    return schema


@router.post("/tools/call")
async def call_tool(
    request: ToolCallRequest,
    executor: KimiToolExecutor = Depends(get_tool_executor),
    user=Depends(get_optional_user),
):
    """
    Execute a tool call.

    This is Kimi's main tool execution endpoint. Kimi decides what to do
    (intelligence) and calls this endpoint to actually do it (tool use).

    Every call is tracked for learning and pattern extraction.
    """
    try:
        result = await executor.call_tool(
            tool_id=request.tool_id,
            parameters=request.parameters,
            reasoning=request.reasoning,
            session_id=request.session_id,
        )

        return {
            "call_id": result.call_id,
            "tool_id": result.tool_id,
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "side_effects": result.side_effects,
            "files_affected": result.files_affected,
        }

    except Exception as e:
        logger.error(f"Error executing tool {request.tool_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tools/call-parallel")
async def call_tools_parallel(
    request: ParallelToolCallRequest,
    executor: KimiToolExecutor = Depends(get_tool_executor),
):
    """
    Execute multiple tools in parallel.

    Useful when Kimi needs to gather information from multiple
    system surfaces simultaneously (e.g., check git status AND
    run health check AND get KPIs all at once).
    """
    try:
        results = await executor.call_tools_parallel(
            calls=request.calls,
            session_id=request.session_id,
        )

        return {
            "total_calls": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "results": [
                {
                    "call_id": r.call_id,
                    "tool_id": r.tool_id,
                    "success": r.success,
                    "output": r.output,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                }
                for r in results
            ],
        }

    except Exception as e:
        logger.error(f"Error executing parallel tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools/stats")
async def get_tool_stats(
    executor: KimiToolExecutor = Depends(get_tool_executor),
):
    """Get Kimi's tool usage statistics."""
    try:
        return executor.get_stats()
    except Exception as e:
        logger.error(f"Error getting tool stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# KIMI BRAIN ENDPOINTS (READ-ONLY INTELLIGENCE)
# =======================================================================

class KimiAnalyzeRequest(BaseModel):
    """Request Kimi to analyze and produce instructions."""
    user_request: str = Field(..., description="What to analyze or what to do")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


def get_brain(db: Session = Depends(get_db)) -> KimiBrain:
    return get_kimi_brain(db)


def get_executor_instance(db: Session = Depends(get_db)) -> GraceVerifiedExecutor:
    return get_grace_verified_executor(db)


@router.get("/kimi/status")
async def get_kimi_status(
    brain: KimiBrain = Depends(get_brain),
):
    """
    Get Kimi brain status.

    Shows connected systems and recent analysis sessions.
    Kimi is read-only -- she observes and instructs, never executes.
    """
    try:
        return brain.get_status()
    except Exception as e:
        logger.error(f"Error getting Kimi status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kimi/read-state")
async def read_system_state(
    brain: KimiBrain = Depends(get_brain),
):
    """
    Kimi reads the current state of all Grace cognitive systems.

    READ-ONLY: Kimi observes mirror, diagnostics, learning,
    patterns, and interaction stats without modifying anything.
    """
    try:
        return brain.read_system_state()
    except Exception as e:
        logger.error(f"Error reading system state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kimi/diagnose")
async def kimi_diagnose(
    brain: KimiBrain = Depends(get_brain),
):
    """
    Kimi diagnoses the system -- identifies problems, gaps, opportunities.

    READ-ONLY: Pure analysis, produces diagnosis but does not execute fixes.
    """
    try:
        diagnosis = brain.diagnose()
        return {
            "diagnosis_id": diagnosis.diagnosis_id,
            "timestamp": diagnosis.timestamp.isoformat(),
            "system_health": diagnosis.system_health,
            "detected_problems": diagnosis.detected_problems,
            "learning_gaps": diagnosis.learning_gaps,
            "improvement_opportunities": diagnosis.improvement_opportunities,
            "overall_assessment": diagnosis.overall_assessment,
            "confidence": diagnosis.confidence,
        }
    except Exception as e:
        logger.error(f"Error in Kimi diagnosis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kimi/analyze")
async def kimi_analyze(
    request: KimiAnalyzeRequest,
    brain: KimiBrain = Depends(get_brain),
):
    """
    Kimi analyzes a request and produces instructions for Grace.

    Kimi READS system state, DIAGNOSES problems, and PRODUCES
    instructions. She does NOT execute anything.

    Returns an instruction set that can be passed to Grace for execution.
    """
    try:
        instruction_set = brain.produce_instructions(
            user_request=request.user_request,
            context=request.context,
        )

        return {
            "session_id": instruction_set.session_id,
            "summary": instruction_set.summary,
            "total_confidence": instruction_set.total_confidence,
            "diagnosis": {
                "id": instruction_set.diagnosis.diagnosis_id,
                "health": instruction_set.diagnosis.system_health,
                "problems": len(instruction_set.diagnosis.detected_problems),
                "assessment": instruction_set.diagnosis.overall_assessment,
            },
            "instructions": [
                {
                    "instruction_id": i.instruction_id,
                    "type": i.instruction_type.value,
                    "priority": i.priority.value,
                    "what": i.what,
                    "why": i.why,
                    "how": i.how,
                    "expected_outcome": i.expected_outcome,
                    "confidence": i.confidence,
                    "target_systems": i.target_systems,
                    "risks": i.risks,
                }
                for i in instruction_set.instructions
            ],
        }

    except Exception as e:
        logger.error(f"Error in Kimi analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# GRACE EXECUTOR ENDPOINTS (VERIFIES & EXECUTES)
# =======================================================================

@router.post("/grace/execute")
async def grace_execute_instructions(
    request: KimiAnalyzeRequest,
    brain: KimiBrain = Depends(get_brain),
    executor: GraceVerifiedExecutor = Depends(get_executor_instance),
    user=Depends(get_optional_user),
):
    """
    Full pipeline: Kimi analyzes -> Grace verifies -> Grace executes.

    1. Kimi reads system state and produces instructions (read-only)
    2. Grace verifies each instruction through her systems
    3. Grace executes approved instructions
    4. Results tracked for learning
    """
    try:
        instruction_set = brain.produce_instructions(
            user_request=request.user_request,
            context=request.context,
        )

        session_result = await executor.process_instruction_set(instruction_set)

        return {
            "kimi_session": instruction_set.session_id,
            "grace_session": session_result.session_id,
            "kimi_analysis": instruction_set.summary,
            "grace_execution": session_result.summary,
            "total_instructions": session_result.total_instructions,
            "approved": session_result.approved,
            "rejected": session_result.rejected,
            "succeeded": session_result.succeeded,
            "failed": session_result.failed,
            "instruction_results": [
                {
                    "instruction_id": r.instruction_id,
                    "type": r.instruction_type,
                    "verification": r.verification.value,
                    "verification_reason": r.verification_reason,
                    "executed": r.executed,
                    "success": r.success,
                    "output": r.output[:500] if r.output else None,
                    "error": r.error,
                    "steps": [
                        {"action": s.action, "success": s.success, "output": s.output[:200]}
                        for s in r.steps_completed
                    ],
                }
                for r in session_result.instruction_results
            ],
            "duration_ms": session_result.total_duration_ms,
        }

    except Exception as e:
        logger.error(f"Error in Grace execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grace/execution-stats")
async def get_grace_execution_stats(
    executor: GraceVerifiedExecutor = Depends(get_executor_instance),
):
    """Get Grace's execution statistics."""
    try:
        return executor.get_execution_stats()
    except Exception as e:
        logger.error(f"Error getting execution stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# VERIFICATION ENDPOINTS
# =======================================================================

class UserConfirmationRequest(BaseModel):
    """User response to a confirmation request."""
    check_id: str = Field(..., description="Check ID from pending confirmation")
    approved: bool = Field(..., description="Whether user approves the action")
    note: Optional[str] = Field(None, description="User's note/reason")


def get_verification_engine(db: Session = Depends(get_db)) -> GraceVerificationEngine:
    return get_grace_verification_engine(db)


@router.get("/grace/verification/stats")
async def get_verification_stats(
    engine: GraceVerificationEngine = Depends(get_verification_engine),
):
    """
    Get verification statistics.

    Shows how many instructions passed/failed verification,
    which sources caught issues, and pending confirmations.
    """
    try:
        return engine.get_verification_stats()
    except Exception as e:
        logger.error(f"Error getting verification stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grace/verification/pending")
async def get_pending_confirmations(
    engine: GraceVerificationEngine = Depends(get_verification_engine),
):
    """
    Get pending user confirmations.

    These are high-risk instructions that need user approval
    before Grace will execute them. Respond via this API or
    through WebSocket/chat/voice bidirectional comms.
    """
    try:
        pending = engine.get_pending_confirmations()
        return {
            "pending_count": len(pending),
            "confirmations": pending,
        }
    except Exception as e:
        logger.error(f"Error getting pending confirmations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grace/verification/confirm")
async def submit_user_confirmation(
    request: UserConfirmationRequest,
    engine: GraceVerificationEngine = Depends(get_verification_engine),
    user=Depends(get_optional_user),
):
    """
    Submit user confirmation for a pending verification check.

    This is the bidirectional comms endpoint. When Grace asks
    for user confirmation (for high-risk actions), the user
    responds here via chat, WebSocket, or voice API.
    """
    try:
        success = engine.submit_user_confirmation(
            check_id=request.check_id,
            approved=request.approved,
            user_note=request.note,
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"No pending confirmation found for check_id: {request.check_id}"
            )

        return {
            "check_id": request.check_id,
            "approved": request.approved,
            "status": "confirmation_recorded",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting confirmation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# HISTORICAL CHAT MINING
# =======================================================================

@router.post("/mine-history")
async def mine_historical_chats(
    limit: int = Query(default=500, le=5000, description="Max chats to mine"),
    db: Session = Depends(get_db),
):
    """
    Mine historical chat data to feed the learning system.

    Every past conversation becomes a training example.
    Extracts patterns from successful Q&A pairs.
    """
    try:
        from models.database_models import Chat
        from cognitive.learning_hook import track_learning_event

        chats = db.query(Chat).order_by(Chat.created_at.desc()).limit(limit).all()

        mined = 0
        for chat in chats:
            user_msg = getattr(chat, 'user_message', None) or ''
            assistant_msg = getattr(chat, 'assistant_message', None) or getattr(chat, 'response', None) or ''

            if user_msg and assistant_msg and len(user_msg) > 5:
                track_learning_event(
                    source="chat_history_mining",
                    description=user_msg[:200],
                    outcome="success",
                    confidence=0.6,
                    interaction_type="question_answer",
                    data={
                        "query": user_msg[:1000],
                        "response": assistant_msg[:1000],
                        "chat_id": getattr(chat, 'id', None),
                        "mined": True,
                    },
                )
                mined += 1

        return {
            "chats_scanned": len(chats),
            "interactions_mined": mined,
            "status": "complete",
        }

    except Exception as e:
        logger.error(f"Error mining history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# LIBRARY CONNECTORS - EXTERNAL DETERMINISTIC KNOWLEDGE
# =======================================================================

@router.post("/library/mine")
async def mine_library_knowledge(
    topic: str = Query(..., description="Topic to mine knowledge about"),
    sources: Optional[List[str]] = Query(default=None, description="Sources: wikidata, conceptnet, wolfram"),
    db: Session = Depends(get_db),
):
    """
    Mine external knowledge libraries for deterministic facts about a topic.

    Queries Wikidata, ConceptNet, and Wolfram Alpha (if configured).
    All results are 100% factual, not probabilistic.
    Facts are compiled directly into Grace's knowledge store.
    """
    try:
        from cognitive.library_connectors import get_library_connectors
        lib = get_library_connectors()
        return lib.mine_and_compile(topic=topic, session=db, sources=sources)
    except Exception as e:
        logger.error(f"Error mining library: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/library/wikidata")
async def query_wikidata(
    term: str = Query(..., description="Search term"),
    limit: int = Query(default=10, le=50),
):
    """Query Wikidata for structured facts. 100% deterministic."""
    try:
        from cognitive.library_connectors import get_library_connectors
        return get_library_connectors().query_wikidata(term, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/library/conceptnet")
async def query_conceptnet(
    term: str = Query(..., description="Term to look up"),
    limit: int = Query(default=20, le=50),
):
    """Query ConceptNet for common sense knowledge. 100% deterministic."""
    try:
        from cognitive.library_connectors import get_library_connectors
        return get_library_connectors().query_conceptnet(term, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# TASK COMPLETION VERIFIER
# =======================================================================

class CreateTaskRequest(BaseModel):
    title: str = Field(..., description="Task title")
    task_type: str = Field(default="new_module", description="new_module, bug_fix, integration, security_fix, api_endpoint")
    description: Optional[str] = Field(None)
    files: Optional[List[str]] = Field(None, description="Files involved")
    extra_criteria: Optional[List[Dict[str, Any]]] = Field(None, description="Additional completion criteria")

@router.post("/tasks/create")
async def create_verified_task(request: CreateTaskRequest, db: Session = Depends(get_db)):
    """Create a task with auto-generated completion criteria."""
    try:
        from cognitive.task_completion_verifier import get_task_completion_verifier
        verifier = get_task_completion_verifier(db)
        task = verifier.create_task(
            title=request.title, task_type=request.task_type,
            description=request.description, files=request.files,
            extra_criteria=request.extra_criteria,
        )
        return {"task_id": task.task_id, "title": task.title, "criteria_total": task.criteria_total, "status": task.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/verify")
async def verify_task(task_id: str, db: Session = Depends(get_db)):
    """Run verification checks. Returns what's done and what's not."""
    try:
        from cognitive.task_completion_verifier import get_task_completion_verifier
        verifier = get_task_completion_verifier(db)
        return verifier.verify(task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, db: Session = Depends(get_db)):
    """Mark task complete. ONLY works if 100% verified."""
    try:
        from cognitive.task_completion_verifier import get_task_completion_verifier
        verifier = get_task_completion_verifier(db)
        return verifier.mark_complete(task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/confirm/{criterion_id}")
async def confirm_criterion(task_id: str, criterion_id: str, passed: bool = True, db: Session = Depends(get_db)):
    """Manually confirm a criterion that can't be auto-checked."""
    try:
        from cognitive.task_completion_verifier import get_task_completion_verifier
        verifier = get_task_completion_verifier(db)
        verifier.confirm_criterion(task_id, criterion_id, passed)
        return {"status": "confirmed", "criterion": criterion_id, "passed": passed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks")
async def list_tasks(status: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    """List all tasks with completion status."""
    try:
        from cognitive.task_completion_verifier import get_task_completion_verifier
        verifier = get_task_completion_verifier(db)
        return verifier.get_all_tasks(status=status, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/stats")
async def get_task_stats(db: Session = Depends(get_db)):
    """Get task management statistics."""
    try:
        from cognitive.task_completion_verifier import get_task_completion_verifier
        verifier = get_task_completion_verifier(db)
        return verifier.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/schedule")
async def get_task_schedule(db: Session = Depends(get_db)):
    """Get schedule predictions for all active tasks. Uses TimeSense for estimates."""
    try:
        from cognitive.task_completion_verifier import get_task_completion_verifier
        verifier = get_task_completion_verifier(db)
        return verifier.get_schedule()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# TASK PLAYBOOK ENGINE
# =======================================================================

@router.post("/tasks/breakdown")
async def break_down_task(
    task_description: str = Query(..., description="What needs to be done"),
    task_type: str = Query(default="new_module"),
    db: Session = Depends(get_db),
):
    """
    Break down a task into ordered subtasks with dependencies.

    Checks playbooks first (instant, no LLM).
    Falls back to Kimi (LLM analysis).
    Falls back to heuristic (rule-based).

    Returns execution waves (dependency-ordered groups).
    """
    try:
        from cognitive.task_completion_verifier import get_task_completion_verifier
        verifier = get_task_completion_verifier(db)
        return verifier.break_down_and_create(task_description, task_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/playbooks")
async def list_playbooks(limit: int = 50, db: Session = Depends(get_db)):
    """List all saved task playbooks."""
    try:
        from cognitive.task_playbook_engine import get_task_playbook_engine
        engine = get_task_playbook_engine(db)
        return engine.list_playbooks(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/playbooks/stats")
async def get_playbook_stats(db: Session = Depends(get_db)):
    """Get playbook statistics including Kimi calls saved."""
    try:
        from cognitive.task_playbook_engine import get_task_playbook_engine
        engine = get_task_playbook_engine(db)
        return engine.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class InterrogateTaskRequest(BaseModel):
    task_description: str = Field(..., description="What the user wants done")
    answers: Optional[Dict[str, str]] = Field(None, description="Answers to previously asked questions")

@router.post("/tasks/interrogate")
async def interrogate_task(request: InterrogateTaskRequest, db: Session = Depends(get_db)):
    """
    Interrogate a task with WHAT/WHERE/WHEN/WHO/HOW/WHY before breaking it down.

    If the task description is vague, returns questions the user must answer.
    If the task is clear (or answers provided), returns the full breakdown.

    Call once to get questions. Call again with answers to get breakdown.
    """
    try:
        from cognitive.task_playbook_engine import get_task_playbook_engine
        engine = get_task_playbook_engine(db)
        return engine.interrogate_task(request.task_description, request.answers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# INTELLIGENCE FEEDBACK LOOPS
# =======================================================================

@router.get("/feedback-loops/recommendations")
async def get_feedback_recommendations(db: Session = Depends(get_db)):
    """Get improvement recommendations from all 11 feedback loops."""
    try:
        from cognitive.intelligence_feedback_loops import get_feedback_coordinator
        coordinator = get_feedback_coordinator(db)
        return coordinator.get_improvement_recommendations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feedback-loops/knowledge-gaps")
async def get_knowledge_gaps(db: Session = Depends(get_db)):
    """Get prioritized knowledge gaps to mine."""
    try:
        from cognitive.intelligence_feedback_loops import get_feedback_coordinator
        coordinator = get_feedback_coordinator(db)
        return {
            "priority_queue": coordinator.gap_queue.get_priority_queue()[:20],
            "top_gaps": coordinator.gap_queue.get_top_gaps(10),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feedback-loops/research-reliability")
async def get_research_reliability(db: Session = Depends(get_db)):
    """Get reliability scores for research sources."""
    try:
        from cognitive.intelligence_feedback_loops import get_feedback_coordinator
        coordinator = get_feedback_coordinator(db)
        return coordinator.research_tracker.get_source_reliability()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# SYSTEM INTEGRITY MONITOR
# =======================================================================

@router.get("/integrity/scan")
async def scan_system_integrity(db: Session = Depends(get_db)):
    """
    Full system integrity scan.

    Shows what's connected, what's broken, what's unknown.
    Kimi reads this automatically. Dashboard shows this.
    """
    try:
        from cognitive.system_integrity_monitor import get_system_integrity_monitor
        monitor = get_system_integrity_monitor(db)
        return monitor.full_scan()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/integrity/status")
async def quick_integrity_status(db: Session = Depends(get_db)):
    """Quick integrity status (cached, fast)."""
    try:
        from cognitive.system_integrity_monitor import get_system_integrity_monitor
        monitor = get_system_integrity_monitor(db)
        return monitor.get_quick_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# COMPILED KNOWLEDGE QUERIES (DETERMINISTIC - NO LLM)
# =======================================================================

@router.get("/compiled/facts")
async def query_compiled_facts(
    subject: Optional[str] = Query(default=None),
    predicate: Optional[str] = Query(default=None),
    domain: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """Query compiled facts. Pure deterministic SQL lookup."""
    try:
        from cognitive.knowledge_compiler import get_knowledge_compiler
        compiler = get_knowledge_compiler(db)
        return compiler.query_facts(subject, predicate, domain, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compiled/procedures")
async def query_compiled_procedures(
    goal: Optional[str] = Query(default=None),
    domain: Optional[str] = Query(default=None),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    """Query compiled procedures. Pure deterministic SQL lookup."""
    try:
        from cognitive.knowledge_compiler import get_knowledge_compiler
        compiler = get_knowledge_compiler(db)
        return compiler.query_procedures(goal, domain, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compiled/rules")
async def query_compiled_rules(
    domain: Optional[str] = Query(default=None),
    context: Optional[str] = Query(default=None),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    """Query compiled decision rules. Pure deterministic SQL lookup."""
    try:
        from cognitive.knowledge_compiler import get_knowledge_compiler
        compiler = get_knowledge_compiler(db)
        return compiler.query_rules(domain, context, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compiled/entities")
async def query_compiled_entities(
    entity: Optional[str] = Query(default=None),
    relation: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """Query entity relationships. Pure deterministic SQL lookup."""
    try:
        from cognitive.knowledge_compiler import get_knowledge_compiler
        compiler = get_knowledge_compiler(db)
        return compiler.query_entities(entity, relation, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compiled/stats")
async def get_compilation_stats(db: Session = Depends(get_db)):
    """Get knowledge compilation statistics."""
    try:
        from cognitive.knowledge_compiler import get_knowledge_compiler
        return get_knowledge_compiler(db).get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compile")
async def compile_knowledge(
    limit: int = Query(default=50, le=500),
    db: Session = Depends(get_db),
):
    """Compile raw document chunks into deterministic knowledge."""
    try:
        from cognitive.knowledge_compiler import get_knowledge_compiler
        return get_knowledge_compiler(db).compile_batch(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# KNOWLEDGE INDEXER (makes ALL internal knowledge RAG-searchable)
# =======================================================================

@router.post("/index/all")
async def index_all_knowledge(
    since_hours: int = Query(default=24, description="Index knowledge from last N hours"),
    db: Session = Depends(get_db),
):
    """
    Index all internal knowledge sources into vector store for RAG.

    Makes searchable: chats, tasks, playbooks, diagnostics,
    Genesis keys, user feedback, distilled knowledge.
    """
    try:
        from cognitive.knowledge_indexer import get_knowledge_indexer
        indexer = get_knowledge_indexer(db)
        return indexer.index_all_sources(since_hours=since_hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/stats")
async def get_index_stats(db: Session = Depends(get_db)):
    """Get knowledge indexer statistics."""
    try:
        from cognitive.knowledge_indexer import get_knowledge_indexer
        return get_knowledge_indexer(db).get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/retrieval-quality")
async def get_retrieval_quality(db: Session = Depends(get_db)):
    """Get retrieval quality report - which results are useful vs noise."""
    try:
        from cognitive.knowledge_indexer import get_retrieval_quality_tracker
        return get_retrieval_quality_tracker(db).get_quality_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/kimi/audit")
async def kimi_audit_system(db: Session = Depends(get_db)):
    """Kimi performs full system audit - scans for non-integrated components, knowledge gaps, security."""
    try:
        from cognitive.kimi_brain import get_kimi_brain
        kimi = get_kimi_brain(db)
        return kimi.audit_system()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
