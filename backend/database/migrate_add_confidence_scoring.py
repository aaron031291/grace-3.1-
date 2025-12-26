"""
Migration script to add confidence scoring columns to documents and document_chunks tables.

This migration adds the following columns:

For documents table:
- confidence_score: Main confidence score (0.0-1.0)
- source_reliability: Source reliability component
- content_quality: Content quality component
- consensus_score: Consensus with existing knowledge
- recency_score: Recency component
- confidence_metadata: JSON field with detailed calculation data

For document_chunks table:
- confidence_score: Chunk-level confidence score
- consensus_similarity_scores: JSON array of similarity scores

The migration also drops the old trust_score column from documents table
and updates indexes for the new confidence_score column.
"""

from sqlalchemy import Column, Float, Text, inspect, text
import logging
from datetime import datetime
import sys
from pathlib import Path

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from database.migration import table_exists, get_table_columns

logger = logging.getLogger(__name__)


def migrate_add_confidence_scoring():
    """
    Add confidence scoring columns to documents and document_chunks tables.
    """
    # Initialize database connection if not already done
    try:
        DatabaseConnection.get_engine()
    except RuntimeError:
        # Not initialized, so initialize it
        config = DatabaseConfig(db_type=DatabaseType.SQLITE)
        DatabaseConnection.initialize(config)
    
    engine = DatabaseConnection.get_engine()
    
    with engine.connect() as connection:
        # Check if documents table exists
        if not table_exists("documents"):
            logger.warning("documents table does not exist, skipping migration")
            return
        
        # Get existing columns
        docs_columns = get_table_columns("documents")
        chunks_columns = get_table_columns("document_chunks")
        
        # Track what was added
        added_columns = {
            "documents": [],
            "document_chunks": [],
        }
        
        # ==================== Migrate documents table ====================
        logger.info("Migrating documents table...")
        
        # Add confidence_score if it doesn't exist
        if "confidence_score" not in docs_columns:
            logger.info("Adding confidence_score column to documents table...")
            try:
                connection.execute(
                    text("ALTER TABLE documents ADD COLUMN confidence_score FLOAT DEFAULT 0.5 NOT NULL")
                )
                added_columns["documents"].append("confidence_score")
                logger.info("✓ Added confidence_score")
            except Exception as e:
                logger.error(f"Error adding confidence_score: {e}")
        
        # Add source_reliability if it doesn't exist
        if "source_reliability" not in docs_columns:
            logger.info("Adding source_reliability column to documents table...")
            try:
                connection.execute(
                    text("ALTER TABLE documents ADD COLUMN source_reliability FLOAT DEFAULT 0.5 NOT NULL")
                )
                added_columns["documents"].append("source_reliability")
                logger.info("✓ Added source_reliability")
            except Exception as e:
                logger.error(f"Error adding source_reliability: {e}")
        
        # Add content_quality if it doesn't exist
        if "content_quality" not in docs_columns:
            logger.info("Adding content_quality column to documents table...")
            try:
                connection.execute(
                    text("ALTER TABLE documents ADD COLUMN content_quality FLOAT DEFAULT 0.5 NOT NULL")
                )
                added_columns["documents"].append("content_quality")
                logger.info("✓ Added content_quality")
            except Exception as e:
                logger.error(f"Error adding content_quality: {e}")
        
        # Add consensus_score if it doesn't exist
        if "consensus_score" not in docs_columns:
            logger.info("Adding consensus_score column to documents table...")
            try:
                connection.execute(
                    text("ALTER TABLE documents ADD COLUMN consensus_score FLOAT DEFAULT 0.5 NOT NULL")
                )
                added_columns["documents"].append("consensus_score")
                logger.info("✓ Added consensus_score")
            except Exception as e:
                logger.error(f"Error adding consensus_score: {e}")
        
        # Add recency_score if it doesn't exist
        if "recency_score" not in docs_columns:
            logger.info("Adding recency_score column to documents table...")
            try:
                connection.execute(
                    text("ALTER TABLE documents ADD COLUMN recency_score FLOAT DEFAULT 0.5 NOT NULL")
                )
                added_columns["documents"].append("recency_score")
                logger.info("✓ Added recency_score")
            except Exception as e:
                logger.error(f"Error adding recency_score: {e}")
        
        # Add confidence_metadata if it doesn't exist
        if "confidence_metadata" not in docs_columns:
            logger.info("Adding confidence_metadata column to documents table...")
            try:
                connection.execute(
                    text("ALTER TABLE documents ADD COLUMN confidence_metadata TEXT")
                )
                added_columns["documents"].append("confidence_metadata")
                logger.info("✓ Added confidence_metadata")
            except Exception as e:
                logger.error(f"Error adding confidence_metadata: {e}")
        
        # Drop trust_score if it still exists (old field)
        if "trust_score" in docs_columns:
            logger.info("Removing old trust_score column from documents table...")
            try:
                connection.execute(
                    text("ALTER TABLE documents DROP COLUMN trust_score")
                )
                logger.info("✓ Dropped trust_score")
            except Exception as e:
                logger.warning(f"Could not drop trust_score (may not exist): {e}")
        
        # ==================== Migrate document_chunks table ====================
        logger.info("Migrating document_chunks table...")
        
        # Add confidence_score if it doesn't exist
        if "confidence_score" not in chunks_columns:
            logger.info("Adding confidence_score column to document_chunks table...")
            try:
                connection.execute(
                    text("ALTER TABLE document_chunks ADD COLUMN confidence_score FLOAT DEFAULT 0.5 NOT NULL")
                )
                added_columns["document_chunks"].append("confidence_score")
                logger.info("✓ Added confidence_score")
            except Exception as e:
                logger.error(f"Error adding confidence_score: {e}")
        
        # Add consensus_similarity_scores if it doesn't exist
        if "consensus_similarity_scores" not in chunks_columns:
            logger.info("Adding consensus_similarity_scores column to document_chunks table...")
            try:
                connection.execute(
                    text("ALTER TABLE document_chunks ADD COLUMN consensus_similarity_scores TEXT")
                )
                added_columns["document_chunks"].append("consensus_similarity_scores")
                logger.info("✓ Added consensus_similarity_scores")
            except Exception as e:
                logger.error(f"Error adding consensus_similarity_scores: {e}")
        
        # Commit all changes
        connection.commit()
        
        # Log summary
        from datetime import timezone
        now = datetime.now(timezone.utc)
        logger.info(f"Migration completed at {now.isoformat()}")
        logger.info(f"Documents table columns added: {added_columns['documents']}")
        logger.info(f"Document_chunks table columns added: {added_columns['document_chunks']}")
        
        return added_columns


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting confidence scoring migration...")
    result = migrate_add_confidence_scoring()
    logger.info("Migration completed successfully!")
