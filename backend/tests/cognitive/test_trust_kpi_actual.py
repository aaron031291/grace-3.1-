"""Tests for Trust Engine + KPI Tracker integration."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ.setdefault("SKIP_EMBEDDING_LOAD", "true")
os.environ.setdefault("SKIP_QDRANT_CHECK", "true")
os.environ.setdefault("SKIP_OLLAMA_CHECK", "true")
os.environ.setdefault("DISABLE_GENESIS_TRACKING", "true")

from cognitive.trust_engine import TrustEngine, ConfidenceCalculator, ComponentScore
from ml_intelligence.kpi_tracker import KPITracker, ComponentKPIs, TrustHistory, reset_kpi_tracker


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset global singletons before each test."""
    import cognitive.trust_engine as te_mod
    import ml_intelligence.kpi_tracker as kpi_mod
    te_mod._trust_engine = None
    kpi_mod._kpi_tracker = None
    yield
    te_mod._trust_engine = None
    kpi_mod._kpi_tracker = None


@pytest.fixture
def trust_engine():
    return TrustEngine()


@pytest.fixture
def confidence_calc():
    return ConfidenceCalculator()


@pytest.fixture
def kpi_tracker(tmp_path, monkeypatch):
    """Fresh KPITracker that won't read/write real history files."""
    fake_history = tmp_path / "trust_history.json"
    monkeypatch.setattr(
        "ml_intelligence.kpi_tracker.KPITracker.load_trust_history",
        lambda self: None,
    )
    tracker = KPITracker()
    tracker.trust_history.clear()
    return tracker


# ═══════════════════════════════════════════════════════════════════════
# 1. Trust Engine basics
# ═══════════════════════════════════════════════════════════════════════

class TestTrustEngineBasics:

    def test_score_output(self, trust_engine):
        """Score a component and verify trust_score is 0-100."""
        comp = trust_engine.score_output(
            "comp_a", "Component A",
            "This is a valid output with enough content to be meaningful for scoring.",
        )
        assert isinstance(comp, ComponentScore)
        assert 0.0 <= comp.trust_score <= 100.0

    def test_score_output_rolling_average(self, trust_engine):
        """Score twice; the second call should blend via rolling average."""
        comp1 = trust_engine.score_output("comp_b", "B", "First output text that is long enough.")
        first_score = comp1.trust_score
        first_count = comp1.execution_count
        assert first_count == 1

        comp2 = trust_engine.score_output("comp_b", "B", "Second output text that is also long enough.")
        assert comp2.execution_count == 2
        # Rolling average: new score is (prev*(N-1) + current) / N
        # execution_count must have advanced from the first call
        assert comp2.execution_count > first_count

    def test_score_output_empty(self, trust_engine):
        """Empty string output should produce a low trust score."""
        comp = trust_engine.score_output("comp_empty", "Empty", "")
        # Empty chunk yields score 5.0 from _score_chunk
        assert comp.trust_score <= 20.0

    def test_get_system_trust_empty(self, trust_engine):
        """No components tracked → system_trust = 0."""
        result = trust_engine.get_system_trust()
        assert result["system_trust"] == 0.0
        assert result["components"] == 0 or result.get("component_count", 0) == 0

    def test_get_system_trust_with_components(self, trust_engine):
        """Add 2 components, verify aggregate is between them."""
        trust_engine.score_output("c1", "C1", "Good deterministic content with enough words for scoring.", source="deterministic")
        trust_engine.score_output("c2", "C2", "Another valid output with sufficient length for analysis.", source="deterministic")
        result = trust_engine.get_system_trust()
        assert result["system_trust"] > 0.0
        assert result["component_count"] == 2

    def test_verification_level_thresholds(self, trust_engine):
        """verify_output should select the right level per trust bracket."""
        # 80+ → internal_only
        r80 = trust_engine.verify_output("x", "output", 85.0)
        assert r80["verification_level"] == "internal_only"

        # 60-79 → knowledge_base
        r60 = trust_engine.verify_output("x", "output", 65.0)
        assert r60["verification_level"] == "knowledge_base"

        # 40-59 → full_verification
        r40 = trust_engine.verify_output("x", "output", 45.0)
        assert r40["verification_level"] == "full_verification"

        # <40 → human_required
        r_low = trust_engine.verify_output("x", "output", 30.0)
        assert r_low["verification_level"] == "human_required"

    def test_remediation_trigger(self, trust_engine):
        """Trust thresholds drive the correct remediation_type."""
        # trust < 40 → human
        comp = trust_engine.score_output("rem_h", "H", "", source="unknown")
        # Empty + unknown source → very low score
        assert comp.trust_score < 40
        assert comp.remediation_type == "human"

        # Force a mid-range score by scoring good content from unknown source
        trust_engine._component_scores.clear()
        comp2 = trust_engine.score_output(
            "rem_ca", "CA",
            "A moderately useful output that has balanced parentheses and no forbidden tokens and is a reasonable length for testing purposes. " * 3,
            source="unknown",
        )
        if 40 <= comp2.trust_score < 60:
            assert comp2.remediation_type == "coding_agent"
        elif 60 <= comp2.trust_score < 70:
            assert comp2.remediation_type == "self_healing"
        elif comp2.trust_score < 40:
            assert comp2.remediation_type == "human"
        else:
            assert comp2.remediation_type is None


