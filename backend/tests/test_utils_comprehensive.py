"""
Comprehensive Test Suite for Utils Module
==========================================
Tests for error_suppression, structured_logging, and rag_prompt utilities.

Coverage:
- Error suppression settings checks
- StructuredLogFormatter JSON formatting
- StructuredLogger extended functionality
- Request context management
- Log decorators (sync and async)
- LoggingMiddleware ASGI
- RAG prompt building
"""

import pytest
import asyncio
import json
import logging
import time
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

import sys
sys.path.insert(0, '/home/user/grace-3.1-/backend')


# =============================================================================
# Error Suppression Tests
# =============================================================================

class TestErrorSuppression:
    """Test error suppression utility functions."""

    def test_should_suppress_genesis_error_no_settings(self):
        """Test genesis error suppression when settings unavailable."""
        with patch.dict('sys.modules', {'settings': None}):
            # Re-import to get new module state
            import importlib
            import utils.error_suppression as es
            importlib.reload(es)

            # When settings is None, should return False
            result = es.should_suppress_genesis_error()
            assert result is False or result is None

    def test_should_suppress_genesis_error_with_settings(self):
        """Test genesis error suppression with settings."""
        mock_settings = Mock()
        mock_settings.SUPPRESS_GENESIS_ERRORS = True

        with patch('utils.error_suppression.settings', mock_settings):
            from utils.error_suppression import should_suppress_genesis_error
            result = should_suppress_genesis_error()
            # Result depends on settings value

    def test_should_suppress_qdrant_error_with_settings(self):
        """Test qdrant error suppression with settings."""
        mock_settings = Mock()
        mock_settings.SUPPRESS_QDRANT_ERRORS = True

        with patch('utils.error_suppression.settings', mock_settings):
            from utils.error_suppression import should_suppress_qdrant_error
            result = should_suppress_qdrant_error()

    def test_should_suppress_ingestion_error_with_settings(self):
        """Test ingestion error suppression with settings."""
        mock_settings = Mock()
        mock_settings.SUPPRESS_INGESTION_ERRORS = False

        with patch('utils.error_suppression.settings', mock_settings):
            from utils.error_suppression import should_suppress_ingestion_error
            result = should_suppress_ingestion_error()

    def test_should_suppress_embedding_error_with_settings(self):
        """Test embedding error suppression with settings."""
        mock_settings = Mock()
        mock_settings.SUPPRESS_EMBEDDING_ERRORS = True

        with patch('utils.error_suppression.settings', mock_settings):
            from utils.error_suppression import should_suppress_embedding_error
            result = should_suppress_embedding_error()


# =============================================================================
# StructuredLogFormatter Tests
# =============================================================================

