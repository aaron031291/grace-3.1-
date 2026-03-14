"""Tests for backend.core.resilience — circuit breakers, error boundaries, graceful degradation."""

import importlib
import pathlib
import time

import pytest

# ── load module directly ──────────────────────────────────────────────
_spec = importlib.util.spec_from_file_location(
    "resilience",
    str(pathlib.Path(__file__).resolve().parents[3] / "backend" / "core" / "resilience.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

CircuitBreaker = _mod.CircuitBreaker
get_breaker = _mod.get_breaker
all_breaker_statuses = _mod.all_breaker_statuses
ErrorBoundary = _mod.ErrorBoundary
error_boundary = _mod.error_boundary
GracefulDegradation = _mod.GracefulDegradation


# ── helpers ───────────────────────────────────────────────────────────
def _ok():
    return "ok"


def _boom():
    raise RuntimeError("boom")


# ══════════════════════════════════════════════════════════════════════
#  CircuitBreaker
# ══════════════════════════════════════════════════════════════════════
class TestCircuitBreaker:
    def _make(self, **kw):
        defaults = dict(name="test", failure_threshold=3, reset_timeout=120)
        defaults.update(kw)
        return CircuitBreaker(**defaults)

    # 1. starts CLOSED
    def test_initial_state_is_closed(self):
        cb = self._make()
        assert cb.state == CircuitBreaker.CLOSED

    # 2. successful call returns result and stays CLOSED
    def test_successful_call_returns_result(self):
        cb = self._make()
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.state == CircuitBreaker.CLOSED

    # 3. after failure_threshold failures → OPEN
    def test_transitions_to_open_after_threshold(self):
        cb = self._make(failure_threshold=3)
        for _ in range(3):
            cb.call(_boom, fallback="fb")
        assert cb.state == CircuitBreaker.OPEN
        assert cb.failure_count == 3

    # 4. OPEN rejects calls, returns fallback
    def test_open_rejects_with_fallback(self):
        cb = self._make(failure_threshold=1)
        cb.call(_boom, fallback="fb")
        assert cb.state == CircuitBreaker.OPEN

        result = cb.call(_ok, fallback="rejected")
        assert result == "rejected"
        assert cb.state == CircuitBreaker.OPEN

    # 5. after reset_timeout → HALF_OPEN
    def test_open_to_half_open_after_timeout(self):
        cb = self._make(failure_threshold=1, reset_timeout=100)
        cb.call(_boom, fallback="fb")
        assert cb.state == CircuitBreaker.OPEN

        # simulate time passing
        cb.last_failure_time = time.time() - 200

        result = cb.call(_ok)
        assert cb.state == CircuitBreaker.CLOSED  # success in HALF_OPEN → CLOSED
        assert result == "ok"

    # 6. successful call in HALF_OPEN → CLOSED
    def test_half_open_success_closes(self):
        cb = self._make(failure_threshold=1, reset_timeout=100)
        cb.call(_boom, fallback="fb")
        cb.last_failure_time = time.time() - 200

        result = cb.call(lambda: "recovered")
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.failure_count == 0
        assert result == "recovered"

    # 7. failed call in HALF_OPEN → back to OPEN
    def test_half_open_failure_reopens(self):
        cb = self._make(failure_threshold=1, reset_timeout=100)
        cb.call(_boom, fallback="fb")
        cb.last_failure_time = time.time() - 200

        result = cb.call(_boom, fallback="still-bad")
        assert cb.state == CircuitBreaker.OPEN
        assert result == "still-bad"

    # 8. status() returns correct dict
    def test_status_dict(self):
        cb = self._make(name="svc", failure_threshold=5, reset_timeout=60)
        s = cb.status()
        assert s == {
            "name": "svc",
            "state": "closed",
            "failure_count": 0,
            "threshold": 5,
            "reset_timeout": 60,
        }

    # 9. fallback=None + exception → re-raises
    def test_no_fallback_reraises(self):
        cb = self._make(failure_threshold=5)
        with pytest.raises(RuntimeError, match="boom"):
            cb.call(_boom)


# ══════════════════════════════════════════════════════════════════════
#  get_breaker / all_breaker_statuses
# ══════════════════════════════════════════════════════════════════════
class TestBreakerRegistry:
    @pytest.fixture(autouse=True)
    def _reset_registry(self):
        _mod._breakers = {}
        yield
        _mod._breakers = {}

    def test_get_breaker_creates_new(self):
        b = get_breaker("alpha")
        assert isinstance(b, CircuitBreaker)
        assert b.name == "alpha"

    def test_get_breaker_returns_same_instance(self):
        b1 = get_breaker("beta")
        b2 = get_breaker("beta")
        assert b1 is b2

    def test_all_breaker_statuses_returns_list(self):
        get_breaker("x")
        get_breaker("y")
        statuses = all_breaker_statuses()
        assert isinstance(statuses, list)
        assert len(statuses) == 2
        names = {s["name"] for s in statuses}
        assert names == {"x", "y"}


# ══════════════════════════════════════════════════════════════════════
#  ErrorBoundary (context manager)
# ══════════════════════════════════════════════════════════════════════
class TestErrorBoundary:
    def test_no_exception_normal_flow(self):
        with ErrorBoundary("test") as eb:
            result = 1 + 1
        assert result == 2
        assert isinstance(eb, ErrorBoundary)

    def test_exception_suppressed(self):
        with ErrorBoundary("test"):
            raise ValueError("oops")
        # if we reach here, the exception was suppressed
        assert True

    def test_code_continues_after_suppression(self):
        flag = False
        with ErrorBoundary("test"):
            raise ValueError("oops")
        flag = True
        assert flag is True


# ══════════════════════════════════════════════════════════════════════
#  error_boundary (decorator)
# ══════════════════════════════════════════════════════════════════════
class TestErrorBoundaryDecorator:
    def test_decorated_works_normally(self):
        @error_boundary("dec")
        def add(a, b):
            return a + b

        assert add(2, 3) == 5

    def test_decorated_returns_fallback_on_error(self):
        @error_boundary("dec", fallback="safe")
        def explode():
            raise RuntimeError("kaboom")

        assert explode() == "safe"

    def test_fallback_none_returns_none_on_error(self):
        @error_boundary("dec")
        def explode():
            raise RuntimeError("kaboom")

        assert explode() is None


# ══════════════════════════════════════════════════════════════════════
#  GracefulDegradation
# ══════════════════════════════════════════════════════════════════════
class TestGracefulDegradation:
    @pytest.fixture(autouse=True)
    def _reset_level(self):
        _mod.GracefulDegradation._level = GracefulDegradation.FULL
        yield
        _mod.GracefulDegradation._level = GracefulDegradation.FULL

    def test_default_level_is_full(self):
        assert GracefulDegradation.get_level() == "full"

    def test_set_level_changes_level(self):
        GracefulDegradation.set_level(GracefulDegradation.REDUCED)
        assert GracefulDegradation.get_level() == "reduced"

    def test_get_level_returns_current(self):
        GracefulDegradation.set_level(GracefulDegradation.EMERGENCY)
        assert GracefulDegradation.get_level() == "emergency"

    def test_status_returns_dict_with_level_and_services(self):
        s = GracefulDegradation.status()
        assert "level" in s
        assert "services" in s
        assert s["level"] == "full"
        assert isinstance(s["services"], dict)
        assert set(s["services"].keys()) == {"full", "reduced", "emergency", "read_only"}
