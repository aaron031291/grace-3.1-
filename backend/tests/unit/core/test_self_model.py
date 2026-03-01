"""
Tests for SelfModel (TimeSense + Mirror).
"""
import pytest


class TestTimeSense:
    def test_now_context_returns_dict(self):
        from cognitive.time_sense import TimeSense
        ctx = TimeSense.now_context()
        assert isinstance(ctx, dict)
        assert "timestamp" in ctx
        assert "period" in ctx
        assert "is_business_hours" in ctx
        assert "day_of_week" in ctx

    def test_get_context_alias(self):
        from cognitive.time_sense import TimeSense
        ctx = TimeSense.get_context()
        assert isinstance(ctx, dict)
        assert "timestamp" in ctx

    def test_period_is_valid(self):
        from cognitive.time_sense import TimeSense
        ctx = TimeSense.now_context()
        valid = {"late_night", "morning", "afternoon", "evening", "night"}
        assert ctx["period"] in valid

    def test_urgency_score_returns_dict(self):
        from cognitive.time_sense import TimeSense
        result = TimeSense.urgency_score("2030-01-01T00:00:00")
        assert isinstance(result, dict)
        assert "urgency" in result
        assert "label" in result

    def test_activity_patterns_with_empty_list(self):
        from cognitive.time_sense import TimeSense
        result = TimeSense.activity_patterns([])
        assert isinstance(result, dict)


class TestSelfModel:
    def test_import_self_model(self):
        from core.awareness.self_model import SelfModel
        assert SelfModel is not None

    def test_self_model_now(self):
        from core.awareness.self_model import SelfModel
        model = SelfModel()
        ctx = model.now()
        assert "timestamp" in ctx
        assert "period" in ctx
