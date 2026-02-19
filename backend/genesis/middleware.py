"""
Genesis Key Middleware for FastAPI.

Automatically tracks all API requests and responses with Genesis Keys.
Assigns Genesis IDs to users on first access.
"""
import logging
import uuid
from datetime import datetime
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
        """Process request and track with Genesis Key."""

        # Generate or retrieve Genesis ID
        genesis_id = self._get_or_create_genesis_id(request)
        session_id = self._get_or_create_session_id(request)

        # Store in request state for use in endpoints
        request.state.genesis_id = genesis_id
        request.state.session_id = session_id

        # Skip tracking for health checks and static files
        if self._should_skip_tracking(request):
            return await call_next(request)

        # Track request start
        start_time = datetime.utcnow()
        request_data = await self._extract_request_data(request)

        # Create Genesis Key for request
        request_key = None
        try:
            request_key = self.genesis_service.create_key(
                key_type=GenesisKeyType.API_REQUEST,
                what_description=f"API Request: {request.method} {request.url.path}",
                who_actor=genesis_id,
                where_location=request.url.path,
                why_reason=f"User action via {request.method} request",
                how_method=f"HTTP {request.method}",
                user_id=genesis_id,
                session_id=session_id,
                input_data={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "headers": dict(request.headers),
                    "body": request_data
                },
                tags=["api_request", request.method.lower(), "input"]
            )
        except Exception as e:
            if not (settings and settings.SUPPRESS_GENESIS_ERRORS):
                logger.error(f"Failed to create request Genesis Key: {e}")

        # Process request
        response = await call_next(request)

        # Track response
        try:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Create Genesis Key for response
            self.genesis_service.create_key(
                key_type=GenesisKeyType.API_REQUEST,
                what_description=f"API Response: {request.method} {request.url.path} [{response.status_code}]",
                who_actor=genesis_id,
                where_location=request.url.path,
                why_reason=f"Response to user request",
                how_method=f"HTTP Response {response.status_code}",
                user_id=genesis_id,
                session_id=session_id,
                parent_key_id=getattr(request_key, 'key_id', None) if request_key else None,
                output_data={
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "headers": dict(response.headers)
                },
                tags=["api_response", request.method.lower(), "output"],
                is_error=(response.status_code >= 400)
            )

            # Add Genesis ID to response headers
            response.headers["X-Genesis-ID"] = genesis_id
            response.headers["X-Session-ID"] = session_id

        except Exception as e:
            if not (settings and settings.SUPPRESS_GENESIS_ERRORS):
                logger.error(f"Failed to create response Genesis Key: {e}")

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

        # Create new Genesis ID
        genesis_id = f"GU-{uuid.uuid4().hex[:16]}"

        # Create user profile
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
                    "first_seen": (user.first_seen or datetime.utcnow()).isoformat(),
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

        # Create new session ID
        session_id = f"SS-{uuid.uuid4().hex[:16]}"
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

        # Skip paths
        skip_paths = [
            "/health",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
            "/static/",
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
