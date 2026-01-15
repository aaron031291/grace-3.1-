"""
Refresh SQLAlchemy metadata to pick up schema changes.
This forces SQLAlchemy to re-read the database schema.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import MetaData, inspect
from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from models.genesis_key_models import GenesisKey

def refresh_metadata():
    """Force SQLAlchemy to refresh table metadata."""
    print("=" * 80)
    print("REFRESHING SQLALCHEMY METADATA")
    print("=" * 80)
    print()
    
    try:
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="data/grace.db"
        )
        DatabaseConnection.initialize(db_config)
        engine = DatabaseConnection.get_engine()
        
        # Force metadata refresh by reflecting the table
        print("[1/2] Reflecting database schema...")
        metadata = MetaData()
        metadata.reflect(bind=engine, only=['genesis_key'])
        
        # Update the GenesisKey table with reflected metadata
        print("[2/2] Updating model metadata...")
        GenesisKey.__table__ = metadata.tables['genesis_key']
        
        print()
        print("[OK] Metadata refreshed successfully")
        print()
        print("Columns in reflected table:")
        for col in GenesisKey.__table__.columns:
            print(f"  - {col.name}")
        print()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Metadata refresh failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = refresh_metadata()
    sys.exit(0 if success else 1)
