"""
Integration tests — validates the full chain end-to-end.
Tests the actual wiring, not just that modules import.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCognitivePipeline:
    """Test the cognitive pipeline chain."""

    def test_pipeline_runs_pre_generation_stages(self):
        from cognitive.pipeline import CognitivePipeline
        p = CognitivePipeline()
        ctx = p.run(
            prompt="Build a REST API",
            project_folder="test_project",
            current_file="app.py",
            skip_stages=["generate", "hallucination", "contradiction", "trust"],
        )
        assert "time_sense" in ctx.stages_passed
        assert "ooda" in ctx.stages_passed
        assert "ambiguity" in ctx.stages_passed
        assert "invariants" in ctx.stages_passed

    def test_pipeline_timesense_produces_data(self):
        from cognitive.pipeline import CognitivePipeline
        p = CognitivePipeline()
        ctx = p.run(prompt="test", skip_stages=["generate", "hallucination", "contradiction", "trust", "ooda", "ambiguity", "invariants"])
        assert ctx.time_context.get("day_of_week") is not None
        assert ctx.time_context.get("period") is not None

    def test_pipeline_ooda_classifies_prompt(self):
        from cognitive.pipeline import CognitivePipeline
        p = CognitivePipeline()
        ctx = p.run(prompt="Write a login function", skip_stages=["generate", "hallucination", "contradiction", "trust", "ambiguity", "invariants", "time_sense"])
        assert ctx.ooda_observations.get("prompt_type") == "code_generation"

    def test_pipeline_ooda_classifies_bugfix(self):
        from cognitive.pipeline import CognitivePipeline
        p = CognitivePipeline()
        ctx = p.run(prompt="Fix the bug in authentication", skip_stages=["generate", "hallucination", "contradiction", "trust", "ambiguity", "invariants", "time_sense"])
        assert ctx.ooda_observations.get("prompt_type") == "bug_fix"

    def test_pipeline_ambiguity_tracks_knowns(self):
        from cognitive.pipeline import CognitivePipeline
        p = CognitivePipeline()
        ctx = p.run(prompt="test", project_folder="my_project", current_file="main.py",
                     skip_stages=["generate", "hallucination", "contradiction", "trust", "ooda", "invariants", "time_sense"])
        assert ctx.ambiguity["known_count"] == 3
        assert ctx.ambiguity["unknown_count"] == 0

    def test_pipeline_ambiguity_tracks_unknowns(self):
        from cognitive.pipeline import CognitivePipeline
        p = CognitivePipeline()
        ctx = p.run(prompt="test", skip_stages=["generate", "hallucination", "contradiction", "trust", "ooda", "invariants", "time_sense"])
        assert ctx.ambiguity["unknown_count"] == 2

    def test_pipeline_invariants_pass_valid(self):
        from cognitive.pipeline import CognitivePipeline
        p = CognitivePipeline()
        ctx = p.run(prompt="Build something useful", skip_stages=["generate", "hallucination", "contradiction", "trust", "ooda", "time_sense"])
        assert ctx.invariant_result["valid"] is True

    def test_pipeline_invariants_fail_empty(self):
        from cognitive.pipeline import CognitivePipeline
        p = CognitivePipeline()
        ctx = p.run(prompt="ab", skip_stages=["generate", "hallucination", "contradiction", "trust", "ooda", "time_sense"])
        assert ctx.invariant_result["valid"] is False
        assert "prompt_too_short" in ctx.invariant_result["details"]


class TestGovernanceWrapper:
    """Test the governance wrapper injects rules."""

    def test_prefix_empty_when_no_rules(self):
        from llm_orchestrator.governance_wrapper import build_governance_prefix
        prefix = build_governance_prefix()
        assert isinstance(prefix, str)

    def test_wrapper_wraps_client(self):
        from llm_orchestrator.factory import get_llm_client
        from llm_orchestrator.governance_wrapper import GovernanceAwareLLM
        client = get_llm_client()
        assert isinstance(client, GovernanceAwareLLM)

    def test_persona_loads(self):
        from api.governance_rules_api import get_active_persona
        persona = get_active_persona()
        assert isinstance(persona, dict)
        assert "personal" in persona
        assert "professional" in persona


class TestTimeSense:
    """Test temporal awareness."""

    def test_now_context(self):
        from cognitive.time_sense import TimeSense
        ctx = TimeSense.now_context()
        assert ctx["day_of_week"] in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        assert ctx["period"] in ["late_night", "morning", "afternoon", "evening", "night"]
        assert isinstance(ctx["is_business_hours"], bool)

    def test_urgency_overdue(self):
        from cognitive.time_sense import TimeSense
        result = TimeSense.urgency_score("2020-01-01T00:00:00")
        assert result["label"] == "overdue"
        assert result["urgency"] == 1.0

    def test_urgency_no_deadline(self):
        from cognitive.time_sense import TimeSense
        result = TimeSense.urgency_score("")
        assert result["label"] == "no_deadline"

    def test_activity_patterns(self):
        from cognitive.time_sense import TimeSense
        result = TimeSense.activity_patterns(["2026-02-25T10:00:00", "2026-02-25T14:00:00", "2026-02-25T10:30:00"])
        assert result["total"] == 3
        assert result["peak_hour"] == "10:00"

    def test_prioritise_by_time(self):
        from cognitive.time_sense import TimeSense
        tasks = [
            {"title": "urgent", "priority": "low", "scheduled_for": "2020-01-01T00:00:00"},
            {"title": "not urgent", "priority": "critical", "deadline": "2030-01-01T00:00:00"},
        ]
        result = TimeSense.prioritise_by_time(tasks)
        assert result[0]["title"] == "urgent"


class TestGenesisTracker:
    """Test genesis key tracking."""

    def test_track_returns_none_gracefully(self):
        from api._genesis_tracker import track
        result = track(key_type="system", what="test")
        assert result is None or isinstance(result, str)

    def test_track_does_not_raise(self):
        from api._genesis_tracker import track
        track(key_type="invalid_type", what="test", who="test")


class TestDocsLibrary:
    """Test docs library helpers."""

    def test_guess_mime(self):
        from api.docs_library_api import _guess_mime
        assert _guess_mime("test.pdf") == "application/pdf"
        assert _guess_mime("test.py") == "text/x-python"
        assert _guess_mime("test.xyz") == "application/octet-stream"

    def test_safe_json_parse(self):
        from api.docs_library_api import _safe_json_parse
        assert _safe_json_parse('{"a":1}') == {"a": 1}
        assert _safe_json_parse("bad", []) == []
        assert _safe_json_parse(None, {}) == {}


class TestIntelligenceScore:
    """Test the coding agent intelligence score."""

    def test_score_is_number(self):
        from api.unified_coding_agent_api import _calculate_intelligence_score
        score = _calculate_intelligence_score()
        assert isinstance(score["score"], (int, float))
        assert 0 <= score["score"] <= 10

    def test_score_has_breakdown(self):
        from api.unified_coding_agent_api import _calculate_intelligence_score
        score = _calculate_intelligence_score()
        assert "breakdown" in score
        assert len(score["breakdown"]) > 20

    def test_available_count(self):
        from api.unified_coding_agent_api import _calculate_intelligence_score
        score = _calculate_intelligence_score()
        assert score["available"] >= 20


class TestManifest:
    """Test the system manifest."""

    def test_summary(self):
        from api.manifest_api import _get_summary
        s = _get_summary()
        assert s["endpoints"] > 100
        assert s["frontend_tabs"] == 12
        assert s["intelligence_systems"] == 28

    def test_frontend_tabs(self):
        from api.manifest_api import _get_frontend_tabs
        tabs = _get_frontend_tabs()
        assert len(tabs) == 12
        tab_ids = [t["id"] for t in tabs]
        assert "chat" in tab_ids
        assert "governance" in tab_ids
        assert "codebase" in tab_ids

    def test_intelligence_systems(self):
        from api.manifest_api import _get_intelligence_systems
        intel = _get_intelligence_systems()
        assert intel["total"] == 28
        assert intel["available"] >= 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
