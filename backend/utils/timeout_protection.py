"""
Universal Timeout Protection

Provides timeout decorators and context managers for operations.
"""
import logging
import signal
import threading
import asyncio
from typing import Callable, Any, Optional
from functools import wraps
from contextlib import contextmanager
import time

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Raised when operation exceeds timeout."""
    pass


def timeout(seconds: int, error_message: Optional[str] = None):
    """
    Decorator to enforce timeout on synchronous functions.
    
    Args:
        seconds: Timeout in seconds
        error_message: Optional custom error message
        
    Example:
        @timeout(30)
        def long_operation():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if seconds <= 0:
                return func(*args, **kwargs)
            
            # Use threading.Timer for cross-platform timeout
            result = [None]
            exception = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout=seconds)
            
            if thread.is_alive():
                error_msg = error_message or f"Operation '{func.__name__}' exceeded {seconds}s timeout"
                logger.warning(f"[TIMEOUT] {error_msg}")
                raise TimeoutError(error_msg)
            
            if exception[0]:
                raise exception[0]
            
            return result[0]
        
        return wrapper
    return decorator


def async_timeout(seconds: int, error_message: Optional[str] = None):
    """
    Decorator to enforce timeout on async functions.
    
    Args:
        seconds: Timeout in seconds
        error_message: Optional custom error message
        
    Example:
        @async_timeout(30)
        async def long_async_operation():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if seconds <= 0:
                return await func(*args, **kwargs)
            
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                error_msg = error_message or f"Async operation '{func.__name__}' exceeded {seconds}s timeout"
                logger.warning(f"[TIMEOUT] {error_msg}")
                raise TimeoutError(error_msg)
        
        return wrapper
    return decorator


@contextmanager
def timeout_context(seconds: int, error_message: Optional[str] = None):
    """
    Context manager for timeout protection.
    
    Args:
        seconds: Timeout in seconds
        error_message: Optional custom error message
        
    Example:
        with timeout_context(30):
            long_operation()
    """
    if seconds <= 0:
        yield
        return
    
    start_time = time.time()
    
    def check_timeout():
        elapsed = time.time() - start_time
        if elapsed >= seconds:
            error_msg = error_message or f"Operation exceeded {seconds}s timeout"
            logger.warning(f"[TIMEOUT] {error_msg}")
            raise TimeoutError(error_msg)
    
    try:
        yield
        check_timeout()
    except TimeoutError:
        raise
    except Exception as e:
        check_timeout()  # Check timeout even on exception
        raise


# Convenience functions for common timeouts
def quick_timeout(func: Callable) -> Callable:
    """5 second timeout for quick operations."""
    return timeout(5)(func)


def standard_timeout(func: Callable) -> Callable:
    """30 second timeout for standard operations."""
    return timeout(30)(func)


def long_timeout(func: Callable) -> Callable:
    """60 second timeout for long operations."""
    return timeout(60)(func)


def very_long_timeout(func: Callable) -> Callable:
    """300 second (5 minute) timeout for very long operations."""
    return timeout(300)(func)
