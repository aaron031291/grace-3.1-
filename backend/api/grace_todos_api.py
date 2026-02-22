"""
Grace Todos API - Autonomous Task Management System

Full integration with Grace backend systems:
- Autonomous task tracking across entire system
- Sub-agents and multi-threading
- Parallel and background processing
- Scheduling and prioritization
- Team management with skill-based assignment
- Genesis ID tracking for all tasks

Classes:
- `TaskStatus`
- `TaskPriority`
- `TaskType`
- `ProcessingMode`
- `AgentType`
- `GraceTask`
- `UserRequirement`
- `TeamMember`
- `GraceAgent`
- `AutonomousAction`
- `TaskBoard`

Key Methods:
- `generate_genesis_id()`
- `get_best_assignee()`
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

router = APIRouter(prefix="/api/grace-todos", tags=["Grace Todos"])

# ============================================================================
# Enums
# ============================================================================

class TaskStatus(str, Enum):
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"

class TaskType(str, Enum):
    AUTONOMOUS = "autonomous"
    USER_REQUEST = "user_request"
    SCHEDULED = "scheduled"
    SUB_AGENT = "sub_agent"
    LEARNING = "learning"
    DIAGNOSTIC = "diagnostic"
    HEALING = "healing"
    MEMORY = "memory"
    ANALYSIS = "analysis"
    INGESTION = "ingestion"

class ProcessingMode(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BACKGROUND = "background"
    MULTI_THREAD = "multi_thread"
    DISTRIBUTED = "distributed"

class AgentType(str, Enum):
    MAIN = "main"
    SUB_AGENT = "sub_agent"
    WORKER = "worker"
    SPECIALIST = "specialist"
    COORDINATOR = "coordinator"

# ============================================================================
# Models
# ============================================================================

class GraceTask(BaseModel):
    genesis_key_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    task_type: TaskType = TaskType.AUTONOMOUS
    status: TaskStatus = TaskStatus.QUEUED
    priority: TaskPriority = TaskPriority.MEDIUM
    processing_mode: ProcessingMode = ProcessingMode.SEQUENTIAL

    # Assignment
    assignee_genesis_id: Optional[str] = None
    assigned_agent: Optional[str] = None
    agent_type: AgentType = AgentType.MAIN

    # Scheduling
    scheduled_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    estimated_duration_ms: Optional[int] = None

    # Progress
    progress_percent: int = 0
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    completed_steps: int = 0

    # Sub-tasks
    parent_task_id: Optional[str] = None
    sub_task_ids: List[str] = []
    dependencies: List[str] = []

    # Execution
    execution_context: Dict[str, Any] = {}
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Grace systems integration
    memory_context_ids: List[str] = []
    genesis_lineage: List[str] = []
    diagnostic_triggers: List[str] = []
    learning_insights: List[str] = []

    # Metadata
    labels: List[str] = []
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    version: int = 1


class UserRequirement(BaseModel):
    genesis_key_id: Optional[str] = None
    user_genesis_id: str
    title: str
    description: str
    requirements: List[str] = []
    acceptance_criteria: List[str] = []
    priority: TaskPriority = TaskPriority.MEDIUM
    status: Literal["draft", "active", "in_progress", "completed", "archived"] = "draft"
    generated_tasks: List[str] = []
    assigned_team: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TeamMember(BaseModel):
    genesis_key_id: str
    name: str
    display_name: str
    role: Literal["developer", "analyst", "reviewer", "lead", "specialist", "agent"] = "developer"
    skill_sets: List[str] = []
    specializations: List[str] = []
    capacity: int = 100  # Percentage of availability
    current_load: int = 0
    assigned_tasks: List[str] = []
    completed_tasks: int = 0
    is_active: bool = True
    is_agent: bool = False  # True if this is a Grace sub-agent
    last_activity: Optional[datetime] = None


class GraceAgent(BaseModel):
    agent_id: str
    name: str
    agent_type: AgentType
    status: Literal["idle", "busy", "processing", "error", "offline"] = "idle"
    capabilities: List[str] = []
    current_task_id: Optional[str] = None
    task_queue: List[str] = []
    processing_mode: ProcessingMode = ProcessingMode.SEQUENTIAL
    max_concurrent: int = 1
    active_threads: int = 0
    total_processed: int = 0
    success_rate: float = 1.0
    avg_processing_time_ms: float = 0
    created_at: datetime = Field(default_factory=datetime.now)


class AutonomousAction(BaseModel):
    action_id: str
    task_id: str
    agent_id: str
    action_type: str
    description: str
    input_data: Dict[str, Any] = {}
    output_data: Optional[Dict[str, Any]] = None
    status: Literal["pending", "executing", "completed", "failed"] = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None


class TaskBoard(BaseModel):
    queued: List[GraceTask] = []
    scheduled: List[GraceTask] = []
    running: List[GraceTask] = []
    paused: List[GraceTask] = []
    completed: List[GraceTask] = []
    failed: List[GraceTask] = []


# ============================================================================
# In-Memory Storage (Replace with DB in production)
# ============================================================================

tasks_store: Dict[str, GraceTask] = {}
requirements_store: Dict[str, UserRequirement] = {}
team_store: Dict[str, TeamMember] = {}
agents_store: Dict[str, GraceAgent] = {}
actions_store: Dict[str, AutonomousAction] = {}
active_websockets: List[WebSocket] = []

# Thread/Process pools
thread_pool = ThreadPoolExecutor(max_workers=10)
process_pool = ProcessPoolExecutor(max_workers=4)

# ============================================================================
# Helper Functions
# ============================================================================

def generate_genesis_id(prefix: str = "GT") -> str:
    """Generate unique Genesis ID for tasks"""
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


async def broadcast_update(update_type: str, data: Dict[str, Any]):
    """Broadcast updates to all connected WebSocket clients"""
    message = json.dumps({
        "type": update_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    })
    for ws in active_websockets:
        try:
            await ws.send_text(message)
        except:
            pass


def get_best_assignee(task: GraceTask) -> Optional[str]:
    """Auto-assign task to best team member based on skills"""
    if not team_store:
        return None

    best_match = None
    best_score = 0

    task_labels = set(task.labels)

    for member in team_store.values():
        if not member.is_active:
            continue
        if member.current_load >= member.capacity:
            continue

        # Calculate match score based on skills
        member_skills = set(member.skill_sets + member.specializations)
        overlap = len(task_labels & member_skills)

        # Factor in current load (prefer less loaded members)
        load_factor = 1 - (member.current_load / 100)
        score = overlap * load_factor

        if score > best_score:
            best_score = score
            best_match = member.genesis_key_id

    return best_match


async def execute_task_async(task_id: str):
    """Execute a task asynchronously"""
    task = tasks_store.get(task_id)
    if not task:
        return

    task.status = TaskStatus.RUNNING
    task.started_at = datetime.now()
    await broadcast_update("task_started", {"task_id": task_id})

    try:
        # Simulate task execution
        for step in range(task.total_steps or 5):
            task.current_step = f"Step {step + 1}"
            task.completed_steps = step + 1
            task.progress_percent = int((step + 1) / (task.total_steps or 5) * 100)
            await broadcast_update("task_progress", {
                "task_id": task_id,
                "progress": task.progress_percent,
                "step": task.current_step
            })
            await asyncio.sleep(0.5)  # Simulate work

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.progress_percent = 100
        task.result = {"success": True, "message": "Task completed successfully"}

        await broadcast_update("task_completed", {"task_id": task_id})

    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error = str(e)
        task.completed_at = datetime.now()
        await broadcast_update("task_failed", {"task_id": task_id, "error": str(e)})


# ============================================================================
# Task CRUD Endpoints
# ============================================================================

@router.post("/tasks", response_model=GraceTask)
async def create_task(task: GraceTask, background_tasks: BackgroundTasks):
    """Create a new Grace task"""
    task.genesis_key_id = generate_genesis_id("GT")
    task.created_at = datetime.now()
    task.updated_at = datetime.now()

    # Auto-assign if no assignee
    if not task.assignee_genesis_id:
        task.assignee_genesis_id = get_best_assignee(task)

    tasks_store[task.genesis_key_id] = task

    # Broadcast creation
    await broadcast_update("task_created", task.dict())

    # Auto-execute if high priority and autonomous
    if task.priority in [TaskPriority.CRITICAL, TaskPriority.HIGH] and task.task_type == TaskType.AUTONOMOUS:
        background_tasks.add_task(execute_task_async, task.genesis_key_id)

    return task


@router.get("/tasks", response_model=List[GraceTask])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    task_type: Optional[TaskType] = None,
    assignee: Optional[str] = None,
    limit: int = 100
):
    """List tasks with optional filters"""
    tasks = list(tasks_store.values())

    if status:
        tasks = [t for t in tasks if t.status == status]
    if priority:
        tasks = [t for t in tasks if t.priority == priority]
    if task_type:
        tasks = [t for t in tasks if t.task_type == task_type]
    if assignee:
        tasks = [t for t in tasks if t.assignee_genesis_id == assignee]

    # Sort by priority and created_at
    priority_order = {
        TaskPriority.CRITICAL: 0,
        TaskPriority.HIGH: 1,
        TaskPriority.MEDIUM: 2,
        TaskPriority.LOW: 3,
        TaskPriority.BACKGROUND: 4
    }
    tasks.sort(key=lambda t: (priority_order.get(t.priority, 5), t.created_at))

    return tasks[:limit]


@router.get("/tasks/{task_id}", response_model=GraceTask)
async def get_task(task_id: str):
    """Get a specific task"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/tasks/{task_id}", response_model=GraceTask)
