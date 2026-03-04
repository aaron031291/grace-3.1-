"""
Workspace and multi-tenant models for Grace's internal platform.

Architecture:
  Workspace (container) → holds one AI instance (Tommy AI, Rebecca AI, etc.)
    ├── has its own knowledge_base/
    ├── has its own file versions (internal VCS)
    ├── has its own pipeline runs (internal CI/CD)
    └── Grace is the intelligence behind all of them

Grace manages all workspaces — she is the brain that fixes, heals,
codes, and learns for every tenant AI.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from database.base import BaseModel
from datetime import datetime, timezone
import enum


class Workspace(BaseModel):
    """
    A self-contained AI workspace — the 'container' for an independent AI system.

    Each workspace is like a virtual project folder:
      - Tommy AI has workspace_id='tommy-ai'
      - Rebecca AI has workspace_id='rebecca-ai'
    Grace is the intelligence backbone behind all of them.
    """
    __tablename__ = "workspaces"

    workspace_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    owner_id = Column(String(255), index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    root_path = Column(Text, nullable=False)
    config = Column(JSON, default=dict)

    total_files = Column(Integer, default=0)
    total_versions = Column(Integer, default=0)
    total_pipeline_runs = Column(Integer, default=0)

    file_versions = relationship("FileVersion", back_populates="workspace", cascade="all, delete-orphan")
    branches = relationship("Branch", back_populates="workspace", cascade="all, delete-orphan")
    pipeline_runs = relationship("PipelineRun", back_populates="workspace", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_workspace_owner", "owner_id"),
    )

    def __repr__(self):
        return f"<Workspace(id={self.id}, workspace_id='{self.workspace_id}', name='{self.name}')>"


class Branch(BaseModel):
    """
    A branch within a workspace's internal VCS.
    Replaces git branches — no external dependency.
    """
    __tablename__ = "vcs_branches"

    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    head_version_id = Column(Integer, ForeignKey("file_versions.id", ondelete="SET NULL"), nullable=True)
    parent_branch_id = Column(Integer, ForeignKey("vcs_branches.id", ondelete="SET NULL"), nullable=True)

    workspace = relationship("Workspace", back_populates="branches")

    __table_args__ = (
        Index("idx_branch_workspace_name", "workspace_id", "name", unique=True),
    )

    def __repr__(self):
        return f"<Branch(id={self.id}, name='{self.name}', workspace_id={self.workspace_id})>"


class FileVersion(BaseModel):
    """
    Internal version control — every file change is tracked as a version.
    Replaces git commits — no external dependency.

    Each version stores:
      - The file path (relative to workspace root)
      - A content hash for integrity
      - The full diff from previous version
      - The commit message (what changed and why)
      - Who made the change
      - Which branch it's on
    """
    __tablename__ = "file_versions"

    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("vcs_branches.id", ondelete="SET NULL"), nullable=True, index=True)
    file_path = Column(Text, nullable=False)
    version_number = Column(Integer, nullable=False)

    content_hash = Column(String(64), nullable=False)
    content_size = Column(Integer, default=0)
    diff_from_previous = Column(Text, default="")
    full_content = Column(Text, default="")

    operation = Column(String(50), default="modify")
    commit_message = Column(Text, default="")
    author = Column(String(255), default="grace")

    genesis_key_id = Column(String(255), nullable=True, index=True)
    parent_version_id = Column(Integer, ForeignKey("file_versions.id", ondelete="SET NULL"), nullable=True)

    workspace = relationship("Workspace", back_populates="file_versions")

    __table_args__ = (
        Index("idx_fv_workspace_file", "workspace_id", "file_path"),
        Index("idx_fv_workspace_branch", "workspace_id", "branch_id"),
        Index("idx_fv_hash", "content_hash"),
    )

    def __repr__(self):
        return f"<FileVersion(id={self.id}, file='{self.file_path}', v{self.version_number})>"


class PipelineRun(BaseModel):
    """
    Internal CI/CD pipeline run — replaces GitHub Actions.
    Grace triggers, monitors, and heals pipelines autonomously.
    """
    __tablename__ = "pipeline_runs"

    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(String(255), unique=True, nullable=False, index=True)
    pipeline_name = Column(String(255), nullable=False)
    trigger = Column(String(100), default="manual")

    status = Column(String(50), default="pending", index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0)

    stages = Column(JSON, default=list)
    config = Column(JSON, default=dict)
    artifacts = Column(JSON, default=list)
    error_message = Column(Text, default="")

    triggered_by = Column(String(255), default="grace")
    genesis_key_id = Column(String(255), nullable=True)

    workspace = relationship("Workspace", back_populates="pipeline_runs")

    __table_args__ = (
        Index("idx_pr_workspace_status", "workspace_id", "status"),
    )

    def __repr__(self):
        return f"<PipelineRun(id={self.id}, run_id='{self.run_id}', status='{self.status}')>"
