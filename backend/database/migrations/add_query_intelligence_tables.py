"""
Database migration: Add query intelligence tables.

Creates tables for tracking multi-tier query handling:
- query_handling_log: Tracks tier usage and confidence scores
- knowledge_gaps: Stores identified knowledge gaps
- context_submissions: Records user-provided context

Uses SQLAlchemy ORM create_all() for cross-database compatibility
(SQLite, PostgreSQL, MySQL).
"""

from sqlalchemy import inspect
from database.connection import DatabaseConnection
from database.base import Base
from models.query_intelligence_models import QueryHandlingLog, KnowledgeGap, ContextSubmission


def upgrade():
    """Create query intelligence tables using ORM models (DB-agnostic)."""
    engine = DatabaseConnection.get_engine()
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())

    tables_to_create = []
    for model in [QueryHandlingLog, KnowledgeGap, ContextSubmission]:
        if model.__tablename__ not in existing:
            tables_to_create.append(model.__table__)

    if tables_to_create:
        Base.metadata.create_all(engine, tables=tables_to_create)
        for t in tables_to_create:
            print(f"[OK] Created table: {t.name}")
    else:
        print("[OK] All query intelligence tables already exist")

    print("[OK] Query intelligence tables migration completed successfully")


def downgrade():
    """Drop query intelligence tables."""
    engine = DatabaseConnection.get_engine()

    for model in reversed([QueryHandlingLog, KnowledgeGap, ContextSubmission]):
        try:
            model.__table__.drop(engine, checkfirst=True)
            print(f"[OK] Dropped table: {model.__tablename__}")
        except Exception as e:
            print(f"[WARN] Could not drop {model.__tablename__}: {e}")

    print("[OK] Query intelligence tables dropped successfully")


if __name__ == "__main__":
    print("Running query intelligence tables migration...")
    upgrade()
    print("Migration complete!")
