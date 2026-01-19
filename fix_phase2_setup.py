"""
Fix Phase 2 Setup

Creates missing database tables in the correct location.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from sqlalchemy import text

def create_tables():
    """Create Phase 2 database tables."""
    logger.info("Creating Phase 2 database tables...")

    # Initialize database
    db_config = DatabaseConfig()
    DatabaseConnection.initialize(db_config)
    engine = DatabaseConnection.get_engine()

    # Create tables using raw SQL
    tables = [
        """
        CREATE TABLE IF NOT EXISTS file_intelligence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
            content_summary TEXT,
            extracted_entities TEXT,
            detected_topics TEXT,
            quality_score REAL,
            complexity_level TEXT,
            recommended_strategy TEXT,
            additional_metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS file_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_a_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            file_b_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            relationship_type TEXT,
            strength REAL,
            detected_by TEXT,
            relationship_metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS processing_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_type TEXT NOT NULL,
            strategy TEXT NOT NULL,
            success_rate REAL DEFAULT 0.5,
            avg_quality_score REAL DEFAULT 0.5,
            times_used INTEGER DEFAULT 0,
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS file_health_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            health_status TEXT,
            anomalies_detected TEXT,
            healing_actions TEXT,
            genesis_key_id INTEGER REFERENCES genesis_key(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]

    with engine.connect() as conn:
        for table_sql in tables:
            conn.execute(text(table_sql))
            conn.commit()

    logger.info("✓ file_intelligence")
    logger.info("✓ file_relationships")
    logger.info("✓ processing_strategies")
    logger.info("✓ file_health_checks")
    logger.info("\nPhase 2 tables created successfully!")

if __name__ == "__main__":
    create_tables()
