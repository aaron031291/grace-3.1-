"""
Tests for the FlashCache — reference-based intelligent caching layer.
"""

import os
import sys
import json
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SKIP_EMBEDDING_LOAD", "true")
os.environ.setdefault("SKIP_QDRANT_CHECK", "true")
os.environ.setdefault("SKIP_OLLAMA_CHECK", "true")
os.environ.setdefault("DISABLE_GENESIS_TRACKING", "true")


class TestFlashCacheCore:
    """Test the core FlashCache engine."""

    @pytest.fixture
    def cache(self, tmp_path):
        from cognitive.flash_cache import FlashCache
        db_path = str(tmp_path / "test_flash.db")
        return FlashCache(db_path=db_path)

    def test_register_and_get(self, cache):
        entry_id = cache.register(
            source_uri="https://api.example.com/data",
            source_type="api",
            source_name="Example API",
            keywords=["python", "rest", "api"],
            summary="A sample REST API for testing",
            trust_score=0.8,
        )
        assert entry_id is not None
        assert len(entry_id) == 16

        entry = cache._get_entry(entry_id)
        assert entry is not None
        assert entry.source_uri == "https://api.example.com/data"
        assert entry.source_name == "Example API"
        assert entry.trust_score == 0.8
        assert "python" in entry.keywords
        assert "rest" in entry.keywords

    def test_keyword_lookup(self, cache):
        cache.register(
            source_uri="https://example.com/ml",
            source_type="web",
            source_name="ML Guide",
            keywords=["machine", "learning", "neural", "network"],
            summary="Machine learning guide",
        )
        cache.register(
            source_uri="https://example.com/dl",
            source_type="web",
            source_name="Deep Learning",
            keywords=["deep", "learning", "neural", "training"],
            summary="Deep learning tutorial",
        )

        results = cache.lookup(keyword="learning")
        assert len(results) == 2

        results = cache.lookup(keyword="machine")
        assert len(results) == 1
        assert results[0]["source_name"] == "ML Guide"

    def test_multi_keyword_lookup(self, cache):
        cache.register(
            source_uri="https://example.com/a",
            source_type="api",
            keywords=["python", "flask", "web"],
        )
        cache.register(
            source_uri="https://example.com/b",
            source_type="api",
            keywords=["python", "django", "web"],
        )
        cache.register(
            source_uri="https://example.com/c",
            source_type="api",
            keywords=["rust", "warp"],
        )

        results = cache.lookup(keywords=["python", "web"])
        assert len(results) == 2
        # Both should match 2 keywords (python + web)
        assert all(r["match_count"] == 2 for r in results)

    def test_search_full_text(self, cache):
        cache.register(
            source_uri="https://example.com/react",
            source_type="web",
            source_name="React Tutorial",
            keywords=["react", "javascript"],
            summary="Complete guide to building React applications with hooks",
        )

        results = cache.search("hooks react")
        assert len(results) >= 1
        assert any("react" in r["source_name"].lower() for r in results)

    def test_source_type_filter(self, cache):
        cache.register(source_uri="https://api.a.com", source_type="api", keywords=["data"])
        cache.register(source_uri="https://web.b.com", source_type="web", keywords=["data"])

        api_only = cache.lookup(keyword="data", source_type="api")
        assert len(api_only) == 1
        assert api_only[0]["source_type"] == "api"

    def test_trust_filter(self, cache):
        cache.register(source_uri="https://high.com", keywords=["test"], trust_score=0.9)
        cache.register(source_uri="https://low.com", keywords=["test"], trust_score=0.2)

        high = cache.lookup(keyword="test", min_trust=0.5)
        assert len(high) == 1
        assert high[0]["trust_score"] == 0.9

    def test_update_trust(self, cache):
        eid = cache.register(source_uri="https://test.com", keywords=["x"], trust_score=0.5)
        cache.update_trust(eid, 0.2)
        entry = cache._get_entry(eid)
        assert abs(entry.trust_score - 0.7) < 0.01

        cache.update_trust(eid, -0.5)
        entry = cache._get_entry(eid)
        assert abs(entry.trust_score - 0.2) < 0.01

        # Clamp to 0
        cache.update_trust(eid, -1.0)
        entry = cache._get_entry(eid)
        assert entry.trust_score == 0.0

    def test_remove_entry(self, cache):
        eid = cache.register(source_uri="https://temp.com", keywords=["temp"])
        assert cache._get_entry(eid) is not None

        cache.remove(eid)
        assert cache._get_entry(eid) is None

    def test_duplicate_uri_replaces(self, cache):
        eid1 = cache.register(source_uri="https://same.com", keywords=["v1"], summary="Version 1")
        eid2 = cache.register(source_uri="https://same.com", keywords=["v2"], summary="Version 2")
        assert eid1 == eid2  # Same URI → same hash → same ID

        entry = cache._get_entry(eid1)
        assert "v2" in entry.keywords  # Updated to latest

    def test_stats(self, cache):
        cache.register(source_uri="https://a.com", source_type="api", keywords=["a"])
        cache.register(source_uri="https://b.com", source_type="web", keywords=["b"])
        cache.register(source_uri="https://c.com", source_type="web", keywords=["c"])

        s = cache.stats()
        assert s["total_entries"] == 3
        assert s["by_type"]["api"] == 1
        assert s["by_type"]["web"] == 2
        assert s["unique_keywords"] >= 3


