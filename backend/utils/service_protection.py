"""
Service Protection Integration

Integrates circuit breakers and timeout protection into critical services.
"""
import logging
from typing import Callable, Any, Optional
from functools import wraps

from .circuit_breaker import (
    get_circuit_breaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError
)
from .timeout_protection import timeout, async_timeout, TimeoutError

logger = logging.getLogger(__name__)


# Circuit breaker configurations for different services
DB_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=2,
    timeout_seconds=60,
    expected_exception=Exception
)

VECTOR_DB_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=2,
    timeout_seconds=60,
    expected_exception=Exception
)

LLM_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,  # Lower threshold for LLM (more sensitive)
    success_threshold=2,
    timeout_seconds=120,  # Longer timeout for LLM
    expected_exception=Exception
)


def protect_database_operation(timeout_seconds: int = 30):
    """
    Decorator to protect database operations with circuit breaker and timeout.
    
    Args:
        timeout_seconds: Timeout in seconds
        
    Example:
        @protect_database_operation(timeout_seconds=30)
        def query_users():
            ...
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker("database", DB_CIRCUIT_CONFIG)
        
        @wraps(func)
        @timeout(timeout_seconds)
        def wrapper(*args, **kwargs):
            try:
                return breaker.call(func, *args, **kwargs)
            except CircuitBreakerOpenError as e:
                logger.error(f"[DB-PROTECTION] Circuit breaker open: {e}")
                raise
            except TimeoutError as e:
                logger.error(f"[DB-PROTECTION] Operation timeout: {e}")
                raise
        
        return wrapper
    return decorator


def protect_vector_db_operation(timeout_seconds: int = 30):
    """
    Decorator to protect vector DB operations with circuit breaker and timeout.
    
    Args:
        timeout_seconds: Timeout in seconds
        
    Example:
        @protect_vector_db_operation(timeout_seconds=30)
        def search_vectors():
            ...
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker("vector_db", VECTOR_DB_CIRCUIT_CONFIG)
        
        @wraps(func)
        @timeout(timeout_seconds)
        def wrapper(*args, **kwargs):
            try:
                return breaker.call(func, *args, **kwargs)
            except CircuitBreakerOpenError as e:
                logger.error(f"[VECTOR-DB-PROTECTION] Circuit breaker open: {e}")
                raise
            except TimeoutError as e:
                logger.error(f"[VECTOR-DB-PROTECTION] Operation timeout: {e}")
                raise
        
        return wrapper
    return decorator


def protect_llm_operation(timeout_seconds: int = 120):
    """
    Decorator to protect LLM operations with circuit breaker and timeout.
    
    Args:
        timeout_seconds: Timeout in seconds
        
    Example:
        @protect_llm_operation(timeout_seconds=120)
        def generate_response():
            ...
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker("llm", LLM_CIRCUIT_CONFIG)
        
        @wraps(func)
        @timeout(timeout_seconds)
        def wrapper(*args, **kwargs):
            try:
                return breaker.call(func, *args, **kwargs)
            except CircuitBreakerOpenError as e:
                logger.error(f"[LLM-PROTECTION] Circuit breaker open: {e}")
                raise
            except TimeoutError as e:
                logger.error(f"[LLM-PROTECTION] Operation timeout: {e}")
                raise
        
        return wrapper
    return decorator


def protect_async_llm_operation(timeout_seconds: int = 120):
    """
    Decorator to protect async LLM operations with circuit breaker and timeout.
    
    Args:
        timeout_seconds: Timeout in seconds
        
    Example:
        @protect_async_llm_operation(timeout_seconds=120)
        async def generate_response_async():
            ...
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker("llm_async", LLM_CIRCUIT_CONFIG)
        
        @wraps(func)
        @async_timeout(timeout_seconds)
        async def wrapper(*args, **kwargs):
            try:
                return await breaker.call(func, *args, **kwargs)
            except CircuitBreakerOpenError as e:
                logger.error(f"[LLM-ASYNC-PROTECTION] Circuit breaker open: {e}")
                raise
            except TimeoutError as e:
                logger.error(f"[LLM-ASYNC-PROTECTION] Operation timeout: {e}")
                raise
        
        return wrapper
    return decorator


def get_service_protection_stats() -> dict:
    """
    Get statistics for all service protection circuit breakers.
    
    Returns:
        dict: Statistics for all circuit breakers
    """
    from .circuit_breaker import get_all_circuit_breakers
    return get_all_circuit_breakers()
