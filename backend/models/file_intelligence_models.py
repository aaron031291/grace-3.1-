"""
File intelligence models for Grace-aligned file management.

Tables: file_intelligence, file_relationships, processing_strategies, file_health_checks.
Registered in database/migration.py so create_tables() creates them with all other app tables.
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey
from backend.database.base import BaseModel


class FileIntelligence(BaseModel):
    """File intelligence metadata - deep content understanding."""
    __tablename__ = "file_intelligence"

    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    content_summary = Column(Text, nullable=True)
    extracted_entities = Column(JSON, nullable=True)  # {people: [], places: [], concepts: []}
    detected_topics = Column(JSON, nullable=True)  # [topic1, topic2, ...]
    quality_score = Column(Float, nullable=True)  # 0.0-1.0
    complexity_level = Column(String(50), nullable=True)  # beginner/intermediate/advanced
    recommended_strategy = Column(JSON, nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=True)  # attribute name avoids shadowing Table.metadata


class FileRelationship(BaseModel):
    """Relationships between files - semantic connections."""
    __tablename__ = "file_relationships"

    file_a_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    file_b_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(100), nullable=True)  # semantic_similarity, entity_overlap, citation, etc.
    strength = Column(Float, nullable=True)  # 0.0-1.0
    detected_by = Column(String(100), nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=True)


class ProcessingStrategy(BaseModel):
    """Learned processing strategies for file types."""
    __tablename__ = "processing_strategies"

    file_type = Column(String(50), nullable=False)  # .pdf, .py, etc.
    strategy = Column(JSON, nullable=False)  # {chunk_size, overlap, use_semantic, etc.}
    success_rate = Column(Float, default=0.5, nullable=True)
    avg_quality_score = Column(Float, default=0.5, nullable=True)
    times_used = Column(Integer, default=0, nullable=True)
    last_used = Column(DateTime, nullable=True)


class FileHealthCheck(BaseModel):
    """File system health check history."""
    __tablename__ = "file_health_checks"

    health_status = Column(String(50), nullable=True)  # healthy, degraded, warning, critical
    anomalies_detected = Column(JSON, nullable=True)  # List of anomalies
    healing_actions = Column(JSON, nullable=True)  # List of actions taken
    genesis_key_id = Column(Integer, ForeignKey("genesis_key.id", ondelete="SET NULL"), nullable=True)
