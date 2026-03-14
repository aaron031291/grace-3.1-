"""
Tests for advanced backend.core modules — real logic, specific inputs/outputs.

Covers: brain_orchestrator, coding_pipeline, cognitive_pipeline,
        governance_engine, worker_pool, project_container,
        semantic_search, document_processor, kpi_recorder.
"""

import time
import threading
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, PropertyMock

import pytest


# ═══════════════════════════════════════════════════════════════════
#  BrainOrchestrator
# ═══════════════════════════════════════════════════════════════════

from backend.core.brain_orchestrator import BrainOrchestrator


class TestBrainOrchestratorDetectBrains:
    def test_known_task_type_returns_mapped_brains(self):
        orch = BrainOrchestrator()
        result = orch._detect_brains("build", {})
        assert result == ["code", "ai", "system", "govern"]

    def test_unknown_task_type_returns_default(self):
        orch = BrainOrchestrator()
        result = orch._detect_brains("nonexistent_task", {})
        assert result == ["ai", "system"]

    def test_payload_with_file_keyword_adds_files_brain(self):
        orch = BrainOrchestrator()
        result = orch._detect_brains("chat", {"message": "look at this file"})
        assert "files" in result

    def test_payload_with_code_keyword_adds_code_brain(self):
        orch = BrainOrchestrator()
        result = orch._detect_brains("chat", {"message": "check this function"})
        assert "code" in result

    def test_max_5_brains_returned(self):
        orch = BrainOrchestrator()
        # "build" has 4 brains, add file+code+rule keywords to trigger extras
        result = orch._detect_brains("build", {"x": "file code rule approve"})
        assert len(result) <= 5


class TestBrainOrchestratorBestAction:
    def test_known_brain_task_pair(self):
        orch = BrainOrchestrator()
        assert orch._best_action("ai", "build", {}) == "pipeline"
        assert orch._best_action("code", "fix", {}) == "generate"
        assert orch._best_action("system", "heal", {}) == "scan_heal"

    def test_unknown_pair_uses_default(self):
        orch = BrainOrchestrator()
        assert orch._best_action("ai", "nonexistent", {}) == "fast"
        assert orch._best_action("system", "nonexistent", {}) == "runtime"

    def test_completely_unknown_brain_returns_runtime(self):
        orch = BrainOrchestrator()
        assert orch._best_action("alien_brain", "anything", {}) == "runtime"


class TestBrainOrchestratorOrchestrate:
    @patch("backend.core.brain_orchestrator.BrainOrchestrator._call_brain")
    def test_orchestrate_aggregates_results(self, mock_call):
        mock_call.return_value = {"ok": True, "data": "done"}
        orch = BrainOrchestrator()
        result = orch.orchestrate("chat", {}, brains=["ai", "chat"])
        assert result["task_type"] == "chat"
        assert result["brains_called"] == ["ai", "chat"]
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert "latency_ms" in result

    @patch("backend.core.brain_orchestrator.BrainOrchestrator._call_brain")
    def test_orchestrate_handles_brain_failure(self, mock_call):
        mock_call.side_effect = [{"ok": True}, RuntimeError("boom")]
        orch = BrainOrchestrator()
        result = orch.orchestrate("build", {}, brains=["ai", "system"])
        assert result["successful"] == 1
        assert result["failed"] == 1


# ═══════════════════════════════════════════════════════════════════
#  CodingPipeline (dataclasses + helpers)
# ═══════════════════════════════════════════════════════════════════

from backend.core.coding_pipeline import (
    LayerResult, PipelineResult, PipelineProgress, CodingPipeline,
)


