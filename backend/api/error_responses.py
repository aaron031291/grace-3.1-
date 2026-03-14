"""Structured error response helpers for GRACE API."""
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import logging
import traceback

logger = logging.getLogger(__name__)


def error_response(
    status_code: int,
    message: str,
    error_type: str = "internal_error",
    details: dict = None,
) -> JSONResponse:
    """Return a structured JSON error response."""
    body = {
        "ok": False,
        "error": {
            "type": error_type,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def handle_api_error(e: Exception, context: str = "API") -> JSONResponse:
    """Log and return a structured 500 error for unhandled exceptions."""
    logger.error(f"[{context}] Unhandled error: {e}", exc_info=True)
    return error_response(
        status_code=500,
        message=f"{context} encountered an internal error",
        error_type="internal_error",
    )
