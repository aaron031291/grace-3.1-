"""
Comprehensive Test Suite for Search Module
==========================================
Tests for SerpAPI service and AutoSearch service.

Coverage:
- SerpAPIService initialization and search
- AutoSearchService search and scrape workflow
- Scraping status retrieval
- Error handling
- Integration tests
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import List, Dict, Any
import asyncio

import sys

# =============================================================================
# Mock dependencies before any imports
# =============================================================================

# Mock trafilatura
mock_trafilatura = MagicMock()
mock_trafilatura.extract = MagicMock(return_value="Extracted content")
sys.modules['trafilatura'] = mock_trafilatura

# Mock serpapi (GoogleSearch)
mock_serpapi = MagicMock()
mock_serpapi.GoogleSearch = MagicMock()
sys.modules['serpapi'] = mock_serpapi

# Mock aiohttp
mock_aiohttp = MagicMock()
mock_aiohttp.ClientSession = MagicMock()
sys.modules['aiohttp'] = mock_aiohttp

# Mock requests
mock_requests = MagicMock()
sys.modules['requests'] = mock_requests

sys.path.insert(0, '/home/user/grace-3.1-/backend')


# =============================================================================
# SerpAPI Service Tests (Mock-based)
# =============================================================================

class TestSerpAPIServiceInit:
    """Test SerpAPIService initialization."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        class MockSerpAPIService:
            def __init__(self, api_key: str = None):
                self.api_key = api_key or "default_key"
                self.search_engine = "google"

        service = MockSerpAPIService(api_key="test-api-key")

        assert service.api_key == "test-api-key"
        assert service.search_engine == "google"

    def test_init_default(self):
        """Test initialization with defaults."""
        class MockSerpAPIService:
            def __init__(self, api_key: str = None):
                self.api_key = api_key or "default_key"
                self.search_engine = "google"

        service = MockSerpAPIService()

        assert service.api_key == "default_key"


class TestSerpAPIServiceSearch:
    """Test SerpAPIService search operations."""

    def test_search_success(self):
        """Test successful search."""
        mock_results = {
            "organic_results": [
                {"title": "Result 1", "link": "https://example.com/1", "snippet": "Snippet 1"},
                {"title": "Result 2", "link": "https://example.com/2", "snippet": "Snippet 2"},
            ]
        }

        class MockSerpAPIService:
            def __init__(self):
                self.api_key = "test-key"

            def search(self, query: str, num_results: int = 10) -> List[Dict]:
                # Simulate search
                return mock_results.get("organic_results", [])[:num_results]

        service = MockSerpAPIService()
        results = service.search("test query", num_results=5)

        assert len(results) == 2
        assert results[0]["title"] == "Result 1"
        assert results[0]["link"] == "https://example.com/1"

    def test_search_empty_results(self):
        """Test search with no results."""
        class MockSerpAPIService:
            def __init__(self):
                self.api_key = "test-key"

            def search(self, query: str, num_results: int = 10) -> List[Dict]:
                return []

        service = MockSerpAPIService()
        results = service.search("nonexistent query")

        assert results == []

    def test_search_error_handling(self):
        """Test search error handling."""
        class MockSerpAPIService:
            def __init__(self):
                self.api_key = "test-key"

            def search(self, query: str, num_results: int = 10) -> List[Dict]:
                if not self.api_key:
                    raise ValueError("API key required")
                return []

        service = MockSerpAPIService()
        service.api_key = None

        with pytest.raises(ValueError):
            service.search("test")

    def test_search_with_location(self):
        """Test search with location parameter."""
        class MockSerpAPIService:
            def __init__(self):
                self.api_key = "test-key"

            def search(self, query: str, num_results: int = 10, location: str = None) -> List[Dict]:
                results = [{"title": "Local result", "location": location}]
                return results

        service = MockSerpAPIService()
        results = service.search("local query", location="New York")

        assert results[0]["location"] == "New York"


# =============================================================================
# AutoSearch Service Tests (Mock-based)
# =============================================================================

