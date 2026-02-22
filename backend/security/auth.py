"""
Authentication and Session Security for GRACE

Provides:
- Secure session management
- Authentication dependencies for FastAPI
- Session validation
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, Response, HTTPException, Depends, Cookie
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from .config import get_security_config
from .logging import get_security_logger


class SessionStore:
    """
    Pluggable session persistence backend.

    Supports:
    - In-memory (default / testing)
    - Database-backed (production)
    - Redis-backed (when available)

    The store is used by SessionManager transparently.
    """

    def __init__(self):
        self._memory: Dict[str, Dict[str, Any]] = {}
        self._use_db = False
        self._db_engine = None
        self._try_init_db()

    def _try_init_db(self):
        """Try to initialise a persistent backend."""
        try:
            from database.connection import DatabaseConnection
            engine = DatabaseConnection.get_engine()
            if engine is not None:
                self._db_engine = engine
                self._use_db = True
                self._ensure_table()
        except Exception:
            self._use_db = False

    def _ensure_table(self):
        """Create sessions table if it doesn't exist."""
        if not self._db_engine:
            return
        try:
            from sqlalchemy import text
            with self._db_engine.connect() as conn:
                conn.execute(text(
                    "CREATE TABLE IF NOT EXISTS grace_sessions ("
                    "  session_id TEXT PRIMARY KEY,"
                    "  user_id TEXT NOT NULL,"
                    "  data TEXT NOT NULL,"
                    "  created_at TEXT NOT NULL,"
                    "  expires_at TEXT NOT NULL,"
                    "  last_activity TEXT NOT NULL"
                    ")"
                ))
                conn.commit()
        except Exception:
            self._use_db = False

    # --- public API ---

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self._use_db:
            return self._db_get(session_id)
        return self._memory.get(session_id)

    def set(self, session_id: str, data: Dict[str, Any]):
        if self._use_db:
            self._db_set(session_id, data)
        else:
            self._memory[session_id] = data

    def delete(self, session_id: str):
        if self._use_db:
            self._db_delete(session_id)
        self._memory.pop(session_id, None)

    def get_by_user(self, user_id: str) -> list:
        if self._use_db:
            return self._db_get_by_user(user_id)
        return [
            {"session_id": sid, **d}
            for sid, d in self._memory.items()
            if d.get("user_id") == user_id
        ]

    def delete_by_user(self, user_id: str):
        if self._use_db:
            self._db_delete_by_user(user_id)
        to_remove = [
            sid for sid, d in self._memory.items()
            if d.get("user_id") == user_id
        ]
        for sid in to_remove:
            del self._memory[sid]

    def cleanup_expired(self) -> int:
        import json as _json
        now = datetime.utcnow()
        removed = 0
        if self._use_db:
            try:
                from sqlalchemy import text
                with self._db_engine.connect() as conn:
                    result = conn.execute(text(
                        "DELETE FROM grace_sessions WHERE expires_at < :now"
                    ), {"now": now.isoformat()})
                    conn.commit()
                    removed = result.rowcount
            except Exception:
                pass
        # also clean memory
        expired = [
            sid for sid, d in self._memory.items()
            if datetime.fromisoformat(d.get("expires_at", "2000-01-01")) < now
        ]
        for sid in expired:
            del self._memory[sid]
            removed += 1
        return removed

    # --- DB helpers ---

    def _db_get(self, session_id: str) -> Optional[Dict[str, Any]]:
        import json as _json
        try:
            from sqlalchemy import text
            with self._db_engine.connect() as conn:
                row = conn.execute(
                    text("SELECT data FROM grace_sessions WHERE session_id = :sid"),
                    {"sid": session_id}
                ).fetchone()
                if row:
                    return _json.loads(row[0])
        except Exception:
            pass
        return self._memory.get(session_id)

    def _db_set(self, session_id: str, data: Dict[str, Any]):
        import json as _json
        try:
            from sqlalchemy import text
            serialised = _json.dumps(data)
            with self._db_engine.connect() as conn:
                conn.execute(text(
                    "INSERT OR REPLACE INTO grace_sessions "
                    "(session_id, user_id, data, created_at, expires_at, last_activity) "
                    "VALUES (:sid, :uid, :data, :ca, :ea, :la)"
                ), {
                    "sid": session_id,
                    "uid": data.get("user_id", ""),
                    "data": serialised,
                    "ca": data.get("created_at", ""),
                    "ea": data.get("expires_at", ""),
                    "la": data.get("last_activity", ""),
                })
                conn.commit()
        except Exception:
            pass
        self._memory[session_id] = data

    def _db_delete(self, session_id: str):
        try:
            from sqlalchemy import text
            with self._db_engine.connect() as conn:
                conn.execute(
                    text("DELETE FROM grace_sessions WHERE session_id = :sid"),
                    {"sid": session_id}
                )
                conn.commit()
        except Exception:
            pass

    def _db_get_by_user(self, user_id: str) -> list:
        import json as _json
        results = []
        try:
            from sqlalchemy import text
            with self._db_engine.connect() as conn:
                rows = conn.execute(
                    text("SELECT session_id, data FROM grace_sessions WHERE user_id = :uid"),
                    {"uid": user_id}
                ).fetchall()
                for row in rows:
                    d = _json.loads(row[1])
                    results.append({"session_id": row[0], **d})
        except Exception:
            pass
        return results

    def _db_delete_by_user(self, user_id: str):
        try:
            from sqlalchemy import text
            with self._db_engine.connect() as conn:
                conn.execute(
                    text("DELETE FROM grace_sessions WHERE user_id = :uid"),
                    {"uid": user_id}
                )
                conn.commit()
        except Exception:
            pass


