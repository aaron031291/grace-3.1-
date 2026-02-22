"""
Database migration to add Genesis Key tables.

Run this script to create the Genesis Key tracking system tables.

Key Methods:
- `run_migration()`
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database.config import DatabaseConfig
from models.genesis_key_models import (
    GenesisKey, FixSuggestion, GenesisKeyArchive, UserProfile
)
from database.base import BaseModel

def run_migration():
    """Create Genesis Key tables."""
    config = DatabaseConfig.from_env()
    database_url = config.get_connection_string()
    engine = create_engine(database_url)

    print("Creating Genesis Key tables...")

    # Create all tables defined in the genesis_key_models
    BaseModel.metadata.create_all(engine, tables=[
        GenesisKey.__table__,
        FixSuggestion.__table__,
        GenesisKeyArchive.__table__,
        UserProfile.__table__
    ])

    print("✓ Genesis Key tables created successfully")
    print("  - genesis_key")
    print("  - fix_suggestion")
    print("  - genesis_key_archive")
    print("  - user_profile")

if __name__ == "__main__":
    run_migration()
