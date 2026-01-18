"""
Middleware Package - Self-Healing and Error Learning Integration

This package provides middleware components for automatic error capture
and self-healing integration across all API endpoints.
"""

from middleware.self_healing_middleware import (
    SelfHealingMiddleware,
    add_self_healing_middleware,
    self_healing_endpoint,
    cache_error_handler,
    database_error_handler,
    test_runner_error_handler,
    get_error_pattern_stats,
    reset_error_patterns,
    classify_severity,
    ErrorPatternTracker
)

__all__ = [
    "SelfHealingMiddleware",
    "add_self_healing_middleware",
    "self_healing_endpoint",
    "cache_error_handler",
    "database_error_handler",
    "test_runner_error_handler",
    "get_error_pattern_stats",
    "reset_error_patterns",
    "classify_severity",
    "ErrorPatternTracker"
]
