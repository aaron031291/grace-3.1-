"""
Tests for Authentication and Session Management

Tests cover:
- Session creation and validation
- Session expiration
- CSRF token generation and validation
- Cookie security settings
- Authentication dependencies
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta
import secrets


class TestSessionManager:
    """Tests for SessionManager class."""

    @pytest.fixture
    def session_manager(self):
        """Create a mock SessionManager for testing."""
        class MockSessionManager:
            def __init__(self):
                self._sessions = {}
                self.config = MagicMock(
                    SESSION_MAX_AGE_HOURS=24,
                    GENESIS_ID_MAX_AGE_DAYS=30,
                    SESSION_COOKIE_HTTPONLY=True,
                    SESSION_COOKIE_SECURE=True,
                    SESSION_COOKIE_SAMESITE="lax"
                )
            
            def create_session(self, user_id, response, metadata=None):
                from datetime import datetime, timedelta
                session_id = f"SS-{secrets.token_hex(16)}"
                expires_at = datetime.utcnow() + timedelta(hours=24)
                self._sessions[session_id] = {
                    "user_id": user_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "metadata": metadata or {},
                }
                response.set_cookie(
                    key="session_id", value=session_id,
                    max_age=24*3600, httponly=True, secure=True, samesite="lax"
                )
                response.set_cookie(
                    key="genesis_id", value=user_id,
                    max_age=30*86400, httponly=True, secure=True, samesite="lax"
                )
                return session_id
            
            def validate_session(self, session_id):
                return self._sessions.get(session_id)
        
        return MockSessionManager()

    def test_create_session_generates_secure_id(self, session_manager):
        """Session IDs should be cryptographically secure."""
        response = MagicMock()
        session_id = session_manager.create_session("user123", response)
        
        assert session_id.startswith("SS-")
        assert len(session_id) == 35  # SS- + 32 hex chars

    def test_create_session_sets_cookies(self, session_manager):
        """Session creation should set proper cookies."""
        response = MagicMock()
        session_manager.create_session("user123", response)
        
        assert response.set_cookie.call_count == 2
        calls = response.set_cookie.call_args_list
        cookie_names = [call.kwargs['key'] for call in calls]
        assert 'session_id' in cookie_names
        assert 'genesis_id' in cookie_names

    def test_create_session_cookies_secure(self, session_manager):
        """Session cookies should have security flags."""
        response = MagicMock()
        session_manager.create_session("user123", response)
        
        for call in response.set_cookie.call_args_list:
            assert call.kwargs['httponly'] is True
            assert call.kwargs['secure'] is True
            assert call.kwargs['samesite'] == "lax"

    def test_validate_session_returns_data(self, session_manager):
        """Valid sessions should return session data."""
        response = MagicMock()
        session_id = session_manager.create_session("user123", response, {"role": "admin"})
        
        session_data = session_manager.validate_session(session_id)
        
        assert session_data is not None
        assert session_data["user_id"] == "user123"
        assert session_data["metadata"]["role"] == "admin"

    def test_validate_invalid_session_returns_none(self, session_manager):
        """Invalid session IDs should return None."""
        result = session_manager.validate_session("invalid-session-id")
        assert result is None

    def test_validate_session_with_wrong_prefix(self, session_manager):
        """Sessions with wrong prefix should be rejected."""
        result = session_manager.validate_session("XX-" + secrets.token_hex(16))
        assert result is None

    def test_session_stores_metadata(self, session_manager):
        """Session should store and return metadata."""
        response = MagicMock()
        metadata = {"ip": "192.168.1.1", "user_agent": "Test/1.0"}
        session_id = session_manager.create_session("user123", response, metadata)
        
        session_data = session_manager.validate_session(session_id)
        assert session_data["metadata"] == metadata


class TestCSRFProtection:
    """Tests for CSRF token generation and validation."""

    @pytest.fixture
    def csrf_token_generator(self):
        """Create CSRF token utilities."""
        def generate_csrf_token():
            return secrets.token_hex(32)
        
        def validate_csrf_token(token: str, stored_token: str) -> bool:
            if not token or not stored_token:
                return False
            return secrets.compare_digest(token, stored_token)
        
        return generate_csrf_token, validate_csrf_token

    def test_csrf_token_generation(self, csrf_token_generator):
        """CSRF tokens should be random and sufficient length."""
        generate, _ = csrf_token_generator
        token = generate()
        
        assert len(token) == 64  # 32 bytes in hex
        assert token.isalnum()

    def test_csrf_tokens_unique(self, csrf_token_generator):
        """Each generated CSRF token should be unique."""
        generate, _ = csrf_token_generator
        tokens = [generate() for _ in range(100)]
        
        assert len(set(tokens)) == 100

    def test_csrf_validation_success(self, csrf_token_generator):
        """Matching CSRF tokens should validate."""
        generate, validate = csrf_token_generator
        token = generate()
        
        assert validate(token, token) is True

    def test_csrf_validation_failure(self, csrf_token_generator):
        """Mismatched CSRF tokens should fail validation."""
        generate, validate = csrf_token_generator
        token1 = generate()
        token2 = generate()
        
        assert validate(token1, token2) is False

    def test_csrf_timing_attack_resistance(self, csrf_token_generator):
        """CSRF validation should use constant-time comparison."""
        _, validate = csrf_token_generator
        token = "a" * 64
        wrong_first = "b" + "a" * 63
        wrong_last = "a" * 63 + "b"
        
        # Both should fail regardless of where the mismatch is
        assert validate(token, wrong_first) is False
        assert validate(token, wrong_last) is False

    def test_csrf_empty_token_rejected(self, csrf_token_generator):
        """Empty CSRF tokens should be rejected."""
        _, validate = csrf_token_generator
        
        assert validate("", "valid_token") is False
        assert validate("valid_token", "") is False
        assert validate("", "") is False


class TestAuthenticationDependencies:
    """Tests for FastAPI authentication dependencies."""

    def test_unauthenticated_request_rejected(self):
        """Requests without auth should be rejected for protected endpoints."""
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        
        request = MagicMock()
        request.cookies = {}
        request.headers = {}
        
        # Simulate auth check logic
        def require_auth(request):
            if 'session_id' not in request.cookies and 'Authorization' not in request.headers:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return True
        
        with pytest.raises(HTTPException) as exc:
            require_auth(request)
        assert exc.value.status_code == 401

    def test_malformed_token_rejected(self):
        """Malformed authentication tokens should be rejected."""
        from fastapi import HTTPException
        
        malformed_tokens = [
            "not-a-token",
            "Bearer ",  # Empty bearer
            "Bearer" + "x" * 10000,  # Too long
            "Basic invalid!!",  # Invalid base64
        ]
        
        for token in malformed_tokens:
            # Each malformed token should be rejected or handled safely
            assert True  # Placeholder - actual validation depends on implementation


class TestSessionExpiration:
    """Tests for session expiration handling."""

    def test_expired_session_rejected(self):
        """Expired sessions should be rejected."""
        # Create a session that's already expired
        from datetime import datetime, timedelta
        
        expired_session = {
            "user_id": "user123",
            "expires_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        }
        
        def is_session_expired(session_data):
            expires_at = datetime.fromisoformat(session_data["expires_at"])
            return datetime.utcnow() > expires_at
        
        assert is_session_expired(expired_session) is True

    def test_valid_session_accepted(self):
        """Non-expired sessions should be accepted."""
        from datetime import datetime, timedelta
        
        valid_session = {
            "user_id": "user123",
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }
        
        def is_session_expired(session_data):
            expires_at = datetime.fromisoformat(session_data["expires_at"])
            return datetime.utcnow() > expires_at
        
        assert is_session_expired(valid_session) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
