import logging
import json
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
from functools import wraps
import time
import uuid
logger = logging.getLogger(__name__)

class StructuredLogFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.
    Outputs logs in a format suitable for log aggregation systems.
    """

    def __init__(self, service_name: str = "grace", environment: str = "development"):
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": self.environment,
        }

        # Add location info
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
            "module": record.module,
        }

        # Add context from context vars
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id

        session_id = session_id_var.get()
        if session_id:
            log_data["session_id"] = session_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info) if record.exc_info[0] else None,
            }

        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_data["extra"] = record.extra_fields

        # Add any additional attributes set on the record
        standard_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'pathname', 'process', 'processName', 'relativeCreated',
            'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
            'extra_fields', 'message'
        }

        extra = {}
        for key, value in record.__dict__.items():
            if key not in standard_attrs:
                try:
                    json.dumps(value)  # Check if serializable
                    extra[key] = value
                except (TypeError, ValueError):
                    extra[key] = str(value)

        if extra:
            log_data.setdefault("extra", {}).update(extra)

        return json.dumps(log_data, default=str)


class StructuredLogger(logging.Logger):
    """
    Extended logger with structured logging support.
    """

    def _log_with_extra(self, level: int, msg: str, extra_fields: Dict[str, Any] = None, *args, **kwargs):
        """Log with extra structured fields."""
        if extra_fields:
            kwargs.setdefault('extra', {})['extra_fields'] = extra_fields
        self.log(level, msg, *args, **kwargs)

    def info_with_context(self, msg: str, **extra_fields):
        """Log info with extra context."""
        self._log_with_extra(logging.INFO, msg, extra_fields)

    def error_with_context(self, msg: str, **extra_fields):
        """Log error with extra context."""
        self._log_with_extra(logging.ERROR, msg, extra_fields)

    def warning_with_context(self, msg: str, **extra_fields):
        """Log warning with extra context."""
        self._log_with_extra(logging.WARNING, msg, extra_fields)

    def debug_with_context(self, msg: str, **extra_fields):
        """Log debug with extra context."""
        self._log_with_extra(logging.DEBUG, msg, extra_fields)


def setup_structured_logging(
    service_name: str = "grace",
    environment: str = "development",
    level: int = logging.INFO,
    json_output: bool = True
) -> logging.Logger:
    """
    Configure structured logging for the application.

    Args:
        service_name: Name of the service for log identification
        environment: Environment name (development, staging, production)
        level: Logging level
        json_output: If True, output JSON format; if False, use standard format

    Returns:
        Configured root logger
    """
    # Set custom logger class
    logging.setLoggerClass(StructuredLogger)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if json_output:
        formatter = StructuredLogFormatter(service_name, environment)
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    return root_logger


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        StructuredLogger instance
    """
    return logging.getLogger(name)


# =============================================================================
# Context Management
# =============================================================================

def set_request_context(request_id: str = None, user_id: str = None, session_id: str = None):
    """Set context variables for the current request."""
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    if session_id:
        session_id_var.set(session_id)


def clear_request_context():
    """Clear all request context variables."""
    request_id_var.set(None)
    user_id_var.set(None)
    session_id_var.set(None)


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())


# =============================================================================
# Decorators
# =============================================================================

def log_function_call(logger: logging.Logger = None):
    """
    Decorator to log function entry and exit.

    Usage:
        @log_function_call()
        def my_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)

            func_name = func.__qualname__

            # Log entry
            logger.debug(f"Entering {func_name}", extra={
                'extra_fields': {
                    'function': func_name,
                    'event': 'function_entry',
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                }
            })

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Log exit
                logger.debug(f"Exiting {func_name}", extra={
                    'extra_fields': {
                        'function': func_name,
                        'event': 'function_exit',
                        'duration_ms': round(duration * 1000, 2),
                        'success': True
                    }
                })

                return result
            except Exception as e:
                duration = time.time() - start_time

                # Log error
                logger.error(f"Error in {func_name}: {str(e)}", extra={
                    'extra_fields': {
                        'function': func_name,
                        'event': 'function_error',
                        'duration_ms': round(duration * 1000, 2),
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    }
                }, exc_info=True)

                raise

        return wrapper
    return decorator


def log_async_function_call(logger: logging.Logger = None):
    """
    Decorator to log async function entry and exit.

    Usage:
        @log_async_function_call()
        async def my_async_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)

            func_name = func.__qualname__

            # Log entry
            logger.debug(f"Entering {func_name}", extra={
                'extra_fields': {
                    'function': func_name,
                    'event': 'function_entry',
                    'async': True
                }
            })

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # Log exit
                logger.debug(f"Exiting {func_name}", extra={
                    'extra_fields': {
                        'function': func_name,
                        'event': 'function_exit',
                        'duration_ms': round(duration * 1000, 2),
                        'success': True,
                        'async': True
                    }
                })

                return result
            except Exception as e:
                duration = time.time() - start_time

                # Log error
                logger.error(f"Error in {func_name}: {str(e)}", extra={
                    'extra_fields': {
                        'function': func_name,
                        'event': 'function_error',
                        'duration_ms': round(duration * 1000, 2),
                        'error_type': type(e).__name__,
                        'async': True
                    }
                }, exc_info=True)

                raise

        return wrapper
    return decorator


# =============================================================================
# FastAPI Middleware Integration
# =============================================================================

class LoggingMiddleware:
    """
    ASGI middleware for request/response logging.

    Usage:
        app.add_middleware(LoggingMiddleware)
    """

    def __init__(self, app):
        self.app = app
        self.logger = get_logger("grace.http")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate request ID
        request_id = generate_request_id()
        set_request_context(request_id=request_id)

        # Extract request info
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        # Log request start
        start_time = time.time()
        self.logger.info(f"Request started: {method} {path}", extra={
            'extra_fields': {
                'event': 'request_start',
                'method': method,
                'path': path,
                'request_id': request_id
            }
        })

        # Track response status
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.time() - start_time

            # Log request completion
            log_level = logging.INFO if status_code < 400 else logging.WARNING if status_code < 500 else logging.ERROR
            self.logger.log(log_level, f"Request completed: {method} {path} - {status_code}", extra={
                'extra_fields': {
                    'event': 'request_complete',
                    'method': method,
                    'path': path,
                    'status_code': status_code,
                    'duration_ms': round(duration * 1000, 2),
                    'request_id': request_id
                }
            })

            # Clear context
            clear_request_context()


# =============================================================================
# Convenience Exports
# =============================================================================

__all__ = [
    'StructuredLogFormatter',
    'StructuredLogger',
    'setup_structured_logging',
    'get_logger',
    'set_request_context',
    'clear_request_context',
    'generate_request_id',
    'log_function_call',
    'log_async_function_call',
    'LoggingMiddleware',
    'request_id_var',
    'user_id_var',
    'session_id_var',
]
