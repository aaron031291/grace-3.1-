"""
PostgreSQL Adapter — production-grade database layer.

Replaces SQLite for scale. Supports:
  - Concurrent writes (no writer lock)
  - Connection pooling (pgbouncer-compatible)
  - Horizontal read replicas
  - Full-text search
  - JSON columns that actually work

Falls back to SQLite if PostgreSQL isn't configured.

Usage in .env:
  DATABASE_TYPE=postgresql
  DATABASE_HOST=localhost
  DATABASE_PORT=5432
  DATABASE_USER=grace
  DATABASE_PASSWORD=your_password
  DATABASE_NAME=grace
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_optimal_engine_config() -> dict:
    """
    Returns the optimal SQLAlchemy engine configuration
    based on the database type.
    """
    db_type = os.getenv("DATABASE_TYPE", "sqlite").lower()

    if db_type == "postgresql":
        return {
            "pool_class": "QueuePool",
            "pool_size": 20,
            "max_overflow": 30,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "pool_timeout": 30,
            "echo": os.getenv("DATABASE_ECHO", "false").lower() == "true",
            "isolation_level": "READ COMMITTED",
            "connect_args": {
                "options": "-c statement_timeout=30000",
            },
        }
    else:
        # SQLite optimized config (current)
        return {
            "pool_class": "StaticPool",
            "connect_args": {
                "check_same_thread": False,
                "timeout": 60,
            },
            "echo": os.getenv("DATABASE_ECHO", "false").lower() == "true",
            "pragmas": {
                "journal_mode": "WAL",
                "busy_timeout": 30000,
                "foreign_keys": "ON",
                "synchronous": "NORMAL",
            },
        }


def get_connection_string() -> str:
    """Build the connection string based on DATABASE_TYPE."""
    db_type = os.getenv("DATABASE_TYPE", "sqlite").lower()

    if db_type == "postgresql":
        host = os.getenv("DATABASE_HOST", "localhost")
        port = os.getenv("DATABASE_PORT", "5432")
        user = os.getenv("DATABASE_USER", "grace")
        password = os.getenv("DATABASE_PASSWORD", "")
        name = os.getenv("DATABASE_NAME", "grace")
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"

    elif db_type == "mysql":
        host = os.getenv("DATABASE_HOST", "localhost")
        port = os.getenv("DATABASE_PORT", "3306")
        user = os.getenv("DATABASE_USER", "grace")
        password = os.getenv("DATABASE_PASSWORD", "")
        name = os.getenv("DATABASE_NAME", "grace")
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"

    else:
        path = os.getenv("DATABASE_PATH", "data/grace.db")
        return f"sqlite:///{path}"


def is_postgres() -> bool:
    return os.getenv("DATABASE_TYPE", "sqlite").lower() == "postgresql"


def migrate_sqlite_to_postgres(sqlite_path: str = "data/grace.db") -> dict:
    """
    Migration helper — export SQLite data to PostgreSQL.
    Run once when switching databases.
    """
    if not is_postgres():
        return {"error": "DATABASE_TYPE is not postgresql"}

    try:
        import sqlite3
        from sqlalchemy import create_engine, text

        # Read from SQLite
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row

        # Connect to PostgreSQL
        pg_url = get_connection_string()
        pg_engine = create_engine(pg_url)

        tables = [r[0] for r in sqlite_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

        migrated = {}
        for table in tables:
            try:
                rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
                if rows:
                    cols = rows[0].keys()
                    with pg_engine.connect() as conn:
                        for row in rows:
                            vals = {c: row[c] for c in cols}
                            placeholders = ", ".join(f":{c}" for c in cols)
                            col_names = ", ".join(cols)
                            conn.execute(text(
                                f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                            ), vals)
                        conn.commit()
                migrated[table] = len(rows)
            except Exception as e:
                migrated[table] = f"error: {e}"

        sqlite_conn.close()
        return {"migrated": migrated, "tables": len(tables)}

    except Exception as e:
        return {"error": str(e)}
