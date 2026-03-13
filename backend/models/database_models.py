"""
Example models demonstrating database usage.
These are templates - modify or replace with your actual models.
"""

from sqlalchemy import Column, String, Text, Float, Boolean, ForeignKey, Index, Integer, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from backend.database.base import BaseModel
from datetime import datetime
import enum


class ChatType(str, enum.Enum):
    """Types of chat sessions."""
    GENERAL = "general"      # General purpose chat
    FORENSIC = "forensic"    # Forensic/diagnostic chat


class User(BaseModel):
    """User model for storing user information."""
    __tablename__ = "users"
    
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class Conversation(BaseModel):
    """Conversation model for storing chat conversations."""
    __tablename__ = "conversations"
    
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    model = Column(String(255), nullable=False, default="mistral:7b")
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_conversations_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title={self.title})>"


class Message(BaseModel):
    """Message model for storing individual messages in conversations."""
    __tablename__ = "messages"
    
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    tokens = Column(String, nullable=True)  # JSON array of token IDs
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    __table_args__ = (
        Index("idx_conversation_created", "conversation_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, role={self.role})>"


class Embedding(BaseModel):
    """Embedding model for storing vector embeddings."""
    __tablename__ = "embeddings"
    
    text = Column(Text, nullable=False)
    embedding = Column(Text, nullable=False)  # Store as JSON array string
    dimension = Column(Integer, nullable=False, default=384)
    model = Column(String(255), nullable=False)  # Model name set by application code
    source = Column(String(255), nullable=True)  # Source of the embedding (e.g., "document_id", "message_id")
    
    __table_args__ = (
        Index("idx_model_source", "model", "source"),
    )
    
    def __repr__(self) -> str:
        return f"<Embedding(id={self.id}, model={self.model}, dimension={self.dimension})>"


class Chat(BaseModel):
    """Chat session model for storing chat sessions."""
    __tablename__ = "chats"
    
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    model = Column(String(255), nullable=False, default="mistral:7b")
    temperature = Column(Float, default=0.7, nullable=False)
    chat_type = Column(SQLEnum(ChatType), nullable=False, default=ChatType.GENERAL, index=True)  # Chat type for context-aware search
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_message_at = Column(DateTime, nullable=True)
    folder_path = Column(String(512), nullable=True, default="", index=True)  # Path to folder context for this chat
    
    # Relationships
    chat_history = relationship("ChatHistory", back_populates="chat", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_chats_created", "created_at"),
        Index("idx_chats_active", "is_active"),
        Index("idx_chats_updated", "updated_at"),
        Index("idx_chats_folder_path", "folder_path"),
    )
    
    def __repr__(self) -> str:
        return f"<Chat(id={self.id}, title={self.title}, folder_path={self.folder_path})>"


class ChatHistory(BaseModel):
    """Chat history model for storing individual messages in a chat session."""
    __tablename__ = "chat_history"
    
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    tokens = Column(Integer, nullable=True)  # Number of tokens used
    token_ids = Column(Text, nullable=True)  # JSON array of token IDs
    completion_time = Column(Float, nullable=True)  # Time taken to generate response (in seconds)
    is_edited = Column(Boolean, default=False, nullable=False)
    edited_at = Column(DateTime, nullable=True)
    edited_content = Column(Text, nullable=True)  # Original content before edit
    message_metadata = Column(Text, nullable=True)  # JSON metadata for additional info
    
    # Relationships
    chat = relationship("Chat", back_populates="chat_history")
    
    __table_args__ = (
        Index("idx_chat_created", "chat_id", "created_at"),
        Index("idx_chat_role", "chat_id", "role"),
        Index("idx_role_created", "role", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ChatHistory(id={self.id}, chat_id={self.chat_id}, role={self.role})>"


# ==================== Knowledge Ingestion Models ====================

class Document(BaseModel):
    """Document model for storing metadata about ingested documents."""
    __tablename__ = "documents"
    
    filename = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(255), nullable=True)  # Original filename uploaded by user
    file_path = Column(String(512), nullable=True)  # Path where file is stored
    file_size = Column(Integer, nullable=True)  # Size in bytes
    content_hash = Column(String(64), nullable=True)  # SHA256 hash for deduplication
    source = Column(String(255), nullable=False, index=True)  # Source (e.g., "upload", "url", "api")
    mime_type = Column(String(100), nullable=True)  # MIME type of the file
    status = Column(String(50), nullable=False, default="pending", index=True)  # pending, processing, completed, failed
    processing_error = Column(Text, nullable=True)  # Error message if processing failed
    total_chunks = Column(Integer, default=0, nullable=False)
    extracted_text_length = Column(Integer, default=0, nullable=False)
    
    # ==================== Metadata Fields ====================
    upload_method = Column(String(50), nullable=False, default="ui-upload")  # ui-upload, ui-paste, api, etc.
    description = Column(Text, nullable=True)  # Optional description of document content
    tags = Column(Text, nullable=True)  # JSON array of tags for categorization
    document_metadata = Column(Text, nullable=True)  # JSON field for additional metadata
    
    # ==================== Confidence Scoring Fields ====================
    confidence_score = Column(Float, default=0.5, nullable=False)  # Auto-calculated confidence score (0.0-1.0)
    source_reliability = Column(Float, default=0.5, nullable=False)  # Source reliability component
    content_quality = Column(Float, default=0.5, nullable=False)  # Content quality component
    consensus_score = Column(Float, default=0.5, nullable=False)  # Consensus with existing knowledge
    recency_score = Column(Float, default=0.5, nullable=False)  # Recency component
    confidence_metadata = Column(Text, nullable=True)  # JSON field with detailed confidence calculation data
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_status_created", "status", "created_at"),
        Index("idx_source_created", "source", "created_at"),
        Index("idx_content_hash", "content_hash"),
        Index("idx_upload_method", "upload_method"),
        Index("idx_confidence_score", "confidence_score"),
    )
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"


class DocumentChunk(BaseModel):
    """Document chunk model for storing text chunks from documents."""
    __tablename__ = "document_chunks"
    
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)  # Position of chunk in document
    text_content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)  # Number of tokens in chunk
    embedding_vector_id = Column(String(64), nullable=True, index=True)  # ID in Qdrant
    embedding_model = Column(String(255), nullable=False)  # Model name set by application code
    char_start = Column(Integer, nullable=True)  # Starting character position in original text
    char_end = Column(Integer, nullable=True)  # Ending character position in original text
    chunk_metadata = Column(Text, nullable=True)  # JSON metadata (page number, section, etc.)
    
    # ==================== Confidence Scoring Fields ====================
    confidence_score = Column(Float, default=0.5, nullable=False)  # Auto-calculated confidence score (0.0-1.0)
    consensus_similarity_scores = Column(Text, nullable=True)  # JSON array of similarity scores from consensus calculation
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    __table_args__ = (
        Index("idx_document_chunks", "document_id", "chunk_index"),
        Index("idx_embedding_vector_id", "embedding_vector_id"),
        Index("idx_embedding_model", "embedding_model"),
        Index("idx_chunk_confidence_score", "confidence_score"),
    )
    
    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"


