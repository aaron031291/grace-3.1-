"""
Enterprise Resilience Patterns — circuit breakers, error boundaries,
backpressure, and graceful degradation.

Used across all controllers and brains.
"""

import time
import threading
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Per-service circuit breaker.
    States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing)

    Usage:
        cb = CircuitBreaker("ollama", failure_threshold=3, reset_timeout=120)
        result = cb.call(lambda: requests.get("http://localhost:11434"))
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, name: str, failure_threshold: int = 3,
                 reset_timeout: int = 120, half_open_max: int = 1):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_max = half_open_max

        self.state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.half_open_calls = 0
        self._lock = threading.Lock()

    def call(self, func: Callable, fallback: Any = None) -> Any:
        with self._lock:
            if self.state == self.OPEN:
                if time.time() - self.last_failure_time > self.reset_timeout:
                    self.state = self.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info(f"Circuit {self.name}: OPEN → HALF_OPEN (testing)")
                else:
                    logger.debug(f"Circuit {self.name}: OPEN — request rejected")
                    return fallback

            if self.state == self.HALF_OPEN and self.half_open_calls >= self.half_open_max:
                return fallback

        try:
            result = func()
            with self._lock:
                if self.state == self.HALF_OPEN:
                    self.state = self.CLOSED
                    self.failure_count = 0
                    logger.info(f"Circuit {self.name}: HALF_OPEN → CLOSED (recovered)")
                elif self.state == self.CLOSED and self.failure_count > 0:
                    self.failure_count = 0
            return result
        except Exception as e:
            with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.state == self.HALF_OPEN:
                    self.state = self.OPEN
                    logger.warning(f"Circuit {self.name}: HALF_OPEN → OPEN (still failing)")
                elif self.failure_count >= self.failure_threshold:
                    self.state = self.OPEN
                    logger.warning(f"Circuit {self.name}: CLOSED → OPEN ({self.failure_count} failures)")
            if fallback is not None:
                return fallback
            raise

    def status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "threshold": self.failure_threshold,
            "reset_timeout": self.reset_timeout,
        }


# Global circuit breakers for external services
_breakers = {}
_breakers_lock = threading.Lock()


def get_breaker(name: str, **kwargs) -> CircuitBreaker:
    with _breakers_lock:
        if name not in _breakers:
            _breakers[name] = CircuitBreaker(name, **kwargs)
        return _breakers[name]


def all_breaker_statuses() -> list:
    with _breakers_lock:
        return [b.status() for b in _breakers.values()]


class ErrorBoundary:
    """
    Wraps a function call so failures are contained and don't cascade.

    Usage:
        with ErrorBoundary("brain.chat"):
            result = do_risky_thing()

    Or as decorator:
        @error_boundary("brain.chat")
        def handle_chat(payload):
            ...
    """

    def __init__(self, name: str, fallback: Any = None):
        self.name = name
        self.fallback = fallback

    def __enter__(self):
        return self

        if exc_type:
            logger.error(f"ErrorBoundary[{self.name}]: {exc_type.__name__}: {exc_val}")
            try:
                from api._genesis_tracker import track
                track(
                    key_type="error",
                    what=f"ErrorBoundary[{self.name}] caught: {exc_val}",
                    who=f"error_boundary.{self.name}",
                    is_error=True,
                    error_type=exc_type.__name__,
                    error_message=str(exc_val)[:200],
                    tags=["error-boundary", self.name],
                )
            except Exception:
                pass
            return True  # Suppress the exception
        return False


def error_boundary(name: str, fallback: Any = None):
    """Decorator version of ErrorBoundary."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"ErrorBoundary[{name}]: {type(e).__name__}: {e}")
                try:
                    from api._genesis_tracker import track
                    track(
                        key_type="error",
                        what=f"ErrorBoundary[{name}] caught: {e}",
                        who=f"error_boundary.{name}",
                        is_error=True,
                        error_type=type(e).__name__,
                        error_message=str(e)[:200],
                        tags=["error-boundary", name],
                    )
                except Exception:
                    pass
                return fallback
        return wrapper
    return decorator


class GracefulDegradation:
    """
    System-wide degradation level manager.

    Levels:
      FULL       — all services operational
      REDUCED    — non-essential services disabled
      EMERGENCY  — only core chat + health endpoints
      READ_ONLY  — no writes, no mutations
    """

    FULL = "full"
    REDUCED = "reduced"
    EMERGENCY = "emergency"
    READ_ONLY = "read_only"

    _level = FULL
    _lock = threading.Lock()

    @classmethod
    def get_level(cls) -> str:
        return cls._level

    @classmethod
    def set_level(cls, level: str):
        old = cls._level
        cls._level = level
        if old != level:
            logger.warning(f"Degradation level: {old} → {level}")
            try:
                from api._genesis_tracker import track
                track(
                    key_type="system_event",
                    what=f"Degradation level changed: {old} → {level}",
                    who="graceful_degradation",
                    tags=["degradation", level],
                )
            except Exception:
                pass

    @classmethod
    def status(cls) -> dict:
        return {
            "level": cls._level,
            "services": {
                "full": "All services operational",
                "reduced": "Non-essential services disabled",
                "emergency": "Core chat + health only",
                "read_only": "No writes, no mutations",
            },
        }
