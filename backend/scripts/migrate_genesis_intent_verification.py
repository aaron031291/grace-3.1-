"""
Database Migration: Add Intent Verification Fields to Genesis Key

Adds new columns for:
- Intent verification (change_origin, authority_scope, etc.)
- Capability binding (required_capabilities, granted_capabilities, etc.)
- State machine versioning (genesis_version, derived_from_version, etc.)
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import logging
from sqlalchemy import text
from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from database.session import initialize_session_factory, get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_genesis_key_table():
    """Add new columns to genesis_key table."""
    print("=" * 80)
    print("GENESIS KEY INTENT VERIFICATION MIGRATION")
    print("=" * 80)
    print()
    
    # Initialize database
    try:
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="backend/data/grace.db"
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())
        print("[OK] Database connected")
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return False
    
    try:
        # Check which columns already exist
        result = session.execute(text("PRAGMA table_info(genesis_key)"))
        existing_columns = {row[1] for row in result}
        
        print(f"\n[INFO] Existing columns: {len(existing_columns)}")
        
        # Columns to add
        new_columns = {
            # Intent verification
            ("change_origin", "VARCHAR(255)"),
            ("authority_scope", "VARCHAR(255)"),
            ("allowed_action_classes", "JSON"),
            ("forbidden_action_classes", "JSON"),
            ("propagation_depth", "INTEGER"),
            
            # Capability binding
            ("required_capabilities", "JSON"),
            ("granted_capabilities", "JSON"),
            ("trust_score", "REAL"),
            ("constraint_tags", "JSON"),
            
            # State machine versioning
            ("genesis_version", "INTEGER"),
            ("derived_from_version", "INTEGER"),
            ("delta_type", "VARCHAR(100)"),
            ("constraints_added", "JSON"),
            ("constraints_removed", "JSON"),
            ("signed_by", "VARCHAR(255)"),
            ("upgrade_path", "JSON"),
        }
        
        added_count = 0
        skipped_count = 0
        
        for column_name, column_type in new_columns:
            if column_name in existing_columns:
                print(f"  [SKIP] Column '{column_name}' already exists")
                skipped_count += 1
            else:
                try:
                    # Add column
                    alter_sql = f"ALTER TABLE genesis_key ADD COLUMN {column_name} {column_type}"
                    session.execute(text(alter_sql))
                    session.commit()
                    print(f"  [OK] Added column '{column_name}'")
                    added_count += 1
                except Exception as e:
                    print(f"  [ERROR] Failed to add column '{column_name}': {e}")
                    session.rollback()
        
        # Create indexes
        print("\n[INFO] Creating indexes...")
        
        indexes_to_create = [
            ("idx_genesis_version", "genesis_version"),
            ("idx_authority_scope", "authority_scope"),
            ("idx_change_origin", "change_origin"),
        ]
        
        for index_name, column_name in indexes_to_create:
            if column_name in existing_columns:
                try:
                    # Check if index exists
                    result = session.execute(text(
                        f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'"
                    ))
                    if result.fetchone():
                        print(f"  [SKIP] Index '{index_name}' already exists")
                    else:
                        create_index_sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON genesis_key({column_name})"
                        session.execute(text(create_index_sql))
                        session.commit()
                        print(f"  [OK] Created index '{index_name}'")
                except Exception as e:
                    print(f"  [WARN] Could not create index '{index_name}': {e}")
        
        print()
        print("=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print(f"  Columns added: {added_count}")
        print(f"  Columns skipped (already exist): {skipped_count}")
        print(f"  Total new columns: {len(new_columns)}")
        print()
        
        if added_count > 0:
            print("[OK] Migration completed successfully!")
        else:
            print("[OK] All columns already exist - no migration needed")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False
    finally:
        session.close()


if __name__ == "__main__":
    success = migrate_genesis_key_table()
    sys.exit(0 if success else 1)
