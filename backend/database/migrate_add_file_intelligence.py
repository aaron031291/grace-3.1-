"""
Database Migration: Add File Intelligence Tables

File intelligence tables are now defined in models/file_intelligence_models.py
and created by database/migration.create_tables() with all other app tables.

This script remains for backwards compatibility: it just runs the shared create_tables().
Run once or rely on app startup create_tables() - no separate table creation needed.
"""

import logging
from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from database.migration import create_tables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Ensure file intelligence tables exist (via shared create_tables)."""
    try:
        logger.info("=" * 60)
        logger.info("MIGRATION: File Intelligence Tables (via create_tables)")
        logger.info("=" * 60)

        config = DatabaseConfig()
        DatabaseConnection.initialize(config)

        logger.info("Creating all app tables (including file_intelligence, file_relationships, etc.)...")
        create_tables()

        logger.info("✓ file_intelligence, file_relationships, processing_strategies, file_health_checks")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error("Migration failed: %s", e, exc_info=True)
        return False


if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)
