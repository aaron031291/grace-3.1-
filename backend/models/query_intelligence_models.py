"""
SQLAlchemy models for query intelligence and multi-tier query handling.

These models track:
- Query handling decisions and tier usage
- Knowledge gaps identified during queries
- User-submitted context for gap resolution
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.base import BaseModel


class QueryHandlingLog(BaseModel):
    """
    Log of query handling decisions and tier usage.
    
    Tracks which tier was used for each query, confidence scores,
    and performance metrics for learning and optimization.
    """
    __tablename__ = "query_handling_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(255), unique=True, nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    tier_used = Column(String(50), nullable=False, index=True)
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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    genesis_key_id = Column(String(255))
    user_id = Column(String(255))
    
    # Relationships
    knowledge_gaps = relationship("KnowledgeGap", back_populates="query_log", cascade="all, delete-orphan")
    context_submissions = relationship("ContextSubmission", back_populates="query_log", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<QueryHandlingLog(id={self.id}, query_id='{self.query_id}', tier='{self.tier_used}', confidence={self.confidence_score})>"


class KnowledgeGap(BaseModel):
    """
    Identified knowledge gaps during query processing.
    
    Represents specific pieces of information that were missing
    and needed to answer a query completely.
    """
    __tablename__ = "knowledge_gaps"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(255), ForeignKey("query_handling_log.query_id", ondelete="CASCADE"), nullable=False, index=True)
    gap_id = Column(String(255), unique=True, nullable=False)
    gap_topic = Column(String(255), nullable=False)
    specific_question = Column(Text, nullable=False)
    required = Column(Boolean, default=True)
    
    # Resolution tracking
    resolved = Column(Boolean, default=False, index=True)
    resolution_source = Column(String(50))
    resolved_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    query_log = relationship("QueryHandlingLog", back_populates="knowledge_gaps")
    context_submissions = relationship("ContextSubmission", back_populates="knowledge_gap")
    
    def __repr__(self):
        return f"<KnowledgeGap(id={self.id}, gap_id='{self.gap_id}', topic='{self.gap_topic}', resolved={self.resolved})>"


class ContextSubmission(BaseModel):
    """
    User-submitted context to fill knowledge gaps.
    
    Stores context provided by users to help answer queries
    where the system lacked sufficient information.
    """
    __tablename__ = "context_submissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(255), ForeignKey("query_handling_log.query_id", ondelete="CASCADE"), nullable=False, index=True)
    gap_id = Column(String(255), ForeignKey("knowledge_gaps.gap_id", ondelete="SET NULL"), index=True)
    submitted_context = Column(Text, nullable=False)
    
    # Usage tracking
    used_in_response = Column(Boolean, default=False)
    improved_response = Column(Boolean)
    
    # Trust scoring
    trust_score = Column(Float, default=0.5)
    validated = Column(Boolean, default=False)
    
    # Tracking
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = Column(String(255))
    genesis_key_id = Column(String(255))
    
    # Relationships
    query_log = relationship("QueryHandlingLog", back_populates="context_submissions")
    knowledge_gap = relationship("KnowledgeGap", back_populates="context_submissions")
    
    def __repr__(self):
        return f"<ContextSubmission(id={self.id}, query_id='{self.query_id}', gap_id='{self.gap_id}', used={self.used_in_response})>"
