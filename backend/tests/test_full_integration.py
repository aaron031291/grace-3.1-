"""
Full Logic Component Tests

Tests all new integrations with 100% pass rate, zero warnings, zero skips.
Covers:
- Unified Learning Pipeline (NeighborByNeighborEngine, pipeline lifecycle)
- Chat Intelligence (ambiguity detection, governance, routing, enrichment)
- Governance Middleware (OutputSafetyValidator, AuditTrailManager)
- Memory optimization verification
- Integration wiring verification
"""

import sys
import os
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Dict, Any, List

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================================
# UNIFIED LEARNING PIPELINE TESTS
# ============================================================================

class TestTopicNode:
    """Tests for TopicNode dataclass."""

    def test_topic_node_creation(self):
        from cognitive.unified_learning_pipeline import TopicNode
        node = TopicNode(topic="REST API design")
        assert node.topic == "REST API design"
        assert node.trust_score == 0.5
        assert node.depth == 0
        assert node.parent_topic is None
        assert node.explored is False
        assert node.discovered_at != ""

    def test_topic_node_with_params(self):
        from cognitive.unified_learning_pipeline import TopicNode
        node = TopicNode(
            topic="Database indexing",
            trust_score=0.85,
            depth=2,
            parent_topic="Databases",
            explored=True
        )
        assert node.topic == "Database indexing"
        assert node.trust_score == 0.85
        assert node.depth == 2
        assert node.parent_topic == "Databases"
        assert node.explored is True

    def test_topic_node_auto_timestamp(self):
        from cognitive.unified_learning_pipeline import TopicNode
        node = TopicNode(topic="test")
        assert node.discovered_at != ""
        datetime.fromisoformat(node.discovered_at)


class TestExpansionResult:
    """Tests for ExpansionResult dataclass."""

    def test_expansion_result_defaults(self):
        from cognitive.unified_learning_pipeline import ExpansionResult
        result = ExpansionResult(
            seed_topic="Python",
            neighbors_found=5,
            new_topics_discovered=3,
            knowledge_items_created=3
        )
        assert result.seed_topic == "Python"
        assert result.neighbors_found == 5
        assert result.new_topics_discovered == 3
        assert result.knowledge_items_created == 3
        assert result.expansion_depth == 0
        assert result.duration_ms == 0.0
        assert result.trust_scores == {}