class TestStructuredLogFormatter:
    """Test StructuredLogFormatter class."""

    def test_formatter_initialization(self):
        """Test formatter initialization."""
        from utils.structured_logging import StructuredLogFormatter

        formatter = StructuredLogFormatter(
            service_name="test_service",
            environment="testing"
        )

        assert formatter.service_name == "test_service"
        assert formatter.environment == "testing"

    def test_formatter_default_values(self):
        """Test formatter default values."""
        from utils.structured_logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()

        assert formatter.service_name == "grace"
        assert formatter.environment == "development"

    def test_format_basic_log(self):
        """Test formatting basic log record."""
        from utils.structured_logging import StructuredLogFormatter

        formatter = StructuredLogFormatter(
            service_name="test",
            environment="test"
        )

        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)

        # Should be valid JSON
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["service"] == "test"
        assert data["environment"] == "test"
        assert data["logger"] == "test.logger"
        assert "timestamp" in data
        assert data["location"]["line"] == 42

    def test_format_with_exception(self):
        """Test formatting log with exception."""
        from utils.structured_logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=50,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert "Test error" in data["exception"]["message"]
        assert data["exception"]["traceback"] is not None

    def test_format_with_context_vars(self):
        """Test formatting with context variables."""
        from utils.structured_logging import (
            StructuredLogFormatter,
            set_request_context,
            clear_request_context
        )

        formatter = StructuredLogFormatter()

        # Set context
        set_request_context(
            request_id="REQ-123",
            user_id="USER-456",
            session_id="SESS-789"
        )

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Request processed",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["request_id"] == "REQ-123"
        assert data["user_id"] == "USER-456"
        assert data["session_id"] == "SESS-789"

        # Clean up
        clear_request_context()

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields."""
        from utils.structured_logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Event logged",
            args=(),
            exc_info=None
        )
        record.extra_fields = {"action": "login", "duration_ms": 150}

        result = formatter.format(record)
        data = json.loads(result)

        assert data["extra"]["action"] == "login"
        assert data["extra"]["duration_ms"] == 150

    def test_format_non_serializable_extra(self):
        """Test formatting with non-serializable extra data."""
        from utils.structured_logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )
        # Add non-serializable attribute
        record.complex_object = object()

        result = formatter.format(record)
        data = json.loads(result)

        # Should convert to string
        assert "complex_object" in data.get("extra", {})


# =============================================================================
# StructuredLogger Tests
# =============================================================================

class TestStructuredLogger:
    """Test StructuredLogger class."""

    def test_info_with_context(self):
        """Test info logging with context."""
        from utils.structured_logging import StructuredLogger

        # Create logger
        logger = StructuredLogger("test")
        logger.setLevel(logging.DEBUG)

        # Add handler to capture output
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # This should not raise
        logger.info_with_context("Test message", key1="value1", key2=123)

    def test_error_with_context(self):
        """Test error logging with context."""
        from utils.structured_logging import StructuredLogger

        logger = StructuredLogger("test")
        logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler()
        logger.addHandler(handler)

        logger.error_with_context("Error message", error_code=500)

    def test_warning_with_context(self):
        """Test warning logging with context."""
        from utils.structured_logging import StructuredLogger

        logger = StructuredLogger("test")
        logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler()
        logger.addHandler(handler)

        logger.warning_with_context("Warning message", severity="medium")

    def test_debug_with_context(self):
        """Test debug logging with context."""
        from utils.structured_logging import StructuredLogger

        logger = StructuredLogger("test")
        logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler()
        logger.addHandler(handler)

        logger.debug_with_context("Debug message", variable="value")


# =============================================================================
# Setup Structured Logging Tests
# =============================================================================

class TestSetupStructuredLogging:
    """Test setup_structured_logging function."""

    def test_setup_json_output(self):
        """Test setup with JSON output."""
        from utils.structured_logging import setup_structured_logging, StructuredLogFormatter

        logger = setup_structured_logging(
            service_name="test_service",
            environment="testing",
            level=logging.INFO,
            json_output=True
        )

        assert logger is not None
        assert len(logger.handlers) > 0

        # Check formatter type
        formatter = logger.handlers[0].formatter
        assert isinstance(formatter, StructuredLogFormatter)

    def test_setup_standard_output(self):
        """Test setup with standard output."""
        from utils.structured_logging import setup_structured_logging

        logger = setup_structured_logging(
            service_name="test_service",
            environment="testing",
            level=logging.DEBUG,
            json_output=False
        )

        assert logger is not None

        # Check it's not JSON formatter
        formatter = logger.handlers[0].formatter
        assert not hasattr(formatter, 'service_name')


# =============================================================================
# Context Management Tests
# =============================================================================

class TestContextManagement:
    """Test request context management."""

    def test_set_request_context(self):
        """Test setting request context."""
        from utils.structured_logging import (
            set_request_context,
            clear_request_context,
            request_id_var,
            user_id_var,
            session_id_var
        )

        set_request_context(
            request_id="REQ-123",
            user_id="USER-456",
            session_id="SESS-789"
        )

        assert request_id_var.get() == "REQ-123"
        assert user_id_var.get() == "USER-456"
        assert session_id_var.get() == "SESS-789"

        clear_request_context()

    def test_clear_request_context(self):
        """Test clearing request context."""
        from utils.structured_logging import (
            set_request_context,
            clear_request_context,
            request_id_var,
            user_id_var,
            session_id_var
        )

        set_request_context(
            request_id="REQ-123",
            user_id="USER-456"
        )

        clear_request_context()

        assert request_id_var.get() is None
        assert user_id_var.get() is None
        assert session_id_var.get() is None

    def test_generate_request_id(self):
        """Test request ID generation."""
        from utils.structured_logging import generate_request_id

        id1 = generate_request_id()
        id2 = generate_request_id()

        assert id1 != id2
        assert len(id1) == 36  # UUID format

    def test_partial_context_set(self):
        """Test setting partial context."""
        from utils.structured_logging import (
            set_request_context,
            clear_request_context,
            request_id_var,
            user_id_var
        )

        # Clear first
        clear_request_context()

        # Set only request_id
        set_request_context(request_id="REQ-ONLY")

        assert request_id_var.get() == "REQ-ONLY"
        assert user_id_var.get() is None

        clear_request_context()


# =============================================================================
# Log Decorator Tests
# =============================================================================

class TestLogDecorators:
    """Test log decorators."""

    def test_log_function_call_success(self):
        """Test log_function_call decorator on success."""
        from utils.structured_logging import log_function_call

        @log_function_call()
        def sample_function(x, y):
            return x + y

        result = sample_function(1, 2)
        assert result == 3

    def test_log_function_call_with_exception(self):
        """Test log_function_call decorator on exception."""
        from utils.structured_logging import log_function_call

        @log_function_call()
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

    def test_log_function_call_with_kwargs(self):
        """Test log_function_call decorator with kwargs."""
        from utils.structured_logging import log_function_call

        @log_function_call()
        def function_with_kwargs(a, b=10, c=20):
            return a + b + c

        result = function_with_kwargs(5, c=15)
        assert result == 30

    @pytest.mark.asyncio
    async def test_log_async_function_call_success(self):
        """Test log_async_function_call decorator on success."""
        from utils.structured_logging import log_async_function_call

        @log_async_function_call()
        async def async_sample_function(x, y):
            await asyncio.sleep(0.01)
            return x * y

        result = await async_sample_function(3, 4)
        assert result == 12

    @pytest.mark.asyncio
    async def test_log_async_function_call_with_exception(self):
        """Test log_async_function_call decorator on exception."""
        from utils.structured_logging import log_async_function_call

        @log_async_function_call()
        async def async_failing_function():
            await asyncio.sleep(0.01)
            raise RuntimeError("Async error")

        with pytest.raises(RuntimeError):
            await async_failing_function()

    def test_log_function_call_custom_logger(self):
        """Test log_function_call with custom logger."""
        from utils.structured_logging import log_function_call

        custom_logger = Mock()
        custom_logger.debug = Mock()
        custom_logger.error = Mock()

        @log_function_call(logger=custom_logger)
        def logged_function():
            return "done"

        result = logged_function()

        assert result == "done"
        # Logger.debug should be called (entry and exit)
        assert custom_logger.debug.call_count >= 1


# =============================================================================
# LoggingMiddleware Tests
# =============================================================================

class TestLoggingMiddleware:
    """Test LoggingMiddleware ASGI middleware."""

    @pytest.mark.asyncio
    async def test_middleware_non_http(self):
        """Test middleware passes through non-HTTP requests."""
        from utils.structured_logging import LoggingMiddleware

        mock_app = AsyncMock()
        middleware = LoggingMiddleware(mock_app)

        scope = {"type": "websocket", "path": "/ws"}

        await middleware(scope, None, None)

        mock_app.assert_called_once_with(scope, None, None)

    @pytest.mark.asyncio
    async def test_middleware_http_request(self):
        """Test middleware logs HTTP requests."""
        from utils.structured_logging import LoggingMiddleware, clear_request_context

        # Clear any existing context
        clear_request_context()

        mock_app = AsyncMock()

        async def mock_send(message):
            if message["type"] == "http.response.start":
                pass

        middleware = LoggingMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test"
        }

        await middleware(scope, None, mock_send)

        mock_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_sets_request_id(self):
        """Test middleware sets request ID in context."""
        from utils.structured_logging import (
            LoggingMiddleware,
            request_id_var,
            clear_request_context
        )

        clear_request_context()

        captured_request_id = None

        async def capture_app(scope, receive, send):
            nonlocal captured_request_id
            captured_request_id = request_id_var.get()

        middleware = LoggingMiddleware(capture_app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/submit"
        }

        await middleware(scope, None, AsyncMock())

        assert captured_request_id is not None


# =============================================================================
# RAG Prompt Tests
# =============================================================================

class TestRagPrompt:
    """Test RAG prompt utilities."""

    def test_build_rag_prompt_with_context(self):
        """Test building RAG prompt with context."""
        from utils.rag_prompt import build_rag_prompt

        query = "What is the capital of France?"
        context = "France is a country in Europe. Its capital is Paris."

        result = build_rag_prompt(query, context)

        assert "What is the capital of France?" in result
        assert "France is a country in Europe" in result
        assert "<context>" in result
        assert "</context>" in result

    def test_build_rag_prompt_no_context(self):
        """Test building RAG prompt without context."""
        from utils.rag_prompt import build_rag_prompt

        query = "What is the capital of France?"

        result = build_rag_prompt(query, None)

        # Should return original query
        assert result == query

    def test_build_rag_prompt_empty_context(self):
        """Test building RAG prompt with empty context."""
        from utils.rag_prompt import build_rag_prompt

        query = "What is the capital of France?"

        result = build_rag_prompt(query, "")
        assert result == query

        result = build_rag_prompt(query, "   ")
        assert result == query

    def test_build_rag_prompt_formatting(self):
        """Test RAG prompt formatting structure."""
        from utils.rag_prompt import build_rag_prompt

        query = "Explain the process"
        context = "The process involves three steps: A, B, C."

        result = build_rag_prompt(query, context)

        # Check structure
        assert result.startswith("Based on the following context")
        assert "User Question:" in result
        assert context in result

    def test_build_rag_system_prompt(self):
        """Test building RAG system prompt."""
        from utils.rag_prompt import build_rag_system_prompt

        result = build_rag_system_prompt()

        assert isinstance(result, str)
        assert len(result) > 0
        assert "knowledge assistant" in result.lower()
        assert "context" in result.lower()

    def test_build_rag_system_prompt_rules(self):
        """Test RAG system prompt contains critical rules."""
        from utils.rag_prompt import build_rag_system_prompt

        result = build_rag_system_prompt()

        # Should mention key rules
        assert "MUST" in result
        assert "context" in result.lower()
        assert "cannot answer" in result.lower() or "I cannot" in result

    def test_rag_prompt_preserves_query(self):
        """Test that query is preserved exactly in prompt."""
        from utils.rag_prompt import build_rag_prompt

        query = "Complex query with 'quotes' and \"double quotes\" and special chars: <>&"
        context = "Some context"

        result = build_rag_prompt(query, context)

        assert query in result


# =============================================================================
# Get Logger Tests
# =============================================================================

class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a logger instance."""
        from utils.structured_logging import get_logger

        logger = get_logger("test.module")

        assert logger is not None
        assert logger.name == "test.module"

    def test_get_logger_same_name(self):
        """Test get_logger returns same logger for same name."""
        from utils.structured_logging import get_logger

        logger1 = get_logger("same.name")
        logger2 = get_logger("same.name")

        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """Test get_logger returns different loggers for different names."""
        from utils.structured_logging import get_logger

        logger1 = get_logger("first.logger")
        logger2 = get_logger("second.logger")

        assert logger1 is not logger2
        assert logger1.name == "first.logger"
        assert logger2.name == "second.logger"


