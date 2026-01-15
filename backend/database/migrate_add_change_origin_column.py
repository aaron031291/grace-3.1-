"""
Database Migration: Add change_origin column to genesis_key table

This migration adds the change_origin column if it doesn't already exist.
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def migrate_add_change_origin_column(db_path: str = "data/grace.db"):
    """
    Add change_origin column to genesis_key table if it doesn't exist.
    
    Args:
        db_path: Path to the SQLite database file
    """
    db_file = Path(db_path)
    
    if not db_file.exists():
        logger.warning(f"Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(genesis_key)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'change_origin' in columns:
            logger.info("Column 'change_origin' already exists in genesis_key table")
            conn.close()
            return True
        
        # Add the column
        cursor.execute("""
            ALTER TABLE genesis_key 
            ADD COLUMN change_origin TEXT
        """)
        
        # Create index for better query performance
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_genesis_key_change_origin 
                ON genesis_key(change_origin)
            """)
        except sqlite3.OperationalError:
            # Index might already exist
            pass
        
        conn.commit()
        conn.close()
        
        logger.info("Successfully added 'change_origin' column to genesis_key table")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add change_origin column: {e}")
        return False

if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/grace.db"
    success = migrate_add_change_origin_column(db_path)
    sys.exit(0 if success else 1)
