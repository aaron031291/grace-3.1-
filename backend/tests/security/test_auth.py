import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta
from fastapi import Request, Response
from backend.security.auth import (
    SessionManager, 
    generate_csrf_token, 
    validate_csrf_token
)

def test_session_manager_create_and_validate():
    manager = SessionManager()
    response_mock = MagicMock(spec=Response)
    
    session_id = manager.create_session("user123", response_mock)
    assert session_id.startswith("SS-")
    assert response_mock.set_cookie.call_count == 2
    
    # Validate
    session_data = manager.validate_session(session_id)
    assert session_data is not None
    assert session_data["user_id"] == "user123"

def test_session_manager_invalidate():
    manager = SessionManager()
    response_mock = MagicMock(spec=Response)
    
    session_id = manager.create_session("user123", response_mock)
    
    manager.invalidate_session(session_id, response_mock)
    assert response_mock.delete_cookie.call_count == 1
    assert manager.validate_session(session_id) is None

def test_session_expiration():
    manager = SessionManager()
    response_mock = MagicMock(spec=Response)
    
    session_id = manager.create_session("user123", response_mock)
    
    # Manually expire
    manager._sessions[session_id]["expires_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    
    assert manager.validate_session(session_id) is None
    assert session_id not in manager._sessions

def test_csrf_tokens():
    token = generate_csrf_token()
    assert len(token) == 64
    
    request_mock = MagicMock(spec=Request)
    request_mock.headers = {"X-CSRF-Token": token}
    
    assert validate_csrf_token(request_mock, token) is True
    assert validate_csrf_token(request_mock, "invalid_token") is False
    
    request_mock.headers = {}
    assert validate_csrf_token(request_mock, token) is False

if __name__ == "__main__":
    pytest.main(['-v', __file__])
