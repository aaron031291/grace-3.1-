"""
Database migration: Add query intelligence tables.

Creates tables for tracking multi-tier query handling:
- query_handling_log: Tracks tier usage and confidence scores
- knowledge_gaps: Stores identified knowledge gaps
- context_submissions: Records user-provided context
"""

from database.connection import DatabaseConnection
from database.base import Base
from models.query_intelligence_models import QueryHandlingLog, KnowledgeGap, ContextSubmission


def upgrade():
    """Create query intelligence tables using ORM (works with both SQLite and PostgreSQL)."""
    engine = DatabaseConnection.get_engine()

    Base.metadata.create_all(
        engine,
        tables=[
            QueryHandlingLog.__table__,
            KnowledgeGap.__table__,
            ContextSubmission.__table__,
        ]
    )

    print("[OK] Query intelligence tables created successfully")


def downgrade():
    """Drop query intelligence tables."""
    engine = DatabaseConnection.get_engine()

    ContextSubmission.__table__.drop(engine, checkfirst=True)
    KnowledgeGap.__table__.drop(engine, checkfirst=True)
    QueryHandlingLog.__table__.drop(engine, checkfirst=True)

    print("[OK] Query intelligence tables dropped successfully")


if __name__ == "__main__":
    print("Running query intelligence tables migration...")
    upgrade()
    print("Migration complete!")