async def update_task(task_id: str, updates: Dict[str, Any]):
    """Update a task"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for key, value in updates.items():
        if hasattr(task, key):
            setattr(task, key, value)

    task.updated_at = datetime.now()
    task.version += 1

    await broadcast_update("task_updated", {"task_id": task_id, "updates": updates})

    return task


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task"""
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="Task not found")

    del tasks_store[task_id]
    await broadcast_update("task_deleted", {"task_id": task_id})

    return {"status": "deleted", "task_id": task_id}


@router.post("/tasks/{task_id}/move")
async def move_task(task_id: str, new_status: TaskStatus, position: Optional[int] = None):
    """Move task to a different status column"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = task.status
    task.status = new_status
    task.updated_at = datetime.now()

    await broadcast_update("task_moved", {
        "task_id": task_id,
        "old_status": old_status.value,
        "new_status": new_status.value,
        "position": position
    })

    return task


@router.post("/tasks/{task_id}/reorder")
async def reorder_task(task_id: str, new_position: int):
    """Reorder task within its column (for drag-drop)"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await broadcast_update("task_reordered", {
        "task_id": task_id,
        "status": task.status.value,
        "position": new_position
    })

    return {"status": "reordered", "task_id": task_id, "position": new_position}


# ============================================================================
# Board Endpoints
# ============================================================================

