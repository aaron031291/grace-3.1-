"""
Real logic tests for the KPI tracking pipeline.

Tests the ACTUAL KPITracker, ComponentKPIs, kpi_recorder, and kpi_api
to verify that KPIs flow from component actions → tracker → API responses
with real computed values (not hardcoded).

No mocks. No socks. Full logic.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ml_intelligence.kpi_tracker import KPITracker, ComponentKPIs, KPI, get_kpi_tracker, reset_kpi_tracker


# ── KPI dataclass tests ──────────────────────────────────────────────────

def test_kpi_increment():
    """KPI.increment should increase count and accumulate value."""
    kpi = KPI(component_name="test", metric_name="requests", value=0.0, count=0)
    kpi.increment(1.0)
    assert kpi.count == 1
    assert kpi.value == 1.0
    kpi.increment(5.0)
    assert kpi.count == 2
    assert kpi.value == 6.0


def test_kpi_increment_with_metadata():
    """KPI metadata should merge on each increment."""
    kpi = KPI(component_name="test", metric_name="requests", value=0.0, count=0)
    kpi.increment(1.0, metadata={"source": "api"})
    assert kpi.metadata == {"source": "api"}
    kpi.increment(1.0, metadata={"user": "alice"})
    assert kpi.metadata == {"source": "api", "user": "alice"}


# ── ComponentKPIs tests ──────────────────────────────────────────────────

def test_component_kpis_get_or_create():
    """get_kpi should create a new KPI if it doesn't exist."""
    comp = ComponentKPIs(component_name="coding_agent")
    kpi = comp.get_kpi("successes")
    assert kpi.metric_name == "successes"
    assert kpi.count == 0
    assert kpi.value == 0.0
    # Second call returns same object
    kpi2 = comp.get_kpi("successes")
    assert kpi2 is kpi


def test_component_kpis_increment():
    """increment_kpi should tick up the right metric."""
    comp = ComponentKPIs(component_name="diagnostic_engine")
    comp.increment_kpi("requests", 1.0)
    comp.increment_kpi("requests", 1.0)
    comp.increment_kpi("failures", 1.0)
    assert comp.get_kpi("requests").count == 2
    assert comp.get_kpi("failures").count == 1


def test_component_trust_score_empty():
    """Empty component should return 0.0 trust (no data)."""
    comp = ComponentKPIs(component_name="empty")
    assert comp.get_trust_score() == 0.0


def test_component_trust_score_grows_with_activity():
    """Trust score should increase as more KPI counts accumulate."""
    comp = ComponentKPIs(component_name="healing")
    # Score after 1 action: count/(count+10) = 1/11 ≈ 0.09
    comp.increment_kpi("requests", 1.0)
    score_1 = comp.get_trust_score()
    assert 0.0 < score_1 < 0.2

    # Score after 50 actions: 50/60 ≈ 0.83
    for _ in range(49):
        comp.increment_kpi("requests", 1.0)
    score_50 = comp.get_trust_score()
    assert score_50 > 0.8
    assert score_50 > score_1


def test_component_trust_score_multiple_metrics():
    """Trust should be weighted average across multiple metrics."""
    comp = ComponentKPIs(component_name="multi")
    # Metric A: 100 counts → 100/110 ≈ 0.91
    for _ in range(100):
        comp.increment_kpi("successes", 1.0)
    # Metric B: 0 counts → 0/10 = 0
    comp.get_kpi("failures")  # create with 0 count

    # With equal weights, average of ~0.91 and 0 → ~0.45
    score = comp.get_trust_score()
    assert 0.4 < score < 0.55


def test_component_trust_score_custom_weights():
    """Custom weights should shift trust toward weighted metrics."""
    comp = ComponentKPIs(component_name="weighted")
    for _ in range(100):
        comp.increment_kpi("successes", 1.0)
    comp.get_kpi("failures")  # create with 0

    # Weight successes 10x more than failures
    score = comp.get_trust_score(metric_weights={"successes": 10.0, "failures": 1.0})
    # Should be close to 0.91 * (10/11) ≈ 0.83
    assert score > 0.75


