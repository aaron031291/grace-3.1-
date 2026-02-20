"""
KNN Sub-Agent Engine — Parallel, Multi-Threaded Knowledge Discovery

Upgrades the KNN expansion from a single-threaded BFS to a swarm of
parallel sub-agents that simultaneously explore different branches
of the knowledge graph.

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                   KNN ORCHESTRATOR                           │
│                                                               │
│  Distributes seeds across sub-agents, merges discoveries     │
│                                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Vector   │ │ Web      │ │ API      │ │ Cross    │       │
│  │ Search   │ │ Search   │ │ Search   │ │ Domain   │       │
│  │ Agent    │ │ Agent    │ │ Agent    │ │ Agent    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│       │             │            │             │             │
│       ▼             ▼            ▼             ▼             │
│  Qdrant KNN    SerpAPI/Web   GitHub/PyPI   Domain folders   │
│  neighbors     results       READMEs      cross-reference   │
│                                                               │
│  All results → Merge → Deduplicate → Score → Feed Oracle    │
└─────────────────────────────────────────────────────────────┘

Sub-Agents:
1. VectorSearchAgent — KNN on Qdrant (existing, now parallel)
2. WebSearchAgent — SerpAPI/web scraping for external knowledge
3. APISearchAgent — GitHub API, PyPI, npm for package docs
4. CrossDomainAgent — Finds connections between different domain folders

All run in parallel via ThreadPoolExecutor.
"""

import logging
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

def _track_knn(desc, **kw):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("knn_subagents", desc, **kw)
    except Exception:
        pass


@dataclass
class Discovery:
    """A single knowledge discovery from any sub-agent."""
    topic: str
    text: str
    source: str  # vector_search, web_search, api_search, cross_domain
    trust_score: float
    similarity: float = 0.0
    url: Optional[str] = None
    domain: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SwarmResult:
    """Combined result from all sub-agents."""
    seed_topic: str
    total_discoveries: int
    discoveries_by_source: Dict[str, int] = field(default_factory=dict)
    cross_domain_connections: int = 0
    new_topics: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


class VectorSearchAgent:
    """Sub-agent: KNN search on Qdrant vector DB."""

    def search(self, query: str, limit: int = 8, threshold: float = 0.40) -> List[Discovery]:
        try:
            from retrieval.retriever import DocumentRetriever
            from embedding import get_embedding_model
            model = get_embedding_model()
            retriever = DocumentRetriever(collection_name="documents", embedding_model=model)
            results = retriever.retrieve(query=query, limit=limit, score_threshold=threshold, include_metadata=True)

            discoveries = []
            for r in results:
                text = r.get("text", r.get("content", ""))
                score = r.get("score", 0.0)
                meta = r.get("metadata", {})
                if text and score >= threshold:
                    discoveries.append(Discovery(
                        topic=self._extract_topic(text, meta),
                        text=text[:500],
                        source="vector_search",
                        trust_score=score * 0.9,
                        similarity=score,
                        domain=meta.get("filename", ""),
                    ))
            return discoveries
        except Exception as e:
            logger.debug(f"[KNN-VECTOR] Search failed: {e}")
            return []

    def _extract_topic(self, text: str, meta: dict) -> str:
        filename = meta.get("filename", meta.get("file_path", ""))
        if filename:
            import os
            return os.path.splitext(os.path.basename(filename))[0].replace("_", " ")[:80]
        return " ".join(text.split()[:10])[:80]


class WebSearchAgent:
    """Sub-agent: Web search via SerpAPI for external knowledge."""

    def search(self, query: str, limit: int = 5) -> List[Discovery]:
        try:
            from search.serpapi_service import SerpAPIService
            from settings import settings
            if not getattr(settings, "SERPAPI_KEY", None):
                return []

            serp = SerpAPIService(api_key=settings.SERPAPI_KEY)
            results = serp.search(f"{query} software engineering tutorial")

            discoveries = []
            for r in (results or [])[:limit]:
                title = r.get("title", "")
                snippet = r.get("snippet", r.get("description", ""))
                url = r.get("link", r.get("url", ""))
                if title and snippet:
                    discoveries.append(Discovery(
                        topic=title[:80],
                        text=f"{title}. {snippet}"[:500],
                        source="web_search",
                        trust_score=0.5,
                        url=url,
                    ))
            return discoveries
        except Exception as e:
            logger.debug(f"[KNN-WEB] Search failed: {e}")
            return []


