"""
Notion Task Management API endpoints.

Provides comprehensive task management with:
- Kanban board columns (Todo, In Progress, In Review, Completed)
- Profile management with Genesis Key generation
- Full task history and versioning
- File/folder association for provenance
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json

from database.session import get_session, initialize_session_factory
from models.notion_models import (
    NotionProfile, NotionTask, TaskHistory, TaskTemplate,
    TaskStatus, TaskPriority, TaskType,
    generate_genesis_key, generate_profile_genesis_id
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/notion", tags=["Notion Task Management"])


def get_db_session():
    """Get a database session."""
    from database.session import SessionLocal
    if SessionLocal is None:
        initialize_session_factory()
    from database.session import SessionLocal
    return SessionLocal()


# ==================== Pydantic Models ====================

# Profile Models
class ProfileCreateRequest(BaseModel):
    """Request to create a new profile."""
    name: str = Field(..., description="Profile name")
    display_name: Optional[str] = Field(None, description="Display name")
    skill_set: Optional[List[str]] = Field(None, description="List of skills")
    specializations: Optional[List[str]] = Field(None, description="Areas of expertise")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")


class ProfileUpdateRequest(BaseModel):
    """Request to update a profile."""
    name: Optional[str] = Field(None, description="Profile name")
    display_name: Optional[str] = Field(None, description="Display name")
    skill_set: Optional[List[str]] = Field(None, description="List of skills")
    specializations: Optional[List[str]] = Field(None, description="Areas of expertise")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    is_active: Optional[bool] = Field(None, description="Whether profile is active")


class ProfileResponse(BaseModel):
    """Response model for a profile."""
    id: int
    genesis_key_id: str
    name: str
    display_name: Optional[str]
    skill_set: Optional[List[str]]
    specializations: Optional[List[str]]
    avatar_url: Optional[str]
    is_active: bool
    last_logged_on: Optional[datetime]
    last_logged_off: Optional[datetime]
    total_time_logged: int
    tasks_completed: int
    tasks_in_progress: int
    tasks_total: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileListResponse(BaseModel):
    """Response for listing profiles."""
    profiles: List[ProfileResponse]
    total: int


# Task Models
class SubtaskModel(BaseModel):
    """Model for a subtask."""
    title: str
    completed: bool = False


class TaskCreateRequest(BaseModel):
    """Request to create a new task."""
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: Optional[TaskStatus] = Field(TaskStatus.TODO, description="Task status")
    priority: Optional[TaskPriority] = Field(TaskPriority.MEDIUM, description="Task priority")
    task_type: Optional[TaskType] = Field(TaskType.OTHER, description="Task type")
    assignee_genesis_key_id: Optional[str] = Field(None, description="Genesis Key ID of assignee")
    due_date: Optional[datetime] = Field(None, description="Due date")
    estimated_hours: Optional[float] = Field(None, description="Estimated hours")
    folder_path: Optional[str] = Field(None, description="Associated folder path")
    file_paths: Optional[List[str]] = Field(None, description="Associated file paths")
    labels: Optional[List[str]] = Field(None, description="Task labels")
    category: Optional[str] = Field(None, description="Task category")
    subtasks: Optional[List[SubtaskModel]] = Field(None, description="Subtasks")
    notes: Optional[str] = Field(None, description="Task notes")


class TaskUpdateRequest(BaseModel):
    """Request to update a task."""
    title: Optional[str] = Field(None, description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: Optional[TaskStatus] = Field(None, description="Task status")
    priority: Optional[TaskPriority] = Field(None, description="Task priority")
    task_type: Optional[TaskType] = Field(None, description="Task type")
    assignee_genesis_key_id: Optional[str] = Field(None, description="Genesis Key ID of assignee")
    due_date: Optional[datetime] = Field(None, description="Due date")
    estimated_hours: Optional[float] = Field(None, description="Estimated hours")
    actual_hours: Optional[float] = Field(None, description="Actual hours spent")
    folder_path: Optional[str] = Field(None, description="Associated folder path")
    file_paths: Optional[List[str]] = Field(None, description="Associated file paths")
    labels: Optional[List[str]] = Field(None, description="Task labels")
    category: Optional[str] = Field(None, description="Task category")
    subtasks: Optional[List[SubtaskModel]] = Field(None, description="Subtasks")
    progress_percent: Optional[int] = Field(None, description="Progress percentage")
    notes: Optional[str] = Field(None, description="Task notes")
    change_reason: Optional[str] = Field(None, description="Reason for changes")


class TaskResponse(BaseModel):
    """Response model for a task."""
    id: int
    genesis_key_id: str
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    task_type: TaskType
    assignee_id: Optional[int]
    assignee_genesis_key_id: Optional[str]
    assignee_name: Optional[str]
    creator_id: Optional[int]
    due_date: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    folder_path: Optional[str]
    file_paths: Optional[List[str]]
    progress_percent: int
    subtasks: Optional[List[dict]]
    labels: Optional[List[str]]
    category: Optional[str]
    version: int
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """Response for listing tasks."""
    tasks: List[TaskResponse]
    total: int
    by_status: Dict[str, int]


class TaskHistoryResponse(BaseModel):
    """Response for task history entry."""
    id: int
    task_id: int
    task_genesis_key_id: str
    action: str
    field_changed: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    actor_id: Optional[int]
    actor_genesis_key_id: Optional[str]
    actor_name: Optional[str]
    version_number: int
    change_reason: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KanbanBoardResponse(BaseModel):
    """Response for the full Kanban board."""
    todo: List[TaskResponse]
    in_progress: List[TaskResponse]
    in_review: List[TaskResponse]
    completed: List[TaskResponse]
    total_tasks: int
    profiles: List[ProfileResponse]


# ==================== Helper Functions ====================

def task_to_response(task: NotionTask, session) -> TaskResponse:
    """Convert a task model to response format."""
    assignee_genesis_key_id = None
    assignee_name = None
    if task.assignee:
        assignee_genesis_key_id = task.assignee.genesis_key_id
        assignee_name = task.assignee.name

    return TaskResponse(
        id=task.id,
        genesis_key_id=task.genesis_key_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        task_type=task.task_type,
        assignee_id=task.assignee_id,
        assignee_genesis_key_id=assignee_genesis_key_id,
        assignee_name=assignee_name,
        creator_id=task.creator_id,
        due_date=task.due_date,
        started_at=task.started_at,
        completed_at=task.completed_at,
        estimated_hours=task.estimated_hours,
        actual_hours=task.actual_hours,
        folder_path=task.folder_path,
        file_paths=task.file_paths,
        progress_percent=task.progress_percent,
        subtasks=task.subtasks,
        labels=task.labels,
        category=task.category,
        version=task.version,
        notes=task.notes,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


def profile_to_response(profile: NotionProfile) -> ProfileResponse:
    """Convert a profile model to response format."""
    return ProfileResponse(
        id=profile.id,
        genesis_key_id=profile.genesis_key_id,
        name=profile.name,
        display_name=profile.display_name,
        skill_set=profile.skill_set,
        specializations=profile.specializations,
        avatar_url=profile.avatar_url,
        is_active=profile.is_active,
        last_logged_on=profile.last_logged_on,
        last_logged_off=profile.last_logged_off,
        total_time_logged=profile.total_time_logged,
        tasks_completed=profile.tasks_completed,
        tasks_in_progress=profile.tasks_in_progress,
        tasks_total=profile.tasks_total,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )


def record_task_history(
    session,
    task: NotionTask,
    action: str,
    field_changed: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    actor_id: Optional[int] = None,
    actor_genesis_key_id: Optional[str] = None,
    change_reason: Optional[str] = None
):
    """Record a change to task history."""
    history = TaskHistory(
        task_id=task.id,
        task_genesis_key_id=task.genesis_key_id,
        action=action,
        field_changed=field_changed,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        actor_id=actor_id,
        actor_genesis_key_id=actor_genesis_key_id,
        version_number=task.version,
        change_reason=change_reason
    )
    session.add(history)


# ==================== Profile Endpoints ====================

@router.post("/profiles", response_model=ProfileResponse, summary="Create a new profile")
async def create_profile(request: ProfileCreateRequest):
    """
    Create a new profile with auto-generated Genesis Key ID.

    Profiles represent workers/agents that can be assigned to tasks.
    """
    session = get_db_session()
    try:
        # Create profile with generated genesis key
        profile = NotionProfile(
            genesis_key_id=generate_profile_genesis_id(),
            name=request.name,
            display_name=request.display_name,
            skill_set=request.skill_set,
            specializations=request.specializations,
            avatar_url=request.avatar_url
        )

        session.add(profile)
        session.commit()
        session.refresh(profile)

        logger.info(f"[NOTION] Created profile: {profile.genesis_key_id} - {profile.name}")

        return profile_to_response(profile)

    except Exception as e:
        session.rollback()
        logger.error(f"[NOTION] Error creating profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create profile: {str(e)}")
    finally:
        session.close()


@router.post("/profiles/generate", response_model=ProfileResponse, summary="Generate a new profile with Genesis Key")
async def generate_profile():
    """
    Generate a new profile with auto-generated Genesis Key ID and default name.

    Quick way to create a new worker profile.
    """
    session = get_db_session()
    try:
        genesis_id = generate_profile_genesis_id()

        profile = NotionProfile(
            genesis_key_id=genesis_id,
            name=f"Worker-{genesis_id[-8:]}",
            display_name=f"Worker {genesis_id[-8:]}",
            skill_set=["general"],
            specializations=[]
        )

        session.add(profile)
        session.commit()
        session.refresh(profile)

        logger.info(f"[NOTION] Generated profile: {profile.genesis_key_id}")

        return profile_to_response(profile)

    except Exception as e:
        session.rollback()
        logger.error(f"[NOTION] Error generating profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate profile: {str(e)}")
    finally:
        session.close()


@router.get("/profiles", response_model=ProfileListResponse, summary="List all profiles")
async def list_profiles(
    active_only: bool = Query(False, description="Only show active profiles"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """List all profiles with optional filtering."""
    session = get_db_session()
    try:
        query = session.query(NotionProfile)

        if active_only:
            query = query.filter(NotionProfile.is_active == True)

        total = query.count()
        profiles = query.order_by(NotionProfile.created_at.desc()).offset(skip).limit(limit).all()

        return ProfileListResponse(
            profiles=[profile_to_response(p) for p in profiles],
            total=total
        )

    except Exception as e:
        logger.error(f"[NOTION] Error listing profiles: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list profiles: {str(e)}")
    finally:
        session.close()


@router.get("/profiles/{genesis_key_id}", response_model=ProfileResponse, summary="Get profile by Genesis Key ID")
async def get_profile(genesis_key_id: str):
    """Get a specific profile by its Genesis Key ID."""
    session = get_db_session()
    try:
        profile = session.query(NotionProfile).filter(
            NotionProfile.genesis_key_id == genesis_key_id
        ).first()

        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile {genesis_key_id} not found")

        return profile_to_response(profile)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[NOTION] Error getting profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")
    finally:
        session.close()


@router.put("/profiles/{genesis_key_id}", response_model=ProfileResponse, summary="Update a profile")
async def update_profile(genesis_key_id: str, request: ProfileUpdateRequest):
    """Update a profile's information."""
    session = get_db_session()
    try:
        profile = session.query(NotionProfile).filter(
            NotionProfile.genesis_key_id == genesis_key_id
        ).first()

        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile {genesis_key_id} not found")

        # Update fields
        if request.name is not None:
            profile.name = request.name
        if request.display_name is not None:
            profile.display_name = request.display_name
        if request.skill_set is not None:
            profile.skill_set = request.skill_set
        if request.specializations is not None:
            profile.specializations = request.specializations
        if request.avatar_url is not None:
            profile.avatar_url = request.avatar_url
        if request.is_active is not None:
            profile.is_active = request.is_active

        profile.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(profile)

        logger.info(f"[NOTION] Updated profile: {genesis_key_id}")

        return profile_to_response(profile)

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"[NOTION] Error updating profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")
    finally:
        session.close()