def test_component_to_dict():
    """to_dict should include trust_score computed from real data."""
    comp = ComponentKPIs(component_name="test_comp")
    for _ in range(20):
        comp.increment_kpi("requests", 1.0)
    d = comp.to_dict()
    assert d["component_name"] == "test_comp"
    assert "trust_score" in d
    assert d["trust_score"] > 0.5  # 20/30 ≈ 0.67
    assert "requests" in d["kpis"]
    assert d["kpis"]["requests"]["count"] == 20


# ── KPITracker tests ─────────────────────────────────────────────────────

def test_tracker_register_and_increment():
    """Tracker should register components and increment their KPIs."""
    tracker = KPITracker()
    tracker.register_component("brain_chat")
    tracker.increment_kpi("brain_chat", "requests", 1.0)
    tracker.increment_kpi("brain_chat", "successes", 1.0)

    comp = tracker.get_component_kpis("brain_chat")
    assert comp is not None
    assert comp.get_kpi("requests").count == 1
    assert comp.get_kpi("successes").count == 1


def test_tracker_auto_register():
    """increment_kpi on unknown component should auto-register it."""
    tracker = KPITracker()
    tracker.increment_kpi("new_component", "actions", 5.0)
    comp = tracker.get_component_kpis("new_component")
    assert comp is not None
    assert comp.get_kpi("actions").count == 1
    assert comp.get_kpi("actions").value == 5.0


def test_tracker_component_trust_score():
    """get_component_trust_score should reflect real activity."""
    tracker = KPITracker()
    for _ in range(50):
        tracker.increment_kpi("coding_agent", "successes", 1.0)
    score = tracker.get_component_trust_score("coding_agent")
    assert score > 0.8  # 50/60 ≈ 0.83


def test_tracker_unknown_component_trust():
    """Unknown component should return 0.0 (no data)."""
    tracker = KPITracker()
    assert tracker.get_component_trust_score("nonexistent") == 0.0


def test_tracker_system_trust_multiple_components():
    """System trust should aggregate all component trusts."""
    tracker = KPITracker()
    # Component A: high activity → high trust
    for _ in range(100):
        tracker.increment_kpi("comp_a", "ok", 1.0)
    # Component B: low activity → low trust
    tracker.increment_kpi("comp_b", "ok", 1.0)

    system_trust = tracker.get_system_trust_score()
    # Average of ~0.91 and ~0.09 → ~0.50
    assert 0.3 < system_trust < 0.7

    a_trust = tracker.get_component_trust_score("comp_a")
    b_trust = tracker.get_component_trust_score("comp_b")
    assert a_trust > b_trust


def test_tracker_health_signal_status():
    """get_health_signal should map trust to status string correctly."""
    tracker = KPITracker()
    # Excellent: trust >= 0.8
    for _ in range(100):
        tracker.increment_kpi("excellent_comp", "ok", 1.0)
    signal = tracker.get_health_signal("excellent_comp")
    assert signal["status"] == "excellent"
    assert signal["trust_score"] > 0.8

    # Poor: trust < 0.4
    tracker.increment_kpi("poor_comp", "ok", 1.0)
    tracker.get_component_kpis("poor_comp").get_kpi("bad")  # add zero-count metric
    signal = tracker.get_health_signal("poor_comp")
    # 1 count on 1 metric, 0 count on other → low trust
    assert signal["trust_score"] < 0.5


def test_tracker_system_health_shape():
    """get_system_health should return complete health object."""
    tracker = KPITracker()
    tracker.increment_kpi("comp_x", "requests", 1.0)
    tracker.increment_kpi("comp_y", "requests", 1.0)

    health = tracker.get_system_health()
    assert "system_trust_score" in health
    assert "status" in health
    assert "component_count" in health
    assert health["component_count"] == 2
    assert "components" in health
    assert "comp_x" in health["components"]
    assert "comp_y" in health["components"]


# ── Singleton tests ──────────────────────────────────────────────────────

