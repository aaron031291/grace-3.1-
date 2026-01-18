"""
Tests for Authentication Middleware

Tests API key authentication, JWT authentication, rate limiting,
public routes, and FastAPI dependencies.
"""

import os
import sys
import time
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, 'backend')

try:
    import jwt
    HAS_JWT = True
except ImportError:
    HAS_JWT = False

requires_jwt = pytest.mark.skipif(not HAS_JWT, reason="PyJWT not installed")

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient


# ==================== Fixtures ====================

@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment variables before each test."""
    env_vars = ["GRACE_API_KEY", "GRACE_API_KEYS", "GRACE_JWT_SECRET", "GRACE_RATE_LIMIT"]
    original = {k: os.environ.get(k) for k in env_vars}
    
    for k in env_vars:
        if k in os.environ:
            del os.environ[k]
    
    yield
    
    for k, v in original.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]


@pytest.fixture
def api_key():
    """Set up a valid API key."""
    key = "test-api-key-12345"
    os.environ["GRACE_API_KEY"] = key
    return key


@pytest.fixture
def multiple_api_keys():
    """Set up multiple valid API keys."""
    keys = ["key1-valid", "key2-valid", "key3-valid"]
    os.environ["GRACE_API_KEYS"] = ",".join(keys)
    return keys


@pytest.fixture
def jwt_secret():
    """Set up JWT secret."""
    secret = "test-jwt-secret-super-secure"
    os.environ["GRACE_JWT_SECRET"] = secret
    return secret


@pytest.fixture
def rate_limit():
    """Set up rate limit."""
    os.environ["GRACE_RATE_LIMIT"] = "5"
    return 5


@pytest.fixture
def app_with_middleware(api_key):
    """Create FastAPI app with authentication middleware."""
    from middleware.authentication import (
        add_authentication_middleware,
        require_auth,
        optional_auth,
        get_rate_limiter
    )
    
    get_rate_limiter().reset()
    
    app = FastAPI()
    add_authentication_middleware(app, require_auth_by_default=True)
    
    @app.get("/health")
    def health():
        return {"status": "healthy"}
    
    @app.get("/docs")
    def docs():
        return {"docs": "available"}
    
    @app.get("/protected")
    def protected():
        return {"message": "protected content"}
    
    @app.get("/with-auth")
    def with_auth(user: dict = Depends(require_auth)):
        return {"user": user}
    
    @app.get("/optional")
    def optional_route(user: dict = Depends(optional_auth)):
        if user:
            return {"authenticated": True, "user": user}
        return {"authenticated": False}
    
    return app


@pytest.fixture
def client(app_with_middleware):
    """Create test client."""
    return TestClient(app_with_middleware)


# ==================== API Key Authentication Tests ====================

class TestAPIKeyAuthentication:
    """Test API key authentication."""
    
    def test_valid_api_key_passes(self, client, api_key):
        """Valid API key should authenticate successfully."""
        response = client.get("/protected", headers={"X-API-Key": api_key})
        assert response.status_code == 200
        assert response.json()["message"] == "protected content"
    
    def test_invalid_api_key_returns_401(self, client, api_key):
        """Invalid API key should return 401."""
        response = client.get("/protected", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 401
        assert "error" in response.json()
    
    def test_missing_api_key_returns_401(self, client, api_key):
        """Missing API key should return 401."""
        response = client.get("/protected")
        assert response.status_code == 401
    
    def test_key_from_header_works(self, client, api_key):
        """API key from X-API-Key header should work."""
        response = client.get("/protected", headers={"X-API-Key": api_key})
        assert response.status_code == 200
    
    def test_key_from_query_param_works(self, client, api_key):
        """API key from query parameter should work."""
        response = client.get(f"/protected?api_key={api_key}")
        assert response.status_code == 200
    
    def test_multiple_api_keys_work(self, multiple_api_keys):
        """Multiple configured API keys should all work."""
        from middleware.authentication import (
            add_authentication_middleware,
            get_rate_limiter
        )
        
        get_rate_limiter().reset()
        
        app = FastAPI()
        add_authentication_middleware(app, require_auth_by_default=True)
        
        @app.get("/test")
        def test_route():
            return {"ok": True}
        
        client = TestClient(app)
        
        for key in multiple_api_keys:
            response = client.get("/test", headers={"X-API-Key": key})
            assert response.status_code == 200, f"Key {key} should work"


# ==================== JWT Authentication Tests ====================

class TestJWTAuthentication:
    """Test JWT authentication."""
    
    @requires_jwt
    def test_valid_jwt_passes(self, jwt_secret):
        """Valid JWT should authenticate successfully."""
        from middleware.authentication import (
            create_jwt,
            add_authentication_middleware,
            get_rate_limiter
        )
        
        get_rate_limiter().reset()
        
        token = create_jwt("test-user", expires_in=3600)
        assert token is not None
        
        app = FastAPI()
        add_authentication_middleware(app, require_auth_by_default=True)
        
        @app.get("/protected")
        def protected():
            return {"message": "success"}
        
        client = TestClient(app)
        response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
    
    @requires_jwt
    def test_expired_jwt_returns_401(self, jwt_secret):
        """Expired JWT should return 401."""
        from middleware.authentication import (
            add_authentication_middleware,
            get_rate_limiter
        )
        import jwt
        
        get_rate_limiter().reset()
        
        expired_payload = {
            "sub": "test-user",
            "iat": datetime.utcnow() - timedelta(hours=2),
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        expired_token = jwt.encode(expired_payload, jwt_secret, algorithm="HS256")
        
        app = FastAPI()
        add_authentication_middleware(app, require_auth_by_default=True)
        
        @app.get("/protected")
        def protected():
            return {"message": "success"}
        
        client = TestClient(app)
        response = client.get("/protected", headers={"Authorization": f"Bearer {expired_token}"})
        assert response.status_code == 401
    
    @requires_jwt
    def test_invalid_signature_returns_401(self, jwt_secret):
        """JWT with invalid signature should return 401."""
        from middleware.authentication import (
            add_authentication_middleware,
            get_rate_limiter
        )
        import jwt
        
        get_rate_limiter().reset()
        
        payload = {
            "sub": "test-user",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        wrong_secret_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        
        app = FastAPI()
        add_authentication_middleware(app, require_auth_by_default=True)
        
        @app.get("/protected")
        def protected():
            return {"message": "success"}
        
        client = TestClient(app)
        response = client.get("/protected", headers={"Authorization": f"Bearer {wrong_secret_token}"})
        assert response.status_code == 401
    
    def test_malformed_jwt_returns_401(self, jwt_secret):
        """Malformed JWT should return 401."""
        from middleware.authentication import (
            add_authentication_middleware,
            get_rate_limiter
        )
        
        get_rate_limiter().reset()
        
        app = FastAPI()
        add_authentication_middleware(app, require_auth_by_default=True)
        
        @app.get("/protected")
        def protected():
            return {"message": "success"}
        
        client = TestClient(app)
        
        malformed_tokens = [
            "not-a-jwt",
            "abc.def",
            "abc.def.ghi.jkl",
            "",
        ]
        
        for token in malformed_tokens:
            response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 401, f"Token '{token}' should fail"


# ==================== Rate Limiting Tests ====================

class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_under_limit_passes(self, api_key, rate_limit):
        """Requests under rate limit should pass."""
        from middleware.authentication import (
            add_authentication_middleware,
            get_rate_limiter
        )
        
        os.environ["GRACE_RATE_LIMIT"] = str(rate_limit)
        
        from middleware import authentication
        authentication._rate_limiter = authentication.RateLimiter(requests_per_minute=rate_limit)
        
        app = FastAPI()
        add_authentication_middleware(app, require_auth_by_default=True)
        
        @app.get("/test")
        def test_route():
            return {"ok": True}
        
        client = TestClient(app)
        
        for i in range(rate_limit):
            response = client.get("/test", headers={"X-API-Key": api_key})
            assert response.status_code == 200, f"Request {i+1} should pass"
    
    def test_over_limit_returns_429(self, api_key, rate_limit):
        """Requests over rate limit should return 429."""
        from middleware.authentication import (
            add_authentication_middleware,
            RateLimiter
        )
        from middleware import authentication
        
        os.environ["GRACE_RATE_LIMIT"] = str(rate_limit)
        authentication._rate_limiter = RateLimiter(requests_per_minute=rate_limit)
        
        app = FastAPI()
        add_authentication_middleware(app, require_auth_by_default=True)
        
        @app.get("/test")
        def test_route():
            return {"ok": True}
        
        client = TestClient(app)
        
        for i in range(rate_limit):
            response = client.get("/test", headers={"X-API-Key": api_key})
            assert response.status_code == 200
        
        response = client.get("/test", headers={"X-API-Key": api_key})
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]
    
    def test_rate_limit_resets_after_window(self, api_key):
        """Rate limit should reset after window expires."""
        from middleware.authentication import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=2, window_seconds=1)
        
        allowed1, _, _ = limiter.is_allowed(api_key)
        allowed2, _, _ = limiter.is_allowed(api_key)
        allowed3, _, _ = limiter.is_allowed(api_key)
        
        assert allowed1 is True
        assert allowed2 is True
        assert allowed3 is False
        
        time.sleep(1.1)
        
        allowed4, _, _ = limiter.is_allowed(api_key)
        assert allowed4 is True


# ==================== Public Routes Tests ====================

class TestPublicRoutes:
    """Test public routes bypass authentication."""
    
    def test_health_bypasses_auth(self, client, api_key):
        """Health endpoint should bypass authentication."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_docs_bypasses_auth(self, client, api_key):
        """Docs endpoint should bypass authentication."""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_public_routes_list(self):
        """Verify all expected public routes are configured."""
        from middleware.authentication import PUBLIC_ROUTES
        
        expected = ["/health", "/healthz", "/ready", "/metrics", "/docs", "/openapi.json", "/redoc"]
        for route in expected:
            assert route in PUBLIC_ROUTES, f"{route} should be public"


