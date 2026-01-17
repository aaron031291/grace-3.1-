"""
Enterprise Coding Agent API

API endpoints for the Enterprise Coding Agent - same quality & standards as self-healing system.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from pathlib import Path

from database.session import get_session
from cognitive.enterprise_coding_agent import (
    get_enterprise_coding_agent,
    EnterpriseCodingAgent,
    CodingTaskType,
    CodeQualityLevel,
    CodingAgentState
)
from cognitive.autonomous_healing_system import TrustLevel

router = APIRouter(prefix="/coding-agent", tags=["coding-agent"])

# Global agent instance
_agent: Optional[EnterpriseCodingAgent] = None


def get_coding_agent(session: Session = Depends(get_session)) -> EnterpriseCodingAgent:
    """Get or create coding agent instance."""
    global _agent
    
    if _agent is None:
        from pathlib import Path
        _agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True,
            enable_sandbox=True
        )
    
    return _agent


# ==================== Request/Response Models ====================

class CreateTaskRequest(BaseModel):
    """Request to create a coding task."""
    task_type: str = Field(..., description="Type of coding task")
    description: str = Field(..., description="Task description")
    target_files: Optional[List[str]] = Field(None, description="Files to work on")
    requirements: Optional[Dict[str, Any]] = Field(None, description="Task requirements")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    priority: str = Field("medium", description="Task priority (low, medium, high, critical)")
    trust_level_required: Optional[int] = Field(None, description="Required trust level (0-9)")


class TaskResponse(BaseModel):
    """Response with task information."""
    task_id: str
    task_type: str
    description: str
    state: str
    priority: str
    genesis_key_id: Optional[str]
    created_at: str


class ExecuteTaskResponse(BaseModel):
    """Response from task execution."""
    success: bool
    task_id: str
    result: Optional[Dict[str, Any]]
    error: Optional[str]


class MetricsResponse(BaseModel):
    """Response with coding agent metrics."""
    total_tasks: int
    tasks_completed: int
    tasks_failed: int
    code_generated: int
    code_fixed: int
    tests_passed: int
    tests_failed: int
    average_trust_score: float
    average_quality_score: float
    learning_cycles: int


class HealthResponse(BaseModel):
    """Response with coding agent health status."""
    state: str
    active_tasks: int
    total_tasks: int
    completion_rate: float
    sandbox_available: bool
    systems_available: Dict[str, bool]


# ==================== API Endpoints ====================

@router.post("/task", response_model=TaskResponse)
async def create_task(
    request: CreateTaskRequest,
    agent: EnterpriseCodingAgent = Depends(get_coding_agent)
):
    """
    Create a coding task.
    
    Task types:
    - code_generation: Generate new code
    - code_fix: Fix existing code
    - code_refactor: Refactor code
    - code_optimize: Optimize code
    - code_review: Review code
    - code_document: Document code
    - code_test: Generate tests
    - code_migrate: Migrate code
    - feature_implement: Implement feature
    - bug_fix: Fix bug
    """
    try:
        # Convert task type string to enum
        task_type = CodingTaskType(request.task_type)
        
        # Convert trust level if provided
        trust_level = None
        if request.trust_level_required is not None:
            trust_level = TrustLevel(request.trust_level_required)
        
        # Create task
        task = agent.create_task(
            task_type=task_type,
            description=request.description,
            target_files=request.target_files,
            requirements=request.requirements,
            context=request.context,
            priority=request.priority,
            trust_level_required=trust_level
        )
        
        return TaskResponse(
            task_id=task.task_id,
            task_type=task.task_type.value,
            description=task.description,
            state=agent.current_state.value,
            priority=task.priority,
            genesis_key_id=task.genesis_key_id,
            created_at=task.created_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid task type or trust level: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.post("/task/{task_id}/execute", response_model=ExecuteTaskResponse)
async def execute_task(
    task_id: str,
    agent: EnterpriseCodingAgent = Depends(get_coding_agent)
):
    """
    Execute a coding task using OODA Loop.
    
    Phases:
    1. OBSERVE: Analyze requirements and context
    2. ORIENT: Retrieve relevant knowledge from Memory Mesh
    3. DECIDE: Choose approach and generate code
    4. ACT: Apply code (in sandbox or real)
    """
    try:
        result = agent.execute_task(task_id)
        
        return ExecuteTaskResponse(
            success=result.get("success", False),
            task_id=task_id,
            result=result if result.get("success") else None,
            error=result.get("error") if not result.get("success") else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute task: {str(e)}")


@router.get("/task/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    agent: EnterpriseCodingAgent = Depends(get_coding_agent)
):
    """Get task information."""
    try:
        if task_id not in agent.active_tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = agent.active_tasks[task_id]
        
        return TaskResponse(
            task_id=task.task_id,
            task_type=task.task_type.value,
            description=task.description,
            state=agent.current_state.value,
            priority=task.priority,
            genesis_key_id=task.genesis_key_id,
            created_at=task.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")


@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    agent: EnterpriseCodingAgent = Depends(get_coding_agent)
):
    """List all active tasks."""
    try:
        tasks = []
        for task in agent.active_tasks.values():
            tasks.append(TaskResponse(
                task_id=task.task_id,
                task_type=task.task_type.value,
                description=task.description,
                state=agent.current_state.value,
                priority=task.priority,
                genesis_key_id=task.genesis_key_id,
                created_at=task.created_at.isoformat()
            ))
        
        return tasks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    agent: EnterpriseCodingAgent = Depends(get_coding_agent)
):
    """Get coding agent metrics."""
    try:
        metrics = agent.get_metrics()
        
        return MetricsResponse(
            total_tasks=metrics.total_tasks,
            tasks_completed=metrics.tasks_completed,
            tasks_failed=metrics.tasks_failed,
            code_generated=metrics.code_generated,
            code_fixed=metrics.code_fixed,
            tests_passed=metrics.tests_passed,
            tests_failed=metrics.tests_failed,
            average_trust_score=metrics.average_trust_score,
            average_quality_score=metrics.average_quality_score,
            learning_cycles=metrics.learning_cycles
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/health", response_model=HealthResponse)
async def get_health(
    agent: EnterpriseCodingAgent = Depends(get_coding_agent)
):
    """Get coding agent health status."""
    try:
        health = agent.get_health_status()
        
        return HealthResponse(
            state=health["state"],
            active_tasks=health["active_tasks"],
            total_tasks=health["total_tasks"],
            completion_rate=health["completion_rate"],
            sandbox_available=health["sandbox_available"],
            systems_available=health["systems_available"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health: {str(e)}")


@router.post("/sandbox/cleanup")
async def cleanup_sandbox(
    agent: EnterpriseCodingAgent = Depends(get_coding_agent)
):
    """Cleanup sandbox."""
    try:
        agent.cleanup_sandbox()
        return {"success": True, "message": "Sandbox cleaned up"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup sandbox: {str(e)}")


@router.post("/sandbox/practice")
async def practice_in_sandbox(
    request: CreateTaskRequest,
    agent: EnterpriseCodingAgent = Depends(get_coding_agent)
):
    """
    Practice coding tasks in sandbox (integrated with self-healing training).
    
    This allows the coding agent to practice and learn in a safe sandbox environment.
    """
    try:
        task_type = CodingTaskType(request.task_type)
        
        result = agent.practice_in_sandbox(
            task_type=task_type,
            description=request.description,
            difficulty_level=1
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid task type: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to practice in sandbox: {str(e)}")


@router.get("/learning/connections")
async def get_learning_connections(
    agent: EnterpriseCodingAgent = Depends(get_coding_agent)
):
    """
    Get information about learning connections.
    
    Returns:
    - Memory Mesh connection status
    - Sandbox training connection status
    - Federated learning connection status
    - Learning cycles count
    """
    try:
        connections = agent.get_learning_connections()
        return connections
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get learning connections: {str(e)}")


@router.post("/healing/request")
async def request_healing_assistance(
    request: Dict[str, Any],
    agent: EnterpriseCodingAgent = Depends(get_coding_agent)
):
    """
    Request assistance from Self-Healing System.
    
    Use cases:
    - Code generation failed
    - Code has issues that need healing
    - Need diagnostic analysis
    """
    try:
        result = agent.request_healing_assistance(
            issue_description=request.get("issue_description", ""),
            affected_files=request.get("affected_files", []),
            issue_type=request.get("issue_type", "code_issue"),
            priority=request.get("priority", "medium")
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to request healing: {str(e)}")


@router.post("/healing/diagnostic")
async def request_diagnostic(
    request: Dict[str, Any],
    agent: EnterpriseCodingAgent = Depends(get_coding_agent)
):
    """Request diagnostic analysis from Self-Healing System."""
    try:
        result = agent.request_diagnostic(
            description=request.get("description", ""),
            context=request.get("context", {})
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to request diagnostic: {str(e)}")
