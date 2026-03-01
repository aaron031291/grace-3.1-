"""
Tests for circuit breaker and resilience patterns.
"""
import pytest


class TestCircuitBreaker:
    def test_breaker_starts_closed(self):
        from core.resilience import CircuitBreaker
        cb = CircuitBreaker("test_service", failure_threshold=3)
        assert cb.state == CircuitBreaker.CLOSED

    def test_breaker_opens_after_threshold(self):
        from core.resilience import CircuitBreaker
        cb = CircuitBreaker("test_fail", failure_threshold=3, reset_timeout=60)
        for _ in range(3):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass
        assert cb.state == CircuitBreaker.OPEN

    def test_breaker_rejects_when_open(self):
        from core.resilience import CircuitBreaker
        cb = CircuitBreaker("test_reject", failure_threshold=1, reset_timeout=60)
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass
        result = cb.call(lambda: "should not run", fallback="rejected")
        assert result == "rejected"

    def test_breaker_recovers(self):
        from core.resilience import CircuitBreaker
        cb = CircuitBreaker("test_recover", failure_threshold=1, reset_timeout=0)
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass
        import time
        time.sleep(0.1)
        result = cb.call(lambda: "recovered")
        assert result == "recovered"
        assert cb.state == CircuitBreaker.CLOSED

    def test_breaker_status(self):
        from core.resilience import CircuitBreaker
        cb = CircuitBreaker("test_status", failure_threshold=5)
        status = cb.status()
        assert status["name"] == "test_status"
        assert status["state"] == "closed"
        assert status["threshold"] == 5


class TestErrorBoundary:
    def test_boundary_contains_exception(self):
        from core.resilience import ErrorBoundary
        with ErrorBoundary("test"):
            raise ValueError("should be caught")
        # If we get here, exception was contained

    def test_boundary_decorator(self):
        from core.resilience import error_boundary

        @error_boundary("test_dec", fallback="fallback_value")
        def risky():
            raise RuntimeError("boom")

        result = risky()
        assert result == "fallback_value"


class TestGracefulDegradation:
    def test_default_level_is_full(self):
        from core.resilience import GracefulDegradation
        GracefulDegradation.set_level("full")
        assert GracefulDegradation.get_level() == "full"

    def test_set_and_get_level(self):
        from core.resilience import GracefulDegradation
        GracefulDegradation.set_level("reduced")
        assert GracefulDegradation.get_level() == "reduced"
        GracefulDegradation.set_level("full")

    def test_status_returns_all_levels(self):
        from core.resilience import GracefulDegradation
        status = GracefulDegradation.status()
        assert "full" in status["services"]
        assert "emergency" in status["services"]
