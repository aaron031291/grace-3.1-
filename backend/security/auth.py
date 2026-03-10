"""
Authentication and Session Security for GRACE

Provides:
- Secure session management
- Authentication dependencies for FastAPI
- Session validation
"""

import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, Response, HTTPException, Depends, Cookie
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from .config import get_security_config
from .logging import get_security_logger


class SessionManager:
    """
    Secure session management.

    Features:
    - Cryptographically secure session IDs
    - Session expiration
    - Server-side session validation (optional)
    """

    def __init__(self):
        self.config = get_security_config()
        self.logger = get_security_logger()

        # In-memory session store (use Redis in production)
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(
        self,
        user_id: str,
        response: Response,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Create a new session for a user.

        Args:
            user_id: The user's Genesis ID
            response: FastAPI response to set cookies
            metadata: Optional session metadata

        Returns:
            Session ID
        """
        # Generate cryptographically secure session ID
        session_id = f"SS-{secrets.token_hex(16)}"

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.config.SESSION_MAX_AGE_HOURS)

        # Store session data
        self._sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at.isoformat(),
            "metadata": metadata or {},
            "last_activity": datetime.now(timezone.utc).isoformat(),
        }

        # Set session cookie
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=self.config.SESSION_MAX_AGE_HOURS * 3600,
            httponly=self.config.SESSION_COOKIE_HTTPONLY,
            secure=self.config.SESSION_COOKIE_SECURE,
            samesite=self.config.SESSION_COOKIE_SAMESITE,
        )

        # Set Genesis ID cookie with shorter expiration
        response.set_cookie(
            key="genesis_id",
            value=user_id,
            max_age=self.config.GENESIS_ID_MAX_AGE_DAYS * 86400,
            httponly=self.config.SESSION_COOKIE_HTTPONLY,
            secure=self.config.SESSION_COOKIE_SECURE,
            samesite=self.config.SESSION_COOKIE_SAMESITE,
        )

        return session_id

    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session ID.

        Args:
            session_id: The session ID to validate

        Returns:
            Session data if valid, None otherwise
        """
        if not session_id or session_id not in self._sessions:
            return None

        session = self._sessions[session_id]

        # Check expiration
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            # Session expired, remove it
            del self._sessions[session_id]
            return None

        # Update last activity
        session["last_activity"] = datetime.now(timezone.utc).isoformat()

        return session

    def invalidate_session(self, session_id: str, response: Response):
        """
        Invalidate a session (logout).

        Args:
            session_id: The session ID to invalidate
            response: FastAPI response to clear cookies
        """
        # Remove from store
        if session_id in self._sessions:
            del self._sessions[session_id]

        # Clear cookies
        response.delete_cookie(
            key="session_id",
            httponly=self.config.SESSION_COOKIE_HTTPONLY,
            secure=self.config.SESSION_COOKIE_SECURE,
            samesite=self.config.SESSION_COOKIE_SAMESITE,
        )

    def get_user_sessions(self, user_id: str) -> list:
        """Get all active sessions for a user."""
        return [
            {"session_id": sid, **data}
            for sid, data in self._sessions.items()
            if data["user_id"] == user_id
        ]

    def invalidate_all_user_sessions(self, user_id: str):
        """Invalidate all sessions for a user."""
        to_remove = [
            sid for sid, data in self._sessions.items()
            if data["user_id"] == user_id
        ]
        for sid in to_remove:
            del self._sessions[sid]

    def cleanup_expired_sessions(self):
        """Remove all expired sessions."""
        now = datetime.now(timezone.utc)
        to_remove = [
            sid for sid, data in self._sessions.items()
            if datetime.fromisoformat(data["expires_at"]) < now
        ]
        for sid in to_remove:
            del self._sessions[sid]
        return len(to_remove)


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the session manager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


# ==================== FastAPI Dependencies ====================


async def get_current_user(
    request: Request,
    genesis_id: Optional[str] = Cookie(None),
    session_id: Optional[str] = Cookie(None),
) -> Dict[str, Any]:
    """
    FastAPI dependency to get the current authenticated user.

    Raises HTTPException if not authenticated.
    """
    logger = get_security_logger()

    if not genesis_id:
        logger.log_access_denied("API", request, "No Genesis ID")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please login.",
            headers={"WWW-Authenticate": "Cookie"},
        )

    # For strict session validation, uncomment below:
    # session_manager = get_session_manager()
    # session = session_manager.validate_session(session_id)
    # if not session:
    #     logger.log_access_denied("API", request, "Invalid session")
    #     raise HTTPException(
    #         status_code=HTTP_401_UNAUTHORIZED,
    #         detail="Session expired. Please login again.",
    #     )

    return {
        "genesis_id": genesis_id,
        "session_id": session_id,
    }


async def get_optional_user(
    genesis_id: Optional[str] = Cookie(None),
    session_id: Optional[str] = Cookie(None),
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to optionally get the current user.

    Returns None if not authenticated (doesn't raise exception).
    """
    if not genesis_id:
        return None

    return {
        "genesis_id": genesis_id,
        "session_id": session_id,
    }


def require_auth(request: Request):
    """
    FastAPI dependency that requires authentication.

    Use as: @app.get("/protected", dependencies=[Depends(require_auth)])
    """
    genesis_id = request.cookies.get("genesis_id")
    if not genesis_id:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return genesis_id


# ==================== CSRF Protection ====================


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_hex(32)


def validate_csrf_token(request: Request, token: str) -> bool:
    """
    Validate a CSRF token.

    The token should be sent in a header (X-CSRF-Token) and match
    the token stored in the session/cookie.
    """
    # Get token from header
    header_token = request.headers.get("X-CSRF-Token")

    if not header_token or not token:
        return False

    # Constant-time comparison to prevent timing attacks
    return secrets.compare_digest(header_token, token)