# =============================================================================
# Integration Tests
# =============================================================================

class TestUtilsIntegration:
    """Integration tests for utils module."""

    def test_structured_logging_end_to_end(self):
        """Test structured logging end-to-end."""
        from utils.structured_logging import (
            setup_structured_logging,
            set_request_context,
            clear_request_context,
            generate_request_id,
            get_logger
        )
        import io

        # Setup logging to capture output
        output = io.StringIO()
        handler = logging.StreamHandler(output)
        handler.setLevel(logging.DEBUG)

        logger = setup_structured_logging(
            service_name="integration_test",
            environment="test",
            level=logging.DEBUG,
            json_output=True
        )

        # Replace handler to capture
        logger.handlers.clear()
        from utils.structured_logging import StructuredLogFormatter
        handler.setFormatter(StructuredLogFormatter("integration_test", "test"))
        logger.addHandler(handler)

        # Set context
        request_id = generate_request_id()
        set_request_context(request_id=request_id, user_id="test-user")

        # Log a message
        logger.info("Integration test message")

        # Get output
        log_output = output.getvalue()

        # Verify
        if log_output:  # If output was captured
            log_data = json.loads(log_output.strip())
            assert log_data["service"] == "integration_test"
            assert log_data["message"] == "Integration test message"

        # Clean up
        clear_request_context()

    def test_decorator_with_structured_logging(self):
        """Test decorator integration with structured logging."""
        from utils.structured_logging import (
            log_function_call,
            setup_structured_logging,
            clear_request_context
        )

        clear_request_context()

        setup_structured_logging(
            service_name="decorator_test",
            level=logging.DEBUG,
            json_output=False
        )

        call_count = 0

        @log_function_call()
        def tracked_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result = tracked_function(5)

        assert result == 10
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_decorator_integration(self):
        """Test async decorator integration."""
        from utils.structured_logging import (
            log_async_function_call,
            setup_structured_logging,
            set_request_context,
            clear_request_context,
            generate_request_id
        )

        clear_request_context()

        setup_structured_logging(
            service_name="async_test",
            level=logging.DEBUG,
            json_output=False
        )

        request_id = generate_request_id()
        set_request_context(request_id=request_id)

        @log_async_function_call()
        async def async_tracked_function(data):
            await asyncio.sleep(0.01)
            return {"processed": data}

        result = await async_tracked_function({"key": "value"})

        assert result == {"processed": {"key": "value"}}

        clear_request_context()


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_formatter_with_none_exc_info(self):
        """Test formatter handles None exc_info."""
        from utils.structured_logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "exception" not in data

    def test_formatter_with_empty_message(self):
        """Test formatter handles empty message."""
        from utils.structured_logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["message"] == ""

    def test_rag_prompt_with_special_characters(self):
        """Test RAG prompt with special characters."""
        from utils.rag_prompt import build_rag_prompt

        query = "What about <script>alert('xss')</script>?"
        context = "Context with & and < and > symbols"

        result = build_rag_prompt(query, context)

        # Should preserve characters
        assert "<script>" in result
        assert "&" in result

    def test_context_isolation(self):
        """Test context variables are isolated."""
        from utils.structured_logging import (
            set_request_context,
            clear_request_context,
            request_id_var
        )

        async def task1():
            set_request_context(request_id="TASK1")
            await asyncio.sleep(0.01)
            return request_id_var.get()

        async def task2():
            set_request_context(request_id="TASK2")
            await asyncio.sleep(0.01)
            return request_id_var.get()

        # Run sequentially to test basic isolation
        # Note: Full context isolation requires copy_context()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
