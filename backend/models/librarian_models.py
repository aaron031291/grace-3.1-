"""
Librarian System Models

Database models for the Grace Librarian System, which provides:
- Automatic file categorization and tagging
- Document relationship tracking
- Rule-based pattern matching
- Approval workflow for sensitive operations
- Complete audit trail

The librarian system automatically organizes and indexes all files from:
- User uploads
- Human-created content
- Grace's autonomous actions
"""

from sqlalchemy import Column, String, Text, Float, Boolean, ForeignKey, Index, Integer, DateTime, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from backend.database.base import BaseModel
from datetime import datetime


class LibrarianTag(BaseModel):
    """
    Tag definitions for document categorization.

    Supports flat tag system where documents can have multiple tags.
    Tags are case-insensitive and normalized (lowercase).

    Examples:
        - "AI", "research", "technical"
        - "python", "code", "documentation"
        - "tutorial", "beginner-friendly"
    """
    __tablename__ = "librarian_tags"

    name = Column(String(100), unique=True, nullable=False, index=True)  # Normalized (lowercase)
    description = Column(Text, nullable=True)  # Tag description for UI
    color = Column(String(7), default="#3B82F6")  # Hex color code for UI badges
    category = Column(String(50), nullable=True, index=True)  # Optional grouping: ai, research, code, etc.
    usage_count = Column(Integer, default=0, index=True)  # Number of documents with this tag
    parent_tag_id = Column(Integer, ForeignKey("librarian_tags.id"), nullable=True)  # Optional for future hierarchy
    tag_metadata = Column(JSON, nullable=True)  # Extensible metadata

    # Relationships
    parent_tag = relationship("LibrarianTag", remote_side="LibrarianTag.id", backref="child_tags")

    __table_args__ = (
        Index("idx_tag_name", "name"),
        Index("idx_tag_category", "category"),
        Index("idx_tag_usage", "usage_count"),
    )

    def __repr__(self) -> str:
        return f"<LibrarianTag(id={self.id}, name={self.name}, usage_count={self.usage_count})>"


class DocumentTag(BaseModel):
    """
    Many-to-many junction table for document-tag relationships.

    Tracks WHO assigned each tag and with what confidence level.
    """
    __tablename__ = "document_tags"

    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("librarian_tags.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by = Column(String(50), default="auto")  # "auto", "user", "ai", "rule"
    confidence = Column(Float, default=1.0)  # Confidence in tag assignment (0.0-1.0)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assignment_metadata = Column(JSON, nullable=True)  # Additional context (e.g., rule_id, ai_reasoning)

    # Relationships
    tag = relationship("LibrarianTag", backref="document_assignments")

    __table_args__ = (
        Index("idx_document_tags_unique", "document_id", "tag_id", unique=True),
        Index("idx_document_id", "document_id"),
        Index("idx_tag_id", "tag_id"),
        Index("idx_assigned_by", "assigned_by"),
    )

    def __repr__(self) -> str:
        return f"<DocumentTag(document_id={self.document_id}, tag_id={self.tag_id}, assigned_by={self.assigned_by})>"


class DocumentRelationship(BaseModel):
    """
    Typed relationships between documents for knowledge graph.

    Relationship Types:
        - citation: Source document references target
        - prerequisite: Target must be read before source
        - related: Similar topic or content
        - version: Source is newer/older version of target
        - supersedes: Source replaces target
        - part_of: Source is part of target collection
        - duplicate: Source is duplicate of target

    Properties:
        - confidence: How certain we are about this relationship (0.0-1.0)
        - strength: Semantic similarity or relevance strength (0.0-1.0)
        - bidirectional: If True, relationship applies both ways
    """
    __tablename__ = "document_relationships"

    source_document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    target_document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(50), nullable=False, index=True)  # citation, prerequisite, related, version, etc.
    confidence = Column(Float, default=1.0)  # Confidence in relationship (0.0-1.0)
    strength = Column(Float, default=0.5)  # Semantic similarity or relevance (0.0-1.0)
    detected_by = Column(String(50), default="auto")  # "auto", "user", "embedding", "heuristic"
    bidirectional = Column(Boolean, default=False)  # If True, relationship goes both ways
    relationship_metadata = Column(JSON, nullable=True)  # Additional context (similarity_score, matched_pattern, etc.)

    __table_args__ = (
        CheckConstraint("source_document_id != target_document_id", name="check_not_self_referential"),
        Index("idx_source_document", "source_document_id"),
        Index("idx_target_document", "target_document_id"),
        Index("idx_relationship_type", "relationship_type"),
        Index("idx_source_target_type", "source_document_id", "target_document_id", "relationship_type"),
    )

    def __repr__(self) -> str:
        return f"<DocumentRelationship(source={self.source_document_id}, target={self.target_document_id}, type={self.relationship_type})>"