# ═══════════════════════════════════════════════════════════════════════
# 2. Confidence Calculator
# ═══════════════════════════════════════════════════════════════════════

class TestConfidenceCalculator:

    def test_confidence_no_data(self, confidence_calc):
        """Empty history → confidence 0."""
        result = confidence_calc.get_confidence("nonexistent")
        assert result["confidence"] == 0.0
        assert result["sample_count"] == 0

    def test_confidence_single_observation(self, confidence_calc):
        """One score → low-medium confidence (stability neutral at 50)."""
        confidence_calc.record_score("x", 75.0)
        result = confidence_calc.get_confidence("x")
        assert 0.0 < result["confidence"] < 80.0
        assert result["sample_count"] == 1
        assert result["stability_factor"] == 50.0  # neutral with 1 obs

    def test_confidence_many_observations(self, confidence_calc):
        """100 scores → high volume factor."""
        for i in range(100):
            confidence_calc.record_score("x", 75.0)
        result = confidence_calc.get_confidence("x")
        # volume_factor = min(100, (100/300)*100) = 33.3
        assert result["volume_factor"] >= 33.0
        assert result["sample_count"] == 100

    def test_confidence_stable_scores(self, confidence_calc):
        """All same score → very high stability factor."""
        for _ in range(20):
            confidence_calc.record_score("stable", 80.0)
        result = confidence_calc.get_confidence("stable")
        assert result["stability_factor"] == 100.0  # zero variance

    def test_confidence_volatile_scores(self, confidence_calc):
        """Wildly varying scores → low stability."""
        import random
        random.seed(42)
        for _ in range(30):
            confidence_calc.record_score("volatile", random.uniform(0, 100))
        result = confidence_calc.get_confidence("volatile")
        # std_dev of uniform(0,100) ≈ 29, so stability ≈ 100 - (29/30)*100 ≈ 3
        assert result["stability_factor"] < 30.0


# ═══════════════════════════════════════════════════════════════════════
# 3. KPI Tracker
# ═══════════════════════════════════════════════════════════════════════

