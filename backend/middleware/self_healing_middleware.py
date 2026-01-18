"""
Self-Healing Middleware - Automatic Error Learning Integration

This middleware automatically captures all API errors and feeds them into
Grace's self-healing and learning pipelines without requiring manual
integration in each endpoint.

Features:
1. Automatic error capture from all API endpoints
2. Pattern recognition for recurring errors
3. Severity classification based on error type and frequency
4. Integration with Genesis Keys, Learning Memory, and Healing System
5. Decorator for additional context on specific endpoints
"""

import logging
import traceback
import functools
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# ==================== Error Pattern Tracking ====================

class ErrorPatternTracker:
    """
    Tracks error patterns to detect recurring issues and escalate severity.
    """
    
    def __init__(self, window_minutes: int = 60, escalation_threshold: int = 3):
        self.window_minutes = window_minutes
        self.escalation_threshold = escalation_threshold
        self._error_counts: Dict[str, List[datetime]] = defaultdict(list)
        self._lock = None  # Lock created lazily when needed in async context
    
    def _get_error_key(self, component: str, error_type: str) -> str:
        """Generate unique key for error pattern."""
        return f"{component}:{error_type}"
    
    def _cleanup_old_errors(self, key: str) -> None:
        """Remove errors outside the time window."""
        cutoff = datetime.now() - timedelta(minutes=self.window_minutes)
        self._error_counts[key] = [
            ts for ts in self._error_counts[key] if ts > cutoff
        ]
    
    def record_error(self, component: str, error_type: str) -> int:
        """Record an error and return the count in the current window."""
        key = self._get_error_key(component, error_type)
        self._cleanup_old_errors(key)
        self._error_counts[key].append(datetime.now())
        return len(self._error_counts[key])
    
    def should_escalate(self, component: str, error_type: str) -> bool:
        """Check if error pattern should escalate severity."""
        key = self._get_error_key(component, error_type)
        self._cleanup_old_errors(key)
        return len(self._error_counts[key]) >= self.escalation_threshold
    
    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get current error pattern statistics."""
        stats = {}
        for key, timestamps in self._error_counts.items():
            self._cleanup_old_errors(key)
            if self._error_counts[key]:
                stats[key] = {
                    "count": len(self._error_counts[key]),
                    "first_seen": min(self._error_counts[key]).isoformat(),
                    "last_seen": max(self._error_counts[key]).isoformat(),
                    "escalated": len(self._error_counts[key]) >= self.escalation_threshold
                }
        return stats


# Global pattern tracker
_pattern_tracker = ErrorPatternTracker()


# ==================== Severity Classification ====================

SEVERITY_MAP = {
    # Critical - system-wide impact
    "DatabaseError": "critical",
    "ConnectionError": "critical",
    "MemoryError": "critical",
    "SystemExit": "critical",
    
    # High - significant impact
    "TimeoutError": "high",
    "AuthenticationError": "high",
    "PermissionError": "high",
    "IntegrityError": "high",
    
    # Medium - standard errors
    "ValueError": "medium",
    "KeyError": "medium",
    "TypeError": "medium",
    "AttributeError": "medium",
    "HTTPException": "medium",
    
    # Low - expected/handled errors
    "ValidationError": "low",
    "NotFoundError": "low",
    "FileNotFoundError": "low",
}


def classify_severity(error: Exception, component: str) -> str:
    """
    Classify error severity based on error type and patterns.
    """
    error_type = type(error).__name__
    
    # Check if pattern should escalate
    if _pattern_tracker.should_escalate(component, error_type):
        # Escalate by one level
        base_severity = SEVERITY_MAP.get(error_type, "medium")
        escalation = {"low": "medium", "medium": "high", "high": "critical"}
        return escalation.get(base_severity, "critical")
    
    return SEVERITY_MAP.get(error_type, "medium")


# ==================== Self-Healing Middleware ====================

class SelfHealingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that automatically captures errors and feeds them
    to the self-healing pipeline.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        excluded_paths: Optional[List[str]] = None,
        min_severity: str = "low"
    ):
        """
        Initialize self-healing middleware.
        
        Args:
            app: FastAPI application
            excluded_paths: Paths to exclude from error tracking (e.g., /health)
            min_severity: Minimum severity to record (low, medium, high, critical)
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.min_severity = min_severity
        self._error_learning = None
        self._session_factory = None
    
    def _get_error_learning(self):
        """Lazy load error learning integration."""
        if self._error_learning is None:
            try:
                from cognitive.error_learning_integration import get_error_learning_integration
                from database.session import SessionLocal
                self._session_factory = SessionLocal
                session = self._session_factory()
                self._error_learning = get_error_learning_integration(session=session)
            except Exception as e:
                logger.warning(f"[SELF-HEALING-MIDDLEWARE] Could not initialize: {e}")
        return self._error_learning
    
    def _should_track(self, path: str) -> bool:
        """Check if path should be tracked for errors."""
        return not any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    def _extract_component(self, path: str) -> str:
        """Extract component name from request path."""
        parts = path.strip("/").split("/")
        if len(parts) >= 1:
            return f"api.{parts[0]}"
        return "api.unknown"
    
    def _severity_meets_threshold(self, severity: str) -> bool:
        """Check if severity meets minimum threshold."""
        levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        return levels.get(severity, 1) >= levels.get(self.min_severity, 0)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and capture any errors."""
        path = request.url.path
        
        # Skip excluded paths
        if not self._should_track(path):
            return await call_next(request)
        
        start_time = datetime.now()
        component = self._extract_component(path)
        
        try:
            response = await call_next(request)
            
            # Track 5xx errors even if they don't raise exceptions
            if response.status_code >= 500:
                await self._record_http_error(
                    request=request,
                    component=component,
                    status_code=response.status_code,
                    start_time=start_time
                )
            
            return response
            
        except Exception as e:
            # Record the error
            await self._record_exception(
                request=request,
                error=e,
                component=component,
                start_time=start_time
            )
            
            # Re-raise to let FastAPI handle the response
            raise
    
    async def _record_exception(
        self,
        request: Request,
        error: Exception,
        component: str,
        start_time: datetime
    ) -> None:
        """Record an exception to the self-healing pipeline."""
        try:
            error_type = type(error).__name__
            severity = classify_severity(error, component)
            
            # Track pattern
            _pattern_tracker.record_error(component, error_type)
            
            # Check if meets threshold
            if not self._severity_meets_threshold(severity):
                return
            
            # Get error learning integration
            error_learning = self._get_error_learning()
            if not error_learning:
                return
            
            # Build context
            context = {
                "location": component,
                "reason": f"API error in {request.method} {request.url.path}",
                "method": f"{request.method} {request.url.path}",
                "query_params": dict(request.query_params),
                "path_params": dict(request.path_params) if hasattr(request, 'path_params') else {},
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "client_host": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "pattern_count": _pattern_tracker.record_error(component, error_type)
            }
            
            # Record error
            error_learning.record_error(
                error=error,
                context=context,
                component=component,
                severity=severity
            )
            
            logger.info(
                f"[SELF-HEALING-MIDDLEWARE] Recorded {severity} error in {component}: "
                f"{error_type}"
            )
            
        except Exception as record_error:
            logger.warning(f"[SELF-HEALING-MIDDLEWARE] Failed to record error: {record_error}")
    
    async def _record_http_error(
        self,
        request: Request,
        component: str,
        status_code: int,
        start_time: datetime
    ) -> None:
        """Record an HTTP 5xx error."""
        try:
            error_type = f"HTTP{status_code}"
            severity = "high" if status_code >= 500 else "medium"
            
            # Track pattern
            _pattern_tracker.record_error(component, error_type)
            
            error_learning = self._get_error_learning()
            if not error_learning:
                return
            
            # Create synthetic error for tracking
            class HTTPStatusError(Exception):
                pass
            
            error = HTTPStatusError(f"HTTP {status_code} response")
            
            context = {
                "location": component,
                "reason": f"HTTP {status_code} in {request.method} {request.url.path}",
                "method": f"{request.method} {request.url.path}",
                "status_code": status_code,
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
            }
            
            error_learning.record_error(
                error=error,
                context=context,
                component=component,
                severity=severity
            )
            
        except Exception as e:
            logger.warning(f"[SELF-HEALING-MIDDLEWARE] Failed to record HTTP error: {e}")


# ==================== Decorator for Enhanced Context ====================

def self_healing_endpoint(
    component: Optional[str] = None,
    severity_override: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
):
    """
    Decorator for API endpoints that provides enhanced error context
    to the self-healing system.
    
    Usage:
        @router.get("/items/{item_id}")
        @self_healing_endpoint(component="inventory", severity_override="high")
        async def get_item(item_id: int):
            ...
    
    Args:
        component: Override component name (defaults to function name)
        severity_override: Force specific severity level
        additional_context: Extra context to include in error reports
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_component = component or f"api.{func.__name__}"
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Enhanced error recording
                try:
                    from cognitive.error_learning_integration import get_error_learning_integration
                    from database.session import SessionLocal
                    
                    session = SessionLocal()
                    try:
                        error_learning = get_error_learning_integration(session=session)
                        
                        severity = severity_override or classify_severity(e, func_component)
                        
                        context = {
                            "location": func_component,
                            "reason": f"Error in {func.__name__}",
                            "method": func.__name__,
                            "args": str(args)[:200],
                            "kwargs_keys": list(kwargs.keys()),
                            **(additional_context or {})
                        }
                        
                        error_learning.record_error(
                            error=e,
                            context=context,
                            component=func_component,
                            severity=severity
                        )
                    finally:
                        session.close()
                except Exception:
                    pass
                
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_component = component or f"api.{func.__name__}"
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Enhanced error recording
                try:
                    from cognitive.error_learning_integration import get_error_learning_integration
                    from database.session import SessionLocal
                    
                    session = SessionLocal()
                    try:
                        error_learning = get_error_learning_integration(session=session)
                        
                        severity = severity_override or classify_severity(e, func_component)
                        
                        context = {
                            "location": func_component,
                            "reason": f"Error in {func.__name__}",
                            "method": func.__name__,
                            "args": str(args)[:200],
                            "kwargs_keys": list(kwargs.keys()),
                            **(additional_context or {})
                        }
                        
                        error_learning.record_error(
                            error=e,
                            context=context,
                            component=func_component,
                            severity=severity
                        )
                    finally:
                        session.close()
                except Exception:
                    pass
                
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# ==================== Component-Specific Wrappers ====================

