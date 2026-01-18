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
import base64

logger = logging.getLogger(__name__)


class Platform(str, Enum):
    """Supported SWE platforms."""
    GITHUB = "github"
    GITLAB = "gitlab"
    STACKOVERFLOW = "stackoverflow"
    PYPI = "pypi"
    NPM = "npm"
    CRATES = "crates"
    DOCKERHUB = "dockerhub"


class ResourceType(str, Enum):
    """Types of resources to fetch."""
    REPOSITORY = "repository"
    CODE = "code"
    ISSUE = "issue"
    PULL_REQUEST = "pull_request"
    DISCUSSION = "discussion"
    WORKFLOW = "workflow"
    PACKAGE = "package"
    DOCUMENTATION = "documentation"


@dataclass
class GitHubRepository:
    """GitHub repository information."""
    owner: str
    name: str
    description: str
    stars: int
    forks: int
    language: str
    topics: List[str]
    default_branch: str
    url: str
    readme_content: Optional[str] = None
    license: Optional[str] = None
    last_updated: Optional[datetime] = None


@dataclass
class CodeSnippet:
    """A code snippet from a repository."""
    file_path: str
    content: str
    language: str
    repository: str
    url: str
    line_start: int = 1
    line_end: int = 1
    relevance_score: float = 0.0


@dataclass
class SWEPattern:
    """A software engineering pattern learned from platforms."""
    pattern_id: str
    name: str
    description: str
    category: str  # design, testing, deployment, security
    examples: List[CodeSnippet]
    source_repos: List[str]
    language: str
    confidence: float
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CIWorkflow:
    """A CI/CD workflow pattern."""
    workflow_id: str
    name: str
    platform: str  # github_actions, gitlab_ci, jenkins
    triggers: List[str]
    steps: List[Dict[str, Any]]
    yaml_content: str
    source_repo: str
    url: str