@router.post("/profiles/{genesis_key_id}/log-on", response_model=ProfileResponse, summary="Log on a profile")
async def log_on_profile(genesis_key_id: str):
    """Record that a profile has logged on."""
    session = get_db_session()
    try:
        profile = session.query(NotionProfile).filter(
            NotionProfile.genesis_key_id == genesis_key_id
        ).first()

        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile {genesis_key_id} not found")

        profile.last_logged_on = datetime.utcnow()
        profile.is_active = True
        profile.updated_at = datetime.utcnow()

        session.commit()
        session.refresh(profile)

        logger.info(f"[NOTION] Profile logged on: {genesis_key_id}")

        return profile_to_response(profile)

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"[NOTION] Error logging on profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log on profile: {str(e)}")
    finally:
        session.close()


@router.post("/profiles/{genesis_key_id}/log-off", response_model=ProfileResponse, summary="Log off a profile")
async def log_off_profile(genesis_key_id: str):
    """Record that a profile has logged off and update time tracking."""
    session = get_db_session()
    try:
        profile = session.query(NotionProfile).filter(
            NotionProfile.genesis_key_id == genesis_key_id
        ).first()

        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile {genesis_key_id} not found")

        now = datetime.utcnow()
        profile.last_logged_off = now

        # Calculate time logged if we have a log on time
        if profile.last_logged_on:
            time_diff = (now - profile.last_logged_on).total_seconds()
            profile.total_time_logged += int(time_diff)

        profile.updated_at = now

        session.commit()
        session.refresh(profile)

        logger.info(f"[NOTION] Profile logged off: {genesis_key_id}")

        return profile_to_response(profile)

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"[NOTION] Error logging off profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log off profile: {str(e)}")
    finally:
        session.close()


