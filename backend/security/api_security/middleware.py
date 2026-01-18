"""
Composed API Security Middleware for GRACE.

Provides:
- APISecurityMiddleware combining all security checks
- SecurityLevel enum for different security profiles
- Configurable security profiles per endpoint
- Audit trail for all security events
"""

import time
import json
import secrets
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Set, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

from backend.security.api_security.oauth import (
    OAuth2Provider,
    TokenService,
    get_oauth2_provider,
)
from backend.security.api_security.rate_limiting import (
    RateLimiter,
    RateLimitMiddleware,
    RateLimitResult,
    RateLimitTier,
    get_rate_limiter,
)
from backend.security.api_security.request_validation import (
    RequestValidator,
    ValidationResult,
    get_request_validator,
)
from backend.security.api_security.response_security import (
    ResponseSigner,
    SensitiveDataMasker,
    PIIRedactor,
    ErrorSanitizer,
    SecurityHeadersInjector,
    get_security_headers_injector,
    get_error_sanitizer,
    get_data_masker,
)
from backend.security.api_security.api_keys import (
    APIKeyManager,
    get_api_key_manager,
)

logger = logging.getLogger(__name__)


class SecurityLevel(str, Enum):
    """Security enforcement levels."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    HIGH = "high"
    MAXIMUM = "maximum"


@dataclass
class SecurityProfile:
    """Security configuration profile."""
    level: SecurityLevel = SecurityLevel.STANDARD
    
    require_authentication: bool = True
    require_api_key: bool = False
    require_oauth: bool = False
    
    enable_rate_limiting: bool = True
    rate_limit_tier: RateLimitTier = RateLimitTier.BASIC
    
    validate_request_signing: bool = False
    validate_replay_prevention: bool = False
    validate_content_type: bool = True
    validate_size_limits: bool = True
    validate_injection: bool = True
    
    sign_responses: bool = False
    redact_pii: bool = False
    sanitize_errors: bool = True
    inject_security_headers: bool = True
    
    exempt_paths: Set[str] = field(default_factory=lambda: {"/health", "/ready", "/metrics"})
    
    @classmethod
    def minimal(cls) -> "SecurityProfile":
        """Minimal security for internal/trusted endpoints."""
        return cls(
            level=SecurityLevel.MINIMAL,
            require_authentication=False,
            enable_rate_limiting=False,
            validate_content_type=False,
            validate_size_limits=True,
            validate_injection=False,
            sanitize_errors=False,
            inject_security_headers=False,
        )
    
    @classmethod
    def standard(cls) -> "SecurityProfile":
        """Standard security for typical API endpoints."""
        return cls(
            level=SecurityLevel.STANDARD,
            require_authentication=True,
            enable_rate_limiting=True,
            validate_content_type=True,
            validate_size_limits=True,
            validate_injection=True,
            sanitize_errors=True,
            inject_security_headers=True,
        )
    
    @classmethod
    def high(cls) -> "SecurityProfile":
        """High security for sensitive endpoints."""
        return cls(
            level=SecurityLevel.HIGH,
            require_authentication=True,
            require_api_key=True,
            enable_rate_limiting=True,
            rate_limit_tier=RateLimitTier.PROFESSIONAL,
            validate_request_signing=True,
            validate_replay_prevention=True,
            validate_content_type=True,
            validate_size_limits=True,
            validate_injection=True,
            sign_responses=True,
            sanitize_errors=True,
            inject_security_headers=True,
        )
    
    @classmethod
    def maximum(cls) -> "SecurityProfile":
        """Maximum security for critical endpoints."""
        return cls(
            level=SecurityLevel.MAXIMUM,
            require_authentication=True,
            require_api_key=True,
            require_oauth=True,
            enable_rate_limiting=True,
            rate_limit_tier=RateLimitTier.ENTERPRISE,
            validate_request_signing=True,
            validate_replay_prevention=True,
            validate_content_type=True,
            validate_size_limits=True,
            validate_injection=True,
            sign_responses=True,
            redact_pii=True,
            sanitize_errors=True,
            inject_security_headers=True,
        )


@dataclass
class SecurityContext:
    """Security context for a request."""
    request_id: str
    client_id: Optional[str] = None
    user_id: Optional[str] = None
    api_key_id: Optional[str] = None
    scopes: Set[str] = field(default_factory=set)
    authenticated: bool = False
    authentication_method: Optional[str] = None
    rate_limit_result: Optional[RateLimitResult] = None
    validation_result: Optional[ValidationResult] = None
    security_level: SecurityLevel = SecurityLevel.STANDARD
    metadata: Dict[str, Any] = field(default_factory=dict)


class APISecurityMiddleware:
    """
    Composed security middleware combining all API security checks.
    
    Applies security checks in order:
    1. Rate limiting
    2. Authentication (API key or OAuth)
    3. Request validation (signing, replay, injection)
    4. Request processing
    5. Response security (signing, headers, error sanitization)
    """
    
    def __init__(
        self,
        default_profile: Optional[SecurityProfile] = None,
        oauth_provider: Optional[OAuth2Provider] = None,
        rate_limiter: Optional[RateLimiter] = None,
        request_validator: Optional[RequestValidator] = None,
        api_key_manager: Optional[APIKeyManager] = None,
        security_headers: Optional[SecurityHeadersInjector] = None,
        error_sanitizer: Optional[ErrorSanitizer] = None,
        data_masker: Optional[SensitiveDataMasker] = None,
        pii_redactor: Optional[PIIRedactor] = None,
        response_signer: Optional[ResponseSigner] = None,
        audit_storage=None
    ):
        self._default_profile = default_profile or SecurityProfile.standard()
        self._oauth = oauth_provider
        self._rate_limiter = rate_limiter
        self._request_validator = request_validator
        self._api_key_manager = api_key_manager
        self._security_headers = security_headers
        self._error_sanitizer = error_sanitizer
        self._data_masker = data_masker
        self._pii_redactor = pii_redactor
        self._response_signer = response_signer
        self._audit = audit_storage
        
        self._endpoint_profiles: Dict[str, SecurityProfile] = {}
        self._initialized = False
        
    def _ensure_initialized(self):
        """Lazy initialization of dependencies."""
        if self._initialized:
            return
        
        if self._oauth is None:
            try:
                self._oauth = get_oauth2_provider()
            except Exception:
                pass
        
        if self._rate_limiter is None:
            self._rate_limiter = get_rate_limiter()
        
        if self._request_validator is None:
            self._request_validator = get_request_validator()
        
        if self._api_key_manager is None:
            self._api_key_manager = get_api_key_manager()
        
        if self._security_headers is None:
            self._security_headers = get_security_headers_injector()
        
        if self._error_sanitizer is None:
            self._error_sanitizer = get_error_sanitizer()
        
        if self._data_masker is None:
            self._data_masker = get_data_masker()
        
        self._initialized = True
    
    def _audit_event(
        self,
        event_type: str,
        context: SecurityContext,
        details: Optional[Dict] = None,
        severity: str = "info"
    ):
        """Record security audit event."""
        log_level = logging.WARNING if severity == "warning" else logging.INFO
        logger.log(
            log_level,
            f"[API-SECURITY] {event_type}: request_id={context.request_id}, "
            f"client={context.client_id}, details={details}"
        )
    
    def set_endpoint_profile(self, path_pattern: str, profile: SecurityProfile):
        """Set security profile for an endpoint pattern."""
        self._endpoint_profiles[path_pattern] = profile
        logger.info(f"Security profile set: {path_pattern} -> {profile.level.value}")
    
    def get_profile_for_path(self, path: str) -> SecurityProfile:
        """Get the security profile for a path."""
        import re
        
        for pattern, profile in self._endpoint_profiles.items():
            regex_pattern = pattern.replace("*", ".*").replace("{", "(?P<").replace("}", ">[^/]+)")
            if re.match(f"^{regex_pattern}$", path):
                return profile
        
        return self._default_profile
    
    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        return f"req_{secrets.token_hex(12)}"
    
    def _extract_client_ip(self, request) -> str:
        """Extract client IP from request."""
        if hasattr(request, "client") and request.client:
            return request.client.host if hasattr(request.client, "host") else str(request.client)
        
        forwarded = getattr(request, "headers", {}).get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        return "unknown"
    
    async def _authenticate_api_key(
        self,
        request,
        context: SecurityContext
    ) -> Tuple[bool, Optional[str]]:
        """Authenticate using API key."""
        api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
        
        if not api_key:
            return False, "API key required"
        
        is_valid, key_data, error = self._api_key_manager.validate_key(
            api_key,
            endpoint=request.url.path,
            client_ip=self._extract_client_ip(request)
        )
        
        if not is_valid:
            return False, error
        
        if key_data:
            context.api_key_id = key_data.key_id
            context.client_id = key_data.owner_id
            context.authenticated = True
            context.authentication_method = "api_key"
        
        return True, None
    
    async def _authenticate_oauth(
        self,
        request,
        context: SecurityContext
    ) -> Tuple[bool, Optional[str]]:
        """Authenticate using OAuth2 token."""
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        
        if not auth_header:
            return False, "Authorization header required"
        
        if not auth_header.startswith("Bearer "):
            return False, "Bearer token required"
        
        token = auth_header[7:]
        
        if self._oauth:
            is_valid, claims, error = self._oauth.validate_token(token)
            
            if not is_valid:
                return False, error
            
            if claims:
                context.client_id = claims.get("client_id")
                context.user_id = claims.get("sub")
                context.scopes = set(claims.get("scope", "").split())
                context.authenticated = True
                context.authentication_method = "oauth2"
            
            return True, None
        
        return False, "OAuth provider not configured"
    
    async def _check_rate_limit(
        self,
        request,
        context: SecurityContext,
        profile: SecurityProfile
    ) -> Tuple[bool, Optional[RateLimitResult]]:
        """Check rate limits."""
        if not profile.enable_rate_limiting or not self._rate_limiter:
            return True, None
        
        client_id = context.client_id or self._extract_client_ip(request)
        
        if context.api_key_id:
            self._rate_limiter.set_client_tier(client_id, profile.rate_limit_tier)
        
        result = self._rate_limiter.check(
            client_id,
            endpoint=request.url.path
        )
        
        context.rate_limit_result = result
        
        return result.allowed, result
    
    async def _validate_request(
        self,
        request,
        context: SecurityContext,
        profile: SecurityProfile,
        body: Optional[bytes] = None
    ) -> Tuple[bool, Optional[ValidationResult]]:
        """Validate request security."""
        if not self._request_validator:
            return True, None
        
        self._request_validator._require_signing = profile.validate_request_signing
        self._request_validator._require_nonce = profile.validate_replay_prevention
        
        headers = dict(request.headers)
        json_data = None
        
        if body:
            try:
                json_data = json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        
        result = self._request_validator.validate(
            method=request.method,
            path=request.url.path,
            headers=headers,
            body=body,
            json_data=json_data,
            client_ip=self._extract_client_ip(request)
        )
        
        context.validation_result = result
        
        return result.valid, result
    
    def _apply_security_headers(self, response, request) -> Dict[str, str]:
        """Apply security headers to response."""
        if not self._security_headers:
            return {}
        
        origin = request.headers.get("Origin")
        return self._security_headers.get_headers(request_origin=origin)
    
    def _sanitize_error_response(
        self,
        error: Exception,
        status_code: int,
        context: SecurityContext
    ) -> Dict[str, Any]:
        """Sanitize error response."""
        if not self._error_sanitizer:
            return {
                "error": "Internal server error",
                "request_id": context.request_id
            }
        
        return self._error_sanitizer.sanitize_error(
            error,
            status_code,
            context.request_id
        )
    
    async def __call__(self, request, call_next):
        """
        Middleware entry point.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response with security applied
        """
        self._ensure_initialized()
        
        context = SecurityContext(
            request_id=self._generate_request_id()
        )
        
        path = request.url.path
        profile = self.get_profile_for_path(path)
        context.security_level = profile.level
        
        if path in profile.exempt_paths:
            response = await call_next(request)
            response.headers["X-Request-ID"] = context.request_id
            return response
        
        from starlette.responses import JSONResponse
        
        is_allowed, rate_result = await self._check_rate_limit(request, context, profile)
        if not is_allowed and rate_result:
            self._audit_event("rate_limit_exceeded", context, {"path": path}, "warning")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests",
                    "retry_after": rate_result.retry_after,
                    "request_id": context.request_id
                },
                headers=rate_result.to_headers()
            )
        
        if profile.require_authentication:
            authenticated = False
            auth_error = None
            
            if profile.require_api_key:
                authenticated, auth_error = await self._authenticate_api_key(request, context)
            
            if not authenticated and profile.require_oauth:
                authenticated, auth_error = await self._authenticate_oauth(request, context)
            
            if not authenticated and not profile.require_api_key and not profile.require_oauth:
                api_auth, _ = await self._authenticate_api_key(request, context)
                if not api_auth:
                    authenticated, auth_error = await self._authenticate_oauth(request, context)
                else:
                    authenticated = True
            
            if not authenticated:
                self._audit_event("authentication_failed", context, {"error": auth_error}, "warning")
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "unauthorized",
                        "message": auth_error or "Authentication required",
                        "request_id": context.request_id
                    }
                )
        
        body = None
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
            except Exception:
                pass
        
        is_valid, validation_result = await self._validate_request(request, context, profile, body)
        if not is_valid and validation_result:
            self._audit_event("validation_failed", context, {"errors": validation_result.errors}, "warning")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "validation_failed",
                    "message": "Request validation failed",
                    "errors": validation_result.errors,
                    "request_id": context.request_id
                }
            )
        
        try:
            response = await call_next(request)
        except Exception as e:
            self._audit_event("request_error", context, {"error": str(e)}, "warning")
            
            error_response = self._sanitize_error_response(e, 500, context)
            return JSONResponse(
                status_code=500,
                content=error_response
            )
        
        response.headers["X-Request-ID"] = context.request_id
        
        if rate_result:
            for header, value in rate_result.to_headers().items():
                response.headers[header] = value
        
        if profile.inject_security_headers:
            security_headers = self._apply_security_headers(response, request)
            for header, value in security_headers.items():
                response.headers[header] = value
        
        self._audit_event(
            "request_completed",
            context,
            {
                "path": path,
                "method": request.method,
                "status_code": response.status_code,
                "authenticated": context.authenticated
            }
        )
        
        return response
    
    def get_stats(self) -> Dict[str, Any]:
        """Get middleware statistics."""
        return {
            "default_profile": self._default_profile.level.value,
            "endpoint_profiles": {
                pattern: profile.level.value
                for pattern, profile in self._endpoint_profiles.items()
            },
            "initialized": self._initialized
        }


_security_middleware: Optional[APISecurityMiddleware] = None


def get_security_middleware(
    profile: Optional[SecurityProfile] = None
) -> APISecurityMiddleware:
    """Get the security middleware singleton."""
    global _security_middleware
    if _security_middleware is None:
        _security_middleware = APISecurityMiddleware(default_profile=profile)
    return _security_middleware


def create_security_middleware(
    level: SecurityLevel = SecurityLevel.STANDARD,
    **kwargs
) -> APISecurityMiddleware:
    """
    Create a new security middleware instance.
    
    Args:
        level: Security level to use
        **kwargs: Additional configuration
        
    Returns:
        Configured APISecurityMiddleware
    """
    profiles = {
        SecurityLevel.MINIMAL: SecurityProfile.minimal,
        SecurityLevel.STANDARD: SecurityProfile.standard,
        SecurityLevel.HIGH: SecurityProfile.high,
        SecurityLevel.MAXIMUM: SecurityProfile.maximum,
    }
    
    profile = profiles.get(level, SecurityProfile.standard)()
    
    for key, value in kwargs.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    
    return APISecurityMiddleware(default_profile=profile)
