"""
Grace AI Comprehensive Test Suite — 4 levels with Genesis key tracking.

Every test creates a Genesis key tagged 'genesis_test' for provenance.

Level 1: SMOKE — is it alive?
Level 2: COMPONENT — does it work correctly?
Level 3: INTEGRATION — do components work together?
Level 4: END-TO-END — full system validation
"""

import pytest
import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.update({
    "SKIP_EMBEDDING_LOAD": "true", "SKIP_QDRANT_CHECK": "true",
    "SKIP_OLLAMA_CHECK": "true", "SKIP_AUTO_INGESTION": "true",
    "DISABLE_CONTINUOUS_LEARNING": "true", "SKIP_LLM_CHECK": "true",
})


def genesis_test(name: str, result: bool, detail: str = ""):
    """Track every test via Genesis key."""
    try:
        from api._genesis_tracker import track
        track(
            key_type="system_event",
            what=f"TEST {'PASS' if result else 'FAIL'}: {name} {detail}",
            who="test_framework",
            tags=["genesis_test", "pass" if result else "fail", name],
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
#  LEVEL 1: SMOKE TESTS — is each component alive?
# ═══════════════════════════════════════════════════════════════════

class TestLevel1Smoke:
    """Can we import and instantiate every critical module?"""

    def test_app_imports(self):
        from app import app
        assert len(app.routes) > 30
        genesis_test("smoke_app_import", True, f"{len(app.routes)} routes")

    def test_brain_api_imports(self):
        from api.brain_api_v2 import call_brain, _build_directory
        d = _build_directory()
        assert len(d) == 9
        genesis_test("smoke_brain_import", True, "8 domains")

    def test_all_services_import(self):
        from core.services.chat_service import list_chats
        from core.services.files_service import stats
        from core.services.govern_service import get_persona
        from core.services.data_service import api_sources
        from core.services.tasks_service import time_sense
        from core.services.code_service import list_projects
        from core.services.system_service import get_runtime_status
        genesis_test("smoke_services_import", True, "7 services")

    def test_consensus_engine_imports(self):
        from core.engines.consensus_engine import run_consensus, get_available_models
        genesis_test("smoke_consensus_import", True)

    def test_memory_imports(self):
        from core.memory.unified_memory import UnifiedMemory, LearningExample, Episode
        genesis_test("smoke_memory_import", True)

    def test_awareness_imports(self):
        from core.awareness.self_model import SelfModel, TimeSense
        genesis_test("smoke_awareness_import", True)

    def test_resilience_imports(self):
        from core.resilience import CircuitBreaker, ErrorBoundary, GracefulDegradation
        genesis_test("smoke_resilience_import", True)

    def test_intelligence_imports(self):
        from core.intelligence import GenesisKeyMiner, AdaptiveTrust, EpisodicMiner
        genesis_test("smoke_intelligence_import", True)

    def test_security_imports(self):
        from core.security import check_rate_limit, check_sql_injection, backup_database
        genesis_test("smoke_security_import", True)

    def test_genesis_tracker_imports(self):
        from api._genesis_tracker import track
        genesis_test("smoke_genesis_tracker", True)

    def test_deep_learning_imports(self):
        from core.deep_learning import get_model, TORCH_AVAILABLE
        genesis_test("smoke_deep_learning", True, f"torch={'yes' if TORCH_AVAILABLE else 'no'}")


# ═══════════════════════════════════════════════════════════════════
#  LEVEL 2: COMPONENT TESTS — does each component work correctly?
# ═══════════════════════════════════════════════════════════════════

class TestLevel2Components:
    """Does each component produce correct output?"""

    def test_brain_returns_valid_response(self):
        from api.brain_api_v2 import call_brain
        r = call_brain("tasks", "time_sense", {})
        assert r["ok"] is True
        assert "period" in r["data"]
        genesis_test("comp_brain_valid_response", True, r["data"].get("period"))

    def test_brain_handles_invalid_action(self):
        from api.brain_api_v2 import call_brain
        r = call_brain("chat", "nonexistent_action_xyz", {})
        assert r["ok"] is False
        assert "Unknown action" in r["error"]
        genesis_test("comp_brain_invalid_action", True)

    def test_brain_all_domains_respond(self):
        from api.brain_api_v2 import call_brain, _build_directory
        d = _build_directory()
        for domain, info in d.items():
            action = info["actions"][0]
            r = call_brain(domain, action, {})
            assert "ok" in r, f"Domain {domain}/{action} missing 'ok'"
            genesis_test(f"comp_brain_{domain}", r.get("ok", False), action)

    def test_files_service_stats(self):
        from core.services.files_service import stats
        s = stats()
        assert "total_files" in s
        assert isinstance(s["total_files"], int)
        genesis_test("comp_files_stats", True, f"{s['total_files']} files")

    def test_govern_persona(self):
        from core.services.govern_service import get_persona
        p = get_persona()
        assert isinstance(p, dict)
        genesis_test("comp_govern_persona", True)

    def test_time_sense_context(self):
        from cognitive.time_sense import TimeSense
        ctx = TimeSense.get_context()
        assert "period" in ctx
        assert "is_business_hours" in ctx
        assert "hour" in ctx
        genesis_test("comp_time_sense", True, ctx["period"])

    def test_circuit_breaker_transitions(self):
        from core.resilience import CircuitBreaker
        cb = CircuitBreaker("test_comp", failure_threshold=2, reset_timeout=0)
        assert cb.state == "closed"
        for _ in range(2):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("x")))
            except Exception:
                pass
        assert cb.state == "open"
        time.sleep(0.1)
        cb.call(lambda: "recovered")
        assert cb.state == "closed"
        genesis_test("comp_circuit_breaker", True, "closed→open→closed")

    def test_error_boundary_contains(self):
        from core.resilience import ErrorBoundary
        caught = False
        with ErrorBoundary("test_comp"):
            raise ValueError("should be caught")
        caught = True
        assert caught
        genesis_test("comp_error_boundary", True)

    def test_rate_limiter(self):
        from core.security import RateLimiter
        rl = RateLimiter(requests_per_minute=3)
        assert rl.allow("test") is True
        assert rl.allow("test") is True
        assert rl.allow("test") is True
        assert rl.allow("test") is False  # 4th should fail
        genesis_test("comp_rate_limiter", True, "blocked on 4th")

    def test_sql_injection_detection(self):
        from core.security import check_sql_injection
        assert check_sql_injection("'; DROP TABLE users--") is True
        assert check_sql_injection("normal text") is False
        assert check_sql_injection("' OR '1'='1") is True
        genesis_test("comp_sql_injection", True)

    def test_adaptive_trust_update(self):
        from core.intelligence import AdaptiveTrust
        old = AdaptiveTrust.get_model_trust("kimi")
        AdaptiveTrust.record_outcome(model_id="kimi", success=True, confidence=0.9)
        new = AdaptiveTrust.get_model_trust("kimi")
        assert new >= old
        genesis_test("comp_adaptive_trust", True, f"{old:.3f}→{new:.3f}")

    def test_json_serialization(self):
        from cognitive.learning_memory import _to_json_str, _from_json_str
        original = {"key": "value", "nested": {"a": 1}}
        serialized = _to_json_str(original)
        assert isinstance(serialized, str)
        restored = _from_json_str(serialized)
        assert restored["key"] == "value"
        assert restored["nested"]["a"] == 1
        genesis_test("comp_json_serialize", True)

    def test_deep_learning_model(self):
        from core.deep_learning import get_model, TORCH_AVAILABLE
        if not TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")
        model = get_model()
        prediction = model.predict({
            "key_type": "ai_response", "what": "test prediction",
            "who": "test", "is_error": False, "tags": ["test"],
        })
        assert "success_probability" in prediction
        assert 0 <= prediction["success_probability"] <= 1
        genesis_test("comp_deep_learning", True, f"p={prediction['success_probability']:.3f}")


