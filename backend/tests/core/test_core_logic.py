"""
Tests for backend.core modules — real logic, specific inputs/outputs.
"""

import time
import threading
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

# ═══════════════════════════════════════════════════════════════════
#  datetime_utils
# ═══════════════════════════════════════════════════════════════════

from core.datetime_utils import ensure_aware, as_naive_utc


class TestEnsureAware:
    def test_none_returns_none(self):
        assert ensure_aware(None) is None

    def test_naive_becomes_utc(self):
        naive = datetime(2025, 6, 15, 12, 0, 0)
        result = ensure_aware(naive)
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc
        assert result.year == 2025 and result.hour == 12

    def test_aware_non_utc_converts(self):
        eastern = timezone(timedelta(hours=-5))
        dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=eastern)
        result = ensure_aware(dt)
        assert result.tzinfo == timezone.utc
        assert result.hour == 17  # 12 EST = 17 UTC


class TestAsNaiveUtc:
    def test_none_returns_none(self):
        assert as_naive_utc(None) is None

    def test_naive_stays_naive(self):
        naive = datetime(2025, 1, 1, 8, 30)
        result = as_naive_utc(naive)
        assert result.tzinfo is None
        assert result == naive

    def test_aware_stripped(self):
        aware = datetime(2025, 6, 15, 17, 0, 0, tzinfo=timezone.utc)
        result = as_naive_utc(aware)
        assert result.tzinfo is None
        assert result.hour == 17


# ═══════════════════════════════════════════════════════════════════
#  clarity_framework
# ═══════════════════════════════════════════════════════════════════

from core.clarity_framework import ClarityFramework, ClarityDecision


class TestClarityFramework:
    def setup_method(self):
        ClarityFramework._recent_decisions = []

    def test_record_decision_returns_model(self):
        d = ClarityFramework.record_decision(
            what="deploy v2", why="scheduled", who={"actor": "ci"},
            where={"env": "prod"}, how={"steps": ["build"]},
            risk_score=0.3,
        )
        assert isinstance(d, ClarityDecision)
        assert d.what == "deploy v2"
        assert 0.0 <= d.risk_score <= 1.0
        assert d.id.startswith("decision_")

    def test_rolling_buffer_capped_at_50(self):
        for i in range(55):
            ClarityFramework.record_decision(
                what=f"action_{i}", why="test", who={}, where={},
                how={}, risk_score=0.1,
            )
        recent = ClarityFramework.get_recent_decisions()
        assert len(recent) == 50
        # Most recent is first
        assert recent[0]["what"] == "action_54"

    def test_related_ids_default_empty(self):
        d = ClarityFramework.record_decision(
            what="x", why="y", who={}, where={}, how={}, risk_score=0.0,
        )
        assert d.related_ids == []


# ═══════════════════════════════════════════════════════════════════
#  loop_output
# ═══════════════════════════════════════════════════════════════════

from core.loop_output import (
    GraceLoopOutput, LoopType, LoopStatus, ReasoningStep,
)


class TestGraceLoopOutput:
    def test_lifecycle_complete(self):
        out = GraceLoopOutput(loop_type=LoopType.OODA)
        out.start()
        assert out.status == LoopStatus.RUNNING
        out.complete(result={"answer": 42}, confidence=0.95, summary="done")
        assert out.success is True
        assert out.confidence == 0.95
        assert out.duration_ms >= 0

    def test_lifecycle_fail(self):
        out = GraceLoopOutput(loop_type=LoopType.EXECUTION)
        out.start()
        out.fail("timeout", details={"code": 504})
        assert out.failed is True
        assert out.error == "timeout"
        assert out.error_details == {"code": 504}

    def test_add_reasoning_steps(self):
        out = GraceLoopOutput()
        out.add_reasoning_step("observe", output="ok", confidence=0.8)
        out.add_reasoning_step("orient", output="aligned", confidence=0.9)
        assert out.step_count == 2
        assert out.average_step_confidence == pytest.approx(0.85)

    def test_average_confidence_empty(self):
        out = GraceLoopOutput()
        assert out.average_step_confidence == 0.0

    def test_to_dict_and_from_dict_roundtrip(self):
        out = GraceLoopOutput(loop_type=LoopType.LEARNING)
        out.start()
        out.add_reasoning_step("step1", output="val", confidence=0.7)
        out.complete(result={"x": 1}, confidence=0.6, summary="s")
        d = out.to_dict()
        restored = GraceLoopOutput.from_dict(d)
        assert restored.loop_type == LoopType.LEARNING
        assert restored.confidence == 0.6
        assert len(restored.reasoning_steps) == 1

    def test_interrupt_sets_status(self):
        out = GraceLoopOutput()
        out.start()
        out.interrupt("user cancelled")
        assert out.status == LoopStatus.INTERRUPTED
        assert "user cancelled" in out.error


# ═══════════════════════════════════════════════════════════════════
#  resilience
# ═══════════════════════════════════════════════════════════════════

from core.resilience import (
    CircuitBreaker, ErrorBoundary, error_boundary, GracefulDegradation,
)


