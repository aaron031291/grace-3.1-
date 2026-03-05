"""
import pytest; pytest.importorskip("api.governance_rules_api", reason="api.governance_rules_api removed — consolidated into Brain API")
10 Industry Standard Tests — Different Perspectives

These tests validate Grace from the perspective of:
1. Security Engineer — governance enforcement
2. DevOps Engineer — self-healing and monitoring
3. Data Engineer — data integrity and provenance
4. ML Engineer — trust scoring and learning
5. QA Engineer — pipeline correctness
6. Product Manager — feature completeness
7. Architect — system integration
8. Compliance Officer — rule enforcement
9. SRE — reliability and recovery
10. End User — functional correctness
"""

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════════════════════════════
# TEST 1: SECURITY ENGINEER — Governance cannot be bypassed
# ═══════════════════════════════════════════════════════════════════════

class TestSecurityEngineer:
    """Every LLM call MUST go through the governance wrapper. No bypass possible."""

    def test_factory_always_wraps(self):
        from llm_orchestrator.factory import get_llm_client
        from llm_orchestrator.governance_wrapper import GovernanceAwareLLM
        for provider in ["ollama", "openai", "kimi"]:
            client = get_llm_client(provider=provider)
            assert isinstance(client, GovernanceAwareLLM), f"{provider} client not wrapped"

    def test_kimi_client_wrapped(self):
        from llm_orchestrator.factory import get_kimi_client
        from llm_orchestrator.governance_wrapper import GovernanceAwareLLM
        assert isinstance(get_kimi_client(), GovernanceAwareLLM)

    def test_raw_client_available_for_internal(self):
        from llm_orchestrator.factory import get_raw_client
        from llm_orchestrator.governance_wrapper import GovernanceAwareLLM
        raw = get_raw_client()
        assert not isinstance(raw, GovernanceAwareLLM), "Raw client should NOT be wrapped"

    def test_governance_prefix_is_string(self):
        from llm_orchestrator.governance_wrapper import build_governance_prefix
        prefix = build_governance_prefix()
        assert isinstance(prefix, str)

    def test_persona_has_both_fields(self):
        from api.governance_rules_api import get_active_persona
        p = get_active_persona()
        assert "personal" in p
        assert "professional" in p


# ═══════════════════════════════════════════════════════════════════════
# TEST 2: DEVOPS ENGINEER — Self-healing detects and recovers
# ═══════════════════════════════════════════════════════════════════════

class TestDevOpsEngineer:
    """Immune system must detect failures, attempt recovery, and log everything."""

    def test_scan_detects_down_services(self):
        from cognitive.immune_system import GraceImmuneSystem
        immune = GraceImmuneSystem()
        result = immune.scan()
        anomalies = result["anomalies"]
        down = [a for a in anomalies if a["type"] == "service_down"]
        assert len(down) > 0, "Should detect at least one service down"

    def test_scan_identifies_root_cause(self):
        from cognitive.immune_system import GraceImmuneSystem
        immune = GraceImmuneSystem()
        result = immune.scan()
        if len(result["anomalies"]) >= 2:
            assert result.get("root_cause") is not None, "Should identify root cause with 2+ anomalies"

    def test_scan_adapts_interval(self):
        from cognitive.immune_system import GraceImmuneSystem
        immune = GraceImmuneSystem()
        result = immune.scan()
        if len(result["anomalies"]) >= 3:
            assert result["next_scan_interval"] <= 30, "Crisis should reduce interval to <=30s"

    def test_healing_creates_playbook_entry(self):
        from cognitive.immune_system import GraceImmuneSystem
        immune = GraceImmuneSystem()
        immune.scan()
        playbook = immune.get_playbook()
        assert len(playbook) > 0, "Healing should create playbook entries"

    def test_baselines_established(self):
        from cognitive.immune_system import GraceImmuneSystem
        immune = GraceImmuneSystem()
        immune.scan()
        status = immune.get_status()
        assert len(status["baselines"]) > 0, "Should establish baselines for healthy components"


# ═══════════════════════════════════════════════════════════════════════
# TEST 3: DATA ENGINEER — Provenance and data integrity
# ═══════════════════════════════════════════════════════════════════════

