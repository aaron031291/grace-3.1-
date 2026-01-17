"""
Migration script to add metadata columns to documents table.
Run this script to migrate the database schema.
"""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "data" / "grace.db"


def column_exists(connection, table_name, column_name):
    """Check if a column exists in a table."""
    cursor = connection.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col[1] == column_name for col in columns)


def add_column(connection, table_name, column_name, column_def):
    """Add a column to a table if it doesn't exist."""
    if column_exists(connection, table_name, column_name):
        logger.info(f"Column {column_name} already exists in {table_name}")
        return True
    
    try:
        cursor = connection.cursor()
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
        connection.commit()
        logger.info(f"Added column {column_name} to {table_name}")
        return True
    except sqlite3.OperationalError as e:
        logger.error(f"Error adding column {column_name}: {e}")
        return False


def migrate():
    """Apply all pending migrations."""
    if not DB_PATH.exists():
        logger.error(f"Database file not found at {DB_PATH}")
        return False
    
    try:
        connection = sqlite3.connect(str(DB_PATH))
        logger.info(f"Connected to database at {DB_PATH}")
        
        # Add missing columns to documents table
        columns_to_add = {
            "upload_method": "VARCHAR(50) NOT NULL DEFAULT 'ui-upload'",
            "trust_score": "REAL NOT NULL DEFAULT 0.0",
            "description": "TEXT",
            "tags": "TEXT",
            "document_metadata": "TEXT",
        }
        
        success = True
        for column_name, column_def in columns_to_add.items():
            if not add_column(connection, "documents", column_name, column_def):
                success = False
        
        # Create indexes if they don't exist
        cursor = connection.cursor()
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_upload_method ON documents(upload_method)",
            "CREATE INDEX IF NOT EXISTS idx_trust_score ON documents(trust_score)",
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                connection.commit()
                logger.info(f"Created index: {index_sql.split('idx_')[1].split()[0]}")
            except sqlite3.OperationalError as e:
                logger.warning(f"Index might already exist: {e}")
        
        connection.close()
        logger.info("Migration completed successfully!")
        return success
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


if __name__ == "__main__":
    if migrate():
        logger.info("✅ Migration successful")
    else:
        logger.error("❌ Migration failed")
