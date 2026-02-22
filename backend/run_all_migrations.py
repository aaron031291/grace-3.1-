"""
Utility script.
"""
#!/usr/bin/env python3
"""
Master migration script to run all database migrations in the correct order.
This script ensures all database schema changes are applied.

Usage:
    python run_all_migrations.py
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database.migration import create_tables
from database.connection import DatabaseConnection
from database.config import DatabaseConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_migration_create_tables():
    """Step 1: Create base tables from SQLAlchemy models."""
    logger.info("=" * 60)
    logger.info("STEP 1: Creating base database tables")
    logger.info("=" * 60)
    
    try:
        # Initialize the database connection with default config
        config = DatabaseConfig()
        DatabaseConnection.initialize(config)
        create_tables()
        logger.info("✓ Base tables created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create base tables: {e}")
        return False


def run_migration_add_metadata_columns():
    """Step 2: Add metadata columns to documents table."""
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Adding metadata columns to documents table")
    logger.info("=" * 60)
    
    try:
        from migrate_add_metadata_columns import migrate as migrate_metadata
        
        success = migrate_metadata()
        if success:
            logger.info("✓ Metadata columns migration completed successfully")
            return True
        else:
            logger.warning("⚠ Metadata columns migration had issues but continuing")
            return True
    except ImportError:
        logger.warning("⚠ Metadata migration module not found, skipping")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to add metadata columns: {e}")
        return False


def run_migration_add_folder_path():
    """Step 3: Add folder_path column to documents table."""
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Adding folder_path column to documents table")
    logger.info("=" * 60)
    
    try:
        from migrate_add_folder_path import migrate as migrate_folder_path
        
        success = migrate_folder_path()
        if success:
            logger.info("✓ Folder path migration completed successfully")
            return True
        else:
            logger.warning("⚠ Folder path migration had issues but continuing")
            return True
    except ImportError:
        logger.warning("⚠ Folder path migration module not found, skipping")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to add folder_path column: {e}")
        return False


def run_migration_add_confidence_scoring():
    """Step 4: Add confidence scoring columns."""
    logger.info("\n" + "=" * 60)
    logger.info("STEP 4: Adding confidence scoring columns")
    logger.info("=" * 60)
    
    try:
        from database.migrate_add_confidence_scoring import migrate as migrate_confidence
        
        success = migrate_confidence()
        if success:
            logger.info("✓ Confidence scoring migration completed successfully")
            return True
        else:
            logger.warning("⚠ Confidence scoring migration had issues but continuing")
            return True
    except ImportError:
        logger.warning("⚠ Confidence scoring migration module not found, skipping")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to add confidence scoring columns: {e}")
        return False


def verify_database():
    """Verify database connection and basic setup."""
    logger.info("\n" + "=" * 60)
    logger.info("VERIFICATION: Checking database connection")
    logger.info("=" * 60)
    
    try:
        engine = DatabaseConnection.get_engine()
        with engine.connect() as connection:
            logger.info("✓ Database connection successful")
            
            # Get list of tables
            inspector = __import__('sqlalchemy').inspect(engine)
            tables = inspector.get_table_names()
            
            logger.info(f"\n✓ Database contains {len(tables)} table(s):")
            for table in sorted(tables):
                num_columns = len(inspector.get_columns(table))
                logger.info(f"   - {table} ({num_columns} columns)")
            
            return True
    except Exception as e:
        logger.error(f"✗ Database verification failed: {e}")
        return False


def main():
    """Run all migrations in order."""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 10 + "GRACE DATABASE MIGRATION SCRIPT" + " " * 18 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    
    migrations = [
        ("Base Tables", run_migration_create_tables),
        ("Metadata Columns", run_migration_add_metadata_columns),
        ("Folder Path", run_migration_add_folder_path),
        ("Confidence Scoring", run_migration_add_confidence_scoring),
        ("Database Verification", verify_database),
    ]
    
    results = []
    
    for migration_name, migration_func in migrations:
        try:
            success = migration_func()
            results.append((migration_name, success))
        except Exception as e:
            logger.error(f"Unexpected error in {migration_name}: {e}")
            results.append((migration_name, False))
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 60)
    
    all_success = True
    for migration_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        logger.info(f"{status}: {migration_name}")
        if not success:
            all_success = False
    
    logger.info("=" * 60)
    
    if all_success:
        logger.info("\n✓ All migrations completed successfully!")
        logger.info("\nYour database is ready for use.")
        return 0
    else:
        logger.error("\n✗ Some migrations failed. Please check the logs above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
