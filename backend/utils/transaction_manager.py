"""
Transaction Management with Rollback Support

Provides transaction context managers with automatic rollback on failure.
"""
import logging
from typing import Optional, Callable, Any, List
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class TransactionError(Exception):
    """Raised when transaction operations fail."""
    pass


@contextmanager
def transaction(session: Session, rollback_on_error: bool = True):
    """
    Context manager for database transactions with automatic rollback.
    
    Args:
        session: SQLAlchemy session
        rollback_on_error: If True, rollback on exception
        
    Example:
        with transaction(session) as tx:
            session.add(new_object)
            # Commit happens automatically on success
    """
    try:
        yield session
        session.commit()
        logger.debug("[TRANSACTION] Committed successfully")
    except Exception as e:
        if rollback_on_error:
            session.rollback()
            logger.warning(f"[TRANSACTION] Rolled back due to error: {e}")
        raise


@contextmanager
def nested_transaction(session: Session):
    """
    Nested transaction (savepoint) context manager.
    
    Args:
        session: SQLAlchemy session
        
    Example:
        with nested_transaction(session) as savepoint:
            session.add(new_object)
            # Rollback only affects this nested transaction
    """
    savepoint = session.begin_nested()
    try:
        yield savepoint
        savepoint.commit()
        logger.debug("[TRANSACTION] Nested transaction committed")
    except Exception as e:
        savepoint.rollback()
        logger.warning(f"[TRANSACTION] Nested transaction rolled back: {e}")
        raise


class TransactionManager:
    """
    Manages multiple operations with rollback support.
    
    Tracks operations and can rollback all if any fail.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.operations: List[Callable] = []
        self.rollback_operations: List[Callable] = []
        self.committed = False
    
    def add_operation(
        self,
        operation: Callable,
        rollback_operation: Optional[Callable] = None
    ):
        """
        Add an operation to the transaction.
        
        Args:
            operation: Function to execute
            rollback_operation: Optional function to undo operation
        """
        self.operations.append(operation)
        if rollback_operation:
            self.rollback_operations.append(rollback_operation)
    
    def execute(self) -> Any:
        """
        Execute all operations in order.
        
        Returns:
            Result of last operation
            
        Raises:
            TransactionError: If any operation fails
        """
        results = []
        
        try:
            for i, operation in enumerate(self.operations):
                result = operation()
                results.append(result)
            
            self.session.commit()
            self.committed = True
            logger.debug(f"[TRANSACTION-MANAGER] Committed {len(self.operations)} operations")
            return results[-1] if results else None
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"[TRANSACTION-MANAGER] Rolled back due to error: {e}")
            
            # Execute rollback operations in reverse order
            for rollback_op in reversed(self.rollback_operations):
                try:
                    rollback_op()
                except Exception as rollback_error:
                    logger.warning(f"[TRANSACTION-MANAGER] Rollback operation failed: {rollback_error}")
            
            raise TransactionError(f"Transaction failed: {e}") from e
    
    def rollback(self):
        """Manually rollback the transaction."""
        if not self.committed:
            self.session.rollback()
            logger.info("[TRANSACTION-MANAGER] Manually rolled back")


def with_rollback(session: Session):
    """
    Decorator to wrap function with transaction rollback.
    
    Args:
        session: SQLAlchemy session
        
    Example:
        @with_rollback(session)
        def create_user():
            session.add(new_user)
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                session.commit()
                return result
            except Exception as e:
                session.rollback()
                raise
        return wrapper
    return decorator
