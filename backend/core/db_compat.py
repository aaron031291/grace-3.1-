"""
Database Compatibility Layer — dialect-agnostic types and utilities.

Ensures ORM models and queries work identically on SQLite and PostgreSQL.
Import these types instead of raw sqlalchemy types when you need
JSON columns, array columns, or dialect-specific behavior.
"""

import json
import os
import logging
from typing import Any

from sqlalchemy import TypeDecorator, Text, types
from sqlalchemy.dialects import postgresql

logger = logging.getLogger(__name__)


def is_postgres() -> bool:
    return os.getenv("DATABASE_TYPE", "sqlite").lower() == "postgresql"


class JSONColumn(TypeDecorator):
    """
    Dialect-agnostic JSON column.

    - PostgreSQL: uses native JSONB (indexed, queryable)
    - SQLite:     stores as TEXT with automatic JSON serialization

    Usage in models:
        from core.db_compat import JSONColumn
        metadata_col = Column(JSONColumn, default={})
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.JSONB)
        return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value, ensure_ascii=False, default=str)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value


class ArrayColumn(TypeDecorator):
    """
    Dialect-agnostic ARRAY column.

    - PostgreSQL: uses native ARRAY type
    - SQLite:     stores as JSON TEXT
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.ARRAY(types.String))
        return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value, ensure_ascii=False, default=str)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return []
        return value if isinstance(value, list) else []


def get_table_stats(engine) -> dict:
    """
    Get row counts for all tables — works on both SQLite and PostgreSQL.
    Returns dict of {table_name: row_count}.
    """
    from sqlalchemy import text, inspect

    stats = {}
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        with engine.connect() as conn:
            for name in table_names:
                try:
                    count = conn.execute(
                        text(f'SELECT COUNT(*) FROM "{name}"')
                    ).scalar()
                    if count and count > 0:
                        stats[name] = count
                except Exception:
                    stats[name] = -1
    except Exception as e:
        logger.debug(f"get_table_stats error: {e}")
    return stats


def get_db_size_mb(engine) -> float:
    """Get database size in MB — works on both SQLite and PostgreSQL."""
    from sqlalchemy import text

    try:
        dialect = engine.dialect.name
        with engine.connect() as conn:
            if dialect == "postgresql":
                result = conn.execute(text(
                    "SELECT pg_database_size(current_database())"
                )).scalar()
                return round(result / 1048576, 2)
            elif dialect == "sqlite":
                result = conn.execute(text(
                    "SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()"
                )).scalar()
                return round(result / 1048576, 2) if result else 0.0
    except Exception as e:
        logger.debug(f"get_db_size_mb error: {e}")
    return 0.0