class LibrarianRule(BaseModel):
    """
    Pattern matching rules for automatic categorization.

    Rules execute in priority order (higher priority first).
    Multiple rules can match the same document.

    Pattern Types:
        - extension: Match file extension (e.g., r"\\.pdf$")
        - filename: Match filename (e.g., r"^README.*")
        - path: Match file path (e.g., r"ai research")
        - mime_type: Match MIME type
        - content: Match text content (expensive, opt-in)

    Action Types:
        - assign_tag: Assign one or more tags
        - set_category: Set document category
        - move_to_folder: Move to specific folder (requires approval)

    Example:
        {
            "name": "PDF Documents",
            "pattern_type": "extension",
            "pattern_value": r"\\.pdf$",
            "action_type": "assign_tag",
            "action_params": {"tag_names": ["document", "pdf"]},
            "priority": 10
        }
    """
    __tablename__ = "librarian_rules"

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, index=True)
    priority = Column(Integer, default=0, index=True)  # Higher = runs first

    # Pattern matching
    pattern_type = Column(String(50), nullable=False, index=True)  # extension, filename, path, mime_type, content
    pattern_value = Column(Text, nullable=False)  # Regex pattern
    case_sensitive = Column(Boolean, default=False)

    # Action to take when pattern matches
    action_type = Column(String(50), nullable=False, index=True)  # assign_tag, set_category, move_to_folder
    action_params = Column(JSON, nullable=False)  # e.g., {"tag_names": ["AI", "research"]}

    # Statistics
    matches_count = Column(Integer, default=0)
    last_matched_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_enabled_priority", "enabled", "priority"),
        Index("idx_pattern_type", "pattern_type"),
        Index("idx_action_type", "action_type"),
    )

    def __repr__(self) -> str:
        return f"<LibrarianRule(id={self.id}, name={self.name}, priority={self.priority}, enabled={self.enabled})>"


class LibrarianAction(BaseModel):
    """
    Approval workflow queue for librarian actions.

    Actions are classified into permission tiers:
        - Auto-commit: Execute immediately (tag assignment, metadata updates, indexing)
        - Approval required: Wait for human approval (folder creation, file deletion, moves)

    Status Flow:
        pending → approved/rejected → executed (if approved)

    Actions can be reviewed by humans before execution.
    All actions are logged to audit trail.
    """
    __tablename__ = "librarian_actions"

    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
    action_type = Column(String(50), nullable=False, index=True)  # assign_tag, create_folder, delete_file, etc.
    action_params = Column(JSON, nullable=False)  # Parameters for the action
    permission_tier = Column(String(20), nullable=False, index=True)  # "auto", "approval_required"
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending, approved, rejected, executed

    # Context
    triggered_by = Column(String(50), nullable=True)  # "upload", "manual", "rule", "ai", "grace"
    reason = Column(Text, nullable=True)  # Human-readable explanation
    confidence = Column(Float, default=1.0)  # Confidence in the action (0.0-1.0)

    # Review
    reviewed_by = Column(String(100), nullable=True)  # User who approved/rejected
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)

    # Execution
    executed_at = Column(DateTime, nullable=True)
    execution_error = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_libaction_status_tier", "status", "permission_tier"),
        Index("idx_libaction_document_status", "document_id", "status"),
        Index("idx_libaction_type", "action_type"),
        Index("idx_libaction_triggered_by", "triggered_by"),
    )

    def __repr__(self) -> str:
        return f"<LibrarianAction(id={self.id}, action_type={self.action_type}, status={self.status}, tier={self.permission_tier})>"


class LibrarianAudit(BaseModel):
    """
    Complete audit trail for all librarian actions.

    Records:
        - What action was taken
        - When it was executed
        - Who triggered it
        - Result (success/failure)
        - Rollback data for undo operations

    Enables:
        - Debugging failed operations
        - Compliance and accountability
        - Rollback/undo functionality
        - Performance analysis
    """
    __tablename__ = "librarian_audit"

    action_id = Column(Integer, ForeignKey("librarian_actions.id", ondelete="SET NULL"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type = Column(String(50), nullable=False, index=True)
    action_details = Column(JSON, nullable=False)  # Complete action parameters and context
    status = Column(String(20), nullable=False, index=True)  # "success", "failed", "rolled_back"
    executed_by = Column(String(50), nullable=True)  # "system", "user", "grace", "rule"
    execution_time_ms = Column(Float, nullable=True)  # Execution duration in milliseconds
    error_message = Column(Text, nullable=True)  # Error details if status="failed"
    rollback_data = Column(JSON, nullable=True)  # Data needed to undo this action

    __table_args__ = (
        Index("idx_libaudit_action_id", "action_id"),
        Index("idx_libaudit_document_id", "document_id"),
        Index("idx_libaudit_action_type", "action_type"),
        Index("idx_libaudit_status_created", "status", "created_at"),
        Index("idx_libaudit_executed_by", "executed_by"),
    )

    def __repr__(self) -> str:
        return f"<LibrarianAudit(id={self.id}, action_type={self.action_type}, status={self.status})>"