# ==================== require_auth Dependency Tests ====================

class TestRequireAuthDependency:
    """Test require_auth FastAPI dependency."""
    
    def test_returns_user_dict_on_success(self, api_key):
        """require_auth should return user dict on successful auth."""
        from middleware.authentication import require_auth, get_rate_limiter
        
        get_rate_limiter().reset()
        
        app = FastAPI()
        
        @app.get("/user")
        async def get_user(user: dict = Depends(require_auth)):
            return user
        
        client = TestClient(app)
        response = client.get("/user", headers={"X-API-Key": api_key})
        
        assert response.status_code == 200
        data = response.json()
        assert data["auth_type"] == "api_key"
        assert data["authenticated"] is True
    
    def test_raises_httpexception_on_failure(self, api_key):
        """require_auth should raise HTTPException on auth failure."""
        from middleware.authentication import require_auth, get_rate_limiter
        
        get_rate_limiter().reset()
        
        app = FastAPI()
        
        @app.get("/user")
        async def get_user(user: dict = Depends(require_auth)):
            return user
        
        client = TestClient(app)
        response = client.get("/user", headers={"X-API-Key": "invalid-key"})
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]


# ==================== optional_auth Dependency Tests ====================

class TestOptionalAuthDependency:
    """Test optional_auth FastAPI dependency."""
    
    def test_returns_user_on_valid_auth(self, api_key):
        """optional_auth should return user on valid authentication."""
        from middleware.authentication import optional_auth, get_rate_limiter
        from typing import Optional
        
        get_rate_limiter().reset()
        
        app = FastAPI()
        
        @app.get("/optional")
        async def optional_route(user: Optional[dict] = Depends(optional_auth)):
            return {"user": user}
        
        client = TestClient(app)
        response = client.get("/optional", headers={"X-API-Key": api_key})
        
        assert response.status_code == 200
        data = response.json()
        assert data["user"] is not None
        assert data["user"]["authenticated"] is True
    
    def test_returns_none_on_no_auth(self, api_key):
        """optional_auth should return None when no auth provided."""
        from middleware.authentication import optional_auth, get_rate_limiter
        from typing import Optional
        
        get_rate_limiter().reset()
        
        app = FastAPI()
        
        @app.get("/optional")
        async def optional_route(user: Optional[dict] = Depends(optional_auth)):
            return {"user": user}
        
        client = TestClient(app)
        response = client.get("/optional")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user"] is None