@router.get("/board", response_model=TaskBoard)
async def get_board():
    """Get full task board organized by status"""
    board = TaskBoard()

    for task in tasks_store.values():
        if task.status == TaskStatus.QUEUED:
            board.queued.append(task)
        elif task.status == TaskStatus.SCHEDULED:
            board.scheduled.append(task)
        elif task.status == TaskStatus.RUNNING:
            board.running.append(task)
        elif task.status == TaskStatus.PAUSED:
            board.paused.append(task)
        elif task.status == TaskStatus.COMPLETED:
            board.completed.append(task)
        elif task.status == TaskStatus.FAILED:
            board.failed.append(task)

    # Sort each column by priority
    priority_order = {
        TaskPriority.CRITICAL: 0,
        TaskPriority.HIGH: 1,
        TaskPriority.MEDIUM: 2,
        TaskPriority.LOW: 3,
        TaskPriority.BACKGROUND: 4
    }

    for column in [board.queued, board.scheduled, board.running, board.paused]:
        column.sort(key=lambda t: priority_order.get(t.priority, 5))

    # Sort completed/failed by completion time
    board.completed.sort(key=lambda t: t.completed_at or t.created_at, reverse=True)
    board.failed.sort(key=lambda t: t.completed_at or t.created_at, reverse=True)

    return board


@router.get("/board/stats")
async def get_board_stats():
    """Get board statistics"""
    tasks = list(tasks_store.values())

    return {
        "total": len(tasks),
        "by_status": {
            status.value: len([t for t in tasks if t.status == status])
            for status in TaskStatus
        },
        "by_priority": {
            priority.value: len([t for t in tasks if t.priority == priority])
            for priority in TaskPriority
        },
        "by_type": {
            task_type.value: len([t for t in tasks if t.task_type == task_type])
            for task_type in TaskType
        },
        "autonomous_active": len([t for t in tasks if t.task_type == TaskType.AUTONOMOUS and t.status == TaskStatus.RUNNING]),
        "completion_rate": len([t for t in tasks if t.status == TaskStatus.COMPLETED]) / len(tasks) if tasks else 0,
        "avg_progress": sum(t.progress_percent for t in tasks if t.status == TaskStatus.RUNNING) / len([t for t in tasks if t.status == TaskStatus.RUNNING]) if [t for t in tasks if t.status == TaskStatus.RUNNING] else 0
    }