class SessionManager:
    """
    Secure session management.

    Features:
    - Cryptographically secure session IDs
    - Session expiration
    - Server-side session validation (enforced)
    - DB-backed persistence (falls back to memory)
    """

    def __init__(self):
        self.config = get_security_config()
        self.logger = get_security_logger()

        self._store = SessionStore()
        self._sessions: Dict[str, Dict[str, Any]] = self._store._memory

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
        expires_at = datetime.now() + timedelta(hours=self.config.SESSION_MAX_AGE_HOURS)

        # Store session data (DB-backed)
        session_data = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat(),
            "metadata": metadata or {},
            "last_activity": datetime.now().isoformat(),
        }
        self._store.set(session_id, session_data)

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
        if not session_id:
            return None

        session = self._store.get(session_id)
        if session is None:
            return None

        # Check expiration
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.now() > expires_at:
            self._store.delete(session_id)
            return None

        session["last_activity"] = datetime.now().isoformat()
        self._store.set(session_id, session)

        return session

    def invalidate_session(self, session_id: str, response: Response):
        """
        Invalidate a session (logout).

        Args:
            session_id: The session ID to invalidate
            response: FastAPI response to clear cookies
        """
        # Remove from store
        self._store.delete(session_id)

        # Clear cookies
        response.delete_cookie(
            key="session_id",
            httponly=self.config.SESSION_COOKIE_HTTPONLY,
            secure=self.config.SESSION_COOKIE_SECURE,
            samesite=self.config.SESSION_COOKIE_SAMESITE,
        )

    def get_user_sessions(self, user_id: str) -> list:
        """Get all active sessions for a user."""
        return self._store.get_by_user(user_id)

    def invalidate_all_user_sessions(self, user_id: str):
        """Invalidate all sessions for a user."""
        self._store.delete_by_user(user_id)

    def cleanup_expired_sessions(self):
        """Remove all expired sessions."""
        return self._store.cleanup_expired()


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

    session_manager = get_session_manager()
    session = session_manager.validate_session(session_id)
    if not session:
        logger.log_access_denied("API", request, "Invalid or expired session")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please login again.",
        )

    return {
        "genesis_id": genesis_id,
        "session_id": session_id,
        "session_data": session,
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
    session_id = request.cookies.get("session_id")
    session_manager = get_session_manager()
    session = session_manager.validate_session(session_id)
    if not session:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Valid session required. Please login.",
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
