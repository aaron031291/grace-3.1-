"""
Migration script to add telemetry and self-modeling tables to Grace.

Run this script to add the operation tracking, baselines, drift detection,
and replay tables to the database.
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import inspect
from database.connection import DatabaseConnection
from database.base import BaseModel
from models.telemetry_models import (
    OperationLog,
    PerformanceBaseline,
    DriftAlert,
    OperationReplay,
    SystemState
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Add telemetry tables to the database."""
    logger.info("Starting telemetry tables migration...")

    # Initialize database connection
    from database.config import DatabaseConfig
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)
    engine = DatabaseConnection.get_engine()

    # Get inspector to check existing tables
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Tables to create
    telemetry_tables = [
        ('operation_log', OperationLog),
        ('performance_baseline', PerformanceBaseline),
        ('drift_alert', DriftAlert),
        ('operation_replay', OperationReplay),
        ('system_state', SystemState)
    ]

    tables_created = []
    tables_skipped = []

    for table_name, model_class in telemetry_tables:
        if table_name in existing_tables:
            logger.info(f"Table '{table_name}' already exists, skipping...")
            tables_skipped.append(table_name)
        else:
            logger.info(f"Creating table '{table_name}'...")
            model_class.__table__.create(engine)
            tables_created.append(table_name)

    logger.info("\nMigration complete!")
    logger.info(f"Created {len(tables_created)} tables: {', '.join(tables_created)}")
    if tables_skipped:
        logger.info(f"Skipped {len(tables_skipped)} existing tables: {', '.join(tables_skipped)}")

    # Verify tables were created
    inspector = inspect(engine)
    final_tables = inspector.get_table_names()

    for table_name, _ in telemetry_tables:
        if table_name in final_tables:
            logger.info(f"✓ Verified table '{table_name}' exists")
        else:
            logger.error(f"✗ Table '{table_name}' was not created!")

    logger.info("\nSelf-modeling mechanism is now active.")
    logger.info("Grace can now track operations, learn baselines, and detect drift.")


if __name__ == "__main__":
    migrate()
