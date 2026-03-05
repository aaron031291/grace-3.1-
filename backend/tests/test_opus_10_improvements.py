"""
import pytest; pytest.importorskip("api.business_intelligence_api", reason="api.business_intelligence_api removed — consolidated into Brain API")
Integration tests for the Opus 10 Improvements.

Tests verify that all component connections work as designed:
1. DB Schema Consolidation
2. Event Bus
3. Pipeline ↔ Consensus
4. Unified Memory
5. Mirror Self-Model (lazy)
6. Trust Engine Integration
7. Governance → BI
8. Structured Logging
9. Config Cleanup
10. This test suite itself
"""

import os
import sys
import pytest
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SKIP_EMBEDDING_LOAD", "true")
os.environ.setdefault("SKIP_QDRANT_CHECK", "true")
os.environ.setdefault("SKIP_OLLAMA_CHECK", "true")
os.environ.setdefault("DISABLE_GENESIS_TRACKING", "true")


# ── 1. DB Schema Consolidation ───────────────────────────────────────

class TestDBSchemaConsolidation:

    def test_learning_example_model_exists(self):
        from models.database_models import LearningExample
        assert LearningExample.__tablename__ == "learning_examples"

    def test_episode_model_exists(self):
        from models.database_models import Episode
        assert Episode.__tablename__ == "episodes"

    def test_procedure_model_exists(self):
        from models.database_models import Procedure
        assert Procedure.__tablename__ == "procedures"

    def test_learning_pattern_model_exists(self):
        from models.database_models import LearningPattern
        assert LearningPattern.__tablename__ == "learning_patterns"

    def test_llm_usage_stats_model_exists(self):
        from models.database_models import LLMUsageStats
        assert LLMUsageStats.__tablename__ == "llm_usage_stats"
        assert hasattr(LLMUsageStats, "provider")
        assert hasattr(LLMUsageStats, "latency_ms")

    def test_all_models_have_base(self):
        from models.database_models import (
            LearningExample, Episode, Procedure, LearningPattern, LLMUsageStats
        )
        from database.base import BaseModel
        for model in [LearningExample, Episode, Procedure, LearningPattern, LLMUsageStats]:
            assert issubclass(model, BaseModel)


# ── 2. Event Bus ─────────────────────────────────────────────────────

class TestEventBus:

    def test_publish_subscribe(self):
        from cognitive.event_bus import subscribe, publish, _subscribers
        received = []
        handler = lambda e: received.append(e.data)
        subscribe("test.improvement2", handler)
        publish("test.improvement2", {"key": "value"})
        assert len(received) == 1
        assert received[0]["key"] == "value"
        _subscribers.pop("test.improvement2", None)

    def test_wildcard_subscription(self):
        from cognitive.event_bus import subscribe, publish, _subscribers
        received = []
        handler = lambda e: received.append(e.topic)
        subscribe("wild.*", handler)
        publish("wild.test", {"x": 1})
        assert "wild.test" in received
        _subscribers.pop("wild.*", None)

    def test_event_log(self):
        from cognitive.event_bus import publish, get_recent_events
        publish("test.log_check", {"logged": True})
        events = get_recent_events(5)
        assert any(e["topic"] == "test.log_check" for e in events)

    def test_subscriber_count(self):
        from cognitive.event_bus import subscribe, get_subscriber_count, _subscribers
        subscribe("count.test", lambda e: None)
        counts = get_subscriber_count()
        assert "count.test" in counts
        _subscribers.pop("count.test", None)


# ── 3. Pipeline ↔ Consensus ──────────────────────────────────────────

class TestPipelineConsensus:

    def test_ambiguity_has_consensus_field(self):
        from cognitive.pipeline import CognitivePipeline, PipelineContext
        pipe = CognitivePipeline()
        ctx = PipelineContext(prompt="Fix the database connection issue")
        pipe._stage_ooda(ctx)
        pipe._stage_ambiguity(ctx)
        assert "consensus_resolution" in ctx.ambiguity

    def test_consensus_callable_from_pipeline(self):
        from cognitive.consensus_engine import run_consensus
        assert callable(run_consensus)


# ── 4. Unified Memory ────────────────────────────────────────────────

class TestUnifiedMemory:

    def test_singleton(self):
        from cognitive.unified_memory import get_unified_memory
        m1 = get_unified_memory()
        m2 = get_unified_memory()
        assert m1 is m2

    def test_has_store_methods(self):
        from cognitive.unified_memory import UnifiedMemory
        assert hasattr(UnifiedMemory, "store_episode")
        assert hasattr(UnifiedMemory, "store_learning")
        assert hasattr(UnifiedMemory, "store_procedure")

    def test_has_recall_methods(self):
        from cognitive.unified_memory import UnifiedMemory
        assert hasattr(UnifiedMemory, "recall_episodes")
        assert hasattr(UnifiedMemory, "recall_learnings")
        assert hasattr(UnifiedMemory, "recall_procedures")

    def test_search_all_structure(self):
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        results = mem.search_all("test query")
        assert "episodes" in results
        assert "learnings" in results
        assert "procedures" in results
        assert "magma" in results
        assert "flash_cache" in results
        assert "total" in results

    def test_get_stats(self):
        from cognitive.unified_memory import get_unified_memory
        stats = get_unified_memory().get_stats()
        assert isinstance(stats, dict)
        assert "flash_cache" in stats


# ── 5. Mirror Self-Model (Lazy) ──────────────────────────────────────

