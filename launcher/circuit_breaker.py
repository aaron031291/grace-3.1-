"""
Circuit Breaker Pattern for Enterprise Launcher

Prevents cascading failures by stopping repeated calls to failing services.
Similar to Netflix Hystrix, Resilience4j, and other enterprise patterns.
"""

import time
import logging
from typing import Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, fast-fail
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5      # Failures before opening
    timeout_seconds: int = 60       # Time before trying half-open
    success_threshold: int = 2      # Successes needed to close from half-open
    name: str = "default"


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by:
    1. Tracking failures
    2. Opening circuit after threshold
    3. Fast-failing when open
    4. Testing recovery (half-open)
    5. Closing when recovered
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        """Initialize circuit breaker."""
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments for function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.config.timeout_seconds:
                    logger.info(f"[CIRCUIT-BREAKER] {self.config.name}: Moving to HALF_OPEN (testing recovery)")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker {self.config.name} is OPEN. "
                        f"Retry in {self.config.timeout_seconds - int(elapsed)}s"
                    )
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        self.last_success_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                logger.info(f"[CIRCUIT-BREAKER] {self.config.name}: Recovered, moving to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.last_failure_time = datetime.utcnow()
        self.failure_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery test - back to open
            logger.warning(f"[CIRCUIT-BREAKER] {self.config.name}: Recovery test failed, back to OPEN")
            self.state = CircuitState.OPEN
            self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Check if threshold reached
            if self.failure_count >= self.config.failure_threshold:
                logger.error(
                    f"[CIRCUIT-BREAKER] {self.config.name}: "
                    f"Failure threshold ({self.config.failure_threshold}) reached, opening circuit"
                )
                self.state = CircuitState.OPEN
    
    def reset(self):
        """Manually reset circuit breaker."""
        logger.info(f"[CIRCUIT-BREAKER] {self.config.name}: Manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
    
    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            "name": self.config.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success": self.last_success_time.isoformat() if self.last_success_time else None
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# Global circuit breakers for different services
_service_circuit_breakers: dict = {}


def get_circuit_breaker(service_name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """
    Get or create circuit breaker for a service.
    
    Args:
        service_name: Name of the service
        config: Optional configuration (uses defaults if not provided)
        
    Returns:
        CircuitBreaker instance
    """
    if service_name not in _service_circuit_breakers:
        if config is None:
            config = CircuitBreakerConfig(name=service_name)
        _service_circuit_breakers[service_name] = CircuitBreaker(config)
    
    return _service_circuit_breakers[service_name]