# ═══════════════════════════════════════════════════════════════════
#  LEVEL 3: DEEP INTEGRATION TESTS — do components work together?
# ═══════════════════════════════════════════════════════════════════

class TestLevel3Integration:
    """Do components actually work together end-to-end?"""

    def test_brain_to_service_to_data(self):
        """Brain call → service function → returns real data."""
        from api.brain_api_v2 import call_brain
        r = call_brain("files", "stats", {})
        assert r["ok"] is True
        assert "total_files" in r["data"]
        genesis_test("integ_brain_service_data", True)

    def test_cross_brain_orchestration(self):
        """Multiple brains called in sequence."""
        from api.brain_api_v2 import call_brain
        r1 = call_brain("tasks", "time_sense", {})
        r2 = call_brain("system", "runtime", {})
        assert r1["ok"] and r2["ok"]
        genesis_test("integ_cross_brain", True)

    def test_consensus_updates_trust(self):
        """Consensus result feeds back into adaptive trust."""
        from core.intelligence import AdaptiveTrust, ConsensusTrustBridge
        old_trust = AdaptiveTrust.get_model_trust("opus")
        ConsensusTrustBridge.process_consensus_result({
            "models_used": ["opus", "kimi"],
            "agreements": ["point1", "point2"],
            "disagreements": [],
            "confidence": 0.9,
            "individual_responses": [],
        })
        new_trust = AdaptiveTrust.get_model_trust("opus")
        assert new_trust >= old_trust
        genesis_test("integ_consensus_trust", True, f"{old_trust:.3f}→{new_trust:.3f}")

    def test_genesis_key_mining(self):
        """Genesis key miner can analyze keys."""
        from core.intelligence import GenesisKeyMiner
        miner = GenesisKeyMiner()
        result = miner.mine_patterns(hours=24, limit=100)
        assert "keys_analyzed" in result
        genesis_test("integ_key_mining", True, f"{result['keys_analyzed']} keys")

    def test_security_pipeline(self):
        """Rate limit → SQL check → sanitize → brain call."""
        from core.security import check_rate_limit, check_sql_injection, sanitize_string
        assert check_rate_limit("test_integ", "1.2.3.4") is True
        assert check_sql_injection("'; DROP TABLE--") is True
        clean = sanitize_string("hello\x00world")
        assert "\x00" not in clean
        genesis_test("integ_security_pipeline", True)

    def test_resilience_with_brain(self):
        """Circuit breaker wrapping a brain call."""
        from core.resilience import CircuitBreaker
        from api.brain_api_v2 import call_brain
        cb = CircuitBreaker("integ_test", failure_threshold=5)
        result = cb.call(lambda: call_brain("system", "runtime", {}))
        assert result["ok"] is True
        genesis_test("integ_resilience_brain", True)

    def test_dl_model_train_and_predict(self):
        """Train model on fake data, then predict."""
        from core.deep_learning import get_model, TORCH_AVAILABLE
        if not TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")
        model = get_model()
        fake_keys = [
            {"key_type": "ai_response", "what": f"action {i}", "who": "test",
             "when": "2026-03-01T12:00:00", "is_error": i % 5 == 0, "tags": ["test"]}
            for i in range(20)
        ]
        train_result = model.train_batch(fake_keys)
        assert train_result["status"] == "trained"
        pred = model.predict(fake_keys[-1])
        assert "success_probability" in pred
        genesis_test("integ_dl_train_predict", True, f"loss={train_result.get('loss')}")


