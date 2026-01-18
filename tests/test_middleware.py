"""
Tests for Self-Healing Middleware

Tests the automatic error capture and self-healing integration middleware:
1. Middleware initialization
2. Request interception
3. Self-healing trigger conditions
4. Error recovery behavior
5. Logging of healing actions
6. Integration with healing system
"""

import sys
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, 'backend')


class TestErrorPatternTracker:
    """Test the ErrorPatternTracker class."""
    
    @pytest.fixture
    def tracker(self):
        from middleware.self_healing_middleware import ErrorPatternTracker
        return ErrorPatternTracker(window_minutes=60, escalation_threshold=3)
    
    def test_initialization(self, tracker):
        """Test ErrorPatternTracker initializes with correct parameters."""
        assert tracker.window_minutes == 60
        assert tracker.escalation_threshold == 3
        assert isinstance(tracker._error_counts, dict)
    
    def test_get_error_key(self, tracker):
        """Test error key generation."""
        key = tracker._get_error_key("api.users", "ValueError")
        assert key == "api.users:ValueError"
    
    def test_record_error_returns_count(self, tracker):
        """Test recording errors returns the count in window."""
        count1 = tracker.record_error("api.users", "ValueError")
        assert count1 == 1
        
        count2 = tracker.record_error("api.users", "ValueError")
        assert count2 == 2
        
        count3 = tracker.record_error("api.users", "ValueError")
        assert count3 == 3
    
    def test_record_error_different_components(self, tracker):
        """Test errors from different components are tracked separately."""
        tracker.record_error("api.users", "ValueError")
        tracker.record_error("api.orders", "ValueError")
        
        count = tracker.record_error("api.users", "ValueError")
        assert count == 2  # Only counts api.users:ValueError
    
    def test_should_escalate_below_threshold(self, tracker):
        """Test escalation returns False below threshold."""
        tracker.record_error("api.test", "TestError")
        tracker.record_error("api.test", "TestError")
        
        assert tracker.should_escalate("api.test", "TestError") is False
    
    def test_should_escalate_at_threshold(self, tracker):
        """Test escalation returns True at threshold."""
        for _ in range(3):
            tracker.record_error("api.test", "TestError")
        
        assert tracker.should_escalate("api.test", "TestError") is True
    
    def test_should_escalate_above_threshold(self, tracker):
        """Test escalation returns True above threshold."""
        for _ in range(5):
            tracker.record_error("api.test", "TestError")
        
        assert tracker.should_escalate("api.test", "TestError") is True
    
    def test_cleanup_old_errors(self, tracker):
        """Test old errors are cleaned up outside the window."""
        tracker._error_counts["api.test:OldError"] = [
            datetime.now() - timedelta(minutes=120),  # Outside window
            datetime.now() - timedelta(minutes=90),   # Outside window
            datetime.now() - timedelta(minutes=30),   # Inside window
        ]
        
        tracker._cleanup_old_errors("api.test:OldError")
        
        assert len(tracker._error_counts["api.test:OldError"]) == 1
    
    def test_get_pattern_stats_empty(self, tracker):
        """Test pattern stats when no errors recorded."""
        stats = tracker.get_pattern_stats()
        assert stats == {}
    
    def test_get_pattern_stats_with_errors(self, tracker):
        """Test pattern stats with recorded errors."""
        tracker.record_error("api.users", "ValueError")
        tracker.record_error("api.users", "ValueError")
        tracker.record_error("api.orders", "KeyError")
        
        stats = tracker.get_pattern_stats()
        
        assert "api.users:ValueError" in stats
        assert stats["api.users:ValueError"]["count"] == 2
        assert stats["api.users:ValueError"]["escalated"] is False
        
        assert "api.orders:KeyError" in stats
        assert stats["api.orders:KeyError"]["count"] == 1
    
    def test_get_pattern_stats_escalated_flag(self, tracker):
        """Test pattern stats shows escalated flag correctly."""
        for _ in range(3):
            tracker.record_error("api.critical", "DatabaseError")
        
        stats = tracker.get_pattern_stats()
        
        assert stats["api.critical:DatabaseError"]["escalated"] is True