# ==================== RateLimiter Class Tests ====================

class TestRateLimiterClass:
    """Test RateLimiter class directly."""
    
    def test_initialization(self):
        """RateLimiter should initialize with correct values."""
        from middleware.authentication import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=50, window_seconds=30)
        assert limiter.requests_per_minute == 50
        assert limiter.window_seconds == 30
    
    def test_get_usage(self):
        """get_usage should return correct stats."""
        from middleware.authentication import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=10)
        key = "test-key"
        
        limiter.is_allowed(key)
        limiter.is_allowed(key)
        limiter.is_allowed(key)
        
        usage = limiter.get_usage(key)
        assert usage["requests_used"] == 3
        assert usage["requests_limit"] == 10
        assert usage["requests_remaining"] == 7
    
    def test_reset_single_key(self):
        """reset should clear a single key's requests."""
        from middleware.authentication import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=5)
        key1 = "key1"
        key2 = "key2"
        
        limiter.is_allowed(key1)
        limiter.is_allowed(key2)
        
        limiter.reset(key1)
        
        assert limiter.get_usage(key1)["requests_used"] == 0
        assert limiter.get_usage(key2)["requests_used"] == 1
    
    def test_reset_all_keys(self):
        """reset without argument should clear all keys."""
        from middleware.authentication import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=5)
        
        limiter.is_allowed("key1")
        limiter.is_allowed("key2")
        limiter.is_allowed("key3")
        
        limiter.reset()
        
        assert limiter.get_usage("key1")["requests_used"] == 0
        assert limiter.get_usage("key2")["requests_used"] == 0
        assert limiter.get_usage("key3")["requests_used"] == 0


# ==================== JWT Utility Tests ====================

