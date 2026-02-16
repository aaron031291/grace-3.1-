"""
TimeSense Engine Tests - Temporal reasoning, OODA timing, predictions, anomalies.

All real logic, zero mocks.
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from cognitive.timesense import (
    TimeSenseEngine, OperationTimer, OODACycleTimer,
    TemporalContext, TimePrediction, CostEstimate, TemporalAnomaly,
    TimeOfDay, WorkPattern, get_timesense, reset_timesense,
)


class TestOperationTimer:
    def test_record_and_mean(self):
        timer = OperationTimer("test.op")
        for d in [100, 110, 90, 105, 95]:
            timer.record(d)
        assert abs(timer.mean - 100.0) < 1.0
        assert timer.total_invocations == 5

    def test_median(self):
        timer = OperationTimer("test.op")
        for d in [10, 20, 30, 40, 50]:
            timer.record(d)
        assert timer.median == 30.0

    def test_p95(self):
        timer = OperationTimer("test.op")
        for d in range(1, 101):
            timer.record(float(d))
        assert timer.p95 >= 95.0

    def test_std(self):
        timer = OperationTimer("test.op")
        for d in [100, 100, 100]:
            timer.record(d)
        assert timer.std == 0.0

        timer2 = OperationTimer("test.op2")
        for d in [50, 150]:
            timer2.record(d)
        assert timer2.std > 0

    def test_success_rate(self):
        timer = OperationTimer("test.op")
        timer.record(100, success=True)
        timer.record(100, success=True)
        timer.record(100, success=False)
        assert abs(timer.success_rate - 0.667) < 0.01

    def test_predict(self):
        timer = OperationTimer("test.op")
        for _ in range(50):
            timer.record(100.0)
        pred = timer.predict()
        assert pred.operation == "test.op"
        assert abs(pred.predicted_ms - 100.0) < 1.0
        assert pred.confidence > 0.4

    def test_anomaly_detection(self):
        timer = OperationTimer("test.op")
        for _ in range(50):
            timer.record(100.0 + (hash(str(_)) % 20 - 10))
        anomaly = timer.is_anomalous(500.0)
        assert anomaly is not None
        assert anomaly.severity in ("minor", "moderate", "severe")

        normal = timer.is_anomalous(105.0)
        assert normal is None

    def test_stats(self):
        timer = OperationTimer("test.op")
        timer.record(100.0)
        stats = timer.get_stats()
        assert stats["operation"] == "test.op"
        assert stats["total_invocations"] == 1
        assert "mean_ms" in stats


class TestOODACycleTimer:
    def test_full_cycle(self):
        ooda = OODACycleTimer()
        ooda.start_cycle()
        ooda.start_phase("observe")
        time.sleep(0.001)
        ooda.end_phase("observe")
        ooda.start_phase("orient")
        time.sleep(0.001)
        ooda.end_phase("orient")
        ooda.start_phase("decide")
        time.sleep(0.001)
        ooda.end_phase("decide")
        ooda.start_phase("act")
        time.sleep(0.001)
        ooda.end_phase("act")
        total = ooda.end_cycle()
        assert total > 0

    def test_stats(self):
        ooda = OODACycleTimer()
        ooda.start_cycle()
        ooda.start_phase("observe")
        ooda.end_phase("observe")
        ooda.end_cycle()
        stats = ooda.get_stats()
        assert "full_cycle" in stats
        assert "phases" in stats
        assert "observe" in stats["phases"]


class TestTimeSenseEngine:
    def test_record_operation(self):
        engine = TimeSenseEngine()
        engine.record_operation("db.query", 50.0, "database")
        assert engine._stats["total_operations_timed"] == 1
        assert "db.query" in engine._operation_timers

    def test_temporal_context(self):
        engine = TimeSenseEngine()
        engine.record_operation("test", 10.0)
        ctx = engine.get_temporal_context()
        assert isinstance(ctx, TemporalContext)
        assert ctx.time_of_day in list(TimeOfDay)
        assert ctx.session_duration_seconds >= 0

    def test_predict_with_history(self):
        engine = TimeSenseEngine()
        for _ in range(20):
            engine.record_operation("api.chat", 200.0)
        pred = engine.predict("api.chat")
        assert abs(pred.predicted_ms - 200.0) < 1.0

    def test_predict_unknown_operation(self):
        engine = TimeSenseEngine()
        pred = engine.predict("never.seen")
        assert pred.confidence == 0.0
        assert pred.based_on_samples == 0

    def test_cost_estimate(self):
        engine = TimeSenseEngine()
        for _ in range(10):
            engine.record_operation("heavy.compute", 2000.0)
        cost = engine.estimate_cost("heavy.compute")
        assert cost.is_expensive is True
        assert cost.estimated_time_ms > 1000

    def test_anomaly_recorded(self):
        engine = TimeSenseEngine()
        for i in range(50):
            engine.record_operation("db.query", 100.0 + (i % 5))
        engine.record_operation("db.query", 5000.0)
        assert engine._stats["total_anomalies_detected"] >= 1
        anomalies = engine.get_anomalies()
        assert len(anomalies) >= 1

    def test_time_operation_context_manager(self):
        engine = TimeSenseEngine()
        with engine.time_operation("compute.sum", "math"):
            total = sum(range(10000))
        assert engine._stats["total_operations_timed"] == 1
        timer = engine._operation_timers.get("compute.sum")
        assert timer is not None
        assert timer.last_duration > 0

    def test_dashboard(self):
        engine = TimeSenseEngine()
        engine.record_operation("op1", 100.0)
        engine.record_operation("op2", 200.0)
        dash = engine.get_dashboard()
        assert "temporal_context" in dash
        assert "operations" in dash
        assert "ooda_timing" in dash
        assert "anomalies" in dash

    def test_singleton(self):
        reset_timesense()
        t1 = get_timesense()
        t2 = get_timesense()
        assert t1 is t2
        reset_timesense()

    def test_self_mirror_integration(self):
        """TimeSense feeds vectors to Self-Mirror when connected."""
        from cognitive.self_mirror import SelfMirror
        mirror = SelfMirror()
        engine = TimeSenseEngine(self_mirror=mirror)
        engine.record_operation("test.op", 150.0, "test_component")
        assert mirror._stats["total_vectors_received"] >= 1


class TestDiagnosticEngineConnection:
    """Verify diagnostic engine is properly wired in startup."""

    def test_startup_subsystems_include_diagnostic(self):
        from startup import GraceSubsystems
        subs = GraceSubsystems()
        assert hasattr(subs, 'diagnostic_engine')

    def test_startup_subsystems_include_timesense(self):
        from startup import GraceSubsystems
        subs = GraceSubsystems()
        assert hasattr(subs, 'timesense')

    def test_startup_subsystems_include_self_mirror(self):
        from startup import GraceSubsystems
        subs = GraceSubsystems()
        assert hasattr(subs, 'self_mirror')


class TestMagmaMemoryAPICoverage:
    """Verify Magma has the APIs it needs."""

    def test_magma_ingest_works(self):
        from cognitive.magma import MagmaMemory
        magma = MagmaMemory()
        result = magma.ingest("Test content for magma memory ingestion")
        assert result is not None

    def test_magma_query_works(self):
        from cognitive.magma import MagmaMemory
        magma = MagmaMemory()
        magma.ingest("Machine learning improves prediction accuracy")
        results = magma.query("predictions", limit=5)
        assert isinstance(results, list)

    def test_magma_stats(self):
        from cognitive.magma import MagmaMemory
        magma = MagmaMemory()
        stats = magma.get_stats()
        assert "graphs" in stats

    def test_magma_context_generation(self):
        from cognitive.magma import MagmaMemory
        magma = MagmaMemory()
        magma.ingest("Neural networks learn from data")
        results = magma.query("learning", limit=3)
        context = magma.get_context(results, query="learning")
        assert isinstance(context, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
