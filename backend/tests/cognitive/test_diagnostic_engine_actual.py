"""Tests for the Autonomous Diagnostic Engine cycle."""
import os
import sys
import gc
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ.setdefault("SKIP_EMBEDDING_LOAD", "true")
os.environ.setdefault("SKIP_QDRANT_CHECK", "true")
os.environ.setdefault("SKIP_OLLAMA_CHECK", "true")
os.environ.setdefault("DISABLE_GENESIS_TRACKING", "true")

from cognitive.autonomous_diagnostics import AutonomousDiagnostics


# ── Fixture: reset singleton between tests ───────────────────────────────

@pytest.fixture(autouse=True)
def reset_singleton():
    AutonomousDiagnostics._instance = None
    yield
    AutonomousDiagnostics._instance = None


# ── 1. AutonomousDiagnostics class tests ─────────────────────────────────

class TestAutonomousDiagnosticsClass:

    def test_singleton(self):
        """get_instance() returns same instance."""
        a = AutonomousDiagnostics.get_instance()
        b = AutonomousDiagnostics.get_instance()
        assert a is b

    def test_initial_state(self):
        """failure_history empty, counters at 0."""
        diag = AutonomousDiagnostics()
        assert diag._failure_history == []
        assert diag._auto_fixes_applied == 0
        assert diag._human_alerts_sent == 0
        assert diag._early_warnings == []

    def test_get_status(self):
        """returns dict with expected keys."""
        diag = AutonomousDiagnostics()
        status = diag.get_status()
        assert isinstance(status, dict)
        for key in ("total_failures_logged", "failures_today", "auto_fixes_today",
                     "auto_fixes_total", "human_alerts", "early_warnings"):
            assert key in status, f"Missing key: {key}"


# ── 2. Error handling cycle ──────────────────────────────────────────────

class TestErrorHandlingCycle:

    def test_on_error_basic(self, monkeypatch):
        """on_error returns dict with event, error_type, auto_fixed keys."""
        diag = AutonomousDiagnostics()
        monkeypatch.setattr(diag, "_attempt_fix", lambda c, m: {"fixed": False, "action": "logged"})
        monkeypatch.setattr(diag, "_log_failure", lambda *a, **kw: None)

        result = diag.on_error("TestError", "something broke", "test_component")
        assert isinstance(result, dict)
        assert result["event"] == "error"
        assert result["error_type"] == "TestError"
        assert "auto_fixed" in result

    def test_on_error_records_history(self, monkeypatch):
        """After calling on_error, failure_history should be non-empty."""
        diag = AutonomousDiagnostics()
        # Let _log_failure run normally but mock external calls inside it
        monkeypatch.setattr(diag, "_attempt_fix", lambda c, m: {"fixed": False, "action": "logged"})

        diag.on_error("TestError", "something broke", "test_component")
        assert len(diag._failure_history) > 0

    def test_on_error_recurring(self, monkeypatch):
        """Call on_error 4 times with same type — the 4th should have recurring=True."""
        diag = AutonomousDiagnostics()
        monkeypatch.setattr(diag, "_attempt_fix", lambda c, m: {"fixed": False, "action": "logged"})

        for _ in range(4):
            result = diag.on_error("RecurringError", "keeps happening", "test_component")

        assert result.get("recurring") is True
        assert result.get("occurrence_count", 0) >= 3


# ── 3. Self-fix attempt tests ───────────────────────────────────────────

class TestSelfFixAttempts:

    def test_attempt_fix_memory(self):
        """Passing 'memory' system should trigger gc.collect and return fixed=True."""
        diag = AutonomousDiagnostics()
        result = diag._attempt_fix("memory", "out of memory")
        assert result["fixed"] is True
        assert "garbage" in result["action"].lower() or "collection" in result["action"].lower()

    def test_attempt_fix_unknown(self):
        """Passing unknown system should return fixed=False."""
        diag = AutonomousDiagnostics()
        result = diag._attempt_fix("unknown_system_xyz", "weird error")
        assert result["fixed"] is False

    def test_attempt_fix_database(self, monkeypatch):
        """Passing 'database' should attempt db reconnect (mock it)."""
        diag = AutonomousDiagnostics()

        mock_init = lambda: None
        monkeypatch.setattr(
            "cognitive.autonomous_diagnostics.AutonomousDiagnostics._attempt_fix",
            AutonomousDiagnostics._attempt_fix,
        )
        # Mock the database session initializer to succeed
        import importlib
        mock_module = type(sys)("database.session")
        mock_module.initialize_session_factory = mock_init
        monkeypatch.setitem(sys.modules, "database.session", mock_module)

        result = diag._attempt_fix("database", "connection lost")
        assert result["fixed"] is True
        assert "database" in result["action"].lower()


# ── 4. Early warning system ──────────────────────────────────────────────

class TestEarlyWarningSystem:

    def test_check_early_warnings_returns_list(self):
        """Should return a list."""
        diag = AutonomousDiagnostics()
        warnings = diag._check_early_warnings()
        assert isinstance(warnings, list)

    def test_early_warnings_recurring_failures(self):
        """Populate failure_history with 5 same-type failures, check warnings detect it."""
        diag = AutonomousDiagnostics()
        for i in range(5):
            diag._failure_history.append({
                "timestamp": "2026-03-14T00:00:00+00:00",
                "error_type": "RepeatedError",
                "error_message": "same problem",
                "auto_fixed": False,
                "action": "logged",
            })

        warnings = diag._check_early_warnings()
        recurring = [w for w in warnings if w["type"] == "recurring_failure"]
        assert len(recurring) >= 1
        assert "RepeatedError" in recurring[0]["message"]


# ── 5. Report generation ────────────────────────────────────────────────

class TestReportGeneration:

    def test_daily_report_structure(self, monkeypatch):
        """Mock smoke_test/diagnostic to avoid real connections, check report keys."""
        diag = AutonomousDiagnostics()

        fake_diag_result = {
            "smoke_test": {
                "checks": [],
                "passed": 5,
                "failed": 0,
                "status": "HEALTHY",
            },
            "full_test": {
                "passed": 10,
                "failed": 0,
            },
        }

        import cognitive.test_framework as tf
        monkeypatch.setattr(tf, "diagnostic", lambda: fake_diag_result)
        monkeypatch.setattr(diag, "_save_diagnostic", lambda r: None)
        monkeypatch.setattr(diag, "_check_early_warnings", lambda: [])

        report = diag.daily_report()
        assert isinstance(report, dict)
        for key in ("event", "date", "summary", "actions", "failures_today",
                     "auto_fixed_today", "human_alerts"):
            assert key in report, f"Missing key: {key}"
        assert report["event"] == "daily_report"


# ── 6. Consensus diagnose ───────────────────────────────────────────────

class TestConsensusDiagnose:

    def test_consensus_diagnose_callable(self):
        """Verify the method exists and is callable."""
        diag = AutonomousDiagnostics()
        assert hasattr(diag, "consensus_diagnose")
        assert callable(diag.consensus_diagnose)
