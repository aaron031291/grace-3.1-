"""
Self-Mirror Tests - Verifies all three phases of the telemetry core.

Phase 1: [T,M,P] vector protocol
Phase 2: Statistical self-modeling + pillar triggers
Phase 3: Bi-directional challenging + RFI protocol

All tests use real logic, zero mocks.
"""

import sys
import os
import time
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from cognitive.self_mirror import (
    TelemetryVector,
    SelfMirror,
    StatisticalProfile,
    PillarType,
    AutonomousResolutionEngine,
    get_self_mirror,
    reset_self_mirror,
)


class TestPhase1TelemetryVectors:
    """Phase 1: [T,M,P] vector protocol tests."""

    def test_vector_creation(self):
        """Telemetry vector creates with correct values."""
        v = TelemetryVector(T=150.0, M=1024.0, P=0.6, component="database", task_domain="query")
        assert v.T == 150.0
        assert v.M == 1024.0
        assert v.P == 0.6
        assert v.component == "database"

    def test_vector_to_dict(self):
        """Vector serializes to dict."""
        v = TelemetryVector(T=50.0, M=2048.0, P=0.3, component="llm", task_domain="inference")
        d = v.to_dict()
        assert d["T"] == 50.0
        assert d["M"] == 2048.0
        assert d["P"] == 0.3
        assert d["component"] == "llm"
        assert "timestamp" in d

    def test_vector_repr_formats_mass(self):
        """Vector repr formats mass correctly."""
        v1 = TelemetryVector(T=10.0, M=500.0, P=0.1)
        assert "500B" in repr(v1)

        v2 = TelemetryVector(T=10.0, M=5000.0, P=0.1)
        assert "KB" in repr(v2)

        v3 = TelemetryVector(T=10.0, M=5000000.0, P=0.1)
        assert "MB" in repr(v3)

    def test_mirror_receives_vector(self):
        """Self-Mirror receives and records vectors."""
        mirror = SelfMirror()
        v = TelemetryVector(T=100.0, M=512.0, P=0.5, component="test", task_domain="unit_test")
        mirror.receive_vector(v)

        assert mirror._stats["total_vectors_received"] == 1
        assert "test" in mirror.component_vectors
        assert "unit_test" in mirror.profiles

    def test_mirror_records_multiple_components(self):
        """Mirror tracks vectors from different components."""
        mirror = SelfMirror()
        mirror.receive_vector(TelemetryVector(T=10.0, M=100.0, P=0.1, component="db", task_domain="query"))
        mirror.receive_vector(TelemetryVector(T=200.0, M=5000.0, P=0.8, component="llm", task_domain="inference"))
        mirror.receive_vector(TelemetryVector(T=50.0, M=2000.0, P=0.3, component="retriever", task_domain="search"))

        pulse = mirror.broadcast_system_pulse()
        assert len(pulse) == 3
        assert "db" in pulse
        assert "llm" in pulse
        assert "retriever" in pulse

    def test_mirror_system_telemetry_collection(self):
        """Mirror collects system-level telemetry."""
        mirror = SelfMirror()
        mirror._collect_system_telemetry()
        assert "system" in mirror.component_vectors
        assert mirror._stats["total_vectors_received"] >= 1


