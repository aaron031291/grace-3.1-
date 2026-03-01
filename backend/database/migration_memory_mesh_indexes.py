"""
Memory Mesh Scalability Migration - Composite Indexes

Adds composite indexes for common query patterns in Memory Mesh:
- Learning examples by type + trust
- Genesis Key lookups
- Episode temporal + trust queries
- Procedure success rate filtering
- Document lookups

Expected Performance Improvement: 5-10x faster queries
"""

import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def _validate_identifier(name: str) -> bool:
    """Validate that a name is a safe SQL identifier (alphanumeric + underscore only)."""
    import re
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))


def safe_create_index(cursor, index_name: str, table: str, columns: str):
    """Safely create index, ignoring if table doesn't exist.

    Note: SQL identifiers cannot be parameterized, so we validate them instead.
    All values must match [a-zA-Z_][a-zA-Z0-9_]* pattern.
    """
    # Validate identifiers to prevent SQL injection
    if not _validate_identifier(index_name):
        logger.error(f"Invalid index name: {index_name}")
        return False
    if not _validate_identifier(table):
        logger.error(f"Invalid table name: {table}")
        return False
    # Columns can include DESC, spaces, and commas, so validate each part
    for col_part in columns.replace(',', ' ').replace('DESC', '').replace('ASC', '').split():
        if col_part and not _validate_identifier(col_part):
            logger.error(f"Invalid column name: {col_part}")
            return False

    try:
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON {table}({columns})
        """)
        logger.info(f"Created {index_name}")
        return True
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            logger.warning(f"Skipping {index_name} - table {table} doesn't exist")
        else:
            logger.error(f"Error creating {index_name}: {e}")
        return False


def upgrade(db_path: str = "backend/data/grace.db"):
    """Add composite indexes for Memory Mesh scalability"""

    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    cursor = conn.cursor()
    created_count = 0

    try:
        logger.info("[MIGRATION] Adding Memory Mesh composite indexes...")

        # Learning Examples Indexes
        if safe_create_index(cursor, "idx_learning_type_trust", "learning_examples", "example_type, trust_score DESC"):
            created_count += 1
        if safe_create_index(cursor, "idx_learning_genesis_key", "learning_examples", "genesis_key_id"):
            created_count += 1
        if safe_create_index(cursor, "idx_learning_trust_desc", "learning_examples", "trust_score DESC"):
            created_count += 1
        if safe_create_index(cursor, "idx_learning_episodic_id", "learning_examples", "episodic_episode_id"):
            created_count += 1
        if safe_create_index(cursor, "idx_learning_procedure_id", "learning_examples", "procedure_id"):
            created_count += 1

        # Episode Indexes
        if safe_create_index(cursor, "idx_episode_genesis_trust", "episodes", "genesis_key_id, trust_score DESC, timestamp DESC"):
            created_count += 1
        if safe_create_index(cursor, "idx_episode_timestamp_desc", "episodes", "timestamp DESC"):
            created_count += 1
        if safe_create_index(cursor, "idx_episode_trust_score", "episodes", "trust_score DESC"):
            created_count += 1

        # Procedure Indexes
        if safe_create_index(cursor, "idx_procedure_type_success", "procedures", "procedure_type, success_rate DESC"):
            created_count += 1
        if safe_create_index(cursor, "idx_procedure_success_desc", "procedures", "success_rate DESC"):
            created_count += 1

        # Document Chunk Indexes
        if safe_create_index(cursor, "idx_chunk_document_id", "document_chunks", "document_id"):
            created_count += 1
        if safe_create_index(cursor, "idx_chunk_embedding_vector_id", "document_chunks", "embedding_vector_id"):
            created_count += 1

        # Document Indexes
        if safe_create_index(cursor, "idx_document_content_hash", "documents", "content_hash"):
            created_count += 1
        if safe_create_index(cursor, "idx_document_file_path", "documents", "file_path"):
            created_count += 1
        if safe_create_index(cursor, "idx_document_status", "documents", "status"):
            created_count += 1
        if safe_create_index(cursor, "idx_document_created_at", "documents", "created_at DESC"):
            created_count += 1

        # Genesis Keys Indexes
        if safe_create_index(cursor, "idx_genesis_key_type_status", "genesis_keys", "key_type, status"):
            created_count += 1
        if safe_create_index(cursor, "idx_genesis_key_user_id", "genesis_keys", "user_id"):
            created_count += 1
        if safe_create_index(cursor, "idx_genesis_key_timestamp", "genesis_keys", "when_timestamp DESC"):
            created_count += 1

        conn.commit()
        logger.info(f"[MIGRATION] Created {created_count} indexes successfully")

        # Analyze tables for query optimization
        tables_to_analyze = [
            "learning_examples", "episodes", "procedures",
            "document_chunks", "documents", "genesis_keys"
        ]
        for table in tables_to_analyze:
            if not _validate_identifier(table):
                continue
            try:
                cursor.execute(f"ANALYZE {table}")
            except sqlite3.OperationalError:
                pass  # Table doesn't exist

        conn.commit()
        logger.info("[MIGRATION] Table statistics updated")

    except sqlite3.Error as e:
        logger.error(f"[MIGRATION] Error creating indexes: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def downgrade(db_path: str = "backend/data/grace.db"):
    """Remove composite indexes"""

    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    cursor = conn.cursor()

    try:
        logger.info("[MIGRATION] Removing Memory Mesh composite indexes...")

        indexes = [
            "idx_learning_type_trust",
            "idx_learning_genesis_key",
            "idx_learning_trust_desc",
            "idx_learning_episodic_id",
            "idx_learning_procedure_id",
            "idx_episode_genesis_trust",
            "idx_episode_timestamp_desc",
            "idx_episode_trust_score",
            "idx_procedure_type_success",
            "idx_procedure_success_desc",
            "idx_chunk_document_id",
            "idx_chunk_embedding_vector_id",
            "idx_document_content_hash",
            "idx_document_file_path",
            "idx_document_status",
            "idx_document_created_at",
            "idx_genesis_key_type_status",
            "idx_genesis_key_user_id",
            "idx_genesis_key_timestamp"
        ]

        for idx in indexes:
            if not _validate_identifier(idx):
                continue
            try:
                cursor.execute(f"DROP INDEX IF EXISTS {idx}")
                logger.info(f"Dropped {idx}")
            except sqlite3.OperationalError:
                pass

        conn.commit()
        logger.info("[MIGRATION] All indexes removed")

    except sqlite3.Error as e:
        logger.error(f"[MIGRATION] Error removing indexes: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Run upgrade
    print("Running Memory Mesh index migration...")
    upgrade()
    print("Migration complete!")
