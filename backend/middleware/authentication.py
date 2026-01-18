"""
Authentication Middleware - API Key and JWT Authentication for Grace API

This middleware provides authentication and rate limiting for the Grace API.

Features:
1. API Key authentication via X-API-Key header or api_key query parameter
2. JWT authentication via Authorization: Bearer <token> header
3. FastAPI dependencies for route protection (require_auth, optional_auth)
4. Public routes whitelist for health/docs endpoints
5. Basic in-memory rate limiting per API key

Environment Variables:
- GRACE_API_KEY: Single API key for authentication
- GRACE_API_KEYS: Comma-separated list of valid API keys
- GRACE_JWT_SECRET: Secret for JWT token validation
- GRACE_RATE_LIMIT: Requests per minute limit (default: 100)
"""

import os
import time
import logging
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps

from fastapi import Request, Response, HTTPException, Depends
from fastapi.security import APIKeyHeader, APIKeyQuery, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# ==================== Configuration ====================

def get_api_keys() -> List[str]:
    """Get valid API keys from environment variables."""
    keys = []
    
    single_key = os.getenv("GRACE_API_KEY", "")
    if single_key:
        keys.append(single_key)
    
    multiple_keys = os.getenv("GRACE_API_KEYS", "")
    if multiple_keys:
        keys.extend([k.strip() for k in multiple_keys.split(",") if k.strip()])
    
    return keys


def get_jwt_secret() -> Optional[str]:
    """Get JWT secret from environment variable."""
    return os.getenv("GRACE_JWT_SECRET")


def get_rate_limit() -> int:
    """Get rate limit from environment variable (requests per minute)."""
    try:
        return int(os.getenv("GRACE_RATE_LIMIT", "100"))
    except ValueError:
        return 100


PUBLIC_ROUTES = [
    "/health",
    "/healthz", 
    "/ready",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
]


# ==================== Rate Limiter ====================

class RateLimiter:
    """
    Simple in-memory rate limiter that tracks requests per API key.
    
    Uses a sliding window algorithm to track requests within the time window.
    """
    
    def __init__(self, requests_per_minute: int = 100, window_seconds: int = 60):
        """
        Initialize the rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
            window_seconds: Time window in seconds (default: 60)
        """
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)
    
    def _get_key_hash(self, api_key: str) -> str:
        """Hash API key for storage (don't store raw keys)."""
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    def _cleanup_old_requests(self, key_hash: str) -> None:
        """Remove requests outside the time window."""
        cutoff = time.time() - self.window_seconds
        self._requests[key_hash] = [
            ts for ts in self._requests[key_hash] if ts > cutoff
        ]
    
    def is_allowed(self, api_key: str) -> Tuple[bool, int, int]:
        """
        Check if request is allowed and record it.
        
        Args:
            api_key: The API key making the request
            
        Returns:
            Tuple of (allowed: bool, remaining: int, reset_in: int)
        """
        key_hash = self._get_key_hash(api_key)
        self._cleanup_old_requests(key_hash)
        
        current_count = len(self._requests[key_hash])
        remaining = max(0, self.requests_per_minute - current_count)
        reset_in = self.window_seconds
        
        if current_count >= self.requests_per_minute:
            if self._requests[key_hash]:
                oldest = min(self._requests[key_hash])
                reset_in = int(oldest + self.window_seconds - time.time())
            return False, 0, reset_in
        
        self._requests[key_hash].append(time.time())
        return True, remaining - 1, reset_in
    
    def get_usage(self, api_key: str) -> Dict[str, Any]:
        """Get current usage stats for an API key."""
        key_hash = self._get_key_hash(api_key)
        self._cleanup_old_requests(key_hash)
        
        current_count = len(self._requests[key_hash])
        return {
            "requests_used": current_count,
            "requests_limit": self.requests_per_minute,
            "requests_remaining": max(0, self.requests_per_minute - current_count),
            "window_seconds": self.window_seconds
        }
    
    def reset(self, api_key: Optional[str] = None) -> None:
        """Reset rate limit tracking (for testing)."""
        if api_key:
            key_hash = self._get_key_hash(api_key)
            self._requests[key_hash] = []
        else:
            self._requests.clear()


# Global rate limiter instance
_rate_limiter = RateLimiter(requests_per_minute=get_rate_limit())


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter


# ==================== JWT Utilities ====================

def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        Decoded payload if valid, None otherwise
    """
    secret = get_jwt_secret()
    if not secret:
        logger.warning("[AUTH] JWT secret not configured")
        return None
    
    try:
        import jwt
        
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat"]}
        )
        
        return payload
        
    except ImportError:
        logger.warning("[AUTH] PyJWT not installed, JWT authentication disabled")
        return None
    except jwt.ExpiredSignatureError:
        logger.debug("[AUTH] JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"[AUTH] Invalid JWT token: {e}")
        return None


def create_jwt(subject: str, expires_in: int = 3600, extra_claims: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Create a JWT token for a subject.
    
    Args:
        subject: The subject (user ID, API key name, etc.)
        expires_in: Token lifetime in seconds (default: 1 hour)
        extra_claims: Additional claims to include
        
    Returns:
        JWT token string if successful, None otherwise
    """
    secret = get_jwt_secret()
    if not secret:
        logger.warning("[AUTH] JWT secret not configured")
        return None
    
    try:
        import jwt
        
        now = datetime.utcnow()
        payload = {
            "sub": subject,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
            **(extra_claims or {})
        }
        
        return jwt.encode(payload, secret, algorithm="HS256")
        
    except ImportError:
        logger.warning("[AUTH] PyJWT not installed")
        return None


# ==================== Authentication Functions ====================

def validate_api_key(api_key: str) -> bool:
    """Validate an API key against configured keys."""
    valid_keys = get_api_keys()
    
    if not valid_keys:
        return True
    
    return api_key in valid_keys


def extract_auth_from_request(request: Request) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract authentication credentials from request.
    
    Returns:
        Tuple of (auth_type, credential) where auth_type is 'api_key' or 'jwt'
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return ("api_key", api_key)
    
    api_key = request.query_params.get("api_key")
    if api_key:
        return ("api_key", api_key)
    
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return ("jwt", token)
    
    return (None, None)


def is_public_route(path: str) -> bool:
    """Check if path is a public route that doesn't require authentication."""
    for public_path in PUBLIC_ROUTES:
        if path == public_path or path.startswith(public_path + "/"):
            return True
    return False


async def authenticate_request(request: Request) -> Optional[Dict[str, Any]]:
    """
    Authenticate a request and return user info.
    
    Args:
        request: The FastAPI request
        
    Returns:
        User info dict if authenticated, None otherwise
    """
    auth_type, credential = extract_auth_from_request(request)
    
    if not auth_type:
        return None
    
    if auth_type == "api_key":
        if validate_api_key(credential):
            return {
                "auth_type": "api_key",
                "api_key": credential[:8] + "..." if len(credential) > 8 else credential,
                "authenticated": True
            }
        return None
    
    elif auth_type == "jwt":
        payload = decode_jwt(credential)
        if payload:
            return {
                "auth_type": "jwt",
                "sub": payload.get("sub"),
                "exp": payload.get("exp"),
                "claims": payload,
                "authenticated": True
            }
        return None
    
    return None


# ==================== FastAPI Dependencies ====================

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def require_auth(
    request: Request,
    api_key_header_val: Optional[str] = Depends(api_key_header),
    api_key_query_val: Optional[str] = Depends(api_key_query),
    bearer_token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Dict[str, Any]:
    """
    FastAPI dependency that requires authentication.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(require_auth)):
            return {"user": user}
    
    Raises:
        HTTPException: 401 if not authenticated, 429 if rate limited
    """
    if not get_api_keys() and not get_jwt_secret():
        return {
            "auth_type": "none",
            "authenticated": True,
            "note": "Authentication not configured"
        }
    
    user = await authenticate_request(request)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer, ApiKey"}
        )
    
    api_key = api_key_header_val or api_key_query_val
    if api_key:
        allowed, remaining, reset_in = _rate_limiter.is_allowed(api_key)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {reset_in} seconds.",
                headers={
                    "X-RateLimit-Limit": str(_rate_limiter.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_in),
                    "Retry-After": str(reset_in)
                }
            )
        user["rate_limit"] = {
            "remaining": remaining,
            "limit": _rate_limiter.requests_per_minute
        }
    
    return user