# ==================== Task Endpoints ====================

@router.post("/tasks", response_model=TaskResponse, summary="Create a new task")
async def create_task(request: TaskCreateRequest):
    """
    Create a new task with auto-generated Genesis Key ID.

    Tasks are tracked on the Kanban board with full provenance.
    """
    session = get_db_session()
    try:
        # Find assignee if specified
        assignee_id = None
        creator_id = None
        if request.assignee_genesis_key_id:
            assignee = session.query(NotionProfile).filter(
                NotionProfile.genesis_key_id == request.assignee_genesis_key_id
            ).first()
            if assignee:
                assignee_id = assignee.id
                # Update assignee's task count
                assignee.tasks_total += 1
                if request.status == TaskStatus.IN_PROGRESS:
                    assignee.tasks_in_progress += 1

        # Convert subtasks to dict format
        subtasks_data = None
        if request.subtasks:
            subtasks_data = [{"title": s.title, "completed": s.completed} for s in request.subtasks]

        # Create task
        task = NotionTask(
            genesis_key_id=generate_genesis_key(),
            title=request.title,
            description=request.description,
            status=request.status or TaskStatus.TODO,
            priority=request.priority or TaskPriority.MEDIUM,
            task_type=request.task_type or TaskType.OTHER,
            assignee_id=assignee_id,
            creator_id=creator_id,
            due_date=request.due_date,
            estimated_hours=request.estimated_hours,
            folder_path=request.folder_path,
            file_paths=request.file_paths,
            labels=request.labels,
            category=request.category,
            subtasks=subtasks_data,
            notes=request.notes
        )

        # Set started_at if task starts in progress
        if request.status == TaskStatus.IN_PROGRESS:
            task.started_at = datetime.utcnow()

        session.add(task)
        session.commit()
        session.refresh(task)

        # Record creation in history
        record_task_history(
            session=session,
            task=task,
            action="created",
            new_value=task.title,
            change_reason="Task created"
        )
        session.commit()

        logger.info(f"[NOTION] Created task: {task.genesis_key_id} - {task.title}")

        return task_to_response(task, session)

    except Exception as e:
        session.rollback()
        logger.error(f"[NOTION] Error creating task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")
    finally:
        session.close()


