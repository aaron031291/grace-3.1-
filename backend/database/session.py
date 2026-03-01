"""
Database session management module.
Provides session factory and context managers for database operations.

Includes automatic retry logic for transient SQLite "database is locked"
errors so callers never need to handle them manually.
"""

import time
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from typing import Generator, Optional
from contextlib import contextmanager
import logging

from .connection import DatabaseConnection


logger = logging.getLogger(__name__)

SessionLocal: Optional[sessionmaker] = None

_RETRY_MAX = 3
_RETRY_BACKOFF_S = 0.5


def _is_lock_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "database is locked" in msg or "locked" in msg


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
    Retries commit up to _RETRY_MAX times on transient lock errors.
    
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
        _commit_with_retry(session)
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


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Provides a transactional scope around a series of operations.
    Retries commit on transient lock errors.
    """
    if SessionLocal is None:
        initialize_session_factory()
    
    session = SessionLocal()
    try:
        yield session
        _commit_with_retry(session)
    except Exception as e:
        session.rollback()
        logger.error(f"Database session_scope error: {e}")
        raise
    finally:
        session.close()


def _commit_with_retry(session: Session) -> None:
    """Attempt session.commit(), retrying on transient lock errors."""
    for attempt in range(1, _RETRY_MAX + 1):
        try:
            session.commit()
            return
        except OperationalError as e:
            if _is_lock_error(e) and attempt < _RETRY_MAX:
                wait = _RETRY_BACKOFF_S * attempt
                logger.warning(
                    "Database locked on commit (attempt %d/%d), "
                    "retrying in %.1fs …",
                    attempt, _RETRY_MAX, wait,
                )
                session.rollback()
                time.sleep(wait)
            else:
                raise