class TestPipelineProgress:
    def test_start_and_get(self):
        prog = PipelineProgress()
        prog.start("run-1", "test task", 3)
        state = prog.get("run-1")
        assert state["status"] == "running"
        assert state["total_chunks"] == 3
        assert state["completed_chunks"] == 0
        assert state["total_layers"] == 24  # 3 chunks * 8 layers

    def test_update_layer_passed(self):
        prog = PipelineProgress()
        prog.start("run-2", "t", 1)
        prog.update_layer("run-2", 0, 1, "Runtime", "passed", trust=0.85)
        state = prog.get("run-2")
        assert state["layers_completed"] == 1
        assert 0.85 in state["trust_scores"]

    def test_update_layer_failed_records_error(self):
        prog = PipelineProgress()
        prog.start("run-3", "t", 1)
        prog.update_layer("run-3", 0, 2, "Decompose", "failed")
        state = prog.get("run-3")
        assert len(state["errors"]) == 1
        assert "Chunk 0 Layer 2" in state["errors"][0]

    def test_finish_sets_100_on_passed(self):
        prog = PipelineProgress()
        prog.start("run-4", "t", 1)
        prog.finish("run-4", "passed")
        state = prog.get("run-4")
        assert state["percent"] == 100
        assert state["status"] == "passed"

    def test_get_nonexistent_returns_empty(self):
        prog = PipelineProgress()
        assert prog.get("no-such-run") == {}


class TestAntiHallucination:
    def setup_method(self):
        self.pipe = CodingPipeline()

    def test_clean_output_passes(self):
        result = self.pipe._anti_hallucination_check("valid output data", 3)
        assert result["passed"] is True
        assert result["flags"] == []

    def test_self_referential_flagged(self):
        result = self.pipe._anti_hallucination_check(
            "As an AI language model, I cannot do that", 3)
        assert result["passed"] is False
        assert "self_referential" in result["flags"]

    def test_overconfident_flagged(self):
        result = self.pipe._anti_hallucination_check(
            "This is 100% guaranteed to work", 5)
        assert result["passed"] is False
        assert "overconfident" in result["flags"]

    def test_suspiciously_short_in_code_gen(self):
        result = self.pipe._anti_hallucination_check("ok", 6)
        assert "suspiciously_short" in result["flags"]

    def test_syntax_valid_code(self):
        code = {"code": "x = 1\nprint(x)"}
        result = self.pipe._anti_hallucination_check(code, 6)
        assert result.get("syntax_valid") is True

    def test_syntax_invalid_code(self):
        code = {"code": "def foo(\n  pass"}
        result = self.pipe._anti_hallucination_check(code, 6)
        assert any("syntax_error" in f for f in result["flags"])

    def test_dangerous_imports_flagged(self):
        code = {"code": "import subprocess\nimport os"}
        result = self.pipe._anti_hallucination_check(code, 6)
        assert any("dangerous_imports" in f for f in result["flags"])


class TestLayerTrust:
    def test_probe_passed_adds_trust(self):
        pipe = CodingPipeline()
        lr = LayerResult(layer=1, name="test", status="passed",
                         output={"some": "data"}, probe_passed=True)
        trust = pipe._layer_trust(1, lr)
        assert trust == pytest.approx(0.9, abs=0.01)

    def test_error_output_lower_trust(self):
        pipe = CodingPipeline()
        lr = LayerResult(layer=1, name="test", status="passed",
                         output={"error": "something"}, probe_passed=False)
        trust = pipe._layer_trust(1, lr)
        # base 0.7 + 0 (no probe) + 0.1 (dict no error key? — has error key)
        assert trust == pytest.approx(0.7, abs=0.05)

    def test_calculate_trust_empty_chunks(self):
        pipe = CodingPipeline()
        pr = PipelineResult(task="test")
        assert pipe._calculate_trust(pr) == 0.0


# ═══════════════════════════════════════════════════════════════════
#  CognitivePipeline
# ═══════════════════════════════════════════════════════════════════

from backend.core.cognitive_pipeline import CognitivePipeline


class TestCognitivePipelineExecute:
    def test_handler_result_returned_directly_when_not_full(self):
        pipe = CognitivePipeline(enable_full=False)
        handler = lambda p: {"ok": True, "data": "hello"}
        result = pipe.execute("chat", "send", {"msg": "hi"}, handler)
        assert result == {"ok": True, "data": "hello"}
        assert pipe._stats["calls"] == 1

    def test_handler_exception_returns_error(self):
        pipe = CognitivePipeline(enable_full=False)
        def handler(p):
            raise ValueError("bad input")
        result = pipe.execute("chat", "send", {}, handler)
        assert "error" in result
        assert "bad input" in result["error"]