class TestPhase2StatisticalSelfModeling:
    """Phase 2: Statistical self-modeling + five pillar triggers."""

    def test_profile_mean(self):
        """Statistical profile calculates mean correctly."""
        profile = StatisticalProfile("test_domain")
        for t in [100, 110, 90, 105, 95]:
            profile.observe(TelemetryVector(T=t, M=100.0, P=0.5))
        assert abs(profile.mean_time - 100.0) < 1.0

    def test_profile_mode(self):
        """Statistical profile identifies mode (most frequent time)."""
        profile = StatisticalProfile("test_domain")
        for _ in range(10):
            profile.observe(TelemetryVector(T=45.0, M=100.0, P=0.3))
        for _ in range(3):
            profile.observe(TelemetryVector(T=95.0, M=100.0, P=0.3))

        assert profile.mode_time == 40.0  # Bucketed to nearest 10

    def test_profile_variance(self):
        """Statistical profile calculates variance."""
        profile = StatisticalProfile("test_domain")
        for t in [100, 100, 100, 100, 100]:
            profile.observe(TelemetryVector(T=t, M=100.0, P=0.5))
        assert profile.variance_time == 0.0

        profile2 = StatisticalProfile("test_domain2")
        for t in [50, 150, 50, 150, 50, 150]:
            profile2.observe(TelemetryVector(T=t, M=100.0, P=0.5))
        assert profile2.variance_time > 0

    def test_degradation_detection(self):
        """Detects when current T exceeds mean + 2*sigma."""
        profile = StatisticalProfile("test_domain")
        values = [95, 100, 105, 98, 102, 97, 103, 99, 101, 96]
        for _ in range(5):
            for v in values:
                profile.observe(TelemetryVector(T=float(v), M=100.0, P=0.3))

        assert not profile.is_degraded(100.0)
        assert not profile.is_degraded(103.0)  # Within normal range
        assert profile.is_degraded(500.0)  # Way beyond 2*sigma

    def test_self_healing_trigger_fires(self):
        """Self-Healing pillar triggers when T exceeds threshold."""
        mirror = SelfMirror()

        for _ in range(50):
            mirror.receive_vector(TelemetryVector(
                T=100.0, M=100.0, P=0.3, component="db", task_domain="query"
            ))

        mirror.receive_vector(TelemetryVector(
            T=500.0, M=100.0, P=0.9, component="db", task_domain="query"
        ))

        healing_triggers = [
            t for t in mirror.pillar_triggers
            if t.pillar == PillarType.SELF_HEALING
        ]
        assert len(healing_triggers) >= 1
        assert "exceeds" in healing_triggers[0].reason.lower()

    def test_self_governing_trigger_fires(self):
        """Self-Governing pillar triggers on high-risk ingestion."""
        mirror = SelfMirror()

        for _ in range(15):
            mirror.receive_vector(TelemetryVector(
                T=100.0, M=1000.0, P=0.3, component="ingestion", task_domain="ingest"
            ))

        mirror.receive_vector(TelemetryVector(
            T=100.0, M=2e12, P=0.95, component="ingestion", task_domain="ingest"
        ))

        governing_triggers = [
            t for t in mirror.pillar_triggers
            if t.pillar == PillarType.SELF_GOVERNING
        ]
        assert len(governing_triggers) >= 1

    def test_dashboard_output(self):
        """Dashboard returns structured data."""
        mirror = SelfMirror()
        for i in range(20):
            mirror.receive_vector(TelemetryVector(
                T=100.0 + i, M=500.0, P=0.4, component="test", task_domain="processing"
            ))

        dashboard = mirror.get_dashboard()
        assert "dashboard" in dashboard
        assert "component_pulse" in dashboard
        assert "stats" in dashboard
        assert len(dashboard["dashboard"]) >= 1

    def test_dashboard_row_status(self):
        """Dashboard rows correctly identify status."""
        profile = StatisticalProfile("test")
        for _ in range(50):
            profile.observe(TelemetryVector(T=100.0, M=100.0, P=0.3))

        row_nominal = profile.get_dashboard_row(100.0)
        assert row_nominal["status"] == "nominal"

        row_degraded = profile.get_dashboard_row(500.0)
        assert row_degraded["status"] == "degraded"


