"""
API Security Module for GRACE.

Provides comprehensive API security including:
- API key management
- OAuth2/OIDC authentication
- Rate limiting
- Request/response security
- API gateway functionality
- Composed security middleware
"""

from backend.security.api_security.api_keys import (
    APIKey,
    APIKeyManager,
    APIKeyScope,
    APIKeyStatus,
    APIKeyQuota,
    APIKeyUsage,
    get_api_key_manager,
)

from backend.security.api_security.oauth import (
    OAuth2Provider,
    OAuth2Client,
    AuthorizationCodeFlow,
    ClientCredentialsFlow,
    TokenService,
    JWTManager,
    TokenType,
    GrantType,
)

from backend.security.api_security.rate_limiting import (
    RateLimiter,
    TieredRateLimits,
    BurstAllowance,
    RateLimitMiddleware,
    RateLimitTier,
    RateLimitResult,
)

from backend.security.api_security.request_validation import (
    RequestValidator,
    RequestSigning,
    ReplayPrevention,
    SizeLimiter,
    ContentTypeValidator,
    InjectionPrevention,
    ValidationResult,
)

from backend.security.api_security.response_security import (
    ResponseSigner,
    SensitiveDataMasker,
    PIIRedactor,
    ErrorSanitizer,
    SecurityHeadersInjector,
)

from backend.security.api_security.gateway import (
    APIGateway,
    CircuitBreaker,
    RequestTransformer,
    ResponseTransformer,
    VersionRouter,
    HealthBasedRouter,
    CircuitState,
)

from backend.security.api_security.middleware import (
    APISecurityMiddleware,
    SecurityLevel,
    SecurityProfile,
    get_security_middleware,
)

__all__ = [
    # API Keys
    "APIKey",
    "APIKeyManager",
    "APIKeyScope",
    "APIKeyStatus",
    "APIKeyQuota",
    "APIKeyUsage",
    "get_api_key_manager",
    # OAuth
    "OAuth2Provider",
    "OAuth2Client",
    "AuthorizationCodeFlow",
    "ClientCredentialsFlow",
    "TokenService",
    "JWTManager",
    "TokenType",
    "GrantType",
    # Rate Limiting
    "RateLimiter",
    "TieredRateLimits",
    "BurstAllowance",
    "RateLimitMiddleware",
    "RateLimitTier",
    "RateLimitResult",
    # Request Validation
    "RequestValidator",
    "RequestSigning",
    "ReplayPrevention",
    "SizeLimiter",
    "ContentTypeValidator",
    "InjectionPrevention",
    "ValidationResult",
    # Response Security
    "ResponseSigner",
    "SensitiveDataMasker",
    "PIIRedactor",
    "ErrorSanitizer",
    "SecurityHeadersInjector",
    # Gateway
    "APIGateway",
    "CircuitBreaker",
    "RequestTransformer",
    "ResponseTransformer",
    "VersionRouter",
    "HealthBasedRouter",
    "CircuitState",
    # Middleware
    "APISecurityMiddleware",
    "SecurityLevel",
    "SecurityProfile",
    "get_security_middleware",
]