class TestDataEngineer:
    """Genesis keys must track every operation with complete metadata."""

    def test_tracker_never_raises(self):
        from api._genesis_tracker import track
        result = track(key_type="invalid", what="test", who="test", is_error=True)
        # Should never raise, even with invalid input

    def test_tracker_accepts_all_fields(self):
        from api._genesis_tracker import track
        track(
            key_type="system", what="full field test", who="test_user",
            where="/test", why="testing", how="pytest",
            file_path="/test/file.py", input_data={"a": 1},
            output_data={"b": 2}, context={"c": 3},
            tags=["test"], is_error=False, code_before="old", code_after="new",
        )

    def test_realtime_engine_fires_instantly(self):
        from genesis.realtime import GenesisRealtimeEngine
        engine = GenesisRealtimeEngine()
        received = []
        engine.watch("__all__", lambda e: received.append(e))
        engine.on_key_created("system", "instant test")
        assert len(received) == 1, "Event should fire immediately, not batched"
        assert received[0]["what"] == "instant test"

    def test_realtime_alert_on_error_spike(self):
        from genesis.realtime import GenesisRealtimeEngine
        engine = GenesisRealtimeEngine()
        for i in range(3):
            engine.on_key_created("error", f"Error {i}", is_error=True)
        alerts = engine.get_alerts()
        assert len(alerts) > 0, "3 errors should trigger an alert"
        assert alerts[0]["type"] == "error_spike"

    def test_streaming_detects_acceleration(self):
        from genesis.realtime import GenesisRealtimeEngine
        engine = GenesisRealtimeEngine()
        # All errors in second half of window
        engine.on_key_created("system", "normal 1")
        engine.on_key_created("error", "err 1", is_error=True)
        engine.on_key_created("error", "err 2", is_error=True)
        engine.on_key_created("error", "err 3", is_error=True)
        stats = engine.get_stream_stats(60)
        assert stats["trend"] == "accelerating"


# ═══════════════════════════════════════════════════════════════════════
# TEST 4: ML ENGINEER — Trust scoring is mathematically sound
# ═══════════════════════════════════════════════════════════════════════

class TestMLEngineer:
    """Trust scores must be bounded, monotonic with quality, and composable."""

    def test_trust_bounded_0_100(self):
        from cognitive.trust_engine import TrustEngine
        engine = TrustEngine()
        for source in ["deterministic", "internal", "llm", "unknown"]:
            comp = engine.score_output(f"test_{source}", "Test", "test content", source=source)
            assert 0 <= comp.trust_score <= 100, f"{source}: {comp.trust_score} out of bounds"

    def test_deterministic_higher_than_unknown(self):
        from cognitive.trust_engine import TrustEngine
        engine = TrustEngine()
        det = engine.score_output("d", "D", "SELECT * FROM users", source="deterministic")
        unk = engine.score_output("u", "U", "random data", source="unknown")
        assert det.trust_score > unk.trust_score

    def test_verification_levels_correct(self):
        from cognitive.trust_engine import TrustEngine
        engine = TrustEngine()
        assert engine.verify_output("x", "y", 85)["verification_level"] == "internal_only"
        assert engine.verify_output("x", "y", 65)["verification_level"] == "knowledge_base"
        assert engine.verify_output("x", "y", 45)["verification_level"] == "full_verification"
        assert engine.verify_output("x", "y", 35)["verification_level"] == "human_required"

    def test_system_trust_aggregates(self):
        from cognitive.trust_engine import TrustEngine
        engine = TrustEngine()
        engine.score_output("a", "A", "good code", source="deterministic")
        engine.score_output("b", "B", "bad data", source="unknown")
        sys = engine.get_system_trust()
        assert sys["component_count"] == 2
        assert 0 < sys["system_trust"] < 100

    def test_intelligence_score_above_8(self):
        from api.unified_coding_agent_api import _calculate_intelligence_score
        score = _calculate_intelligence_score()
        assert score["score"] >= 8.0, f"Intelligence score {score['score']} too low"
        assert score["available"] >= 20, f"Only {score['available']} systems available"


# ═══════════════════════════════════════════════════════════════════════
# TEST 5: QA ENGINEER — Pipeline stages execute in correct order
# ═══════════════════════════════════════════════════════════════════════

