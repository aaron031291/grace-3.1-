"""
Database Tracking via SQLAlchemy Event Listeners

Automatically tracks all database operations:
- SELECT queries (reads)
- INSERT/UPDATE/DELETE operations (writes)
- Schema changes
- Connection events

Uses SQLAlchemy event listeners for automatic, comprehensive tracking.
"""

import logging
import time
from typing import Optional, Dict, Any, Set
from datetime import datetime, UTC
from sqlalchemy import event, Engine
from sqlalchemy.engine import Connection
from sqlalchemy.pool import Pool
from sqlalchemy.sql import ClauseElement
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import SessionTransaction

from database.session import SessionLocal
from genesis.comprehensive_tracker import ComprehensiveTracker
from models.genesis_key_models import GenesisKeyType

logger = logging.getLogger(__name__)

# Track active queries to avoid duplicate tracking
_active_queries: Set[str] = set()
_tracking_enabled = True


def enable_database_tracking():
    """Enable database tracking."""
    global _tracking_enabled
    _tracking_enabled = True
    logger.info("[GENESIS-DB-TRACKING] Database tracking enabled")


def disable_database_tracking():
    """Disable database tracking (for testing or performance)."""
    global _tracking_enabled
    _tracking_enabled = False
    logger.info("[GENESIS-DB-TRACKING] Database tracking disabled")


def _track_query_async(
    query_type: str,
    statement: str,
    parameters: Optional[Dict[str, Any]],
    execution_time_ms: float,
    result_count: Optional[int] = None,
    table_name: Optional[str] = None
):
    """Track a database query asynchronously (non-blocking)."""
    if not _tracking_enabled:
        return

    try:
        # Create a new session for tracking (to avoid circular dependencies)
        db = SessionLocal()
        tracker = ComprehensiveTracker(db_session=db)

        try:
            if query_type == "SELECT":
                # Track read operation
                tracker.track_database_read(
                    table_name=table_name or "unknown",
                    query_params=parameters,
                    result_count=result_count,
                    execution_time_ms=execution_time_ms,
                    query_type="SELECT",
                    metadata={
                        "statement": statement[:500],  # Limit statement length
                        "full_statement": len(statement) > 500
                    }
                )
            elif query_type in ("INSERT", "UPDATE", "DELETE"):
                # Track write operation
                tracker.track_database_change(
                    table_name=table_name or "unknown",
                    operation=query_type,
                    metadata={
                        "statement": statement[:500],
                        "execution_time_ms": execution_time_ms,
                        "affected_rows": result_count
                    }
                )

            db.commit()
        except Exception as e:
            logger.warning(f"[GENESIS-DB-TRACKING] Failed to track query: {e}")
            db.rollback()
        finally:
            db.close()

    except Exception as e:
        logger.warning(f"[GENESIS-DB-TRACKING] Failed to create tracking session: {e}")


def _extract_table_name(statement: str) -> Optional[str]:
    """Extract table name from SQL statement."""
    statement_upper = statement.upper().strip()
    
    # Try to extract table name from common patterns
    if statement_upper.startswith("SELECT"):
        # SELECT ... FROM table_name
        if "FROM" in statement_upper:
            parts = statement_upper.split("FROM", 1)
            if len(parts) > 1:
                table_part = parts[1].strip().split()[0]
                return table_part.lower()
    elif statement_upper.startswith("INSERT"):
        # INSERT INTO table_name
        if "INTO" in statement_upper:
            parts = statement_upper.split("INTO", 1)
            if len(parts) > 1:
                table_part = parts[1].strip().split()[0]
                return table_part.lower()
    elif statement_upper.startswith("UPDATE"):
        # UPDATE table_name
        parts = statement_upper.split()
        if len(parts) > 1:
            return parts[1].lower()
    elif statement_upper.startswith("DELETE"):
        # DELETE FROM table_name
        if "FROM" in statement_upper:
            parts = statement_upper.split("FROM", 1)
            if len(parts) > 1:
                table_part = parts[1].strip().split()[0]
                return table_part.lower()
    elif statement_upper.startswith("ALTER") or statement_upper.startswith("CREATE") or statement_upper.startswith("DROP"):
        # ALTER/CREATE/DROP TABLE table_name
        if "TABLE" in statement_upper:
            parts = statement_upper.split("TABLE", 1)
            if len(parts) > 1:
                table_part = parts[1].strip().split()[0]
                return table_part.lower()

    return None


