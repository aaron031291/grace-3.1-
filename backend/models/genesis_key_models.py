"""
Genesis Key models for comprehensive version control and tracking.

Genesis Keys track every input, change, and action in the system with
complete metadata for what, where, when, why, who, and how.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Float, DateTime,
    JSON, Text, Boolean, Index, Enum as SQLEnum, ForeignKey
)
from sqlalchemy.orm import relationship
from database.base import BaseModel
import enum


class GenesisKeyType(str, enum.Enum):
    """Types of Genesis Keys - tracks ALL inputs and changes."""
    # User interactions
    USER_INPUT = "user_input"                    # User messages, requests, commands
    USER_UPLOAD = "user_upload"                  # Files uploaded by user

    # AI/Agent interactions
    AI_RESPONSE = "ai_response"                  # AI-generated responses, decisions
    AI_CODE_GENERATION = "ai_code_generation"    # AI-generated code
    CODING_AGENT_ACTION = "coding_agent_action"  # Autonomous coding agent actions

    # Code and file operations
    CODE_CHANGE = "code_change"                  # Code modifications
    FILE_OPERATION = "file_operation"            # File create/update/delete
    FILE_INGESTION = "file_ingestion"            # File ingested into knowledge base

    # API and external interactions
    API_REQUEST = "api_request"                  # Internal API calls
    EXTERNAL_API_CALL = "external_api_call"      # External API interactions
    WEB_FETCH = "web_fetch"                      # HTML/web content fetched

    # Data operations
    DATABASE_CHANGE = "database_change"          # Database modifications
    LIBRARIAN_ACTION = "librarian_action"        # Librarian auto-categorization

    # Autonomous learning operations
    LEARNING_COMPLETE = "learning_complete"      # Study session completed
    GAP_IDENTIFIED = "gap_identified"            # Knowledge gap detected
    PRACTICE_OUTCOME = "practice_outcome"        # Practice task result

    # System operations
    CONFIGURATION = "configuration"              # Config changes
    SYSTEM_EVENT = "system_event"               # System-level events
    ERROR = "error"                             # Errors occurred
    FIX = "fix"                                 # Fixes applied
    ROLLBACK = "rollback"                       # Rollbacks performed
    
    # HITL / Spindle Handoff Signals
    HITL_HANDOFF = "GRACE-OP-012"                # Moving from autonomous mode to HITL
    HITL_PROBLEMS = "GRACE-HO-004"               # Flagging a specific logic error or SMT timeout
    HITL_CONFIDENCE_LOW = "GRACE-GV-012"         # Layer score fell below threshold
    HITL_CLARIFICATION_REQ = "GRACE-CG-001"      # Requesting user clarification on a vague intent



class GenesisKeyStatus(str, enum.Enum):
    """Status of a Genesis Key."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    ROLLED_BACK = "rolled_back"
    ERROR = "error"
    FIXED = "fixed"


class FixSuggestionStatus(str, enum.Enum):
    """Status of fix suggestions."""
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"
    EXPIRED = "expired"


class GenesisKey(BaseModel):
    """
    Genesis Key - tracks every action with comprehensive metadata.

    Each Genesis Key captures:
    - What: The action/change that occurred
    - Where: Location in code/system
    - When: Timestamp
    - Who: User/system identifier
    - Why: Purpose/reason for change
    - How: Method/mechanism used
    """
    __tablename__ = "genesis_key"

    # Core identification
    key_id = Column(String(36), nullable=False, index=True, unique=True)
    parent_key_id = Column(String(36), nullable=True, index=True)  # For tracking chains
    key_type = Column(SQLEnum(GenesisKeyType), nullable=False, index=True)
    status = Column(SQLEnum(GenesisKeyStatus), nullable=False, default=GenesisKeyStatus.ACTIVE)

    # Profile and user tracking
    user_id = Column(String(255), nullable=True, index=True)  # Genesis-generated user ID
    user_profile = Column(JSON, nullable=True)  # User profile data
    session_id = Column(String(255), nullable=True, index=True)  # Session tracking

    # What, Where, When, Why, Who, How
    what_description = Column(Text, nullable=False)  # What happened
    where_location = Column(String(500), nullable=True)  # File path, function, line number
    when_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    why_reason = Column(Text, nullable=True)  # Purpose/justification
    who_actor = Column(String(255), nullable=False)  # User, system, or process
    how_method = Column(Text, nullable=True)  # How it was done

    # Code-specific tracking
    file_path = Column(String(500), nullable=True, index=True)
    line_number = Column(Integer, nullable=True)
    function_name = Column(String(255), nullable=True)
    code_before = Column(Text, nullable=True)
    code_after = Column(Text, nullable=True)

    # Error tracking
    is_error = Column(Boolean, nullable=False, default=False, index=True)
    error_type = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Fix tracking
    has_fix_suggestion = Column(Boolean, nullable=False, default=False, index=True)
    fix_applied = Column(Boolean, nullable=False, default=False)
    fix_key_id = Column(String(36), nullable=True)  # Links to fix Genesis Key

    # Version control
    commit_sha = Column(String(40), nullable=True, index=True)
    branch_name = Column(String(255), nullable=True)
    version_number = Column(String(50), nullable=True)

    # Metadata (human and AI readable)
    metadata_human = Column(Text, nullable=True)  # Human-readable summary
    metadata_ai = Column(JSON, nullable=True)  # Structured data for AI

    # Archival information
    archived_at = Column(DateTime, nullable=True)
    archive_path = Column(String(500), nullable=True)  # Path to archived data

    # Additional context
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    context_data = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)  # Searchable tags

    # Relationships
    fix_suggestions = relationship("FixSuggestion", back_populates="genesis_key", cascade="all, delete-orphan")

    # Indexing for performance
    __table_args__ = (
        Index('idx_key_type_status', 'key_type', 'status'),
        Index('idx_user_session', 'user_id', 'session_id'),
        Index('idx_error_fix', 'is_error', 'has_fix_suggestion'),
        Index('idx_timestamp', 'when_timestamp'),
        Index('idx_file_path', 'file_path'),
    )

    def __repr__(self):
        return f"<GenesisKey(key_id={self.key_id}, type={self.key_type}, who={self.who_actor})>"


