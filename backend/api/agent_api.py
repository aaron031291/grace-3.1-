"""
Grace Agent API

REST API endpoints for Grace's software engineering agent.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging

from agent.grace_agent import GraceAgent, AgentConfig, TaskResult, TaskStatus
from execution.actions import GraceAction, ActionRequest, ActionResult
from execution.feedback import get_feedback_processor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


# ==================== Request/Response Models ====================

class TaskRequest(BaseModel):
    """Request to start a new task."""
    task: str = Field(..., description="Natural language description of the task")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    workspace: Optional[str] = Field(None, description="Workspace directory")
    max_iterations: int = Field(50, ge=1, le=200, description="Maximum iterations")
    auto_confirm: bool = Field(False, description="Auto-confirm dangerous actions")


class TaskResponse(BaseModel):
    """Response with task details."""
    task_id: str
    status: str
    summary: str
    output: Optional[str] = None
    error: Optional[str] = None
    actions_executed: int
    actions_succeeded: int
    actions_failed: int
    files_created: List[str]
    files_modified: List[str]
    files_deleted: List[str]
    patterns_learned: int
    duration_seconds: float
    started_at: datetime
    completed_at: Optional[datetime] = None


class ActionExecuteRequest(BaseModel):
    """Request to execute a single action."""
    action_type: str = Field(..., description="Action type (e.g., run_python, write_file)")
    parameters: Dict[str, Any] = Field(..., description="Action parameters")
    reasoning: Optional[str] = Field(None, description="Why this action")


class ActionResponse(BaseModel):
    """Response from action execution."""
    action_id: str
    action_type: str
    status: str
    output: str
    error: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: float
    files_affected: List[str]


class AgentStatusResponse(BaseModel):
    """Response with agent status."""
    running: bool
    current_task: Optional[str]
    tasks_completed: int
    tasks_failed: int
    total_actions: int
    success_rate: float
    patterns_learned: int


# ==================== State ====================

# Store running tasks
_running_tasks: Dict[str, asyncio.Task] = {}
_task_results: Dict[str, TaskResult] = {}

# Agent instance
_agent: Optional[GraceAgent] = None


def get_agent() -> GraceAgent:
    """Get or create the agent instance."""
    global _agent
    if _agent is None:
        _agent = GraceAgent()
    return _agent


# ==================== Endpoints ====================

@router.post("/task", response_model=TaskResponse)
async def start_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    Start a new software engineering task.

    The task runs in the background. Use /agent/task/{task_id} to check status.
    """
    agent = get_agent()

    # Configure agent
    agent.config.max_iterations = request.max_iterations
    if request.workspace:
        agent.config.workspace_dir = request.workspace

    # Create task
    task_id = f"TASK-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    # Start task in background
    async def run_task():
        try:
            result = await agent.solve_task(
                task=request.task,
                context=request.context or {},
            )
            _task_results[task_id] = result
        except Exception as e:
            logger.exception(f"Task {task_id} failed")
            _task_results[task_id] = TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error=str(e),
            )

    # Run in background
    task = asyncio.create_task(run_task())
    _running_tasks[task_id] = task

    # Return initial response
    return TaskResponse(
        task_id=task_id,
        status="pending",
        summary=f"Task started: {request.task[:100]}",
        actions_executed=0,
        actions_succeeded=0,
        actions_failed=0,
        files_created=[],
        files_modified=[],
        files_deleted=[],
        patterns_learned=0,
        duration_seconds=0,
        started_at=datetime.utcnow(),
    )