class TestCircuitBreaker:
    def test_closed_on_success(self):
        cb = CircuitBreaker("test-svc", failure_threshold=2)
        result = cb.call(lambda: "ok")
        assert result == "ok"
        assert cb.state == CircuitBreaker.CLOSED

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test-svc", failure_threshold=2, reset_timeout=300)
        for _ in range(2):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")), fallback="fb")
        assert cb.state == CircuitBreaker.OPEN

    def test_open_returns_fallback(self):
        cb = CircuitBreaker("test-svc", failure_threshold=1, reset_timeout=999)
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError()), fallback="fb")
        assert cb.state == CircuitBreaker.OPEN
        result = cb.call(lambda: "should not run", fallback="blocked")
        assert result == "blocked"

    def test_half_open_recovery(self):
        cb = CircuitBreaker("test-svc", failure_threshold=1, reset_timeout=0)
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError()), fallback="x")
        assert cb.state == CircuitBreaker.OPEN
        # reset_timeout=0 means immediate transition to HALF_OPEN
        result = cb.call(lambda: "recovered")
        assert result == "recovered"
        assert cb.state == CircuitBreaker.CLOSED

    def test_status_dict(self):
        cb = CircuitBreaker("svc", failure_threshold=5)
        s = cb.status()
        assert s["name"] == "svc"
        assert s["state"] == "closed"
        assert s["threshold"] == 5


class TestErrorBoundary:
    def test_suppresses_exception(self):
        with ErrorBoundary("test"):
            raise ValueError("should be caught")
        # If we reach here, exception was suppressed

    def test_decorator_returns_fallback(self):
        @error_boundary("test-fn", fallback={"error": True})
        def failing():
            raise RuntimeError("boom")

        result = failing()
        assert result == {"error": True}

    def test_decorator_passes_through_on_success(self):
        @error_boundary("test-fn", fallback=None)
        def succeeding(x):
            return x * 2

        assert succeeding(5) == 10


class TestGracefulDegradation:
    def setup_method(self):
        GracefulDegradation._level = GracefulDegradation.FULL

    def test_default_full(self):
        assert GracefulDegradation.get_level() == "full"

    def test_set_and_get(self):
        GracefulDegradation.set_level(GracefulDegradation.EMERGENCY)
        assert GracefulDegradation.get_level() == "emergency"

    def test_status_has_all_levels(self):
        s = GracefulDegradation.status()
        assert set(s["services"].keys()) == {"full", "reduced", "emergency", "read_only"}


# ═══════════════════════════════════════════════════════════════════
#  safety — security scanning + budget
# ═══════════════════════════════════════════════════════════════════

from core.safety import scan_code_security, check_budget, record_usage, _budget


class TestScanCodeSecurity:
    def test_safe_code(self):
        result = scan_code_security("x = 1 + 2\nprint(x)")
        assert result["safe"] is True
        assert result["blocked"] is False
        assert result["total"] == 0

    def test_critical_blocked(self):
        result = scan_code_security("exec('import os')")
        assert result["safe"] is False
        assert result["blocked"] is True
        assert any(f["severity"] == "critical" for f in result["findings"])

    def test_comment_lines_skipped(self):
        result = scan_code_security("# exec('hack')\nx = 1")
        assert result["safe"] is True

    def test_multiple_findings(self):
        code = "eval('x')\nos.system('ls')\nsubprocess.Popen(['ls'])"
        result = scan_code_security(code, filepath="gen.py")
        assert result["total"] >= 3
        assert all(f["file"] == "gen.py" for f in result["findings"])


class TestBudgetCircuitBreaker:
    def setup_method(self):
        _budget["total_calls"] = 0
        _budget["total_tokens_est"] = 0
        _budget["window_start"] = time.time()
        _budget["blocked"] = 0
        _budget["limit_calls_per_hour"] = 500
        _budget["limit_tokens_per_hour"] = 500000

    def test_within_budget(self):
        assert check_budget() is True

    def test_exceeds_call_limit(self):
        _budget["total_calls"] = 500
        assert check_budget() is False

    def test_record_usage_increments(self):
        record_usage(tokens=100)
        record_usage(tokens=200)
        assert _budget["total_calls"] == 2
        assert _budget["total_tokens_est"] == 300

    def test_window_reset(self):
        _budget["total_calls"] = 999
        _budget["window_start"] = time.time() - 7200  # 2 hours ago
        assert check_budget() is True  # window resets
        assert _budget["total_calls"] == 0


# ═══════════════════════════════════════════════════════════════════
#  determinism
# ═══════════════════════════════════════════════════════════════════

from core.determinism import (
    deterministic_choice, deterministic_temperature,
    should_use_llm, llm_kwargs_for_determinism,
    deterministic_model_choice, deterministic_run_id,
    _hash_payload,
)


