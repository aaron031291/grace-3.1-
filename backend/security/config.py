"""
Security Configuration for GRACE

Centralized security settings loaded from environment variables.
"""

import os
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class SecurityConfig:
    """
    Centralized security configuration.

    All security-related settings in one place for easy management.
    """

    # ==================== CORS Configuration ====================
    # Allowed origins for CORS - NEVER use "*" in production with credentials
    CORS_ALLOWED_ORIGINS: List[str] = field(default_factory=lambda: [
        "http://localhost:3000",      # React dev server
        "http://localhost:5173",      # Vite dev server
        "http://localhost:8000",      # FastAPI itself
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ])
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOWED_METHODS: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
    CORS_ALLOWED_HEADERS: List[str] = field(default_factory=lambda: [
        "Content-Type",
        "Authorization",
        "X-Genesis-ID",
        "X-Session-ID",
        "X-Request-ID",
    ])
    CORS_MAX_AGE: int = 600  # 10 minutes

    # ==================== Rate Limiting ====================
    # Global rate limits (requests per minute)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"           # Default for most endpoints
    RATE_LIMIT_AUTH: str = "10/minute"               # Stricter for auth endpoints
    RATE_LIMIT_UPLOAD: str = "20/minute"             # File uploads
    RATE_LIMIT_AI: str = "30/minute"                 # AI/LLM endpoints
    RATE_LIMIT_BURST: int = 10                       # Allow burst of 10 requests

    # ==================== Session Security ====================
    SESSION_COOKIE_SECURE: bool = True               # Require HTTPS in production
    SESSION_COOKIE_HTTPONLY: bool = True             # Prevent JavaScript access
    SESSION_COOKIE_SAMESITE: str = "lax"             # CSRF protection
    SESSION_MAX_AGE_HOURS: int = 24                  # Session expiration
    GENESIS_ID_MAX_AGE_DAYS: int = 30                # Reduced from 365 days

    # ==================== Security Headers ====================
    # Content Security Policy
    # FIX: unsafe-inline should only be used in development mode
    # Production mode uses stricter CSP (set dynamically in __post_init__)
    CSP_DEFAULT_SRC: str = "'self'"
    CSP_SCRIPT_SRC: str = "'self'"   # No unsafe-inline by default (see __post_init__)
    CSP_STYLE_SRC: str = "'self'"    # No unsafe-inline by default (see __post_init__)
    CSP_IMG_SRC: str = "'self' data: blob:"
    CSP_CONNECT_SRC: str = "'self'"
    CSP_FRAME_ANCESTORS: str = "'none'"              # Prevent clickjacking

    # Other security headers
    X_CONTENT_TYPE_OPTIONS: str = "nosniff"
    X_FRAME_OPTIONS: str = "DENY"
    X_XSS_PROTECTION: str = "1; mode=block"
    REFERRER_POLICY: str = "strict-origin-when-cross-origin"
    PERMISSIONS_POLICY: str = "geolocation=(), microphone=(), camera=()"

    # HSTS (HTTP Strict Transport Security)
    HSTS_ENABLED: bool = True
    HSTS_MAX_AGE: int = 31536000                     # 1 year
    HSTS_INCLUDE_SUBDOMAINS: bool = True
    HSTS_PRELOAD: bool = False

    # ==================== Input Validation ====================
    MAX_REQUEST_SIZE_MB: int = 50                    # Max request body size
    MAX_FILE_UPLOAD_SIZE_MB: int = 100               # Max file upload size
    MAX_STRING_LENGTH: int = 10000                   # Max string input length
    MAX_ARRAY_LENGTH: int = 1000                     # Max array input length

    # Allowed file types for upload
    ALLOWED_FILE_EXTENSIONS: List[str] = field(default_factory=lambda: [
        ".txt", ".md", ".json", ".csv", ".xml",
        ".pdf", ".doc", ".docx",
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".html", ".css", ".yaml", ".yml",
    ])

    # ==================== Security Logging ====================
    LOG_SECURITY_EVENTS: bool = True
    LOG_FAILED_AUTH: bool = True
    LOG_RATE_LIMIT_EXCEEDED: bool = True
    LOG_SUSPICIOUS_REQUESTS: bool = True

    # ==================== Production Mode ====================
    # Set to True in production for stricter security
    PRODUCTION_MODE: bool = False

    def __post_init__(self):
        """Load overrides from environment variables."""
        # CORS origins from environment
        env_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
        if env_origins:
            self.CORS_ALLOWED_ORIGINS = [o.strip() for o in env_origins.split(",")]

        # Production mode
        self.PRODUCTION_MODE = os.getenv("PRODUCTION_MODE", "false").lower() == "true"

        # Cookie security - force secure in production
        if self.PRODUCTION_MODE:
            self.SESSION_COOKIE_SECURE = True
            self.HSTS_ENABLED = True
            # FIX: Strict CSP in production - no unsafe-inline
            # Use nonces or hashes for inline scripts/styles instead
        else:
            # Allow insecure cookies in development
            self.SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
            # FIX: Only allow unsafe-inline in development mode for convenience
            self.CSP_SCRIPT_SRC = "'self' 'unsafe-inline'"
            self.CSP_STYLE_SRC = "'self' 'unsafe-inline'"

        # Rate limiting
        self.RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", self.RATE_LIMIT_DEFAULT)
        self.RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", self.RATE_LIMIT_AUTH)

        # Security logging
        self.LOG_SECURITY_EVENTS = os.getenv("LOG_SECURITY_EVENTS", "true").lower() == "true"

    def get_csp_header(self) -> str:
        """Build Content-Security-Policy header value."""
        directives = [
            f"default-src {self.CSP_DEFAULT_SRC}",
            f"script-src {self.CSP_SCRIPT_SRC}",
            f"style-src {self.CSP_STYLE_SRC}",
            f"img-src {self.CSP_IMG_SRC}",
            f"connect-src {self.CSP_CONNECT_SRC}",
            f"frame-ancestors {self.CSP_FRAME_ANCESTORS}",
        ]
        return "; ".join(directives)

    def get_hsts_header(self) -> str:
        """Build Strict-Transport-Security header value."""
        if not self.HSTS_ENABLED:
            return ""

        value = f"max-age={self.HSTS_MAX_AGE}"
        if self.HSTS_INCLUDE_SUBDOMAINS:
            value += "; includeSubDomains"
        if self.HSTS_PRELOAD:
            value += "; preload"
        return value


# Singleton instance
_security_config: Optional[SecurityConfig] = None


def get_security_config() -> SecurityConfig:
    """Get the security configuration singleton."""
    global _security_config
    if _security_config is None:
        _security_config = SecurityConfig()
    return _security_config