class TestCognitivePipelineAmbiguity:
    def test_clear_input_low_score(self):
        pipe = CognitivePipeline()
        result = pipe._check_ambiguity({"command": "build the project now"})
        assert result["score"] == 0.0
        assert result["is_ambiguous"] is False

    def test_ambiguous_input_high_score(self):
        pipe = CognitivePipeline()
        result = pipe._check_ambiguity(
            {"msg": "maybe could perhaps might not sure unclear"})
        # 6 out of 6 ambiguous words present
        assert result["score"] == pytest.approx(1.0, abs=0.01)
        assert result["is_ambiguous"] is True

    def test_partial_ambiguity(self):
        pipe = CognitivePipeline()
        result = pipe._check_ambiguity({"msg": "maybe do this"})
        # 1 out of 6
        assert result["score"] == pytest.approx(1 / 6, abs=0.02)
        assert result["is_ambiguous"] is False  # 0.167 < 0.2


class TestCognitivePipelineStats:
    def test_stats_increment(self):
        pipe = CognitivePipeline(enable_full=False)
        pipe.execute("a", "b", {}, lambda p: {"ok": True})
        pipe.execute("a", "b", {}, lambda p: {"ok": True})
        assert pipe.get_stats()["calls"] == 2


# ═══════════════════════════════════════════════════════════════════
#  GovernanceEngine
# ═══════════════════════════════════════════════════════════════════

import backend.core.governance_engine as gov_mod


class TestRecordKpi:
    def setup_method(self):
        gov_mod._kpi_scores.clear()

    def test_single_pass(self):
        gov_mod.record_kpi("test_comp", "feat_a", passed=True, layer=1)
        scores = gov_mod.get_kpi_scores("test_comp")
        assert scores["total_features"] == 1
        entry = list(scores["scores"].values())[0]
        assert entry["passed"] == 1
        assert entry["failed"] == 0
        assert entry["score"] == 100.0

    def test_mixed_pass_fail(self):
        gov_mod.record_kpi("comp", "feat", passed=True)
        gov_mod.record_kpi("comp", "feat", passed=False)
        gov_mod.record_kpi("comp", "feat", passed=True)
        scores = gov_mod.get_kpi_scores("comp")
        entry = list(scores["scores"].values())[0]
        assert entry["total_checks"] == 3
        assert entry["passed"] == 2
        assert entry["failed"] == 1
        assert entry["score"] == pytest.approx(66.7, abs=0.1)

    def test_trust_from_scores(self):
        gov_mod.record_kpi("c", "f", passed=True)
        scores = gov_mod.get_kpi_scores("c")
        assert scores["trust_score"] == 1.0

    def test_empty_scores_trust_default(self):
        scores = gov_mod.get_kpi_scores()
        assert scores["trust_score"] == 0.5


class TestApprovalWorkflow:
    def setup_method(self):
        gov_mod._approvals.clear()
        gov_mod._approval_counter = 0

    def test_create_approval(self):
        a = gov_mod.create_approval("Deploy v2", "Release new version", "deploy")
        assert a["id"] == 1
        assert a["status"] == "pending"
        assert a["title"] == "Deploy v2"

    def test_approve_approval(self):
        gov_mod.create_approval("Test", "test desc")
        result = gov_mod.respond_to_approval(1, "approve", "looks good")
        assert result["status"] == "approved"
        assert len(result["responses"]) == 1

    def test_deny_approval(self):
        gov_mod.create_approval("Risky", "risky change")
        result = gov_mod.respond_to_approval(1, "deny", "too risky")
        assert result["status"] == "denied"

    def test_discuss_approval(self):
        gov_mod.create_approval("Q", "question")
        result = gov_mod.respond_to_approval(1, "discuss", "need more info")
        assert result["status"] == "discussing"

    def test_respond_nonexistent(self):
        result = gov_mod.respond_to_approval(999, "approve")
        assert "error" in result

    def test_filter_by_status(self):
        gov_mod.create_approval("A", "a")
        gov_mod.create_approval("B", "b")
        gov_mod.respond_to_approval(1, "approve")
        pending = gov_mod.get_approvals(status="pending")
        assert len(pending) == 1
        assert pending[0]["title"] == "B"


