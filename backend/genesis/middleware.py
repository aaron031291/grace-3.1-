"""
Genesis Key Middleware for FastAPI.

Automatically tracks all API requests and responses with Genesis Keys.
Assigns Genesis IDs to users on first access.
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import FastAPI

from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKeyType
from genesis.kb_integration import get_kb_integration

try:
    from settings import settings
except ImportError:
    settings = None

logger = logging.getLogger(__name__)


class GenesisKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tracks all API requests with Genesis Keys.

    Features:
    - Assigns Genesis ID to users on first access
    - Tracks all inputs (requests) and outputs (responses)
    - Creates session IDs for tracking user journeys
    - Auto-populates to knowledge base
    """

    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.genesis_service = get_genesis_service()
        self.kb_integration = get_kb_integration()

    async def dispatch(self, request: Request, call_next):
        # Generate or retrieve Genesis ID
        genesis_id = self._get_or_create_genesis_id(request)
        session_id = self._get_or_create_session_id(request)

        # Store in request state for use in endpoints
        request.state.genesis_id = genesis_id
        request.state.session_id = session_id

        # Skip tracking for health checks, high-frequency, and static paths
        if self._should_skip_tracking(request):
            return await call_next(request)

        start_time = datetime.now(timezone.utc)

        # Process request FIRST — zero blocking before response
        response = await call_next(request)

        # Set cookie if it was newly generated
        if not request.cookies.get("genesis_id"):
            response.set_cookie(key="genesis_id", value=genesis_id, max_age=31536000)

        response.headers["X-Genesis-ID"] = genesis_id
        response.headers["X-Session-ID"] = session_id

        # Fire-and-forget: create genesis keys in background thread (no blocking)
        try:
            from core.async_parallel import run_background
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            method = request.method
            path = request.url.path
            status_code = response.status_code
            _svc = self.genesis_service

            def _track():
                try:
                    _svc.create_key(
                        key_type=GenesisKeyType.API_REQUEST,
                        what_description=f"API {method} {path} [{status_code}]",
                        who_actor=genesis_id,
                        where_location=path,
                        why_reason=f"HTTP {method} request",
                        how_method=f"HTTP {method}",
                        user_id=genesis_id,
                        session_id=session_id,
                        output_data={"status_code": status_code, "duration_ms": round(duration_ms, 1)},
                        tags=["api_request", method.lower()],
                        is_error=(status_code >= 400),
                    )
                except Exception:
                    pass

            run_background(_track, f"genesis:{path}")
        except Exception:
            pass

        return response

    def _get_or_create_genesis_id(self, request: Request) -> str:
        """
        Get or create Genesis ID for user.

        Priority:
        1. X-Genesis-ID header
        2. genesis_id cookie
        3. Create new Genesis ID
        """
        # Check header
        genesis_id = request.headers.get("X-Genesis-ID")
        if genesis_id and genesis_id.startswith("GU-"):
            return genesis_id

        # Check cookie
        genesis_id = request.cookies.get("genesis_id")
        if genesis_id and genesis_id.startswith("GU-"):
            return genesis_id

        # Create deterministic Genesis ID (no random, no model) from request fingerprint
        seed = f"{request.client.host if request.client else ''}|{request.headers.get('user-agent', '')}|{request.url.path}"
        genesis_id = self.genesis_service.generate_user_id(seed)

        # Create user profile ONLY if we generated a new one
        try:
            user = self.genesis_service.get_or_create_user(
                user_id=genesis_id,
                username=f"User_{genesis_id[-8:]}",
                email=None
            )

            # Save profile to knowledge base
            self.kb_integration.save_user_profile(
                user_id=genesis_id,
                profile_data={
                    "user_id": genesis_id,
                    "username": user.username,
                    "first_seen": (user.first_seen or datetime.now(timezone.utc)).isoformat(),
                    "user_agent": request.headers.get("user-agent"),
                    "initial_ip": request.client.host if request.client else None,
                    "initial_path": request.url.path
                }
            )

            logger.info(f"Created new Genesis ID: {genesis_id}")

        except Exception as e:
            if not (settings and settings.SUPPRESS_GENESIS_ERRORS):
                logger.error(f"Failed to create user profile: {e}")

        return genesis_id

    def _get_or_create_session_id(self, request: Request) -> str:
        """
        Get or create session ID.

        Sessions track a user's journey through the application.
        """
        # Check header
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            return session_id

        # Check cookie
        session_id = request.cookies.get("session_id")
        if session_id:
            return session_id

        # Deterministic session ID (no random) from genesis + path + date-hour
        hour_bucket = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
        gid = getattr(request.state, "genesis_id", "") or ""
        seed = f"{gid}|{request.url.path}|{hour_bucket}"
        session_id = f"SS-{hashlib.sha256(seed.encode()).hexdigest()[:16]}"
        return session_id

    async def _extract_request_data(self, request: Request) -> Optional[dict]:
        """Extract request body data if available."""
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                # Clone the body for reading
                body = await request.body()
                if body:
                    # Try to parse as JSON
                    try:
                        import json
                        return json.loads(body)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        return {"raw": body.decode('utf-8', errors='ignore')[:1000]}
        except Exception as e:
            logger.debug(f"Could not extract request data: {e}")
        return None

    def _should_skip_tracking(self, request: Request) -> bool:
        """Determine if request should be skipped from tracking."""
        path = request.url.path

        # Skip high-frequency and internal paths from genesis tracking
        skip_paths = [
            "/health",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
            "/static/",
            "/kpi/",
            "/api/probe/",
            "/api/autonomous/status",
            "/api/component-health/",
            "/api/bi/",
            "/monitoring/",
            "/telemetry/",
            "/brain/directory",
        ]

        for skip_path in skip_paths:
            if path.startswith(skip_path):
                return True

        return False


def add_genesis_middleware(app: FastAPI):
    """
    Add Genesis Key middleware to FastAPI app.

    Call this during app initialization:
        app = FastAPI()
        add_genesis_middleware(app)
    """
    app.add_middleware(GenesisKeyMiddleware)
    logger.info("Genesis Key middleware enabled - tracking all requests")
