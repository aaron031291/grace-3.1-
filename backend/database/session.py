"""
Database session management module.
Provides session factory and context managers for database operations.

Includes automatic retry logic for transient SQLite "database is locked"
errors so callers never need to handle them manually.
"""

import time
import threading
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
        # Do not log auth/HTTP errors as database session errors
        from fastapi import HTTPException
        if not isinstance(e, HTTPException):
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



# ── Circuit breaker state ────────────────────────────────────────────────
_cb_failures = 0
_cb_open_until = 0.0
_CB_THRESHOLD = 10          # failures before opening circuit
_CB_RECOVERY_S = 30         # seconds before retrying after circuit open
_cb_lock = threading.Lock()


def _cb_record_failure() -> bool:
    """Record a DB failure. Returns True if circuit is now open."""
    global _cb_failures, _cb_open_until
    with _cb_lock:
        _cb_failures += 1
        if _cb_failures >= _CB_THRESHOLD:
            _cb_open_until = time.time() + _CB_RECOVERY_S
            return True
    return False


def _cb_record_success() -> None:
    global _cb_failures, _cb_open_until
    with _cb_lock:
        _cb_failures = max(0, _cb_failures - 1)
        _cb_open_until = 0.0


def _cb_is_open() -> bool:
    with _cb_lock:
        if _cb_open_until and time.time() < _cb_open_until:
            return True
        return False


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Provides a transactional scope around a series of operations.
    Retries commit on transient lock errors.

    Self-healing:
    - Schema drift (UndefinedColumn/Table) → runs auto_migrate, then signals
      the error_pipeline so the fix is learned and tracked.
    - All other errors → reported to error_pipeline for coding-agent routing.
    - Circuit breaker: if DB fails repeatedly, trips open for 30s to avoid
      hammering a dead database.
    """
    if _cb_is_open():
        raise RuntimeError(
            "Database circuit breaker OPEN — too many consecutive failures. "
            f"Will retry in {max(0, _cb_open_until - time.time()):.0f}s."
        )

    if SessionLocal is None:
        initialize_session_factory()

    session = SessionLocal()
    try:
        yield session
        _commit_with_retry(session)
        _cb_record_success()
    except Exception as e:
        session.rollback()
        err_str = str(e)

        # ── Self-healing: schema drift ──────────────────────────────────
        _SCHEMA_SIGNALS = (
            "UndefinedColumn", "UndefinedTable",
            "does not exist", "no such column", "no such table",
        )
        is_schema_error = (
            any(sig in err_str for sig in _SCHEMA_SIGNALS)
            and ("psycopg2" in err_str or "sqlite" in err_str.lower())
        )

        if is_schema_error:
            logger.warning(
                "[SESSION] Schema drift — running auto-migrate: %s", err_str[:200]
            )
            try:
                from database.auto_migrate import run_auto_migrate
                engine = session.get_bind()
                changes = run_auto_migrate(engine)
                if changes:
                    logger.info(
                        "[SESSION] ✅ Schema healed: %d change(s): %s",
                        len(changes), changes,
                    )
            except Exception as migrate_err:
                logger.error("[SESSION] Auto-migrate failed: %s", migrate_err)

        # ── Route to error pipeline (non-blocking) ──────────────────────
        try:
            # Avoid circular import — lazy import inside handler
            import importlib
            ep_mod = importlib.import_module("self_healing.error_pipeline")
            ep_mod.report_error(e, context={"sql_error": err_str[:300]})
        except Exception:
            pass

        _cb_record_failure()
        logger.error("Database session_scope error: %s", e)
        raise
    finally:
        session.close()


@contextmanager
def batch_session_scope(batch_size: int = 1000):
    """
    Context manager optimised for high-volume bulk inserts.

    Yields (session, flush_batch) — call flush_batch() after adding
    `batch_size` objects to flush and clear the identity map, keeping
    memory bounded on large ingests.

    Example::

        with batch_session_scope(batch_size=250) as (session, flush):
            for i, row in enumerate(rows):
                session.add(SomeModel(**row))
                if (i + 1) % 250 == 0:
                    flush()
    """
    if SessionLocal is None:
        initialize_session_factory()

    session = SessionLocal()
    counter = {"n": 0}

    def flush_batch():
        counter["n"] += 1
        try:
            session.flush()
            session.expire_all()
        except OperationalError as e:
            if _is_lock_error(e):
                logger.warning("Batch flush hit lock — retrying after rollback")
                session.rollback()
                time.sleep(_RETRY_BACKOFF_S)
            else:
                raise

    try:
        yield session, flush_batch
        _commit_with_retry(session)
        logger.debug("Batch session committed (%d flushes)", counter["n"])
    except Exception as e:
        session.rollback()
        logger.error(f"Batch session error: {e}")
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
                _track_db_error(e)
                raise


def _track_db_error(exc: Exception) -> None:
    """Fire-and-forget Genesis key for DB errors."""
    try:
        from api._genesis_tracker import track
        track(
            key_type="error",
            what=f"Database error: {str(exc)[:100]}",
            who="database.session",
            is_error=True,
            error_type=type(exc).__name__,
            error_message=str(exc)[:300],
            tags=["database", "db", "operational_error"],
        )
    except Exception:
        pass
