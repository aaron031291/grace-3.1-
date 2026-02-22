"""
Migration: Add Memory Mesh Tables

Creates tables for:
- Learning examples (with trust scores)
- Learning patterns
- Episodes (episodic memory)
- Procedures (procedural memory)

Key Methods:
- `migrate()`
"""
import sqlite3
from pathlib import Path


def migrate():
    """Run migration to add memory mesh tables."""
    db_path = Path(__file__).parent.parent.parent / "data" / "grace.db"

    print(f"Migrating database at: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # ==================== Learning Examples ====================
        print("Creating learning_examples table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_examples (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- What was learned
                example_type TEXT NOT NULL,
                input_context TEXT NOT NULL,  -- JSON
                expected_output TEXT NOT NULL,  -- JSON
                actual_output TEXT,  -- JSON

                -- Trust scoring
                trust_score REAL DEFAULT 0.5 NOT NULL,
                source_reliability REAL DEFAULT 0.5 NOT NULL,
                outcome_quality REAL DEFAULT 0.5 NOT NULL,
                consistency_score REAL DEFAULT 0.5 NOT NULL,
                recency_weight REAL DEFAULT 1.0 NOT NULL,

                -- Provenance
                source TEXT NOT NULL,
                source_user_id TEXT,
                genesis_key_id TEXT,

                -- Learning metadata
                times_referenced INTEGER DEFAULT 0,
                times_validated INTEGER DEFAULT 0,
                times_invalidated INTEGER DEFAULT 0,
                last_used TIMESTAMP,

                -- Storage location
                file_path TEXT,

                -- Connections to memory mesh
                episodic_episode_id TEXT,
                procedure_id TEXT,

                -- Metadata
                metadata TEXT  -- JSON
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_learning_type
            ON learning_examples(example_type)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_learning_trust
            ON learning_examples(trust_score)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_learning_source
            ON learning_examples(source)
        ''')

        # ==================== Learning Patterns ====================
        print("Creating learning_patterns table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_patterns (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                pattern_name TEXT NOT NULL UNIQUE,
                pattern_type TEXT NOT NULL,

                -- Pattern definition
                preconditions TEXT NOT NULL,  -- JSON
                actions TEXT NOT NULL,  -- JSON
                expected_outcomes TEXT NOT NULL,  -- JSON

                -- Trust and quality
                trust_score REAL DEFAULT 0.5 NOT NULL,
                success_rate REAL DEFAULT 0.0 NOT NULL,
                sample_size INTEGER DEFAULT 0,

                -- Supporting evidence
                supporting_examples TEXT NOT NULL,  -- JSON array

                -- Usage tracking
                times_applied INTEGER DEFAULT 0,
                times_succeeded INTEGER DEFAULT 0,
                times_failed INTEGER DEFAULT 0,

                -- Connection to memory mesh
                linked_procedures TEXT  -- JSON array
            )
        ''')

        # ==================== Episodes (Episodic Memory) ====================
        print("Creating episodes table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- What happened
                problem TEXT NOT NULL,
                action TEXT NOT NULL,  -- JSON
                outcome TEXT NOT NULL,  -- JSON
                predicted_outcome TEXT,  -- JSON

                -- How accurate was prediction
                prediction_error REAL DEFAULT 0.0,

                -- Trust and quality
                trust_score REAL DEFAULT 0.5 NOT NULL,
                source TEXT NOT NULL,

                -- Provenance
                genesis_key_id TEXT,
                decision_id TEXT,

                -- Temporal
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Embedding for similarity search
                embedding TEXT,  -- JSON array

                -- Metadata
                metadata TEXT  -- JSON
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_episode_timestamp
            ON episodes(timestamp)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_episode_trust
            ON episodes(trust_score)
        ''')

        # ==================== Procedures (Procedural Memory) ====================
        print("Creating procedures table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS procedures (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Identification
                name TEXT NOT NULL UNIQUE,
                goal TEXT NOT NULL,
                procedure_type TEXT NOT NULL,

                -- How to execute
                steps TEXT NOT NULL,  -- JSON array
                preconditions TEXT NOT NULL,  -- JSON

                -- Quality metrics
                trust_score REAL DEFAULT 0.5 NOT NULL,
                success_rate REAL DEFAULT 0.0 NOT NULL,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,

                -- Evidence
                supporting_examples TEXT,  -- JSON array
                learned_from_episode_id TEXT,

                -- Embedding for similarity
                embedding TEXT,  -- JSON array

                -- Metadata
                metadata TEXT  -- JSON
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_procedure_type
            ON procedures(procedure_type)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_procedure_success
            ON procedures(success_rate)
        ''')

        conn.commit()
        print("✓ Memory mesh tables created successfully")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
