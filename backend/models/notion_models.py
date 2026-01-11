"""
Notion Task Management Models for Grace.

Provides comprehensive task tracking with Genesis Key integration,
profile management, skill tracking, and full provenance.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, Integer, Float, DateTime,
    JSON, Text, Boolean, Index, Enum as SQLEnum, ForeignKey
)
from sqlalchemy.orm import relationship
from database.base import BaseModel
import enum
import uuid


class TaskStatus(str, enum.Enum):
    """Status of a task in the Kanban board."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskPriority(str, enum.Enum):
    """Priority levels for tasks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskType(str, enum.Enum):
    """Types of tasks Grace can work on."""
    LEARNING = "learning"           # Learning new concepts/skills
    BUILDING = "building"           # Building features/components
    RESEARCH = "research"           # Researching topics
    MAINTENANCE = "maintenance"     # System maintenance
    EXPERIMENT = "experiment"       # Running experiments
    DOCUMENTATION = "documentation" # Creating documentation
    ANALYSIS = "analysis"           # Data analysis
    OTHER = "other"


def generate_genesis_key() -> str:
    """Generate a unique Genesis Key ID in format GK-[hex]."""
    return f"GK-{uuid.uuid4().hex[:16].upper()}"


def generate_profile_genesis_id() -> str:
    """Generate a unique Profile Genesis ID in format GP-[hex]."""
    return f"GP-{uuid.uuid4().hex[:16].upper()}"


class NotionProfile(BaseModel):
    """
    Profile for task assignment and tracking.

    Each profile has a unique Genesis Key ID for tracking all
    work, tasks, and contributions.
    """
    __tablename__ = "notion_profile"

    # Genesis Key identification
    genesis_key_id = Column(String(36), nullable=False, index=True, unique=True, default=generate_profile_genesis_id)

    # Profile information
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Skill set tracking
    skill_set = Column(JSON, nullable=True)  # List of skills/capabilities
    specializations = Column(JSON, nullable=True)  # Primary areas of expertise

    # Activity tracking
    is_active = Column(Boolean, nullable=False, default=True)
    last_logged_on = Column(DateTime, nullable=True)
    last_logged_off = Column(DateTime, nullable=True)
    total_time_logged = Column(Integer, nullable=False, default=0)  # Total seconds logged

    # Statistics
    tasks_completed = Column(Integer, nullable=False, default=0)
    tasks_in_progress = Column(Integer, nullable=False, default=0)
    tasks_total = Column(Integer, nullable=False, default=0)

    # Metadata
    profile_metadata = Column(JSON, nullable=True)

    # Relationships
    assigned_tasks = relationship("NotionTask", back_populates="assignee", foreign_keys="NotionTask.assignee_id")
    created_tasks = relationship("NotionTask", back_populates="creator", foreign_keys="NotionTask.creator_id")
    task_history = relationship("TaskHistory", back_populates="actor")

    __table_args__ = (
        Index('idx_profile_genesis_key', 'genesis_key_id'),
        Index('idx_profile_active', 'is_active'),
    )

    def __repr__(self):
        return f"<NotionProfile(genesis_key_id={self.genesis_key_id}, name={self.name})>"


class NotionTask(BaseModel):
    """
    Task in the Notion-style Kanban board.

    Tracks work that Grace is doing, with full provenance,
    file associations, and version history.
    """
    __tablename__ = "notion_task"

    # Genesis Key identification for tracking
    genesis_key_id = Column(String(36), nullable=False, index=True, unique=True, default=generate_genesis_key)

    # Task details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.TODO, index=True)
    priority = Column(SQLEnum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM)
    task_type = Column(SQLEnum(TaskType), nullable=False, default=TaskType.OTHER)

    # Assignment tracking
    assignee_id = Column(Integer, ForeignKey('notion_profile.id'), nullable=True, index=True)
    creator_id = Column(Integer, ForeignKey('notion_profile.id'), nullable=True)

    # Time tracking
    due_date = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    estimated_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, nullable=True)

    # File/folder associations (connects to file manager)
    folder_path = Column(String(500), nullable=True)  # Associated folder in knowledge_base
    file_paths = Column(JSON, nullable=True)  # List of associated files

    # Progress tracking
    progress_percent = Column(Integer, nullable=False, default=0)
    subtasks = Column(JSON, nullable=True)  # List of subtasks with status

    # Labels and categorization
    labels = Column(JSON, nullable=True)  # List of labels/tags
    category = Column(String(100), nullable=True)

    # Versioning
    version = Column(Integer, nullable=False, default=1)

    # Notes and comments
    notes = Column(Text, nullable=True)

    # Metadata for full provenance
    task_metadata = Column(JSON, nullable=True)

    # Relationships
    assignee = relationship("NotionProfile", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    creator = relationship("NotionProfile", back_populates="created_tasks", foreign_keys=[creator_id])
    history = relationship("TaskHistory", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_task_status', 'status'),
        Index('idx_task_assignee', 'assignee_id'),
        Index('idx_task_genesis_key', 'genesis_key_id'),
        Index('idx_task_priority_status', 'priority', 'status'),
    )

    def __repr__(self):
        return f"<NotionTask(genesis_key_id={self.genesis_key_id}, title={self.title[:30]}, status={self.status})>"


class TaskHistory(BaseModel):
    """
    Complete history of task changes for versioning and provenance.

    Every change to a task is recorded here for full audit trail.
    """
    __tablename__ = "task_history"

    # Link to task
    task_id = Column(Integer, ForeignKey('notion_task.id'), nullable=False, index=True)
    task_genesis_key_id = Column(String(36), nullable=False, index=True)

    # What changed
    action = Column(String(50), nullable=False)  # created, status_changed, assigned, etc.
    field_changed = Column(String(100), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    # Who made the change
    actor_id = Column(Integer, ForeignKey('notion_profile.id'), nullable=True, index=True)
    actor_genesis_key_id = Column(String(36), nullable=True)

    # Version at time of change
    version_number = Column(Integer, nullable=False, default=1)

    # Additional context
    change_reason = Column(Text, nullable=True)
    history_metadata = Column(JSON, nullable=True)

    # Relationships
    task = relationship("NotionTask", back_populates="history")
    actor = relationship("NotionProfile", back_populates="task_history")

    __table_args__ = (
        Index('idx_history_task', 'task_id'),
        Index('idx_history_timestamp', 'created_at'),
        Index('idx_history_action', 'action'),
    )

    def __repr__(self):
        return f"<TaskHistory(task_id={self.task_id}, action={self.action}, at={self.created_at})>"


class TaskTemplate(BaseModel):
    """
    Reusable task templates for common work patterns.
    """
    __tablename__ = "task_template"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Template fields
    default_title = Column(String(500), nullable=True)
    default_description = Column(Text, nullable=True)
    default_priority = Column(SQLEnum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM)
    default_task_type = Column(SQLEnum(TaskType), nullable=False, default=TaskType.OTHER)
    default_labels = Column(JSON, nullable=True)
    default_subtasks = Column(JSON, nullable=True)
    estimated_hours = Column(Float, nullable=True)

    # Metadata
    template_metadata = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<TaskTemplate(name={self.name})>"
