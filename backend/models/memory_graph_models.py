"""
Persistent graph memory models — nodes, edges, and user thinking patterns.

These models back MAGMA's in-memory graphs with database persistence.
On startup, graphs are rehydrated from the database.
On every add_node/add_edge, the change is persisted.

User thinking pattern models track how each user communicates,
what topics they focus on, and how Grace should adapt.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.database.base import BaseModel
from datetime import datetime, timezone


class GraphNodeRecord(BaseModel):
    """Persistent storage for MAGMA graph nodes."""
    __tablename__ = "graph_nodes"

    node_id = Column(String(255), unique=True, nullable=False, index=True)
    graph_type = Column(String(50), nullable=False, index=True)
    node_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    genesis_key_id = Column(String(255), nullable=True, index=True)
    trust_score = Column(Float, default=0.5)
    workspace_id = Column(String(255), nullable=True, index=True)

    __table_args__ = (
        Index("idx_gn_graph_type", "graph_type"),
        Index("idx_gn_workspace", "workspace_id"),
    )


class GraphEdgeRecord(BaseModel):
    """Persistent storage for MAGMA graph edges."""
    __tablename__ = "graph_edges"

    edge_id = Column(String(255), unique=True, nullable=False, index=True)
    graph_type = Column(String(50), nullable=False, index=True)
    source_node_id = Column(String(255), nullable=False, index=True)
    target_node_id = Column(String(255), nullable=False, index=True)
    relation_type = Column(String(100), nullable=False)
    weight = Column(Float, default=1.0)
    confidence = Column(Float, default=0.5)
    metadata_json = Column(JSON, default=dict)
    genesis_key_id = Column(String(255), nullable=True)
    workspace_id = Column(String(255), nullable=True, index=True)

    __table_args__ = (
        Index("idx_ge_source", "source_node_id"),
        Index("idx_ge_target", "target_node_id"),
        Index("idx_ge_relation", "relation_type"),
    )


class UserThinkingPattern(BaseModel):
    """
    Tracks how a user thinks, communicates, and works.

    Grace observes each user's interactions over time and builds a profile:
    - Communication style (verbose vs concise, technical vs casual)
    - Topic preferences (what they ask about most)
    - Problem-solving approach (methodical vs exploratory)
    - Response preferences (code-first vs explanation-first)
    - Time patterns (when they're active, session lengths)
    - Error patterns (common mistakes, recurring issues)
    """
    __tablename__ = "user_thinking_patterns"

    user_id = Column(String(255), nullable=False, index=True)
    pattern_type = Column(String(100), nullable=False, index=True)
    pattern_key = Column(String(255), nullable=False)
    pattern_value = Column(Text, nullable=False)
    confidence = Column(Float, default=0.5)
    observation_count = Column(Integer, default=1)
    last_observed = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    metadata_json = Column(JSON, default=dict)

    __table_args__ = (
        Index("idx_utp_user_type", "user_id", "pattern_type"),
        Index("idx_utp_user_key", "user_id", "pattern_key"),
    )


class UserInteractionLog(BaseModel):
    """
    Raw interaction log for user pattern extraction.

    Every user message is logged (content hash only, not full content for privacy)
    with metadata that the pattern learner analyzes.
    """
    __tablename__ = "user_interaction_logs"

    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    interaction_type = Column(String(50), nullable=False)
    content_hash = Column(String(64), nullable=True)
    content_length = Column(Integer, default=0)
    topic_tags = Column(JSON, default=list)
    response_type = Column(String(50), nullable=True)
    response_length = Column(Integer, default=0)
    response_time_ms = Column(Float, default=0)
    satisfaction_signal = Column(Float, nullable=True)
    metadata_json = Column(JSON, default=dict)

    __table_args__ = (
        Index("idx_uil_user_session", "user_id", "session_id"),
        Index("idx_uil_user_type", "user_id", "interaction_type"),
    )
