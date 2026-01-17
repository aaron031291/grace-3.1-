"""
Database Error Logger - Logs database errors as Genesis Keys for self-healing detection.

This module provides utilities to automatically log database errors as Genesis Keys
so that the autonomous healing system can detect and fix them.
"""

import logging
import traceback
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, SQLAlchemyError
import sqlite3

from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKeyType

logger = logging.getLogger(__name__)


def log_database_error(
    error: Exception,
    operation: str,
    table_name: Optional[str] = None,
    session: Optional[Session] = None
) -> Optional[str]:
    """
    Log a database error as a Genesis Key for self-healing detection.
    
    Args:
        error: The database error exception
        operation: Description of the operation that failed
        table_name: Name of the table involved (if known)
        session: Database session (if available)
        
    Returns:
        Genesis Key ID if successfully logged, None otherwise
    """
    try:
        genesis_service = get_genesis_service()
        
        # Extract table name from error message if not provided
        error_msg = str(error)
        if not table_name:
            # Try to extract table name from "no such table: X" error
            if "no such table" in error_msg.lower():
                import re
                match = re.search(r"table['\"]?\s*:?\s*['\"]?(\w+)['\"]?", error_msg, re.IGNORECASE)
                if match:
                    table_name = match.group(1)
        
        # Determine error type
        error_type = type(error).__name__
        is_table_error = "no such table" in error_msg.lower() or "table" in error_msg.lower()
        
        # Create Genesis Key
        key = genesis_service.create_key(
            key_type=GenesisKeyType.ERROR,
            what_description=f"Database error during {operation}: {error_type}",
            who_actor="database_system",
            where_location=table_name or "database",
            why_reason=f"Database operation failed: {operation}",
            how_method="error_logging",
            is_error=True,
            error_type=error_type,
            error_message=error_msg,
            error_traceback=traceback.format_exc(),
            context_data={
                "operation": operation,
                "table_name": table_name,
                "is_table_error": is_table_error,
                "error_class": error_type
            },
            tags=["database_error", "self_healing_target"],
            session=session
        )
        
        logger.info(
            f"[DB-ERROR-LOGGER] Logged database error as Genesis Key: {key.key_id} "
            f"(operation={operation}, table={table_name or 'unknown'})"
        )
        
        return key.key_id
        
    except Exception as e:
        # Can't log to Genesis Keys if Genesis Keys themselves are failing
        logger.error(f"[DB-ERROR-LOGGER] Failed to log database error: {e}")
        logger.error(f"[DB-ERROR-LOGGER] Original error: {error}")
        return None


def log_table_error(
    error: Exception,
    table_name: str,
    operation: str,
    session: Optional[Session] = None
) -> Optional[str]:
    """
    Log a table-specific database error.
    
    Convenience wrapper for log_database_error with table name.
    """
    return log_database_error(error, operation, table_name, session)


def catch_and_log_db_errors(func):
    """
    Decorator to automatically catch and log database errors as Genesis Keys.
    
    Usage:
        @catch_and_log_db_errors
        def my_database_operation():
            # Database operations here
            pass
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (OperationalError, SQLAlchemyError, sqlite3.OperationalError) as e:
            # Log the error as Genesis Key
            log_database_error(
                error=e,
                operation=func.__name__,
                session=kwargs.get('session') if 'session' in kwargs else None
            )
            # Re-raise the error so calling code can handle it
            raise
        except Exception as e:
            # Check if it's a database-related error
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ["database", "table", "sql", "operational"]):
                log_database_error(
                    error=e,
                    operation=func.__name__,
                    session=kwargs.get('session') if 'session' in kwargs else None
                )
            raise
    
    return wrapper