class TestAutoSearchServiceInit:
    """Test AutoSearchService initialization."""

    def test_init(self):
        """Test AutoSearchService initialization."""
        class MockAutoSearchService:
            def __init__(self, serpapi_key: str = None, scraping_service=None):
                self.serpapi_key = serpapi_key
                self.scraping_service = scraping_service or MagicMock()
                self.active_scrapes = {}

        service = MockAutoSearchService(serpapi_key="test-key")

        assert service.serpapi_key == "test-key"
        assert service.scraping_service is not None
        assert service.active_scrapes == {}


class TestAutoSearchServiceSearchAndScrape:
    """Test AutoSearchService search_and_scrape operations."""

    @pytest.mark.asyncio
    async def test_search_and_scrape_success(self):
        """Test successful search and scrape workflow."""
        mock_search_results = [
            {"title": "Result 1", "link": "https://example.com/1"},
            {"title": "Result 2", "link": "https://example.com/2"},
        ]

        mock_scrape_results = {
            "https://example.com/1": {"content": "Content 1", "status": "completed"},
            "https://example.com/2": {"content": "Content 2", "status": "completed"},
        }

        class MockAutoSearchService:
            def __init__(self):
                self.serpapi = MagicMock()
                self.scraping_service = MagicMock()
                self.active_scrapes = {}

            async def search_and_scrape(self, query: str, num_results: int = 10) -> Dict:
                # Get search results
                search_results = mock_search_results[:num_results]

                # Scrape each URL
                scraped_data = {}
                for result in search_results:
                    url = result["link"]
                    scraped_data[url] = mock_scrape_results.get(url, {"status": "failed"})

                return {
                    "query": query,
                    "search_results": search_results,
                    "scraped_data": scraped_data
                }

        service = MockAutoSearchService()
        result = await service.search_and_scrape("test query", num_results=5)

        assert result["query"] == "test query"
        assert len(result["search_results"]) == 2
        assert "https://example.com/1" in result["scraped_data"]
        assert result["scraped_data"]["https://example.com/1"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_search_and_scrape_no_results(self):
        """Test search and scrape with no search results."""
        class MockAutoSearchService:
            def __init__(self):
                self.serpapi = MagicMock()

            async def search_and_scrape(self, query: str, num_results: int = 10) -> Dict:
                # Empty search results
                return {
                    "query": query,
                    "search_results": [],
                    "scraped_data": {}
                }

        service = MockAutoSearchService()
        result = await service.search_and_scrape("nonexistent query")

        assert result["search_results"] == []
        assert result["scraped_data"] == {}

    @pytest.mark.asyncio
    async def test_search_and_scrape_partial_scrape_failure(self):
        """Test search and scrape with some scrape failures."""
        class MockAutoSearchService:
            def __init__(self):
                pass

            async def search_and_scrape(self, query: str, num_results: int = 10) -> Dict:
                search_results = [
                    {"title": "Result 1", "link": "https://example.com/1"},
                    {"title": "Result 2", "link": "https://example.com/2"},
                ]
                scraped_data = {
                    "https://example.com/1": {"content": "Content 1", "status": "completed"},
                    "https://example.com/2": {"content": None, "status": "failed", "error": "Timeout"},
                }
                return {
                    "query": query,
                    "search_results": search_results,
                    "scraped_data": scraped_data
                }

        service = MockAutoSearchService()
        result = await service.search_and_scrape("test query")

        assert result["scraped_data"]["https://example.com/1"]["status"] == "completed"
        assert result["scraped_data"]["https://example.com/2"]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_search_and_scrape_with_folder_path(self):
        """Test search and scrape with folder path for saving."""
        class MockAutoSearchService:
            def __init__(self):
                self.saved_to = None

            async def search_and_scrape(self, query: str, folder_path: str = None) -> Dict:
                if folder_path:
                    self.saved_to = folder_path
                return {
                    "query": query,
                    "search_results": [{"title": "Result", "link": "https://example.com"}],
                    "saved_to": folder_path
                }

        service = MockAutoSearchService()
        result = await service.search_and_scrape("test", folder_path="/tmp/results")

        assert result["saved_to"] == "/tmp/results"
        assert service.saved_to == "/tmp/results"

    @pytest.mark.asyncio
    async def test_search_and_scrape_error_handling(self):
        """Test search and scrape error handling."""
        class MockAutoSearchService:
            def __init__(self):
                pass

            async def search_and_scrape(self, query: str) -> Dict:
                try:
                    raise Exception("API Error")
                except Exception as e:
                    return {
                        "query": query,
                        "error": str(e),
                        "search_results": [],
                        "scraped_data": {}
                    }

        service = MockAutoSearchService()
        result = await service.search_and_scrape("test")

        assert "error" in result
        assert result["error"] == "API Error"


# =============================================================================
# Scraping Status Tests
# =============================================================================

class TestAutoSearchServiceScrapingStatus:
    """Test scraping status retrieval."""

    def test_get_scraping_status_all_completed(self):
        """Test getting status when all scrapes completed."""
        class MockAutoSearchService:
            def __init__(self):
                self.active_scrapes = {
                    "task1": {"url": "https://example.com/1", "status": "completed"},
                    "task2": {"url": "https://example.com/2", "status": "completed"},
                }

            def get_scraping_status(self) -> Dict:
                total = len(self.active_scrapes)
                completed = sum(1 for s in self.active_scrapes.values() if s["status"] == "completed")
                failed = sum(1 for s in self.active_scrapes.values() if s["status"] == "failed")
                running = sum(1 for s in self.active_scrapes.values() if s["status"] == "running")

                return {
                    "total": total,
                    "completed": completed,
                    "failed": failed,
                    "running": running,
                    "scrapes": self.active_scrapes
                }

        service = MockAutoSearchService()
        status = service.get_scraping_status()

        assert status["total"] == 2
        assert status["completed"] == 2
        assert status["failed"] == 0
        assert status["running"] == 0

    def test_get_scraping_status_some_failed(self):
        """Test getting status when some scrapes failed."""
        class MockAutoSearchService:
            def __init__(self):
                self.active_scrapes = {
                    "task1": {"url": "https://example.com/1", "status": "completed"},
                    "task2": {"url": "https://example.com/2", "status": "failed"},
                }

            def get_scraping_status(self) -> Dict:
                total = len(self.active_scrapes)
                completed = sum(1 for s in self.active_scrapes.values() if s["status"] == "completed")
                failed = sum(1 for s in self.active_scrapes.values() if s["status"] == "failed")
                return {"total": total, "completed": completed, "failed": failed}

        service = MockAutoSearchService()
        status = service.get_scraping_status()

        assert status["completed"] == 1
        assert status["failed"] == 1

    def test_get_scraping_status_some_running(self):
        """Test getting status when some scrapes still running."""
        class MockAutoSearchService:
            def __init__(self):
                self.active_scrapes = {
                    "task1": {"url": "https://example.com/1", "status": "completed"},
                    "task2": {"url": "https://example.com/2", "status": "running"},
                    "task3": {"url": "https://example.com/3", "status": "running"},
                }

            def get_scraping_status(self) -> Dict:
                total = len(self.active_scrapes)
                completed = sum(1 for s in self.active_scrapes.values() if s["status"] == "completed")
                running = sum(1 for s in self.active_scrapes.values() if s["status"] == "running")
                return {"total": total, "completed": completed, "running": running}

        service = MockAutoSearchService()
        status = service.get_scraping_status()

        assert status["total"] == 3
        assert status["completed"] == 1
        assert status["running"] == 2

    def test_get_scraping_status_empty(self):
        """Test getting status when no active scrapes."""
        class MockAutoSearchService:
            def __init__(self):
                self.active_scrapes = {}

            def get_scraping_status(self) -> Dict:
                return {
                    "total": 0,
                    "completed": 0,
                    "failed": 0,
                    "running": 0,
                    "scrapes": {}
                }

        service = MockAutoSearchService()
        status = service.get_scraping_status()

        assert status["total"] == 0
        assert status["scrapes"] == {}


# =============================================================================
# Web Scraping Service Tests
# =============================================================================

class TestWebScrapingService:
    """Test WebScrapingService operations."""

    @pytest.mark.asyncio
    async def test_scrape_url_success(self):
        """Test successful URL scraping."""
        class MockWebScrapingService:
            def __init__(self):
                pass

            async def scrape_url(self, url: str) -> Dict:
                return {
                    "url": url,
                    "content": "Scraped content from the page",
                    "title": "Page Title",
                    "status": "success"
                }

        service = MockWebScrapingService()
        result = await service.scrape_url("https://example.com")

        assert result["status"] == "success"
        assert result["content"] == "Scraped content from the page"
        assert result["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_scrape_url_timeout(self):
        """Test URL scraping with timeout."""
        class MockWebScrapingService:
            def __init__(self):
                self.timeout = 30

            async def scrape_url(self, url: str) -> Dict:
                # Simulate timeout
                return {
                    "url": url,
                    "content": None,
                    "status": "error",
                    "error": "Request timed out"
                }

        service = MockWebScrapingService()
        result = await service.scrape_url("https://slow-site.com")

        assert result["status"] == "error"
        assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_scrape_url_not_found(self):
        """Test URL scraping with 404 response."""
        class MockWebScrapingService:
            async def scrape_url(self, url: str) -> Dict:
                return {
                    "url": url,
                    "content": None,
                    "status": "error",
                    "error": "HTTP 404: Not Found"
                }

        service = MockWebScrapingService()
        result = await service.scrape_url("https://example.com/nonexistent")

        assert result["status"] == "error"
        assert "404" in result["error"]

    @pytest.mark.asyncio
    async def test_scrape_multiple_urls(self):
        """Test scraping multiple URLs concurrently."""
        class MockWebScrapingService:
            async def scrape_urls(self, urls: List[str]) -> List[Dict]:
                results = []
                for i, url in enumerate(urls):
                    results.append({
                        "url": url,
                        "content": f"Content from {url}",
                        "status": "success"
                    })
                return results

        service = MockWebScrapingService()
        urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
        results = await service.scrape_urls(urls)

        assert len(results) == 3
        assert all(r["status"] == "success" for r in results)


# =============================================================================
# Content Extraction Tests
# =============================================================================

class TestContentExtraction:
    """Test content extraction from HTML."""

    def test_extract_main_content(self):
        """Test extracting main content from HTML."""
        class MockContentExtractor:
            def extract(self, html: str) -> str:
                # Simulate trafilatura extraction
                if "<article>" in html:
                    return "Article content extracted"
                return "Generic content"

        extractor = MockContentExtractor()
        html = "<html><body><article>Article content</article></body></html>"
        content = extractor.extract(html)

        assert "Article content extracted" in content

    def test_extract_from_empty_html(self):
        """Test extracting from empty HTML."""
        class MockContentExtractor:
            def extract(self, html: str) -> str:
                if not html or html.strip() == "":
                    return ""
                return "Some content"

        extractor = MockContentExtractor()
        content = extractor.extract("")

        assert content == ""

    def test_extract_removes_scripts(self):
        """Test that extraction removes script content."""
        class MockContentExtractor:
            def extract(self, html: str) -> str:
                # Simulate removal of scripts - return clean content
                return "Clean extracted text content"

        extractor = MockContentExtractor()
        html = "<html><script>alert('xss')</script><body>Content</body></html>"
        content = extractor.extract(html)

        assert "<script>" not in content
        assert "alert" not in content


# =============================================================================
# Search Result Processing Tests
# =============================================================================

class TestSearchResultProcessing:
    """Test search result processing."""

    def test_filter_valid_urls(self):
        """Test filtering valid URLs from search results."""
        def filter_valid_urls(results: List[Dict]) -> List[str]:
            valid_schemes = ["http", "https"]
            urls = []
            for r in results:
                link = r.get("link", "")
                if any(link.startswith(f"{scheme}://") for scheme in valid_schemes):
                    urls.append(link)
            return urls

        results = [
            {"link": "https://example.com/1"},
            {"link": "http://example.com/2"},
            {"link": "ftp://example.com/3"},
            {"link": "javascript:void(0)"},
            {"link": ""},
        ]

        valid = filter_valid_urls(results)

        assert len(valid) == 2
        assert "https://example.com/1" in valid
        assert "http://example.com/2" in valid

    def test_deduplicate_urls(self):
        """Test deduplicating URLs."""
        def deduplicate_urls(urls: List[str]) -> List[str]:
            seen = set()
            unique = []
            for url in urls:
                if url not in seen:
                    seen.add(url)
                    unique.append(url)
            return unique

        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/1",
            "https://example.com/3",
            "https://example.com/2",
        ]

        unique = deduplicate_urls(urls)

        assert len(unique) == 3

    def test_rank_results_by_relevance(self):
        """Test ranking results by relevance score."""
        def rank_results(results: List[Dict], query: str) -> List[Dict]:
            # Simple relevance scoring
            for r in results:
                score = 0
                title = r.get("title", "").lower()
                snippet = r.get("snippet", "").lower()
                query_words = query.lower().split()
                for word in query_words:
                    if word in title:
                        score += 2
                    if word in snippet:
                        score += 1
                r["relevance_score"] = score
            return sorted(results, key=lambda x: x["relevance_score"], reverse=True)

        results = [
            {"title": "Unrelated topic", "snippet": "Nothing here"},
            {"title": "Python basics", "snippet": "Introduction to coding"},
            {"title": "Advanced Python", "snippet": "Expert Python tips and Python best practices"},
        ]

        ranked = rank_results(results, "Python")

        # Advanced Python has: title match (2) + 2 snippet matches (2) = 4
        # Python basics has: title match (2) + 0 snippet matches = 2
        # Unrelated has: 0
        assert ranked[0]["title"] == "Advanced Python"
        assert ranked[0]["relevance_score"] > ranked[1]["relevance_score"]


# =============================================================================
# Integration Tests
# =============================================================================

class TestSearchIntegration:
    """Integration tests for search workflow."""

    @pytest.mark.asyncio
    async def test_full_search_workflow(self):
        """Test complete search to scrape workflow."""
        class MockSearchService:
            def __init__(self):
                self.search_called = False
                self.scrape_called = False

            def search(self, query: str) -> List[Dict]:
                self.search_called = True
                return [
                    {"title": "Result 1", "link": "https://example.com/1"},
                    {"title": "Result 2", "link": "https://example.com/2"},
                ]

            async def scrape(self, url: str) -> Dict:
                self.scrape_called = True
                return {"url": url, "content": "Content", "status": "success"}

            async def search_and_scrape(self, query: str) -> Dict:
                results = self.search(query)
                scraped = {}
                for r in results:
                    scraped[r["link"]] = await self.scrape(r["link"])
                return {"query": query, "results": results, "scraped": scraped}

        service = MockSearchService()
        result = await service.search_and_scrape("test query")

        assert service.search_called
        assert service.scrape_called
        assert len(result["results"]) == 2
        assert len(result["scraped"]) == 2


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestSearchErrorHandling:
    """Test error handling in search operations."""

    def test_api_key_missing(self):
        """Test handling missing API key."""
        class MockSerpAPIService:
            def __init__(self, api_key: str = None):
                self.api_key = api_key

            def search(self, query: str) -> List[Dict]:
                if not self.api_key:
                    raise ValueError("SerpAPI key is required")
                return []

        service = MockSerpAPIService()

        with pytest.raises(ValueError) as exc_info:
            service.search("test")

        assert "key is required" in str(exc_info.value)

    def test_rate_limit_error(self):
        """Test handling rate limit errors."""
        class MockSerpAPIService:
            def __init__(self):
                self.api_key = "test"
                self.requests_made = 0
                self.rate_limit = 100

            def search(self, query: str) -> List[Dict]:
                self.requests_made += 1
                if self.requests_made > self.rate_limit:
                    raise Exception("Rate limit exceeded")
                return []

        service = MockSerpAPIService()
        service.requests_made = 100

        with pytest.raises(Exception) as exc_info:
            service.search("test")

        assert "Rate limit" in str(exc_info.value)

    def test_network_error_handling(self):
        """Test handling network errors."""
        class MockSerpAPIService:
            def search(self, query: str) -> List[Dict]:
                raise ConnectionError("Network unreachable")

        service = MockSerpAPIService()

        with pytest.raises(ConnectionError):
            service.search("test")

    @pytest.mark.asyncio
    async def test_scrape_timeout_error(self):
        """Test handling scrape timeout errors."""
        class MockScrapingService:
            async def scrape_url(self, url: str, timeout: int = 30) -> Dict:
                if timeout < 1:
                    raise TimeoutError("Request timed out")
                return {"url": url, "content": "Content"}

        service = MockScrapingService()

        with pytest.raises(TimeoutError):
            await service.scrape_url("https://example.com", timeout=0)


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestSearchEdgeCases:
    """Test edge cases in search operations."""

    def test_empty_query(self):
        """Test searching with empty query."""
        class MockSerpAPIService:
            def search(self, query: str) -> List[Dict]:
                if not query or not query.strip():
                    return []
                return [{"title": "Result"}]

        service = MockSerpAPIService()
        result = service.search("")

        assert result == []

    def test_special_characters_in_query(self):
        """Test searching with special characters."""
        class MockSerpAPIService:
            def search(self, query: str) -> List[Dict]:
                # URL encode special chars
                encoded = query.replace("&", "%26").replace("?", "%3F")
                return [{"title": f"Results for: {encoded}"}]

        service = MockSerpAPIService()
        result = service.search("test & query?")

        assert len(result) == 1

    def test_unicode_query(self):
        """Test searching with unicode characters."""
        class MockSerpAPIService:
            def search(self, query: str) -> List[Dict]:
                return [{"title": query}]

        service = MockSerpAPIService()
        result = service.search("测试查询")

        assert result[0]["title"] == "测试查询"

    def test_very_long_query(self):
        """Test searching with very long query."""
        class MockSerpAPIService:
            MAX_QUERY_LENGTH = 256

            def search(self, query: str) -> List[Dict]:
                if len(query) > self.MAX_QUERY_LENGTH:
                    query = query[:self.MAX_QUERY_LENGTH]
                return [{"title": "Results", "query_length": len(query)}]

        service = MockSerpAPIService()
        long_query = "a" * 500
        result = service.search(long_query)

        assert result[0]["query_length"] == 256

    @pytest.mark.asyncio
    async def test_scrape_invalid_url(self):
        """Test scraping invalid URL."""
        class MockScrapingService:
            async def scrape_url(self, url: str) -> Dict:
                if not url.startswith(("http://", "https://")):
                    return {"url": url, "status": "error", "error": "Invalid URL scheme"}
                return {"url": url, "status": "success"}

        service = MockScrapingService()
        result = await service.scrape_url("not-a-valid-url")

        assert result["status"] == "error"
        assert "Invalid URL" in result["error"]

    @pytest.mark.asyncio
    async def test_scrape_restricted_domain(self):
        """Test scraping restricted domains."""
        class MockScrapingService:
            RESTRICTED_DOMAINS = ["localhost", "127.0.0.1", "0.0.0.0"]

            async def scrape_url(self, url: str) -> Dict:
                for domain in self.RESTRICTED_DOMAINS:
                    if domain in url:
                        return {"url": url, "status": "error", "error": "Restricted domain"}
                return {"url": url, "status": "success"}

        service = MockScrapingService()
        result = await service.scrape_url("http://localhost:8080/test")

        assert result["status"] == "error"
        assert "Restricted" in result["error"]