def cache_error_handler(func: Callable):
    """
    Decorator for cache operations that records failures to self-healing.
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            try:
                from cognitive.error_learning_integration import get_error_learning_integration
                from database.session import SessionLocal
                
                session = SessionLocal()
                try:
                    error_learning = get_error_learning_integration(session=session)
                    error_learning.record_error(
                        error=e,
                        context={
                            "location": "cache.redis",
                            "reason": f"Cache operation failed: {func.__name__}",
                            "method": func.__name__
                        },
                        component="cache.redis",
                        severity="medium"
                    )
                finally:
                    session.close()
            except Exception:
                pass
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            try:
                from cognitive.error_learning_integration import get_error_learning_integration
                from database.session import SessionLocal
                
                session = SessionLocal()
                try:
                    error_learning = get_error_learning_integration(session=session)
                    error_learning.record_error(
                        error=e,
                        context={
                            "location": "cache.redis",
                            "reason": f"Cache operation failed: {func.__name__}",
                            "method": func.__name__
                        },
                        component="cache.redis",
                        severity="medium"
                    )
                finally:
                    session.close()
            except Exception:
                pass
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def database_error_handler(func: Callable):
    """
    Decorator for database operations that records failures to self-healing.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            try:
                from cognitive.error_learning_integration import get_error_learning_integration
                from database.session import SessionLocal
                
                session = SessionLocal()
                try:
                    error_learning = get_error_learning_integration(session=session)
                    error_learning.record_error(
                        error=e,
                        context={
                            "location": "database.session",
                            "reason": f"Database operation failed: {func.__name__}",
                            "method": func.__name__
                        },
                        component="database.session",
                        severity="critical"
                    )
                finally:
                    session.close()
            except Exception:
                pass
            raise
    
    return wrapper


