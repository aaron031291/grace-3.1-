"""Tests for Phase 3.2: External Knowledge Pull Pipeline."""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ.setdefault("SKIP_EMBEDDING_LOAD", "true")
os.environ.setdefault("SKIP_QDRANT_CHECK", "true")
os.environ.setdefault("SKIP_OLLAMA_CHECK", "true")
os.environ.setdefault("DISABLE_GENESIS_TRACKING", "true")

from cognitive.external_knowledge_pipeline import (
    ExternalKnowledgePipeline,
    get_external_knowledge_pipeline,
    SOURCE_RELIABILITY,
    MIN_RELIABILITY_THRESHOLD,
    MAX_TOPICS_PER_CYCLE,
    MAX_RESULTS_PER_SOURCE,
    MIN_CONTENT_LENGTH,
)


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset global singletons before each test."""
    import cognitive.external_knowledge_pipeline as ekp_mod
    ekp_mod._pipeline = None
    yield
    ekp_mod._pipeline = None


@pytest.fixture
def pipeline():
    return ExternalKnowledgePipeline()


# Sample external source hits
SAMPLE_HITS = [
    {"title": "FastAPI Docs", "link": "https://github.com/tiangolo/fastapi", "snippet": "FastAPI is a modern, fast web framework for building APIs with Python 3.7+. " * 3, "source": "github"},
    {"title": "Python best practices", "link": "https://stackoverflow.com/q/123", "snippet": "Here are the best practices for Python development including type hints and testing. " * 3, "source": "stackoverflow"},
    {"title": "Attention Is All You Need", "link": "https://arxiv.org/abs/1706.03762", "snippet": "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms. " * 3, "source": "arxiv"},
    {"title": "Short", "link": "https://devto.com/x", "snippet": "Hi", "source": "devto"},  # Too short
    {"title": "HN discussion", "link": "https://news.ycombinator.com/item?id=1", "snippet": "This is a very interesting discussion about recent developments in AI systems." * 3, "source": "hackernews"},
]


# ═══════════════════════════════════════════════════════════════════════
# 1. Pipeline Initialization
# ═══════════════════════════════════════════════════════════════════════

class TestPipelineInit:

    def test_pipeline_creates(self, pipeline):
        """Pipeline initializes with correct defaults."""
        assert pipeline._running is False
        assert pipeline._total_cycles == 0
        assert pipeline._total_fetches == 0
        assert pipeline._total_ingested == 0
        assert pipeline._total_rejected == 0

    def test_singleton(self):
        """Singleton returns same instance."""
        p1 = get_external_knowledge_pipeline()
        p2 = get_external_knowledge_pipeline()
        assert p1 is p2

    def test_start_stop(self, pipeline):
        """Pipeline starts and stops cleanly."""
        started = pipeline.start()
        assert started is True
        assert pipeline._running is True
        assert pipeline.start() is False  # already running
        pipeline.stop()
        assert pipeline._running is False


# ═══════════════════════════════════════════════════════════════════════
# 2. Source Reliability Weights
# ═══════════════════════════════════════════════════════════════════════

class TestSourceReliability:

    def test_all_sources_have_weights(self):
        """All expected sources have reliability weights."""
        expected = ["github", "stackoverflow", "arxiv", "wikipedia", "hackernews",
                     "devto", "pypi", "mdn", "semantic_scholar", "npm", "ietf_rfc"]
        for source in expected:
            assert source in SOURCE_RELIABILITY, f"Missing weight for {source}"

    def test_weights_in_valid_range(self):
        """All weights are between 0 and 1."""
        for source, weight in SOURCE_RELIABILITY.items():
            assert 0.0 <= weight <= 1.0, f"{source} weight {weight} out of range"

    def test_academic_sources_highest(self):
        """Academic sources (arXiv, Semantic Scholar, IETF) have highest reliability."""
        assert SOURCE_RELIABILITY["ietf_rfc"] >= 0.85
        assert SOURCE_RELIABILITY["arxiv"] >= 0.80
        assert SOURCE_RELIABILITY["semantic_scholar"] >= 0.80

    def test_discussion_sources_lowest(self):
        """Discussion sources (HackerNews, DevTo) have lowest reliability."""
        assert SOURCE_RELIABILITY["hackernews"] < SOURCE_RELIABILITY["github"]
        assert SOURCE_RELIABILITY["devto"] < SOURCE_RELIABILITY["stackoverflow"]

    def test_reliability_ordering(self):
        """Sources are ordered: standards > academic > code > community > discussion."""
        assert SOURCE_RELIABILITY["ietf_rfc"] >= SOURCE_RELIABILITY["arxiv"]
        assert SOURCE_RELIABILITY["arxiv"] >= SOURCE_RELIABILITY["github"]
        assert SOURCE_RELIABILITY["github"] >= SOURCE_RELIABILITY["stackoverflow"]
        assert SOURCE_RELIABILITY["stackoverflow"] >= SOURCE_RELIABILITY["devto"]
        assert SOURCE_RELIABILITY["devto"] >= SOURCE_RELIABILITY["hackernews"]


# ═══════════════════════════════════════════════════════════════════════
# 3. Quality Filtering
# ═══════════════════════════════════════════════════════════════════════

class TestQualityFiltering:

    def test_short_content_rejected(self, pipeline):
        """Snippets shorter than MIN_CONTENT_LENGTH are rejected."""
        with patch("cognitive.unified_memory.get_unified_memory") as mock_mem:
            mock_mem.return_value = MagicMock()
            with patch("search.external_sources.fetch_all_external", return_value=[
                {"title": "Short", "link": "http://x", "snippet": "Hi", "source": "github"},
            ]):
                result = pipeline._process_topic("test topic")

        assert result["rejected"] == 1
        assert result["ingested"] == 0

    def test_good_content_ingested(self, pipeline):
        """Content meeting length and reliability thresholds is ingested."""
        good_hit = {
            "title": "Good Repo",
            "link": "https://github.com/good/repo",
            "snippet": "This is a comprehensive guide to building production Python APIs. " * 5,
            "source": "github",
        }
        with patch("cognitive.unified_memory.get_unified_memory") as mock_mem:
            mock_mem.return_value = MagicMock()
            with patch("search.external_sources.fetch_all_external", return_value=[good_hit]):
                result = pipeline._process_topic("python APIs")

        assert result["ingested"] == 1
        assert result["rejected"] == 0
        assert "github" in result["sources_used"]

    def test_mixed_quality_filtered(self, pipeline):
        """Mix of good and bad content: good ingested, bad rejected."""
        with patch("cognitive.unified_memory.get_unified_memory") as mock_mem:
            mock_mem.return_value = MagicMock()
            with patch("search.external_sources.fetch_all_external", return_value=SAMPLE_HITS):
                result = pipeline._process_topic("AI systems")

        # github (good), stackoverflow (good), arxiv (good) → ingested
        # devto "Hi" (too short) → rejected
        # hackernews (good content, reliability 0.45 >= 0.40) → ingested
        assert result["ingested"] >= 3
        assert result["rejected"] >= 1  # at least the short one


# ═══════════════════════════════════════════════════════════════════════
# 4. Gap Detection
# ═══════════════════════════════════════════════════════════════════════

class TestGapDetection:

    def test_detects_gaps_from_reverse_knn(self, pipeline):
        """Gap detection uses reverse kNN suggestions."""
        with patch("cognitive.reverse_knn.ReverseKNNOracle") as MockOracle:
            mock_oracle = MagicMock()
            mock_oracle.suggest_expansion_topics.return_value = ["machine learning", "kubernetes"]
            mock_oracle.get_demand_gaps.return_value = []
            MockOracle.return_value = mock_oracle

            with patch("cognitive.trust_engine.get_trust_engine") as mock_te:
                mock_te.return_value = MagicMock()
                mock_te.return_value.get_system_trust.return_value = {"components": {}}

                topics = pipeline._detect_gaps()

        assert "machine learning" in topics
        assert "kubernetes" in topics

    def test_detects_gaps_from_governance(self, pipeline):
        """Gap detection includes topics from low-trust components."""
        with patch("cognitive.reverse_knn.ReverseKNNOracle") as MockOracle:
            mock_oracle = MagicMock()
            mock_oracle.suggest_expansion_topics.return_value = []
            mock_oracle.get_demand_gaps.return_value = []
            MockOracle.return_value = mock_oracle

            with patch("cognitive.trust_engine.get_trust_engine") as mock_te:
                mock_te.return_value = MagicMock()
                mock_te.return_value.get_system_trust.return_value = {
                    "components": {
                        "ingestion": {"trust": 55.0, "name": "Ingestion Pipeline"},
                    }
                }

                topics = pipeline._detect_gaps()

        # Should include governance-derived topic
        assert any("ingestion" in t.lower() for t in topics)

    def test_deduplicates_topics(self, pipeline):
        """Duplicate topics are removed."""
        with patch("cognitive.reverse_knn.ReverseKNNOracle") as MockOracle:
            mock_oracle = MagicMock()
            mock_oracle.suggest_expansion_topics.return_value = ["python", "Python", "PYTHON"]
            mock_oracle.get_demand_gaps.return_value = [{"topic": "python"}]
            MockOracle.return_value = mock_oracle

            with patch("cognitive.trust_engine.get_trust_engine") as mock_te:
                mock_te.return_value = MagicMock()
                mock_te.return_value.get_system_trust.return_value = {"components": {}}

                topics = pipeline._detect_gaps()

        # Should be deduplicated
        assert len(topics) == 1

    def test_caps_at_max_topics(self, pipeline):
        """Gap detection caps at MAX_TOPICS_PER_CYCLE."""
        with patch("cognitive.reverse_knn.ReverseKNNOracle") as MockOracle:
            mock_oracle = MagicMock()
            mock_oracle.suggest_expansion_topics.return_value = [f"topic_{i}" for i in range(20)]
            mock_oracle.get_demand_gaps.return_value = []
            MockOracle.return_value = mock_oracle

            with patch("cognitive.trust_engine.get_trust_engine") as mock_te:
                mock_te.return_value = MagicMock()
                mock_te.return_value.get_system_trust.return_value = {"components": {}}

                topics = pipeline._detect_gaps()

        assert len(topics) <= MAX_TOPICS_PER_CYCLE


# ═══════════════════════════════════════════════════════════════════════
# 5. Ingestion
# ═══════════════════════════════════════════════════════════════════════

class TestIngestion:

    def test_ingest_stores_in_unified_memory(self, pipeline):
        """Ingested items are stored in unified memory."""
        with patch("cognitive.unified_memory.get_unified_memory") as mock_mem:
            mock_instance = MagicMock()
            mock_mem.return_value = mock_instance

            success = pipeline._ingest_item(
                "python testing",
                {"title": "Pytest Guide", "snippet": "Comprehensive guide to pytest.", "link": "http://x", "source": "github"},
                0.75,
            )

        assert success is True
        mock_instance.store_learning.assert_called_once()
        call_kwargs = mock_instance.store_learning.call_args
        assert call_kwargs[1]["trust"] == 0.75
        assert call_kwargs[1]["source"] == "external_github"

    def test_ingest_fails_gracefully(self, pipeline):
        """If unified memory fails, ingest returns False."""
        with patch("cognitive.unified_memory.get_unified_memory", side_effect=RuntimeError("no DB")):
            success = pipeline._ingest_item(
                "test",
                {"title": "X", "snippet": "Y", "link": "", "source": "github"},
                0.5,
            )
        assert success is False

    def test_ingest_uses_source_reliability_as_trust(self, pipeline):
        """Trust score for ingested items equals source reliability."""
        with patch("cognitive.unified_memory.get_unified_memory") as mock_mem:
            mock_instance = MagicMock()
            mock_mem.return_value = mock_instance

            pipeline._ingest_item("topic", {"title": "T", "snippet": "S" * 100, "link": "", "source": "arxiv"}, 0.85)

        call_kwargs = mock_instance.store_learning.call_args[1]
        assert call_kwargs["trust"] == 0.85


# ═══════════════════════════════════════════════════════════════════════
# 6. Full Cycle
# ═══════════════════════════════════════════════════════════════════════

class TestFullCycle:

    def test_run_cycle_with_gaps(self, pipeline):
        """Full cycle: gaps detected → fetched → ingested."""
        with patch.object(pipeline, "_detect_gaps", return_value=["fastapi"]):
            with patch("search.external_sources.fetch_all_external", return_value=[
                {"title": "FastAPI", "link": "http://x", "snippet": "A" * 100, "source": "github"},
            ]):
                with patch("cognitive.unified_memory.get_unified_memory") as mock_mem:
                    mock_mem.return_value = MagicMock()
                    with patch("cognitive.event_bus.publish_async"):
                        pipeline._run_cycle()

        assert pipeline._total_cycles == 1
        assert pipeline._total_ingested >= 1

    def test_run_cycle_no_gaps(self, pipeline):
        """Full cycle with no gaps detected: no fetches."""
        with patch.object(pipeline, "_detect_gaps", return_value=[]):
            pipeline._run_cycle()

        assert pipeline._total_cycles == 1
        assert pipeline._total_fetches == 0

    def test_force_cycle(self, pipeline):
        """force_cycle() runs a full cycle manually."""
        with patch.object(pipeline, "_run_cycle") as mock_run:
            result = pipeline.force_cycle()

        assert result["status"] == "completed"
        mock_run.assert_called_once()

    def test_force_cycle_error(self, pipeline):
        """force_cycle() handles errors gracefully."""
        with patch.object(pipeline, "_run_cycle", side_effect=RuntimeError("boom")):
            result = pipeline.force_cycle()

        assert result["status"] == "error"
        assert "boom" in result["error"]


# ═══════════════════════════════════════════════════════════════════════
# 7. Manual Pull
# ═══════════════════════════════════════════════════════════════════════

class TestManualPull:

    def test_pull_specific_topic(self, pipeline):
        """pull_topic() fetches and ingests for a specific topic."""
        with patch("search.external_sources.fetch_all_external", return_value=[
            {"title": "Result", "link": "http://x", "snippet": "B" * 100, "source": "stackoverflow"},
        ]):
            with patch("cognitive.unified_memory.get_unified_memory") as mock_mem:
                mock_mem.return_value = MagicMock()
                result = pipeline.pull_topic("docker networking")

        assert result["topic"] == "docker networking"
        assert result["fetched"] >= 1
        assert result["ingested"] >= 1


# ═══════════════════════════════════════════════════════════════════════
# 8. Status & History
# ═══════════════════════════════════════════════════════════════════════

class TestStatusHistory:

    def test_status_includes_reliability(self, pipeline):
        """Status includes source reliability weights."""
        status = pipeline.get_status()
        assert "source_reliability" in status
        assert status["source_reliability"]["github"] == 0.75

    def test_status_counters(self, pipeline):
        """Status shows correct counters."""
        status = pipeline.get_status()
        assert status["running"] is False
        assert status["total_cycles"] == 0
        assert status["total_ingested"] == 0

    def test_history_populates(self, pipeline):
        """After a fetch, history has entries."""
        with patch("search.external_sources.fetch_all_external", return_value=[
            {"title": "X", "link": "http://x", "snippet": "C" * 100, "source": "github"},
        ]):
            with patch("cognitive.unified_memory.get_unified_memory") as mock_mem:
                mock_mem.return_value = MagicMock()
                pipeline._process_topic("test")

        history = pipeline.get_fetch_history()
        assert len(history) == 1
        assert history[0]["topic"] == "test"


# ═══════════════════════════════════════════════════════════════════════
# 9. Adaptive Interval
# ═══════════════════════════════════════════════════════════════════════

class TestAdaptiveInterval:

    def test_default_interval(self, pipeline):
        """Without TimeSense, returns default interval."""
        with patch("cognitive.time_sense.TimeSense.now_context", side_effect=ImportError):
            interval = pipeline._get_adaptive_interval()
        assert interval == 1800  # 30 minutes

    def test_business_hours_faster(self, pipeline):
        """During business hours, cycles faster."""
        with patch("cognitive.time_sense.TimeSense.now_context", return_value={"is_business_hours": True}):
            interval = pipeline._get_adaptive_interval()
        assert interval == 900  # 15 minutes

    def test_late_night_slower(self, pipeline):
        """Late night cycles much slower."""
        with patch("cognitive.time_sense.TimeSense.now_context", return_value={"period": "late_night"}):
            interval = pipeline._get_adaptive_interval()
        assert interval == 7200  # 2 hours


# ═══════════════════════════════════════════════════════════════════════
# 10. Configuration Constants
# ═══════════════════════════════════════════════════════════════════════

class TestConstants:

    def test_threshold_valid(self):
        """MIN_RELIABILITY_THRESHOLD is reasonable."""
        assert 0.0 < MIN_RELIABILITY_THRESHOLD < 1.0

    def test_max_topics_valid(self):
        """MAX_TOPICS_PER_CYCLE is positive."""
        assert MAX_TOPICS_PER_CYCLE > 0

    def test_max_results_valid(self):
        """MAX_RESULTS_PER_SOURCE is positive."""
        assert MAX_RESULTS_PER_SOURCE > 0

    def test_min_content_length_valid(self):
        """MIN_CONTENT_LENGTH is reasonable."""
        assert MIN_CONTENT_LENGTH > 0
        assert MIN_CONTENT_LENGTH < 500
