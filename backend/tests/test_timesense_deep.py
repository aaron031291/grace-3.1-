"""
TimeSense Deep Capability Tests.
Learning curves, persistence, predictive scaling, scheduling, dependencies.
All real logic, zero mocks.
"""

import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from cognitive.timesense_deep import (
    LearningCurveTracker, TimeSensePersistence,
    PredictiveScaler, TimeAwareScheduler,
    OperationDependencyGraph,
)
from cognitive.timesense import TimeSenseEngine, reset_timesense


class TestLearningCurves:
    def test_record_and_curve(self):
        tracker = LearningCurveTracker()
        for i in range(200):
            tracker.record("embed", 300.0 - i)
        curve = tracker.get_curve("embed")
        assert curve["phase"] in ("still_improving", "plateaued", "degrading")
        assert curve["total_executions"] == 200
        assert curve["first_avg_ms"] > curve["current_avg_ms"]

    def test_insufficient_data(self):
        tracker = LearningCurveTracker()
        tracker.record("test", 100.0)
        curve = tracker.get_curve("test")
        assert curve["status"] == "insufficient_data"

    def test_plateau_detection(self):
        tracker = LearningCurveTracker()
        for _ in range(100):
            tracker.record("stable_op", 100.0)
        curve = tracker.get_curve("stable_op")
        assert curve["phase"] == "plateaued"

    def test_degradation_detection(self):
        tracker = LearningCurveTracker()
        for i in range(100):
            tracker.record("slow_op", 100.0 + i * 3)
        curve = tracker.get_curve("slow_op")
        assert curve["phase"] == "degrading"

    def test_all_curves(self):
        tracker = LearningCurveTracker()
        for i in range(20):
            tracker.record("op_a", 200.0 - i)
            tracker.record("op_b", 100.0)
        result = tracker.get_all_curves()
        assert result["summary"]["total_operations"] == 2

    def test_serialization(self):
        tracker = LearningCurveTracker()
        for i in range(20):
            tracker.record("test_op", 100.0 + i)
        data = tracker.to_json()
        assert "test_op" in data

        tracker2 = LearningCurveTracker()
        tracker2.from_json(data)
        curve = tracker2.get_curve("test_op")
        assert curve["total_executions"] == 20


class TestPersistence:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = TimeSensePersistence(data_dir=tmpdir)
            engine = TimeSenseEngine()
            for _ in range(10):
                engine.record_operation("test.op", 150.0, data_bytes=1024)

            assert persistence.save(engine)
            assert os.path.exists(os.path.join(tmpdir, "timesense_state.json"))

            engine2 = TimeSenseEngine()
            assert persistence.load(engine2)

    def test_load_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = TimeSensePersistence(data_dir=tmpdir)
            engine = TimeSenseEngine()
            assert not persistence.load(engine)

    def test_saved_file_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = TimeSensePersistence(data_dir=tmpdir)
            engine = TimeSenseEngine()
            engine.record_operation("a", 100.0, data_bytes=500)
            persistence.save(engine)

            with open(os.path.join(tmpdir, "timesense_state.json")) as f:
                data = json.load(f)
            assert "saved_at" in data
            assert "stats" in data
            assert "learning_curves" in data


class TestPredictiveScaler:
    def test_predict_with_no_data(self):
        scaler = PredictiveScaler()
        result = scaler.predict_disk_exhaustion(100 * 1024**3)
        assert result["prediction"] == "insufficient_data"

    def test_predict_with_ingestion_data(self):
        from datetime import datetime, timedelta
        scaler = PredictiveScaler()
        now = datetime.utcnow()
        for i in range(10):
            scaler._ingestion_history.append(
                (now - timedelta(hours=i), 1024**3)
            )
        result = scaler.predict_disk_exhaustion(50 * 1024**3)
        assert result["prediction"] in ("estimated", "no_growth")
        if result["prediction"] == "estimated":
            assert "days_until_full" in result
            assert "exhaustion_date" in result

    def test_scaling_recommendation(self):
        scaler = PredictiveScaler()
        assert "CRITICAL" in scaler._scaling_recommendation(2)
        assert "WARNING" in scaler._scaling_recommendation(10)
        assert "HEALTHY" in scaler._scaling_recommendation(60)