class SWEPlatformConnector:
    """
    Connector to SWE platforms for real-time knowledge.

    Provides:
    - Repository analysis
    - Code search and examples
    - Issue and PR patterns
    - CI/CD workflow patterns
    - Best practices extraction
    """

    def __init__(
        self,
        github_token: Optional[str] = None,
        gitlab_token: Optional[str] = None,
        session=None
    ):
        self.github_token = github_token
        self.gitlab_token = gitlab_token
        self.session = session

        # API endpoints
        self._endpoints = {
            Platform.GITHUB: "https://api.github.com",
            Platform.GITLAB: "https://gitlab.com/api/v4",
            Platform.STACKOVERFLOW: "https://api.stackexchange.com/2.3",
            Platform.PYPI: "https://pypi.org/pypi",
            Platform.NPM: "https://registry.npmjs.org",
            Platform.CRATES: "https://crates.io/api/v1",
            Platform.DOCKERHUB: "https://hub.docker.com/v2"
        }

        # Pattern storage
        self._patterns: Dict[str, SWEPattern] = {}
        self._workflows: Dict[str, CIWorkflow] = {}

        # Cache
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = timedelta(hours=6)

        # Metrics
        self.metrics = {
            "api_calls": 0,
            "patterns_extracted": 0,
            "repos_analyzed": 0,
            "code_snippets_found": 0
        }

        logger.info("[SWE-CONNECTOR] Platform connector initialized")

    def _get_headers(self, platform: Platform) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {"Accept": "application/json"}

        if platform == Platform.GITHUB and self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
            headers["Accept"] = "application/vnd.github.v3+json"
        elif platform == Platform.GITLAB and self.gitlab_token:
            headers["PRIVATE-TOKEN"] = self.gitlab_token

        return headers

    async def analyze_repository(
        self,
        owner: str,
        repo: str,
        platform: Platform = Platform.GITHUB
    ) -> Optional[GitHubRepository]:
        """Analyze a repository for patterns and practices."""
        if platform != Platform.GITHUB:
            logger.warning(f"[SWE-CONNECTOR] Platform {platform} not yet supported for repo analysis")
            return None

        try:
            url = f"{self._endpoints[Platform.GITHUB]}/repos/{owner}/{repo}"
            headers = self._get_headers(Platform.GITHUB)

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Fetch README
                        readme = await self._fetch_readme(owner, repo)

                        repository = GitHubRepository(
                            owner=owner,
                            name=repo,
                            description=data.get("description", ""),
                            stars=data.get("stargazers_count", 0),
                            forks=data.get("forks_count", 0),
                            language=data.get("language", ""),
                            topics=data.get("topics", []),
                            default_branch=data.get("default_branch", "main"),
                            url=data.get("html_url", ""),
                            readme_content=readme,
                            license=data.get("license", {}).get("spdx_id"),
                            last_updated=datetime.fromisoformat(
                                data.get("updated_at", "").replace("Z", "+00:00")
                            ) if data.get("updated_at") else None
                        )

                        self.metrics["repos_analyzed"] += 1
                        self.metrics["api_calls"] += 1

                        return repository

        except Exception as e:
            logger.warning(f"[SWE-CONNECTOR] Repository analysis failed: {e}")

        return None

    async def _fetch_readme(self, owner: str, repo: str) -> Optional[str]:
        """Fetch repository README content."""
        try:
            url = f"{self._endpoints[Platform.GITHUB]}/repos/{owner}/{repo}/readme"
            headers = self._get_headers(Platform.GITHUB)

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("content", "")
                        if content:
                            # Decode base64
                            return base64.b64decode(content).decode("utf-8")

        except Exception as e:
            logger.debug(f"[SWE-CONNECTOR] README fetch failed: {e}")

        return None

    async def search_code(
        self,
        query: str,
        language: Optional[str] = None,
        limit: int = 10
    ) -> List[CodeSnippet]:
        """Search for code across GitHub."""
        snippets = []

        try:
            url = f"{self._endpoints[Platform.GITHUB]}/search/code"
            params = {"q": query, "per_page": min(limit, 30)}

            if language:
                params["q"] += f" language:{language}"

            headers = self._get_headers(Platform.GITHUB)

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()

                        for item in data.get("items", [])[:limit]:
                            # Fetch actual content
                            content = await self._fetch_file_content(
                                item.get("repository", {}).get("full_name", ""),
                                item.get("path", "")
                            )

                            snippet = CodeSnippet(
                                file_path=item.get("path", ""),
                                content=content or "",
                                language=self._detect_language(item.get("path", "")),
                                repository=item.get("repository", {}).get("full_name", ""),
                                url=item.get("html_url", ""),
                                relevance_score=min(1.0, item.get("score", 0) / 100)
                            )
                            snippets.append(snippet)

                        self.metrics["code_snippets_found"] += len(snippets)
                        self.metrics["api_calls"] += 1

        except Exception as e:
            logger.warning(f"[SWE-CONNECTOR] Code search failed: {e}")

        return snippets

    async def _fetch_file_content(
        self,
        repo_full_name: str,
        file_path: str
    ) -> Optional[str]:
        """Fetch file content from repository."""
        try:
            url = f"{self._endpoints[Platform.GITHUB]}/repos/{repo_full_name}/contents/{file_path}"
            headers = self._get_headers(Platform.GITHUB)

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("content", "")
                        if content:
                            return base64.b64decode(content).decode("utf-8")[:5000]

        except Exception:
            pass

        return None

    async def get_workflow_patterns(
        self,
        purpose: str,
        language: Optional[str] = None,
        limit: int = 5
    ) -> List[CIWorkflow]:
        """Get CI/CD workflow patterns for a purpose."""
        workflows = []

        # Search for workflow files
        query = f".github/workflows {purpose}"
        if language:
            query += f" language:{language}"

        try:
            snippets = await self.search_code(query + " filename:yml", limit=limit)

            for snippet in snippets:
                if snippet.content and "jobs:" in snippet.content:
                    workflow = self._parse_workflow(snippet)
                    if workflow:
                        workflows.append(workflow)
                        self._workflows[workflow.workflow_id] = workflow

        except Exception as e:
            logger.warning(f"[SWE-CONNECTOR] Workflow pattern fetch failed: {e}")

        return workflows

    def _parse_workflow(self, snippet: CodeSnippet) -> Optional[CIWorkflow]:
        """Parse a workflow YAML into structured format."""
        try:
            import yaml
            data = yaml.safe_load(snippet.content)

            if not data or "jobs" not in data:
                return None

            # Extract triggers
            triggers = []
            on_config = data.get("on", {})
            if isinstance(on_config, list):
                triggers = on_config
            elif isinstance(on_config, dict):
                triggers = list(on_config.keys())
            elif isinstance(on_config, str):
                triggers = [on_config]

            # Extract steps
            steps = []
            for job_name, job in data.get("jobs", {}).items():
                job_steps = job.get("steps", [])
                for step in job_steps:
                    steps.append({
                        "job": job_name,
                        "name": step.get("name", ""),
                        "uses": step.get("uses", ""),
                        "run": step.get("run", "")[:200] if step.get("run") else ""
                    })

            return CIWorkflow(
                workflow_id=f"WF-{hash(snippet.content) % 10000:04d}",
                name=data.get("name", snippet.file_path),
                platform="github_actions",
                triggers=triggers,
                steps=steps[:20],
                yaml_content=snippet.content[:2000],
                source_repo=snippet.repository,
                url=snippet.url
            )

        except Exception as e:
            logger.debug(f"[SWE-CONNECTOR] Workflow parse failed: {e}")
            return None

    async def extract_patterns(
        self,
        topic: str,
        category: str = "design",
        language: str = "python",
        limit: int = 5
    ) -> List[SWEPattern]:
        """Extract SWE patterns from repositories."""
        patterns = []

        # Search for repositories with this topic
        query = f"{topic} {category} in:readme,description language:{language}"

        try:
            url = f"{self._endpoints[Platform.GITHUB]}/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": 10
            }
            headers = self._get_headers(Platform.GITHUB)

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()

                        for item in data.get("items", [])[:limit]:
                            repo_name = item.get("full_name", "")

                            # Get code examples
                            code_snippets = await self.search_code(
                                f"{topic} repo:{repo_name}",
                                language=language,
                                limit=3
                            )

                            if code_snippets:
                                pattern = SWEPattern(
                                    pattern_id=f"PAT-{hash(topic + repo_name) % 100000:05d}",
                                    name=f"{topic.title()} Pattern",
                                    description=item.get("description", "")[:200],
                                    category=category,
                                    examples=code_snippets,
                                    source_repos=[repo_name],
                                    language=language,
                                    confidence=min(1.0, item.get("stargazers_count", 0) / 10000),
                                    usage_count=item.get("stargazers_count", 0)
                                )
                                patterns.append(pattern)
                                self._patterns[pattern.pattern_id] = pattern

                        self.metrics["patterns_extracted"] += len(patterns)
                        self.metrics["api_calls"] += 1

        except Exception as e:
            logger.warning(f"[SWE-CONNECTOR] Pattern extraction failed: {e}")

        return patterns

    async def get_trending_repos(
        self,
        language: Optional[str] = None,
        since: str = "weekly",
        limit: int = 10
    ) -> List[GitHubRepository]:
        """Get trending repositories."""
        repos = []

        try:
            # Calculate date range
            days = {"daily": 1, "weekly": 7, "monthly": 30}.get(since, 7)
            date_from = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

            query = f"created:>{date_from}"
            if language:
                query += f" language:{language}"

            url = f"{self._endpoints[Platform.GITHUB]}/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": min(limit, 30)
            }
            headers = self._get_headers(Platform.GITHUB)

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()

                        for item in data.get("items", [])[:limit]:
                            repo = GitHubRepository(
                                owner=item.get("owner", {}).get("login", ""),
                                name=item.get("name", ""),
                                description=item.get("description", ""),
                                stars=item.get("stargazers_count", 0),
                                forks=item.get("forks_count", 0),
                                language=item.get("language", ""),
                                topics=item.get("topics", []),
                                default_branch=item.get("default_branch", "main"),
                                url=item.get("html_url", "")
                            )
                            repos.append(repo)

                        self.metrics["api_calls"] += 1

        except Exception as e:
            logger.warning(f"[SWE-CONNECTOR] Trending repos fetch failed: {e}")

        return repos

    async def get_issue_patterns(
        self,
        topic: str,
        state: str = "closed",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get patterns from resolved issues."""
        patterns = []

        try:
            url = f"{self._endpoints[Platform.GITHUB]}/search/issues"
            params = {
                "q": f"{topic} is:issue is:{state}",
                "sort": "reactions",
                "order": "desc",
                "per_page": min(limit, 30)
            }
            headers = self._get_headers(Platform.GITHUB)

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()

                        for item in data.get("items", [])[:limit]:
                            pattern = {
                                "title": item.get("title", ""),
                                "body": item.get("body", "")[:500] if item.get("body") else "",
                                "labels": [l.get("name") for l in item.get("labels", [])],
                                "reactions": item.get("reactions", {}).get("total_count", 0),
                                "url": item.get("html_url", ""),
                                "state": item.get("state", ""),
                                "repository": item.get("repository_url", "").split("/")[-1] if item.get("repository_url") else ""
                            }
                            patterns.append(pattern)

                        self.metrics["api_calls"] += 1

        except Exception as e:
            logger.warning(f"[SWE-CONNECTOR] Issue pattern fetch failed: {e}")

        return patterns

    async def get_best_practices_for(
        self,
        topic: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """Get comprehensive best practices for a topic."""
        practices = {
            "topic": topic,
            "language": language,
            "patterns": [],
            "code_examples": [],
            "workflows": [],
            "common_issues": [],
            "top_repos": []
        }

        # Get patterns
        patterns = await self.extract_patterns(topic, language=language, limit=3)
        practices["patterns"] = [
            {"name": p.name, "description": p.description, "confidence": p.confidence}
            for p in patterns
        ]

        # Get code examples
        snippets = await self.search_code(f"{topic} best practice", language=language, limit=5)
        practices["code_examples"] = [
            {"file": s.file_path, "repo": s.repository, "url": s.url}
            for s in snippets
        ]

        # Get workflows
        if topic in ["testing", "ci", "deploy", "lint", "build"]:
            workflows = await self.get_workflow_patterns(topic, language=language, limit=3)
            practices["workflows"] = [
                {"name": w.name, "triggers": w.triggers, "source": w.source_repo}
                for w in workflows
            ]

        # Get common issues
        issues = await self.get_issue_patterns(topic, limit=5)
        practices["common_issues"] = issues[:5]

        return practices

    def _detect_language(self, file_path: str) -> str:
        """Detect language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".rb": "ruby",
            ".php": "php",
            ".yml": "yaml",
            ".yaml": "yaml",
        }

        for ext, lang in ext_map.items():
            if file_path.endswith(ext):
                return lang

        return "unknown"

    def get_cached_patterns(self) -> List[SWEPattern]:
        """Get all cached patterns."""
        return list(self._patterns.values())

    def get_cached_workflows(self) -> List[CIWorkflow]:
        """Get all cached workflows."""
        return list(self._workflows.values())

    def get_metrics(self) -> Dict[str, Any]:
        """Get connector metrics."""
        return {
            **self.metrics,
            "cached_patterns": len(self._patterns),
            "cached_workflows": len(self._workflows)
        }