# ==================== Governance Models ====================

class GovernanceRule(BaseModel):
    """Governance rule model for storing operational and behavioral rules."""
    __tablename__ = "governance_rules"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    pillar_type = Column(String(50), nullable=False, index=True)  # operational, behavioral, immutable
    severity = Column(Integer, default=5, nullable=False)  # 1-10
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    pattern = Column(Text, nullable=True)  # Regex pattern for content matching
    action = Column(String(50), default="warn", nullable=False)  # warn, block, flag, redact
    source = Column(String(255), nullable=True)  # e.g., "ISO 27001", "GDPR", "User-defined"

    __table_args__ = (
        Index("idx_pillar_enabled", "pillar_type", "enabled"),
        Index("idx_severity", "severity"),
    )

    def __repr__(self) -> str:
        return f"<GovernanceRule(id={self.id}, name={self.name}, pillar={self.pillar_type})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "pillar_type": self.pillar_type,
            "severity": self.severity,
            "enabled": self.enabled,
            "pattern": self.pattern,
            "action": self.action,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GovernanceDocument(BaseModel):
    """Governance document model for uploaded compliance documents."""
    __tablename__ = "governance_documents"

    filename = Column(String(255), nullable=False)
    pillar_type = Column(String(50), nullable=False, index=True)
    status = Column(String(50), default="uploaded", nullable=False)  # uploaded, processing, processed, error
    file_path = Column(String(512), nullable=True)
    extracted_rules_count = Column(Integer, default=0)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_doc_pillar_status", "pillar_type", "status"),
    )

    def __repr__(self) -> str:
        return f"<GovernanceDocument(id={self.id}, filename={self.filename}, pillar={self.pillar_type})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "filename": self.filename,
            "pillar_type": self.pillar_type,
            "status": self.status,
            "extracted_rules": self.extracted_rules_count,
            "uploaded_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }


class GovernanceDecision(BaseModel):
    """Human-in-the-loop decision model for pending approvals."""
    __tablename__ = "governance_decisions"

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    pillar_type = Column(String(50), nullable=False, index=True)
    severity = Column(Integer, default=5, nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, confirmed, denied, discussing
    context = Column(JSON, nullable=True)  # JSON context data
    rule_reference = Column(String(255), nullable=True)  # Related rule name
    discussion = Column(JSON, nullable=True)  # Array of discussion messages
    resolution_note = Column(Text, nullable=True)
    resolved_by = Column(String(255), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Link to GovernanceEngine approval workflow
    approval_id = Column(String(64), nullable=True, index=True)  # Links to GovernanceEngine approval
    action_type = Column(String(100), nullable=True)  # The action that triggered this decision
    target_resource = Column(String(255), nullable=True)  # Resource affected by the action

    __table_args__ = (
        Index("idx_decision_status", "status"),
        Index("idx_decision_pillar", "pillar_type", "status"),
        Index("idx_decision_severity", "severity"),
        Index("idx_decision_approval", "approval_id"),
    )

    def __repr__(self) -> str:
        return f"<GovernanceDecision(id={self.id}, title={self.title}, status={self.status})>"

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "pillar_type": self.pillar_type,
            "severity": self.severity,
            "status": self.status,
            "context": self.context,
            "rule_reference": self.rule_reference,
            "discussion": self.discussion,
            "resolution_note": self.resolution_note,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "approval_id": self.approval_id,
            "action_type": self.action_type,
            "target_resource": self.target_resource,
        }


class AdaptiveOverride(BaseModel):
    """Stores user meta-learning overrides to governance/system rules."""
    __tablename__ = "adaptive_overrides"

    override_id = Column(String(64), nullable=False, index=True, unique=True)
    context = Column(String(255), nullable=False)
    rule_broken = Column(String(255), nullable=False)
    actual_metric = Column(String(255), nullable=True)
    user_action = Column(String(255), nullable=False)
    llm_analysis = Column(Text, nullable=True)
    proposed_rule = Column(Text, nullable=True)
    genesis_key_id = Column(String(255), nullable=True, index=True)
    status = Column(String(50), default="proposed", nullable=False)

    __table_args__ = (
        Index("idx_override_status", "status"),
        Index("idx_override_genesis", "genesis_key_id"),
    )

    def __repr__(self) -> str:
        return f"<AdaptiveOverride(id={self.id}, override_id={self.override_id}, status={self.status})>"

    def to_dict(self):
        return {
            "id": self.id,
            "override_id": self.override_id,
            "context": self.context,
            "rule_broken": self.rule_broken,
            "actual_metric": self.actual_metric,
            "user_action": self.user_action,
            "llm_analysis": self.llm_analysis,
            "proposed_rule": self.proposed_rule,
            "genesis_key": self.genesis_key_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Learning & Memory ORM Models (consolidation) ─────────────────────

class LearningExample(BaseModel):
    """Training data examples with trust scores."""
    __tablename__ = "learning_examples"
    __table_args__ = {"extend_existing": True}

    example_type = Column(String(100), default="general", index=True)
    input_context = Column(Text, nullable=True)
    expected_output = Column(Text, nullable=True)
    actual_output = Column(Text, nullable=True)
    trust_score = Column(Float, default=0.5, index=True)
    source = Column(String(255), default="system")
    file_path = Column(String(512), nullable=True)
    source_reliability = Column(Float, default=0.5)
    content_quality = Column(Float, default=0.5)
    consensus_score = Column(Float, default=0.5)
    recency_score = Column(Float, default=1.0)
    genesis_key_id = Column(String(255), nullable=True, index=True)
    procedure_id = Column(Integer, nullable=True, index=True)


class LearningPattern(BaseModel):
    """Extracted knowledge patterns."""
    __tablename__ = "learning_patterns"
    __table_args__ = {"extend_existing": True}

    pattern_name = Column(String(255), nullable=True)
    pattern_type = Column(String(100), default="general", index=True)
    pattern_data = Column(Text, nullable=True)
    trust_score = Column(Float, default=0.5, index=True)
    success_rate = Column(Float, default=0.5)
    usage_count = Column(Integer, default=0)


class Episode(BaseModel):
    """Episodic memory — concrete past experiences."""
    __tablename__ = "episodes"
    __table_args__ = {"extend_existing": True}

    problem = Column(Text, nullable=True)
    action = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    trust_score = Column(Float, default=0.5, index=True)
    source = Column(String(255), default="system")
    context = Column(Text, nullable=True)
    genesis_key_id = Column(String(255), nullable=True, index=True)


class Procedure(BaseModel):
    """Procedural memory — learned skills."""
    __tablename__ = "procedures"
    __table_args__ = {"extend_existing": True}

    name = Column(String(255), nullable=True)
    goal = Column(Text, nullable=True)
    procedure_type = Column(String(100), default="general", index=True)
    steps = Column(Text, nullable=True)
    trust_score = Column(Float, default=0.5, index=True)
    success_rate = Column(Float, default=0.5)
    usage_count = Column(Integer, default=0)
    genesis_key_id = Column(String(255), nullable=True, index=True)


class LLMUsageStats(BaseModel):
    """LLM usage tracking for BI dashboard (Improvement #7)."""
    __tablename__ = "llm_usage_stats"
    __table_args__ = {"extend_existing": True}

    provider = Column(String(100), nullable=False, index=True)
    model = Column(String(255), nullable=True)
    call_type = Column(String(50), default="generate")
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Float, default=0)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    caller = Column(String(255), nullable=True)


class GraphNode(BaseModel):
    """
    Persisted graph nodes for Magma / relation graphs (semantic, temporal, causal, entity).
    Used when graph state is stored in the DB. Table created so queries for graph_type='semantic' etc. succeed.
    """
    __tablename__ = "graph_nodes"
    __table_args__ = {"extend_existing": True}

    node_id = Column(String(255), nullable=False, index=True)
    graph_type = Column(String(64), nullable=False, index=True)
    node_type = Column(String(64), nullable=True)
    content = Column(Text, nullable=True)
    embedding_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    genesis_key_id = Column(String(255), nullable=True, index=True)
    trust_score = Column(Float, default=0.5, nullable=True)
    workspace_id = Column(String(255), nullable=True, index=True)

class SchemaProposal(BaseModel):
    """
    Autonomous Schema Evolution proposal model.
    Tracks LLM-generated SQLAlchemy ast code before human approval.
    """
    __tablename__ = "schema_proposals"
    __table_args__ = {"extend_existing": True}

    proposal_id = Column(String(100), unique=True, nullable=False, index=True)
    trigger_reason = Column(Text, nullable=False)
    proposed_code = Column(Text, nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True) # pending, approved, rejected, failed
    execution_logs = Column(Text, nullable=True)
    genesis_key_id = Column(String(255), nullable=True, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "proposal_id": self.proposal_id,
            "trigger_reason": self.trigger_reason,
            "proposed_code": self.proposed_code,
            "status": self.status,
            "execution_logs": self.execution_logs,
            "genesis_key": self.genesis_key_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
