"""
Database models for web scraping functionality.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database.base import Base


class ScrapingJob(Base):
    """Model for tracking web scraping jobs."""
    
    __tablename__ = 'scraping_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2048), nullable=False)
    depth = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default='pending')  # pending, running, completed, failed, cancelled
    total_pages = Column(Integer, default=0)
    pages_scraped = Column(Integer, default=0)
    pages_failed = Column(Integer, default=0)
    pages_filtered = Column(Integer, default=0)  # Pages filtered by semantic similarity
    pages_downloaded = Column(Integer, default=0)  # Documents downloaded (PDFs, DOCXs, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    folder_path = Column(String(512), nullable=True)
    same_domain_only = Column(Integer, default=1)  # SQLite doesn't have boolean
    max_pages = Column(Integer, default=100)
    
    # Relationship to scraped pages
    pages = relationship("ScrapedPage", back_populates="job", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ScrapingJob(id={self.id}, url='{self.url}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'url': self.url,
            'depth': self.depth,
            'status': self.status,
            'total_pages': self.total_pages,
            'pages_scraped': self.pages_scraped,
            'pages_failed': self.pages_failed,
            'pages_filtered': self.pages_filtered,
            'pages_downloaded': self.pages_downloaded,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'folder_path': self.folder_path,
            'same_domain_only': bool(self.same_domain_only),
            'max_pages': self.max_pages,
            'progress_percentage': int((self.pages_scraped / self.total_pages * 100) if self.total_pages > 0 else 0)
        }


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
    status = Column(String(50), nullable=False, default='pending')  # pending, success, failed, filtered
    error_message = Column(Text, nullable=True)
    similarity_score = Column(String(10), nullable=True)  # Semantic similarity score (stored as string for SQLite)
    scraped_at = Column(DateTime, nullable=True)
    document_id = Column(Integer, nullable=True)  # FK to documents table after ingestion
    file_path = Column(String(1024), nullable=True)  # Path to downloaded document
    file_size = Column(Integer, nullable=True)  # Size in bytes for downloaded documents
    file_type = Column(String(50), nullable=True)  # File extension (e.g., 'pdf', 'docx')
    
    # Relationship to job
    job = relationship("ScrapingJob", back_populates="pages")
    
    def __repr__(self):
        return f"<ScrapedPage(id={self.id}, url='{self.url}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'url': self.url,
            'depth_level': self.depth_level,
            'parent_url': self.parent_url,
            'title': self.title,
            'content_length': self.content_length,
            'status': self.status,
            'error_message': self.error_message,
            'similarity_score': float(self.similarity_score) if self.similarity_score else None,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'document_id': self.document_id,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_type': self.file_type
        }
