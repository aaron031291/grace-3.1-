"""
Migration: Add missing columns to learning_examples for cognitive/learning_memory schema.

The cognitive.learning_memory.LearningExample model expects columns that may be
missing when the table was created from models.database_models (different schema).
This migration adds outcome_quality, consistency_score, recency_weight, and
other columns required by memory_mesh_learner and related cognitive code.

Error fixed: column learning_examples.outcome_quality does not exist
"""
import sys
from pathlib import Path

# Ensure backend is on path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from database.connection import DatabaseConnection
from database.config import DatabaseConfig


# Columns required by cognitive/learning_memory.LearningExample that may be missing
COLUMNS_TO_ADD = [
    ("outcome_quality", "REAL DEFAULT 0.5 NOT NULL"),
    ("consistency_score", "REAL DEFAULT 0.5 NOT NULL"),
    ("recency_weight", "REAL DEFAULT 1.0 NOT NULL"),
    ("source_user_id", "VARCHAR"),
    ("genesis_key_id", "VARCHAR"),
    ("times_referenced", "INTEGER DEFAULT 0"),
    ("times_validated", "INTEGER DEFAULT 0"),
    ("times_invalidated", "INTEGER DEFAULT 0"),
    ("last_used", "TIMESTAMP"),
    ("episodic_episode_id", "VARCHAR"),
    ("procedure_id", "VARCHAR"),
    ("example_metadata", "TEXT"),
]


def get_existing_columns(conn, table_name: str, is_postgres: bool) -> set:
    """Return set of existing column names for the table."""
    if is_postgres:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = :tbl
            """),
            {"tbl": table_name},
        )
    else:
        result = conn.execute(
            text(f"PRAGMA table_info({table_name})"),
        )
    if is_postgres:
        return {row[0] for row in result}
    # SQLite PRAGMA returns (cid, name, type, notnull, dflt_value, pk)
    return {row[1] for row in result}


def ensure_learning_examples_columns(engine, quiet: bool = False):
    """
    Add any missing columns to learning_examples. Call at startup so the system
    auto-aligns schema (e.g. after create_tables). Returns number of columns added.
    """
    from sqlalchemy.engine import Engine
    is_postgres = engine.dialect.name == "postgresql"
    added_count = 0
    with engine.connect() as conn:
        if is_postgres:
            r = conn.execute(
                text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'learning_examples')"),
            )
            exists = r.scalar()
        else:
            r = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='learning_examples'"))
            exists = r.fetchone() is not None
        if not exists:
            if not quiet:
                print("[SKIP] learning_examples table does not exist.")
            return 0
        existing = get_existing_columns(conn, "learning_examples", is_postgres)
        for col_name, col_def in COLUMNS_TO_ADD:
            if col_name in existing:
                continue
            try:
                if is_postgres:
                    sql = f'ALTER TABLE learning_examples ADD COLUMN IF NOT EXISTS "{col_name}" {col_def}'
                else:
                    sql = f'ALTER TABLE learning_examples ADD COLUMN "{col_name}" {col_def}'
                conn.execute(text(sql))
                conn.commit()
                added_count += 1
                if not quiet:
                    print(f"  + {col_name}")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    pass
                elif not quiet:
                    print(f"  ! {col_name}: {e}")
    return added_count


def run_migration():
    """Add missing columns to learning_examples (standalone script)."""
    print("=" * 60)
    print("Migration: Add learning_examples columns")
    print("=" * 60)
    config = DatabaseConfig.from_env()
    print(f"\nDatabase type: {config.db_type}")
    DatabaseConnection.initialize(config)
    engine = DatabaseConnection.get_engine()
    with engine.connect() as conn:
        is_postgres = engine.dialect.name == "postgresql"
        if is_postgres:
            r = conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'learning_examples')"))
            exists = r.scalar()
        else:
            r = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='learning_examples'"))
            exists = r.fetchone() is not None
        if not exists:
            print("\n[SKIP] learning_examples table does not exist. Run create_all first.")
            print("=" * 60)
            return True
        existing = get_existing_columns(conn, "learning_examples", is_postgres)
        print(f"\nExisting columns: {sorted(existing)}")
    added_count = ensure_learning_examples_columns(engine, quiet=False)
    if added_count:
        print(f"\n[OK] Added {added_count} column(s)")
    else:
        print("\n[OK] No columns to add (all already exist)")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        run_migration()
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
