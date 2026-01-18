"""
RBAC Middleware for GRACE.

Provides:
- Permission injection into request context
- Permission caching per session
- Integration with existing auth middleware
- Automatic role and permission resolution
"""

import logging
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set, Callable, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from .models import AuthorizationContext
from .roles import get_role_manager, RoleManager
from .permissions import get_permission_manager
from .enforcer import get_enforcer

logger = logging.getLogger(__name__)


class SimpleTTLCache:
    """Simple thread-safe TTL cache implementation."""
    
    def __init__(self, maxsize: int = 1000, ttl: int = 300):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._maxsize = maxsize
        self._ttl = ttl
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value if exists and not expired."""
        with self._lock:
            if key not in self._cache:
                return None
            value, expiry = self._cache[key]
            if datetime.utcnow().timestamp() > expiry:
                del self._cache[key]
                return None
            return value
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Set value with TTL."""
        with self._lock:
            if len(self._cache) >= self._maxsize:
                self._evict_oldest()
            expiry = datetime.utcnow().timestamp() + self._ttl
            self._cache[key] = (value, expiry)
    
    def pop(self, key: str, default: Any = None) -> Any:
        """Remove and return value."""
        with self._lock:
            if key in self._cache:
                value, _ = self._cache.pop(key)
                return value
            return default
    
    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()
    
    def _evict_oldest(self) -> None:
        """Evict oldest entry to make room."""
        if not self._cache:
            return
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
        del self._cache[oldest_key]


class PermissionCache:
    """
    Thread-safe permission cache with TTL.
    
    Caches user permissions to avoid repeated database lookups.
    """
    
    def __init__(self, maxsize: int = 1000, ttl: int = 300):
        self._cache = SimpleTTLCache(maxsize=maxsize, ttl=ttl)
        self._role_cache = SimpleTTLCache(maxsize=maxsize, ttl=ttl)
    
    def get_permissions(self, genesis_id: str) -> Optional[Set[str]]:
        """Get cached permissions for a user."""
        return self._cache.get(genesis_id)
    
    def set_permissions(self, genesis_id: str, permissions: Set[str]) -> None:
        """Cache permissions for a user."""
        self._cache[genesis_id] = permissions
    
    def get_roles(self, genesis_id: str) -> Optional[list]:
        """Get cached roles for a user."""
        return self._role_cache.get(genesis_id)
    
    def set_roles(self, genesis_id: str, roles: list) -> None:
        """Cache roles for a user."""
        self._role_cache[genesis_id] = roles
    
    def invalidate(self, genesis_id: str) -> None:
        """Invalidate cache for a user."""
        self._cache.pop(genesis_id, None)
        self._role_cache.pop(genesis_id, None)
    
    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._role_cache.clear()


_permission_cache = PermissionCache()


