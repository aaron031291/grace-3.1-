"""
GRACE Personnel Tracking Middleware

Automatically tracks personnel input/output through API requests.
Integrates with the Genesis Key personnel tracking system.
"""

import logging
import time
from datetime import datetime
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class PersonnelTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track personnel activity.
    
    Features:
    - Tracks API requests as activities
    - Measures request duration
    - Captures input/output sizes
    - Integrates with session tracking
    """
    
    def __init__(
        self,
        app,
        excluded_paths: Optional[list] = None,
        max_body_capture: int = 10000,
        track_responses: bool = True,
    ):
        super().__init__(app)
        
        self._excluded_paths = excluded_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/personnel/stats",
            "/static",
        ]
        
        self._max_body_capture = max_body_capture
        self._track_responses = track_responses
        
        logger.info("[PERSONNEL-MIDDLEWARE] Personnel tracking middleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track activity."""
        
        # Skip excluded paths
        if self._should_skip(request.url.path):
            return await call_next(request)
        
        # Get session ID from cookie or header
        session_id = self._get_session_id(request)
        
        if not session_id:
            # No session - just pass through
            return await call_next(request)
        
        # Track timing
        start_time = time.time()
        
        # Capture request body (if small enough)
        input_data = None
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if len(body) <= self._max_body_capture:
                    input_data = body.decode("utf-8", errors="ignore")
        except Exception:
            pass
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Capture response (if enabled and small enough)
        output_data = None
        output_size = 0
        
        if self._track_responses:
            try:
                # Note: Can't easily capture streaming responses
                content_length = response.headers.get("content-length")
                if content_length:
                    output_size = int(content_length)
            except Exception:
                pass
        
        # Record activity
        self._record_activity(
            session_id=session_id,
            method=request.method,
            path=request.url.path,
            input_data=input_data,
            input_size=len(input_data) if input_data else 0,
            output_size=output_size,
            duration_ms=duration_ms,
            status_code=response.status_code,
        )
        
        return response
    
    def _should_skip(self, path: str) -> bool:
        """Check if path should be skipped."""
        for excluded in self._excluded_paths:
            if path.startswith(excluded):
                return True
        return False
    
    def _get_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request."""
        # Try cookie first
        session_id = request.cookies.get("session_id")
        if session_id:
            return session_id
        
        # Try header
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            return session_id
        
        # Try request state (set by auth middleware)
        if hasattr(request.state, "session_id"):
            return request.state.session_id
        
        return None
    
    def _record_activity(
        self,
        session_id: str,
        method: str,
        path: str,
        input_data: Optional[str],
        input_size: int,
        output_size: int,
        duration_ms: int,
        status_code: int,
    ):
        """Record the activity to personnel tracker."""
        try:
            from genesis.personnel_tracker import (
                get_personnel_tracker,
                ActivityType,
            )
            
            tracker = get_personnel_tracker()
            
            # Determine activity type based on method
            activity_type_map = {
                "GET": ActivityType.QUERY,
                "POST": ActivityType.INPUT,
                "PUT": ActivityType.INPUT,
                "PATCH": ActivityType.INPUT,
                "DELETE": ActivityType.COMMAND,
            }
            
            activity_type = activity_type_map.get(method, ActivityType.API_CALL)
            
            # Check for errors
            if status_code >= 400:
                activity_type = ActivityType.ERROR
            
            tracker.record_activity(
                session_id=session_id,
                activity_type=activity_type,
                input_data=input_data,
                output_data=None,  # Don't capture full response
                endpoint=f"{method} {path}",
                duration_ms=duration_ms,
                metadata={
                    "status_code": status_code,
                    "input_size": input_size,
                    "output_size": output_size,
                },
            )
            
        except Exception as e:
            logger.debug(f"[PERSONNEL-MIDDLEWARE] Activity recording failed: {e}")


class SessionTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track session lifecycle.
    
    Automatically logs sessions in/out based on activity patterns.
    """
    
    def __init__(
        self,
        app,
        session_timeout_minutes: int = 30,
    ):
        super().__init__(app)
        self._timeout = session_timeout_minutes
        
        logger.info("[SESSION-MIDDLEWARE] Session tracking middleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track session activity."""
        
        # Get genesis ID
        genesis_id = self._get_genesis_id(request)
        
        if genesis_id:
            # Check/create session
            self._ensure_session(genesis_id, request)
        
        response = await call_next(request)
        
        return response
    
    def _get_genesis_id(self, request: Request) -> Optional[str]:
        """Get genesis ID from request."""
        # Cookie
        genesis_id = request.cookies.get("genesis_id")
        if genesis_id:
            return genesis_id
        
        # Header
        genesis_id = request.headers.get("X-Genesis-ID")
        if genesis_id:
            return genesis_id
        
        # Request state
        if hasattr(request.state, "genesis_id"):
            return request.state.genesis_id
        
        return None
    
    def _ensure_session(self, genesis_id: str, request: Request):
        """Ensure user has an active session."""
        try:
            from genesis.personnel_tracker import get_personnel_tracker
            
            tracker = get_personnel_tracker()
            
            # Check if user has active session
            for session_id, session in tracker._active_sessions.items():
                if session["genesis_id"] == genesis_id:
                    # Update last activity
                    session["last_activity"] = datetime.utcnow()
                    
                    # Store session ID in request state
                    request.state.session_id = session_id
                    return
            
            # No active session - create one
            ip = None
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip = forwarded.split(",")[0].strip()
            elif request.client:
                ip = request.client.host
            
            session_id = tracker.record_login(
                genesis_id=genesis_id,
                ip_address=ip,
                user_agent=request.headers.get("User-Agent"),
                metadata={"auto_created": True},
            )
            
            request.state.session_id = session_id
            
        except Exception as e:
            logger.debug(f"[SESSION-MIDDLEWARE] Session tracking failed: {e}")


def setup_personnel_tracking(app):
    """
    Setup personnel tracking middleware.
    
    Call this in your FastAPI app setup:
    
        from genesis.personnel_middleware import setup_personnel_tracking
        setup_personnel_tracking(app)
    """
    app.add_middleware(PersonnelTrackingMiddleware)
    app.add_middleware(SessionTrackingMiddleware)
    
    logger.info("[PERSONNEL-TRACKING] Personnel tracking enabled")