@router.get("/tasks", response_model=TaskListResponse, summary="List all tasks")
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    task_type: Optional[TaskType] = Query(None, description="Filter by type"),
    assignee_genesis_key_id: Optional[str] = Query(None, description="Filter by assignee"),
    folder_path: Optional[str] = Query(None, description="Filter by folder path"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """List all tasks with optional filtering."""
    session = get_db_session()
    try:
        query = session.query(NotionTask)

        if status:
            query = query.filter(NotionTask.status == status)
        if priority:
            query = query.filter(NotionTask.priority == priority)
        if task_type:
            query = query.filter(NotionTask.task_type == task_type)
        if assignee_genesis_key_id:
            assignee = session.query(NotionProfile).filter(
                NotionProfile.genesis_key_id == assignee_genesis_key_id
            ).first()
            if assignee:
                query = query.filter(NotionTask.assignee_id == assignee.id)
        if folder_path:
            query = query.filter(NotionTask.folder_path == folder_path)

        total = query.count()

        # Get counts by status
        by_status = {}
        for s in TaskStatus:
            count = session.query(NotionTask).filter(NotionTask.status == s).count()
            by_status[s.value] = count

        tasks = query.order_by(
            NotionTask.priority.desc(),
            NotionTask.created_at.desc()
        ).offset(skip).limit(limit).all()

        return TaskListResponse(
            tasks=[task_to_response(t, session) for t in tasks],
            total=total,
            by_status=by_status
        )

    except Exception as e:
        logger.error(f"[NOTION] Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")
    finally:
        session.close()


@router.get("/tasks/{genesis_key_id}", response_model=TaskResponse, summary="Get task by Genesis Key ID")
async def get_task(genesis_key_id: str):
    """Get a specific task by its Genesis Key ID."""
    session = get_db_session()
    try:
        task = session.query(NotionTask).filter(
            NotionTask.genesis_key_id == genesis_key_id
        ).first()

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {genesis_key_id} not found")

        return task_to_response(task, session)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[NOTION] Error getting task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")
    finally:
        session.close()


@router.put("/tasks/{genesis_key_id}", response_model=TaskResponse, summary="Update a task")
async def update_task(genesis_key_id: str, request: TaskUpdateRequest):
    """Update a task and record changes in history."""
    session = get_db_session()
    try:
        task = session.query(NotionTask).filter(
            NotionTask.genesis_key_id == genesis_key_id
        ).first()

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {genesis_key_id} not found")

        # Track changes
        changes = []

        if request.title is not None and request.title != task.title:
            changes.append(("title", task.title, request.title))
            task.title = request.title

        if request.description is not None and request.description != task.description:
            changes.append(("description", task.description, request.description))
            task.description = request.description

        if request.status is not None and request.status != task.status:
            old_status = task.status
            changes.append(("status", old_status.value, request.status.value))
            task.status = request.status

            # Handle status transitions
            if request.status == TaskStatus.IN_PROGRESS and not task.started_at:
                task.started_at = datetime.utcnow()
            elif request.status == TaskStatus.COMPLETED:
                task.completed_at = datetime.utcnow()
                task.progress_percent = 100
                # Update assignee stats
                if task.assignee:
                    task.assignee.tasks_completed += 1
                    task.assignee.tasks_in_progress = max(0, task.assignee.tasks_in_progress - 1)

            # Update assignee in_progress count
            if task.assignee:
                if old_status == TaskStatus.IN_PROGRESS and request.status != TaskStatus.IN_PROGRESS:
                    task.assignee.tasks_in_progress = max(0, task.assignee.tasks_in_progress - 1)
                elif old_status != TaskStatus.IN_PROGRESS and request.status == TaskStatus.IN_PROGRESS:
                    task.assignee.tasks_in_progress += 1

        if request.priority is not None and request.priority != task.priority:
            changes.append(("priority", task.priority.value, request.priority.value))
            task.priority = request.priority

        if request.task_type is not None and request.task_type != task.task_type:
            changes.append(("task_type", task.task_type.value, request.task_type.value))
            task.task_type = request.task_type

        if request.assignee_genesis_key_id is not None:
            new_assignee = session.query(NotionProfile).filter(
                NotionProfile.genesis_key_id == request.assignee_genesis_key_id
            ).first()
            if new_assignee and new_assignee.id != task.assignee_id:
                old_assignee_id = task.assignee.genesis_key_id if task.assignee else None
                changes.append(("assignee", old_assignee_id, request.assignee_genesis_key_id))

                # Update old assignee stats
                if task.assignee:
                    task.assignee.tasks_total = max(0, task.assignee.tasks_total - 1)
                    if task.status == TaskStatus.IN_PROGRESS:
                        task.assignee.tasks_in_progress = max(0, task.assignee.tasks_in_progress - 1)

                # Update new assignee stats
                new_assignee.tasks_total += 1
                if task.status == TaskStatus.IN_PROGRESS:
                    new_assignee.tasks_in_progress += 1

                task.assignee_id = new_assignee.id

        if request.due_date is not None:
            changes.append(("due_date", str(task.due_date), str(request.due_date)))
            task.due_date = request.due_date

        if request.estimated_hours is not None:
            changes.append(("estimated_hours", task.estimated_hours, request.estimated_hours))
            task.estimated_hours = request.estimated_hours

        if request.actual_hours is not None:
            changes.append(("actual_hours", task.actual_hours, request.actual_hours))
            task.actual_hours = request.actual_hours

        if request.folder_path is not None:
            changes.append(("folder_path", task.folder_path, request.folder_path))
            task.folder_path = request.folder_path

        if request.file_paths is not None:
            changes.append(("file_paths", str(task.file_paths), str(request.file_paths)))
            task.file_paths = request.file_paths

        if request.labels is not None:
            changes.append(("labels", str(task.labels), str(request.labels)))
            task.labels = request.labels

        if request.category is not None:
            changes.append(("category", task.category, request.category))
            task.category = request.category

        if request.subtasks is not None:
            subtasks_data = [{"title": s.title, "completed": s.completed} for s in request.subtasks]
            changes.append(("subtasks", str(task.subtasks), str(subtasks_data)))
            task.subtasks = subtasks_data

        if request.progress_percent is not None:
            changes.append(("progress_percent", task.progress_percent, request.progress_percent))
            task.progress_percent = request.progress_percent

        if request.notes is not None:
            changes.append(("notes", task.notes, request.notes))
            task.notes = request.notes

        # Increment version
        task.version += 1
        task.updated_at = datetime.utcnow()

        # Record all changes in history
        for field, old_val, new_val in changes:
            record_task_history(
                session=session,
                task=task,
                action="updated",
                field_changed=field,
                old_value=old_val,
                new_value=new_val,
                change_reason=request.change_reason
            )

        session.commit()
        session.refresh(task)

        logger.info(f"[NOTION] Updated task: {genesis_key_id}, {len(changes)} changes")

        return task_to_response(task, session)

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"[NOTION] Error updating task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")
    finally:
        session.close()


