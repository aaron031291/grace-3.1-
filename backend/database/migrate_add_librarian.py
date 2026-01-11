"""
Migration script to add Librarian System tables to Grace.

This migration adds 6 new tables for the Librarian System:
- librarian_tags: Tag definitions
- document_tags: Document-tag relationships
- document_relationships: Document relationship graph
- librarian_rules: Pattern matching rules
- librarian_actions: Approval workflow queue
- librarian_audit: Complete audit trail

Run this script to enable automatic file organization and categorization.
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import inspect
from database.connection import DatabaseConnection
from database.config import DatabaseConfig
from database.base import BaseModel
from models.database_models import Document, DocumentChunk  # Ensure Document model is loaded
from models.librarian_models import (
    LibrarianTag,
    DocumentTag,
    DocumentRelationship,
    LibrarianRule,
    LibrarianAction,
    LibrarianAudit
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Add Librarian System tables to the database."""
    logger.info("=" * 60)
    logger.info("Starting Librarian System migration...")
    logger.info("=" * 60)

    # Initialize database connection
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    engine = DatabaseConnection.get_engine()

    # Get inspector to check existing tables
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Tables to create (in dependency order)
    librarian_tables = [
        ('librarian_tags', LibrarianTag),
        ('document_tags', DocumentTag),
        ('document_relationships', DocumentRelationship),
        ('librarian_rules', LibrarianRule),
        ('librarian_actions', LibrarianAction),
        ('librarian_audit', LibrarianAudit)
    ]

    tables_created = []
    tables_skipped = []

    logger.info("")
    for table_name, model_class in librarian_tables:
        if table_name in existing_tables:
            logger.info(f"✓ Table '{table_name}' already exists, skipping...")
            tables_skipped.append(table_name)
        else:
            logger.info(f"→ Creating table '{table_name}'...")
            try:
                model_class.__table__.create(engine)
                tables_created.append(table_name)
                logger.info(f"  ✓ Table '{table_name}' created successfully")
            except Exception as e:
                logger.error(f"  ✗ Failed to create table '{table_name}': {e}")
                raise

    logger.info("")
    logger.info("=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    logger.info(f"Created: {len(tables_created)} tables")
    if tables_created:
        for table in tables_created:
            logger.info(f"  - {table}")

    if tables_skipped:
        logger.info(f"Skipped: {len(tables_skipped)} existing tables")
        for table in tables_skipped:
            logger.info(f"  - {table}")

    # Verify tables were created
    logger.info("")
    logger.info("Verifying table creation...")
    inspector = inspect(engine)
    final_tables = inspector.get_table_names()

    all_verified = True
    for table_name, _ in librarian_tables:
        if table_name in final_tables:
            logger.info(f"  ✓ Verified table '{table_name}' exists")
        else:
            logger.error(f"  ✗ Table '{table_name}' was not created!")
            all_verified = False

    logger.info("")
    logger.info("=" * 60)
    if all_verified:
        logger.info("✓ Librarian System is now active!")
    else:
        logger.error("✗ Some tables were not created. Check errors above.")
    logger.info("=" * 60)

    if all_verified:
        logger.info("")
        logger.info("The Librarian System provides:")
        logger.info("  • Automatic file categorization with hybrid rules + AI")
        logger.info("  • Flat tag system for flexible organization")
        logger.info("  • Document relationship tracking and knowledge graphs")
        logger.info("  • Tiered permissions with approval workflows")
        logger.info("  • Complete audit trail for all operations")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Seed default rules: python backend/librarian/seed_default_rules.py")
        logger.info("  2. Process existing documents: Use /librarian/process/all API endpoint")
        logger.info("  3. Configure settings in backend/settings.py")


if __name__ == "__main__":
    migrate()
