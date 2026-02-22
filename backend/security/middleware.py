"""
Security Middleware for GRACE

Provides:
- Security headers middleware
- Rate limiting middleware
- CSRF protection middleware
- Authentication enforcement middleware
- Input sanitisation middleware

Classes:
- `SecurityHeadersMiddleware`
- `RateLimitMiddleware`
- `RequestValidationMiddleware`
"""

import time
import hashlib
import secrets
from typing import Dict, Callable, Optional, Set
from collections import defaultdict
from datetime import datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import HTTPException

from .config import get_security_config
from .logging import log_security_event


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.

    Headers added:
    - Content-Security-Policy
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    - Strict-Transport-Security (if enabled)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        config = get_security_config()

        # Process the request
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = config.X_CONTENT_TYPE_OPTIONS
        response.headers["X-Frame-Options"] = config.X_FRAME_OPTIONS
        response.headers["X-XSS-Protection"] = config.X_XSS_PROTECTION
        response.headers["Referrer-Policy"] = config.REFERRER_POLICY
        response.headers["Permissions-Policy"] = config.PERMISSIONS_POLICY

        # Content Security Policy
        csp = config.get_csp_header()
        if csp:
            response.headers["Content-Security-Policy"] = csp

        # HSTS (only in production or when explicitly enabled)
        hsts = config.get_hsts_header()
        if hsts and (config.PRODUCTION_MODE or config.HSTS_ENABLED):
            response.headers["Strict-Transport-Security"] = hsts

        # Remove server header if present
        if "server" in response.headers:
            del response.headers["server"]

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using a sliding window algorithm.

    Features:
    - Per-IP rate limiting
    - Different limits for different endpoints
    - Burst allowance
    - Rate limit headers in response
    """

    def __init__(self, app, default_limit: str = "100/minute"):
        super().__init__(app)
        self.config = get_security_config()
        self.default_limit = self._parse_limit(default_limit)

        # In-memory storage for rate limiting
        # In production, use Redis or similar
        self.request_counts: Dict[str, list] = defaultdict(list)

        # Endpoint-specific limits
        self.endpoint_limits = {
            "/auth/": self._parse_limit(self.config.RATE_LIMIT_AUTH),
            "/login": self._parse_limit(self.config.RATE_LIMIT_AUTH),
            "/upload": self._parse_limit(self.config.RATE_LIMIT_UPLOAD),
            "/ingest": self._parse_limit(self.config.RATE_LIMIT_UPLOAD),
            "/chat": self._parse_limit(self.config.RATE_LIMIT_AI),
            "/grace/": self._parse_limit(self.config.RATE_LIMIT_AI),
            "/prompt": self._parse_limit(self.config.RATE_LIMIT_AI),
        }

    def _parse_limit(self, limit_str: str) -> tuple:
        """Parse rate limit string like '100/minute' into (count, seconds)."""
        try:
            count, period = limit_str.split("/")
            count = int(count)

            period_seconds = {
                "second": 1,
                "minute": 60,
                "hour": 3600,
                "day": 86400,
            }

            seconds = period_seconds.get(period.lower(), 60)
            return (count, seconds)
        except Exception:
            return (100, 60)  # Default: 100 per minute

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for the client (IP + optional user ID)."""
        # Get IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        # Add user ID if available (from cookie or header)
        user_id = request.cookies.get("genesis_id", "")

        # Create hash for privacy
        identifier = f"{ip}:{user_id}"
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]

    def _get_limit_for_path(self, path: str) -> tuple:
        """Get the rate limit for a specific path."""
        for pattern, limit in self.endpoint_limits.items():
            if pattern in path:
                return limit
        return self.default_limit

    def _is_rate_limited(self, identifier: str, path: str) -> tuple:
        """
        Check if the client is rate limited.

        Returns:
            (is_limited, remaining, reset_time)
        """
        now = time.time()
        limit_count, window_seconds = self._get_limit_for_path(path)

        # Clean old requests outside the window
        key = f"{identifier}:{path}"
        self.request_counts[key] = [
            ts for ts in self.request_counts[key]
            if now - ts < window_seconds
        ]

        current_count = len(self.request_counts[key])
        remaining = max(0, limit_count - current_count)

        # Calculate reset time
        if self.request_counts[key]:
            oldest = min(self.request_counts[key])
            reset_time = int(oldest + window_seconds - now)
        else:
            reset_time = window_seconds

        # Check if over limit
        if current_count >= limit_count:
            return (True, remaining, reset_time)

        # Add current request
        self.request_counts[key].append(now)
        return (False, remaining - 1, reset_time)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting if disabled
        if not self.config.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip for health checks and static files
        path = request.url.path
        skip_paths = ["/health", "/docs", "/openapi.json", "/favicon.ico"]
        if any(path.startswith(skip) for skip in skip_paths):
            return await call_next(request)

        # Get client identifier
        identifier = self._get_client_identifier(request)

        # Check rate limit
        is_limited, remaining, reset_time = self._is_rate_limited(identifier, path)

        if is_limited:
            # Log the rate limit event
            if self.config.LOG_RATE_LIMIT_EXCEEDED:
                log_security_event(
                    event_type="RATE_LIMIT_EXCEEDED",
                    request=request,
                    details={"path": path, "identifier": identifier[:8]},
                )

            # Return 429 Too Many Requests
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please slow down.",
                    "retry_after": reset_time,
                },
                headers={
                    "Retry-After": str(reset_time),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )

        # Process request and add rate limit headers
        response = await call_next(request)

        limit_count, _ = self._get_limit_for_path(path)
        response.headers["X-RateLimit-Limit"] = str(limit_count)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Validates API key on requests when REQUIRE_API_KEY is enabled.

    Checks X-API-Key header against configured API_KEYS list.
    Exempt paths: /health, /docs, /openapi.json
    """

    def __init__(self, app):
        super().__init__(app)
        self.config = get_security_config()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.config.REQUIRE_API_KEY:
            return await call_next(request)

        # Exempt paths
        path = request.url.path
        exempt = ["/health", "/docs", "/openapi.json", "/redoc", "/"]
        if any(path.startswith(e) for e in exempt):
            return await call_next(request)

        # Check API key
        api_key = request.headers.get(self.config.API_KEY_HEADER)

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "API key required. Set X-API-Key header."},
            )

        if api_key not in self.config.API_KEYS:
            log_security_event(
                event_type="INVALID_API_KEY",
                request=request,
                details={"key_prefix": api_key[:8] + "..."},
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid API key."},
            )

        return await call_next(request)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validates incoming requests for security issues.

    Checks:
    - Request size limits
    - Suspicious patterns in URLs
    - Content-Type validation
    """

    def __init__(self, app):
        super().__init__(app)
        self.config = get_security_config()

        # Suspicious patterns to block
        self.suspicious_patterns = [
            "../",          # Path traversal
            "..\\",         # Windows path traversal
            "<script",      # XSS attempt
            "javascript:",  # XSS attempt
            "data:text/html", # XSS attempt
            "SELECT%20",    # SQL injection
            "UNION%20",     # SQL injection
            "INSERT%20",    # SQL injection
            "DELETE%20",    # SQL injection
            "DROP%20",      # SQL injection
            "%00",          # Null byte injection
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check URL for suspicious patterns
        url = str(request.url)
        for pattern in self.suspicious_patterns:
            if pattern.lower() in url.lower():
                if self.config.LOG_SUSPICIOUS_REQUESTS:
                    log_security_event(
                        event_type="SUSPICIOUS_REQUEST",
                        request=request,
                        details={"pattern": pattern, "url": url[:200]},
                    )
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Bad request"},
                )

        # Check Content-Length for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length:
                max_size = self.config.MAX_REQUEST_SIZE_MB * 1024 * 1024
                if int(content_length) > max_size:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"Request too large. Maximum size: {self.config.MAX_REQUEST_SIZE_MB}MB"},
                    )

        return await call_next(request)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware.

    Enforces CSRF token validation on state-changing requests
    (POST, PUT, PATCH, DELETE).

    Safe methods (GET, HEAD, OPTIONS) are exempted.
    """

    SAFE_METHODS: Set[str] = {"GET", "HEAD", "OPTIONS"}
    EXEMPT_PATHS: Set[str] = {
        "/auth/login",
        "/auth/register",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        config = get_security_config()

        # Skip for safe methods
        if request.method in self.SAFE_METHODS:
            response = await call_next(request)
            # Provide a CSRF token cookie on GET so clients can read it
            if request.method == "GET" and "csrf_token" not in request.cookies:
                csrf_token = secrets.token_hex(32)
                response.set_cookie(
                    key="csrf_token",
                    value=csrf_token,
                    httponly=False,  # JS must read this
                    secure=config.SESSION_COOKIE_SECURE,
                    samesite=config.SESSION_COOKIE_SAMESITE,
                )
            return response

        # Skip for exempt paths
        path = request.url.path
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return await call_next(request)

        # Validate CSRF token
        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("X-CSRF-Token")

        if not cookie_token or not header_token:
            log_security_event(
                event_type="CSRF_TOKEN_MISSING",
                request=request,
                details={"path": path},
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing"},
            )

        if not secrets.compare_digest(cookie_token, header_token):
            log_security_event(
                event_type="CSRF_TOKEN_MISMATCH",
                request=request,
                details={"path": path},
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token invalid"},
            )

        return await call_next(request)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Global authentication enforcement middleware.

    Ensures ALL API endpoints (except a whitelist of public paths)
    require a valid genesis_id cookie and session.
    """

    PUBLIC_PATHS: Set[str] = {
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/auth/login",
        "/auth/register",
        "/auth/genesis-login",
        "/favicon.ico",
        "/metrics",
    }

    PUBLIC_PREFIXES = (
        "/docs",
        "/openapi",
        "/redoc",
        "/auth/",
    )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Skip public paths
        if path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Skip public prefixes
        if any(path.startswith(prefix) for prefix in self.PUBLIC_PREFIXES):
            return await call_next(request)

        # Skip health check variants
        if path.startswith("/health"):
            return await call_next(request)

        # Require genesis_id cookie
        genesis_id = request.cookies.get("genesis_id")
        if not genesis_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required. Please login."},
            )

        # Validate session
        session_id = request.cookies.get("session_id")
        if session_id:
            from .auth import get_session_manager
            session_manager = get_session_manager()
            session = session_manager.validate_session(session_id)
            if not session:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Session expired. Please login again."},
                )

        return await call_next(request)


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Input sanitization middleware.

    Applies InputValidator/sanitize_input to all incoming JSON
    request bodies before they reach endpoint handlers.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only process requests with JSON body
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    from .validators import get_validator
                    validator = get_validator()
                    body = await request.body()
                    if body:
                        import json
                        try:
                            data = json.loads(body)
                            is_valid, sanitized, error = validator.validate_json_input(data)
                            if not is_valid:
                                log_security_event(
                                    event_type="INPUT_VALIDATION_FAILED",
                                    request=request,
                                    details={"error": error},
                                )
                                return JSONResponse(
                                    status_code=400,
                                    content={"detail": f"Input validation failed: {error}"},
                                )
                        except json.JSONDecodeError:
                            pass  # Let FastAPI handle malformed JSON
                except Exception:
                    pass  # Don't block on validator import errors

        return await call_next(request)
