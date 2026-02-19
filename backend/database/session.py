"""
Database session management module.
Provides session factory and context managers for database operations.
"""

from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional
import logging

from .connection import DatabaseConnection


logger = logging.getLogger(__name__)

# Session factory will be initialized after database connection
SessionLocal: Optional[sessionmaker] = None


def initialize_session_factory() -> sessionmaker:
    """
    Initialize the session factory with the database engine.
    
    Returns:
        sessionmaker: Session factory
    """
    global SessionLocal
    
    engine = DatabaseConnection.get_engine()
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    
    return SessionLocal


def get_session() -> Generator[Session, None, None]:
    """
    Dependency injection for FastAPI - yields a new database session.
    
    Usage:
        @app.get("/items/")
        def read_items(session: Session = Depends(get_session)):
            return session.query(Item).all()
    
    Yields:
        Session: SQLAlchemy session instance
    """
    if SessionLocal is None:
        initialize_session_factory()
    
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    Alternative alias for get_session().

    Yields:
        Session: SQLAlchemy session instance
    """
    yield from get_session()


def get_session_factory() -> sessionmaker:
    """
    Get the session factory for creating sessions directly.

    Useful for background tasks and thread-based operations
    that need to manage their own session lifecycle.

    Returns:
        sessionmaker: Session factory that can be called to create sessions

    Example:
        session_factory = get_session_factory()
        session = session_factory()
        try:
            # do work
            session.commit()
        finally:
            session.close()
    """
    if SessionLocal is None:
        initialize_session_factory()

    return SessionLocal