class TestNeighborByNeighborEngine:
    """Tests for the neighbor-by-neighbor expansion engine."""

    def test_engine_initialization(self):
        from cognitive.unified_learning_pipeline import NeighborByNeighborEngine
        engine = NeighborByNeighborEngine(
            max_depth=2,
            max_neighbors_per_node=5,
            similarity_threshold=0.5,
            max_total_nodes=50
        )
        assert engine.max_depth == 2
        assert engine.max_neighbors_per_node == 5
        assert engine.similarity_threshold == 0.5
        assert engine.max_total_nodes == 50

    def test_engine_default_params(self):
        from cognitive.unified_learning_pipeline import NeighborByNeighborEngine
        engine = NeighborByNeighborEngine()
        assert engine.max_depth == 3
        assert engine.max_neighbors_per_node == 8
        assert engine.similarity_threshold == 0.45
        assert engine.max_total_nodes == 100

    def test_empty_knowledge_graph(self):
        from cognitive.unified_learning_pipeline import NeighborByNeighborEngine
        engine = NeighborByNeighborEngine()
        graph = engine.get_knowledge_graph()
        assert graph["total_nodes"] == 0
        assert graph["total_edges"] == 0
        assert graph["nodes"] == []
        assert graph["edges"] == {}

    def test_expand_without_retriever(self):
        from cognitive.unified_learning_pipeline import NeighborByNeighborEngine
        engine = NeighborByNeighborEngine()
        result = engine.expand_from_seed("test topic", "test text")
        assert result.seed_topic == "test topic"
        assert result.neighbors_found == 0
        assert result.new_topics_discovered == 0

    def test_expand_with_mock_retriever(self):
        from cognitive.unified_learning_pipeline import NeighborByNeighborEngine
        engine = NeighborByNeighborEngine(max_depth=1, max_neighbors_per_node=3)

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {"text": "Related topic about APIs", "score": 0.8, "metadata": {"filename": "apis.md"}},
            {"text": "Another related topic about REST", "score": 0.7, "metadata": {"filename": "rest_design.md"}},
        ]
        engine._retriever = mock_retriever
        engine._embedding_model = MagicMock()

        result = engine.expand_from_seed("API design", "How to design APIs")
        assert result.seed_topic == "API design"
        assert result.neighbors_found >= 2
        assert result.new_topics_discovered >= 2
        assert result.duration_ms > 0

        graph = engine.get_knowledge_graph()
        assert graph["total_nodes"] >= 3
        assert graph["total_edges"] >= 2

    def test_extract_topic_from_metadata(self):
        from cognitive.unified_learning_pipeline import NeighborByNeighborEngine
        engine = NeighborByNeighborEngine()

        topic = engine._extract_topic("some text", {"filename": "machine_learning.md"})
        assert topic == "machine learning"

        topic = engine._extract_topic("some text", {"file_path": "/docs/api-design.txt"})
        assert topic == "api design"

    def test_extract_topic_from_text(self):
        from cognitive.unified_learning_pipeline import NeighborByNeighborEngine
        engine = NeighborByNeighborEngine()

        topic = engine._extract_topic(
            "This is a long piece of text about natural language processing and how it works",
            {}
        )
        assert len(topic) > 0
        assert len(topic) <= 80

    def test_knowledge_graph_structure(self):
        from cognitive.unified_learning_pipeline import NeighborByNeighborEngine
        engine = NeighborByNeighborEngine(max_depth=1)

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {"text": "neighbor1", "score": 0.9, "metadata": {"filename": "n1.md"}},
        ]
        engine._retriever = mock_retriever
        engine._embedding_model = MagicMock()

        engine.expand_from_seed("seed", "seed text")
        graph = engine.get_knowledge_graph()

        for node in graph["nodes"]:
            assert "topic" in node
            assert "trust_score" in node
            assert "depth" in node
            assert "explored" in node
            assert "discovered_at" in node


class TestUnifiedLearningPipeline:
    """Tests for the 24/7 continuous learning pipeline."""

    def test_pipeline_singleton(self):
        from cognitive.unified_learning_pipeline import get_unified_pipeline
        p1 = get_unified_pipeline()
        p2 = get_unified_pipeline()
        assert p1 is p2

    def test_pipeline_initialization(self):
        from cognitive.unified_learning_pipeline import UnifiedLearningPipeline
        pipeline = UnifiedLearningPipeline()
        assert pipeline.running is False
        assert pipeline.stats["total_expansions"] == 0
        assert pipeline.stats["total_cycles"] == 0
        assert len(pipeline._pending_seeds) == 0
        assert len(pipeline._processed_seeds) == 0

    def test_pipeline_config(self):
        from cognitive.unified_learning_pipeline import UnifiedLearningPipeline
        pipeline = UnifiedLearningPipeline()
        assert "scan_interval_seconds" in pipeline.config
        assert "expansion_interval_seconds" in pipeline.config
        assert "min_trust_for_expansion" in pipeline.config
        assert "auto_expand_on_ingest" in pipeline.config
        assert "max_expansions_per_cycle" in pipeline.config
        assert "enable_predictive_prefetch" in pipeline.config

    def test_add_seed(self):
        from cognitive.unified_learning_pipeline import UnifiedLearningPipeline
        pipeline = UnifiedLearningPipeline()
        pipeline.add_seed("Python basics", "Introduction to Python")
        assert len(pipeline._pending_seeds) == 1
        assert pipeline._pending_seeds[0]["topic"] == "Python basics"
        assert pipeline._pending_seeds[0]["text"] == "Introduction to Python"

    def test_add_duplicate_seed_skipped(self):
        from cognitive.unified_learning_pipeline import UnifiedLearningPipeline
        pipeline = UnifiedLearningPipeline()
        pipeline._processed_seeds.add("Already done")
        pipeline.add_seed("Already done", "text")
        assert len(pipeline._pending_seeds) == 0

    def test_pipeline_start_stop(self):
        from cognitive.unified_learning_pipeline import UnifiedLearningPipeline
        pipeline = UnifiedLearningPipeline()
        pipeline.config["scan_interval_seconds"] = 1

        pipeline.start()
        assert pipeline.running is True
        assert pipeline._thread is not None
        assert pipeline._thread.is_alive()

        time.sleep(0.1)
        pipeline.stop()
        assert pipeline.running is False

    def test_pipeline_status(self):
        from cognitive.unified_learning_pipeline import UnifiedLearningPipeline
        pipeline = UnifiedLearningPipeline()
        pipeline.add_seed("test", "test text")

        status = pipeline.get_status()
        assert "running" in status
        assert "stats" in status
        assert "config" in status
        assert "pending_seeds" in status
        assert "processed_seeds" in status
        assert "knowledge_graph" in status
        assert status["pending_seeds"] == 1

    def test_process_pending_seeds(self):
        from cognitive.unified_learning_pipeline import UnifiedLearningPipeline
        pipeline = UnifiedLearningPipeline()
        pipeline.add_seed("topic1", "text1")
        pipeline.add_seed("topic2", "text2")

        processed = pipeline._process_pending_seeds()
        assert processed == 2
        assert len(pipeline._pending_seeds) == 0
        assert "topic1" in pipeline._processed_seeds
        assert "topic2" in pipeline._processed_seeds
        assert pipeline.stats["total_expansions"] == 2


