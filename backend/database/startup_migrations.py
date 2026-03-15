"""
Idempotent startup migration runner for Grace.

Tracks which standalone migration scripts have been applied via a
`schema_migrations` table and runs any pending ones on every startup.
Safe to call repeatedly — already-applied migrations are skipped.

Usage (from app.py lifespan, after create_tables()):
    from database.startup_migrations import run_pending_migrations
    engine = DatabaseConnection.get_engine()
    run_pending_migrations(engine)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, List, NamedTuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Migration registry
# ---------------------------------------------------------------------------

class Migration(NamedTuple):
    """A registered migration with a unique name and callable entry point."""
    name: str
    fn: Callable[[Engine], None]


def _wrap_telemetry(engine: Engine) -> None:
    from database.migrate_add_telemetry import migrate as _m
    # Original script initialises its own connection; we just call it.
    # The tables use create_all checkfirst so it's safe.
    _m()


def _wrap_librarian(engine: Engine) -> None:
    from database.migrate_add_librarian import migrate as _m
    _m()


def _wrap_genesis_keys(engine: Engine) -> None:
    from database.migrate_add_genesis_keys import run_migration as _m
    _m()


def _wrap_file_intelligence(engine: Engine) -> None:
    from database.migrate_add_file_intelligence import run_migration as _m
    _m()


def _wrap_confidence_scoring(engine: Engine) -> None:
    from database.migrate_add_confidence_scoring import migrate_add_confidence_scoring as _m
    _m()


def _wrap_memory_mesh(engine: Engine) -> None:
    from database.migrate_add_memory_mesh import migrate as _m
    _m()


def _wrap_memory_mesh_indexes(engine: Engine) -> None:
    from database.migration_memory_mesh_indexes import upgrade as _m
    _m()


def _wrap_learning_example_columns(engine: Engine) -> None:
    from database.migrations.add_learning_example_columns import ensure_learning_examples_columns
    ensure_learning_examples_columns(engine, quiet=False)


def _wrap_memory_mesh_tables(engine: Engine) -> None:
    from database.migrations.add_memory_mesh_tables import run_migration as _m
    _m()


def _wrap_document_download_fields(engine: Engine) -> None:
    from database.migrations.add_document_download_fields import run_migration as _m
    _m()


def _wrap_query_intelligence_tables(engine: Engine) -> None:
    from database.migrations.add_query_intelligence_tables import upgrade as _m
    _m()


def _wrap_scraping_tables(engine: Engine) -> None:
    from database.migrations.add_scraping_tables import migrate as _m
    _m()


# Ordered list — migrations run in this order on first deploy.
# New migrations should be appended at the end.
MIGRATIONS: List[Migration] = [
    Migration("001_add_telemetry",               _wrap_telemetry),
    Migration("002_add_librarian",               _wrap_librarian),
    Migration("003_add_genesis_keys",            _wrap_genesis_keys),
    Migration("004_add_file_intelligence",       _wrap_file_intelligence),
    Migration("005_add_confidence_scoring",      _wrap_confidence_scoring),
    Migration("006_add_memory_mesh",             _wrap_memory_mesh),
    Migration("007_memory_mesh_indexes",         _wrap_memory_mesh_indexes),
    Migration("008_learning_example_columns",    _wrap_learning_example_columns),
    Migration("009_memory_mesh_tables",          _wrap_memory_mesh_tables),
    Migration("010_document_download_fields",    _wrap_document_download_fields),
    Migration("011_query_intelligence_tables",   _wrap_query_intelligence_tables),
    Migration("012_scraping_tables",             _wrap_scraping_tables),
]


# ---------------------------------------------------------------------------
# Tracking table helpers
# ---------------------------------------------------------------------------

_CREATE_TRACKING_TABLE_SQLITE = """\
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name VARCHAR(255) PRIMARY KEY,
    applied_at     TIMESTAMP NOT NULL
)
"""

_CREATE_TRACKING_TABLE_PG = """\
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name VARCHAR(255) PRIMARY KEY,
    applied_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
)
"""


def _ensure_tracking_table(engine: Engine) -> None:
    """Create the schema_migrations table if it doesn't exist."""
    is_sqlite = engine.dialect.name == "sqlite"
    ddl = _CREATE_TRACKING_TABLE_SQLITE if is_sqlite else _CREATE_TRACKING_TABLE_PG
    with engine.connect() as conn:
        conn.execute(text(ddl))
        conn.commit()


def _get_applied_migrations(engine: Engine) -> set[str]:
    """Return set of migration names already recorded."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT migration_name FROM schema_migrations")
        ).fetchall()
    return {row[0] for row in rows}


def _record_migration(engine: Engine, name: str) -> None:
    """Record a migration as applied."""
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO schema_migrations (migration_name, applied_at) "
                "VALUES (:name, :applied_at)"
            ),
            {"name": name, "applied_at": datetime.now(timezone.utc)},
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_pending_migrations(engine: Engine) -> list[str]:
    """
    Run all pending migrations and return list of newly-applied names.

    Safe to call on every startup — already-applied migrations are skipped.
    Each migration is wrapped in try/except so a single failure does not
    prevent subsequent migrations or crash the application.
    """
    _ensure_tracking_table(engine)
    applied = _get_applied_migrations(engine)
    newly_applied: list[str] = []

    for migration in MIGRATIONS:
        if migration.name in applied:
            continue

        logger.info("[MIGRATION] Running: %s", migration.name)
        try:
            migration.fn(engine)
            _record_migration(engine, migration.name)
            newly_applied.append(migration.name)
            logger.info("[MIGRATION] ✓ Applied: %s", migration.name)
        except Exception:
            logger.exception(
                "[MIGRATION] ✗ Failed: %s (will retry next startup)",
                migration.name,
            )
            # Continue with remaining migrations — don't crash.

    if newly_applied:
        logger.info(
            "[MIGRATION] Applied %d migration(s): %s",
            len(newly_applied),
            ", ".join(newly_applied),
        )
    else:
        logger.info("[MIGRATION] All migrations already applied")

    return newly_applied
