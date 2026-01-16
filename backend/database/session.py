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

    Note: This function auto-commits on success and auto-rolls back on error.
    For explicit transaction control, use get_transaction_session() instead.
    """
    if SessionLocal is None:
        initialize_session_factory()

    session = SessionLocal()
    try:
        yield session
        # Only commit if no exception was raised during yield
        try:
            session.commit()
        except Exception as commit_error:
            logger.error(f"Database commit failed: {commit_error}")
            session.rollback()
            raise
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def get_transaction_session() -> Generator[Session, None, None]:
    """
    Dependency injection for explicit transaction control.

    Unlike get_session(), this does NOT auto-commit.
    The caller is responsible for calling session.commit() or session.rollback().

    Usage:
        @app.post("/items/")
        def create_items(session: Session = Depends(get_transaction_session)):
            session.add(item1)
            session.add(item2)
            session.commit()  # Explicit commit required

    Yields:
        Session: SQLAlchemy session instance
    """
    if SessionLocal is None:
        initialize_session_factory()

    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction error: {e}")
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