class RBACMiddleware(BaseHTTPMiddleware):
    """
    RBAC middleware for FastAPI/Starlette.
    
    Injects user permissions and roles into request state.
    Provides caching for improved performance.
    """
    
    def __init__(
        self,
        app,
        enforce_on_all: bool = False,
        public_endpoints: Optional[list] = None,
        excluded_methods: Optional[list] = None,
        cache_ttl: int = 300
    ):
        super().__init__(app)
        self.enforce_on_all = enforce_on_all
        self.public_endpoints = public_endpoints or [
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
        self.excluded_methods = excluded_methods or ["OPTIONS"]
        self.cache_ttl = cache_ttl
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and inject RBAC context."""
        if request.method in self.excluded_methods:
            return await call_next(request)
        
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)
        
        genesis_id = self._get_genesis_id(request)
        
        if not genesis_id:
            request.state.rbac_user = None
            request.state.rbac_roles = []
            request.state.rbac_permissions = set()
            
            if self.enforce_on_all:
                return JSONResponse(
                    status_code=HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Authentication required",
                        "message": "Please login to access this resource"
                    }
                )
            
            return await call_next(request)
        
        try:
            roles, permissions = await self._resolve_permissions(genesis_id)
            
            request.state.rbac_user = genesis_id
            request.state.rbac_roles = roles
            request.state.rbac_permissions = permissions
            request.state.rbac_context = AuthorizationContext(
                genesis_id=genesis_id,
                session_id=getattr(request.state, "session_id", None),
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                request_path=str(request.url.path),
                request_method=request.method
            )
            
        except Exception as e:
            logger.error(f"[RBAC-MIDDLEWARE] Error resolving permissions: {e}")
            request.state.rbac_user = genesis_id
            request.state.rbac_roles = []
            request.state.rbac_permissions = set()
        
        return await call_next(request)
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if path is a public endpoint."""
        for public in self.public_endpoints:
            if path == public or path.startswith(public + "/"):
                return True
        return False
    
    def _get_genesis_id(self, request: Request) -> Optional[str]:
        """Extract Genesis ID from request."""
        if hasattr(request.state, "genesis_id"):
            return request.state.genesis_id
        
        genesis_id = request.cookies.get("genesis_id")
        if genesis_id:
            return genesis_id
        
        genesis_id = request.headers.get("X-Genesis-ID")
        if genesis_id:
            return genesis_id
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return token[:64] if len(token) >= 64 else None
        
        return None
    
    async def _resolve_permissions(
        self,
        genesis_id: str
    ) -> tuple:
        """Resolve roles and permissions for a user."""
        cached_roles = _permission_cache.get_roles(genesis_id)
        cached_perms = _permission_cache.get_permissions(genesis_id)
        
        if cached_roles is not None and cached_perms is not None:
            return cached_roles, cached_perms
        
        from database.session import get_db
        session = next(get_db())
        
        try:
            role_manager = get_role_manager(session)
            
            roles = role_manager.get_user_roles(genesis_id)
            role_names = [r.name for r in roles]
            
            permissions = role_manager.get_user_permissions(genesis_id)
            
            _permission_cache.set_roles(genesis_id, role_names)
            _permission_cache.set_permissions(genesis_id, permissions)
            
            return role_names, permissions
            
        finally:
            session.close()


class RBACEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces RBAC on all endpoints.
    
    Maps endpoints to required permissions and denies access
    if the user doesn't have the required permission.
    """
    
    def __init__(
        self,
        app,
        endpoint_permissions: Optional[Dict[str, str]] = None,
        default_permission: Optional[str] = None,
        public_endpoints: Optional[list] = None
    ):
        super().__init__(app)
        self.endpoint_permissions = endpoint_permissions or {}
        self.default_permission = default_permission
        self.public_endpoints = public_endpoints or [
            "/health",
            "/docs",
            "/openapi.json",
            "/auth/",
        ]
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enforce RBAC on the request."""
        if request.method == "OPTIONS":
            return await call_next(request)
        
        if self._is_public(request.url.path):
            return await call_next(request)
        
        required_permission = self._get_required_permission(
            request.method,
            request.url.path
        )
        
        if not required_permission:
            return await call_next(request)
        
        genesis_id = getattr(request.state, "rbac_user", None)
        if not genesis_id:
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Authentication required",
                    "required_permission": required_permission
                }
            )
        
        permissions = getattr(request.state, "rbac_permissions", set())
        
        if self._has_permission(permissions, required_permission):
            return await call_next(request)
        
        logger.warning(
            f"[RBAC-ENFORCE] Access denied: user={genesis_id}, "
            f"path={request.url.path}, required={required_permission}"
        )
        
        return JSONResponse(
            status_code=HTTP_403_FORBIDDEN,
            content={
                "error": "Access denied",
                "required_permission": required_permission,
                "message": "You don't have permission to access this resource"
            }
        )
    
    def _is_public(self, path: str) -> bool:
        """Check if path is public."""
        for public in self.public_endpoints:
            if path.startswith(public):
                return True
        return False
    
    def _get_required_permission(
        self,
        method: str,
        path: str
    ) -> Optional[str]:
        """Get required permission for an endpoint."""
        key = f"{method}:{path}"
        if key in self.endpoint_permissions:
            return self.endpoint_permissions[key]
        
        for pattern, permission in self.endpoint_permissions.items():
            if self._path_matches(path, pattern.split(":", 1)[-1]):
                return permission
        
        return self.default_permission
    
    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if path matches a pattern with wildcards."""
        if pattern.endswith("*"):
            return path.startswith(pattern[:-1])
        return path == pattern
    
    def _has_permission(
        self,
        user_permissions: Set[str],
        required: str
    ) -> bool:
        """Check if user has required permission."""
        if "*:*:*" in user_permissions:
            return True
        
        if required in user_permissions:
            return True
        
        parts = required.split(":")
        resource = parts[0]
        action = parts[-1]
        
        wildcards = [
            f"{resource}:*:*",
            f"{resource}:*:{action}",
            f"*:*:{action}",
        ]
        
        for wc in wildcards:
            if wc in user_permissions:
                return True
        
        return False


def get_permission_cache() -> PermissionCache:
    """Get the global permission cache."""
    return _permission_cache


def invalidate_user_cache(genesis_id: str) -> None:
    """Invalidate cached permissions for a user."""
    _permission_cache.invalidate(genesis_id)


def clear_permission_cache() -> None:
    """Clear all cached permissions."""
    _permission_cache.clear()


ENDPOINT_PERMISSION_MAP = {
    "GET:/api/users": "users:*:read",
    "POST:/api/users": "users:*:create",
    "PUT:/api/users/*": "users:*:update",
    "DELETE:/api/users/*": "users:*:delete",
    
    "GET:/api/roles": "roles:*:read",
    "POST:/api/roles": "roles:*:create",
    "PUT:/api/roles/*": "roles:*:update",
    "DELETE:/api/roles/*": "roles:*:delete",
    
    "GET:/api/code/*": "code:*:read",
    "POST:/api/code/*": "code:*:create",
    "PUT:/api/code/*": "code:*:update",
    "DELETE:/api/code/*": "code:*:delete",
    
    "GET:/api/audit/*": "audit:*:read",
    "POST:/api/audit/export": "audit:*:export",
    
    "GET:/api/knowledge/*": "knowledge_base:*:read",
    "POST:/api/knowledge/*": "knowledge_base:*:create",
    "PUT:/api/knowledge/*": "knowledge_base:*:update",
    
    "GET:/api/genesis-keys/*": "genesis_keys:*:read",
    "POST:/api/genesis-keys/*": "genesis_keys:*:create",
    
    "GET:/api/system/config": "system:config:read",
    "PUT:/api/system/config": "system:config:update",
    "GET:/api/system/status": "system:status:read",
}
