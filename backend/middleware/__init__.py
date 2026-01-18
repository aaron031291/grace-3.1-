"""
Middleware Package - Self-Healing, Authentication, and Error Learning Integration

This package provides middleware components for:
- Automatic error capture and self-healing integration
- API authentication (API Key and JWT)
- Rate limiting
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

from middleware.authentication import (
    AuthenticationMiddleware,
    add_authentication_middleware,
    require_auth,
    optional_auth,
    RateLimiter,
    get_rate_limiter,
    validate_api_key,
    decode_jwt,
    create_jwt,
    get_current_user,
    require_permission,
    is_public_route,
    PUBLIC_ROUTES
)

__all__ = [
    # Self-healing middleware
    "SelfHealingMiddleware",
    "add_self_healing_middleware",
    "self_healing_endpoint",
    "cache_error_handler",
    "database_error_handler",
    "test_runner_error_handler",
    "get_error_pattern_stats",
    "reset_error_patterns",
    "classify_severity",
    "ErrorPatternTracker",
    # Authentication middleware
    "AuthenticationMiddleware",
    "add_authentication_middleware",
    "require_auth",
    "optional_auth",
    "RateLimiter",
    "get_rate_limiter",
    "validate_api_key",
    "decode_jwt",
    "create_jwt",
    "get_current_user",
    "require_permission",
    "is_public_route",
    "PUBLIC_ROUTES"
]
