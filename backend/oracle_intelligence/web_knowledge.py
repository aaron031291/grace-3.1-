"""
Web Knowledge Integration for Oracle
======================================

Gives the Oracle real-time access to web knowledge:
1. Web search for current information
2. Documentation lookups (Python, JS, frameworks)
3. GitHub repository analysis
4. StackOverflow solution search
5. Security vulnerability databases
6. Best practices and patterns

Enables Grace to stay current and learn from the global
software engineering knowledge base.
"""

import logging
import asyncio
import aiohttp
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import urllib.parse

logger = logging.getLogger(__name__)


class KnowledgeSource(str, Enum):
    """Sources of web knowledge."""
    WEB_SEARCH = "web_search"
    GITHUB = "github"
    STACKOVERFLOW = "stackoverflow"
    DOCUMENTATION = "documentation"
    SECURITY_DB = "security_db"
    PACKAGE_REGISTRY = "package_registry"
    BEST_PRACTICES = "best_practices"


class DocumentationType(str, Enum):
    """Types of documentation to fetch."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    REACT = "react"
    FASTAPI = "fastapi"
    DJANGO = "django"
    NODEJS = "nodejs"
    RUST = "rust"
    GO = "go"


@dataclass
class WebKnowledge:
    """A piece of knowledge from the web."""
    knowledge_id: str
    source: KnowledgeSource
    title: str
    content: str
    url: Optional[str] = None
    relevance_score: float = 0.0
    verified: bool = False
    code_examples: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    cached_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    genesis_key_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "source": self.source.value,
            "title": self.title,
            "content": self.content[:500],
            "url": self.url,
            "relevance_score": self.relevance_score,
            "verified": self.verified,
            "code_examples": self.code_examples[:3],
            "tags": self.tags,
            "cached_at": self.cached_at.isoformat()
        }


@dataclass
class SecurityVulnerability:
    """A security vulnerability from databases."""
    cve_id: str
    severity: str  # low, medium, high, critical
    description: str
    affected_packages: List[str]
    fixed_versions: List[str]
    references: List[str]
    published_date: Optional[datetime] = None


class WebKnowledgeIntegration:
    """
    Web knowledge integration for real-time learning.

    Provides access to:
    - Web search results
    - Official documentation
    - GitHub code examples
    - StackOverflow solutions
    - Security vulnerability databases
    - Package registries
    """

    def __init__(
        self,
        session=None,
        genesis_service=None,
        cache_ttl_hours: int = 24
    ):
        self.session = session
        self._genesis_service = genesis_service
        self.cache_ttl = timedelta(hours=cache_ttl_hours)

        # Knowledge cache
        self._cache: Dict[str, WebKnowledge] = {}

        # Rate limiting
        self._rate_limits = {
            KnowledgeSource.GITHUB: {"calls": 0, "reset_at": datetime.utcnow()},
            KnowledgeSource.STACKOVERFLOW: {"calls": 0, "reset_at": datetime.utcnow()},
        }

        # API endpoints
        self._endpoints = {
            "github_api": "https://api.github.com",
            "stackoverflow_api": "https://api.stackexchange.com/2.3",
            "pypi_api": "https://pypi.org/pypi",
            "npm_api": "https://registry.npmjs.org",
            "cve_api": "https://services.nvd.nist.gov/rest/json/cves/2.0",
            "python_docs": "https://docs.python.org/3",
            "mdn_docs": "https://developer.mozilla.org/api/v1"
        }

        # Documentation URLs
        self._doc_urls = {
            DocumentationType.PYTHON: "https://docs.python.org/3/library/{}.html",
            DocumentationType.FASTAPI: "https://fastapi.tiangolo.com/reference/{}",
            DocumentationType.REACT: "https://react.dev/reference/react/{}",
            DocumentationType.NODEJS: "https://nodejs.org/api/{}.html",
        }

        # Metrics
        self.metrics = {
            "searches_performed": 0,
            "cache_hits": 0,
            "knowledge_fetched": 0,
            "vulnerabilities_found": 0
        }

        logger.info("[WEB-KNOWLEDGE] Integration initialized")

    async def search(
        self,
        query: str,
        sources: Optional[List[KnowledgeSource]] = None,
        limit: int = 5
    ) -> List[WebKnowledge]:
        """
        Search for knowledge across multiple sources.

        Args:
            query: Search query
            sources: Sources to search (default: all)
            limit: Maximum results per source

        Returns:
            List of WebKnowledge items
        """
        sources = sources or [
            KnowledgeSource.DOCUMENTATION,
            KnowledgeSource.STACKOVERFLOW,
            KnowledgeSource.GITHUB
        ]

        results = []
        self.metrics["searches_performed"] += 1

        # Check cache first
        cache_key = self._cache_key(query, sources)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if cached.expires_at and cached.expires_at > datetime.utcnow():
                self.metrics["cache_hits"] += 1
                return [cached]

        # Search each source
        tasks = []
        for source in sources:
            if source == KnowledgeSource.STACKOVERFLOW:
                tasks.append(self._search_stackoverflow(query, limit))
            elif source == KnowledgeSource.GITHUB:
                tasks.append(self._search_github(query, limit))
            elif source == KnowledgeSource.DOCUMENTATION:
                tasks.append(self._search_documentation(query, limit))
            elif source == KnowledgeSource.SECURITY_DB:
                tasks.append(self._search_security_db(query, limit))
            elif source == KnowledgeSource.PACKAGE_REGISTRY:
                tasks.append(self._search_package_registry(query, limit))

        # Gather results
        source_results = await asyncio.gather(*tasks, return_exceptions=True)

        for source_result in source_results:
            if isinstance(source_result, Exception):
                logger.warning(f"[WEB-KNOWLEDGE] Source search failed: {source_result}")
                continue
            results.extend(source_result)

        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        # Cache results
        for result in results[:limit]:
            self._cache[result.knowledge_id] = result
            self.metrics["knowledge_fetched"] += 1

        return results[:limit]

    async def _search_stackoverflow(
        self,
        query: str,
        limit: int
    ) -> List[WebKnowledge]:
        """Search StackOverflow for solutions."""
        results = []

        try:
            url = f"{self._endpoints['stackoverflow_api']}/search/advanced"
            params = {
                "order": "desc",
                "sort": "relevance",
                "q": query,
                "site": "stackoverflow",
                "filter": "withbody",
                "pagesize": min(limit, 10)
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        for item in data.get("items", [])[:limit]:
                            # Extract code examples from body
                            code_examples = self._extract_code_blocks(
                                item.get("body", "")
                            )

                            knowledge = WebKnowledge(
                                knowledge_id=f"SO-{item.get('question_id', '')}",
                                source=KnowledgeSource.STACKOVERFLOW,
                                title=item.get("title", ""),
                                content=self._clean_html(item.get("body", ""))[:1000],
                                url=item.get("link"),
                                relevance_score=min(1.0, item.get("score", 0) / 100),
                                code_examples=code_examples,
                                tags=item.get("tags", []),
                                expires_at=datetime.utcnow() + self.cache_ttl
                            )
                            results.append(knowledge)

        except Exception as e:
            logger.warning(f"[WEB-KNOWLEDGE] StackOverflow search failed: {e}")

        return results

    async def _search_github(
        self,
        query: str,
        limit: int
    ) -> List[WebKnowledge]:
        """Search GitHub for code examples."""
        results = []

        try:
            url = f"{self._endpoints['github_api']}/search/code"
            params = {
                "q": query,
                "per_page": min(limit, 10)
            }
            headers = {
                "Accept": "application/vnd.github.v3+json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        for item in data.get("items", [])[:limit]:
                            knowledge = WebKnowledge(
                                knowledge_id=f"GH-{item.get('sha', '')[:12]}",
                                source=KnowledgeSource.GITHUB,
                                title=item.get("name", ""),
                                content=f"Repository: {item.get('repository', {}).get('full_name', '')}",
                                url=item.get("html_url"),
                                relevance_score=min(1.0, item.get("score", 0) / 100),
                                tags=[item.get("repository", {}).get("language", "")],
                                expires_at=datetime.utcnow() + self.cache_ttl
                            )
                            results.append(knowledge)

        except Exception as e:
            logger.warning(f"[WEB-KNOWLEDGE] GitHub search failed: {e}")

        return results

    async def _search_documentation(
        self,
        query: str,
        limit: int
    ) -> List[WebKnowledge]:
        """Search official documentation."""
        results = []

        # Determine which documentation to search based on query
        doc_types = []
        query_lower = query.lower()

        if any(kw in query_lower for kw in ["python", "def ", "class ", "import "]):
            doc_types.append(DocumentationType.PYTHON)
        if any(kw in query_lower for kw in ["react", "jsx", "component", "hook"]):
            doc_types.append(DocumentationType.REACT)
        if any(kw in query_lower for kw in ["fastapi", "endpoint", "route", "pydantic"]):
            doc_types.append(DocumentationType.FASTAPI)
        if any(kw in query_lower for kw in ["node", "npm", "require", "module"]):
            doc_types.append(DocumentationType.NODEJS)

        if not doc_types:
            doc_types = [DocumentationType.PYTHON]  # Default

        for doc_type in doc_types[:2]:
            doc_result = await self._fetch_documentation(query, doc_type)
            if doc_result:
                results.append(doc_result)

        return results[:limit]

    async def _fetch_documentation(
        self,
        query: str,
        doc_type: DocumentationType
    ) -> Optional[WebKnowledge]:
        """Fetch specific documentation."""
        try:
            # Extract module/function name from query
            words = query.split()
            module_name = words[0] if words else query

            if doc_type == DocumentationType.PYTHON:
                url = self._doc_urls[doc_type].format(module_name)

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            html = await response.text()

                            # Extract relevant content
                            content = self._extract_doc_content(html)

                            return WebKnowledge(
                                knowledge_id=f"DOC-{doc_type.value}-{module_name}",
                                source=KnowledgeSource.DOCUMENTATION,
                                title=f"Python: {module_name}",
                                content=content[:1000],
                                url=url,
                                relevance_score=0.9,  # Official docs are highly relevant
                                verified=True,
                                tags=[doc_type.value, "official"],
                                expires_at=datetime.utcnow() + timedelta(days=7)
                            )

        except Exception as e:
            logger.debug(f"[WEB-KNOWLEDGE] Documentation fetch failed: {e}")

        return None

    async def _search_security_db(
        self,
        query: str,
        limit: int
    ) -> List[WebKnowledge]:
        """Search security vulnerability databases."""
        results = []

        try:
            # Search NVD (National Vulnerability Database)
            url = self._endpoints["cve_api"]
            params = {
                "keywordSearch": query,
                "resultsPerPage": min(limit, 10)
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()

                        for vuln in data.get("vulnerabilities", [])[:limit]:
                            cve = vuln.get("cve", {})
                            metrics = cve.get("metrics", {})

                            # Get severity
                            severity = "unknown"
                            if "cvssMetricV31" in metrics:
                                severity = metrics["cvssMetricV31"][0].get("cvssData", {}).get("baseSeverity", "unknown")

                            description = ""
                            for desc in cve.get("descriptions", []):
                                if desc.get("lang") == "en":
                                    description = desc.get("value", "")
                                    break

                            knowledge = WebKnowledge(
                                knowledge_id=f"CVE-{cve.get('id', '')}",
                                source=KnowledgeSource.SECURITY_DB,
                                title=cve.get("id", "Unknown CVE"),
                                content=description[:1000],
                                relevance_score={"critical": 1.0, "high": 0.8, "medium": 0.6, "low": 0.4}.get(severity.lower(), 0.5),
                                verified=True,
                                tags=["security", "cve", severity],
                                expires_at=datetime.utcnow() + timedelta(days=1)
                            )
                            results.append(knowledge)

                            self.metrics["vulnerabilities_found"] += 1

        except Exception as e:
            logger.warning(f"[WEB-KNOWLEDGE] Security DB search failed: {e}")

        return results

    async def _search_package_registry(
        self,
        query: str,
        limit: int
    ) -> List[WebKnowledge]:
        """Search package registries (PyPI, npm)."""
        results = []

        # Search PyPI
        try:
            url = f"{self._endpoints['pypi_api']}/{query}/json"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        info = data.get("info", {})

                        knowledge = WebKnowledge(
                            knowledge_id=f"PYPI-{info.get('name', query)}",
                            source=KnowledgeSource.PACKAGE_REGISTRY,
                            title=f"PyPI: {info.get('name', query)}",
                            content=info.get("summary", "")[:500],
                            url=info.get("project_url"),
                            relevance_score=0.8,
                            verified=True,
                            tags=["python", "package", info.get("license", "")],
                            expires_at=datetime.utcnow() + timedelta(hours=12)
                        )
                        results.append(knowledge)

        except Exception as e:
            logger.debug(f"[WEB-KNOWLEDGE] PyPI search failed: {e}")

        # Search npm
        try:
            url = f"{self._endpoints['npm_api']}/{query}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        knowledge = WebKnowledge(
                            knowledge_id=f"NPM-{data.get('name', query)}",
                            source=KnowledgeSource.PACKAGE_REGISTRY,
                            title=f"npm: {data.get('name', query)}",
                            content=data.get("description", "")[:500],
                            url=f"https://www.npmjs.com/package/{query}",
                            relevance_score=0.8,
                            verified=True,
                            tags=["javascript", "npm", "package"],
                            expires_at=datetime.utcnow() + timedelta(hours=12)
                        )
                        results.append(knowledge)

        except Exception as e:
            logger.debug(f"[WEB-KNOWLEDGE] npm search failed: {e}")

        return results[:limit]

    async def get_best_practices(
        self,
        topic: str,
        language: str = "python"
    ) -> List[WebKnowledge]:
        """Get best practices for a topic."""
        query = f"{topic} best practices {language}"
        return await self.search(
            query,
            sources=[KnowledgeSource.STACKOVERFLOW, KnowledgeSource.DOCUMENTATION],
            limit=5
        )

    async def check_security(
        self,
        package_name: str,
        version: Optional[str] = None
    ) -> List[SecurityVulnerability]:
        """Check for security vulnerabilities in a package."""
        vulnerabilities = []

        query = f"{package_name} {version or ''}"
        knowledge = await self.search(
            query,
            sources=[KnowledgeSource.SECURITY_DB],
            limit=10
        )

        for item in knowledge:
            if item.source == KnowledgeSource.SECURITY_DB:
                vuln = SecurityVulnerability(
                    cve_id=item.knowledge_id,
                    severity=self._extract_severity(item.tags),
                    description=item.content,
                    affected_packages=[package_name],
                    fixed_versions=[],
                    references=[item.url] if item.url else []
                )
                vulnerabilities.append(vuln)

        return vulnerabilities

    async def get_code_examples(
        self,
        concept: str,
        language: str = "python",
        limit: int = 5
    ) -> List[str]:
        """Get code examples for a concept."""
        query = f"{concept} example {language}"
        knowledge = await self.search(
            query,
            sources=[KnowledgeSource.GITHUB, KnowledgeSource.STACKOVERFLOW],
            limit=limit
        )

        examples = []
        for item in knowledge:
            examples.extend(item.code_examples)

        return examples[:limit]

    async def get_api_documentation(
        self,
        api_name: str,
        endpoint: Optional[str] = None
    ) -> Optional[WebKnowledge]:
        """Get API documentation."""
        query = f"{api_name} API {endpoint or ''} documentation"
        results = await self.search(
            query,
            sources=[KnowledgeSource.DOCUMENTATION],
            limit=1
        )
        return results[0] if results else None

    def _cache_key(self, query: str, sources: List[KnowledgeSource]) -> str:
        """Generate cache key."""
        source_str = ",".join(sorted(s.value for s in sources))
        return hashlib.md5(f"{query}:{source_str}".encode()).hexdigest()

    def _extract_code_blocks(self, html: str) -> List[str]:
        """Extract code blocks from HTML."""
        code_blocks = []

        # Match <code> and <pre> tags
        patterns = [
            r'<code[^>]*>(.*?)</code>',
            r'<pre[^>]*>(.*?)</pre>',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for match in matches:
                cleaned = self._clean_html(match).strip()
                if len(cleaned) > 10 and len(cleaned) < 2000:
                    code_blocks.append(cleaned)

        return code_blocks[:5]

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags from text."""
        # Remove tags
        text = re.sub(r'<[^>]+>', '', html)
        # Decode entities
        text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        return text.strip()

    def _extract_doc_content(self, html: str) -> str:
        """Extract main content from documentation HTML."""
        # Try to find main content
        patterns = [
            r'<div class="section"[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>',
            r'<main[^>]*>(.*?)</main>',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                return self._clean_html(match.group(1))[:2000]

        # Fallback: clean entire HTML
        return self._clean_html(html)[:2000]

    def _extract_severity(self, tags: List[str]) -> str:
        """Extract severity from tags."""
        for tag in tags:
            if tag.lower() in ["critical", "high", "medium", "low"]:
                return tag.lower()
        return "unknown"

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.utcnow()
        valid_entries = sum(
            1 for k in self._cache.values()
            if k.expires_at and k.expires_at > now
        )

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries
        }

    def clear_expired_cache(self):
        """Clear expired cache entries."""
        now = datetime.utcnow()
        expired = [
            k for k, v in self._cache.items()
            if v.expires_at and v.expires_at < now
        ]
        for key in expired:
            del self._cache[key]

        logger.info(f"[WEB-KNOWLEDGE] Cleared {len(expired)} expired cache entries")

    def get_metrics(self) -> Dict[str, Any]:
        """Get web knowledge metrics."""
        return {
            **self.metrics,
            **self.get_cache_stats()
        }