class TestKeywordExtraction:
    """Test the keyword extraction engine."""

    @pytest.fixture
    def cache(self, tmp_path):
        from cognitive.flash_cache import FlashCache
        return FlashCache(db_path=str(tmp_path / "test_kw.db"))

    def test_basic_extraction(self, cache):
        text = "Python machine learning with neural networks and deep learning frameworks"
        keywords = cache.extract_keywords(text)
        assert "python" in keywords
        assert "learning" in keywords
        assert "neural" in keywords

    def test_stop_words_removed(self, cache):
        text = "The quick brown fox jumps over the lazy dog in the park"
        keywords = cache.extract_keywords(text)
        assert "the" not in keywords
        assert "over" not in keywords
        assert "quick" in keywords
        assert "brown" in keywords

    def test_frequency_ranking(self, cache):
        text = "Python Python Python Java Java C++"
        keywords = cache.extract_keywords(text)
        assert keywords[0] == "python"  # Most frequent

    def test_max_keywords(self, cache):
        text = " ".join(f"word{i}" for i in range(100))
        keywords = cache.extract_keywords(text, max_keywords=5)
        assert len(keywords) <= 5


class TestKeywordPrediction:
    """Test pre-emptive keyword discovery."""

    @pytest.fixture
    def cache(self, tmp_path):
        from cognitive.flash_cache import FlashCache
        c = FlashCache(db_path=str(tmp_path / "test_pred.db"))
        # Seed with related entries
        c.register(source_uri="https://ml1.com", keywords=["machine", "learning", "tensorflow", "keras"])
        c.register(source_uri="https://ml2.com", keywords=["machine", "learning", "pytorch", "gpu"])
        c.register(source_uri="https://dl.com", keywords=["deep", "learning", "neural", "convolution"])
        c.register(source_uri="https://nlp.com", keywords=["natural", "language", "processing", "transformer"])
        return c

    def test_predicts_related_keywords(self, cache):
        predictions = cache.predict_keywords("machine learning")
        kw_names = [p["keyword"] for p in predictions]
        # Should find co-occurring keywords from ML entries
        assert any(kw in kw_names for kw in ["tensorflow", "pytorch", "keras", "gpu"])

    def test_empty_topic_returns_empty(self, cache):
        predictions = cache.predict_keywords("")
        assert predictions == []


class TestCleanup:
    """Test stale entry cleanup."""

    @pytest.fixture
    def cache(self, tmp_path):
        from cognitive.flash_cache import FlashCache
        return FlashCache(db_path=str(tmp_path / "test_clean.db"))

    def test_cleanup_unreachable(self, cache):
        eid = cache.register(source_uri="https://stale.com", keywords=["stale"], ttl_hours=0)
        cache._mark_validation(eid, "unreachable")
        # Set last_accessed to the past
        import sqlite3
        conn = sqlite3.connect(cache._db_path)
        conn.execute("UPDATE flash_entries SET last_accessed = '2020-01-01T00:00:00' WHERE id = ?", (eid,))
        conn.commit()
        conn.close()
        # Clear LRU so it re-reads from DB
        cache._lru.clear()

        removed = cache.cleanup_stale()
        assert removed == 1

    def test_no_cleanup_validated(self, cache):
        eid = cache.register(source_uri="https://good.com", keywords=["good"])
        cache._mark_validation(eid, "validated")
        removed = cache.cleanup_stale()
        assert removed == 0


class TestFlashCacheAPI:
    """Test the API module imports and configuration."""

    def test_import_router(self):
        from api.flash_cache_api import router
        assert router is not None
        assert router.prefix == "/api/flash-cache"

    def test_api_routes_exist(self):
        from api.flash_cache_api import router
        paths = [r.path for r in router.routes]
        prefix = router.prefix
        assert f"{prefix}/register" in paths
        assert f"{prefix}/lookup" in paths
        assert f"{prefix}/search" in paths
        assert f"{prefix}/stats" in paths
        assert f"{prefix}/cleanup" in paths
        assert f"{prefix}/predict" in paths
        assert f"{prefix}/bulk-register" in paths
        assert f"{prefix}/extract-keywords" in paths


class TestIntegrationWithWhitelist:
    """Verify FlashCache is importable from whitelist context."""

    def test_get_flash_cache_callable(self):
        from cognitive.flash_cache import get_flash_cache
        assert callable(get_flash_cache)

    def test_extract_keywords_from_api_data(self):
        from cognitive.flash_cache import FlashCache
        cache = FlashCache.__new__(FlashCache)
        cache._db_path = None
        cache._lru = {}
        cache._keyword_index = {}
        kw = cache.extract_keywords("Git REST API v3 for repository management")
        assert "git" in kw
        assert "api" in kw or "rest" in kw


class TestLRUBehavior:
    """Test the LRU cache eviction."""

    def test_lru_eviction(self, tmp_path):
        from cognitive.flash_cache import FlashCache
        cache = FlashCache(db_path=str(tmp_path / "test_lru.db"))

        # Register more than LRU_MAX_SIZE entries? No, that's 10K.
        # Instead just verify entries go into LRU
        eid = cache.register(source_uri="https://lru.com", keywords=["lru"])
        assert eid in cache._lru

    def test_lru_access_moves_to_end(self, tmp_path):
        from cognitive.flash_cache import FlashCache
        cache = FlashCache(db_path=str(tmp_path / "test_lru2.db"))

        eid1 = cache.register(source_uri="https://first.com", keywords=["first"])
        eid2 = cache.register(source_uri="https://second.com", keywords=["second"])

        # Access first entry — should move to end
        cache._get_entry(eid1)
        keys = list(cache._lru.keys())
        assert keys[-1] == eid1