class TestQAEngineer:
    """Pipeline must execute stages sequentially, each feeding the next."""

    def test_all_pre_generation_stages_pass(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run("Build a login form", project_folder="test",
            skip_stages=["generate", "contradiction", "hallucination"])
        required = ["time_sense", "ooda", "ambiguity", "invariants", "trust_pre"]
        for stage in required:
            assert stage in ctx.stages_passed, f"Stage {stage} did not pass"

    def test_stages_execute_in_order(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run("test prompt", project_folder="test",
            skip_stages=["generate", "contradiction", "hallucination"])
        order = ["time_sense", "ooda", "ambiguity", "invariants", "trust_pre", "trust_post"]
        passed = [s for s in ctx.stages_passed if s in order]
        assert passed == sorted(passed, key=order.index), "Stages out of order"

    def test_prompt_classification_complete(self):
        from cognitive.pipeline import _classify_prompt
        assert _classify_prompt("write a function") == "code_generation"
        assert _classify_prompt("fix the bug") == "bug_fix"
        assert _classify_prompt("what does this do") == "question"
        assert _classify_prompt("optimize the code") == "refactor"
        assert _classify_prompt("write tests for API") == "testing"
        assert _classify_prompt("delete all files") == "destructive"
        assert _classify_prompt("hello") == "general"

    def test_invariants_check_all_12(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run("test", project_folder="test",
            skip_stages=["time_sense", "generate", "contradiction", "hallucination", "trust_pre", "trust_post"])
        assert ctx.invariants["checked"] == 12

    def test_ambiguity_detects_implicit_references(self):
        from cognitive.pipeline import CognitivePipeline
        ctx = CognitivePipeline().run("connect to the database and the server",
            skip_stages=["time_sense", "ooda", "invariants", "generate", "contradiction", "hallucination", "trust_pre", "trust_post"])
        assert len(ctx.ambiguity["implicit_refs"]) >= 1


# ═══════════════════════════════════════════════════════════════════════
# TEST 6: PRODUCT MANAGER — All features exist and are accessible
# ═══════════════════════════════════════════════════════════════════════

class TestProductManager:
    """Every feature promised must exist and be reachable."""

    def test_12_frontend_tabs_exist(self):
        tab_dir = "/workspace/frontend/src/components"
        tabs = [f for f in os.listdir(tab_dir) if f.endswith("Tab.jsx")]
        assert len(tabs) == 12, f"Expected 12 tabs, found {len(tabs)}: {tabs}"

    def test_v1_api_has_10_resources(self):
        v1_dir = "/workspace/backend/api/v1"
        resources = [f for f in os.listdir(v1_dir) if f.endswith(".py") and f != "__init__.py" and f != "router.py"]
        assert len(resources) == 10, f"Expected 10 resources, found {len(resources)}: {resources}"

    def test_manifest_reports_correct_counts(self):
        from api.manifest_api import _get_summary
        s = _get_summary()
        assert s["frontend_tabs"] == 12
        assert s["intelligence_systems"] == 28
        assert s["endpoints"] > 200

    def test_frontend_builds_clean(self):
        assert os.path.exists("/workspace/frontend/dist/index.html"), "Frontend not built"

    def test_kimi_has_8_capabilities(self):
        from llm_orchestrator.kimi_enhanced import KimiEnhanced
        methods = [m for m in dir(KimiEnhanced()) if not m.startswith("_")]
        assert len(methods) >= 8, f"Kimi has {len(methods)} methods, expected 8+"


# ═══════════════════════════════════════════════════════════════════════
# TEST 7: ARCHITECT — Systems integrate correctly
# ═══════════════════════════════════════════════════════════════════════

class TestArchitect:
    """Core systems must be properly integrated, not just coexisting."""

    def test_magma_available(self):
        from cognitive.magma_bridge import is_available
        assert is_available(), "Magma should be available"

    def test_magma_has_4_graphs(self):
        from cognitive.magma_bridge import get_stats
        stats = get_stats()
        assert "graphs" in stats
        for graph in ["semantic", "temporal", "causal", "entity"]:
            assert graph in stats["graphs"], f"Missing graph: {graph}"

    def test_pipeline_queries_magma(self):
        content = open("/workspace/backend/cognitive/pipeline.py").read()
        assert "magma_bridge" in content, "Pipeline should import magma_bridge"
        assert "query_context" in content, "Pipeline should query Magma context"

    def test_immune_writes_to_magma(self):
        content = open("/workspace/backend/cognitive/immune_system.py").read()
        assert "magma_bridge" in content, "Immune system should import magma_bridge"
        assert "store_pattern" in content, "Immune should store patterns in Magma"

    def test_healing_coordinator_exists(self):
        from cognitive.healing_coordinator import HealingCoordinator
        h = HealingCoordinator()
        assert hasattr(h, "resolve"), "Coordinator must have resolve method"


# ═══════════════════════════════════════════════════════════════════════
# TEST 8: COMPLIANCE OFFICER — Rules are enforced everywhere
# ═══════════════════════════════════════════════════════════════════════

class TestComplianceOfficer:
    """Governance rules must be enforced in every LLM call path."""

    def test_agent_rules_api_exists(self):
        from api.agent_rules_api import get_agent_rules_context
        ctx = get_agent_rules_context()
        assert isinstance(ctx, str)

    def test_governance_rules_api_exists(self):
        from api.governance_rules_api import get_active_persona
        assert get_active_persona() is not None

    def test_governance_wrapper_reads_rules(self):
        from llm_orchestrator.governance_wrapper import build_governance_prefix
        prefix = build_governance_prefix()
        assert isinstance(prefix, str)

    def test_pipeline_injects_agent_rules(self):
        content = open("/workspace/backend/cognitive/pipeline.py").read()
        assert "agent_rules_api" in content, "Pipeline should inject agent rules"
        assert "get_agent_rules_context" in content

    def test_mcp_orchestrator_injects_governance(self):
        content = open("/workspace/backend/grace_mcp/orchestrator.py").read()
        assert "governance_wrapper" in content or "governance_prefix" in content or "build_governance_prefix" in content


# ═══════════════════════════════════════════════════════════════════════
# TEST 9: SRE — System is reliable and recoverable
# ═══════════════════════════════════════════════════════════════════════

class TestSRE:
    """System must handle failures gracefully and recover autonomously."""

    def test_self_healer_reconnects_database(self):
        from cognitive.self_healing import SelfHealer
        healer = SelfHealer()
        result = healer._heal_database()
        assert isinstance(result, bool)

    def test_immune_system_heals_database(self):
        from cognitive.immune_system import GraceImmuneSystem
        immune = GraceImmuneSystem()
        result = immune.scan()
        db_heals = [h for h in result.get("healing_actions", []) if h.get("component") == "database"]
        if db_heals:
            assert db_heals[0].get("success") is True, "Database healing should succeed"

    def test_genesis_tracker_never_crashes(self):
        from api._genesis_tracker import track
        for _ in range(10):
            track(key_type="error", what="stress test", is_error=True)

    def test_realtime_engine_handles_volume(self):
        from genesis.realtime import GenesisRealtimeEngine
        engine = GenesisRealtimeEngine()
        for i in range(100):
            engine.on_key_created("system", f"Event {i}")
        assert engine.get_stats()["total_events"] == 100

    def test_trust_engine_handles_rapid_scoring(self):
        from cognitive.trust_engine import TrustEngine
        engine = TrustEngine()
        for i in range(20):
            engine.score_output(f"comp_{i}", f"Component {i}", f"Output {i}", source="llm")
        sys = engine.get_system_trust()
        assert sys["component_count"] == 20


# ═══════════════════════════════════════════════════════════════════════
# TEST 10: END USER — Core features work correctly
# ═══════════════════════════════════════════════════════════════════════

class TestEndUser:
    """Core user-facing features must produce correct, useful results."""

    def test_timesense_knows_current_day(self):
        from cognitive.time_sense import TimeSense
        ctx = TimeSense.now_context()
        assert ctx["day_of_week"] in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        assert ctx["period"] in ["late_night", "morning", "afternoon", "evening", "night"]
        assert isinstance(ctx["is_business_hours"], bool)

    def test_timesense_urgency_scoring(self):
        from cognitive.time_sense import TimeSense
        overdue = TimeSense.urgency_score("2020-01-01T00:00:00")
        assert overdue["label"] == "overdue"
        assert overdue["urgency"] == 1.0

        no_deadline = TimeSense.urgency_score("")
        assert no_deadline["label"] == "no_deadline"

    def test_docs_library_helpers_work(self):
        from api.docs_library_api import _guess_mime, _safe_json_parse
        assert _guess_mime("report.pdf") == "application/pdf"
        assert _guess_mime("script.py") == "text/x-python"
        assert _safe_json_parse('{"a":1}') == {"a": 1}
        assert _safe_json_parse("bad", []) == []

    def test_file_suggestion_works(self):
        from api.librarian_autonomous_api import _suggest_directory
        assert _suggest_directory("main.py", "", ".py") == "code/python"
        assert _suggest_directory("README.md", "", ".md") == "documentation"
        assert _suggest_directory("data.csv", "", ".csv") == "data/csv"

    def test_feedback_loop_doesnt_crash(self):
        from cognitive.pipeline import FeedbackLoop
        FeedbackLoop.record_outcome("test-key", "test prompt", "test output", "positive")
        patterns = FeedbackLoop.get_relevant_patterns("test")
        assert isinstance(patterns, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
