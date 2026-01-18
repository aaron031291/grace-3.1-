import logging
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from database.config import DatabaseConfig
from database.connection import DatabaseConnection
logger = logging.getLogger(__name__)

class FileIntelligenceModel(Base):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """File intelligence metadata."""
    __tablename__ = 'file_intelligence'

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, unique=True)
    content_summary = Column(Text)
    extracted_entities = Column(JSON)  # {people: [], places: [], concepts: []}
    detected_topics = Column(JSON)     # [topic1, topic2, ...]
    quality_score = Column(Float)      # 0.0-1.0
    complexity_level = Column(String(50))  # beginner/intermediate/advanced
    recommended_strategy = Column(JSON)
    metadata = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FileRelationshipModel(Base):
    """Relationships between files."""
    __tablename__ = 'file_relationships'

    id = Column(Integer, primary_key=True)
    file_a_id = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    file_b_id = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    relationship_type = Column(String(100))  # semantic_similarity, entity_overlap, citation, etc.
    strength = Column(Float)  # 0.0-1.0
    detected_by = Column(String(100))
    metadata = Column(JSON)  # Additional relationship data
    created_at = Column(DateTime, server_default=func.now())


class ProcessingStrategyModel(Base):
    """Learned processing strategies."""
    __tablename__ = 'processing_strategies'

    id = Column(Integer, primary_key=True)
    file_type = Column(String(50), nullable=False)  # .pdf, .py, etc.
    strategy = Column(JSON, nullable=False)  # {chunk_size, overlap, use_semantic, etc.}
    success_rate = Column(Float, default=0.5)
    avg_quality_score = Column(Float, default=0.5)
    times_used = Column(Integer, default=0)
    last_used = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FileHealthCheckModel(Base):
    """File system health check history."""
    __tablename__ = 'file_health_checks'

    id = Column(Integer, primary_key=True)
    health_status = Column(String(50))  # healthy, degraded, warning, critical
    anomalies_detected = Column(JSON)  # List of anomalies
    healing_actions = Column(JSON)  # List of actions taken
    genesis_key_id = Column(Integer, ForeignKey('genesis_key.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


def run_migration():
    """Run the migration."""
    try:
        logger.info("="*60)
        logger.info("MIGRATION: Add File Intelligence Tables")
        logger.info("="*60)

        # Initialize database connection
        config = DatabaseConfig()
        DatabaseConnection.initialize(config)
        engine = DatabaseConnection.get_engine()

        logger.info("\nCreating tables...")

        # Create all tables
        Base.metadata.create_all(engine)

        logger.info("✓ file_intelligence")
        logger.info("✓ file_relationships")
        logger.info("✓ processing_strategies")
        logger.info("✓ file_health_checks")

        logger.info("\n" + "="*60)
        logger.info("MIGRATION COMPLETE")
        logger.info("="*60)

        # Show summary
        logger.info("\nNew Tables:")
        logger.info("  1. file_intelligence - Deep content understanding")
        logger.info("  2. file_relationships - Semantic file connections")
        logger.info("  3. processing_strategies - Learned optimizations")
        logger.info("  4. file_health_checks - Health monitoring history")

        return True

    except Exception as e:
        logger.error(f"\n[ERROR] Migration failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)
