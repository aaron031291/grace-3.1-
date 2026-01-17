"""
Optional Authentication Middleware for GRACE

Provides configurable authentication enforcement for API endpoints.
Can be enabled/disabled via security configuration.
"""

import logging
from typing import List, Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

from .config import get_security_config
from .auth import get_current_user
from .logging import get_security_logger

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Optional authentication middleware.
    
    When enabled, requires authentication for all endpoints except:
    - Public endpoints (health checks, docs, auth endpoints)
    - Endpoints explicitly marked as public
    
    Configuration:
    - Set AUTH_REQUIRED=True in security config to enable
    - Set AUTH_PUBLIC_ENDPOINTS to list of public paths
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.config = get_security_config()
        self.security_logger = get_security_logger()
        
        # Public endpoints that don't require authentication
        self.public_endpoints = [
            "/health",
            "/health/live",
            "/health/ready",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/",
            "/version",
            "/auth/login",
            "/auth/logout",
            "/auth/whoami",
        ]
        
        # Add configured public endpoints
        if hasattr(self.config, 'AUTH_PUBLIC_ENDPOINTS'):
            self.public_endpoints.extend(self.config.AUTH_PUBLIC_ENDPOINTS)
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Check authentication if enabled."""
        
        # Skip if authentication not required
        if not getattr(self.config, 'AUTH_REQUIRED', False):
            return await call_next(request)
        
        # Skip public endpoints
        if request.url.path in self.public_endpoints or any(
            request.url.path.startswith(public) for public in self.public_endpoints
        ):
            return await call_next(request)
        
        # Check authentication
        try:
            # Try to get current user
            genesis_id = request.cookies.get("genesis_id")
            session_id = request.cookies.get("session_id")
            
            if not genesis_id:
                # Check header as fallback
                genesis_id = request.headers.get("X-Genesis-ID")
            
            if not genesis_id:
                self.security_logger.log_access_denied(
                    "API",
                    request,
                    "No authentication credentials"
                )
                return JSONResponse(
                    status_code=HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Authentication required",
                        "message": "Please login at /auth/login to get a Genesis ID",
                        "login_url": "/auth/login"
                    },
                    headers={"WWW-Authenticate": "Cookie"}
                )
            
            # Validate session if session_id provided
            if session_id:
                from .auth import get_session_manager
                session_manager = get_session_manager()
                session = session_manager.validate_session(session_id)
                if not session:
                    self.security_logger.log_access_denied(
                        "API",
                        request,
                        "Invalid or expired session"
                    )
                    return JSONResponse(
                        status_code=HTTP_401_UNAUTHORIZED,
                        content={
                            "error": "Session expired",
                            "message": "Please login again at /auth/login"
                        }
                    )
            
            # Add user info to request state
            request.state.genesis_id = genesis_id
            request.state.session_id = session_id
            request.state.authenticated = True
            
        except HTTPException:
            # Re-raise HTTP exceptions (like from get_current_user)
            raise
        except Exception as e:
            logger.warning(f"[AUTH-MIDDLEWARE] Authentication check failed: {e}")
            # In case of error, allow request but log it
            request.state.authenticated = False
        
        return await call_next(request)
