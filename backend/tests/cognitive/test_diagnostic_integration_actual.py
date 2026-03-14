"""Integration tests for the end-to-end diagnostic cycle.

Tests the full path: error occurs → error pipeline classifies it →
deterministic healer tries → coding agent escalation → learning recorded.

External connections (DB, Qdrant, LLM) are mocked.
"""
import os
import sys
import pytest
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ.setdefault("SKIP_EMBEDDING_LOAD", "true")
os.environ.setdefault("SKIP_QDRANT_CHECK", "true")
os.environ.setdefault("SKIP_OLLAMA_CHECK", "true")
os.environ.setdefault("DISABLE_GENESIS_TRACKING", "true")


# ── 1. Error classification integration ──────────────────────────────────

from self_healing.error_pipeline import classify_error


def test_classify_attribute_error():
    assert classify_error(AttributeError("has no attribute 'foo'")) == "attribute"


def test_classify_import_error():
    assert classify_error(ImportError("No module named 'xyz'")) == "import"


def test_classify_network_error():
    assert classify_error(ConnectionError("Connection refused")) == "network"


def test_classify_schema_error():
    exc = Exception("UndefinedColumn: column does not exist")
    assert classify_error(exc) == "schema"


def test_classify_name_error():
    assert classify_error(NameError("name 'x' is not defined")) == "name"


def test_classify_type_error():
    assert classify_error(TypeError("takes 1 argument")) == "type"


def test_classify_unknown():
    assert classify_error(RuntimeError("something random")) == "unknown"


# ── 2. Error pipeline → healer routing ───────────────────────────────────

def test_error_pipeline_processes_attribute_error():
    """An AttributeError should reach the deterministic healer."""
    from self_healing.error_pipeline import ErrorPipeline
    import time

    pipeline = ErrorPipeline()
    # Just verify handle() doesn't crash
    pipeline.handle(
        AttributeError("'NoneType' object has no attribute 'foo'"),
        context={"test": True},
        module="test_module",
        function="test_func",
    )
    # Give worker thread time to process
    time.sleep(2)
    # Pipeline should still be alive
    assert pipeline._worker.is_alive()


# ── 3. MTTR tracking ─────────────────────────────────────────────────────

from self_healing.error_pipeline import record_heal_time, get_mttr


def test_mttr_tracking():
    record_heal_time("test_class", 1.5)
    record_heal_time("test_class", 2.5)
    mttr = get_mttr("test_class")
    assert mttr == 2.0  # average of 1.5 and 2.5


def test_mttr_empty():
    assert get_mttr("nonexistent") is None


# ── 4. Deduplication ─────────────────────────────────────────────────────

from self_healing.error_pipeline import _error_key, _already_seen


def test_deduplication():
    key = _error_key("TestError", "test_location_unique_123")
    # First time — not seen
    assert _already_seen(key) is False
    # Second time — already seen
    assert _already_seen(key) is True


# ── 5. Trigger fabric start ─────────────────────────────────────────────

def test_trigger_fabric_start():
    """Trigger fabric should start without crashing even without FastAPI app."""
    from self_healing.trigger_fabric import start
    import self_healing.trigger_fabric as tf

    # Reset for test
    tf._started = False
    start(app=None)
    assert tf._started is True


# ── 6. Full diagnostic cycle ────────────────────────────────────────────

def test_full_diagnostic_cycle(monkeypatch):
    """Error → diagnosis → classification → healing attempt → learning."""
    from cognitive.autonomous_diagnostics import AutonomousDiagnostics

    # Reset singleton
    AutonomousDiagnostics._instance = None
    diag = AutonomousDiagnostics.get_instance()

    # Mock smoke_test to avoid real connections
    import cognitive.test_framework as tf
    monkeypatch.setattr(tf, "smoke_test", lambda: {
        "passed": 3, "failed": 1, "status": "DEGRADED",
        "checks": [
            {"name": "database", "passed": True, "detail": "OK"},
            {"name": "qdrant", "passed": True, "detail": "OK"},
            {"name": "llm", "passed": True, "detail": "OK"},
            {"name": "test_sensor", "passed": False, "detail": "Sensor down"},
        ]
    })

    result = diag.on_error("TestError", "test failure", "test_component")
    assert result["event"] == "error"
    assert result["error_type"] == "TestError"
    assert "auto_fixed" in result
    assert len(diag._failure_history) >= 1


if __name__ == "__main__":
    pytest.main(["-v", __file__])
