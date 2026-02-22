"""
Migration: Add LLM Learning and Tracking Tables

Creates tables for:
- llm_interactions: Records every LLM interaction
- reasoning_paths: Captures reasoning chains
- extracted_patterns: Patterns learned from LLM interactions
- coding_task_records: Tracks coding task delegation
- llm_dependency_metrics: Dependency reduction tracking
"""

import logging
from sqlalchemy import inspect
from database.base import Base
from database.connection import DatabaseConnection

from models.llm_tracking_models import (
    LLMInteraction,
    ReasoningPath,
    ExtractedPattern,
    CodingTaskRecord,
    LLMDependencyMetric,
)

logger = logging.getLogger(__name__)

TABLES = [
    "llm_interactions",
    "reasoning_paths",
    "extracted_patterns",
    "coding_task_records",
    "llm_dependency_metrics",
]


def run_migration():
    """Create LLM tracking tables if they don't exist."""
    try:
        engine = DatabaseConnection.get_engine()
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        tables_to_create = [t for t in TABLES if t not in existing_tables]

        if not tables_to_create:
            logger.info("[MIGRATION] All LLM tracking tables already exist")
            return True

        logger.info(f"[MIGRATION] Creating LLM tracking tables: {tables_to_create}")

        target_metadata = Base.metadata
        tables_objs = [
            target_metadata.tables[t]
            for t in tables_to_create
            if t in target_metadata.tables
        ]

        if tables_objs:
            target_metadata.create_all(engine, tables=tables_objs)
            logger.info(f"[MIGRATION] Created {len(tables_objs)} LLM tracking tables")
        else:
            Base.metadata.create_all(engine)
            logger.info("[MIGRATION] Created all tables via Base.metadata.create_all")

        return True

    except Exception as e:
        logger.error(f"[MIGRATION] Failed to create LLM tracking tables: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migration()
