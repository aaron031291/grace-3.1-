import logging
import time
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from functools import wraps
from database.session import SessionLocal
from genesis.comprehensive_tracker import ComprehensiveTracker
from models.genesis_key_models import GenesisKeyType
class GenesisTrackingMiddleware(BaseHTTPMiddleware):
    logger = logging.getLogger(__name__)
    """
    Middleware that tracks all API requests with Genesis Keys.

    Automatically creates Genesis Keys for:
    - All incoming requests
    - Responses
    - Errors
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and create Genesis Key.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response from handler
        """
        # Skip tracking for health checks and static files
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        start_time = time.time()
        genesis_key_id = None

        # Get user/session info from request
        user_id = request.headers.get("X-User-ID")
        session_id = request.headers.get("X-Session-ID")

        try:
            # Create tracker
            db = SessionLocal()
            tracker = ComprehensiveTracker(
                db_session=db,
                user_id=user_id,
                session_id=session_id
            )

            # Track API request
            request_body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    request_body = await request.body()
                    # Re-create request with same body for handler
                    request._body = request_body
                except Exception:
                    pass

            genesis_key = tracker._create_genesis_key(
                key_type=GenesisKeyType.API_REQUEST,
                what_description=f"{request.method} {request.url.path}",
                where_location=request.url.path,
                why_reason="API request",
                who_actor=user_id or "anonymous",
                how_method=f"{request.method} request",
                input_data={
                    "method": request.method,
                    "url": str(request.url),
                    "headers": dict(request.headers),
                    "query_params": dict(request.query_params)
                },
                tags=["api-request", request.method.lower()]
            )
            genesis_key_id = genesis_key.key_id

            # Process request
            response = await call_next(request)

            # Track response
            processing_time = time.time() - start_time

            tracker._create_genesis_key(
                key_type=GenesisKeyType.API_REQUEST,
                what_description=f"Response: {response.status_code} for {request.method} {request.url.path}",
                where_location=request.url.path,
                why_reason="API response",
                who_actor="system",
                how_method=f"Response with status {response.status_code}",
                output_data={
                    "status_code": response.status_code,
                    "processing_time": processing_time
                },
                tags=["api-response", str(response.status_code)],
                parent_key_id=genesis_key_id
            )

            db.close()

            # Add Genesis Key ID to response headers for tracking
            response.headers["X-Genesis-Key"] = genesis_key_id

            return response

        except Exception as e:
            logger.error(f"[GENESIS-MIDDLEWARE] Error tracking request: {e}")

            # Track error
            try:
                if db:
                    tracker._create_genesis_key(
                        key_type=GenesisKeyType.ERROR,
                        what_description=f"Error in {request.method} {request.url.path}: {str(e)}",
                        where_location=request.url.path,
                        why_reason="Request processing error",
                        is_error=True,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        tags=["error", "api-error"],
                        parent_key_id=genesis_key_id
                    )
                    db.close()
            except Exception:
                pass

            raise


def track_file_operation(operation_type: str = "file_operation"):
    """
    Decorator to track file operations with Genesis Keys.

    Usage:
        @track_file_operation("file_upload")
        def upload_file(file_path, ...):
            ...

    Args:
        operation_type: Type of file operation

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            db = SessionLocal()
            tracker = ComprehensiveTracker(db_session=db)

            # Extract file path from args/kwargs
            file_path = kwargs.get('file_path') or (args[0] if args else None)

            try:
                # Track operation start
                start_key = tracker._create_genesis_key(
                    key_type=GenesisKeyType.FILE_OPERATION,
                    what_description=f"{operation_type} starting: {file_path}",
                    where_location=str(file_path) if file_path else "unknown",
                    why_reason=f"File operation: {operation_type}",
                    how_method=func.__name__,
                    tags=["file-operation", operation_type]
                )

                # Execute function
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Track success
                tracker._create_genesis_key(
                    key_type=GenesisKeyType.FILE_OPERATION,
                    what_description=f"{operation_type} completed: {file_path}",
                    where_location=str(file_path) if file_path else "unknown",
                    why_reason=f"File operation completed",
                    how_method=func.__name__,
                    output_data={
                        "execution_time": execution_time,
                        "result": str(result) if result else None
                    },
                    tags=["file-operation", operation_type, "success"],
                    parent_key_id=start_key.key_id
                )

                db.close()
                return result

            except Exception as e:
                # Track error
                tracker._create_genesis_key(
                    key_type=GenesisKeyType.ERROR,
                    what_description=f"{operation_type} failed: {str(e)}",
                    where_location=str(file_path) if file_path else "unknown",
                    why_reason="File operation error",
                    is_error=True,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    tags=["error", "file-operation-error"],
                    parent_key_id=start_key.key_id if 'start_key' in locals() else None
                )
                db.close()
                raise

        return wrapper
    return decorator


def track_database_operation(table_name: str, operation: str):
    """
    Decorator to track database operations with Genesis Keys.

    Usage:
        @track_database_operation("documents", "INSERT")
        def create_document(...):
            ...

    Args:
        table_name: Database table name
        operation: Operation type (INSERT, UPDATE, DELETE)

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            db = SessionLocal()
            tracker = ComprehensiveTracker(db_session=db)

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Track database change
                tracker.track_database_change(
                    table_name=table_name,
                    operation=operation,
                    data_after={"result": str(result) if result else None}
                )

                db.close()
                return result

            except Exception as e:
                logger.error(f"[GENESIS] Database operation error: {e}")
                db.close()
                raise

        return wrapper
    return decorator


class SessionTracker:
    """
    Context manager for tracking a complete session/operation.

    Usage:
        with SessionTracker("librarian-processing") as tracker:
            tracker.track_ai_response(...)
            tracker.track_file_ingestion(...)
    """

    def __init__(self, session_name: str, user_id: Optional[str] = None):
        """
        Initialize session tracker.

        Args:
            session_name: Name of session
            user_id: User identifier
        """
        self.session_name = session_name
        self.user_id = user_id
        self.db = None
        self.tracker = None
        self.session_key_id = None

    def __enter__(self):
        """Start tracking session."""
        self.db = SessionLocal()
        self.tracker = ComprehensiveTracker(
            db_session=self.db,
            user_id=self.user_id
        )

        # Create session start key
        session_key = self.tracker._create_genesis_key(
            key_type=GenesisKeyType.SYSTEM_EVENT,
            what_description=f"Session started: {self.session_name}",
            why_reason="Session tracking",
            tags=["session", "session-start"]
        )
        self.session_key_id = session_key.key_id

        return self.tracker

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End tracking session."""
        if exc_type is not None:
            # Track error
            self.tracker._create_genesis_key(
                key_type=GenesisKeyType.ERROR,
                what_description=f"Session error: {exc_val}",
                why_reason="Session ended with error",
                is_error=True,
                error_type=exc_type.__name__ if exc_type else "Unknown",
                error_message=str(exc_val),
                tags=["session", "session-error"],
                parent_key_id=self.session_key_id
            )
        else:
            # Track successful completion
            self.tracker._create_genesis_key(
                key_type=GenesisKeyType.SYSTEM_EVENT,
                what_description=f"Session completed: {self.session_name}",
                why_reason="Session tracking",
                tags=["session", "session-end"],
                parent_key_id=self.session_key_id
            )

        if self.db:
            self.db.close()

        return False  # Don't suppress exceptions