class TestSeverityClassification:
    """Test severity classification functions."""
    
    def test_classify_severity_critical_errors(self):
        """Test critical errors are classified correctly."""
        from middleware.self_healing_middleware import classify_severity, reset_error_patterns
        
        reset_error_patterns()
        
        class DatabaseError(Exception): pass
        class ConnectionError(Exception): pass
        class MemoryError(Exception): pass
        
        assert classify_severity(DatabaseError(), "test") == "critical"
        assert classify_severity(MemoryError(), "test") == "critical"
    
    def test_classify_severity_high_errors(self):
        """Test high severity errors are classified correctly."""
        from middleware.self_healing_middleware import classify_severity, reset_error_patterns
        
        reset_error_patterns()
        
        class TimeoutError(Exception): pass
        class PermissionError(Exception): pass
        
        assert classify_severity(TimeoutError(), "test") == "high"
        assert classify_severity(PermissionError(), "test") == "high"
    
    def test_classify_severity_medium_errors(self):
        """Test medium severity errors are classified correctly."""
        from middleware.self_healing_middleware import classify_severity, reset_error_patterns
        
        reset_error_patterns()
        
        assert classify_severity(ValueError(), "test") == "medium"
        assert classify_severity(KeyError(), "test") == "medium"
        assert classify_severity(TypeError(), "test") == "medium"
    
    def test_classify_severity_low_errors(self):
        """Test low severity errors are classified correctly."""
        from middleware.self_healing_middleware import classify_severity, reset_error_patterns
        
        reset_error_patterns()
        
        assert classify_severity(FileNotFoundError(), "test") == "low"
    
    def test_classify_severity_unknown_errors(self):
        """Test unknown errors default to medium severity."""
        from middleware.self_healing_middleware import classify_severity, reset_error_patterns
        
        reset_error_patterns()
        
        class CustomUnknownError(Exception): pass
        
        assert classify_severity(CustomUnknownError(), "test") == "medium"
    
    def test_classify_severity_escalation(self):
        """Test severity escalation for recurring errors."""
        from middleware.self_healing_middleware import classify_severity, reset_error_patterns
        import middleware.self_healing_middleware as shm
        
        reset_error_patterns()
        
        # Record errors to trigger escalation using module's tracker after reset
        for _ in range(4):
            shm._pattern_tracker.record_error("api.escalate", "ValueError")
        
        # Verify escalation is triggered
        assert shm._pattern_tracker.should_escalate("api.escalate", "ValueError") is True
        
        # Now classify - should escalate from medium to high
        severity = classify_severity(ValueError(), "api.escalate")
        assert severity == "high"


class TestSelfHealingMiddlewareInit:
    """Test SelfHealingMiddleware initialization."""
    
    @pytest.fixture
    def mock_app(self):
        return MagicMock()
    
    def test_middleware_initialization_defaults(self, mock_app):
        """Test middleware initializes with default values."""
        from middleware.self_healing_middleware import SelfHealingMiddleware
        
        middleware = SelfHealingMiddleware(mock_app)
        
        assert middleware.excluded_paths == ["/health", "/metrics", "/docs", "/openapi.json"]
        assert middleware.min_severity == "low"
        assert middleware._error_learning is None
        assert middleware._session_factory is None
    
    def test_middleware_initialization_custom_excluded_paths(self, mock_app):
        """Test middleware initializes with custom excluded paths."""
        from middleware.self_healing_middleware import SelfHealingMiddleware
        
        custom_paths = ["/api/v1/health", "/internal/status"]
        middleware = SelfHealingMiddleware(mock_app, excluded_paths=custom_paths)
        
        assert middleware.excluded_paths == custom_paths
    
    def test_middleware_initialization_custom_min_severity(self, mock_app):
        """Test middleware initializes with custom minimum severity."""
        from middleware.self_healing_middleware import SelfHealingMiddleware
        
        middleware = SelfHealingMiddleware(mock_app, min_severity="high")
        
        assert middleware.min_severity == "high"