@router.delete("/tasks/{genesis_key_id}", summary="Delete a task")
async def delete_task(genesis_key_id: str):
    """Delete a task (moves to archived status or hard delete)."""
    session = get_db_session()
    try:
        task = session.query(NotionTask).filter(
            NotionTask.genesis_key_id == genesis_key_id
        ).first()

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {genesis_key_id} not found")

        # Update assignee stats
        if task.assignee:
            task.assignee.tasks_total = max(0, task.assignee.tasks_total - 1)
            if task.status == TaskStatus.IN_PROGRESS:
                task.assignee.tasks_in_progress = max(0, task.assignee.tasks_in_progress - 1)

        session.delete(task)
        session.commit()

        logger.info(f"[NOTION] Deleted task: {genesis_key_id}")

        return {"message": f"Task {genesis_key_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"[NOTION] Error deleting task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")
    finally:
        session.close()


@router.post("/tasks/{genesis_key_id}/move", response_model=TaskResponse, summary="Move task to new status")
async def move_task(
    genesis_key_id: str,
    new_status: TaskStatus = Query(..., description="New status for the task"),
    change_reason: Optional[str] = Query(None, description="Reason for status change")
):
    """Quick endpoint to move a task to a new status column."""
    session = get_db_session()
    try:
        task = session.query(NotionTask).filter(
            NotionTask.genesis_key_id == genesis_key_id
        ).first()

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {genesis_key_id} not found")

        old_status = task.status
        if old_status == new_status:
            return task_to_response(task, session)

        task.status = new_status

        # Handle status transitions
        if new_status == TaskStatus.IN_PROGRESS and not task.started_at:
            task.started_at = datetime.utcnow()
        elif new_status == TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()
            task.progress_percent = 100
            if task.assignee:
                task.assignee.tasks_completed += 1
                task.assignee.tasks_in_progress = max(0, task.assignee.tasks_in_progress - 1)

        # Update assignee in_progress count
        if task.assignee:
            if old_status == TaskStatus.IN_PROGRESS and new_status != TaskStatus.IN_PROGRESS:
                task.assignee.tasks_in_progress = max(0, task.assignee.tasks_in_progress - 1)
            elif old_status != TaskStatus.IN_PROGRESS and new_status == TaskStatus.IN_PROGRESS:
                task.assignee.tasks_in_progress += 1

        task.version += 1
        task.updated_at = datetime.utcnow()

        record_task_history(
            session=session,
            task=task,
            action="status_changed",
            field_changed="status",
            old_value=old_status.value,
            new_value=new_status.value,
            change_reason=change_reason
        )

        session.commit()
        session.refresh(task)

        logger.info(f"[NOTION] Moved task {genesis_key_id}: {old_status.value} -> {new_status.value}")

        return task_to_response(task, session)

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"[NOTION] Error moving task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to move task: {str(e)}")
    finally:
        session.close()


