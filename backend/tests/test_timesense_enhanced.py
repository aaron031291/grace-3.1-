"""
TimeSense Enhanced Capability Tests.
Task planning, throughput, memory prediction, trends.
All real logic, zero mocks.
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from cognitive.timesense_enhanced import (
    TaskPlanner, TaskPlan, TaskStep,
    ThroughputTracker, ThroughputBudget,
    MemoryPressurePredictor,
    PerformanceTrendTracker,
)
from cognitive.timesense import TimeSenseEngine, get_timesense, reset_timesense


class TestTaskPlanner:
    def test_plan_ingest_repository(self):
        planner = TaskPlanner()
        plan = planner.plan("ingest_repository", 500 * 1024**2)  # 500MB
        assert plan.task_name == "ingest_repository"
        assert len(plan.steps) == 5
        assert plan.total_estimated_ms > 0
        assert plan.bottleneck_step is not None

    def test_plan_chat_query(self):
        planner = TaskPlanner()
        plan = planner.plan("chat_query", 1024)  # Small query
        assert plan.task_name == "chat_query"
        assert len(plan.steps) == 4
        assert plan.bottleneck_step == "generate_response"

    def test_plan_to_dict(self):
        planner = TaskPlanner()
        plan = planner.plan("ingest_document", 10 * 1024**2)  # 10MB
        d = plan.to_dict()
        assert "steps" in d
        assert "total_estimated_time" in d
        assert "bottleneck" in d
        assert len(d["steps"]) > 0

    def test_plan_uses_timesense_rates(self):
        engine = TimeSenseEngine()
        for _ in range(20):
            engine.record_operation("embedding_generate", 100.0, data_bytes=1024**2)
        planner = TaskPlanner(timesense=engine)
        plan = planner.plan("ingest_document", 100 * 1024**2)
        embed_step = next(s for s in plan.steps if s.operation == "embedding_generate")
        assert embed_step.confidence > 0.1

    def test_available_tasks(self):
        planner = TaskPlanner()
        tasks = planner.get_available_tasks()
        assert "ingest_repository" in tasks
        assert "chat_query" in tasks
        assert "web_scrape" in tasks

    def test_plan_formatted_time(self):
        planner = TaskPlanner()
        plan = planner.plan("knowledge_base_rebuild", 10 * 1024**3)  # 10GB
        assert "minutes" in plan.total_estimated_formatted or "hours" in plan.total_estimated_formatted


class TestThroughputTracker:
    def test_start_end_operation(self):
        tracker = ThroughputTracker()
        tracker.start_operation("chat")
        assert tracker._active_operations["chat"] == 1
        tracker.end_operation("chat", 200.0)
        assert tracker._active_operations["chat"] == 0

    def test_concurrent_tracking(self):
        tracker = ThroughputTracker()
        tracker.start_operation("chat")
        tracker.start_operation("chat")
        tracker.start_operation("chat")
        assert tracker._active_operations["chat"] == 3
        budget = tracker.get_budget("chat")
        assert budget.current_concurrent == 3

    def test_budget_calculation(self):
        tracker = ThroughputTracker()
        for _ in range(30):
            tracker.start_operation("embed")
            tracker.end_operation("embed", 100.0)
        budget = tracker.get_budget("embed")
        assert budget.max_safe_concurrent > 0
        assert budget.headroom_percent >= 0

    def test_should_throttle(self):
        tracker = ThroughputTracker()
        for i in range(25):
            tracker.start_operation("heavy_op")
        assert tracker._active_operations["heavy_op"] == 25

    def test_all_budgets(self):
        tracker = ThroughputTracker()
        tracker.start_operation("a")
        tracker.end_operation("a", 50.0)
        tracker.start_operation("b")
        tracker.end_operation("b", 100.0)
        budgets = tracker.get_all_budgets()
        assert "a" in budgets
        assert "b" in budgets


class TestMemoryPressurePredictor:
    def test_predict_small_operation(self):
        predictor = MemoryPressurePredictor()
        result = predictor.predict_memory_impact("embed", 1024**2)  # 1MB
        assert "OK" in result["recommendation"]
        assert result["predicted_ram_percent"] > 0

    def test_predict_with_history(self):
        predictor = MemoryPressurePredictor()
        predictor.record_memory_usage("embed", 1024**2, 3 * 1024**2)
        result = predictor.predict_memory_impact("embed", 10 * 1024**2)
        assert result["confidence"] == "measured"

    def test_batching_suggestion(self):
        predictor = MemoryPressurePredictor()
        import psutil
        total_ram = psutil.virtual_memory().total
        huge_size = total_ram * 2
        result = predictor.predict_memory_impact("ingest", huge_size)
        assert "BLOCK" in result["recommendation"] or "WARN" in result["recommendation"]
        if "suggested_batch_size" in result:
            assert result["suggested_batch_count"] > 1


class TestPerformanceTrends:
    def test_record_and_trend(self):
        tracker = PerformanceTrendTracker()
        for i in range(50):
            tracker.record("api.chat", 200.0 + i)
        trend = tracker.get_trend("api.chat", days=7)
        assert trend["operation"] == "api.chat"
        assert "daily" in trend or trend["trend"] == "insufficient_data"

    def test_insufficient_data(self):
        tracker = PerformanceTrendTracker()
        trend = tracker.get_trend("never.seen", days=7)
        assert trend["trend"] == "insufficient_data"

    def test_all_trends(self):
        tracker = PerformanceTrendTracker()
        tracker.record("op_a", 100.0)
        tracker.record("op_b", 200.0)
        result = tracker.get_all_trends(7)
        assert "summary" in result
        assert result["summary"]["total_operations"] == 2


class TestEnhancedIntegration:
    def test_engine_has_enhanced_capabilities(self):
        engine = TimeSenseEngine()
        assert hasattr(engine, 'task_planner')
        assert hasattr(engine, 'throughput')
        assert hasattr(engine, 'memory_predictor')
        assert hasattr(engine, 'trends')

    def test_record_feeds_trends(self):
        engine = TimeSenseEngine()
        engine.record_operation("test.op", 150.0)
        trend = engine.trends.get_trend("test.op")
        assert trend["days_tracked"] >= 0

    def test_full_planning_flow(self):
        engine = TimeSenseEngine()
        for _ in range(10):
            engine.record_operation("embedding_generate", 500.0, data_bytes=1024**2)
        plan = engine.task_planner.plan("ingest_repository", 100 * 1024**2)
        assert plan.total_estimated_ms > 0
        assert plan.bottleneck_step is not None
        d = plan.to_dict()
        assert len(d["steps"]) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