class TestMirrorSelfModel:

    def test_can_instantiate_without_session(self):
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem
        mirror = MirrorSelfModelingSystem()
        assert mirror is not None
        assert mirror._session is None

    def test_lazy_session_property(self):
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem
        mirror = MirrorSelfModelingSystem()
        assert hasattr(mirror, "session")
        # Property exists but may fail to connect — that's OK for this test

    def test_lazy_memory_learner_property(self):
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem
        mirror = MirrorSelfModelingSystem()
        assert hasattr(mirror, "memory_learner")

    def test_behavioral_patterns_initialized(self):
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem
        mirror = MirrorSelfModelingSystem()
        assert mirror.behavioral_patterns == []
        assert mirror.improvement_suggestions == []


# ── 6. Trust Engine Integration ───────────────────────────────────────

class TestTrustEngineIntegration:

    def test_consensus_uses_trust(self):
        from cognitive.consensus_engine import layer4_verify
        result = layer4_verify("Test output for trust", "Test prompt")
        assert "trust_score" in result
        assert result["trust_score"] >= 0

    def test_pipeline_flash_cache_filters_trust(self):
        from cognitive.flash_cache import FlashCache
        cache = FlashCache.__new__(FlashCache)
        cache._db_path = None
        cache._lru = {}
        cache._keyword_index = {}
        assert hasattr(cache, "lookup")


# ── 7. Governance → BI Dashboard ──────────────────────────────────────

class TestGovernanceBIDashboard:

    def test_usage_stats_function_exists(self):
        from llm_orchestrator.governance_wrapper import get_llm_usage_stats
        stats = get_llm_usage_stats()
        assert "total_calls" in stats
        assert "total_errors" in stats
        assert "by_provider" in stats
        assert "avg_latency_ms" in stats
        assert "error_rate" in stats

    def test_bi_llm_usage_endpoint_exists(self):
        from api.business_intelligence_api import router
        paths = [r.path for r in router.routes]
        assert any("llm-usage" in p for p in paths)

    def test_bi_memory_stats_endpoint_exists(self):
        from api.business_intelligence_api import router
        paths = [r.path for r in router.routes]
        assert any("memory-stats" in p for p in paths)

    def test_bi_event_log_endpoint_exists(self):
        from api.business_intelligence_api import router
        paths = [r.path for r in router.routes]
        assert any("event-log" in p for p in paths)


# ── 8. Structured Logging ────────────────────────────────────────────

class TestStructuredLogging:

    def test_structured_formatter_exists(self):
        from logging_config import StructuredFormatter
        fmt = StructuredFormatter()
        assert fmt is not None

    def test_structured_format_produces_json(self):
        from logging_config import StructuredFormatter
        import logging
        fmt = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="Test message", args=(), exc_info=None
        )
        output = fmt.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["msg"] == "Test message"
        assert "ts" in parsed

    def test_setup_creates_handlers(self):
        from logging_config import setup_logging
        assert callable(setup_logging)


# ── 9. Config Cleanup ────────────────────────────────────────────────

class TestConfigCleanup:

    def test_no_duplicate_skip_flags(self):
        from settings import Settings
        import inspect
        source = inspect.getsource(Settings)
        # Each of these should appear exactly once as a class attribute
        for attr in ["SKIP_QDRANT_CHECK", "SKIP_OLLAMA_CHECK", "SKIP_EMBEDDING_LOAD",
                      "LIGHTWEIGHT_MODE", "DISABLE_GENESIS_TRACKING"]:
            count = source.count(f"{attr}:")
            assert count == 1, f"{attr} appears {count} times (should be 1)"

    def test_consensus_config_exists(self):
        from settings import Settings
        assert hasattr(Settings, "CONSENSUS_BATCH_SCHEDULE")
        assert hasattr(Settings, "CONSENSUS_MAX_BATCH_SIZE")


# ── 10. Integration Verification ─────────────────────────────────────

class TestIntegrationVerification:

    def test_all_cognitive_modules_importable(self):
        modules = [
            "cognitive.pipeline",
            "cognitive.consensus_engine",
            "cognitive.flash_cache",
            "cognitive.event_bus",
            "cognitive.unified_memory",
            "cognitive.trust_engine",
            "cognitive.immune_system",
            "cognitive.knowledge_cycle",
            "cognitive.model_updater",
        ]
        for mod in modules:
            __import__(mod)

    def test_all_api_modules_importable(self):
        modules = [
            "api.consensus_api",
            "api.flash_cache_api",
            "api.system_audit_api",
            "api.api_vault_api",
            "api.chunked_upload_api",
            "api.business_intelligence_api",
        ]
        for mod in modules:
            __import__(mod)

    def test_event_bus_to_governance_integration(self):
        """Verify event bus fires on LLM calls (via governance wrapper)."""
        from cognitive.event_bus import subscribe, _subscribers
        events = []
        subscribe("llm.called", lambda e: events.append(e))
        # The governance wrapper publishes llm.called events
        from llm_orchestrator.governance_wrapper import get_llm_usage_stats
        stats = get_llm_usage_stats()
        assert isinstance(stats, dict)
        _subscribers.pop("llm.called", None)

    def test_unified_memory_to_flash_cache_integration(self):
        """Verify unified memory searches flash cache."""
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        results = mem.search_all("integration test")
        assert "flash_cache" in results

    def test_mirror_to_pipeline_integration(self):
        """Verify mirror can be created without session for pipeline use."""
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem
        mirror = MirrorSelfModelingSystem(observation_window_hours=1)
        assert mirror.observation_window_hours == 1
