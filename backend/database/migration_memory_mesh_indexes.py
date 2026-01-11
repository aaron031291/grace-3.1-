"""
Memory Mesh Scalability Migration - Composite Indexes

Adds composite indexes for common query patterns in Memory Mesh:
- Learning examples by type + trust
- Genesis Key lookups
- Episode temporal + trust queries
- Procedure success rate filtering

Expected Performance Improvement: 5-10x faster queries
"""

import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def upgrade(db_path: str = "backend/data/grace.db"):
    """Add composite indexes for Memory Mesh scalability"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        logger.info("[MIGRATION] Adding Memory Mesh composite indexes...")

        # Learning Examples Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_type_trust
            ON learning_examples(example_type, trust_score DESC)
        """)
        logger.info("✓ Created idx_learning_type_trust")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_genesis_key
            ON learning_examples(genesis_key_id)
        """)
        logger.info("✓ Created idx_learning_genesis_key")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_trust_desc
            ON learning_examples(trust_score DESC)
        """)
        logger.info("✓ Created idx_learning_trust_desc")

        # Episode Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_episode_genesis_trust
            ON episodes(genesis_key_id, trust_score DESC, timestamp DESC)
        """)
        logger.info("✓ Created idx_episode_genesis_trust")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_episode_timestamp_desc
            ON episodes(timestamp DESC)
        """)
        logger.info("✓ Created idx_episode_timestamp_desc")

        # Procedure Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_procedure_type_success
            ON procedures(procedure_type, success_rate DESC)
        """)
        logger.info("✓ Created idx_procedure_type_success")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_procedure_success_desc
            ON procedures(success_rate DESC)
        """)
        logger.info("✓ Created idx_procedure_success_desc")

        # Foreign Key Indexes (for joins)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_episodic_id
            ON learning_examples(episodic_episode_id)
        """)
        logger.info("✓ Created idx_learning_episodic_id")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_procedure_id
            ON learning_examples(procedure_id)
        """)
        logger.info("✓ Created idx_learning_procedure_id")

        # Document Chunk Indexes (for retrieval optimization)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_document_id
            ON document_chunks(document_id)
        """)
        logger.info("✓ Created idx_chunk_document_id")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_embedding_vector_id
            ON document_chunks(embedding_vector_id)
        """)
        logger.info("✓ Created idx_chunk_embedding_vector_id")

        conn.commit()
        logger.info("[MIGRATION] ✓ All composite indexes created successfully")

        # Analyze tables for query optimization
        cursor.execute("ANALYZE learning_examples")
        cursor.execute("ANALYZE episodes")
        cursor.execute("ANALYZE procedures")
        cursor.execute("ANALYZE document_chunks")
        conn.commit()

        logger.info("[MIGRATION] ✓ Table statistics updated")

    except sqlite3.Error as e:
        logger.error(f"[MIGRATION] Error creating indexes: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def downgrade(db_path: str = "backend/data/grace.db"):
    """Remove composite indexes"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        logger.info("[MIGRATION] Removing Memory Mesh composite indexes...")

        indexes = [
            "idx_learning_type_trust",
            "idx_learning_genesis_key",
            "idx_learning_trust_desc",
            "idx_episode_genesis_trust",
            "idx_episode_timestamp_desc",
            "idx_procedure_type_success",
            "idx_procedure_success_desc",
            "idx_learning_episodic_id",
            "idx_learning_procedure_id",
            "idx_chunk_document_id",
            "idx_chunk_embedding_vector_id"
        ]

        for idx in indexes:
            cursor.execute(f"DROP INDEX IF EXISTS {idx}")
            logger.info(f"✓ Dropped {idx}")

        conn.commit()
        logger.info("[MIGRATION] ✓ All indexes removed")

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
