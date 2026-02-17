"""
Multi-Source Fetcher

Takes whitelist items and fetches content from multiple sources:
- Web search (deterministic because user asked for it)
- GitHub API (repos, code, READMEs)
- arXiv API (research papers)
- Direct URL scraping
- File upload handling
- API endpoint calls

Because the user explicitly whitelisted these, all fetched data
starts at 100% trust (deterministic from user standpoint).
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from .whitelist_box import WhitelistItem, WhitelistItemType

logger = logging.getLogger(__name__)


class FetchSource(str, Enum):
    """Sources for fetching data."""
    WEB_SEARCH = "web_search"
    GITHUB_API = "github_api"
    ARXIV_API = "arxiv_api"
    DIRECT_URL = "direct_url"
    FILE_UPLOAD = "file_upload"
    API_ENDPOINT = "api_endpoint"
    LLM_GENERATION = "llm_generation"


class FetchStatus(str, Enum):
    """Status of a fetch operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class FetchResult:
    """Result of fetching content from a source."""
    fetch_id: str
    item_id: str
    source: FetchSource
    status: FetchStatus
    content: str = ""
    title: Optional[str] = None
    url: Optional[str] = None
    content_type: str = "text"
    byte_size: int = 0
    trust_score: float = 1.0
    domain: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List[str] = field(default_factory=list)
    error: Optional[str] = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MultiSourceFetcher:
    """
    Fetches content from multiple sources based on whitelist item type.

    Routing:
    - URL -> Direct URL fetch
    - GitHub repo -> GitHub API (README, code, issues)
    - arXiv paper -> arXiv API (abstract, PDF text)
    - Authority figure -> Web search for their content
    - Topic/Domain -> Web search + GitHub search
    - Code -> GitHub code search
    - File upload -> Local file processing
    - API endpoint -> API call
    - Search query -> Web search
    - Study material -> Web + academic search

    All results get 100% trust because user explicitly requested them.
    """

    TYPE_TO_SOURCE = {
        WhitelistItemType.URL: [FetchSource.DIRECT_URL],
        WhitelistItemType.GITHUB_REPO: [FetchSource.GITHUB_API],
        WhitelistItemType.ARXIV_PAPER: [FetchSource.ARXIV_API],
        WhitelistItemType.AUTHORITY_FIGURE: [FetchSource.WEB_SEARCH, FetchSource.GITHUB_API],
        WhitelistItemType.TOPIC: [FetchSource.WEB_SEARCH],
        WhitelistItemType.DOMAIN: [FetchSource.WEB_SEARCH, FetchSource.GITHUB_API],
        WhitelistItemType.CODE: [FetchSource.GITHUB_API],
        WhitelistItemType.DOCUMENTATION: [FetchSource.WEB_SEARCH, FetchSource.DIRECT_URL],
        WhitelistItemType.FILE_UPLOAD: [FetchSource.FILE_UPLOAD],
        WhitelistItemType.API_ENDPOINT: [FetchSource.API_ENDPOINT],
        WhitelistItemType.SEARCH_QUERY: [FetchSource.WEB_SEARCH],
        WhitelistItemType.STUDY_MATERIAL: [FetchSource.WEB_SEARCH, FetchSource.ARXIV_API],
        WhitelistItemType.SCIENCE_PAPER: [FetchSource.ARXIV_API, FetchSource.WEB_SEARCH],
        WhitelistItemType.BULLET_LIST: [FetchSource.WEB_SEARCH],
        WhitelistItemType.RAW_TEXT: [FetchSource.LLM_GENERATION],
    }

    def __init__(self):
        self.fetch_log: List[FetchResult] = []
        self._handlers: Dict[FetchSource, Any] = {}
        logger.info("[FETCHER] Multi-Source Fetcher initialized")

    def register_handler(self, source: FetchSource, handler: Any) -> None:
        """Register a handler for a fetch source."""
        self._handlers[source] = handler

    def fetch_item(self, item: WhitelistItem) -> List[FetchResult]:
        """
        Fetch content for a whitelist item from appropriate sources.

        Args:
            item: The whitelist item to fetch

        Returns:
            List of FetchResult (one per source tried)
        """
        sources = self.TYPE_TO_SOURCE.get(item.item_type, [FetchSource.WEB_SEARCH])
        results: List[FetchResult] = []

        for source in sources:
            result = self._fetch_from_source(item, source)
            results.append(result)
            self.fetch_log.append(result)

        return results

    def fetch_batch(self, items: List[WhitelistItem]) -> Dict[str, List[FetchResult]]:
        """
        Fetch content for a batch of whitelist items.

        Args:
            items: List of whitelist items

        Returns:
            Dict mapping item_id to list of FetchResults
        """
        batch_results: Dict[str, List[FetchResult]] = {}

        for item in items:
            results = self.fetch_item(item)
            batch_results[item.item_id] = results

        total = sum(len(r) for r in batch_results.values())
        successful = sum(
            1 for results in batch_results.values()
            for r in results if r.status == FetchStatus.COMPLETED
        )
        logger.info(
            f"[FETCHER] Batch fetch: {len(items)} items, "
            f"{total} fetches, {successful} successful"
        )

        return batch_results

    def _fetch_from_source(
        self, item: WhitelistItem, source: FetchSource
    ) -> FetchResult:
        """Fetch from a specific source."""
        if source in self._handlers:
            try:
                handler = self._handlers[source]
                return handler(item)
            except Exception as e:
                logger.warning(f"[FETCHER] Handler for {source.value} failed: {e}")
                return FetchResult(
                    fetch_id=f"fetch-{uuid.uuid4().hex[:12]}",
                    item_id=item.item_id,
                    source=source,
                    status=FetchStatus.FAILED,
                    error=str(e),
                    domain=item.domain,
                )

        # Default fetch simulation (placeholder for real API integrations)
        return self._default_fetch(item, source)

    def _default_fetch(
        self, item: WhitelistItem, source: FetchSource
    ) -> FetchResult:
        """Default fetch handler - processes based on item content."""

        if source == FetchSource.FILE_UPLOAD:
            return self._fetch_file_upload(item)
        elif source == FetchSource.LLM_GENERATION:
            return self._fetch_llm_generation(item)
        elif source == FetchSource.DIRECT_URL:
            return self._fetch_direct_url(item)
        elif source == FetchSource.GITHUB_API:
            return self._fetch_github(item)
        elif source == FetchSource.ARXIV_API:
            return self._fetch_arxiv(item)
        elif source == FetchSource.WEB_SEARCH:
            return self._fetch_web_search(item)
        elif source == FetchSource.API_ENDPOINT:
            return self._fetch_api_endpoint(item)

        return FetchResult(
            fetch_id=f"fetch-{uuid.uuid4().hex[:12]}",
            item_id=item.item_id,
            source=source,
            status=FetchStatus.COMPLETED,
            content=item.content,
            trust_score=item.trust_score,
            domain=item.domain,
            metadata={"source_type": source.value, "simulated": True},
        )

    def _fetch_file_upload(self, item: WhitelistItem) -> FetchResult:
        """Handle file upload items."""
        return FetchResult(
            fetch_id=f"fetch-{uuid.uuid4().hex[:12]}",
            item_id=item.item_id,
            source=FetchSource.FILE_UPLOAD,
            status=FetchStatus.COMPLETED,
            content=item.content,
            content_type="file",
            byte_size=len(item.content.encode("utf-8")),
            trust_score=1.0,
            domain=item.domain,
            metadata={"file_content": True},
        )

    def _fetch_llm_generation(self, item: WhitelistItem) -> FetchResult:
        """Handle LLM-generated content enrichment."""
        return FetchResult(
            fetch_id=f"fetch-{uuid.uuid4().hex[:12]}",
            item_id=item.item_id,
            source=FetchSource.LLM_GENERATION,
            status=FetchStatus.COMPLETED,
            content=item.content,
            content_type="text",
            byte_size=len(item.content.encode("utf-8")),
            trust_score=1.0,
            domain=item.domain,
            metadata={"llm_enrichment_pending": True},
        )

    def _fetch_direct_url(self, item: WhitelistItem) -> FetchResult:
        """Handle direct URL fetching (placeholder for real HTTP)."""
        return FetchResult(
            fetch_id=f"fetch-{uuid.uuid4().hex[:12]}",
            item_id=item.item_id,
            source=FetchSource.DIRECT_URL,
            status=FetchStatus.COMPLETED,
            content=f"[Content from URL: {item.content}]",
            url=item.content,
            trust_score=1.0,
            domain=item.domain,
            metadata={"url": item.content, "needs_real_fetch": True},
        )

    def _fetch_github(self, item: WhitelistItem) -> FetchResult:
        """Handle GitHub API fetch (placeholder)."""
        return FetchResult(
            fetch_id=f"fetch-{uuid.uuid4().hex[:12]}",
            item_id=item.item_id,
            source=FetchSource.GITHUB_API,
            status=FetchStatus.COMPLETED,
            content=f"[GitHub content for: {item.content}]",
            trust_score=1.0,
            domain=item.domain or "code",
            metadata={"github_query": item.content, "needs_real_fetch": True},
        )

    def _fetch_arxiv(self, item: WhitelistItem) -> FetchResult:
        """Handle arXiv API fetch (placeholder)."""
        return FetchResult(
            fetch_id=f"fetch-{uuid.uuid4().hex[:12]}",
            item_id=item.item_id,
            source=FetchSource.ARXIV_API,
            status=FetchStatus.COMPLETED,
            content=f"[arXiv paper: {item.content}]",
            trust_score=1.0,
            domain=item.domain or "science",
            metadata={"arxiv_query": item.content, "needs_real_fetch": True},
        )

    def _fetch_web_search(self, item: WhitelistItem) -> FetchResult:
        """Handle web search fetch (placeholder)."""
        return FetchResult(
            fetch_id=f"fetch-{uuid.uuid4().hex[:12]}",
            item_id=item.item_id,
            source=FetchSource.WEB_SEARCH,
            status=FetchStatus.COMPLETED,
            content=f"[Web search results for: {item.content}]",
            trust_score=1.0,
            domain=item.domain,
            metadata={"search_query": item.content, "needs_real_fetch": True},
        )

    def _fetch_api_endpoint(self, item: WhitelistItem) -> FetchResult:
        """Handle API endpoint fetch (placeholder)."""
        return FetchResult(
            fetch_id=f"fetch-{uuid.uuid4().hex[:12]}",
            item_id=item.item_id,
            source=FetchSource.API_ENDPOINT,
            status=FetchStatus.COMPLETED,
            content=f"[API response from: {item.content}]",
            trust_score=1.0,
            domain=item.domain,
            metadata={"api_endpoint": item.content, "needs_real_fetch": True},
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get fetcher statistics."""
        by_source = {}
        for s in FetchSource:
            count = sum(1 for r in self.fetch_log if r.source == s)
            if count > 0:
                by_source[s.value] = count
        successful = sum(
            1 for r in self.fetch_log if r.status == FetchStatus.COMPLETED
        )
        return {
            "total_fetches": len(self.fetch_log),
            "successful": successful,
            "failed": len(self.fetch_log) - successful,
            "by_source": by_source,
        }
