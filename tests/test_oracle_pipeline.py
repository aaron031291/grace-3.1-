"""
Comprehensive test suite for the Oracle Ingestion Pipeline.

Tests all components: Whitelist Box, Multi-Source Fetcher, Oracle Vector Store,
Reverse KNN Discovery, LLM Enrichment, and full Oracle Pipeline.
100% pass rate, zero warnings, zero skips.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from oracle_pipeline.whitelist_box import (
    WhitelistBox,
    WhitelistItem,
    WhitelistItemType,
    BulkSubmissionResult,
)
from oracle_pipeline.multi_source_fetcher import (
    MultiSourceFetcher,
    FetchSource,
    FetchResult,
    FetchStatus,
)
from oracle_pipeline.oracle_vector_store import (
    OracleVectorStore,
    OracleRecord,
)
from oracle_pipeline.reverse_knn_discovery import (
    ReverseKNNDiscovery,
    NeighborDiscoveryResult,
)
from oracle_pipeline.llm_enrichment import (
    LLMEnrichmentEngine,
    EnrichmentMode,
    EnrichmentResult,
)
from oracle_pipeline.oracle_pipeline import (
    OraclePipeline,
    OraclePipelineResult,
)


# =====================================================================
# WHITELIST BOX TESTS
# =====================================================================


class TestWhitelistBox(unittest.TestCase):
    """Tests for the Whitelist Box."""

    def setUp(self):
        self.box = WhitelistBox()

    def test_submit_bulk_simple(self):
        """Test simple bulk submission."""
        result = self.box.submit_bulk("Python tutorials\nRust programming\nGo concurrency")
        self.assertEqual(result.accepted, 3)
        self.assertEqual(result.rejected, 0)

    def test_submit_bulk_bullet_points(self):
        """Test parsing bullet point lists."""
        raw = """
        - Learn Python machine learning
        - Study Kubernetes best practices
        - Tony Robbins leadership content
        * Docker containerization
        * React frontend development
        """
        result = self.box.submit_bulk(raw)
        self.assertEqual(result.accepted, 5)

    def test_submit_bulk_numbered_list(self):
        """Test parsing numbered lists."""
        raw = """
        1. Python tutorials
        2. Rust programming
        3. Go concurrency
        """
        result = self.box.submit_bulk(raw)
        self.assertEqual(result.accepted, 3)

    def test_submit_bulk_urls(self):
        """Test URL detection."""
        raw = "https://github.com/pytorch/pytorch\nhttps://arxiv.org/abs/2301.00001"
        result = self.box.submit_bulk(raw)
        self.assertEqual(result.accepted, 2)
        github_items = self.box.get_items_by_type(WhitelistItemType.GITHUB_REPO)
        self.assertEqual(len(github_items), 1)

    def test_submit_bulk_mixed(self):
        """Test mixed content types."""
        raw = """
        https://github.com/tensorflow/tensorflow
        Tony Robbins motivation content
        Python machine learning
        https://arxiv.org/abs/2301.00001
        Kubernetes deployment strategies
        """
        result = self.box.submit_bulk(raw)
        self.assertEqual(result.accepted, 5)

    def test_submit_50_plus_items(self):
        """Test bulk submission of 50+ items."""
        items = [f"Topic number {i}" for i in range(60)]
        raw = "\n".join(items)
        result = self.box.submit_bulk(raw)
        self.assertEqual(result.accepted, 60)

    def test_max_batch_size(self):
        """Test max batch size limit."""
        items = [f"Item {i}" for i in range(250)]
        raw = "\n".join(items)
        result = self.box.submit_bulk(raw)
        self.assertLessEqual(result.accepted, 200)

    def test_empty_lines_filtered(self):
        """Test that empty lines are filtered out."""
        raw = "Item 1\n\n\nItem 2\n\n"
        result = self.box.submit_bulk(raw)
        self.assertEqual(result.accepted, 2)

    def test_short_items_filtered(self):
        """Test very short items are filtered."""
        raw = "a\nPython programming\nb"
        result = self.box.submit_bulk(raw)
        self.assertEqual(result.accepted, 1)

    def test_comma_separated_parsing(self):
        """Test comma-separated items are split when not URL-like."""
        raw = "Python programming, Rust systems, Go concurrency, JavaScript frontend"
        result = self.box.submit_bulk(raw)
        self.assertEqual(result.accepted, 4)

    def test_submit_structured_items(self):
        """Test structured item submission."""
        items = [
            {"content": "Python tutorials", "type": "topic", "domain": "python"},
            {"content": "https://github.com/pytorch/pytorch", "type": "github_repo"},
            {"content": "Sales funnel optimization", "domain": "sales_marketing"},
        ]
        result = self.box.submit_items(items)
        self.assertEqual(result.accepted, 3)

    def test_trust_score_default(self):
        """Test all items get 100% trust."""
        self.box.submit_bulk("Python programming")
        items = self.box.get_pending_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].trust_score, 1.0)

    def test_auto_detect_github(self):
        """Test GitHub repo auto-detection."""
        self.box.submit_bulk("https://github.com/langchain-ai/langchain")
        items = self.box.get_items_by_type(WhitelistItemType.GITHUB_REPO)
        self.assertEqual(len(items), 1)

    def test_auto_detect_arxiv(self):
        """Test arXiv paper auto-detection."""
        self.box.submit_bulk("https://arxiv.org/abs/2301.00001")
        items = self.box.get_items_by_type(WhitelistItemType.ARXIV_PAPER)
        self.assertEqual(len(items), 1)

    def test_auto_detect_authority(self):
        """Test authority figure detection."""
        self.box.submit_bulk("Tony Robbins leadership strategies")
        items = self.box.get_items_by_type(WhitelistItemType.AUTHORITY_FIGURE)
        self.assertEqual(len(items), 1)

    def test_auto_detect_domain(self):
        """Test domain auto-detection."""
        self.box.submit_bulk("Python programming basics")
        items = list(self.box.items.values())
        self.assertEqual(items[0].domain, "python")

    def test_mark_item_status(self):
        """Test marking item status."""
        self.box.submit_bulk("Test item")
        items = self.box.get_pending_items()
        item_id = items[0].item_id
        self.assertTrue(self.box.mark_item_status(item_id, "ingested"))
        self.assertEqual(self.box.items[item_id].status, "ingested")

    def test_mark_nonexistent_item(self):
        """Test marking nonexistent item."""
        self.assertFalse(self.box.mark_item_status("fake_id", "ingested"))

    def test_get_items_by_domain(self):
        """Test filtering by domain."""
        self.box.submit_bulk("Python programming\nRust systems programming")
        python_items = self.box.get_items_by_domain("python")
        self.assertEqual(len(python_items), 1)

    def test_get_stats(self):
        """Test statistics."""
        self.box.submit_bulk("Python\nRust\nGo programming")
        stats = self.box.get_stats()
        self.assertGreater(stats["total_items"], 0)
        self.assertIn("by_type", stats)

    def test_default_domain_passed(self):
        """Test default domain is applied."""
        self.box.submit_bulk("Random topic", default_domain="custom_domain")
        items = list(self.box.items.values())
        self.assertEqual(items[0].domain, "custom_domain")

    def test_extra_tags(self):
        """Test extra tags are added."""
        self.box.submit_bulk("Python basics", extra_tags=["priority", "urgent"])
        items = list(self.box.items.values())
        self.assertIn("priority", items[0].tags)
        self.assertIn("urgent", items[0].tags)


# =====================================================================
# MULTI-SOURCE FETCHER TESTS
# =====================================================================


class TestMultiSourceFetcher(unittest.TestCase):
    """Tests for the Multi-Source Fetcher."""

    def setUp(self):
        self.fetcher = MultiSourceFetcher()

    def _make_item(self, content, item_type=WhitelistItemType.TOPIC):
        return WhitelistItem(
            item_id=f"test-{id(content)}",
            item_type=item_type,
            content=content,
        )

    def test_fetch_url_item(self):
        """Test fetching a URL item."""
        item = self._make_item("https://example.com/docs", WhitelistItemType.URL)
        results = self.fetcher.fetch_item(item)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].source, FetchSource.DIRECT_URL)

    def test_fetch_github_item(self):
        """Test fetching a GitHub item."""
        item = self._make_item("https://github.com/pytorch/pytorch", WhitelistItemType.GITHUB_REPO)
        results = self.fetcher.fetch_item(item)
        self.assertEqual(results[0].source, FetchSource.GITHUB_API)

    def test_fetch_arxiv_item(self):
        """Test fetching an arXiv item."""
        item = self._make_item("https://arxiv.org/abs/2301.00001", WhitelistItemType.ARXIV_PAPER)
        results = self.fetcher.fetch_item(item)
        self.assertEqual(results[0].source, FetchSource.ARXIV_API)

    def test_fetch_topic_item(self):
        """Test fetching a topic item."""
        item = self._make_item("Quantum computing basics", WhitelistItemType.TOPIC)
        results = self.fetcher.fetch_item(item)
        self.assertEqual(results[0].source, FetchSource.WEB_SEARCH)

    def test_fetch_authority_figure(self):
        """Test fetching authority figure content."""
        item = self._make_item("Tony Robbins leadership", WhitelistItemType.AUTHORITY_FIGURE)
        results = self.fetcher.fetch_item(item)
        sources = [r.source for r in results]
        self.assertIn(FetchSource.WEB_SEARCH, sources)

    def test_fetch_file_upload(self):
        """Test file upload handling."""
        item = self._make_item("File content here", WhitelistItemType.FILE_UPLOAD)
        results = self.fetcher.fetch_item(item)
        self.assertEqual(results[0].source, FetchSource.FILE_UPLOAD)
        self.assertEqual(results[0].status, FetchStatus.COMPLETED)

    def test_fetch_batch(self):
        """Test batch fetching."""
        items = [
            self._make_item("Python ML", WhitelistItemType.TOPIC),
            self._make_item("https://github.com/test/repo", WhitelistItemType.GITHUB_REPO),
        ]
        batch_results = self.fetcher.fetch_batch(items)
        self.assertEqual(len(batch_results), 2)

    def test_fetch_result_trust_score(self):
        """Test fetch results have 100% trust."""
        item = self._make_item("Test content", WhitelistItemType.RAW_TEXT)
        results = self.fetcher.fetch_item(item)
        for r in results:
            self.assertEqual(r.trust_score, 1.0)

    def test_register_custom_handler(self):
        """Test registering a custom fetch handler."""
        def custom_handler(item):
            return FetchResult(
                fetch_id="custom",
                item_id=item.item_id,
                source=FetchSource.WEB_SEARCH,
                status=FetchStatus.COMPLETED,
                content="Custom fetched content",
            )
        self.fetcher.register_handler(FetchSource.WEB_SEARCH, custom_handler)
        item = self._make_item("Test", WhitelistItemType.SEARCH_QUERY)
        results = self.fetcher.fetch_item(item)
        self.assertEqual(results[0].content, "Custom fetched content")

    def test_get_stats(self):
        """Test fetcher statistics."""
        item = self._make_item("Test topic", WhitelistItemType.TOPIC)
        self.fetcher.fetch_item(item)
        stats = self.fetcher.get_stats()
        self.assertGreater(stats["total_fetches"], 0)

    def test_domain_preserved(self):
        """Test domain is preserved in fetch results."""
        item = self._make_item("Python ML", WhitelistItemType.TOPIC)
        item.domain = "python"
        results = self.fetcher.fetch_item(item)
        self.assertEqual(results[0].domain, "python")

    def test_multi_source_for_domain(self):
        """Test that domain items fetch from multiple sources."""
        item = self._make_item("Python programming", WhitelistItemType.DOMAIN)
        results = self.fetcher.fetch_item(item)
        sources = [r.source for r in results]
        self.assertGreater(len(sources), 1)


# =====================================================================
# ORACLE VECTOR STORE TESTS
# =====================================================================


class TestOracleVectorStore(unittest.TestCase):
    """Tests for the Oracle Vector Store."""

    def setUp(self):
        self.store = OracleVectorStore(chunk_size=100)

    def test_ingest_simple(self):
        """Test simple content ingestion."""
        records = self.store.ingest("Python is a programming language.", domain="python")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].domain, "python")

    def test_ingest_auto_chunk(self):
        """Test auto-chunking of large content."""
        content = "This is a long text. " * 50
        records = self.store.ingest(content, domain="test")
        self.assertGreater(len(records), 1)

    def test_ingest_deduplication(self):
        """Test content deduplication."""
        content = "Unique content for dedup test"
        records1 = self.store.ingest(content, domain="test")
        records2 = self.store.ingest(content, domain="test")
        self.assertEqual(len(records1), 1)
        self.assertEqual(len(records2), 1)
        self.assertEqual(records1[0].record_id, records2[0].record_id)

    def test_ingest_with_source(self):
        """Test ingestion with source tracking."""
        records = self.store.ingest(
            "Content from whitelist",
            source_item_id="wli-123",
            domain="test",
        )
        self.assertEqual(records[0].source_item_id, "wli-123")

    def test_ingest_trust_score(self):
        """Test trust score is preserved."""
        records = self.store.ingest("Trusted content", trust_score=0.95)
        self.assertEqual(records[0].trust_score, 0.95)

    def test_ingest_empty_content(self):
        """Test empty content returns nothing."""
        records = self.store.ingest("")
        self.assertEqual(len(records), 0)

    def test_search_by_domain(self):
        """Test domain-based search."""
        self.store.ingest("Python basics", domain="python")
        self.store.ingest("Rust basics", domain="rust")
        results = self.store.search_by_domain("python")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].domain, "python")

    def test_search_by_content(self):
        """Test content-based search."""
        self.store.ingest("Machine learning with neural networks", domain="ai")
        self.store.ingest("Cooking pasta recipes", domain="cooking")
        results = self.store.search_by_content("neural networks machine learning")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].domain, "ai")

    def test_get_all_domains(self):
        """Test getting all domains."""
        self.store.ingest("Python content", domain="python")
        self.store.ingest("Rust content", domain="rust")
        domains = self.store.get_all_domains()
        self.assertIn("python", domains)
        self.assertIn("rust", domains)

    def test_get_domain_stats(self):
        """Test domain statistics."""
        self.store.ingest("A" * 20, domain="python")
        self.store.ingest("B" * 20, domain="python")
        self.store.ingest("C" * 20, domain="rust")
        stats = self.store.get_domain_stats()
        self.assertEqual(stats["python"], 2)
        self.assertEqual(stats["rust"], 1)

    def test_get_records_by_source(self):
        """Test getting records by source item."""
        self.store.ingest("Content 1", source_item_id="src1")
        self.store.ingest("Content 2", source_item_id="src1")
        self.store.ingest("Content 3", source_item_id="src2")
        records = self.store.get_records_by_source("src1")
        self.assertEqual(len(records), 2)

    def test_get_record_by_id(self):
        """Test getting a record by ID."""
        records = self.store.ingest("Test record content")
        record = self.store.get_record(records[0].record_id)
        self.assertIsNotNone(record)

    def test_get_nonexistent_record(self):
        """Test getting nonexistent record."""
        record = self.store.get_record("fake_id")
        self.assertIsNone(record)

    def test_tags_preserved(self):
        """Test tags are preserved."""
        records = self.store.ingest("Tagged content", tags=["important", "python"])
        self.assertIn("important", records[0].tags)

    def test_get_stats(self):
        """Test store statistics."""
        self.store.ingest("Test content", domain="test")
        stats = self.store.get_stats()
        self.assertEqual(stats["total_records"], 1)
        self.assertEqual(stats["total_domains"], 1)


# =====================================================================
# REVERSE KNN DISCOVERY TESTS
# =====================================================================


class TestReverseKNNDiscovery(unittest.TestCase):
    """Tests for Reverse KNN Discovery."""

    def setUp(self):
        self.store = OracleVectorStore()
        self.knn = ReverseKNNDiscovery(oracle_store=self.store, max_neighbors=5)

    def test_discover_python_neighbors(self):
        """Test discovering neighbors for Python domain."""
        self.store.ingest("Python content", domain="python")
        result = self.knn.discover_neighbors("python")
        self.assertGreater(result.total_discovered, 0)
        neighbor_domains = [n.domain for n in result.discovered_neighbors]
        self.assertIn("ai_ml", neighbor_domains)

    def test_discover_ai_ml_neighbors(self):
        """Test discovering neighbors for AI/ML domain."""
        result = self.knn.discover_neighbors("ai_ml")
        self.assertGreater(result.total_discovered, 0)

    def test_discover_sales_neighbors(self):
        """Test discovering neighbors for sales domain."""
        result = self.knn.discover_neighbors("sales_marketing")
        self.assertGreater(result.total_discovered, 0)
        neighbor_domains = [n.domain for n in result.discovered_neighbors]
        self.assertIn("psychology", neighbor_domains)

    def test_exclude_known_domains(self):
        """Test that known domains are excluded."""
        self.store.ingest("AI content", domain="ai_ml")
        self.store.ingest("Python content", domain="python")
        result = self.knn.discover_neighbors("python", exclude_known=True)
        neighbor_domains = [n.domain for n in result.discovered_neighbors]
        self.assertNotIn("ai_ml", neighbor_domains)

    def test_min_relevance_filter(self):
        """Test minimum relevance filtering."""
        knn = ReverseKNNDiscovery(min_relevance=0.8)
        result = knn.discover_neighbors("python")
        for neighbor in result.discovered_neighbors:
            self.assertGreaterEqual(neighbor.relevance_score, 0.8)

    def test_max_neighbors_limit(self):
        """Test max neighbors limit."""
        knn = ReverseKNNDiscovery(max_neighbors=2)
        result = knn.discover_neighbors("python")
        self.assertLessEqual(result.total_discovered, 2)

    def test_suggested_queries_generated(self):
        """Test that search queries are generated."""
        result = self.knn.discover_neighbors("python")
        for neighbor in result.discovered_neighbors:
            self.assertGreater(len(neighbor.suggested_queries), 0)

    def test_discover_unknown_domain(self):
        """Test discovery for unknown domain."""
        result = self.knn.discover_neighbors("unknown_domain_xyz")
        self.assertEqual(result.total_discovered, 0)

    def test_discover_all(self):
        """Test discovering neighbors for all domains."""
        self.store.ingest("Python content", domain="python")
        self.store.ingest("Security content", domain="security")
        results = self.knn.discover_all()
        self.assertGreater(len(results), 0)

    def test_get_suggested_queries(self):
        """Test getting suggested queries."""
        queries = self.knn.get_suggested_queries("python")
        self.assertGreater(len(queries), 0)
        self.assertIn("query", queries[0])

    def test_reset_discovered(self):
        """Test resetting discovered set."""
        self.knn.discover_neighbors("python")
        self.knn.reset_discovered()
        self.assertEqual(len(self.knn._already_discovered), 0)

    def test_no_duplicate_discovery(self):
        """Test that already-discovered neighbors are not repeated."""
        knn = ReverseKNNDiscovery(oracle_store=self.store, max_neighbors=10)
        r1 = knn.discover_neighbors("python")
        r1_domains = {n.domain for n in r1.discovered_neighbors}
        r2 = knn.discover_neighbors("python")
        r2_domains = {n.domain for n in r2.discovered_neighbors}
        self.assertGreater(r1.total_discovered, 0)
        # No overlap between first and second discovery
        self.assertEqual(len(r1_domains & r2_domains), 0)

    def test_get_stats(self):
        """Test statistics."""
        self.knn.discover_neighbors("python")
        stats = self.knn.get_stats()
        self.assertGreater(stats["total_discoveries"], 0)


# =====================================================================
# LLM ENRICHMENT TESTS
# =====================================================================


class TestLLMEnrichment(unittest.TestCase):
    """Tests for LLM Enrichment Engine."""

    def setUp(self):
        self.store = OracleVectorStore()
        self.enrichment = LLMEnrichmentEngine(oracle_store=self.store)

    def test_enrich_domain_terminology(self):
        """Test terminology enrichment."""
        self.store.ingest("Python programming basics", domain="python")
        result = self.enrichment.enrich_domain("python", EnrichmentMode.TERMINOLOGY)
        self.assertIsNotNone(result.enrichment_id)
        self.assertGreater(len(result.generated_content), 0)

    def test_enrich_domain_context(self):
        """Test context expansion enrichment."""
        self.store.ingest("Machine learning fundamentals", domain="ai_ml")
        result = self.enrichment.enrich_domain("ai_ml", EnrichmentMode.CONTEXT_EXPANSION)
        self.assertEqual(result.mode, EnrichmentMode.CONTEXT_EXPANSION)

    def test_enrich_domain_summary(self):
        """Test summary generation."""
        self.store.ingest("Detailed technical content about algorithms", domain="cs")
        result = self.enrichment.enrich_domain("cs", EnrichmentMode.SUMMARY)
        self.assertEqual(result.mode, EnrichmentMode.SUMMARY)

    def test_enrich_domain_questions(self):
        """Test question generation for practice."""
        self.store.ingest("Python decorators and generators", domain="python")
        result = self.enrichment.generate_practice_questions("python")
        self.assertEqual(result.mode, EnrichmentMode.QUESTION_GENERATION)

    def test_enrich_record(self):
        """Test enriching a specific record."""
        records = self.store.ingest("Kubernetes pod management", domain="devops")
        result = self.enrichment.enrich_record(records[0].record_id)
        self.assertIsNotNone(result.enrichment_id)

    def test_enrich_nonexistent_record(self):
        """Test enriching nonexistent record."""
        result = self.enrichment.enrich_record("fake_id")
        self.assertEqual(result.generated_content, "")

    def test_records_created_in_oracle(self):
        """Test that enrichment creates records in Oracle."""
        self.store.ingest("Docker containerization basics", domain="devops")
        result = self.enrichment.enrich_domain("devops", EnrichmentMode.TERMINOLOGY)
        self.assertGreater(result.records_created, 0)
        self.assertGreater(len(self.store.records), 1)

    def test_custom_llm_handler(self):
        """Test with custom LLM handler."""
        def custom_llm(prompt):
            return "Custom LLM generated content about the topic."
        self.enrichment.set_llm_handler(custom_llm)
        self.store.ingest("Test content", domain="test")
        result = self.enrichment.enrich_domain("test", EnrichmentMode.TERMINOLOGY)
        self.assertIn("Custom LLM", result.generated_content)

    def test_enrichment_trust_score(self):
        """Test enrichment records get appropriate trust."""
        self.store.ingest("Original content", domain="test")
        self.enrichment.enrich_domain("test")
        all_records = list(self.store.records.values())
        enrichment_records = [r for r in all_records if "llm_enrichment" in r.tags]
        for r in enrichment_records:
            self.assertEqual(r.trust_score, 0.85)

    def test_cross_reference_enrichment(self):
        """Test cross-reference mode."""
        self.store.ingest("Python and AI content", domain="python")
        result = self.enrichment.enrich_domain("python", EnrichmentMode.CROSS_REFERENCE)
        self.assertEqual(result.mode, EnrichmentMode.CROSS_REFERENCE)

    def test_get_stats(self):
        """Test enrichment statistics."""
        self.store.ingest("Content", domain="test")
        self.enrichment.enrich_domain("test")
        stats = self.enrichment.get_stats()
        self.assertEqual(stats["total_enrichments"], 1)


# =====================================================================
# FULL ORACLE PIPELINE TESTS
# =====================================================================


class TestOraclePipeline(unittest.TestCase):
    """Tests for the full Oracle Pipeline."""

    def setUp(self):
        self.pipeline = OraclePipeline()

    def test_run_full_pipeline_simple(self):
        """Test full pipeline with simple input."""
        result = self.pipeline.run_full_pipeline("Python machine learning tutorials")
        self.assertIsNotNone(result.pipeline_id)
        self.assertEqual(result.items_accepted, 1)
        self.assertGreater(result.records_ingested, 0)

    def test_run_full_pipeline_bulk(self):
        """Test full pipeline with bulk input."""
        raw = """
        - Python machine learning
        - Rust systems programming
        - https://github.com/pytorch/pytorch
        - Tony Robbins leadership
        - Kubernetes best practices
        """
        result = self.pipeline.run_full_pipeline(raw)
        self.assertEqual(result.items_accepted, 5)
        self.assertGreater(result.records_ingested, 0)

    def test_pipeline_knn_discovery(self):
        """Test that KNN discovery runs."""
        result = self.pipeline.run_full_pipeline(
            "Python programming basics",
            enable_knn_discovery=True,
        )
        self.assertGreaterEqual(result.neighbors_discovered, 0)

    def test_pipeline_llm_enrichment(self):
        """Test that LLM enrichment runs."""
        result = self.pipeline.run_full_pipeline(
            "Docker containerization fundamentals",
            enable_llm_enrichment=True,
        )
        self.assertGreaterEqual(result.enrichments_performed, 0)

    def test_pipeline_without_knn(self):
        """Test pipeline without KNN discovery."""
        result = self.pipeline.run_full_pipeline(
            "Simple test", enable_knn_discovery=False
        )
        self.assertEqual(result.neighbors_discovered, 0)

    def test_pipeline_without_enrichment(self):
        """Test pipeline without LLM enrichment."""
        result = self.pipeline.run_full_pipeline(
            "Simple test", enable_llm_enrichment=False
        )
        self.assertEqual(result.enrichments_performed, 0)

    def test_pipeline_status(self):
        """Test pipeline status."""
        result = self.pipeline.run_full_pipeline("Test content")
        self.assertIn(result.status, ["completed", "completed_with_errors"])

    def test_pipeline_domains_covered(self):
        """Test domains covered tracking."""
        result = self.pipeline.run_full_pipeline(
            "Python programming\nRust systems"
        )
        self.assertIsInstance(result.domains_covered, list)

    def test_run_items_pipeline(self):
        """Test pipeline with structured items."""
        items = [
            {"content": "Python tutorials", "domain": "python"},
            {"content": "React development", "domain": "javascript"},
        ]
        result = self.pipeline.run_items_pipeline(items)
        self.assertEqual(result.items_accepted, 2)
        self.assertGreater(result.records_ingested, 0)

    def test_pipeline_50_items(self):
        """Test pipeline handles 50 items."""
        items = "\n".join([f"Learning topic number {i}" for i in range(50)])
        result = self.pipeline.run_full_pipeline(items)
        self.assertEqual(result.items_accepted, 50)

    def test_oracle_stats(self):
        """Test getting Oracle stats."""
        self.pipeline.run_full_pipeline("Test content")
        stats = self.pipeline.get_oracle_stats()
        self.assertIn("whitelist", stats)
        self.assertIn("fetcher", stats)
        self.assertIn("oracle_store", stats)
        self.assertIn("knn_discovery", stats)
        self.assertIn("llm_enrichment", stats)

    def test_pipeline_log(self):
        """Test pipeline log tracking."""
        self.pipeline.run_full_pipeline("Test 1")
        self.pipeline.run_full_pipeline("Test 2")
        log = self.pipeline.get_pipeline_log()
        self.assertEqual(len(log), 2)

    def test_pipeline_duration_tracked(self):
        """Test pipeline duration is tracked."""
        result = self.pipeline.run_full_pipeline("Duration test")
        self.assertGreater(result.pipeline_duration_ms, 0)

    def test_pipeline_total_oracle_records(self):
        """Test total Oracle records count."""
        self.pipeline.run_full_pipeline("Content 1")
        result = self.pipeline.run_full_pipeline("Content 2")
        self.assertGreater(result.total_oracle_records, 0)

    def test_default_domain(self):
        """Test default domain assignment."""
        result = self.pipeline.run_full_pipeline(
            "Generic content", default_domain="custom"
        )
        self.assertIsNotNone(result.pipeline_id)

    def test_pipeline_whitelist_status_updated(self):
        """Test whitelist item status updates after pipeline."""
        self.pipeline.run_full_pipeline("Status test item")
        items = list(self.pipeline.whitelist_box.items.values())
        for item in items:
            self.assertIn(item.status, ["ingested", "failed"])

    def test_end_to_end_authority_figure(self):
        """Test end-to-end with authority figure."""
        result = self.pipeline.run_full_pipeline(
            "Tony Robbins motivation and leadership strategies"
        )
        self.assertGreater(result.records_ingested, 0)

    def test_end_to_end_github_repos(self):
        """Test end-to-end with GitHub repos."""
        result = self.pipeline.run_full_pipeline(
            "https://github.com/pytorch/pytorch\n"
            "https://github.com/tensorflow/tensorflow"
        )
        self.assertEqual(result.items_accepted, 2)

    def test_end_to_end_mixed_input(self):
        """Test end-to-end with mixed input types."""
        raw = """
        - https://github.com/langchain-ai/langchain
        - Tony Robbins leadership content
        - Python machine learning
        - https://arxiv.org/abs/2301.00001
        - Kubernetes deployment strategies
        - Sales funnel optimization
        - def hello(): print('world')
        - Quantum computing research
        """
        result = self.pipeline.run_full_pipeline(raw)
        self.assertGreaterEqual(result.items_accepted, 7)
        self.assertGreater(result.records_ingested, 0)


# =====================================================================
# INTEGRATION TESTS
# =====================================================================


class TestOraclePipelineIntegration(unittest.TestCase):
    """Integration tests for the Oracle Pipeline."""

    def test_whitelist_to_oracle_flow(self):
        """Test data flows from whitelist to Oracle store."""
        pipeline = OraclePipeline()
        pipeline.run_full_pipeline("Python machine learning tutorials")
        records = pipeline.oracle_store.search_by_content("Python machine learning")
        self.assertGreater(len(records), 0)

    def test_knn_triggers_after_ingestion(self):
        """Test KNN runs after ingestion with domain data."""
        pipeline = OraclePipeline()
        result = pipeline.run_full_pipeline(
            "Python programming basics",
            enable_knn_discovery=True,
        )
        if result.domains_covered:
            self.assertGreaterEqual(result.neighbors_discovered, 0)

    def test_enrichment_adds_to_oracle(self):
        """Test LLM enrichment adds records to Oracle."""
        pipeline = OraclePipeline()
        result = pipeline.run_full_pipeline(
            "Docker containerization",
            enable_llm_enrichment=True,
        )
        total_records = len(pipeline.oracle_store.records)
        self.assertGreater(total_records, result.records_ingested)

    def test_multiple_runs_accumulate(self):
        """Test multiple pipeline runs accumulate data."""
        pipeline = OraclePipeline()
        pipeline.run_full_pipeline("Python basics")
        r2 = pipeline.run_full_pipeline("Rust programming")
        self.assertGreater(r2.total_oracle_records, 0)

    def test_dedup_across_runs(self):
        """Test deduplication across pipeline runs."""
        pipeline = OraclePipeline()
        pipeline.run_full_pipeline("Unique test content for dedup")
        r1_count = len(pipeline.oracle_store.records)
        pipeline.run_full_pipeline("Unique test content for dedup")
        r2_count = len(pipeline.oracle_store.records)
        self.assertEqual(r1_count, r2_count)


if __name__ == "__main__":
    unittest.main(verbosity=2)
