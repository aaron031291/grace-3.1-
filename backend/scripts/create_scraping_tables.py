"""
Simple script to create scraping tables.
Run this from the backend directory with: ./venv/bin/python create_scraping_tables.py
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import relationship
from datetime import datetime
from database.connection import DatabaseConnection
from database.base import Base


# Define models inline to avoid import issues
class ScrapingJob(Base):
    """Model for tracking web scraping jobs."""
    __tablename__ = 'scraping_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2048), nullable=False)
    depth = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default='pending')
    total_pages = Column(Integer, default=0)
    pages_scraped = Column(Integer, default=0)
    pages_failed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    folder_path = Column(String(512), nullable=True)
    same_domain_only = Column(Integer, default=1)
    max_pages = Column(Integer, default=100)


class ScrapedPage(Base):
    """Model for individual scraped pages."""
    __tablename__ = 'scraped_pages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey('scraping_jobs.id', ondelete='CASCADE'), nullable=False)
    url = Column(String(2048), nullable=False)
    depth_level = Column(Integer, nullable=False)
    parent_url = Column(String(2048), nullable=True)
    title = Column(String(512), nullable=True)
    content = Column(Text, nullable=True)
    content_length = Column(Integer, default=0)
    status = Column(String(50), nullable=False, default='pending')
    error_message = Column(Text, nullable=True)
    scraped_at = Column(DateTime, nullable=True)
    document_id = Column(Integer, nullable=True)


def create_tables():
    """Create scraping tables in the database."""
    try:
        print("Creating scraping tables...")
        
        # Initialize database connection
        from database.config import DatabaseConfig, DatabaseType
        config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="./data/grace.db"
        )
        DatabaseConnection.initialize(config)
        
        engine = DatabaseConnection.get_engine()
        
        # Create tables
        Base.metadata.create_all(
            engine,
            tables=[ScrapingJob.__table__, ScrapedPage.__table__]
        )
        
        print("✓ Created scraping_jobs table")
        print("✓ Created scraped_pages table")
        print("✓ Migration completed successfully!")
        print("\nYou can now restart your backend server to use the web scraping feature.")
        
        return True
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)