async def optional_auth(
    request: Request,
    api_key_header_val: Optional[str] = Depends(api_key_header),
    api_key_query_val: Optional[str] = Depends(api_key_query),
    bearer_token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency that optionally authenticates.
    
    Returns user info if authenticated, None if not.
    Does not raise exceptions for missing/invalid auth.
    
    Usage:
        @app.get("/optional")
        async def optional_route(user: Optional[dict] = Depends(optional_auth)):
            if user:
                return {"message": f"Hello, {user.get('sub', 'user')}"}
            return {"message": "Hello, anonymous"}
    """
    return await authenticate_request(request)


# ==================== ASGI Middleware ====================

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware for request authentication.
    
    Checks authentication on all non-public routes and adds rate limiting.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[List[str]] = None,
        require_auth_by_default: bool = False
    ):
        """
        Initialize authentication middleware.
        
        Args:
            app: ASGI application
            exclude_paths: Additional paths to exclude from auth checks
            require_auth_by_default: If True, require auth on all non-public routes
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
        self.require_auth_by_default = require_auth_by_default
        self._public_routes = PUBLIC_ROUTES + self.exclude_paths
    
    def _is_excluded(self, path: str) -> bool:
        """Check if path should skip authentication."""
        for excluded in self._public_routes:
            if path == excluded or path.startswith(excluded + "/"):
                return True
        return False
    
    def _create_error_response(self, status_code: int, detail: str, headers: Optional[Dict[str, str]] = None) -> JSONResponse:
        """Create a JSON error response."""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": True,
                "status_code": status_code,
                "detail": detail,
                "timestamp": datetime.utcnow().isoformat()
            },
            headers=headers
        )
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through authentication middleware."""
        path = request.url.path
        
        if self._is_excluded(path):
            return await call_next(request)
        
        if not get_api_keys() and not get_jwt_secret():
            return await call_next(request)
        
        user = await authenticate_request(request)
        
        if self.require_auth_by_default and not user:
            return self._create_error_response(
                401,
                "Authentication required",
                {"WWW-Authenticate": "Bearer, ApiKey"}
            )
        
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if api_key and user:
            allowed, remaining, reset_in = _rate_limiter.is_allowed(api_key)
            if not allowed:
                return self._create_error_response(
                    429,
                    f"Rate limit exceeded. Try again in {reset_in} seconds.",
                    {
                        "X-RateLimit-Limit": str(_rate_limiter.requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_in),
                        "Retry-After": str(reset_in)
                    }
                )
        
        request.state.user = user
        
        response = await call_next(request)
        
        if api_key and user:
            usage = _rate_limiter.get_usage(api_key)
            response.headers["X-RateLimit-Limit"] = str(usage["requests_limit"])
            response.headers["X-RateLimit-Remaining"] = str(usage["requests_remaining"])
        
        return response


# ==================== FastAPI Integration ====================

def add_authentication_middleware(
    app,
    exclude_paths: Optional[List[str]] = None,
    require_auth_by_default: bool = False
) -> None:
    """
    Add authentication middleware to a FastAPI application.
    
    Usage:
        from middleware.authentication import add_authentication_middleware
        
        app = FastAPI()
        add_authentication_middleware(app, require_auth_by_default=True)
    
    Args:
        app: FastAPI application instance
        exclude_paths: Additional paths to exclude from auth
        require_auth_by_default: Require auth on all non-public routes
    """
    app.add_middleware(
        AuthenticationMiddleware,
        exclude_paths=exclude_paths,
        require_auth_by_default=require_auth_by_default
    )
    logger.info("[AUTH-MIDDLEWARE] Added to FastAPI application")


# ==================== Utility Functions ====================

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get the current authenticated user from request state.
    
    Use this in route handlers after middleware has run.
    """
    return getattr(request.state, "user", None)


def require_permission(permission: str):
    """
    Decorator factory for permission-based access control.
    
    Usage:
        @app.get("/admin")
        @require_permission("admin")
        async def admin_route(request: Request):
            return {"message": "Admin access"}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if "request" in kwargs:
                request = kwargs["request"]
            
            if not request:
                raise HTTPException(status_code=500, detail="Request not found")
            
            user = get_current_user(request)
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            user_permissions = user.get("claims", {}).get("permissions", [])
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