# ============================================================================
# Autonomous Execution Endpoints
# ============================================================================

@router.post("/tasks/{task_id}/execute")
async def execute_task(task_id: str, background_tasks: BackgroundTasks):
    """Execute a task"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == TaskStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Task already running")

    background_tasks.add_task(execute_task_async, task_id)

    return {"status": "executing", "task_id": task_id}


@router.post("/tasks/{task_id}/pause")
async def pause_task(task_id: str):
    """Pause a running task"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Task not running")

    task.status = TaskStatus.PAUSED
    task.updated_at = datetime.now()

    await broadcast_update("task_paused", {"task_id": task_id})

    return task


@router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str, background_tasks: BackgroundTasks):
    """Resume a paused task"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Task not paused")

    background_tasks.add_task(execute_task_async, task_id)

    return {"status": "resuming", "task_id": task_id}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a task"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = TaskStatus.CANCELLED
    task.updated_at = datetime.now()
    task.completed_at = datetime.now()

    await broadcast_update("task_cancelled", {"task_id": task_id})

    return task


@router.post("/tasks/{task_id}/retry")
async def retry_task(task_id: str, background_tasks: BackgroundTasks):
    """Retry a failed task"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.FAILED:
        raise HTTPException(status_code=400, detail="Task not failed")

    if task.retry_count >= task.max_retries:
        raise HTTPException(status_code=400, detail="Max retries exceeded")

    task.retry_count += 1
    task.error = None
    task.status = TaskStatus.QUEUED

    background_tasks.add_task(execute_task_async, task_id)

    return {"status": "retrying", "task_id": task_id, "retry_count": task.retry_count}


# ============================================================================
# Sub-Tasks & Dependencies
# ============================================================================

