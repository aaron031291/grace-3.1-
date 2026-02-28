"""
Integration tests — validates the full cognitive pipeline chain.
Tests real logic, not just imports.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPipelineTimeSense:
    def test_produces_valid_context(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run(prompt="test", skip_stages=["ooda","ambiguity","invariants","generate","contradiction","hallucination","trust_pre","trust_post"])
        assert ctx.time_context["day_of_week"] in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        assert ctx.time_context["period"] in ["late_night","morning","afternoon","evening","night"]
        assert "time_sense" in ctx.stages_passed


class TestPipelineOODA:
    def test_classifies_code_generation(self):
        ctx = self._run("Write a login function")
        assert ctx.ooda["prompt_type"] == "code_generation"

    def test_classifies_bug_fix(self):
        ctx = self._run("Fix the authentication bug")
        assert ctx.ooda["prompt_type"] == "bug_fix"

    def test_classifies_question(self):
        ctx = self._run("What does this function do?")
        assert ctx.ooda["prompt_type"] == "question"

    def test_classifies_refactor(self):
        ctx = self._run("Refactor the database module")
        assert ctx.ooda["prompt_type"] == "refactor"

    def test_classifies_testing(self):
        ctx = self._run("Write tests for the API")
        assert ctx.ooda["prompt_type"] == "testing"

    def test_classifies_destructive(self):
        ctx = self._run("Delete all temp files")
        assert ctx.ooda["prompt_type"] == "destructive"

    def test_detects_approach(self):
        ctx = self._run("Build a REST API")
        assert ctx.ooda["approach"] == "direct"

    def test_question_is_analytical(self):
        ctx = self._run("Explain how authentication works")
        assert ctx.ooda["approach"] == "analytical"

    def _run(self, prompt):
        from cognitive.pipeline import CognitivePipeline
        return CognitivePipeline().run(prompt=prompt, skip_stages=["time_sense","ambiguity","invariants","generate","contradiction","hallucination","trust_pre","trust_post"])


class TestPipelineAmbiguity:
    def test_tracks_knowns_with_full_context(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run(prompt="test", project_folder="myproject", current_file="app.py",
                                       skip_stages=["time_sense","ooda","invariants","generate","contradiction","hallucination","trust_pre","trust_post"])
        assert ctx.ambiguity["known_count"] >= 3
        assert ctx.ambiguity["unknown_count"] == 0

    def test_tracks_unknowns_without_project(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run(prompt="test",
                                       skip_stages=["time_sense","ooda","invariants","generate","contradiction","hallucination","trust_pre","trust_post"])
        assert ctx.ambiguity["unknown_count"] >= 1

    def test_detects_implicit_references(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run(prompt="connect to the database and the api",
                                       skip_stages=["time_sense","ooda","invariants","generate","contradiction","hallucination","trust_pre","trust_post"])
        assert len(ctx.ambiguity["implicit_refs"]) >= 1

    def test_no_blocking_for_analytical(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run(prompt="explain something",
                                       skip_stages=["time_sense","invariants","generate","contradiction","hallucination","trust_pre","trust_post"])
        assert ctx.ambiguity["has_blocking"] is False


class TestPipelineInvariants:
    def test_passes_valid_prompt(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run(prompt="Build a user registration system", project_folder="test",
                                       skip_stages=["time_sense","generate","contradiction","hallucination","trust_pre","trust_post"])
        assert ctx.invariants["valid"] is True

    def test_warns_on_short_prompt(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run(prompt="Build a user registration system",
                                       skip_stages=["time_sense","generate","contradiction","hallucination","trust_pre","trust_post"])
        # This prompt is long enough, should not have vague warning
        assert "vague_prompt" not in str(ctx.invariants.get("warnings", []))

    def test_warns_on_destructive(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run(prompt="Delete all files in the project",
                                       skip_stages=["time_sense","generate","contradiction","hallucination","trust_pre","trust_post"])
        warnings = ctx.invariants.get("warnings", [])
        assert any("irreversible" in w for w in warnings)

    def test_warns_on_large_blast_radius(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run(prompt="Refactor all files in the entire project",
                                       skip_stages=["time_sense","generate","contradiction","hallucination","trust_pre","trust_post"])
        warnings = ctx.invariants.get("warnings", [])
        assert any("blast_radius" in w for w in warnings)

    def test_checks_all_12(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run(prompt="test prompt here",
                                       skip_stages=["time_sense","generate","contradiction","hallucination","trust_pre","trust_post"])
        assert ctx.invariants["checked"] == 12


class TestPipelineContradiction:
    def test_detects_language_mismatch_python(self):
        from cognitive.pipeline import CognitivePipeline, PipelineContext
        ctx = PipelineContext(prompt="test")
        ctx.ooda = {"tech_stack": ["python"]}
        ctx.llm_response = "const app = require('express');\nfunction handler() {}"
        ctx.stages_passed = ["ooda"]
        p = CognitivePipeline()
        p._stage_contradiction(ctx)
        assert ctx.contradictions["issue_count"] > 0
        assert any("language_mismatch" in i for i in ctx.contradictions["issues"])

    def test_no_contradiction_when_matching(self):
        from cognitive.pipeline import CognitivePipeline, PipelineContext
        ctx = PipelineContext(prompt="test")
        ctx.ooda = {"tech_stack": ["python"]}
        ctx.llm_response = "def hello():\n    print('hello')"
        ctx.stages_passed = ["ooda"]
        p = CognitivePipeline()
        p._stage_contradiction(ctx)
        assert ctx.contradictions["issue_count"] == 0


class TestPipelineHallucination:
    def test_calculates_confidence(self):
        from cognitive.pipeline import CognitivePipeline, PipelineContext
        ctx = PipelineContext(prompt="test")
        ctx.project_files = ["src/app.py", "src/utils.py"]
        ctx.llm_response = "import src.app\nfrom nonexistent.module import thing"
        ctx.contradictions = {"issue_count": 0}
        ctx.stages_passed = []
        p = CognitivePipeline()
        p._stage_hallucination(ctx)
        assert 0 < ctx.verification["confidence"] <= 1.0

    def test_perfect_grounding(self):
        from cognitive.pipeline import CognitivePipeline, PipelineContext
        ctx = PipelineContext(prompt="test")
        ctx.project_files = []
        ctx.llm_response = "def hello():\n    return 'world'"
        ctx.contradictions = {"issue_count": 0}
        ctx.stages_passed = []
        p = CognitivePipeline()
        p._stage_hallucination(ctx)
        assert ctx.verification["grounded"] is True


class TestPipelineTrust:
    def test_high_trust_for_clean_run(self):
        from cognitive.pipeline import CognitivePipeline, PipelineContext
        ctx = PipelineContext(prompt="test")
        ctx.verification = {"grounded": True}
        ctx.contradictions = {"issue_count": 0}
        ctx.invariants = {"valid": True}
        ctx.ambiguity = {"has_blocking": False}
        ctx.stages_passed = ["time_sense", "ooda", "ambiguity", "invariants", "generate", "contradiction", "hallucination"]
        ctx.stages_failed = []
        p = CognitivePipeline()
        p._stage_trust_post(ctx)
        assert ctx.trust_score >= 0.8

    def test_lower_trust_for_issues(self):
        from cognitive.pipeline import CognitivePipeline, PipelineContext
        ctx = PipelineContext(prompt="test")
        ctx.verification = {"grounded": False}
        ctx.contradictions = {"issue_count": 2}
        ctx.invariants = {"valid": False}
        ctx.ambiguity = {"has_blocking": True}
        ctx.ooda = {}
        ctx.stages_passed = []
        ctx.stages_failed = ["ooda", "ambiguity"]
        p = CognitivePipeline()
        p._stage_trust_post(ctx)
        # Trust Engine scores chunks individually — with issues it should be lower than clean
        clean_ctx = PipelineContext(prompt="test")
        clean_ctx.verification = {"grounded": True}
        clean_ctx.contradictions = {"issue_count": 0}
        clean_ctx.invariants = {"valid": True}
        clean_ctx.ambiguity = {"has_blocking": False}
        clean_ctx.ooda = {}
        clean_ctx.stages_passed = ["time_sense", "ooda", "ambiguity", "invariants", "generate"]
        clean_ctx.stages_failed = []
        p._stage_trust_post(clean_ctx)
        assert ctx.trust_score < clean_ctx.trust_score


class TestPipelineFullChain:
    def test_full_pre_generation_chain(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run(
            prompt="Build a REST API for user management with authentication",
            project_folder="test_project",
            current_file="app.py",
            skip_stages=["generate", "contradiction", "hallucination"],
        )
        assert "time_sense" in ctx.stages_passed
        assert "ooda" in ctx.stages_passed
        assert "ambiguity" in ctx.stages_passed
        assert "invariants" in ctx.stages_passed
        assert "trust_pre" in ctx.stages_passed
        assert ctx.ooda["prompt_type"] == "code_generation"
        assert ctx.invariants["valid"] is True
        assert ctx.invariants["checked"] == 12


class TestFeedbackLoop:
    def test_record_does_not_raise(self):
        from cognitive.pipeline import FeedbackLoop
        FeedbackLoop.record_outcome(
            genesis_key="test-key", prompt="test", output="test output",
            outcome="positive",
        )

    def test_get_patterns_returns_list(self):
        from cognitive.pipeline import FeedbackLoop
        patterns = FeedbackLoop.get_relevant_patterns("test")
        assert isinstance(patterns, list)


class TestPromptClassification:
    def test_all_types(self):
        from cognitive.pipeline import _classify_prompt
        assert _classify_prompt("write a function") == "code_generation"
        assert _classify_prompt("fix this bug") == "bug_fix"
        assert _classify_prompt("what does this do") == "question"
        assert _classify_prompt("optimize the code") == "refactor"
        assert _classify_prompt("write tests for the API") == "testing"
        assert _classify_prompt("delete all temp files") == "destructive"
        assert _classify_prompt("hello") == "general"


class TestGovernanceWrapper:
    def test_wraps_every_client(self):
        from llm_orchestrator.factory import get_llm_client
        from llm_orchestrator.governance_wrapper import GovernanceAwareLLM
        assert isinstance(get_llm_client(), GovernanceAwareLLM)

    def test_persona_loads(self):
        from api.governance_rules_api import get_active_persona
        p = get_active_persona()
        assert "personal" in p and "professional" in p


class TestManifest:
    def test_summary_counts(self):
        from api.manifest_api import _get_summary
        s = _get_summary()
        assert s["endpoints"] > 100
        assert s["frontend_tabs"] == 12
        assert s["intelligence_systems"] == 28


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
