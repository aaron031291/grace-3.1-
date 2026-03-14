"""
Real logic tests for Diagnostic Engine sensor defaults.

Verifies that sensor health flags default to False (DEGRADED) not True (HEALTHY),
so unchecked services don't silently pass.

No mocks. Tests actual dataclass defaults.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from diagnostic_machine.sensors import MetricsData, LogData, AgentOutputData


# ── MetricsData defaults ─────────────────────────────────────────────────

def test_metrics_health_defaults_are_false():
    """All health flags should default to False, not True."""
    m = MetricsData()
    assert m.database_health is False, "database_health should default False"
    assert m.vector_db_health is False, "vector_db_health should default False"
    assert m.llm_health is False, "llm_health should default False"
    assert m.embedding_health is False, "embedding_health should default False"
    assert m.learning_memory_health is False, "learning_memory_health should default False"
    assert m.genesis_qdrant_health is False, "genesis_qdrant_health should default False"


def test_metrics_numeric_defaults_are_zero():
    """Numeric metrics should default to 0."""
    m = MetricsData()
    assert m.cpu_percent == 0.0
    assert m.memory_percent == 0.0
    assert m.disk_percent == 0.0
    assert m.active_connections == 0
    assert m.request_latency_ms == 0.0
    assert m.requests_per_second == 0.0


def test_metrics_explicit_true_overrides():
    """Explicitly setting health to True should work."""
    m = MetricsData(database_health=True, llm_health=True)
    assert m.database_health is True
    assert m.llm_health is True
    # Others still False
    assert m.vector_db_health is False
    assert m.embedding_health is False


def test_metrics_timestamp_is_set():
    """Timestamp should be auto-populated."""
    m = MetricsData()
    assert m.timestamp is not None


# ── LogData defaults ─────────────────────────────────────────────────────

def test_log_data_defaults():
    """LogData should initialize with empty collections."""
    d = LogData()
    assert d.log_level_counts == {}
    assert d.error_messages == []
    assert d.warning_messages == []
    assert d.recent_exceptions == []
    assert d.log_volume_per_minute == 0.0


# ── AgentOutputData defaults ─────────────────────────────────────────────

def test_agent_output_defaults():
    """AgentOutputData should default to zero counts."""
    a = AgentOutputData()
    assert a.total_decisions == 0
    assert a.successful_decisions == 0
    assert a.failed_decisions == 0
    assert a.pending_decisions == 0
    assert a.average_confidence == 0.0
    assert a.invariant_violations == 0
    assert a.recent_decisions == []


# ── Degradation logic ────────────────────────────────────────────────────

def test_unchecked_service_reports_degraded():
    """A MetricsData with no checks run should report all services as unhealthy."""
    m = MetricsData()
    unhealthy_count = sum([
        not m.database_health,
        not m.vector_db_health,
        not m.llm_health,
        not m.embedding_health,
        not m.learning_memory_health,
        not m.genesis_qdrant_health,
    ])
    assert unhealthy_count == 6, "All 6 services should be unhealthy by default"


def test_partial_check_shows_partial_health():
    """Only checked services should show as healthy."""
    m = MetricsData()
    m.database_health = True  # only DB checked
    m.llm_health = True       # only LLM checked

    healthy = [m.database_health, m.llm_health]
    unhealthy = [m.vector_db_health, m.embedding_health,
                 m.learning_memory_health, m.genesis_qdrant_health]

    assert all(healthy), "Checked services should be healthy"
    assert not any(unhealthy), "Unchecked services should be unhealthy"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