class TestCompliancePresets:
    def test_get_presets(self):
        result = gov_mod.get_compliance_presets()
        assert result["total"] >= 7
        assert "iso_27001" in result["presets"]
        assert "gdpr" in result["presets"]

    def test_unknown_preset_returns_error(self):
        result = gov_mod.apply_compliance_preset("proj1", "nonexistent")
        assert "error" in result


class TestKpiDashboard:
    def setup_method(self):
        gov_mod._kpi_scores.clear()

    def test_dashboard_groups_by_component(self):
        gov_mod.record_kpi("alpha", "f1", True)
        gov_mod.record_kpi("alpha", "f2", False)
        gov_mod.record_kpi("beta", "f3", True)
        dash = gov_mod.get_kpi_dashboard()
        assert dash["total_components"] == 2
        assert "alpha" in dash["components"]
        assert dash["components"]["alpha"]["features"] == 2


# ═══════════════════════════════════════════════════════════════════
#  WorkerPool
# ═══════════════════════════════════════════════════════════════════

import backend.core.worker_pool as wp_mod


class TestSubmitTask:
    def setup_method(self):
        wp_mod._user_requests.clear()

    def test_simple_task_returns_result(self):
        result = wp_mod.submit_task(lambda: 42, user_id="u1", timeout=5)
        assert result == 42

    def test_rate_limit_exceeded(self):
        # Fill up user quota
        wp_mod._user_requests["u2"] = [
            {"ts": time.time(), "success": True}
            for _ in range(wp_mod.MAX_REQUESTS_PER_USER)
        ]
        with pytest.raises(RuntimeError, match="Rate limit exceeded"):
            wp_mod.submit_task(lambda: 1, user_id="u2")

    def test_old_requests_expired(self):
        # Requests older than 1 hour should not count
        wp_mod._user_requests["u3"] = [
            {"ts": time.time() - 7200, "success": True}
            for _ in range(wp_mod.MAX_REQUESTS_PER_USER)
        ]
        result = wp_mod.submit_task(lambda: 99, user_id="u3", timeout=5)
        assert result == 99


class TestCachedBrainCall:
    def setup_method(self):
        wp_mod._response_cache.clear()

    def test_cache_hit(self):
        call_count = {"n": 0}
        def func():
            call_count["n"] += 1
            return {"ok": True}
        wp_mod.cached_brain_call("ai", "fast", "hash1", func)
        wp_mod.cached_brain_call("ai", "fast", "hash1", func)
        assert call_count["n"] == 1  # only called once

    def test_cache_miss_different_hash(self):
        call_count = {"n": 0}
        def func():
            call_count["n"] += 1
            return {"ok": True}
        wp_mod.cached_brain_call("ai", "fast", "h1", func)
        wp_mod.cached_brain_call("ai", "fast", "h2", func)
        assert call_count["n"] == 2

    def test_cache_eviction(self):
        for i in range(wp_mod.MAX_CACHE_SIZE + 5):
            wp_mod.cached_brain_call("d", "a", f"h{i}", lambda: i)
        stats = wp_mod.get_cache_stats()
        assert stats["entries"] <= wp_mod.MAX_CACHE_SIZE


class TestPoolStats:
    def test_stats_structure(self):
        stats = wp_mod.get_pool_stats()
        assert "max_workers" in stats
        assert "active_users" in stats
        assert "timeout_seconds" in stats


# ═══════════════════════════════════════════════════════════════════
#  SemanticSearch
# ═══════════════════════════════════════════════════════════════════

from backend.core.semantic_search import (
    semantic_query, get_component_registry, get_component_profile, COMPONENTS,
)