def test_runner_error_handler(func: Callable):
    """
    Decorator for test runner operations that records failures to self-healing.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            try:
                from cognitive.error_learning_integration import get_error_learning_integration
                from database.session import SessionLocal
                
                session = SessionLocal()
                try:
                    error_learning = get_error_learning_integration(session=session)
                    error_learning.record_error(
                        error=e,
                        context={
                            "location": "test_runner",
                            "reason": f"Test execution failed: {func.__name__}",
                            "method": func.__name__
                        },
                        component="test_runner",
                        severity="high"
                    )
                finally:
                    session.close()
            except Exception:
                pass
            raise
    
    return wrapper


# ==================== Utility Functions ====================

def get_error_pattern_stats() -> Dict[str, Any]:
    """Get current error pattern statistics."""
    return _pattern_tracker.get_pattern_stats()


def reset_error_patterns() -> None:
    """Reset error pattern tracking (for testing)."""
    global _pattern_tracker
    _pattern_tracker = ErrorPatternTracker()


# ==================== FastAPI Integration ====================

def add_self_healing_middleware(
    app,
    excluded_paths: Optional[List[str]] = None,
    min_severity: str = "low"
) -> None:
    """
    Add self-healing middleware to a FastAPI application.
    
    Usage:
        from middleware.self_healing_middleware import add_self_healing_middleware
        
        app = FastAPI()
        add_self_healing_middleware(app)
    
    Args:
        app: FastAPI application instance
        excluded_paths: Paths to exclude from tracking
        min_severity: Minimum severity to record
    """
    app.add_middleware(
        SelfHealingMiddleware,
        excluded_paths=excluded_paths,
        min_severity=min_severity
    )
    logger.info("[SELF-HEALING-MIDDLEWARE] Added to FastAPI application")
