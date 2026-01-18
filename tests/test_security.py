"""
Tests for Security Module

Tests:
1. SessionManager - create, validate, invalidate sessions
2. Authentication dependencies
3. CSRF protection
4. Session expiration
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestSessionManager:
    """Tests for SessionManager class."""
    
    @pytest.fixture
    def session_manager(self):
        """Create SessionManager instance."""
        with patch('backend.security.auth.get_security_config') as mock_config:
            mock_config.return_value = Mock(
                SESSION_MAX_AGE_HOURS=24,
                GENESIS_ID_MAX_AGE_DAYS=30,
                SESSION_COOKIE_HTTPONLY=True,
                SESSION_COOKIE_SECURE=True,
                SESSION_COOKIE_SAMESITE="lax"
            )
            with patch('backend.security.auth.get_security_logger') as mock_logger:
                mock_logger.return_value = Mock()
                from backend.security.auth import SessionManager
                return SessionManager()
    
    def test_init(self, session_manager):
        """Test SessionManager initialization."""
        assert session_manager is not None
        assert session_manager._sessions == {}
    
    def test_create_session(self, session_manager):
        """Test session creation."""
        mock_response = Mock()
        
        session_id = session_manager.create_session(
            user_id="G-test-user",
            response=mock_response
        )
        
        assert session_id.startswith("SS-")
        assert len(session_id) == 35  # "SS-" + 32 hex chars
        assert session_id in session_manager._sessions
        mock_response.set_cookie.assert_called()
    
    def test_create_session_with_metadata(self, session_manager):
        """Test session creation with metadata."""
        mock_response = Mock()
        
        session_id = session_manager.create_session(
            user_id="G-test-user",
            response=mock_response,
            metadata={"ip": "192.168.1.1"}
        )
        
        session = session_manager._sessions[session_id]
        assert session["metadata"]["ip"] == "192.168.1.1"
    
    def test_validate_session_valid(self, session_manager):
        """Test validation of valid session."""
        mock_response = Mock()
        session_id = session_manager.create_session("G-user", mock_response)
        
        result = session_manager.validate_session(session_id)
        
        assert result is not None
        assert result["user_id"] == "G-user"
    
    def test_validate_session_invalid(self, session_manager):
        """Test validation of invalid session."""
        result = session_manager.validate_session("SS-invalid")
        
        assert result is None
    
    def test_validate_session_expired(self, session_manager):
        """Test validation of expired session."""
        mock_response = Mock()
        session_id = session_manager.create_session("G-user", mock_response)
        
        # Manually expire the session
        session_manager._sessions[session_id]["expires_at"] = (
            datetime.utcnow() - timedelta(hours=1)
        ).isoformat()
        
        result = session_manager.validate_session(session_id)
        
        assert result is None
        assert session_id not in session_manager._sessions
    
    def test_invalidate_session(self, session_manager):
        """Test session invalidation."""
        mock_response = Mock()
        session_id = session_manager.create_session("G-user", mock_response)
        
        session_manager.invalidate_session(session_id, mock_response)
        
        assert session_id not in session_manager._sessions
        mock_response.delete_cookie.assert_called()
    
    def test_get_user_sessions(self, session_manager):
        """Test getting all user sessions."""
        mock_response = Mock()
        
        session_manager.create_session("G-user1", mock_response)
        session_manager.create_session("G-user1", mock_response)
        session_manager.create_session("G-user2", mock_response)
        
        sessions = session_manager.get_user_sessions("G-user1")
        
        assert len(sessions) == 2
    
    def test_invalidate_all_user_sessions(self, session_manager):
        """Test invalidating all user sessions."""
        mock_response = Mock()
        
        session_manager.create_session("G-user1", mock_response)
        session_manager.create_session("G-user1", mock_response)
        session_manager.create_session("G-user2", mock_response)
        
        session_manager.invalidate_all_user_sessions("G-user1")
        
        assert len(session_manager.get_user_sessions("G-user1")) == 0
        assert len(session_manager.get_user_sessions("G-user2")) == 1
    
    def test_cleanup_expired_sessions(self, session_manager):
        """Test cleanup of expired sessions."""
        mock_response = Mock()
        
        # Create sessions
        session1 = session_manager.create_session("G-user1", mock_response)
        session2 = session_manager.create_session("G-user2", mock_response)
        
        # Expire one session
        session_manager._sessions[session1]["expires_at"] = (
            datetime.utcnow() - timedelta(hours=1)
        ).isoformat()
        
        removed = session_manager.cleanup_expired_sessions()
        
        assert removed == 1
        assert session1 not in session_manager._sessions
        assert session2 in session_manager._sessions


class TestGetSessionManager:
    """Tests for get_session_manager singleton."""
    
    def test_singleton_pattern(self):
        """Test singleton returns same instance."""
        with patch('backend.security.auth.get_security_config') as mock_config:
            mock_config.return_value = Mock(
                SESSION_MAX_AGE_HOURS=24,
                GENESIS_ID_MAX_AGE_DAYS=30,
                SESSION_COOKIE_HTTPONLY=True,
                SESSION_COOKIE_SECURE=True,
                SESSION_COOKIE_SAMESITE="lax"
            )
            with patch('backend.security.auth.get_security_logger') as mock_logger:
                mock_logger.return_value = Mock()
                
                # Reset singleton
                import backend.security.auth as auth_module
                auth_module._session_manager = None
                
                from backend.security.auth import get_session_manager
                
                manager1 = get_session_manager()
                manager2 = get_session_manager()
                
                assert manager1 is manager2


class TestAuthDependencies:
    """Tests for FastAPI authentication dependencies."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock()
        request.cookies = {}
        return request
    
    @pytest.mark.asyncio
    async def test_get_current_user_no_genesis_id(self, mock_request):
        """Test get_current_user raises without genesis_id."""
        with patch('backend.security.auth.get_security_logger') as mock_logger:
            mock_logger.return_value = Mock()
            
            from backend.security.auth import get_current_user
            from fastapi import HTTPException
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request, None, None)
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_valid(self, mock_request):
        """Test get_current_user with valid credentials."""
        with patch('backend.security.auth.get_security_logger') as mock_logger:
            mock_logger.return_value = Mock()
            with patch('backend.security.auth.get_security_config') as mock_config:
                mock_config.return_value = Mock(PRODUCTION_MODE=False)
                
                from backend.security.auth import get_current_user
                
                result = await get_current_user(
                    mock_request,
                    genesis_id="G-test-user",
                    session_id=None
                )
                
                assert result["genesis_id"] == "G-test-user"
    
    @pytest.mark.asyncio
    async def test_get_optional_user_no_credentials(self):
        """Test get_optional_user returns None without credentials."""
        from backend.security.auth import get_optional_user
        
        result = await get_optional_user(None, None)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_optional_user_with_credentials(self):
        """Test get_optional_user with credentials."""
        from backend.security.auth import get_optional_user
        
        result = await get_optional_user("G-user", "SS-session")
        
        assert result["genesis_id"] == "G-user"
        assert result["session_id"] == "SS-session"
    
    def test_require_auth_no_cookie(self, mock_request):
        """Test require_auth raises without cookie."""
        mock_request.cookies.get = Mock(return_value=None)
        
        from backend.security.auth import require_auth
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            require_auth(mock_request)
        
        assert exc_info.value.status_code == 401
    
    def test_require_auth_with_cookie(self, mock_request):
        """Test require_auth with valid cookie."""
        mock_request.cookies.get = Mock(return_value="G-test-user")
        
        from backend.security.auth import require_auth
        
        result = require_auth(mock_request)
        
        assert result == "G-test-user"