class TestJWTUtilities:
    """Test JWT creation and decoding utilities."""
    
    @requires_jwt
    def test_create_jwt_returns_token(self, jwt_secret):
        """create_jwt should return a valid token string."""
        from middleware.authentication import create_jwt
        
        token = create_jwt("test-subject", expires_in=3600)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    @requires_jwt
    def test_create_jwt_with_extra_claims(self, jwt_secret):
        """create_jwt should include extra claims."""
        from middleware.authentication import create_jwt, decode_jwt
        
        extra = {"role": "admin", "permissions": ["read", "write"]}
        token = create_jwt("test-subject", extra_claims=extra)
        
        payload = decode_jwt(token)
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]
    
    @requires_jwt
    def test_decode_jwt_returns_payload(self, jwt_secret):
        """decode_jwt should return decoded payload."""
        from middleware.authentication import create_jwt, decode_jwt
        
        token = create_jwt("test-subject")
        payload = decode_jwt(token)
        
        assert payload is not None
        assert payload["sub"] == "test-subject"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_decode_jwt_without_secret_returns_none(self):
        """decode_jwt without configured secret should return None."""
        from middleware.authentication import decode_jwt
        
        result = decode_jwt("some-token")
        assert result is None


# ==================== Middleware Integration Tests ====================

class TestMiddlewareIntegration:
    """Test AuthenticationMiddleware integration."""
    
    def test_middleware_adds_rate_limit_headers(self, api_key):
        """Middleware should add rate limit headers to response."""
        from middleware.authentication import (
            add_authentication_middleware,
            get_rate_limiter,
            RateLimiter
        )
        from middleware import authentication
        
        authentication._rate_limiter = RateLimiter(requests_per_minute=100)
        
        app = FastAPI()
        add_authentication_middleware(app, require_auth_by_default=True)
        
        @app.get("/test")
        def test_route():
            return {"ok": True}
        
        client = TestClient(app)
        response = client.get("/test", headers={"X-API-Key": api_key})
        
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
    
    def test_middleware_excludes_custom_paths(self, api_key):
        """Middleware should exclude custom paths from auth."""
        from middleware.authentication import add_authentication_middleware
        
        app = FastAPI()
        add_authentication_middleware(
            app,
            exclude_paths=["/custom-public", "/api/public"],
            require_auth_by_default=True
        )
        
        @app.get("/custom-public")
        def custom_public():
            return {"public": True}
        
        @app.get("/api/public/data")
        def api_public_data():
            return {"data": "public"}
        
        client = TestClient(app)
        
        response = client.get("/custom-public")
        assert response.status_code == 200
        
        response = client.get("/api/public/data")
        assert response.status_code == 200


# ==================== Edge Cases ====================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_no_auth_configured_allows_all(self):
        """When no auth is configured, all requests should pass."""
        from middleware.authentication import add_authentication_middleware
        
        app = FastAPI()
        add_authentication_middleware(app, require_auth_by_default=True)
        
        @app.get("/test")
        def test_route():
            return {"ok": True}
        
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
    
    def test_empty_api_key_rejected(self, api_key):
        """Empty API key should be rejected."""
        from middleware.authentication import (
            add_authentication_middleware,
            get_rate_limiter
        )
        
        get_rate_limiter().reset()
        
        app = FastAPI()
        add_authentication_middleware(app, require_auth_by_default=True)
        
        @app.get("/test")
        def test_route():
            return {"ok": True}
        
        client = TestClient(app)
        response = client.get("/test", headers={"X-API-Key": ""})
        assert response.status_code == 401
    
    def test_bearer_without_token_rejected(self, api_key):
        """Bearer header without token should be rejected."""
        from middleware.authentication import (
            add_authentication_middleware,
            get_rate_limiter
        )
        
        get_rate_limiter().reset()
        
        app = FastAPI()
        add_authentication_middleware(app, require_auth_by_default=True)
        
        @app.get("/test")
        def test_route():
            return {"ok": True}
        
        client = TestClient(app)
        response = client.get("/test", headers={"Authorization": "Bearer "})
        assert response.status_code == 401
    
    def test_api_key_takes_precedence_over_jwt(self, api_key, jwt_secret):
        """API key should work even if invalid JWT is also provided."""
        from middleware.authentication import (
            add_authentication_middleware,
            get_rate_limiter
        )
        
        get_rate_limiter().reset()
        
        app = FastAPI()
        add_authentication_middleware(app, require_auth_by_default=True)
        
        @app.get("/test")
        def test_route():
            return {"ok": True}
        
        client = TestClient(app)
        response = client.get(
            "/test",
            headers={
                "X-API-Key": api_key,
                "Authorization": "Bearer invalid-jwt"
            }
        )
        assert response.status_code == 200
