"""
Database migration to add is_broken column to genesis_key table.

This column is needed for Grace to track broken Genesis Keys (red flags).
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text, inspect
from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType

def migrate_add_is_broken_column():
    """Add is_broken column to genesis_key table if it doesn't exist."""
    
    print("=" * 80)
    print("DATABASE MIGRATION: Add is_broken column to genesis_key")
    print("=" * 80)
    print()
    
    try:
        # Initialize database connection
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="data/grace.db"
        )
        DatabaseConnection.initialize(db_config)
        engine = DatabaseConnection.get_engine()
        
        # Check if column exists
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('genesis_key')]
        
        if 'is_broken' in columns:
            print("[OK] Column 'is_broken' already exists in genesis_key table")
            return True
        
        print("[1/2] Adding is_broken column to genesis_key table...")
        
        # Add the column
        with engine.connect() as connection:
            connection.execute(text("""
                ALTER TABLE genesis_key 
                ADD COLUMN is_broken BOOLEAN NOT NULL DEFAULT 0
            """))
            connection.commit()
        
        print("[OK] Column 'is_broken' added successfully")
        
        # Create index for faster queries
        print("[2/2] Creating index on is_broken column...")
        try:
            with engine.connect() as connection:
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_genesis_key_is_broken 
                    ON genesis_key(is_broken)
                """))
                connection.commit()
            print("[OK] Index created successfully")
        except Exception as e:
            print(f"[WARN] Index creation failed (may already exist): {e}")
        
        print()
        print("=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)
        print()
        print("Grace can now track broken Genesis Keys!")
        print()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_add_is_broken_column()
    sys.exit(0 if success else 1)
