"""
Database migration: Add document download fields

This migration adds support for tracking downloaded documents in the scraping system.

New fields:
- scraping_jobs.pages_downloaded: Count of downloaded documents
- scraped_pages.file_path: Path to downloaded document file
- scraped_pages.file_size: Size of downloaded document in bytes
- scraped_pages.file_type: File extension (pdf, docx, etc.)
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run_migration():
    """Run the migration to add document download fields."""
    
    # Get database path
    backend_dir = Path(__file__).parent.parent.parent
    db_path = backend_dir / "data" / "grace.db"
    
    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        logger.info("Starting migration: add_document_download_fields")
        
        # Add pages_downloaded to scraping_jobs table
        try:
            cursor.execute("""
                ALTER TABLE scraping_jobs 
                ADD COLUMN pages_downloaded INTEGER DEFAULT 0
            """)
            logger.info("✓ Added pages_downloaded to scraping_jobs")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                logger.info("⚠ pages_downloaded already exists in scraping_jobs")
            else:
                raise
        
        # Add file_path to scraped_pages table
        try:
            cursor.execute("""
                ALTER TABLE scraped_pages 
                ADD COLUMN file_path VARCHAR(1024)
            """)
            logger.info("✓ Added file_path to scraped_pages")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                logger.info("⚠ file_path already exists in scraped_pages")
            else:
                raise
        
        # Add file_size to scraped_pages table
        try:
            cursor.execute("""
                ALTER TABLE scraped_pages 
                ADD COLUMN file_size INTEGER
            """)
            logger.info("✓ Added file_size to scraped_pages")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                logger.info("⚠ file_size already exists in scraped_pages")
            else:
                raise
        
        # Add file_type to scraped_pages table
        try:
            cursor.execute("""
                ALTER TABLE scraped_pages 
                ADD COLUMN file_type VARCHAR(50)
            """)
            logger.info("✓ Added file_type to scraped_pages")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                logger.info("⚠ file_type already exists in scraped_pages")
            else:
                raise
        
        # Commit changes
        conn.commit()
        logger.info("✓ Migration completed successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = run_migration()
    exit(0 if success else 1)
