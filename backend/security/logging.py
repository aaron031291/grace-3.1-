"""
Security Event Logging for GRACE

Provides centralized logging for security-related events:
- Authentication attempts
- Rate limit violations
- Suspicious requests
- Input validation failures
- Access control events
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from starlette.requests import Request

from .config import get_security_config


# Configure security logger
security_logger = logging.getLogger("grace.security")
security_logger.setLevel(logging.INFO)

# Create console handler if not already present
if not security_logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] [SECURITY] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)


class SecurityLogger:
    """
    Centralized security event logger.

    Logs security events with structured data for analysis and alerting.
    """

    def __init__(self):
        self.config = get_security_config()
        self.logger = security_logger

    def _get_request_info(self, request: Optional[Request]) -> Dict[str, Any]:
        """Extract relevant information from a request."""
        if not request:
            return {}

        # Get client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return {
            "ip": ip,
            "method": request.method,
            "path": str(request.url.path),
            "user_agent": request.headers.get("User-Agent", "unknown")[:200],
            "genesis_id": request.cookies.get("genesis_id", "anonymous")[:20],
        }

    def log_auth_attempt(
        self,
        success: bool,
        username: Optional[str] = None,
        request: Optional[Request] = None,
        reason: Optional[str] = None
    ):
        """Log an authentication attempt."""
        if not self.config.LOG_FAILED_AUTH and not success:
            return

        request_info = self._get_request_info(request)

        event = {
            "event_type": "AUTH_ATTEMPT",
            "timestamp": datetime.utcnow().isoformat(),
            "success": success,
            "username": username[:50] if username else None,
            "reason": reason,
            **request_info
        }

        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, json.dumps(event))

    def log_rate_limit(
        self,
        request: Optional[Request] = None,
        limit: Optional[str] = None,
        endpoint: Optional[str] = None
    ):
        """Log a rate limit violation."""
        if not self.config.LOG_RATE_LIMIT_EXCEEDED:
            return

        request_info = self._get_request_info(request)

        event = {
            "event_type": "RATE_LIMIT_EXCEEDED",
            "timestamp": datetime.utcnow().isoformat(),
            "limit": limit,
            "endpoint": endpoint,
            **request_info
        }

        self.logger.warning(json.dumps(event))

    def log_suspicious_request(
        self,
        request: Optional[Request] = None,
        reason: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log a suspicious request."""
        if not self.config.LOG_SUSPICIOUS_REQUESTS:
            return

        request_info = self._get_request_info(request)

        event = {
            "event_type": "SUSPICIOUS_REQUEST",
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "details": details,
            **request_info
        }

        self.logger.warning(json.dumps(event))

    def log_validation_failure(
        self,
        field_name: str,
        error: str,
        request: Optional[Request] = None
    ):
        """Log an input validation failure."""
        request_info = self._get_request_info(request)

        event = {
            "event_type": "VALIDATION_FAILURE",
            "timestamp": datetime.utcnow().isoformat(),
            "field": field_name,
            "error": error,
            **request_info
        }

        self.logger.warning(json.dumps(event))

    def log_access_denied(
        self,
        resource: str,
        request: Optional[Request] = None,
        reason: Optional[str] = None
    ):
        """Log an access denied event."""
        request_info = self._get_request_info(request)

        event = {
            "event_type": "ACCESS_DENIED",
            "timestamp": datetime.utcnow().isoformat(),
            "resource": resource,
            "reason": reason,
            **request_info
        }

        self.logger.warning(json.dumps(event))

    def log_security_event(
        self,
        event_type: str,
        request: Optional[Request] = None,
        details: Optional[Dict] = None,
        level: int = logging.INFO
    ):
        """Log a generic security event."""
        if not self.config.LOG_SECURITY_EVENTS:
            return

        request_info = self._get_request_info(request)

        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details,
            **request_info
        }

        self.logger.log(level, json.dumps(event))


# Singleton instance
_security_logger: Optional[SecurityLogger] = None


def get_security_logger() -> SecurityLogger:
    """Get the security logger singleton."""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityLogger()
    return _security_logger


def log_security_event(
    event_type: str,
    request: Optional[Request] = None,
    details: Optional[Dict] = None,
    level: int = logging.INFO
):
    """Convenience function to log a security event."""
    logger = get_security_logger()
    logger.log_security_event(event_type, request, details, level)
