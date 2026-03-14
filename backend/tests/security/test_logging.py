import pytest
import logging
import json
from unittest.mock import MagicMock, patch
from backend.security.logging import SecurityLogger, get_security_logger, log_security_event

def test_security_logger_singleton():
    l1 = get_security_logger()
    l2 = get_security_logger()
    assert l1 is l2

def test_get_request_info():
    logger = get_security_logger()
    
    request = MagicMock()
    request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1", "User-Agent": "TestAgent"}
    request.method = "POST"
    request.url.path = "/api/login"
    request.cookies = {"genesis_id": "user123"}
    
    info = logger._get_request_info(request)
    assert info["ip"] == "192.168.1.1"
    assert info["method"] == "POST"
    assert info["path"] == "/api/login"
    assert info["user_agent"] == "TestAgent"
    assert info["genesis_id"] == "user123"

@patch.object(logging.Logger, 'log')
def test_log_auth_attempt_failure(mock_log):
    logger = get_security_logger()
    logger.config.LOG_FAILED_AUTH = True
    
    logger.log_auth_attempt(success=False, username="admin_hacker")
    
    assert mock_log.call_count == 1
    logged_json = mock_log.call_args[0][1]
    data = json.loads(logged_json)
    assert data["event_type"] == "AUTH_ATTEMPT"
    assert data["success"] is False
    assert data["username"] == "admin_hacker"

@patch.object(logging.Logger, 'log')
def test_log_security_event_convenience(mock_log):
    logger = get_security_logger()
    logger.config.LOG_SECURITY_EVENTS = True
    
    log_security_event("TEST_EVENT", details={"k": "v"})
    
    assert mock_log.call_count == 1
    logged_json = mock_log.call_args[0][1]
    data = json.loads(logged_json)
    assert data["event_type"] == "TEST_EVENT"
    assert data["details"]["k"] == "v"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
