"""
Fix Genesis Key table schema by ensuring all columns exist.
This script adds missing columns and refreshes SQLAlchemy metadata.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import inspect, text
from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType

def fix_genesis_schema():
    """Add missing columns to genesis_key table."""
    print("=" * 80)
    print("FIXING GENESIS_KEY TABLE SCHEMA")
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
        
        # Check existing columns
        inspector = inspect(engine)
        columns = {col['name'] for col in inspector.get_columns('genesis_key')}
        print(f"Existing columns: {len(columns)}")
        
        # Columns that should exist
        required_columns = {
            'change_origin': 'VARCHAR(255)',
            'authority_scope': 'VARCHAR(255)',
            'is_broken': 'BOOLEAN NOT NULL DEFAULT 0'
        }
        
        added_count = 0
        with engine.connect() as conn:
            for col_name, col_def in required_columns.items():
                if col_name not in columns:
                    print(f"Adding column: {col_name}...")
                    try:
                        conn.execute(text(f"ALTER TABLE genesis_key ADD COLUMN {col_name} {col_def}"))
                        conn.commit()
                        print(f"[OK] Added column: {col_name}")
                        added_count += 1
                    except Exception as e:
                        error_str = str(e).lower()
                        if "duplicate column" in error_str or "already exists" in error_str:
                            print(f"[OK] Column {col_name} already exists (detected via error)")
                        else:
                            print(f"[ERROR] Failed to add {col_name}: {e}")
                else:
                    print(f"[OK] Column {col_name} already exists")
            
            # Create indexes if they don't exist
            print("\n[2/2] Creating indexes...")
            indexes_to_create = [
                ("idx_genesis_key_change_origin", "change_origin"),
                ("idx_genesis_key_is_broken", "is_broken")
            ]
            
            existing_indexes = {idx['name'] for idx in inspector.get_indexes('genesis_key')}
            
            for idx_name, col_name in indexes_to_create:
                if idx_name not in existing_indexes and col_name in columns:
                    try:
                        conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON genesis_key({col_name})"))
                        conn.commit()
                        print(f"[OK] Created index: {idx_name}")
                    except Exception as e:
                        print(f"[WARN] Index creation failed (may already exist): {e}")
        
        print()
        print("=" * 80)
        if added_count > 0:
            print(f"SCHEMA FIX COMPLETE - Added {added_count} column(s)")
        else:
            print("SCHEMA FIX COMPLETE - All columns already exist")
        print("=" * 80)
        print()
        print("NOTE: You may need to restart the application for SQLAlchemy")
        print("      to pick up the schema changes.")
        print()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Schema fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_genesis_schema()
    sys.exit(0 if success else 1)