class TestCSRFProtection:
    """Tests for CSRF protection."""
    
    def test_generate_csrf_token(self):
        """Test CSRF token generation."""
        from backend.security.auth import generate_csrf_token
        
        token = generate_csrf_token()
        
        assert len(token) == 64  # 32 bytes = 64 hex chars
        assert isinstance(token, str)
    
    def test_generate_csrf_token_unique(self):
        """Test CSRF tokens are unique."""
        from backend.security.auth import generate_csrf_token
        
        tokens = [generate_csrf_token() for _ in range(10)]
        
        assert len(set(tokens)) == 10
    
    def test_validate_csrf_token_valid(self):
        """Test CSRF validation with valid token."""
        mock_request = Mock()
        token = "abc123def456"
        mock_request.headers.get = Mock(return_value=token)
        
        from backend.security.auth import validate_csrf_token
        
        result = validate_csrf_token(mock_request, token)
        
        assert result == True
    
    def test_validate_csrf_token_invalid(self):
        """Test CSRF validation with invalid token."""
        mock_request = Mock()
        mock_request.headers.get = Mock(return_value="wrong_token")
        
        from backend.security.auth import validate_csrf_token
        
        result = validate_csrf_token(mock_request, "correct_token")
        
        assert result == False
    
    def test_validate_csrf_token_missing_header(self):
        """Test CSRF validation with missing header."""
        mock_request = Mock()
        mock_request.headers.get = Mock(return_value=None)
        
        from backend.security.auth import validate_csrf_token
        
        result = validate_csrf_token(mock_request, "token")
        
        assert result == False
    
    def test_validate_csrf_token_empty_token(self):
        """Test CSRF validation with empty token."""
        mock_request = Mock()
        mock_request.headers.get = Mock(return_value="header_token")
        
        from backend.security.auth import validate_csrf_token
        
        result = validate_csrf_token(mock_request, "")
        
        assert result == False


class TestSecurityConfig:
    """Tests for security configuration."""
    
    def test_get_security_config(self):
        """Test getting security config."""
        try:
            from backend.security.config import get_security_config
            config = get_security_config()
            assert config is not None
        except ImportError:
            pytest.skip("Security config not available")


class TestValidators:
    """Tests for input validators."""
    
    def test_validators_module_exists(self):
        """Test validators module exists."""
        try:
            from backend.security import validators
            assert validators is not None
        except ImportError:
            pytest.skip("Validators module not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x", "--tb=short"])
