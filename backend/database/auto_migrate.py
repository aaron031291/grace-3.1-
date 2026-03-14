"""
database/auto_migrate.py
─────────────────────────────────────────────────────────────────────────────
Grace's Self-Healing Schema Migration System
─────────────────────────────────────────────────────────────────────────────
Runs at startup (called from app.py lifespan) and:
  1. Inspects the live PostgreSQL schema.
  2. Compares it against every SQLAlchemy model registered in
     database.base.Base.
  3. Automatically adds any missing columns, tables, and enum values.
  4. Logs each change to Grace's learning system so she can track
     drift patterns over time.

Never drops columns—only adds new ones (safe, forward-only migration).
"""
from __future__ import annotations

import logging
import time
from typing import Any

import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# ── known enum column → (pg_type_name, desired_values) ───────────────────
# Extend this mapping whenever a new enum column is added to any model.
ENUM_COLUMN_MAP: dict[str, tuple[str, list[str]]] = {
    "genesiskeytype": (
        "genesiskeytype",
        [
            # Core types
            "file_op", "code_change", "ai_response", "user_action",
            "api_request", "error", "learning", "system_event",
            "agent_action", "test_run",
            # Extended types used at runtime
            "learning_complete", "gap_identified", "audit_event",
            "mission_created", "research", "fix_applied",
            "schema_migration", "healing_event",
        ],
    ),
    "genesiskeystatus": (
        "genesiskeystatus",
        ["active", "archived", "deleted", "flagged", "pending", "resolved"],
    ),
}


# Columns that SQLAlchemy may carry as server-side types the inspector
# cannot auto-detect — map column python type → pg type string.
_PY_TO_PG: dict[str, str] = {
    "String":  "VARCHAR",
    "Text":    "TEXT",
    "Float":   "DOUBLE PRECISION",
    "Integer": "INTEGER",
    "Boolean": "BOOLEAN",
    "DateTime":"TIMESTAMP WITHOUT TIME ZONE",
    "JSON":    "JSONB",
    "LargeBinary": "BYTEA",
}


def _pg_type_for_column(col: sa.Column) -> str:
    """Best-effort PostgreSQL type from a SQLAlchemy Column."""
    type_name = type(col.type).__name__
    return _PY_TO_PG.get(type_name, "TEXT")


def _get_existing_columns(conn, table_name: str) -> set[str]:
    result = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :t"
        ),
        {"t": table_name},
    )
    return {row[0] for row in result}


def _get_existing_enum_values(conn, type_name: str) -> set[str]:
    result = conn.execute(
        text(
            "SELECT e.enumlabel FROM pg_type t "
            "JOIN pg_enum e ON t.oid = e.enumtypid "
            "WHERE t.typname = :n"
        ),
        {"n": type_name},
    )
    return {row[0] for row in result}


def _ensure_enum_values(conn, type_name: str, desired: list[str], changes: list[str]) -> None:
    existing = _get_existing_enum_values(conn, type_name)
    if not existing:
        return  # enum type doesn't exist yet — let Alembic/create_all handle it
    for val in desired:
        if val not in existing:
            conn.execute(
                text(f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS '{val}'")
            )
            msg = f"enum:{type_name} +{val}"
            changes.append(msg)
            logger.info("[AUTO-MIGRATE] Added enum value: %s -> %s", type_name, val)


def run_auto_migrate(engine: Engine) -> list[str]:
    """
    Inspect all registered SQLAlchemy models and apply any missing schema
    changes to the database.

    Returns a list of change descriptions (empty = nothing needed).
    """
    from database.base import Base  # local import to avoid circular deps

    changes: list[str] = []
    start = time.monotonic()

    try:
        with engine.begin() as conn:
            inspector = inspect(conn)
            existing_tables = set(inspector.get_table_names())

            for mapper in Base.registry.mappers:
                model = mapper.class_
                table: sa.Table = getattr(model, "__table__", None)
                if table is None:
                    continue

                table_name = table.name

                # ── Create whole table if it doesn't exist ──────────────
                if table_name not in existing_tables:
                    logger.info("[AUTO-MIGRATE] Creating missing table: %s", table_name)
                    table.create(bind=conn, checkfirst=True)
                    changes.append(f"table:+{table_name}")
                    # Re-read after create
                    existing_tables.add(table_name)
                    continue

                # ── Add missing columns ─────────────────────────────────
                existing_cols = _get_existing_columns(conn, table_name)
                for col in table.columns:
                    col_name = col.name
                    if col_name in existing_cols:
                        continue
                    # Skip columns managed by DB (e.g. generated)
                    if col.server_default and col.name in ("id", "created_at", "updated_at"):
                        continue

                    pg_type = _pg_type_for_column(col)
                    nullable_clause = "" if col.nullable else " NOT NULL DEFAULT ''"
                    try:
                        conn.execute(
                            text(
                                f"ALTER TABLE {table_name} "
                                f"ADD COLUMN IF NOT EXISTS {col_name} {pg_type}{nullable_clause}"
                            )
                        )
                        changes.append(f"col:{table_name}.{col_name}({pg_type})")
                        logger.info(
                            "[AUTO-MIGRATE] Added column %s.%s (%s)",
                            table_name, col_name, pg_type,
                        )
                    except Exception as col_err:
                        logger.warning(
                            "[AUTO-MIGRATE] Could not add %s.%s: %s",
                            table_name, col_name, col_err,
                        )

            # ── Sync all known enums ────────────────────────────────────
            for _, (type_name, desired_vals) in ENUM_COLUMN_MAP.items():
                _ensure_enum_values(conn, type_name, desired_vals, changes)

    except Exception as e:
        logger.error("[AUTO-MIGRATE] Migration failed: %s", e)
        return changes

    elapsed = (time.monotonic() - start) * 1000
    if changes:
        logger.info(
            "[AUTO-MIGRATE] Applied %d schema change(s) in %.0fms: %s",
            len(changes), elapsed, changes,
        )
        _record_learning(changes)
    else:
        logger.debug("[AUTO-MIGRATE] Schema is up to date (%.0fms)", elapsed)

    return changes


def _record_learning(changes: list[str]) -> None:
    """Feed schema drift discoveries into Grace's learning system."""
    try:
        from api._genesis_tracker import track
        track(
            key_type="system_event",
            what_description=f"Auto-migration applied {len(changes)} schema change(s)",
            why_reason="Schema drift detected between ORM models and live database",
            how_method="auto_migrate.run_auto_migrate",
            context_data={"changes": changes},
            is_error=False,
        )
    except Exception:
        pass  # learning system is optional

    # Also record in cognitive decision log if available
    try:
        from core.clarity_framework import ClarityFramework
        cf = ClarityFramework()
        cf.record_decision(
            what=f"Schema auto-migration: {len(changes)} column(s)/enum(s) added",
            why="ORM models diverged from live DB schema — forward-only migration applied",
            who={"actor": "auto_migrate", "service": "database"},
            how={"changes": changes, "method": "ALTER TABLE ADD COLUMN IF NOT EXISTS"},
            risk_score=0.1,
        )
    except Exception:
        pass