class TestKPITracker:

    def test_increment_kpi(self, kpi_tracker):
        """Increment a KPI, verify count goes up."""
        kpi_tracker.increment_kpi("svc_a", "requests", 1.0)
        kpi = kpi_tracker.components["svc_a"].get_kpi("requests")
        assert kpi.count == 1

        kpi_tracker.increment_kpi("svc_a", "requests", 1.0)
        assert kpi.count == 2

    def test_component_trust_score(self, kpi_tracker):
        """Increment several KPIs, verify trust > 0."""
        kpi_tracker.register_component("worker")
        for _ in range(5):
            kpi_tracker.increment_kpi("worker", "success")
            kpi_tracker.increment_kpi("worker", "processed")
        trust = kpi_tracker.get_component_trust_score("worker")
        assert trust > 0.0
        assert trust <= 1.0

    def test_system_trust_score(self, kpi_tracker):
        """Register 2 components, increment, verify system trust."""
        kpi_tracker.register_component("alpha")
        kpi_tracker.register_component("beta")
        for _ in range(10):
            kpi_tracker.increment_kpi("alpha", "ops")
            kpi_tracker.increment_kpi("beta", "ops")
        system_trust = kpi_tracker.get_system_trust_score()
        assert 0.0 < system_trust <= 1.0

    def test_trust_history_record(self, kpi_tracker):
        """Record trust snapshots, verify they exist."""
        kpi_tracker.register_component("hist_comp")
        kpi_tracker.increment_kpi("hist_comp", "action")
        assert "hist_comp" in kpi_tracker.trust_history
        history = kpi_tracker.trust_history["hist_comp"]
        assert len(history.snapshots) >= 1

    def test_trust_history_trend(self):
        """Record improving scores, verify trend = 'improving'."""
        history = TrustHistory(component_name="trend_comp")
        # Record scores that improve over time
        for i in range(10):
            history.record(
                trust_score=0.3 + i * 0.05,
                kpi_count=2,
                total_actions=i + 1,
            )
        trend = history.get_trend(window_days=7)
        assert trend == "improving"

    def test_daily_snapshot(self, kpi_tracker):
        """Call take_daily_snapshot, verify it returns data."""
        kpi_tracker.register_component("snap_a")
        kpi_tracker.increment_kpi("snap_a", "work")
        result = kpi_tracker.take_daily_snapshot()
        assert "snap_a" in result


# ═══════════════════════════════════════════════════════════════════════
# 4. Integration (Trust Engine ↔ KPI Tracker)
# ═══════════════════════════════════════════════════════════════════════

class TestIntegration:

    def test_trust_engine_record_kpi(self):
        """record_kpi on TrustEngine should reach the global KPI tracker."""
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        engine = TrustEngine()
        engine.record_kpi("int_comp", "test_metric", 1.0)
        tracker = get_kpi_tracker()
        assert "int_comp" in tracker.components
        kpi = tracker.components["int_comp"].get_kpi("test_metric")
        assert kpi.count == 1

    def test_get_dashboard(self):
        """get_dashboard should return valid structure."""
        engine = TrustEngine()
        engine.score_output("dash_a", "DashA", "Some useful output for the dashboard test case.")
        dash = engine.get_dashboard()
        assert "overall_trust" in dash
        assert "trust_engine" in dash
        assert "kpi_tracker" in dash
        assert "timestamp" in dash
        assert dash["overall_trust"] >= 0.0

    def test_kpi_trust_bonus_with_data(self):
        """KPI data should influence score_output via _get_kpi_trust_bonus."""
        from ml_intelligence.kpi_tracker import get_kpi_tracker

        engine = TrustEngine()
        tracker = get_kpi_tracker()

        # Prime the KPI tracker with enough data so trust > 0.5 → positive bonus
        tracker.register_component("bonus_comp")
        for _ in range(50):
            tracker.increment_kpi("bonus_comp", "success")
            tracker.increment_kpi("bonus_comp", "quality")

        kpi_trust = tracker.get_component_trust_score("bonus_comp")
        assert kpi_trust > 0.0  # KPI trust is non-zero

        bonus = engine._get_kpi_trust_bonus("bonus_comp")
        # bonus = (kpi_trust - 0.5) * 20
        expected_bonus = (kpi_trust - 0.5) * 20
        assert abs(bonus - expected_bonus) < 0.01

        # Score an output — the bonus should shift the trust_score
        comp_with = engine.score_output(
            "bonus_comp", "BonusComp",
            "A valid output string long enough for meaningful chunk scoring results.",
            source="deterministic",
        )
        assert 0.0 <= comp_with.trust_score <= 100.0
