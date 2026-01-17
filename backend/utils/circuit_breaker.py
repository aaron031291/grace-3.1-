"""
Universal Circuit Breaker Implementation

Provides circuit breaker pattern for external service calls to prevent cascading failures.
"""
import logging
import time
from enum import Enum
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
import threading

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Open after N failures
    success_threshold: int = 2  # Close after N successes in half-open
    timeout_seconds: int = 60  # Time before attempting half-open
    expected_exception: type = Exception  # Exception type to catch


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    state_changes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    Prevents cascading failures by:
    1. Opening circuit after failure threshold
    2. Rejecting requests when open
    3. Testing recovery in half-open state
    4. Closing circuit after success threshold
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = threading.Lock()
        self._opened_at: Optional[datetime] = None
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        with self._lock:
            # Check if circuit should transition
            self._check_state_transition()
            
            # If open, reject immediately
            if self.state == CircuitState.OPEN:
                self.stats.total_requests += 1
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Last failure: {self.stats.last_failure_time}. "
                    f"Will retry after {self.config.timeout_seconds}s"
                )
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            raise
    
    def _check_state_transition(self):
        """Check if circuit state should transition."""
        now = datetime.utcnow()
        
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._opened_at and (now - self._opened_at).total_seconds() >= self.config.timeout_seconds:
                self._transition_to_half_open()
        elif self.state == CircuitState.HALF_OPEN:
            # Half-open state is managed by success/failure counts
            pass
    
    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            self.stats.total_requests += 1
            self.stats.total_successes += 1
            self.stats.last_success_time = datetime.utcnow()
            self.stats.consecutive_successes += 1
            self.stats.consecutive_failures = 0
            
            if self.state == CircuitState.HALF_OPEN:
                if self.stats.consecutive_successes >= self.config.success_threshold:
                    self._transition_to_closed()
            elif self.state == CircuitState.OPEN:
                # Shouldn't happen, but handle gracefully
                self._transition_to_half_open()
    
    def _on_failure(self):
        """Handle failed call."""
        with self._lock:
            self.stats.total_requests += 1
            self.stats.total_failures += 1
            self.stats.last_failure_time = datetime.utcnow()
            self.stats.consecutive_failures += 1
            self.stats.consecutive_successes = 0
            
            if self.state == CircuitState.CLOSED:
                if self.stats.consecutive_failures >= self.config.failure_threshold:
                    self._transition_to_open()
            elif self.state == CircuitState.HALF_OPEN:
                # Failed in half-open, go back to open
                self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition to OPEN state."""
        if self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            self._opened_at = datetime.utcnow()
            self.stats.state_changes += 1
            logger.warning(
                f"[CIRCUIT-BREAKER] '{self.name}' OPENED after "
                f"{self.stats.consecutive_failures} consecutive failures"
            )
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        if self.state != CircuitState.HALF_OPEN:
            self.state = CircuitState.HALF_OPEN
            self.stats.state_changes += 1
            self.stats.consecutive_successes = 0
            logger.info(
                f"[CIRCUIT-BREAKER] '{self.name}' HALF_OPEN - testing recovery"
            )
    
    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        if self.state != CircuitState.CLOSED:
            self.state = CircuitState.CLOSED
            self._opened_at = None
            self.stats.state_changes += 1
            logger.info(
                f"[CIRCUIT-BREAKER] '{self.name}' CLOSED - service recovered"
            )
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self._opened_at = None
            self.stats.consecutive_failures = 0
            self.stats.consecutive_successes = 0
            self.stats.state_changes += 1
            logger.info(f"[CIRCUIT-BREAKER] '{self.name}' manually RESET")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_requests": self.stats.total_requests,
            "total_failures": self.stats.total_failures,
            "total_successes": self.stats.total_successes,
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "last_failure_time": self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None,
            "last_success_time": self.stats.last_success_time.isoformat() if self.stats.last_success_time else None,
            "state_changes": self.stats.state_changes,
            "opened_at": self._opened_at.isoformat() if self._opened_at else None,
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_breaker_lock = threading.Lock()


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """
    Get or create a circuit breaker.
    
    Args:
        name: Circuit breaker name
        config: Optional configuration
        
    Returns:
        CircuitBreaker instance
    """
    with _breaker_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, config)
        return _circuit_breakers[name]


def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    expected_exception: type = Exception
):
    """
    Decorator to apply circuit breaker to a function.
    
    Args:
        name: Circuit breaker name
        config: Optional configuration
        expected_exception: Exception type to catch
        
    Example:
        @circuit_breaker("database", CircuitBreakerConfig(failure_threshold=5))
        def query_database():
            ...
    """
    def decorator(func: Callable) -> Callable:
        breaker_config = config or CircuitBreakerConfig()
        breaker_config.expected_exception = expected_exception
        breaker = get_circuit_breaker(name, breaker_config)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


def get_all_circuit_breakers() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all circuit breakers."""
    with _breaker_lock:
        return {
            name: breaker.get_stats()
            for name, breaker in _circuit_breakers.items()
        }