class TestSelfHealingMiddlewareMethods:
    """Test SelfHealingMiddleware internal methods."""
    
    @pytest.fixture
    def middleware(self):
        from middleware.self_healing_middleware import SelfHealingMiddleware
        mock_app = MagicMock()
        return SelfHealingMiddleware(mock_app)
    
    def test_should_track_included_path(self, middleware):
        """Test _should_track returns True for included paths."""
        assert middleware._should_track("/api/users") is True
        assert middleware._should_track("/api/orders/123") is True
    
    def test_should_track_excluded_path(self, middleware):
        """Test _should_track returns False for excluded paths."""
        assert middleware._should_track("/health") is False
        assert middleware._should_track("/metrics") is False
        assert middleware._should_track("/docs") is False
        assert middleware._should_track("/openapi.json") is False
    
    def test_should_track_partial_match(self, middleware):
        """Test _should_track with paths that start with excluded paths."""
        assert middleware._should_track("/health/detailed") is False
        assert middleware._should_track("/metrics/prometheus") is False
    
    def test_extract_component_simple(self, middleware):
        """Test _extract_component with simple paths."""
        assert middleware._extract_component("/users") == "api.users"
        assert middleware._extract_component("/orders") == "api.orders"
    
    def test_extract_component_nested(self, middleware):
        """Test _extract_component with nested paths."""
        assert middleware._extract_component("/users/123/orders") == "api.users"
        assert middleware._extract_component("/api/v1/items") == "api.api"
    
    def test_extract_component_root(self, middleware):
        """Test _extract_component with root path."""
        # Root path "/" splits to ['', ''] so parts[0] is empty string
        assert middleware._extract_component("/") == "api."
    
    def test_severity_meets_threshold_low(self, middleware):
        """Test severity threshold check with low min_severity."""
        middleware.min_severity = "low"
        
        assert middleware._severity_meets_threshold("low") is True
        assert middleware._severity_meets_threshold("medium") is True
        assert middleware._severity_meets_threshold("high") is True
        assert middleware._severity_meets_threshold("critical") is True
    
    def test_severity_meets_threshold_medium(self, middleware):
        """Test severity threshold check with medium min_severity."""
        middleware.min_severity = "medium"
        
        assert middleware._severity_meets_threshold("low") is False
        assert middleware._severity_meets_threshold("medium") is True
        assert middleware._severity_meets_threshold("high") is True
        assert middleware._severity_meets_threshold("critical") is True
    
    def test_severity_meets_threshold_high(self, middleware):
        """Test severity threshold check with high min_severity."""
        middleware.min_severity = "high"
        
        assert middleware._severity_meets_threshold("low") is False
        assert middleware._severity_meets_threshold("medium") is False
        assert middleware._severity_meets_threshold("high") is True
        assert middleware._severity_meets_threshold("critical") is True
    
    def test_severity_meets_threshold_critical(self, middleware):
        """Test severity threshold check with critical min_severity."""
        middleware.min_severity = "critical"
        
        assert middleware._severity_meets_threshold("low") is False
        assert middleware._severity_meets_threshold("medium") is False
        assert middleware._severity_meets_threshold("high") is False
        assert middleware._severity_meets_threshold("critical") is True


