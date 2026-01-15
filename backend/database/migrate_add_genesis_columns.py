"""
Database migration to add is_broken and change_origin columns to genesis_key table.

This migration adds:
- is_broken: Boolean column to track broken Genesis Keys (red flags)
- change_origin: String column to track the source of changes
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

def migrate_add_genesis_columns():
    """Add is_broken and change_origin columns to genesis_key table if they don't exist."""
    
    print("=" * 80)
    print("DATABASE MIGRATION: Add is_broken and change_origin columns to genesis_key")
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
        
        # Check if columns exist
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('genesis_key')]
        
        changes_made = False
        
        # Add is_broken column if it doesn't exist
        if 'is_broken' not in columns:
            print("[1/4] Adding is_broken column to genesis_key table...")
            with engine.connect() as connection:
                connection.execute(text("""
                    ALTER TABLE genesis_key 
                    ADD COLUMN is_broken BOOLEAN NOT NULL DEFAULT 0
                """))
                connection.commit()
            print("[OK] Column 'is_broken' added successfully")
            changes_made = True
        else:
            print("[OK] Column 'is_broken' already exists")
        
        # Add change_origin column if it doesn't exist
        if 'change_origin' not in columns:
            print("[2/4] Adding change_origin column to genesis_key table...")
            with engine.connect() as connection:
                connection.execute(text("""
                    ALTER TABLE genesis_key 
                    ADD COLUMN change_origin VARCHAR(255)
                """))
                connection.commit()
            print("[OK] Column 'change_origin' added successfully")
            changes_made = True
        else:
            print("[OK] Column 'change_origin' already exists")
        
        # Create index on is_broken if it doesn't exist
        print("[3/4] Creating index on is_broken column...")
        try:
            with engine.connect() as connection:
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_genesis_key_is_broken 
                    ON genesis_key(is_broken)
                """))
                connection.commit()
            print("[OK] Index on is_broken created successfully")
        except Exception as e:
            print(f"[WARN] Index creation failed (may already exist): {e}")
        
        # Create index on change_origin if it doesn't exist
        print("[4/4] Creating index on change_origin column...")
        try:
            with engine.connect() as connection:
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_genesis_key_change_origin 
                    ON genesis_key(change_origin)
                """))
                connection.commit()
            print("[OK] Index on change_origin created successfully")
        except Exception as e:
            print(f"[WARN] Index creation failed (may already exist): {e}")
        
        print()
        print("=" * 80)
        if changes_made:
            print("MIGRATION COMPLETE - Changes applied")
        else:
            print("MIGRATION COMPLETE - No changes needed (columns already exist)")
        print("=" * 80)
        print()
        print("Grace can now track broken Genesis Keys and change origins!")
        print()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_add_genesis_columns()
    sys.exit(0 if success else 1)
