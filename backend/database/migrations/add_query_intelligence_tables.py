"""
Database migration: Add query intelligence tables.

Creates tables for tracking multi-tier query handling:
- query_handling_log: Tracks tier usage and confidence scores
- knowledge_gaps: Stores identified knowledge gaps
- context_submissions: Records user-provided context
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Index,
    Table, MetaData,
)
from sqlalchemy.sql import func
from database.connection import DatabaseConnection
from database.base import Base


# ── Table definitions (database-agnostic via SQLAlchemy) ─────────────────

class QueryHandlingLog(Base):
    __tablename__ = "query_handling_log"
    __table_args__ = (
        Index("idx_query_handling_log_tier", "tier_used"),
        Index("idx_query_handling_log_created", "created_at"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(255), unique=True, nullable=False)
    query_text = Column(Text, nullable=False)
    tier_used = Column(String(50), nullable=False)
    confidence_score = Column(Float)

    # Tier 1: VectorDB metrics
    vectordb_attempted = Column(Boolean, default=False)
    vectordb_quality = Column(Float)
    vectordb_result_count = Column(Integer)

    # Tier 2: Model Knowledge metrics
    model_attempted = Column(Boolean, default=False)
    model_confidence = Column(Float)
    uncertainty_detected = Column(Boolean, default=False)

    # Tier 3: Context Request metrics
    context_requested = Column(Boolean, default=False)
    context_provided = Column(Boolean, default=False)

    # Outcome
    final_success = Column(Boolean, default=False)
    response_time_ms = Column(Integer)

    # Tracking
    created_at = Column(DateTime, server_default=func.now())
    genesis_key_id = Column(String(255))
    user_id = Column(String(255))


class KnowledgeGap(Base):
    __tablename__ = "knowledge_gaps"
    __table_args__ = (
        Index("idx_knowledge_gaps_query", "query_id"),
        Index("idx_knowledge_gaps_resolved", "resolved"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(255), ForeignKey("query_handling_log.query_id", ondelete="CASCADE"), nullable=False)
    gap_id = Column(String(255), unique=True, nullable=False)
    gap_topic = Column(String(255), nullable=False)
    specific_question = Column(Text, nullable=False)
    required = Column(Boolean, default=True)

    # Resolution tracking
    resolved = Column(Boolean, default=False)
    resolution_source = Column(String(50))
    resolved_at = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())


class ContextSubmission(Base):
    __tablename__ = "context_submissions"
    __table_args__ = (
        Index("idx_context_submissions_query", "query_id"),
        Index("idx_context_submissions_gap", "gap_id"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(255), ForeignKey("query_handling_log.query_id", ondelete="CASCADE"), nullable=False)
    gap_id = Column(String(255), ForeignKey("knowledge_gaps.gap_id", ondelete="SET NULL"))
    submitted_context = Column(Text, nullable=False)

    # Usage tracking
    used_in_response = Column(Boolean, default=False)
    improved_response = Column(Boolean)

    # Trust scoring
    trust_score = Column(Float, default=0.5)
    validated = Column(Boolean, default=False)

    # Tracking
    created_at = Column(DateTime, server_default=func.now())
    user_id = Column(String(255))
    genesis_key_id = Column(String(255))


def upgrade():
    """Create query intelligence tables."""
    engine = DatabaseConnection.get_engine()

    Base.metadata.create_all(
        engine,
        tables=[
            QueryHandlingLog.__table__,
            KnowledgeGap.__table__,
            ContextSubmission.__table__,
        ],
    )

    print("[OK] Query intelligence tables created successfully")


def downgrade():
    """Drop query intelligence tables."""
    engine = DatabaseConnection.get_engine()

    Base.metadata.drop_all(
        engine,
        tables=[
            ContextSubmission.__table__,
            KnowledgeGap.__table__,
            QueryHandlingLog.__table__,
        ],
    )

    print("[OK] Query intelligence tables dropped successfully")


if __name__ == "__main__":
    print("Running query intelligence tables migration...")
    upgrade()
    print("Migration complete!")
