"""
Database migration to add web scraping tables.
"""

from database.connection import DatabaseConnection, Base
from scraping.models import ScrapingJob, ScrapedPage


def migrate():
    """Create scraping tables in the database."""
    try:
        engine = DatabaseConnection.get_engine()
        
        # Create tables
        Base.metadata.create_all(
            engine,
            tables=[ScrapingJob.__table__, ScrapedPage.__table__]
        )
        
        print("✓ Created scraping_jobs table")
        print("✓ Created scraped_pages table")
        print("✓ Web scraping tables migration completed successfully")
        
        return True
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        return False


if __name__ == "__main__":
    migrate()