# ═══════════════════════════════════════════════════════════════════
#  LEVEL 4: END-TO-END VALIDATION — full system flow
# ═══════════════════════════════════════════════════════════════════

class TestLevel4EndToEnd:
    """Complete system validation — everything works together."""

    def test_full_brain_directory(self):
        """All 8 domains with 87+ actions accessible."""
        from api.brain_api_v2 import _build_directory
        d = _build_directory()
        assert len(d) == 9
        total = sum(len(b["actions"]) for b in d.values())
        assert total >= 87
        genesis_test("e2e_brain_directory", True, f"{len(d)} domains, {total} actions")

    def test_full_system_status(self):
        """System runtime, health, trust all accessible via brain."""
        from api.brain_api_v2 import call_brain
        runtime = call_brain("system", "runtime", {})
        trust = call_brain("system", "trust", {})
        assert runtime["ok"]
        assert trust["ok"]
        genesis_test("e2e_system_status", True)

    def test_full_intelligence_report(self):
        """Intelligence report mines keys, trust, episodes."""
        from core.intelligence import get_intelligence_report
        report = get_intelligence_report(hours=1)
        assert "genesis_patterns" in report
        assert "trust_state" in report
        assert "episodic_analysis" in report
        genesis_test("e2e_intelligence_report", True)

    def test_full_verification_script(self):
        """The verify_system.py script passes."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/verify_system.py"],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )
        assert "ALL CHECKS PASSED" in result.stdout
        genesis_test("e2e_verification_script", True)