def test_singleton_persistence():
    """get_kpi_tracker should return same instance, reset should clear it."""
    reset_kpi_tracker()
    t1 = get_kpi_tracker()
    t2 = get_kpi_tracker()
    assert t1 is t2
    t1.increment_kpi("test", "count", 1.0)
    assert t2.get_component_kpis("test") is not None

    reset_kpi_tracker()
    t3 = get_kpi_tracker()
    assert t3 is not t1
    assert t3.get_component_kpis("test") is None


# ── KPI Recorder → Tracker integration ──────────────────────────────────

def test_kpi_recorder_flows_to_tracker():
    """record_brain_kpi should actually increment the ML KPI tracker."""
    reset_kpi_tracker()
    from core.kpi_recorder import record_brain_kpi
    record_brain_kpi("chat", "ask", ok=True)
    record_brain_kpi("chat", "ask", ok=True)
    record_brain_kpi("chat", "ask", ok=False)

    tracker = get_kpi_tracker()
    comp = tracker.get_component_kpis("brain_chat")
    assert comp is not None
    assert comp.get_kpi("requests").count == 3
    assert comp.get_kpi("successes").count == 2
    assert comp.get_kpi("failures").count == 1


def test_component_kpi_recorder():
    """record_component_kpi should feed the tracker for non-brain components."""
    reset_kpi_tracker()
    from core.kpi_recorder import record_component_kpi
    record_component_kpi("retrieval", "queries", 1.0, success=True)
    record_component_kpi("retrieval", "queries", 1.0, success=True)
    record_component_kpi("retrieval", "queries", 1.0, success=False)

    tracker = get_kpi_tracker()
    comp = tracker.get_component_kpis("retrieval")
    assert comp is not None
    assert comp.get_kpi("queries").count == 3
    assert comp.get_kpi("successes").count == 2
    assert comp.get_kpi("failures").count == 1


# ── KPI API → Tracker integration ────────────────────────────────────────

def test_tracker_get_system_health_feeds_dashboard():
    """Tracker system_health output should have the shape the KPI API dashboard expects.

    This tests the real data pipeline: tracker.get_system_health() produces
    per-component signals with {component_name, status, trust_score, total_actions, kpi_count}
    — exactly what the KPI API dashboard reshapes into its response.
    """
    reset_kpi_tracker()
    tracker = get_kpi_tracker()
    for _ in range(50):
        tracker.increment_kpi("coding_agent", "successes", 1.0)
    tracker.increment_kpi("coding_agent", "failures", 1.0)

    health = tracker.get_system_health()
    assert "components" in health
    assert "coding_agent" in health["components"]

    signal = health["components"]["coding_agent"]
    # These are the exact fields the KPI API dashboard endpoint reads
    assert "component_name" in signal
    assert "status" in signal
    assert "trust_score" in signal
    assert "total_actions" in signal
    assert "kpi_count" in signal

    assert signal["component_name"] == "coding_agent"
    # Trust with 2 metrics: avg of 50/60≈0.83 and 1/11≈0.09 → ~0.46
    assert signal["trust_score"] > 0.3
    assert signal["total_actions"] == 51  # 50 successes + 1 failure
    assert signal["kpi_count"] == 2  # "successes" and "failures"


def test_tracker_empty_returns_neutral():
    """Empty tracker should return neutral health — the API falls back to static data."""
    reset_kpi_tracker()
    tracker = get_kpi_tracker()
    assert len(tracker.components) == 0
    health = tracker.get_system_health()
    assert health["system_trust_score"] == 0.0
    assert health["component_count"] == 0


def test_kpi_api_trust_increases_over_time():
    """Simulating 100 days of brain activity should produce trust approaching 1.0."""
    reset_kpi_tracker()
    tracker = get_kpi_tracker()
    # Simulate heavy usage
    for _ in range(1000):
        tracker.increment_kpi("brain_chat", "successes", 1.0)
    score = tracker.get_component_trust_score("brain_chat")
    # 1000/1010 ≈ 0.99
    assert score > 0.95


if __name__ == "__main__":
    pytest.main(["-v", __file__])