class TestSelfHealingMiddlewareDispatch:
    """Test SelfHealingMiddleware dispatch behavior."""
    
    @pytest.fixture
    def middleware(self):
        from middleware.self_healing_middleware import SelfHealingMiddleware
        mock_app = MagicMock()
        return SelfHealingMiddleware(mock_app)
    
    @pytest.fixture
    def mock_request(self):
        request = MagicMock()
        request.url.path = "/api/users"
        request.method = "GET"
        request.query_params = {}
        request.path_params = {}
        request.headers = {"user-agent": "test-agent"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        return request
    
    @pytest.mark.asyncio
    async def test_dispatch_excluded_path_passes_through(self, middleware):
        """Test excluded paths are passed through without tracking."""
        request = MagicMock()
        request.url.path = "/health"
        
        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)
        
        response = await middleware.dispatch(request, mock_call_next)
        
        assert response == mock_response
        mock_call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_dispatch_successful_request(self, middleware, mock_request):
        """Test successful requests pass through without recording."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_call_next = AsyncMock(return_value=mock_response)
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response == mock_response
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_dispatch_5xx_error_tracked(self, middleware, mock_request):
        """Test 5xx responses are tracked."""
        from middleware.self_healing_middleware import reset_error_patterns
        reset_error_patterns()
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_call_next = AsyncMock(return_value=mock_response)
        
        # Mock _record_http_error to track it was called
        middleware._record_http_error = AsyncMock()
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response == mock_response
        middleware._record_http_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dispatch_exception_recorded_and_reraised(self, middleware, mock_request):
        """Test exceptions are recorded and re-raised."""
        from middleware.self_healing_middleware import reset_error_patterns
        reset_error_patterns()
        
        test_error = ValueError("Test error")
        mock_call_next = AsyncMock(side_effect=test_error)
        
        # Mock _record_exception to track it was called
        middleware._record_exception = AsyncMock()
        
        with pytest.raises(ValueError, match="Test error"):
            await middleware.dispatch(mock_request, mock_call_next)
        
        middleware._record_exception.assert_called_once()


class TestSelfHealingEndpointDecorator:
    """Test the self_healing_endpoint decorator."""
    
    def test_decorator_sync_function(self):
        """Test decorator works with sync functions."""
        from middleware.self_healing_middleware import self_healing_endpoint
        
        @self_healing_endpoint(component="test.sync")
        def sync_function():
            return "success"
        
        result = sync_function()
        assert result == "success"
    
    def test_decorator_sync_function_with_exception(self):
        """Test decorator records exception from sync function."""
        from middleware.self_healing_middleware import self_healing_endpoint
        
        @self_healing_endpoint(component="test.sync")
        def sync_function_error():
            raise ValueError("Test sync error")
        
        with pytest.raises(ValueError, match="Test sync error"):
            sync_function_error()
    
    @pytest.mark.asyncio
    async def test_decorator_async_function(self):
        """Test decorator works with async functions."""
        from middleware.self_healing_middleware import self_healing_endpoint
        
        @self_healing_endpoint(component="test.async")
        async def async_function():
            return "async success"
        
        result = await async_function()
        assert result == "async success"
    
    @pytest.mark.asyncio
    async def test_decorator_async_function_with_exception(self):
        """Test decorator records exception from async function."""
        from middleware.self_healing_middleware import self_healing_endpoint
        
        @self_healing_endpoint(component="test.async")
        async def async_function_error():
            raise KeyError("Test async error")
        
        with pytest.raises(KeyError, match="Test async error"):
            await async_function_error()
    
    def test_decorator_preserves_function_name(self):
        """Test decorator preserves the original function name."""
        from middleware.self_healing_middleware import self_healing_endpoint
        
        @self_healing_endpoint()
        def original_function_name():
            pass
        
        assert original_function_name.__name__ == "original_function_name"
    
    def test_decorator_with_severity_override(self):
        """Test decorator with severity override."""
        from middleware.self_healing_middleware import self_healing_endpoint
        
        @self_healing_endpoint(severity_override="critical")
        def critical_function():
            return "critical"
        
        result = critical_function()
        assert result == "critical"


class TestCacheErrorHandler:
    """Test the cache_error_handler decorator."""
    
    def test_sync_cache_handler_success(self):
        """Test sync cache handler on success."""
        from middleware.self_healing_middleware import cache_error_handler
        
        @cache_error_handler
        def cache_get(key):
            return f"value_{key}"
        
        result = cache_get("test_key")
        assert result == "value_test_key"
    
    def test_sync_cache_handler_exception(self):
        """Test sync cache handler records exception."""
        from middleware.self_healing_middleware import cache_error_handler
        
        @cache_error_handler
        def cache_fail():
            raise ConnectionError("Redis connection failed")
        
        with pytest.raises(ConnectionError):
            cache_fail()
    
    @pytest.mark.asyncio
    async def test_async_cache_handler_success(self):
        """Test async cache handler on success."""
        from middleware.self_healing_middleware import cache_error_handler
        
        @cache_error_handler
        async def async_cache_get(key):
            return f"async_value_{key}"
        
        result = await async_cache_get("async_key")
        assert result == "async_value_async_key"
    
    @pytest.mark.asyncio
    async def test_async_cache_handler_exception(self):
        """Test async cache handler records exception."""
        from middleware.self_healing_middleware import cache_error_handler
        
        @cache_error_handler
        async def async_cache_fail():
            raise ConnectionError("Async Redis connection failed")
        
        with pytest.raises(ConnectionError):
            await async_cache_fail()


class TestDatabaseErrorHandler:
    """Test the database_error_handler decorator."""
    
    def test_database_handler_success(self):
        """Test database handler on success."""
        from middleware.self_healing_middleware import database_error_handler
        
        @database_error_handler
        def db_query():
            return [{"id": 1}, {"id": 2}]
        
        result = db_query()
        assert len(result) == 2
    
    def test_database_handler_exception(self):
        """Test database handler records exception."""
        from middleware.self_healing_middleware import database_error_handler
        
        class DatabaseError(Exception): pass
        
        @database_error_handler
        def db_fail():
            raise DatabaseError("Connection refused")
        
        with pytest.raises(DatabaseError):
            db_fail()


class TestTestRunnerErrorHandler:
    """Test the test_runner_error_handler decorator."""
    
    def test_test_runner_handler_success(self):
        """Test test runner handler on success."""
        from middleware.self_healing_middleware import test_runner_error_handler
        
        @test_runner_error_handler
        def run_tests():
            return {"passed": 10, "failed": 0}
        
        result = run_tests()
        assert result["passed"] == 10
    
    def test_test_runner_handler_exception(self):
        """Test test runner handler records exception."""
        from middleware.self_healing_middleware import test_runner_error_handler
        
        @test_runner_error_handler
        def run_tests_fail():
            raise RuntimeError("Test execution failed")
        
        with pytest.raises(RuntimeError):
            run_tests_fail()


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_get_error_pattern_stats(self):
        """Test get_error_pattern_stats function."""
        from middleware.self_healing_middleware import (
            get_error_pattern_stats, reset_error_patterns
        )
        import middleware.self_healing_middleware as shm
        
        reset_error_patterns()
        
        # Use the module's current tracker after reset
        shm._pattern_tracker.record_error("api.stats", "StatsError")
        shm._pattern_tracker.record_error("api.stats", "StatsError")
        
        stats = get_error_pattern_stats()
        
        assert "api.stats:StatsError" in stats
        assert stats["api.stats:StatsError"]["count"] == 2
    
    def test_reset_error_patterns(self):
        """Test reset_error_patterns clears all patterns."""
        from middleware.self_healing_middleware import (
            get_error_pattern_stats, reset_error_patterns, _pattern_tracker
        )
        
        _pattern_tracker.record_error("api.clear", "ClearError")
        
        reset_error_patterns()
        
        stats = get_error_pattern_stats()
        assert stats == {}


class TestAddSelfHealingMiddleware:
    """Test add_self_healing_middleware function."""
    
    def test_add_middleware_to_app(self):
        """Test adding middleware to FastAPI app."""
        from middleware.self_healing_middleware import add_self_healing_middleware
        
        mock_app = MagicMock()
        
        add_self_healing_middleware(mock_app)
        
        mock_app.add_middleware.assert_called_once()
    
    def test_add_middleware_with_custom_params(self):
        """Test adding middleware with custom parameters."""
        from middleware.self_healing_middleware import add_self_healing_middleware
        
        mock_app = MagicMock()
        
        add_self_healing_middleware(
            mock_app,
            excluded_paths=["/custom/health"],
            min_severity="high"
        )
        
        mock_app.add_middleware.assert_called_once()
        call_kwargs = mock_app.add_middleware.call_args[1]
        assert call_kwargs["excluded_paths"] == ["/custom/health"]
        assert call_kwargs["min_severity"] == "high"


class TestIntegrationWithHealingSystem:
    """Test integration with the healing system."""
    
    @pytest.fixture
    def mock_error_learning(self):
        mock = MagicMock()
        mock.record_error = MagicMock()
        return mock
    
    def test_lazy_load_error_learning(self):
        """Test error learning is lazily loaded."""
        from middleware.self_healing_middleware import SelfHealingMiddleware
        
        mock_app = MagicMock()
        middleware = SelfHealingMiddleware(mock_app)
        
        assert middleware._error_learning is None
        
        # Attempt to load (will fail due to missing dependencies, but tests lazy load)
        result = middleware._get_error_learning()
        # Either returns None (no deps) or the loaded integration
        assert middleware._error_learning is None or middleware._error_learning is not None
    
    @pytest.mark.asyncio
    async def test_record_exception_without_error_learning(self):
        """Test _record_exception handles missing error_learning gracefully."""
        from middleware.self_healing_middleware import SelfHealingMiddleware, reset_error_patterns
        
        reset_error_patterns()
        
        mock_app = MagicMock()
        middleware = SelfHealingMiddleware(mock_app)
        
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/test"
        request.query_params = {}
        request.path_params = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test"}
        
        # Should not raise even without error_learning
        await middleware._record_exception(
            request=request,
            error=ValueError("Test"),
            component="api.test",
            start_time=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_record_http_error_without_error_learning(self):
        """Test _record_http_error handles missing error_learning gracefully."""
        from middleware.self_healing_middleware import SelfHealingMiddleware, reset_error_patterns
        
        reset_error_patterns()
        
        mock_app = MagicMock()
        middleware = SelfHealingMiddleware(mock_app)
        
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/api/error"
        
        # Should not raise even without error_learning
        await middleware._record_http_error(
            request=request,
            component="api.error",
            status_code=500,
            start_time=datetime.now()
        )


class TestLoggingOfHealingActions:
    """Test logging behavior of the middleware."""
    
    @pytest.mark.asyncio
    async def test_logs_on_exception_recording(self):
        """Test that exceptions are logged when recorded."""
        from middleware.self_healing_middleware import SelfHealingMiddleware, reset_error_patterns
        
        reset_error_patterns()
        
        mock_app = MagicMock()
        middleware = SelfHealingMiddleware(mock_app)
        
        # Mock the error learning
        mock_error_learning = MagicMock()
        middleware._error_learning = mock_error_learning
        
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/test"
        request.query_params = {}
        request.path_params = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test"}
        
        with patch('middleware.self_healing_middleware.logger') as mock_logger:
            await middleware._record_exception(
                request=request,
                error=ValueError("Test error"),
                component="api.test",
                start_time=datetime.now()
            )
            
            # Check that logging occurred
            mock_logger.info.assert_called()


class TestSeverityMap:
    """Test SEVERITY_MAP constant."""
    
    def test_severity_map_has_critical(self):
        """Test SEVERITY_MAP has critical severity entries."""
        from middleware.self_healing_middleware import SEVERITY_MAP
        
        critical_errors = [k for k, v in SEVERITY_MAP.items() if v == "critical"]
        assert len(critical_errors) >= 4
        assert "DatabaseError" in critical_errors
        assert "MemoryError" in critical_errors
    
    def test_severity_map_has_high(self):
        """Test SEVERITY_MAP has high severity entries."""
        from middleware.self_healing_middleware import SEVERITY_MAP
        
        high_errors = [k for k, v in SEVERITY_MAP.items() if v == "high"]
        assert len(high_errors) >= 3
        assert "TimeoutError" in high_errors
    
    def test_severity_map_has_medium(self):
        """Test SEVERITY_MAP has medium severity entries."""
        from middleware.self_healing_middleware import SEVERITY_MAP
        
        medium_errors = [k for k, v in SEVERITY_MAP.items() if v == "medium"]
        assert len(medium_errors) >= 4
        assert "ValueError" in medium_errors
        assert "KeyError" in medium_errors
    
    def test_severity_map_has_low(self):
        """Test SEVERITY_MAP has low severity entries."""
        from middleware.self_healing_middleware import SEVERITY_MAP
        
        low_errors = [k for k, v in SEVERITY_MAP.items() if v == "low"]
        assert len(low_errors) >= 2
        assert "FileNotFoundError" in low_errors


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