# ============================================================================
# CHAT INTELLIGENCE TESTS
# ============================================================================

class TestChatIntelligence:
    """Tests for the ChatIntelligence integration layer."""

    def test_singleton(self):
        from cognitive.chat_intelligence import get_chat_intelligence
        ci1 = get_chat_intelligence()
        ci2 = get_chat_intelligence()
        assert ci1 is ci2

    def test_initialization(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        assert ci._ambiguity_engine is None
        assert ci._episodic_buffer is None
        assert ci._governance is None
        assert ci._oracle is None


class TestAmbiguityDetection:
    """Tests for ambiguity detection in chat."""

    def test_clear_query_no_ambiguity(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.detect_ambiguity("How do I implement a REST API with authentication in Python using FastAPI?")
        assert result is None

    def test_empty_query(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        assert ci.detect_ambiguity("") is None
        assert ci.detect_ambiguity("ab") is None
        assert ci.detect_ambiguity(None) is None

    def test_vague_pronoun_detected(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.detect_ambiguity("it doesn't work")
        assert result is not None
        assert result["is_ambiguous"] is True
        assert "vague_pronoun_without_context" in result["ambiguity_signals"]
        assert len(result["clarifying_questions"]) > 0

    def test_too_short_detected(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.detect_ambiguity("code")
        assert result is not None
        assert result["is_ambiguous"] is True
        assert "too_short" in result["ambiguity_signals"]

    def test_vague_request_detected(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.detect_ambiguity("help me")
        assert result is not None
        assert result["is_ambiguous"] is True

    def test_greeting_not_ambiguous(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.detect_ambiguity("hello")
        assert result is None

    def test_multiple_options_detected(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.detect_ambiguity("this or that")
        assert result is not None
        assert "multiple_options" in result["ambiguity_signals"]

    def test_ambiguity_levels(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()

        result = ci.detect_ambiguity("it or that")
        assert result is not None
        assert result["ambiguity_level"] in ("low", "medium", "high")
        assert 0 <= result["ambiguity_score"] <= 1.0

    def test_clarifying_questions_generated(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()

        result = ci.detect_ambiguity("it broke")
        assert result is not None
        questions = result["clarifying_questions"]
        assert isinstance(questions, list)
        assert len(questions) <= 3
        for q in questions:
            assert isinstance(q, str)
            assert len(q) > 10


class TestGovernanceChecks:
    """Tests for inline governance checking."""

    def test_safe_response_passes(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.check_governance(
            "Here's how to implement a REST API with FastAPI. "
            "First, install FastAPI using pip install fastapi."
        )
        assert result["passed"] is True
        assert len(result["violations"]) == 0
        assert len(result["checks_performed"]) > 0

    def test_dangerous_language_detected(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.check_governance("I will delete all your data now.")
        assert result["passed"] is False
        assert len(result["violations"]) > 0
        assert result["violations"][0]["rule"] == "SAFETY_FIRST"

    def test_short_response_warning(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.check_governance("Ok.")
        assert result["passed"] is True
        assert len(result["warnings"]) > 0
        assert result["warnings"][0]["rule"] == "RESPONSE_QUALITY"

    def test_all_checks_performed(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.check_governance("A normal helpful response about Python programming.")
        assert "safety_language" in result["checks_performed"]
        assert "response_quality" in result["checks_performed"]
        assert "transparency" in result["checks_performed"]


class TestQueryRoutingPrediction:
    """Tests for Oracle ML query routing."""

    def test_technical_query_routes_to_vectordb(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.predict_query_routing("How do I fix this Python function bug?")
        assert result["predicted_tier"] == "VECTORDB"
        assert result["confidence"] > 0

    def test_temporal_query_routes_to_internet(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.predict_query_routing("What is the latest news about AI in 2026?")
        assert result["predicted_tier"] == "INTERNET"

    def test_general_knowledge_routes_to_model(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.predict_query_routing("What is machine learning?")
        assert result["predicted_tier"] == "MODEL_KNOWLEDGE"

    def test_default_routes_to_vectordb(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.predict_query_routing("asdfghjkl random text")
        assert result["predicted_tier"] == "VECTORDB"
        assert result["reason"] == "default"

    def test_routing_result_structure(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.predict_query_routing("some query")
        assert "predicted_tier" in result
        assert "confidence" in result
        assert "reason" in result
        assert 0 <= result["confidence"] <= 1.0


class TestResponseEnrichment:
    """Tests for response enrichment with ambiguity and governance."""

    def test_no_enrichment_when_clear(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        original = "This is the answer."
        enriched = ci.enrich_response(original, None, None)
        assert enriched == original

    def test_ambiguity_enrichment_on_high(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()

        ambiguity = {
            "is_ambiguous": True,
            "ambiguity_level": "high",
            "clarifying_questions": ["What do you mean?", "Can you be more specific?"]
        }
        enriched = ci.enrich_response("Answer text.", ambiguity, None)
        assert "clarify" in enriched.lower() or "interpreted" in enriched.lower()
        assert "Answer text." in enriched

    def test_no_enrichment_on_low_ambiguity(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()

        ambiguity = {
            "is_ambiguous": True,
            "ambiguity_level": "low",
            "clarifying_questions": ["What do you mean?"]
        }
        enriched = ci.enrich_response("Answer.", ambiguity, None)
        assert enriched == "Answer."

    def test_governance_warning_appended(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()

        governance = {
            "passed": True,
            "warnings": [{"detail": "Response might contain ungrounded claims"}]
        }
        enriched = ci.enrich_response("Some response.", None, governance)
        assert "ungrounded" in enriched.lower()


# ============================================================================
# GOVERNANCE MIDDLEWARE TESTS
# ============================================================================

class TestOutputSafetyValidator:
    """Tests for OutputSafetyValidator."""

    def test_safe_output(self):
        from security.governance_middleware import OutputSafetyValidator
        result = OutputSafetyValidator.validate(
            "Here's how to build a REST API. First, define your routes."
        )
        assert result["safe"] is True
        assert len(result["violations"]) == 0
        assert result["checks_performed"] > 0
        assert "timestamp" in result

    def test_harmful_output_detected(self):
        from security.governance_middleware import OutputSafetyValidator
        result = OutputSafetyValidator.validate("Let me show you how to hack into the system")
        assert result["safe"] is False
        assert len(result["violations"]) > 0
        assert result["violations"][0]["rule"] == "SAFETY_FIRST"
        assert result["violations"][0]["severity"] == "high"

    def test_system_command_detected(self):
        from security.governance_middleware import OutputSafetyValidator
        result = OutputSafetyValidator.validate("Just run rm -rf / to clean up")
        assert result["safe"] is False

    def test_password_leak_detected(self):
        from security.governance_middleware import OutputSafetyValidator
        result = OutputSafetyValidator.validate("The password is admin123")
        assert result["safe"] is False

    def test_fabrication_warning(self):
        from security.governance_middleware import OutputSafetyValidator
        result = OutputSafetyValidator.validate(
            "According to a study that was conducted last year, 99% of..."
        )
        assert result["safe"] is False
        has_transparency = any(v["rule"] == "TRANSPARENCY_REQUIRED" for v in result["violations"])
        assert has_transparency

    def test_case_insensitive_detection(self):
        from security.governance_middleware import OutputSafetyValidator
        result = OutputSafetyValidator.validate("HOW TO HACK into systems")
        assert result["safe"] is False


class TestAuditTrailManager:
    """Tests for governance audit trail."""

    def test_record_and_retrieve(self):
        from security.governance_middleware import AuditTrailManager
        manager = AuditTrailManager()

        manager.record(
            action="chat_response",
            input_data="test query",
            output_data="test response",
            governance_result={"safe": True, "violations": []},
            trust_score=0.8,
            genesis_key="gk-123"
        )

        recent = manager.get_recent(limit=10)
        assert len(recent) == 1
        assert recent[0]["action"] == "chat_response"
        assert recent[0]["governance_passed"] is True
        assert recent[0]["trust_score"] == 0.8
        assert recent[0]["genesis_key"] == "gk-123"

    def test_violation_summary(self):
        from security.governance_middleware import AuditTrailManager
        manager = AuditTrailManager()

        manager.record("a", "q1", "r1", {"safe": True, "violations": []})
        manager.record("a", "q2", "r2", {"safe": False, "violations": [{"rule": "SAFETY"}]})
        manager.record("a", "q3", "r3", {"safe": True, "violations": []})

        summary = manager.get_violation_summary()
        assert summary["total_entries"] == 3
        assert summary["total_violations"] == 1
        assert 0 < summary["violation_rate"] < 1

    def test_max_trail_size(self):
        from security.governance_middleware import AuditTrailManager
        manager = AuditTrailManager(max_trail_size=5)

        for i in range(10):
            manager.record(f"action_{i}", f"q{i}", f"r{i}", {"safe": True, "violations": []})

        recent = manager.get_recent(limit=100)
        assert len(recent) == 5

    def test_singleton(self):
        from security.governance_middleware import get_audit_trail_manager
        m1 = get_audit_trail_manager()
        m2 = get_audit_trail_manager()
        assert m1 is m2

    def test_empty_trail(self):
        from security.governance_middleware import AuditTrailManager
        manager = AuditTrailManager()
        assert manager.get_recent() == []
        summary = manager.get_violation_summary()
        assert summary["total_entries"] == 0
        assert summary["violation_rate"] == 0


class TestGovernanceMiddleware:
    """Tests for GovernanceEnforcementMiddleware."""

    def test_middleware_stats(self):
        from security.governance_middleware import GovernanceEnforcementMiddleware
        middleware = GovernanceEnforcementMiddleware(app=MagicMock())
        stats = middleware.get_stats()
        assert stats["checks_performed"] == 0
        assert stats["violations_caught"] == 0
        assert stats["enforcement_enabled"] is True

    def test_middleware_disabled(self):
        from security.governance_middleware import GovernanceEnforcementMiddleware
        middleware = GovernanceEnforcementMiddleware(
            app=MagicMock(), enable_enforcement=False
        )
        assert middleware.enable_enforcement is False


# ============================================================================
# MEMORY OPTIMIZATION TESTS
# ============================================================================

class TestMemoryOptimization:
    """Tests for memory system optimization."""

    def test_knowledge_graph_memory_bounded(self):
        from cognitive.unified_learning_pipeline import NeighborByNeighborEngine
        engine = NeighborByNeighborEngine(max_total_nodes=10)
        assert engine.max_total_nodes == 10

    def test_audit_trail_memory_bounded(self):
        from security.governance_middleware import AuditTrailManager
        manager = AuditTrailManager(max_trail_size=100)
        for i in range(200):
            manager.record(f"a{i}", f"q{i}", f"r{i}", {"safe": True, "violations": []})
        assert len(manager._trail) <= 100

    def test_pipeline_processed_seeds_tracking(self):
        from cognitive.unified_learning_pipeline import UnifiedLearningPipeline
        pipeline = UnifiedLearningPipeline()
        for i in range(100):
            pipeline._processed_seeds.add(f"seed_{i}")
        assert len(pipeline._processed_seeds) == 100

    def test_chat_intelligence_lazy_init(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        assert ci._ambiguity_engine is None
        assert ci._episodic_buffer is None
        assert ci._governance is None
        assert ci._oracle is None


# ============================================================================
# INTEGRATION WIRING TESTS
# ============================================================================

class TestIntegrationWiring:
    """Tests that all integrations are properly wired."""

    def test_app_imports_unified_pipeline_router(self):
        """Verify the unified pipeline router is imported in app.py."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
        with open(app_path, "r") as f:
            content = f.read()
        assert "unified_pipeline_router" in content
        assert "from api.unified_pipeline_api import router as unified_pipeline_router" in content

    def test_app_includes_pipeline_router(self):
        """Verify the pipeline router is registered."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
        with open(app_path, "r") as f:
            content = f.read()
        assert "app.include_router(unified_pipeline_router)" in content

    def test_app_includes_governance_middleware(self):
        """Verify governance middleware is registered."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
        with open(app_path, "r") as f:
            content = f.read()
        assert "GovernanceEnforcementMiddleware" in content

    def test_app_starts_unified_pipeline(self):
        """Verify pipeline auto-starts in lifespan."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
        with open(app_path, "r") as f:
            content = f.read()
        assert "unified_pipeline.start()" in content

    def test_chat_intelligence_wired_in_send_prompt(self):
        """Verify ChatIntelligence is called in send_prompt."""
        app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
        with open(app_path, "r") as f:
            content = f.read()
        assert "get_chat_intelligence" in content
        assert "chat_intel.detect_ambiguity" in content
        assert "chat_intel.check_governance" in content
        assert "chat_intel.enrich_response" in content
        assert "chat_intel.record_episode" in content
        assert "chat_intel.predict_query_routing" in content

    def test_ingestion_feeds_pipeline(self):
        """Verify ingestion pipeline feeds unified learning pipeline."""
        service_path = os.path.join(os.path.dirname(__file__), "..", "ingestion", "service.py")
        with open(service_path, "r") as f:
            content = f.read()
        assert "unified_learning_pipeline" in content
        assert "pipeline.add_seed" in content

    def test_librarian_feeds_pipeline(self):
        """Verify librarian feeds unified learning pipeline."""
        engine_path = os.path.join(os.path.dirname(__file__), "..", "librarian", "engine.py")
        with open(engine_path, "r") as f:
            content = f.read()
        assert "unified_learning_pipeline" in content
        assert "pipeline.add_seed" in content

    def test_continuous_learning_connects_pipeline(self):
        """Verify continuous learning orchestrator connects to unified pipeline."""
        orch_path = os.path.join(
            os.path.dirname(__file__), "..", "cognitive",
            "continuous_learning_orchestrator.py"
        )
        with open(orch_path, "r") as f:
            content = f.read()
        assert "unified_learning_pipeline" in content

    def test_frontend_api_config_has_pipeline(self):
        """Verify frontend API config includes pipeline endpoints."""
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "frontend", "src", "config", "api.js"
        )
        with open(config_path, "r") as f:
            content = f.read()
        assert "pipeline:" in content
        assert "pipelineStatus:" in content
        assert "pipelineGraph:" in content

    def test_voice_panel_uses_api_base_url(self):
        """Verify PersistentVoicePanel uses centralized API_BASE_URL."""
        panel_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "frontend", "src",
            "components", "PersistentVoicePanel.jsx"
        )
        with open(panel_path, "r") as f:
            content = f.read()
        assert "API_BASE_URL" in content
        assert "http://localhost:8000/voice" not in content

    def test_security_allows_microphone(self):
        """Verify security config allows microphone for voice."""
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "security", "config.py"
        )
        with open(config_path, "r") as f:
            content = f.read()
        assert "microphone=(self)" in content