class FixSuggestion(BaseModel):
    """
    Fix suggestions for errors detected by Genesis Key system.

    Provides one-click solutions like spell-check for code.
    """
    __tablename__ = "fix_suggestion"

    suggestion_id = Column(String(36), nullable=False, index=True, unique=True)
    genesis_key_id = Column(String(36), ForeignKey('genesis_key.key_id'), nullable=False, index=True)

    # Fix information
    suggestion_type = Column(String(100), nullable=False)  # "syntax", "logic", "performance", etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)  # "low", "medium", "high", "critical"

    # Code fix
    fix_code = Column(Text, nullable=True)  # Suggested code replacement
    fix_diff = Column(Text, nullable=True)  # Diff showing changes

    # Status
    status = Column(SQLEnum(FixSuggestionStatus), nullable=False, default=FixSuggestionStatus.PENDING)
    confidence = Column(Float, nullable=True)  # AI confidence in fix (0-1)

    # Application tracking
    applied_at = Column(DateTime, nullable=True)
    applied_by = Column(String(255), nullable=True)
    result_key_id = Column(String(36), nullable=True)  # Genesis Key for applied fix

    # Metadata
    fix_metadata = Column(JSON, nullable=True)

    # Relationship
    genesis_key = relationship("GenesisKey", back_populates="fix_suggestions")

    __table_args__ = (
        Index('idx_status_severity', 'status', 'severity'),
    )

    def __repr__(self):
        return f"<FixSuggestion(id={self.suggestion_id}, type={self.suggestion_type}, status={self.status})>"


class GenesisKeyArchive(BaseModel):
    """
    Daily archives of Genesis Keys for organization and reporting.

    Every 24 hours, keys are collected and stored with a generated report.
    """
    __tablename__ = "genesis_key_archive"

    archive_id = Column(String(36), nullable=False, index=True, unique=True)
    archive_date = Column(DateTime, nullable=False, index=True)

    # Archive metadata
    key_count = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    fix_count = Column(Integer, nullable=False, default=0)
    user_count = Column(Integer, nullable=False, default=0)

    # Statistics
    most_active_user = Column(String(255), nullable=True)
    most_changed_file = Column(String(500), nullable=True)
    most_common_error = Column(String(255), nullable=True)

    # Report
    report_summary = Column(Text, nullable=True)  # Human-readable summary
    report_data = Column(JSON, nullable=True)  # Detailed statistics

    # File paths
    archive_file_path = Column(String(500), nullable=True)
    report_file_path = Column(String(500), nullable=True)

    __table_args__ = (
        Index('idx_archive_date', 'archive_date'),
    )

    def __repr__(self):
        return f"<GenesisKeyArchive(date={self.archive_date}, keys={self.key_count})>"


class UserProfile(BaseModel):
    """
    User profiles for tracking actions with Genesis Keys.

    Each user gets a Genesis-generated ID for action tracking.
    """
    __tablename__ = "user_profile"

    user_id = Column(String(36), nullable=False, index=True, unique=True)
    username = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)

    # Profile metadata
    first_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Activity statistics
    total_actions = Column(Integer, nullable=False, default=0)
    total_changes = Column(Integer, nullable=False, default=0)
    total_errors = Column(Integer, nullable=False, default=0)
    total_fixes = Column(Integer, nullable=False, default=0)

    # Profile data
    preferences = Column(JSON, nullable=True)
    user_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_last_seen', 'last_seen'),
    )

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, username={self.username})>"