class TestTimeAwareScheduler:
    def test_default_window(self):
        scheduler = TimeAwareScheduler()
        result = scheduler.get_optimal_window(2)
        assert "window" in result
        assert result["confidence"] == "default"

    def test_measured_window(self):
        scheduler = TimeAwareScheduler()
        for hour in range(24):
            load = 0.8 if 9 <= hour <= 17 else 0.1
            for _ in range(5):
                scheduler.record_load(hour, load)
        result = scheduler.get_optimal_window(3)
        assert "window" in result
        start_hour = int(result["window"].split(":")[0])
        assert start_hour < 9 or start_hour > 17

    def test_is_good_time_now(self):
        scheduler = TimeAwareScheduler()
        result = scheduler.is_good_time_now()
        assert "is_good_time" in result
        assert isinstance(result["is_good_time"], bool)


class TestOperationDependencyGraph:
    def test_known_dependencies(self):
        graph = OperationDependencyGraph()
        deps = graph.get_dependencies("embedding_generate")
        assert "text_chunk" in deps

    def test_no_dependencies(self):
        graph = OperationDependencyGraph()
        deps = graph.get_dependencies("file_scan")
        assert deps == []

    def test_execution_order(self):
        graph = OperationDependencyGraph()
        ops = ["file_scan", "document_parse", "text_chunk", "embedding_generate", "vector_store"]
        result = graph.get_execution_order(ops)
        assert result["total_levels"] >= 1
        assert "critical_path" in result
        assert result["execution_levels"][0]["operations"] == ["file_scan"]

    def test_parallelization_detection(self):
        graph = OperationDependencyGraph()
        ops = ["file_scan", "query_embed", "http_fetch"]
        result = graph.get_execution_order(ops)
        assert result["can_parallelize"] is True
        assert result["max_parallelism"] >= 2

    def test_critical_path(self):
        graph = OperationDependencyGraph()
        ops = ["file_scan", "document_parse", "text_chunk", "embedding_generate", "vector_store"]
        result = graph.get_execution_order(ops)
        assert len(result["critical_path"]) >= 3

    def test_custom_dependency(self):
        graph = OperationDependencyGraph()
        graph.add_dependency("custom_op", "file_scan")
        deps = graph.get_dependencies("custom_op")
        assert "file_scan" in deps


class TestDeepIntegration:
    def test_engine_has_deep_capabilities(self):
        engine = TimeSenseEngine()
        assert hasattr(engine, 'learning_curves')
        assert hasattr(engine, 'persistence')
        assert hasattr(engine, 'scaler')
        assert hasattr(engine, 'scheduler')
        assert hasattr(engine, 'dep_graph')

    def test_record_feeds_learning_curves(self):
        engine = TimeSenseEngine()
        for i in range(20):
            engine.record_operation("test.learn", 200.0 - i * 5)
        curve = engine.learning_curves.get_curve("test.learn")
        assert curve["total_executions"] == 20

    def test_record_feeds_scheduler(self):
        engine = TimeSenseEngine()
        engine.record_operation("test.op", 500.0)
        hour = __import__('datetime').datetime.utcnow().hour
        loads = engine.scheduler._hourly_load.get(hour, [])
        assert len(loads) >= 1

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = TimeSenseEngine()
            engine.persistence = __import__('cognitive.timesense_deep', fromlist=['TimeSensePersistence']).TimeSensePersistence(data_dir=tmpdir)
            for i in range(15):
                engine.record_operation("roundtrip.op", 100.0 + i)
            assert engine.save_state()
            engine2 = TimeSenseEngine()
            engine2.persistence = __import__('cognitive.timesense_deep', fromlist=['TimeSensePersistence']).TimeSensePersistence(data_dir=tmpdir)
            assert engine2.load_state()


class TestSelfMirrorPersistence:
    def test_save_and_load(self):
        from cognitive.self_mirror import SelfMirror, TelemetryVector
        mirror = SelfMirror()
        for _ in range(10):
            mirror.receive_vector(TelemetryVector(T=100.0, M=500.0, P=0.3, component="test", task_domain="test"))
        assert mirror.save_state()
        mirror2 = SelfMirror()
        assert mirror2.load_state()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