@router.get("/tasks/{genesis_key_id}/history", response_model=List[TaskHistoryResponse], summary="Get task history")
async def get_task_history(
    genesis_key_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """Get the complete history of a task."""
    session = get_db_session()
    try:
        task = session.query(NotionTask).filter(
            NotionTask.genesis_key_id == genesis_key_id
        ).first()

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {genesis_key_id} not found")

        history = session.query(TaskHistory).filter(
            TaskHistory.task_id == task.id
        ).order_by(TaskHistory.created_at.desc()).offset(skip).limit(limit).all()

        result = []
        for h in history:
            actor_name = None
            if h.actor:
                actor_name = h.actor.name

            result.append(TaskHistoryResponse(
                id=h.id,
                task_id=h.task_id,
                task_genesis_key_id=h.task_genesis_key_id,
                action=h.action,
                field_changed=h.field_changed,
                old_value=h.old_value,
                new_value=h.new_value,
                actor_id=h.actor_id,
                actor_genesis_key_id=h.actor_genesis_key_id,
                actor_name=actor_name,
                version_number=h.version_number,
                change_reason=h.change_reason,
                created_at=h.created_at
            ))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[NOTION] Error getting task history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task history: {str(e)}")
    finally:
        session.close()


# ==================== Kanban Board Endpoint ====================

@router.get("/board", response_model=KanbanBoardResponse, summary="Get full Kanban board")
async def get_kanban_board():
    """
    Get the complete Kanban board with all tasks organized by status.

    Returns tasks in all columns: Todo, In Progress, In Review, Completed.
    """
    session = get_db_session()
    try:
        # Get tasks by status
        todo = session.query(NotionTask).filter(
            NotionTask.status == TaskStatus.TODO
        ).order_by(NotionTask.priority.desc(), NotionTask.created_at.desc()).all()

        in_progress = session.query(NotionTask).filter(
            NotionTask.status == TaskStatus.IN_PROGRESS
        ).order_by(NotionTask.priority.desc(), NotionTask.created_at.desc()).all()

        in_review = session.query(NotionTask).filter(
            NotionTask.status == TaskStatus.IN_REVIEW
        ).order_by(NotionTask.priority.desc(), NotionTask.created_at.desc()).all()

        completed = session.query(NotionTask).filter(
            NotionTask.status == TaskStatus.COMPLETED
        ).order_by(NotionTask.completed_at.desc()).limit(50).all()  # Limit completed to recent 50

        # Get all active profiles
        profiles = session.query(NotionProfile).filter(
            NotionProfile.is_active == True
        ).all()

        total_tasks = len(todo) + len(in_progress) + len(in_review) + len(completed)

        return KanbanBoardResponse(
            todo=[task_to_response(t, session) for t in todo],
            in_progress=[task_to_response(t, session) for t in in_progress],
            in_review=[task_to_response(t, session) for t in in_review],
            completed=[task_to_response(t, session) for t in completed],
            total_tasks=total_tasks,
            profiles=[profile_to_response(p) for p in profiles]
        )

    except Exception as e:
        logger.error(f"[NOTION] Error getting Kanban board: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get Kanban board: {str(e)}")
    finally:
        session.close()


# ==================== Statistics Endpoint ====================

@router.get("/stats", summary="Get Notion task statistics")
async def get_stats():
    """Get overall statistics for the task management system."""
    session = get_db_session()
    try:
        # Task counts by status
        task_counts = {}
        for status in TaskStatus:
            count = session.query(NotionTask).filter(NotionTask.status == status).count()
            task_counts[status.value] = count

        # Task counts by priority
        priority_counts = {}
        for priority in TaskPriority:
            count = session.query(NotionTask).filter(NotionTask.priority == priority).count()
            priority_counts[priority.value] = count

        # Task counts by type
        type_counts = {}
        for task_type in TaskType:
            count = session.query(NotionTask).filter(NotionTask.task_type == task_type).count()
            type_counts[task_type.value] = count

        # Profile stats
        total_profiles = session.query(NotionProfile).count()
        active_profiles = session.query(NotionProfile).filter(NotionProfile.is_active == True).count()

        # Recent activity
        recent_tasks = session.query(NotionTask).order_by(
            NotionTask.updated_at.desc()
        ).limit(5).all()

        return {
            "task_counts_by_status": task_counts,
            "task_counts_by_priority": priority_counts,
            "task_counts_by_type": type_counts,
            "total_tasks": sum(task_counts.values()),
            "total_profiles": total_profiles,
            "active_profiles": active_profiles,
            "recent_tasks": [
                {
                    "genesis_key_id": t.genesis_key_id,
                    "title": t.title,
                    "status": t.status.value,
                    "updated_at": t.updated_at.isoformat()
                }
                for t in recent_tasks
            ]
        }

    except Exception as e:
        logger.error(f"[NOTION] Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
    finally:
        session.close()