def _extract_query_type(statement: str) -> Optional[str]:
    """Extract query type from SQL statement."""
    statement_upper = statement.upper().strip()
    
    if statement_upper.startswith("SELECT"):
        return "SELECT"
    elif statement_upper.startswith("INSERT"):
        return "INSERT"
    elif statement_upper.startswith("UPDATE"):
        return "UPDATE"
    elif statement_upper.startswith("DELETE"):
        return "DELETE"
    elif statement_upper.startswith("ALTER"):
        return "ALTER"
    elif statement_upper.startswith("CREATE"):
        return "CREATE"
    elif statement_upper.startswith("DROP"):
        return "DROP"
    
    return None


@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Track SQL execution start."""
    if not _tracking_enabled:
        return

    # Store start time for execution tracking
    conn.info.setdefault("query_start_time", []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Track SQL execution completion."""
    if not _tracking_enabled:
        return

    try:
        # Get execution time
        start_times = conn.info.get("query_start_time", [])
        if start_times:
            start_time = start_times.pop()
            execution_time_ms = (time.time() - start_time) * 1000
        else:
            execution_time_ms = 0

        # Extract query type and table name
        query_type = _extract_query_type(statement)
        table_name = _extract_table_name(statement)

        # Skip tracking for Genesis Key operations to avoid recursion
        # Also skip tracking operations on system tables
        statement_lower = statement.lower()
        if any(table in statement_lower for table in ["genesis_key", "genesis_key_archive", "user_profile"]):
            if query_type in ("INSERT", "UPDATE", "SELECT"):
                return

        # Convert parameters to dict if possible
        params_dict = None
        if parameters:
            if isinstance(parameters, dict):
                params_dict = parameters
            elif isinstance(parameters, (list, tuple)):
                # Try to convert positional params to dict
                params_dict = {f"param_{i}": p for i, p in enumerate(parameters)}

        # Get result count for SELECT queries
        result_count = None
        if query_type == "SELECT" and cursor.rowcount >= 0:
            result_count = cursor.rowcount

        # Track the query
        if query_type:
            _track_query_async(
                query_type=query_type,
                statement=statement,
                parameters=params_dict,
                execution_time_ms=execution_time_ms,
                result_count=result_count,
                table_name=table_name
            )

    except Exception as e:
        logger.warning(f"[GENESIS-DB-TRACKING] Error tracking query: {e}")


@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Track database connection establishment."""
    if not _tracking_enabled:
        return

    try:
        db = SessionLocal()
        tracker = ComprehensiveTracker(db_session=db)

        try:
            tracker._create_genesis_key(
                key_type=GenesisKeyType.SYSTEM_EVENT,
                what_description="Database connection established",
                where_location="database",
                why_reason="Database connection",
                how_method="connection_pool",
                tags=["database", "connection", "open"]
            )
            db.commit()
        except Exception as e:
            logger.warning(f"[GENESIS-DB-TRACKING] Failed to track connection: {e}")
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[GENESIS-DB-TRACKING] Failed to track connection: {e}")


@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Track connection checkout from pool."""
    # Connection checkout is less critical, skip for now to avoid noise
    pass


@event.listens_for(Pool, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Track connection checkin to pool."""
    # Connection checkin is less critical, skip for now to avoid noise
    pass


def setup_database_tracking(engine: Engine):
    """
    Setup database tracking event listeners on an engine.

    Args:
        engine: SQLAlchemy engine to attach listeners to
    """
    # Event listeners are registered globally via @event.listens_for decorators
    # This function is for explicit setup/verification
    logger.info("[GENESIS-DB-TRACKING] Database tracking event listeners registered")
    enable_database_tracking()
