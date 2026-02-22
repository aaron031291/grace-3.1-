"""
Unified Migration Runner

Creates ALL tables in the correct order. One command.

Usage:
    python -m database.migrate_all

Or from startup:
    from database.migrate_all import run_all_migrations
    run_all_migrations()
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


def run_all_migrations():
    """Create ALL tables across the entire system."""
    from database.base import Base
    from database.connection import DatabaseConnection

    # Import ALL models so they register with Base.metadata
    model_imports = [
        "models.database_models",
        "models.genesis_key_models",
        "models.librarian_models",
        "models.llm_tracking_models",
        "models.notion_models",
        "models.query_intelligence_models",
        "models.telemetry_models",
        "cognitive.learning_memory",
        "cognitive.episodic_memory",
        "cognitive.procedural_memory",
        "cognitive.knowledge_compiler",
        "cognitive.task_completion_verifier",
        "cognitive.task_playbook_engine",
    ]

    imported = 0
    for module in model_imports:
        try:
            __import__(module)
            imported += 1
        except Exception as e:
            logger.debug(f"[MIGRATE] Skipped {module}: {e}")

    # Create all tables
    try:
        engine = DatabaseConnection.get_engine()
        Base.metadata.create_all(bind=engine)

        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print(f"[MIGRATE] Imported {imported}/{len(model_imports)} model modules")
        print(f"[MIGRATE] {len(tables)} tables exist in database")
        print(f"[MIGRATE] All migrations complete")

        return {"imported": imported, "tables": len(tables), "table_names": tables}

    except Exception as e:
        print(f"[MIGRATE] Error: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from database.connection import DatabaseConnection
    from database.config import DatabaseConfig, DatabaseType

    config = DatabaseConfig(db_type=DatabaseType.SQLITE, database_path="data/documents.db")
    DatabaseConnection.initialize(config)

    result = run_all_migrations()
    if "table_names" in result:
        for t in sorted(result["table_names"]):
            print(f"  {t}")
