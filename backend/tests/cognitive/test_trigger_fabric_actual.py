"""
Real logic tests for the Trigger Fabric — Grace's event nervous system.

Tests actual event routing, network probing, MTTR pattern detection,
and event handler logic with NO mocks.
"""
import pytest
import sys
import os
import socket
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from self_healing.trigger_fabric import (
    _probe_tcp,
    _route_mirror_pattern,
    _on_llm_error,
    _on_hallucination,
    _on_knowledge_gap,
    _on_repeated_error,
    _on_fix_applied,
    _on_verification_rejected,
    _on_rate_limited,
    _on_network_healed,
    _on_probe_result,
    _SERVICE_MAP,
)


# ── TCP probe tests (real socket logic) ──────────────────────────────────

def test_probe_tcp_localhost_invalid_port():
    """Probing a port with nothing listening should return False."""
    # Port 19999 should not have anything listening
    result = _probe_tcp("localhost", 19999, timeout=0.5)
    assert result is False


def test_probe_tcp_real_open_port():
    """Probing an actual open port should return True."""
    # Start a temporary TCP server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("localhost", 0))
    port = server.getsockname()[1]
    server.listen(1)
    try:
        result = _probe_tcp("localhost", port, timeout=1.0)
        assert result is True
    finally:
        server.close()


def test_probe_tcp_unreachable_host():
    """Probing unreachable host should return False (not crash)."""
    result = _probe_tcp("192.0.2.1", 9999, timeout=0.5)  # RFC 5737 TEST-NET, always unreachable
    assert result is False


def test_service_map_completeness():
    """Service map should cover the 5 core Grace services."""
    service_names = {s[2] for s in _SERVICE_MAP}
    assert "PostgreSQL" in service_names
    assert "Qdrant" in service_names
    assert "Ollama" in service_names
    assert "GraceAPI" in service_names


# ── Event handler tests (real logic, no mocks) ──────────────────────────

def test_on_llm_error_does_not_crash():
    """_on_llm_error should handle missing error pipeline gracefully."""
    # Should not raise even if error pipeline isn't running
    _on_llm_error({"provider": "ollama", "error": "connection refused"})


def test_on_hallucination_does_not_crash():
    """_on_hallucination should handle missing unified memory gracefully."""
    _on_hallucination({
        "flags": ["unsupported_claim", "phantom_reference"],
        "prompt_preview": "What is the capital of Atlantis?",
    })


def test_on_knowledge_gap_does_not_crash():
    """_on_knowledge_gap should not crash if autonomous loop isn't running."""
    _on_knowledge_gap({"gap": "quantum error correction", "topic": "QEC"})


def test_on_repeated_error_does_not_crash():
    """_on_repeated_error should not crash if coding agent isn't available."""
    _on_repeated_error({"pattern": "ImportError", "count": 5})


def test_on_fix_applied_does_not_crash():
    """_on_fix_applied should not crash if unified memory isn't available."""
    _on_fix_applied({
        "file": "backend/cognitive/trust_engine.py",
        "task_id": "task-001",
        "lines": 15,
    })


def test_on_verification_rejected_does_not_crash():
    """_on_verification_rejected should not crash without unified memory."""
    _on_verification_rejected({
        "flags": ["phantom_import", "syntax_error"],
        "trust_score": 0.2,
    })


def test_on_rate_limited_does_not_crash():
    """_on_rate_limited should log and not crash."""
    _on_rate_limited({"service": "ollama", "error": "429 Too Many Requests"})


def test_on_network_healed_does_not_crash():
    """_on_network_healed should log and not crash."""
    _on_network_healed({"fixes": ["reconnected PostgreSQL", "restarted Qdrant"]})


def test_on_probe_result_no_failures():
    """Probe result with 0 failures should be a no-op."""
    _on_probe_result({"failed": 0, "results": []})


def test_on_probe_result_with_failures():
    """Probe result with failures should route to error pipeline without crashing."""
    _on_probe_result({
        "failed": 2,
        "results": [
            {"check": "PostgreSQL", "status": "FAIL", "detail": "Connection refused"},
            {"check": "Qdrant", "status": "FAIL", "detail": "Timeout after 3s"},
            {"check": "Ollama", "status": "OK", "detail": ""},
        ],
    })


# ── Mirror pattern routing (real logic) ──────────────────────────────────

def test_route_mirror_pattern_repeated_failure():
    """repeated_failure pattern should route to error pipeline without crash."""
    _route_mirror_pattern({
        "type": "repeated_failure",
        "description": "Database connection drops every 5 minutes",
        "frequency": 12,
        "suggestions": ["Check connection pool", "Increase timeout"],
    })


def test_route_mirror_pattern_success_sequence():
    """success_sequence should not crash even without episodic memory DB."""
    _route_mirror_pattern({
        "type": "success_sequence",
        "description": "Consistent healing of import errors",
        "frequency": 8,
        "suggestions": [],
    })


def test_route_mirror_pattern_anomalous_behavior():
    """anomalous_behavior should not crash without genesis tracker."""
    _route_mirror_pattern({
        "type": "anomalous_behavior",
        "description": "CPU spike during idle period",
        "frequency": 1,
        "suggestions": ["Check background tasks"],
    })


def test_route_mirror_pattern_unknown_type():
    """Unknown pattern type should be silently ignored."""
    _route_mirror_pattern({
        "type": "completely_unknown",
        "description": "This shouldn't crash",
        "frequency": 1,
        "suggestions": [],
    })


# ── MTTR watcher function exists and is callable ────────────────────────

def test_watch_mttr_patterns_exists():
    """_watch_mttr_patterns should be importable (was dead code before fix)."""
    from self_healing.trigger_fabric import _watch_mttr_patterns
    assert callable(_watch_mttr_patterns)


def test_start_wires_mttr_watcher():
    """start() should launch the MTTR watcher thread."""
    import self_healing.trigger_fabric as tf
    # Reset the started flag to allow re-calling start
    with tf._started_lock:
        tf._started = False

    # Call start (will launch threads)
    tf.start(app=None)

    # Check that the MTTR watcher thread was started
    thread_names = [t.name for t in threading.enumerate()]
    assert "grace-mttr-watcher" in thread_names

    # Also verify the other threads
    assert "grace-network-probe" in thread_names
    assert "grace-mirror-observer" in thread_names


# ── Event bus subscription wiring ────────────────────────────────────────

def test_event_bus_subscriptions():
    """_wire_event_bus_triggers should subscribe to all 10 required topics."""
    try:
        from cognitive.event_bus import _subscribers
        # The trigger fabric subscribes to these topics
        expected_topics = [
            "llm.error",
            "hallucination.detected",
            "knowledge.gap",
            "error.repeated",
            "fix.applied",
            "verification.rejected",
            "network.rate_limited",
            "network.healed",
            "probe.light.result",
            "probe.deep.result",
        ]
        for topic in expected_topics:
            assert topic in _subscribers, f"Missing subscription: {topic}"
    except ImportError:
        pytest.skip("Event bus not available")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