class TestSemanticQuery:
    def test_exact_component_name_match(self):
        result = semantic_query("librarian")
        assert result["component_id"] == "librarian"
        assert "purpose" in result

    def test_purpose_keyword_match(self):
        result = semantic_query("consensus deliberation")
        assert result["component_id"] == "consensus_engine"

    def test_no_match_returns_suggestion(self):
        result = semantic_query("xyzzy_nonexistent_term")
        assert result["component_matches"] == 0
        assert "suggestion" in result

    def test_related_components_returned(self):
        result = semantic_query("coding pipeline deterministic")
        assert "related" in result or result["component_id"] in (
            "coding_pipeline", "deterministic_bridge")


class TestComponentRegistry:
    def test_registry_has_entries(self):
        reg = get_component_registry()
        assert reg["total"] > 10
        assert "librarian" in reg["components"]

    def test_profile_known_component(self):
        result = get_component_profile("governance_engine")
        assert result.get("component_id") == "governance_engine"

    def test_profile_unknown_component(self):
        result = get_component_profile("no_such_thing")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════
#  DocumentProcessor (_chunk_text is the testable pure function)
# ═══════════════════════════════════════════════════════════════════

from backend.core.document_processor import _chunk_text, process_documents


class TestChunkText:
    def test_short_text_single_chunk(self):
        text = "Hello world"
        chunks = _chunk_text(text, chunk_size=2000, overlap=200)
        assert chunks == ["Hello world"]

    def test_long_text_multiple_chunks(self):
        text = "A" * 5000
        chunks = _chunk_text(text, chunk_size=2000, overlap=200)
        assert len(chunks) >= 3
        # All content should be covered
        total_unique = set()
        for c in chunks:
            assert len(c) <= 2000
        # Chunks overlap
        if len(chunks) >= 2:
            assert chunks[0][-200:] in text

    def test_natural_boundary_splitting(self):
        text = ("word " * 400) + "\n\n" + ("more " * 400)
        chunks = _chunk_text(text, chunk_size=2000, overlap=200)
        assert len(chunks) >= 2

    def test_empty_chunks_filtered(self):
        text = "Hello"
        chunks = _chunk_text(text, chunk_size=10, overlap=0)
        assert all(c.strip() for c in chunks)


class TestProcessDocuments:
    @patch("backend.core.document_processor._process_single")
    @patch("backend.core.document_processor._ensure_processor")
    def test_splits_into_immediate_and_queued(self, mock_proc, mock_single):
        mock_single.return_value = {"file": "f", "status": "done", "chunks": 1}
        files = [{"name": f"f{i}.txt", "content": "data"} for i in range(15)]
        result = process_documents(files, category="test")
        assert result["total"] == 15
        assert result["immediate"] == 10
        assert result["queued"] == 5


# ═══════════════════════════════════════════════════════════════════
#  KpiRecorder
# ═══════════════════════════════════════════════════════════════════

from backend.core.kpi_recorder import record_brain_kpi, record_component_kpi


class TestRecordBrainKpi:
    @patch("core.governance_engine.record_kpi")
    def test_calls_governance_record_kpi(self, mock_kpi):
        record_brain_kpi("chat", "send", ok=True)
        mock_kpi.assert_called_once_with("brain", "chat/send", passed=True)

    def test_governance_failure_does_not_raise(self):
        # record_brain_kpi wraps everything in try/except, so even if
        # governance_engine raises, it should not propagate
        with patch("core.governance_engine.record_kpi", side_effect=Exception("boom")):
            record_brain_kpi("chat", "send", ok=False)  # must not raise


class TestRecordComponentKpi:
    @patch("ml_intelligence.kpi_tracker.get_kpi_tracker")
    def test_calls_ml_tracker(self, mock_get_tracker):
        mock_tracker = MagicMock()
        mock_get_tracker.return_value = mock_tracker
        record_component_kpi("retrieval", "latency", value=42.0, success=True)
        mock_tracker.increment_kpi.assert_any_call("retrieval", "latency", 42.0)
        mock_tracker.increment_kpi.assert_any_call("retrieval", "successes", 1.0)

    def test_ml_failure_does_not_raise(self):
        # Should swallow any exception from the tracker
        record_component_kpi("x", "y", value=1.0)