class APISearchAgent:
    """Sub-agent: GitHub/PyPI/npm API search for package documentation."""

    def search(self, query: str, limit: int = 5) -> List[Discovery]:
        discoveries = []

        # GitHub search
        try:
            import requests
            resp = requests.get(
                f"https://api.github.com/search/repositories?q={query}+in:readme&sort=stars&per_page={limit}",
                timeout=10,
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            if resp.status_code == 200:
                for repo in resp.json().get("items", [])[:limit]:
                    discoveries.append(Discovery(
                        topic=repo.get("full_name", "")[:80],
                        text=f"{repo.get('full_name', '')}: {repo.get('description', '')}. Stars: {repo.get('stargazers_count', 0)}"[:500],
                        source="api_search",
                        trust_score=min(0.8, 0.3 + (repo.get("stargazers_count", 0) / 10000)),
                        url=repo.get("html_url", ""),
                        metadata={"stars": repo.get("stargazers_count", 0), "language": repo.get("language", "")},
                    ))
        except Exception as e:
            logger.debug(f"[KNN-API] GitHub search failed: {e}")

        # PyPI search
        try:
            import requests
            resp = requests.get(f"https://pypi.org/pypi/{query}/json", timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("info", {})
                if data.get("summary"):
                    discoveries.append(Discovery(
                        topic=f"PyPI: {data.get('name', query)}",
                        text=f"{data.get('name', '')}: {data.get('summary', '')}. Version: {data.get('version', '')}. Author: {data.get('author', '')}"[:500],
                        source="api_search",
                        trust_score=0.7,
                        url=data.get("project_url", ""),
                    ))
        except Exception:
            pass

        return discoveries


class CrossDomainAgent:
    """Sub-agent: Finds connections between different domain folders."""

    def search(self, query: str, limit: int = 5) -> List[Discovery]:
        try:
            from librarian.knowledge_organizer import get_knowledge_organizer
            organizer = get_knowledge_organizer()
            structure = organizer.get_domain_structure()

            query_lower = query.lower()
            discoveries = []

            for domain, info in structure.items():
                if not info.get("files"):
                    continue
                desc = info.get("description", "").lower()
                # Check if query relates to this domain
                if any(w in desc for w in query_lower.split() if len(w) > 3):
                    for f in info["files"][:2]:
                        discoveries.append(Discovery(
                            topic=f"{domain}/{f['name']}",
                            text=f"Cross-domain: '{query}' relates to {domain} domain — file: {f['name']}",
                            source="cross_domain",
                            trust_score=0.6,
                            domain=domain,
                            metadata={"domain": domain, "file": f["name"]},
                        ))

            return discoveries[:limit]
        except Exception as e:
            logger.debug(f"[KNN-CROSS] Cross-domain search failed: {e}")
            return []


class KNNSubAgentOrchestrator:
    """
    Orchestrates parallel KNN sub-agents.

    Distributes a seed topic across all sub-agents simultaneously,
    merges results, deduplicates, scores, and feeds the Oracle.
    """

    def __init__(self, max_workers: int = 6):
        self.max_workers = max_workers
        self.vector_agent = VectorSearchAgent()
        self.web_agent = WebSearchAgent()
        self.api_agent = APISearchAgent()
        self.cross_domain_agent = CrossDomainAgent()
        self._seen_topics: Set[str] = set()
        self._lock = threading.Lock()

        # Swarm communication — agents talk to each other
        from cognitive.swarm_comms import get_swarm_comm_bus, get_shared_task_log, SwarmMessage, TaskLogEntry
        self._comm_bus = get_swarm_comm_bus()
        self._task_log = get_shared_task_log()
        self._SwarmMessage = SwarmMessage
        self._TaskLogEntry = TaskLogEntry

        # Register reactive listeners — when one agent finds something,
        # other agents react by searching deeper
        self._reactive_discoveries: List[Discovery] = []
        self._comm_bus.register_reactive_listener("orchestrator", self._on_agent_discovery)

        self.stats = {
            "total_swarms": 0,
            "total_discoveries": 0,
            "reactive_discoveries": 0,
            "tasks_skipped_duplicate": 0,
            "by_source": {"vector_search": 0, "web_search": 0, "api_search": 0, "cross_domain": 0},
        }

    def _on_agent_discovery(self, message):
        """Reactive callback — when any agent posts a discovery."""
        if message.trust_score >= 0.7 and message.message_type == "discovery":
            self._reactive_discoveries.append(Discovery(
                topic=message.topic,
                text=message.content[:300],
                source=f"reactive_{message.sender}",
                trust_score=message.trust_score * 0.9,
            ))
            self.stats["reactive_discoveries"] += 1

    def swarm_expand(self, seed_topic: str, seed_text: str = "") -> SwarmResult:
        """
        Launch all sub-agents in parallel to expand a seed topic.

        Agents communicate via the comm bus during search.
        Task log prevents duplicate work.
        """
        start = time.time()
        self.stats["total_swarms"] += 1
        query = seed_text[:200] if seed_text else seed_topic

        # Check task log — was this already expanded?
        if self._task_log.was_already_done(seed_topic, "swarm_expand"):
            self.stats["tasks_skipped_duplicate"] += 1
            return SwarmResult(seed_topic=seed_topic, total_discoveries=0, duration_ms=0)

        # Clear reactive discoveries for this round
        self._reactive_discoveries = []

        all_discoveries: List[Discovery] = []

        def _agent_wrapper(name: str, fn, q: str) -> List[Discovery]:
            """Wraps agent search — posts discoveries to comm bus as they're found."""
            results = fn(q)
            for d in results:
                self._comm_bus.post(self._SwarmMessage(
                    sender=name, message_type="discovery",
                    topic=d.topic, content=d.text[:300],
                    trust_score=d.trust_score,
                ))
            return results

        agents = [
            ("vector", self.vector_agent.search, query),
            ("web", self.web_agent.search, query),
            ("api", self.api_agent.search, seed_topic),
            ("cross_domain", self.cross_domain_agent.search, query),
        ]

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for name, fn, q in agents:
                futures[executor.submit(_agent_wrapper, name, fn, q)] = name

            for future in as_completed(futures, timeout=30):
                agent_name = futures[future]
                try:
                    results = future.result()
                    all_discoveries.extend(results)
                except Exception as e:
                    logger.debug(f"[KNN-SWARM] {agent_name} failed: {e}")

        # Add reactive discoveries (found because agents talked to each other)
        all_discoveries.extend(self._reactive_discoveries)

        # Deduplicate
        unique = self._deduplicate(all_discoveries)

        # Score and sort
        unique.sort(key=lambda d: d.trust_score, reverse=True)

        # Update stats
        by_source = {}
        for d in unique:
            by_source[d.source] = by_source.get(d.source, 0) + 1
            self.stats["by_source"][d.source] = self.stats["by_source"].get(d.source, 0) + 1

        self.stats["total_discoveries"] += len(unique)
        cross_domain = sum(1 for d in unique if d.source == "cross_domain")

        # Feed high-trust discoveries to Oracle
        self._feed_oracle(seed_topic, unique)

        # Feed to Kimi knowledge feedback for vector embedding
        self._feed_kimi_feedback(seed_topic, unique)

        # Feed to ingestion pipeline for embedding
        self._feed_pipeline(seed_topic, unique)

        duration = (time.time() - start) * 1000

        # Log to shared task log — other agents can see this was done
        self._task_log.log_task(self._TaskLogEntry(
            task_type="swarm_expand",
            topic=seed_topic,
            agent="knn_orchestrator",
            status="completed",
            result_count=len(unique),
            trust_score=unique[0].trust_score if unique else 0,
            details={"by_source": by_source, "reactive": len(self._reactive_discoveries)},
        ))

        _track_knn(
            f"Swarm: {len(unique)} discoveries from {len(by_source)} sources "
            f"(+{len(self._reactive_discoveries)} reactive)",
            confidence=unique[0].trust_score if unique else 0,
        )

        return SwarmResult(
            seed_topic=seed_topic,
            total_discoveries=len(unique),
            discoveries_by_source=by_source,
            cross_domain_connections=cross_domain,
            new_topics=[d.topic for d in unique[:20]],
            duration_ms=duration,
        )

    def _deduplicate(self, discoveries: List[Discovery]) -> List[Discovery]:
        """Deduplicate discoveries by topic hash."""
        unique = []
        with self._lock:
            for d in discoveries:
                topic_hash = hashlib.md5(d.topic.lower().encode()).hexdigest()[:12]
                if topic_hash not in self._seen_topics:
                    self._seen_topics.add(topic_hash)
                    unique.append(d)
        return unique

    def _feed_oracle(self, seed: str, discoveries: List[Discovery]):
        """Feed discoveries to unified intelligence."""
        try:
            from genesis.unified_intelligence import UnifiedIntelligenceEngine
            from database.session import SessionLocal
            session = SessionLocal()
            if session:
                try:
                    engine = UnifiedIntelligenceEngine(session)
                    engine.record(
                        source_system="knn_swarm",
                        signal_type="swarm_result",
                        signal_name=f"swarm_{seed[:60]}",
                        value_numeric=len(discoveries),
                        value_json={
                            "seed": seed[:100],
                            "sources": {d.source for d in discoveries},
                            "top_topics": [d.topic for d in discoveries[:5]],
                        },
                        trust_score=0.8,
                        ttl_seconds=1800,
                    )
                finally:
                    session.close()
        except Exception:
            pass

    def _feed_kimi_feedback(self, seed: str, discoveries: List[Discovery]):
        """Feed high-trust discoveries to Kimi feedback for vector embedding."""
        try:
            from cognitive.kimi_knowledge_feedback import get_kimi_feedback
            fb = get_kimi_feedback()
            for d in discoveries:
                if d.trust_score >= 0.7 and len(d.text) >= 200:
                    fb.feed_answer(
                        question=f"What is {d.topic}?",
                        answer=d.text,
                        confidence=d.trust_score,
                        tier_used="knn_swarm",
                    )
        except Exception:
            pass

    def _feed_pipeline(self, seed: str, discoveries: List[Discovery]):
        """Feed high-trust discoveries back to the learning pipeline."""
        try:
            from cognitive.unified_learning_pipeline import get_unified_pipeline
            pipeline = get_unified_pipeline()
            if pipeline.running:
                for d in discoveries:
                    if d.trust_score >= 0.6:
                        pipeline.add_seed(topic=d.topic, text=d.text[:300])
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "topics_seen": len(self._seen_topics),
        }


_orchestrator: Optional[KNNSubAgentOrchestrator] = None

def get_knn_orchestrator() -> KNNSubAgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = KNNSubAgentOrchestrator()
    return _orchestrator
