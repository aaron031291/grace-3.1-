#!/usr/bin/env python3
"""
Track datetime fixes with Genesis Keys.

This script creates Genesis Keys for all the datetime.utcnow() fixes
that were applied to the codebase.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from genesis.symbiotic_version_control import SymbioticVersionControl
from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from database.base import BaseModel
from models.genesis_key_models import GenesisKey, FixSuggestion, GenesisKeyArchive, UserProfile
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Files that were modified for datetime fixes
FIXED_FILES = [
    "backend/api/knowledge_base_cicd.py",
    "backend/file_manager/knowledge_base_manager.py",
    "backend/layer1/components/knowledge_base_connector.py",
    "backend/api/knowledge_base_api.py",
    "backend/migrate_add_folder_path.py",
]

def track_datetime_fixes():
    """Track all datetime fixes with Genesis Keys."""
    try:
        # Initialize database connection
        logger.info("Initializing database connection...")
        db_config = DatabaseConfig.from_env()
        DatabaseConnection.initialize(db_config)
        logger.info("Database connection initialized.")
        
        # Ensure Genesis Key tables exist
        logger.info("Ensuring Genesis Key tables exist...")
        engine = DatabaseConnection.get_engine()
        BaseModel.metadata.create_all(engine, tables=[
            GenesisKey.__table__,
            FixSuggestion.__table__,
            GenesisKeyArchive.__table__,
            UserProfile.__table__
        ])
        logger.info("Genesis Key tables ready.")
        
        # Initialize symbiotic version control
        symbiotic = SymbioticVersionControl()
        
        tracked_count = 0
        errors = []
        
        for file_path in FIXED_FILES:
            try:
                # Check if file exists
                full_path = Path(backend_dir.parent / file_path)
                if not full_path.exists():
                    logger.warning(f"File not found: {file_path}")
                    continue
                
                # Track the change
                result = symbiotic.track_file_change(
                    file_path=file_path,
                    user_id="system:datetime_fix_script",
                    change_description=(
                        "Fixed datetime.utcnow() deprecation warnings by replacing "
                        "with datetime.now(UTC). Updated imports to include UTC. "
                        "Part of systematic warning reduction effort."
                    ),
                    operation_type="modify"
                )
                
                tracked_count += 1
                logger.info(
                    f"✓ Tracked: {file_path} - "
                    f"Genesis Key: {result.get('operation_genesis_key', 'N/A')}"
                )
                
            except Exception as e:
                error_msg = f"Error tracking {file_path}: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append({"file": file_path, "error": str(e)})
        
        # Summary
        print("\n" + "="*60)
        print("DATETIME FIXES - GENESIS KEY TRACKING SUMMARY")
        print("="*60)
        print(f"Files tracked: {tracked_count}/{len(FIXED_FILES)}")
        
        if errors:
            print(f"\nErrors ({len(errors)}):")
            for err in errors:
                print(f"  - {err['file']}: {err['error']}")
        else:
            print("\n✓ All files successfully tracked with Genesis Keys!")
        
        return tracked_count == len(FIXED_FILES)
        
    except Exception as e:
        logger.error(f"Failed to track datetime fixes: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = track_datetime_fixes()
    sys.exit(0 if success else 1)
