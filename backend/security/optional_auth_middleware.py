"""
Optional authentication middleware for FastAPI.

This middleware can be enabled/disabled via environment variable.
When enabled, it requires authentication for all endpoints except
health checks and public endpoints.

Usage:
    Set ENABLE_AUTHENTICATION=true in .env to enable
    Set ENABLE_AUTHENTICATION=false (or omit) to disable (default)
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import os
import logging

logger = logging.getLogger(__name__)

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = {
    "/health",
    "/metrics",
    "/auth/login",
    "/auth/session",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class OptionalAuthMiddleware(BaseHTTPMiddleware):
    """
    Optional authentication middleware.
    
    Checks for authentication token in cookies or headers.
    Can be enabled/disabled via ENABLE_AUTHENTICATION environment variable.
    """
    
    def __init__(self, app: ASGIApp, enabled: bool = None):
        """
        Initialize middleware.
        
        Args:
            app: ASGI application
            enabled: Whether authentication is enabled (defaults to env var)
        """
        super().__init__(app)
        if enabled is None:
            enabled = os.getenv("ENABLE_AUTHENTICATION", "false").lower() == "true"
        self.enabled = enabled
        
        if self.enabled:
            logger.info("[AUTH] Authentication middleware ENABLED - endpoints require authentication")
        else:
            logger.info("[AUTH] Authentication middleware DISABLED - endpoints are public")
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and check authentication if enabled.
        """
        # Skip authentication if disabled
        if not self.enabled:
            return await call_next(request)
        
        # Skip authentication for public endpoints
        if request.url.path in PUBLIC_ENDPOINTS or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
            return await call_next(request)
        
        # Check for session cookie or authorization header
        session_id = request.cookies.get("session_id")
        auth_header = request.headers.get("Authorization")
        
        # For now, allow requests with any session_id or Authorization header
        # In production, validate the session/token here
        if session_id or auth_header:
            return await call_next(request)
        
        # No authentication provided - return 401
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Authentication required",
                "message": "Please login at /auth/login to get a session",
                "login_endpoint": "/auth/login"
            }
        )
