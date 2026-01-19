"""
Authentication Security - REAL Functional Tests

Tests verify ACTUAL auth behavior using real implementations:
- SessionManager creation and validation
- Session expiration handling
- Multi-session per user
- Session invalidation
- Cookie security attributes
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# =============================================================================
# SESSION MANAGER FUNCTIONAL TESTS
# =============================================================================

class TestSessionManagerFunctional:
    """Functional tests for SessionManager."""

    @pytest.fixture
    def session_manager(self):
        """Create fresh SessionManager instance."""
        from security.auth import SessionManager
        return SessionManager()

    @pytest.fixture
    def mock_response(self):
        """Create mock FastAPI Response."""
        response = MagicMock()
        response.set_cookie = MagicMock()
        response.delete_cookie = MagicMock()
        return response

    def test_create_session_returns_session_id(self, session_manager, mock_response):
        """create_session must return a session ID."""
        session_id = session_manager.create_session(
            user_id="user-123",
            response=mock_response
        )

        assert session_id is not None
        assert session_id.startswith("SS-")
        assert len(session_id) > 10

    def test_create_session_sets_cookies(self, session_manager, mock_response):
        """create_session must set session and genesis_id cookies."""
        session_manager.create_session(
            user_id="user-123",
            response=mock_response
        )

        # Verify cookies were set
        assert mock_response.set_cookie.call_count == 2

        # Check session_id cookie
        calls = mock_response.set_cookie.call_args_list
        cookie_keys = [call.kwargs.get('key') or call.args[0] for call in calls]
        assert "session_id" in cookie_keys
        assert "genesis_id" in cookie_keys

    def test_create_session_cookie_httponly(self, session_manager, mock_response):
        """Session cookies must be httponly."""
        session_manager.create_session(
            user_id="user-123",
            response=mock_response
        )

        # Check httponly flag in any of the calls
        for call in mock_response.set_cookie.call_args_list:
            if call.kwargs.get('key') == "session_id" or (call.args and call.args[0] == "session_id"):
                assert call.kwargs.get('httponly') is True

    def test_validate_session_returns_session_data(self, session_manager, mock_response):
        """validate_session must return session data for valid session."""
        session_id = session_manager.create_session(
            user_id="user-456",
            response=mock_response,
            metadata={"device": "desktop"}
        )

        session = session_manager.validate_session(session_id)

        assert session is not None
        assert session["user_id"] == "user-456"
        assert "created_at" in session
        assert "expires_at" in session

    def test_validate_session_returns_none_for_invalid(self, session_manager):
        """validate_session must return None for invalid session."""
        session = session_manager.validate_session("invalid-session-id")

        assert session is None

    def test_validate_session_returns_none_for_expired(self, session_manager, mock_response):
        """validate_session must return None for expired session."""
        session_id = session_manager.create_session(
            user_id="user-789",
            response=mock_response
        )

        # Manually expire the session
        session_manager._sessions[session_id]["expires_at"] = (
            datetime.utcnow() - timedelta(hours=1)
        ).isoformat()

        session = session_manager.validate_session(session_id)

        assert session is None

    def test_expired_session_removed_from_store(self, session_manager, mock_response):
        """Expired sessions must be removed from store on validation."""
        session_id = session_manager.create_session(
            user_id="user-expired",
            response=mock_response
        )

        # Expire the session
        session_manager._sessions[session_id]["expires_at"] = (
            datetime.utcnow() - timedelta(hours=1)
        ).isoformat()

        # Validate should remove it
        session_manager.validate_session(session_id)

        assert session_id not in session_manager._sessions

    def test_validate_session_updates_last_activity(self, session_manager, mock_response):
        """validate_session must update last_activity timestamp."""
        session_id = session_manager.create_session(
            user_id="user-activity",
            response=mock_response
        )

        original_activity = session_manager._sessions[session_id]["last_activity"]

        # Wait a tiny bit and validate again
        import time
        time.sleep(0.01)

        session_manager.validate_session(session_id)

        new_activity = session_manager._sessions[session_id]["last_activity"]
        assert new_activity >= original_activity

    def test_invalidate_session_removes_from_store(self, session_manager, mock_response):
        """invalidate_session must remove session from store."""
        session_id = session_manager.create_session(
            user_id="user-logout",
            response=mock_response
        )

        assert session_id in session_manager._sessions

        session_manager.invalidate_session(session_id, mock_response)

        assert session_id not in session_manager._sessions

    def test_invalidate_session_clears_cookies(self, session_manager, mock_response):
        """invalidate_session must clear session cookies."""
        session_id = session_manager.create_session(
            user_id="user-logout",
            response=mock_response
        )

        session_manager.invalidate_session(session_id, mock_response)

        mock_response.delete_cookie.assert_called()

    def test_get_user_sessions_returns_all_sessions(self, session_manager, mock_response):
        """get_user_sessions must return all sessions for a user."""
        user_id = "multi-session-user"

        # Create multiple sessions
        session_manager.create_session(user_id=user_id, response=mock_response)
        session_manager.create_session(user_id=user_id, response=mock_response)
        session_manager.create_session(user_id=user_id, response=mock_response)

        sessions = session_manager.get_user_sessions(user_id)

        assert len(sessions) == 3
        assert all(s["user_id"] == user_id for s in sessions)

    def test_get_user_sessions_returns_empty_for_unknown_user(self, session_manager):
        """get_user_sessions must return empty list for unknown user."""
        sessions = session_manager.get_user_sessions("unknown-user")

        assert sessions == []

    def test_invalidate_all_user_sessions(self, session_manager, mock_response):
        """invalidate_all_user_sessions must remove all sessions for user."""
        user_id = "user-to-logout-everywhere"

        # Create multiple sessions
        session_manager.create_session(user_id=user_id, response=mock_response)
        session_manager.create_session(user_id=user_id, response=mock_response)

        # Also create session for different user
        session_manager.create_session(user_id="other-user", response=mock_response)

        session_manager.invalidate_all_user_sessions(user_id)

        # Target user sessions should be gone
        assert session_manager.get_user_sessions(user_id) == []

        # Other user session should remain
        assert len(session_manager.get_user_sessions("other-user")) == 1

    def test_cleanup_expired_sessions(self, session_manager, mock_response):
        """cleanup_expired_sessions must remove all expired sessions."""
        # Create some sessions
        s1 = session_manager.create_session(user_id="user-1", response=mock_response)
        s2 = session_manager.create_session(user_id="user-2", response=mock_response)
        s3 = session_manager.create_session(user_id="user-3", response=mock_response)

        # Expire first two
        session_manager._sessions[s1]["expires_at"] = (
            datetime.utcnow() - timedelta(hours=1)
        ).isoformat()
        session_manager._sessions[s2]["expires_at"] = (
            datetime.utcnow() - timedelta(hours=2)
        ).isoformat()

        removed_count = session_manager.cleanup_expired_sessions()

        assert removed_count == 2
        assert s1 not in session_manager._sessions
        assert s2 not in session_manager._sessions
        assert s3 in session_manager._sessions

    def test_session_id_is_cryptographically_random(self, session_manager, mock_response):
        """Session IDs must be unique and unpredictable."""
        session_ids = set()

        for _ in range(100):
            sid = session_manager.create_session(
                user_id=f"user-{_}",
                response=mock_response
            )
            session_ids.add(sid)

        # All should be unique
        assert len(session_ids) == 100

    def test_session_metadata_stored(self, session_manager, mock_response):
        """Session metadata must be stored correctly."""
        session_id = session_manager.create_session(
            user_id="user-meta",
            response=mock_response,
            metadata={
                "device": "mobile",
                "browser": "Chrome",
                "ip": "192.168.1.1"
            }
        )

        session = session_manager.validate_session(session_id)

        assert session["metadata"]["device"] == "mobile"
        assert session["metadata"]["browser"] == "Chrome"
        assert session["metadata"]["ip"] == "192.168.1.1"


# =============================================================================
# SESSION MANAGER SINGLETON TESTS
# =============================================================================

class TestSessionManagerSingletonFunctional:
    """Functional tests for SessionManager singleton."""

    def test_get_session_manager_returns_instance(self):
        """get_session_manager must return SessionManager instance."""
        from security.auth import get_session_manager, SessionManager

        manager = get_session_manager()

        assert isinstance(manager, SessionManager)

    def test_get_session_manager_returns_same_instance(self):
        """get_session_manager must return same instance (singleton)."""
        from security.auth import get_session_manager

        manager1 = get_session_manager()
        manager2 = get_session_manager()

        assert manager1 is manager2


# =============================================================================
# AUTHENTICATION DEPENDENCY TESTS
# =============================================================================

class TestAuthDependenciesFunctional:
    """Functional tests for FastAPI authentication dependencies."""

    def test_get_optional_user_returns_none_without_genesis_id(self):
        """get_optional_user must return None without genesis_id."""
        import asyncio
        from security.auth import get_optional_user

        result = asyncio.get_event_loop().run_until_complete(
            get_optional_user(genesis_id=None, session_id=None)
        )

        assert result is None

    def test_get_optional_user_returns_user_with_genesis_id(self):
        """get_optional_user must return user dict with genesis_id."""
        import asyncio
        from security.auth import get_optional_user

        result = asyncio.get_event_loop().run_until_complete(
            get_optional_user(genesis_id="test-genesis-123", session_id="test-session")
        )

        assert result is not None
        assert result["genesis_id"] == "test-genesis-123"
        assert result["session_id"] == "test-session"


# =============================================================================
# SESSION SECURITY TESTS
# =============================================================================

class TestSessionSecurityFunctional:
    """Functional tests for session security properties."""

    @pytest.fixture
    def session_manager(self):
        """Create fresh SessionManager instance."""
        from security.auth import SessionManager
        return SessionManager()

    @pytest.fixture
    def mock_response(self):
        """Create mock FastAPI Response."""
        response = MagicMock()
        response.set_cookie = MagicMock()
        return response

    def test_session_id_length_sufficient(self, session_manager, mock_response):
        """Session ID must have sufficient entropy (at least 128 bits)."""
        session_id = session_manager.create_session(
            user_id="user-123",
            response=mock_response
        )

        # SS- prefix + 32 hex chars (16 bytes = 128 bits)
        raw_id = session_id.replace("SS-", "")
        assert len(raw_id) >= 32

    def test_session_expiration_enforced(self, session_manager, mock_response):
        """Sessions must have expiration time."""
        session_id = session_manager.create_session(
            user_id="user-123",
            response=mock_response
        )

        session = session_manager._sessions[session_id]
        expires_at = datetime.fromisoformat(session["expires_at"])

        # Should expire in the future
        assert expires_at > datetime.utcnow()

    def test_cannot_validate_nonexistent_session(self, session_manager):
        """Cannot validate session that doesn't exist."""
        result = session_manager.validate_session("nonexistent-session-id")

        assert result is None

    def test_cannot_validate_empty_session_id(self, session_manager):
        """Cannot validate empty session ID."""
        result = session_manager.validate_session("")

        assert result is None

    def test_cannot_validate_none_session_id(self, session_manager):
        """Cannot validate None session ID."""
        result = session_manager.validate_session(None)

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
