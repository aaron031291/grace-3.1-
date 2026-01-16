"""
Update scraping tables to add filtering tracking.
Run this with: ./venv/bin/python update_scraping_tables.py
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from sqlalchemy import text


def update_tables():
    """Add new columns to scraping tables."""
    try:
        print("Updating scraping tables...")
        
        # Initialize database connection
        config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="./data/grace.db"
        )
        DatabaseConnection.initialize(config)
        
        engine = DatabaseConnection.get_engine()
        
        # Add columns using raw SQL (SQLite doesn't support ALTER TABLE ADD COLUMN IF NOT EXISTS)
        with engine.connect() as conn:
            # Add pages_filtered to scraping_jobs
            try:
                conn.execute(text("ALTER TABLE scraping_jobs ADD COLUMN pages_filtered INTEGER DEFAULT 0"))
                conn.commit()
                print("✓ Added pages_filtered column to scraping_jobs")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("  pages_filtered column already exists")
                else:
                    raise
            
            # Add similarity_score to scraped_pages
            try:
                conn.execute(text("ALTER TABLE scraped_pages ADD COLUMN similarity_score TEXT"))
                conn.commit()
                print("✓ Added similarity_score column to scraped_pages")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("  similarity_score column already exists")
                else:
                    raise
        
        print("✓ Migration completed successfully!")
        print("\nYou can now restart your backend server.")
        
        return True
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = update_tables()
    sys.exit(0 if success else 1)