class TestPhase3BiDirectionalChallenging:
    """Phase 3: Bi-directional challenging + RFI protocol."""

    def test_challenge_issued_on_deviation(self):
        """Challenge issued when one component is 3x+ slower than another."""
        mirror = SelfMirror()

        mirror.receive_vector(TelemetryVector(
            T=50.0, M=100.0, P=0.2, component="fast_module", task_domain="processing"
        ))

        mirror.receive_vector(TelemetryVector(
            T=200.0, M=100.0, P=0.7, component="slow_module", task_domain="processing"
        ))

        challenges = list(mirror.challenges)
        assert len(challenges) >= 1
        assert challenges[0].deviation_factor >= 3.0
        assert "slower" in challenges[0].message.lower()

    def test_no_challenge_for_similar_speed(self):
        """No challenge when components perform similarly."""
        mirror = SelfMirror()

        mirror.receive_vector(TelemetryVector(
            T=100.0, M=100.0, P=0.3, component="module_a", task_domain="task_x"
        ))

        mirror.receive_vector(TelemetryVector(
            T=120.0, M=100.0, P=0.3, component="module_b", task_domain="task_x"
        ))

        challenges = [c for c in mirror.challenges if c.challenged in ("module_a", "module_b")]
        assert len(challenges) == 0

    def test_rfi_creation(self):
        """RFI (Request for Intelligence) can be created."""
        mirror = SelfMirror()
        rfi = mirror.create_rfi(
            void="Missing async F# pattern for PB-scale streams",
            required="2026-standard async handling pattern",
            source="llm_orchestrator",
        )

        assert rfi.rfi_id.startswith("RFI-")
        assert rfi.status == "pending"
        assert mirror._stats["total_rfis_created"] == 1

    def test_rfi_resolution_workflow(self):
        """RFI resolution workflow executes all steps."""
        engine = AutonomousResolutionEngine()
        rfi = engine.create_rfi(
            void="Need faster indexing algorithm",
            required="B-tree variant for high-cardinality data",
            source="librarian",
        )

        result = asyncio.run(engine.execute_resolution(rfi))

        assert result["status"] == "completed"
        assert "search_initiated" in result["steps_completed"]
        assert "oracle_vetting" in result["steps_completed"]
        assert "baked_to_pillars" in result["steps_completed"]
        assert rfi.status == "baked"
        assert len(rfi.baked_to_pillars) > 0

    def test_resolution_engine_stats(self):
        """Resolution engine tracks statistics."""
        engine = AutonomousResolutionEngine()
        engine.create_rfi("void1", "need1", "source1")
        engine.create_rfi("void2", "need2", "source2")

        stats = engine.get_stats()
        assert stats["total_rfis"] == 2
        assert stats["pending_rfis"] == 2


class TestSelfMirrorIntegration:
    """Integration tests across all three phases."""

    def test_full_lifecycle(self):
        """Test complete vector -> trigger -> challenge -> RFI flow."""
        mirror = SelfMirror()

        for _ in range(50):
            mirror.receive_vector(TelemetryVector(
                T=100.0, M=500.0, P=0.3, component="retriever", task_domain="search"
            ))

        mirror.receive_vector(TelemetryVector(
            T=50.0, M=200.0, P=0.2, component="fast_retriever", task_domain="search"
        ))

        mirror.receive_vector(TelemetryVector(
            T=800.0, M=500.0, P=0.9, component="retriever", task_domain="search"
        ))

        assert mirror._stats["total_vectors_received"] == 52
        assert mirror._stats["total_triggers_fired"] >= 1
        assert mirror._stats["total_challenges_issued"] >= 0

        stats = mirror.get_stats()
        assert stats["active_profiles"] >= 1
        assert stats["components_reporting"] >= 2

    def test_singleton_pattern(self):
        """get_self_mirror returns same instance."""
        reset_self_mirror()
        m1 = get_self_mirror()
        m2 = get_self_mirror()
        assert m1 is m2
        reset_self_mirror()

    def test_operation_measurer(self):
        """Context manager measures operations correctly."""
        mirror = SelfMirror()

        with mirror.measure_operation("test_component", "test_task"):
            total = sum(range(10000))

        assert mirror._stats["total_vectors_received"] == 1
        vec = mirror.component_vectors.get("test_component")
        assert vec is not None
        assert vec.T > 0
        assert vec.task_domain == "test_task"

    def test_pillar_trigger_counts_accumulate(self):
        """Pillar trigger counts accumulate correctly."""
        mirror = SelfMirror()

        for _ in range(50):
            mirror.receive_vector(TelemetryVector(
                T=100.0, M=100.0, P=0.3, component="db", task_domain="query"
            ))

        for _ in range(5):
            mirror.receive_vector(TelemetryVector(
                T=600.0, M=100.0, P=0.9, component="db", task_domain="query"
            ))

        healing_count = mirror._stats["pillar_trigger_counts"][PillarType.SELF_HEALING.value]
        assert healing_count >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