class TestDeterministicChoice:
    def test_same_seed_same_result(self):
        opts = ["a", "b", "c", "d"]
        r1 = deterministic_choice(opts, "seed-42")
        r2 = deterministic_choice(opts, "seed-42")
        assert r1 == r2
        assert r1 in opts

    def test_empty_returns_none(self):
        assert deterministic_choice([], "anything") is None

    def test_different_seeds_can_differ(self):
        opts = list(range(100))
        r1 = deterministic_choice(opts, "alpha")
        r2 = deterministic_choice(opts, "beta")
        # With 100 options, extremely unlikely to collide
        assert r1 != r2


class TestShouldUseLlm:
    def test_force_deterministic(self):
        assert should_use_llm(force_deterministic=True) is False

    def test_phase0_no_handoff(self):
        assert should_use_llm(phase0_result={"handoff_to_llm": False}) is False

    def test_default_true(self):
        assert should_use_llm() is True

    def test_phase0_with_handoff(self):
        assert should_use_llm(phase0_result={"handoff_to_llm": True}) is True


class TestDeterministicTemperature:
    def test_deterministic_zero(self):
        assert deterministic_temperature(True) == 0.0

    def test_non_deterministic_capped(self):
        t = deterministic_temperature(False)
        assert t == pytest.approx(0.3)

    def test_llm_kwargs_merge(self):
        kw = llm_kwargs_for_determinism(True, model="gpt-4")
        assert kw["temperature"] == 0.0
        assert kw["model"] == "gpt-4"


class TestDeterministicModelChoice:
    def test_empty_returns_empty(self):
        assert deterministic_model_choice([]) == ""

    def test_single_model(self):
        assert deterministic_model_choice(["qwen"]) == "qwen"

    def test_deterministic_same_seed(self):
        models = ["a", "b", "c"]
        r1 = deterministic_model_choice(models, "task-x")
        r2 = deterministic_model_choice(models, "task-x")
        assert r1 == r2


# ═══════════════════════════════════════════════════════════════════
#  tracing
# ═══════════════════════════════════════════════════════════════════

from core.tracing import new_trace, get_trace_id, add_span, get_trace, light_track, get_recent_keys, LightKey, _ring_buffer


class TestTracing:
    def test_new_trace_returns_hex(self):
        tid = new_trace("/api/chat", "handle")
        assert len(tid) == 16
        int(tid, 16)  # must be valid hex

    def test_get_trace_id_consistent(self):
        tid = new_trace("/x")
        assert get_trace_id() == tid

    def test_add_span_and_get_trace(self):
        new_trace("/test")
        add_span("step1", {"key": "val"})
        add_span("step2")
        trace = get_trace()
        assert len(trace["spans"]) == 2
        assert trace["spans"][0]["name"] == "step1"
        assert trace["duration_ms"] >= 0

    def test_light_track_appends_to_buffer(self):
        before = len(_ring_buffer)
        light_track("test_event", "something happened", who="test")
        assert len(_ring_buffer) >= before + 1
        last = _ring_buffer[-1]
        assert isinstance(last, LightKey)
        assert last.key_type == "test_event"


# ═══════════════════════════════════════════════════════════════════
#  hot_reload
# ═══════════════════════════════════════════════════════════════════

from core.hot_reload import (
    hot_reload_module, get_reload_history, _file_path_to_module,
    _reload_history,
)


class TestHotReload:
    def setup_method(self):
        _reload_history.clear()

    def test_not_loaded_module(self):
        result = hot_reload_module("totally.fake.module.xyz")
        assert result["status"] == "not_loaded"

    def test_reload_real_module(self):
        import json
        result = hot_reload_module("json")
        assert result["status"] == "reloaded"
        assert result["state_preserved"] is False

    def test_history_recorded(self):
        hot_reload_module("nonexistent.mod")
        assert len(get_reload_history()) == 1

    def test_file_path_to_module(self):
        from pathlib import Path
        import tempfile, os
        root = Path(tempfile.gettempdir()) / "backend"
        fp = root / "core" / "services" / "chat_service.py"
        # _file_path_to_module uses resolve(), so create dirs to make it work
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.touch(exist_ok=True)
        assert _file_path_to_module(root.resolve(), fp) == "core.services.chat_service"

    def test_file_path_to_module_init_skipped(self):
        from pathlib import Path
        import tempfile
        root = Path(tempfile.gettempdir()) / "backend"
        fp = root / "core" / "__init__.py"
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.touch(exist_ok=True)
        assert _file_path_to_module(root.resolve(), fp) is None


# ═══════════════════════════════════════════════════════════════════
#  environment (mocked filesystem)
# ═══════════════════════════════════════════════════════════════════

from core.environment import get_environment, set_environment, _active_env


class TestEnvironment:
    def setup_method(self):
        _active_env.clear()
        _active_env["default"] = "grace-ai"

    def test_default_env(self):
        assert get_environment() == "grace-ai"

    @patch("core.environment.PROJECTS_DIR")
    def test_set_environment(self, mock_dir):
        mock_path = MagicMock()
        mock_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        result = set_environment("myproject", user_id="u1")
        assert result["environment"] == "myproject"
        assert get_environment("u1") == "myproject"

    def test_get_unknown_user_defaults(self):
        assert get_environment("unknown_user") == "grace-ai"