@router.get("/task/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a running or completed task.
    """
    # Check if completed
    if task_id in _task_results:
        result = _task_results[task_id]
        return TaskResponse(
            task_id=result.task_id,
            status=result.status.value,
            summary=result.summary,
            output=result.output,
            error=result.error,
            actions_executed=result.actions_executed,
            actions_succeeded=result.actions_succeeded,
            actions_failed=result.actions_failed,
            files_created=result.files_created,
            files_modified=result.files_modified,
            files_deleted=result.files_deleted,
            patterns_learned=result.patterns_learned,
            duration_seconds=result.duration_seconds,
            started_at=result.started_at,
            completed_at=result.completed_at,
        )

    # Check if running
    if task_id in _running_tasks:
        return TaskResponse(
            task_id=task_id,
            status="running",
            summary="Task in progress",
            actions_executed=0,
            actions_succeeded=0,
            actions_failed=0,
            files_created=[],
            files_modified=[],
            files_deleted=[],
            patterns_learned=0,
            duration_seconds=0,
            started_at=datetime.utcnow(),
        )

    raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")


@router.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    """
    Cancel a running task.
    """
    if task_id in _running_tasks:
        task = _running_tasks[task_id]
        task.cancel()
        del _running_tasks[task_id]

        # Store cancelled result
        _task_results[task_id] = TaskResult(
            task_id=task_id,
            status=TaskStatus.CANCELLED,
            summary="Task cancelled by user",
        )

        return {"status": "cancelled", "task_id": task_id}

    raise HTTPException(status_code=404, detail=f"Running task not found: {task_id}")


@router.post("/execute", response_model=ActionResponse)
async def execute_action(request: ActionExecuteRequest):
    """
    Execute a single action directly.

    Useful for testing or direct control.
    """
    agent = get_agent()

    # Parse action type
    try:
        action_type = GraceAction(request.action_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action type: {request.action_type}. "
                   f"Valid types: {[a.value for a in GraceAction]}"
        )

    # Create action request
    action = ActionRequest(
        action_type=action_type,
        parameters=request.parameters,
        reasoning=request.reasoning or "",
    )

    # Execute
    result = await agent.execution.execute(action)

    # Process feedback for learning
    if agent.config.learn_from_execution:
        await agent.feedback.process(action, result)

    return ActionResponse(
        action_id=result.action_id,
        action_type=result.action_type.value,
        status=result.status.value,
        output=result.output,
        error=result.error,
        exit_code=result.exit_code,
        execution_time=result.execution_time,
        files_affected=result.files_created + result.files_modified + result.files_deleted,
    )


@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status():
    """
    Get the overall status of the agent.
    """
    agent = get_agent()
    feedback = get_feedback_processor()
    stats = feedback.get_stats()

    running_count = len([t for t in _running_tasks.values() if not t.done()])
    completed_count = len([r for r in _task_results.values() if r.status == TaskStatus.COMPLETED])
    failed_count = len([r for r in _task_results.values() if r.status == TaskStatus.FAILED])

    return AgentStatusResponse(
        running=running_count > 0,
        current_task=agent.current_task,
        tasks_completed=completed_count,
        tasks_failed=failed_count,
        total_actions=stats.get("total_processed", 0),
        success_rate=stats.get("success_rate", 0),
        patterns_learned=stats.get("patterns_extracted", 0),
    )


@router.get("/actions")
async def list_available_actions():
    """
    List all available actions the agent can perform.
    """
    return {
        "actions": [
            {
                "name": action.value,
                "category": _categorize_action(action),
                "description": _describe_action(action),
            }
            for action in GraceAction
        ]
    }


@router.get("/history")
async def get_action_history(limit: int = 50):
    """
    Get recent action history.
    """
    agent = get_agent()
    history = agent.action_history[-limit:]

    return {
        "history": [
            {
                "action_id": action.action_id,
                "action_type": action.action_type.value,
                "parameters": action.parameters,
                "reasoning": action.reasoning,
                "result_status": result.status.value,
                "result_output": result.output[:500] if result.output else None,
                "execution_time": result.execution_time,
            }
            for action, result in history
        ],
        "total": len(history),
    }


@router.post("/learn")
async def trigger_learning():
    """
    Trigger learning from recent action history.
    """
    agent = get_agent()
    feedback = get_feedback_processor()

    signals_created = 0
    for action, result in agent.action_history[-20:]:
        signals = await feedback.process(action, result)
        signals_created += len(signals)

    return {
        "status": "success",
        "signals_created": signals_created,
        "stats": feedback.get_stats(),
    }


@router.delete("/history")
async def clear_history():
    """
    Clear action history.
    """
    agent = get_agent()
    count = len(agent.action_history)
    agent.action_history = []

    return {"cleared": count}


# ==================== Helper Functions ====================

def _categorize_action(action: GraceAction) -> str:
    """Categorize an action."""
    name = action.value
    if name.startswith("git_"):
        return "git"
    elif name.startswith("run_"):
        return "execution"
    elif name in ["read_file", "write_file", "edit_file", "delete_file"]:
        return "file"
    elif name in ["search_code", "grep_code", "find_files"]:
        return "search"
    elif name in ["think", "plan", "finish", "ask_user"]:
        return "control"
    else:
        return "other"


def _describe_action(action: GraceAction) -> str:
    """Get description of an action."""
    descriptions = {
        GraceAction.READ_FILE: "Read contents of a file",
        GraceAction.WRITE_FILE: "Write content to a file",
        GraceAction.EDIT_FILE: "Edit a file by replacing content",
        GraceAction.DELETE_FILE: "Delete a file",
        GraceAction.RUN_PYTHON: "Execute Python code",
        GraceAction.RUN_BASH: "Execute a bash command",
        GraceAction.RUN_TESTS: "Run tests using detected framework",
        GraceAction.RUN_PYTEST: "Run pytest tests",
        GraceAction.GIT_STATUS: "Get git status",
        GraceAction.GIT_DIFF: "Get git diff",
        GraceAction.GIT_ADD: "Stage files for commit",
        GraceAction.GIT_COMMIT: "Create a git commit",
        GraceAction.SEARCH_CODE: "Search code using ripgrep",
        GraceAction.FIND_FILES: "Find files matching pattern",
        GraceAction.THINK: "Record a thought (no execution)",
        GraceAction.PLAN: "Create an execution plan",
        GraceAction.FINISH: "Mark task as finished",
    }
    return descriptions.get(action, action.value)
