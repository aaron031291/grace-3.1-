"""
database/models/coding_agent_task.py
─────────────────────────────────────────────────────────────────────────────
SQLAlchemy model for coding agent task persistence.

This table backs coding_agent.task_queue so tasks survive server restarts.
auto_migrate picks it up automatically on startup — no manual migration needed.
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

try:
    from database.base import Base
except ImportError:
    Base = declarative_base()


class CodingAgentTask(Base):
    """Persistent record of every coding agent task."""
    __tablename__ = "coding_agent_tasks"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(128), unique=True, nullable=False, index=True)
    task_type = Column(String(64), nullable=False, index=True)
    instructions = Column(Text, nullable=False)
    context_data = Column(Text, default="{}")          # JSON
    priority = Column(Integer, default=5)
    origin = Column(String(128), default="unknown")
    error_class = Column(String(64), default="")
    status = Column(String(32), default="pending", index=True)
    attempts = Column(Integer, default=0)
    result_data = Column(Text, default="{}")           # JSON — outcome
    error = Column(Text, default="")
    # Apply result
    target_file = Column(String(512), default="")
    applied = Column(Boolean, default=False)
    rolled_back = Column(Boolean, default=False)
    lines_written = Column(Integer, default=0)
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