@router.post("/tasks/{task_id}/subtasks", response_model=GraceTask)
async def create_subtask(task_id: str, subtask: GraceTask):
    """Create a subtask under a parent task"""
    parent = tasks_store.get(task_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent task not found")

    subtask.genesis_key_id = generate_genesis_id("GST")
    subtask.parent_task_id = task_id
    subtask.task_type = TaskType.SUB_AGENT
    subtask.created_at = datetime.now()

    tasks_store[subtask.genesis_key_id] = subtask
    parent.sub_task_ids.append(subtask.genesis_key_id)

    await broadcast_update("subtask_created", {
        "parent_id": task_id,
        "subtask_id": subtask.genesis_key_id
    })

    return subtask


@router.get("/tasks/{task_id}/subtasks", response_model=List[GraceTask])
async def get_subtasks(task_id: str):
    """Get all subtasks for a task"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return [tasks_store[sid] for sid in task.sub_task_ids if sid in tasks_store]


# ============================================================================
# User Requirements Endpoints
# ============================================================================

@router.post("/requirements", response_model=UserRequirement)
async def create_requirement(req: UserRequirement):
    """Create a user requirement (job request)"""
    req.genesis_key_id = generate_genesis_id("GR")
    req.created_at = datetime.now()

    requirements_store[req.genesis_key_id] = req

    await broadcast_update("requirement_created", req.dict())

    return req


@router.get("/requirements", response_model=List[UserRequirement])
async def list_requirements(
    user_id: Optional[str] = None,
    status: Optional[str] = None
):
    """List user requirements"""
    reqs = list(requirements_store.values())

    if user_id:
        reqs = [r for r in reqs if r.user_genesis_id == user_id]
    if status:
        reqs = [r for r in reqs if r.status == status]

    return reqs


@router.get("/requirements/{req_id}", response_model=UserRequirement)
async def get_requirement(req_id: str):
    """Get a specific requirement"""
    req = requirements_store.get(req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return req


@router.post("/requirements/{req_id}/generate-tasks")
async def generate_tasks_from_requirement(req_id: str, background_tasks: BackgroundTasks):
    """Auto-generate tasks from a user requirement"""
    req = requirements_store.get(req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    generated_tasks = []

    # Generate tasks from requirements list
    for i, requirement in enumerate(req.requirements):
        task = GraceTask(
            genesis_key_id=generate_genesis_id("GT"),
            title=f"Implement: {requirement[:50]}...",
            description=requirement,
            task_type=TaskType.USER_REQUEST,
            priority=req.priority,
            created_by=req.user_genesis_id,
            labels=[f"requirement:{req_id}"]
        )
        tasks_store[task.genesis_key_id] = task
        generated_tasks.append(task.genesis_key_id)
        req.generated_tasks.append(task.genesis_key_id)

    req.status = "in_progress"
    req.updated_at = datetime.now()

    await broadcast_update("tasks_generated", {
        "requirement_id": req_id,
        "task_ids": generated_tasks
    })

    return {"generated": len(generated_tasks), "task_ids": generated_tasks}


# ============================================================================
# Team Management Endpoints
# ============================================================================

@router.post("/team", response_model=TeamMember)
async def add_team_member(member: TeamMember):
    """Add a team member"""
    if not member.genesis_key_id:
        member.genesis_key_id = generate_genesis_id("GM")

    team_store[member.genesis_key_id] = member

    await broadcast_update("team_member_added", member.dict())

    return member


@router.get("/team", response_model=List[TeamMember])
async def list_team():
    """List all team members"""
    return list(team_store.values())


@router.get("/team/{member_id}", response_model=TeamMember)
async def get_team_member(member_id: str):
    """Get a specific team member"""
    member = team_store.get(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    return member


@router.put("/team/{member_id}", response_model=TeamMember)
async def update_team_member(member_id: str, updates: Dict[str, Any]):
    """Update a team member"""
    member = team_store.get(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")

    for key, value in updates.items():
        if hasattr(member, key):
            setattr(member, key, value)

    return member


@router.post("/team/{member_id}/assign/{task_id}")
async def assign_task_to_member(member_id: str, task_id: str):
    """Assign a task to a team member"""
    member = team_store.get(member_id)
    task = tasks_store.get(task_id)

    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.assignee_genesis_id = member_id
    member.assigned_tasks.append(task_id)
    member.current_load += 10  # Increase load

    await broadcast_update("task_assigned", {
        "task_id": task_id,
        "member_id": member_id
    })

    return {"assigned": True, "task_id": task_id, "member_id": member_id}


@router.post("/team/auto-assign/{task_id}")
async def auto_assign_task(task_id: str):
    """Auto-assign task based on skills"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    best_assignee = get_best_assignee(task)

    if best_assignee:
        task.assignee_genesis_id = best_assignee
        member = team_store[best_assignee]
        member.assigned_tasks.append(task_id)
        member.current_load += 10

        await broadcast_update("task_auto_assigned", {
            "task_id": task_id,
            "member_id": best_assignee
        })

        return {"assigned": True, "task_id": task_id, "member_id": best_assignee}

    return {"assigned": False, "reason": "No suitable team member found"}


# ============================================================================
# Grace Agents Endpoints
# ============================================================================

@router.post("/agents", response_model=GraceAgent)
async def create_agent(agent: GraceAgent):
    """Create a Grace agent"""
    if not agent.agent_id:
        agent.agent_id = generate_genesis_id("GA")

    agents_store[agent.agent_id] = agent

    await broadcast_update("agent_created", agent.dict())

    return agent


@router.get("/agents", response_model=List[GraceAgent])
async def list_agents():
    """List all Grace agents"""
    return list(agents_store.values())


@router.get("/agents/{agent_id}", response_model=GraceAgent)
async def get_agent(agent_id: str):
    """Get a specific agent"""
    agent = agents_store.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/agents/{agent_id}/assign/{task_id}")
async def assign_task_to_agent(agent_id: str, task_id: str, background_tasks: BackgroundTasks):
    """Assign a task to a Grace agent for autonomous execution"""
    agent = agents_store.get(agent_id)
    task = tasks_store.get(task_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.assigned_agent = agent_id
    task.agent_type = agent.agent_type
    agent.task_queue.append(task_id)

    # Auto-execute if agent is idle
    if agent.status == "idle":
        agent.status = "busy"
        agent.current_task_id = task_id
        background_tasks.add_task(execute_task_async, task_id)

    await broadcast_update("task_assigned_to_agent", {
        "task_id": task_id,
        "agent_id": agent_id
    })

    return {"assigned": True, "task_id": task_id, "agent_id": agent_id}


# ============================================================================
# Scheduling Endpoints
# ============================================================================

@router.post("/schedule")
async def schedule_task(
    task_id: str,
    scheduled_at: datetime,
    background_tasks: BackgroundTasks
):
    """Schedule a task for later execution"""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.scheduled_at = scheduled_at
    task.status = TaskStatus.SCHEDULED
    task.updated_at = datetime.now()

    await broadcast_update("task_scheduled", {
        "task_id": task_id,
        "scheduled_at": scheduled_at.isoformat()
    })

    return {"scheduled": True, "task_id": task_id, "scheduled_at": scheduled_at}


@router.get("/schedule")
async def get_scheduled_tasks():
    """Get all scheduled tasks"""
    scheduled = [t for t in tasks_store.values() if t.status == TaskStatus.SCHEDULED]
    scheduled.sort(key=lambda t: t.scheduled_at or datetime.max)
    return scheduled


# ============================================================================
# Parallel Processing Endpoints
# ============================================================================

@router.post("/parallel/execute")
async def execute_parallel(task_ids: List[str], background_tasks: BackgroundTasks):
    """Execute multiple tasks in parallel"""
    valid_tasks = []

    for task_id in task_ids:
        task = tasks_store.get(task_id)
        if task and task.status not in [TaskStatus.RUNNING, TaskStatus.COMPLETED]:
            task.processing_mode = ProcessingMode.PARALLEL
            valid_tasks.append(task_id)
            background_tasks.add_task(execute_task_async, task_id)

    await broadcast_update("parallel_execution_started", {"task_ids": valid_tasks})

    return {"executing": len(valid_tasks), "task_ids": valid_tasks}


@router.post("/background/execute")
async def execute_background(task_ids: List[str], background_tasks: BackgroundTasks):
    """Execute tasks in background with low priority"""
    for task_id in task_ids:
        task = tasks_store.get(task_id)
        if task:
            task.processing_mode = ProcessingMode.BACKGROUND
            task.priority = TaskPriority.BACKGROUND
            background_tasks.add_task(execute_task_async, task_id)

    return {"queued_for_background": len(task_ids)}


# ============================================================================
# WebSocket for Real-time Updates
# ============================================================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time task updates"""
    await websocket.accept()
    active_websockets.append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif message.get("type") == "subscribe":
                await websocket.send_json({
                    "type": "subscribed",
                    "channels": message.get("channels", [])
                })
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
    except Exception:
        if websocket in active_websockets:
            active_websockets.remove(websocket)


# ============================================================================
# Grace System Integration Endpoints
# ============================================================================

@router.get("/grace/thinking")
async def get_grace_thinking():
    """Get Grace's current thinking/processing state"""
    running_tasks = [t for t in tasks_store.values() if t.status == TaskStatus.RUNNING]
    queued_tasks = [t for t in tasks_store.values() if t.status == TaskStatus.QUEUED]

    return {
        "current_thoughts": [
            {
                "task_id": t.genesis_key_id,
                "title": t.title,
                "progress": t.progress_percent,
                "current_step": t.current_step
            }
            for t in running_tasks
        ],
        "pending_thoughts": len(queued_tasks),
        "total_capacity": 100,
        "current_load": len(running_tasks) * 20,
        "agents_active": len([a for a in agents_store.values() if a.status == "busy"])
    }


@router.post("/grace/prioritize")
async def reprioritize_tasks():
    """Let Grace reprioritize all tasks autonomously"""
    tasks = list(tasks_store.values())

    # Simple prioritization logic (can be enhanced with ML)
    for task in tasks:
        if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            continue

        # Increase priority if deadline approaching
        if task.deadline:
            time_until_deadline = (task.deadline - datetime.now()).total_seconds()
            if time_until_deadline < 3600:  # Less than 1 hour
                task.priority = TaskPriority.CRITICAL
            elif time_until_deadline < 86400:  # Less than 1 day
                task.priority = TaskPriority.HIGH

        # Increase priority if many dependencies waiting
        dependents = [t for t in tasks if task.genesis_key_id in t.dependencies]
        if len(dependents) >= 3:
            if task.priority == TaskPriority.LOW:
                task.priority = TaskPriority.MEDIUM
            elif task.priority == TaskPriority.MEDIUM:
                task.priority = TaskPriority.HIGH

    await broadcast_update("tasks_reprioritized", {"count": len(tasks)})

    return {"reprioritized": len(tasks)}


@router.post("/grace/scale")
async def scale_processing(max_concurrent: int = 5):
    """Scale Grace's processing capacity"""
    for agent in agents_store.values():
        agent.max_concurrent = max_concurrent

    return {
        "scaled": True,
        "max_concurrent": max_concurrent,
        "agents_updated": len(agents_store)
    }
