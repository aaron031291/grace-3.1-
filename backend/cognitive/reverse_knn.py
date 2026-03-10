"""
Reverse kNN Oracle Discovery — Find What Grace DOESN'T Know

Not "find similar" but "find what's MISSING":
  - Knowledge gaps: topics with fewer than K neighbours (sparse regions)
  - Isolated knowledge: nearest neighbour is far away (disconnected facts)
  - Stale knowledge: clusters where all data is old (needs refresh)
  - Demand gaps: user queries with no good matches (supply vs demand)

Embedding sources (all used for training-data-aware gap analysis):
  - Qdrant documents
  - Learning memory (LearningExample): embedded on the fly so neighbor search
    sees sparse regions in training data; filled content is stored back as training data.
Run nightly or on-demand. Results feed into idle learner and
knowledge expansion cycle to automatically fill gaps.
"""

import hashlib
import json
import logging
import math
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

GAPS_DIR = Path(__file__).parent.parent / "data" / "knowledge_gaps"


class ReverseKNNOracle:
    """Discover what Grace doesn't know by analysing embedding density."""

    def __init__(self):
        self._embeddings: List[Tuple[str, List[float], Dict]] = []
        self._query_log: List[Dict] = []

    def scan_knowledge_gaps(self, k: int = 10, distance_threshold: float = 0.6,
                            min_neighbours: int = 3) -> Dict[str, Any]:
        """
        Full gap analysis across all knowledge sources.
        Returns gaps sorted by severity.
        """
        gaps = {
            "sparse_regions": [],
            "isolated_points": [],
            "stale_clusters": [],
            "demand_gaps": [],
            "summary": {},
        }

        # Load embeddings from all sources
        embeddings = self._load_all_embeddings()

        if not embeddings:
            # Fall back to text-based gap analysis
            return self._text_based_gap_analysis()

        # Sparse regions: points with fewer than min_neighbours within threshold
        for i, (eid, vec, meta) in enumerate(embeddings):
            distances = []
            for j, (_, other_vec, _) in enumerate(embeddings):
                if i == j:
                    continue
                dist = self._cosine_distance(vec, other_vec)
                distances.append(dist)

            distances.sort()
            near_count = sum(1 for d in distances[:k] if d < distance_threshold)

            if near_count < min_neighbours:
                gaps["sparse_regions"].append({
                    "id": eid,
                    "topic": meta.get("source", meta.get("title", eid)),
                    "neighbours_within_threshold": near_count,
                    "nearest_distance": distances[0] if distances else 1.0,
                    "severity": "high" if near_count == 0 else "medium",
                })

            # Isolated points: nearest neighbour is very far
            if distances and distances[0] > 0.8:
                gaps["isolated_points"].append({
                    "id": eid,
                    "topic": meta.get("source", eid),
                    "nearest_distance": round(distances[0], 3),
                    "severity": "high",
                })

        # Stale clusters: group by source, check recency
        by_source = defaultdict(list)
        for eid, vec, meta in embeddings:
            source = meta.get("source", "unknown")
            created = meta.get("created_at", "")
            by_source[source].append(created)

        cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        for source, dates in by_source.items():
            if dates and all(d < cutoff for d in dates if d):
                gaps["stale_clusters"].append({
                    "source": source,
                    "count": len(dates),
                    "oldest": min(d for d in dates if d) if any(d for d in dates) else "unknown",
                    "severity": "medium",
                })

        # Summary
        total_gaps = (len(gaps["sparse_regions"]) + len(gaps["isolated_points"])
                      + len(gaps["stale_clusters"]) + len(gaps["demand_gaps"]))
        gaps["summary"] = {
            "total_embeddings": len(embeddings),
            "total_gaps": total_gaps,
            "sparse_regions": len(gaps["sparse_regions"]),
            "isolated_points": len(gaps["isolated_points"]),
            "stale_clusters": len(gaps["stale_clusters"]),
            "demand_gaps": len(gaps["demand_gaps"]),
            "health_score": round(max(0, 100 - total_gaps * 2), 1),
        }

        # Save gaps report
        self._save_gaps(gaps)

        # Fire event
        try:
            from cognitive.event_bus import publish
            publish("knowledge.gaps_discovered", {
                "total_gaps": total_gaps,
                "sparse": len(gaps["sparse_regions"]),
                "isolated": len(gaps["isolated_points"]),
            }, source="reverse_knn")
        except Exception:
            pass

        return gaps

    def fill_gaps_actively(self, max_gaps: int = 5, auto_ingest: bool = True) -> Dict[str, Any]:
        """
        Actively fill knowledge gaps through 4 data pathways:
          1. FlashCache — cached API/web refs
          2. Web search — SerpAPI
          3. Direct fetch — known URLs (e.g. Python PEPs)
          4. External sources — GitHub (repos), Stack Overflow, research papers (arXiv)

        Each gap topic is tried in order until data is acquired.
        Results flow into FlashCache + Oracle + unified memory.
        """
        gaps = self.scan_knowledge_gaps()
        topics = self.suggest_expansion_topics(limit=max_gaps)

        fill_results = []
        for topic in topics:
            if not topic:
                continue

            result = {"topic": topic, "pathways_tried": [], "data_acquired": False}

            # Pathway 1: FlashCache — check for cached API/web sources on this topic
            try:
                from cognitive.flash_cache import get_flash_cache
                fc = get_flash_cache()
                refs = fc.lookup(keyword=topic, min_trust=0.3, limit=5)
                api_refs = [r for r in refs if r.get("source_type") in ("api", "web")]

                for ref in api_refs[:2]:
                    uri = ref.get("source_uri", "")
                    if not uri or uri.startswith("internal://"):
                        continue

                    # Stream content from the cached source
                    streamed = fc.stream_content(ref.get("id", ""))
                    if streamed and not streamed.get("error"):
                        content = streamed.get("text", streamed.get("data", ""))
                        if content and len(str(content)) > 50:
                            result["pathways_tried"].append({
                                "pathway": "flash_cache_stream",
                                "source": ref.get("source_name", uri),
                                "chars": len(str(content)),
                            })
                            result["data_acquired"] = True

                            # Store in unified memory
                            if auto_ingest:
                                self._ingest_discovery(topic, str(content)[:5000], f"flash_cache:{uri}")
            except Exception:
                pass

            # Pathway 2: Web search via SerpAPI
            if not result["data_acquired"]:
                try:
                    from settings import settings
                    if settings.SERPAPI_KEY:
                        from search.serpapi_service import SerpAPIService
                        serp = SerpAPIService(api_key=settings.SERPAPI_KEY)
                        search_results = serp.search(f"{topic} software engineering best practices", num_results=3)

                        for sr in search_results:
                            result["pathways_tried"].append({
                                "pathway": "web_search",
                                "source": sr.get("link", ""),
                                "title": sr.get("title", ""),
                            })

                            # Cache the search result
                            try:
                                fc = get_flash_cache()
                                fc.register(
                                    source_uri=sr.get("link", ""),
                                    source_type="search",
                                    source_name=sr.get("title", "")[:100],
                                    keywords=fc.extract_keywords(f"{topic} {sr.get('snippet', '')}"),
                                    summary=sr.get("snippet", ""),
                                    trust_score=0.5,
                                )
                            except Exception:
                                pass

                        if search_results:
                            result["data_acquired"] = True
                            if auto_ingest:
                                combined = "\n".join(f"{r['title']}: {r.get('snippet', '')}" for r in search_results)
                                self._ingest_discovery(topic, combined, "web_search")
                except Exception:
                    pass

            # Pathway 3: Direct web fetch from known sources
            if not result["data_acquired"]:
                try:
                    import requests as req
                    # Host-agnostic: use configurable or generic sources (no hardcoded GitHub API)
                    known_urls = {
                        "python": "https://peps.python.org/api/peps.json",
                    }

                    for keyword, url in known_urls.items():
                        if keyword in topic.lower():
                            try:
                                resp = req.get(url, timeout=10, headers={"User-Agent": "Grace/1.0"})
                                if resp.status_code == 200:
                                    data = resp.text[:5000]
                                    result["pathways_tried"].append({
                                        "pathway": "direct_fetch",
                                        "source": url,
                                        "chars": len(data),
                                    })
                                    result["data_acquired"] = True
                                    if auto_ingest:
                                        self._ingest_discovery(topic, data, f"direct:{url}")
                            except Exception:
                                pass
                except Exception:
                    pass

            # Pathway 4: GitHub, Stack Overflow, research papers (arXiv)
            if not result["data_acquired"]:
                try:
                    from settings import settings
                    from search.external_sources import fetch_all_external
                    ext = fetch_all_external(
                        topic,
                        max_per_source=2,
                        github_token=settings.GITHUB_TOKEN or None,
                        include_github=getattr(settings, "GAP_FILL_GITHUB", True),
                        include_stackoverflow=getattr(settings, "GAP_FILL_STACKOVERFLOW", True),
                        include_arxiv=getattr(settings, "GAP_FILL_ARXIV", True),
                        include_wikipedia=getattr(settings, "GAP_FILL_WIKIPEDIA", True),
                        include_hackernews=getattr(settings, "GAP_FILL_HACKERNEWS", True),
                        include_devto=getattr(settings, "GAP_FILL_DEVTO", True),
                        include_pypi=getattr(settings, "GAP_FILL_PYPI", True),
                        include_mdn=getattr(settings, "GAP_FILL_MDN", True),
                        include_semantic_scholar=getattr(settings, "GAP_FILL_SEMANTIC_SCHOLAR", True),
                        include_npm=getattr(settings, "GAP_FILL_NPM", True),
                        include_ietf_rfc=getattr(settings, "GAP_FILL_IETF_RFC", True),
                        semantic_scholar_key=getattr(settings, "SEMANTIC_SCHOLAR_API_KEY", None) or None,
                    )
                    for hit in ext:
                        result["pathways_tried"].append({
                            "pathway": hit.get("source", "external"),
                            "source": hit.get("link", ""),
                            "title": hit.get("title", ""),
                        })
                    if ext:
                        result["data_acquired"] = True
                        combined = "\n".join(
                            f"{h.get('title', '')}: {h.get('snippet', '')}" for h in ext
                        )
                        if auto_ingest and combined.strip():
                            self._ingest_discovery(topic, combined[:5000], "external:" + ",".join({h.get("source", "") for h in ext}))
                        # Cache each in FlashCache
                        try:
                            from cognitive.flash_cache import get_flash_cache
                            fc = get_flash_cache()
                            for h in ext:
                                fc.register(
                                    source_uri=h.get("link", ""),
                                    source_type=h.get("source", "web"),
                                    source_name=(h.get("title", "") or "")[:100],
                                    keywords=fc.extract_keywords(f"{topic} {h.get('snippet', '')}"),
                                    summary=(h.get("snippet", "") or "")[:500],
                                    trust_score=0.5,
                                )
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug("External sources (GitHub/StackOverflow/arXiv) failed: %s", e)

            fill_results.append(result)

        # Track
        acquired = sum(1 for r in fill_results if r["data_acquired"])
        try:
            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"Reverse kNN active fill: {acquired}/{len(fill_results)} gaps filled",
                how="reverse_knn.fill_gaps_actively",
                output_data={"filled": acquired, "total": len(fill_results)},
                tags=["reverse_knn", "active_fill", "knowledge_expansion"],
            )
        except Exception:
            pass

        return {
            "topics_processed": len(fill_results),
            "gaps_filled": acquired,
            "results": fill_results,
        }

    def _ingest_discovery(self, topic: str, content: str, source: str):
        """Ingest discovered data into Oracle + unified memory."""
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            mem.store_learning(
                input_ctx=f"Knowledge gap fill: {topic}",
                expected=content[:5000],
                trust=0.6,
                source=f"reverse_knn_{source}",
                example_type="gap_fill",
            )
        except Exception:
            pass

        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            kw = fc.extract_keywords(f"{topic} {content[:500]}")
            fc.register(
                source_uri=f"internal://gap_fill/{topic.replace(' ', '_')}",
                source_type="internal",
                source_name=f"Gap fill: {topic}",
                keywords=kw,
                summary=content[:300],
                trust_score=0.6,
            )
        except Exception:
            pass

    def log_query(self, query: str, had_results: bool, best_score: float = 0.0):
        """Log a user query for demand-gap analysis."""
        self._query_log.append({
            "query": query,
            "had_results": had_results,
            "best_score": best_score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if len(self._query_log) > 1000:
            self._query_log = self._query_log[-500:]

    def get_demand_gaps(self) -> List[Dict]:
        """Find topics users ask about but Oracle can't answer."""
        no_result_queries = [q for q in self._query_log if not q["had_results"]]
        low_score_queries = [q for q in self._query_log if q["best_score"] < 0.3 and q["had_results"]]

        # Group by similarity
        topics = defaultdict(int)
        for q in no_result_queries + low_score_queries:
            words = q["query"].lower().split()
            for w in words:
                if len(w) > 3:
                    topics[w] += 1

        return [
            {"topic": t, "demand_count": c, "severity": "high" if c > 3 else "medium"}
            for t, c in sorted(topics.items(), key=lambda x: -x[1])[:20]
        ]

    def suggest_expansion_topics(self, limit: int = 10) -> List[str]:
        """Suggest topics to expand based on gaps."""
        gaps = self.scan_knowledge_gaps()
        topics = []

        for gap in gaps.get("sparse_regions", [])[:limit]:
            topics.append(gap.get("topic", ""))

        for gap in gaps.get("demand_gaps", [])[:limit]:
            topics.append(gap.get("topic", ""))

        return [t for t in topics if t][:limit]

    # ── Internal ──────────────────────────────────────────────────────

    def _load_all_embeddings(self) -> List[Tuple[str, List[float], Dict]]:
        """Load embeddings from vector DB, FlashCache, and learning memory (training data)."""
        embeddings = []

        # 1. Qdrant documents
        try:
            from vector_db.client import get_qdrant_client
            client = get_qdrant_client()
            results = client.scroll(
                collection_name="documents",
                limit=1000,
                with_vectors=True,
                with_payload=True,
            )
            if results and results[0]:
                for point in results[0]:
                    vec = point.vector if hasattr(point, 'vector') else []
                    payload = point.payload if hasattr(point, 'payload') else {}
                    if vec:
                        embeddings.append((str(point.id), list(vec), payload))
        except Exception:
            pass

        # 2. Learning memory (training data) — embed examples for neighbor search
        try:
            learning_embeddings = self._load_learning_memory_embeddings(limit=500, min_trust=0.3)
            embeddings.extend(learning_embeddings)
        except Exception as e:
            logger.debug("Learning memory embeddings skipped: %s", e)

        return embeddings

    def _load_learning_memory_embeddings(
        self, limit: int = 500, min_trust: float = 0.3
    ) -> List[Tuple[str, List[float], Dict]]:
        """
        Load learning examples and embed them for use as training-data-aware neighbor search.
        Used for gap analysis so sparse regions in learning memory get filled from API/web/FlashCache.
        """
        out: List[Tuple[str, List[float], Dict]] = []
        try:
            from database.session import session_scope
            from cognitive.learning_memory import LearningExample, _from_json_str
        except Exception:
            return out

        try:
            from embedding.embedder import get_embedding_model
            embedder = get_embedding_model()
        except Exception:
            logger.debug("Embedder unavailable for learning memory")
            return out

        if embedder is None:
            return out

        texts: List[str] = []
        metas: List[Dict] = []
        ids: List[str] = []

        with session_scope() as session:
            rows = (
                session.query(LearningExample)
                .filter(LearningExample.trust_score >= min_trust)
                .order_by(LearningExample.trust_score.desc(), LearningExample.last_used.desc())
                .limit(limit)
                .all()
            )
            for r in rows:
                eid = str(getattr(r, "id", ""))
                if not eid:
                    continue
                ic = getattr(r, "input_context", "") or "{}"
                eo = getattr(r, "expected_output", "") or "{}"
                d_ic = _from_json_str(ic) if isinstance(ic, str) else (ic or {})
                d_eo = _from_json_str(eo) if isinstance(eo, str) else (eo or {})
                text_ic = json.dumps(d_ic, default=str)[:1200]
                text_eo = json.dumps(d_eo, default=str)[:1200]
                text = f"{text_ic} {text_eo}".strip() or " "
                created = getattr(r, "created_at", None)
                created_at = created.isoformat() if hasattr(created, "isoformat") else str(created or "")
                trust = float(getattr(r, "trust_score", 0) or 0)
                example_type = str(getattr(r, "example_type", "") or "")
                texts.append(text)
                ids.append(f"learning_memory_{eid}")
                metas.append({
                    "source": "learning_memory",
                    "created_at": created_at,
                    "trust_score": trust,
                    "example_type": example_type,
                    "title": example_type or eid,
                })

        if not texts:
            return out

        try:
            import numpy as np
            emb = embedder.embed_text(texts, batch_size=32, convert_to_numpy=True)
            if emb is None:
                return out
            arr = np.asarray(emb)
            if arr.ndim == 1:
                vec_list = [arr.tolist()]
            else:
                vec_list = [arr[i].tolist() for i in range(min(len(ids), len(arr)))]
            for i, vec in enumerate(vec_list):
                if i < len(ids) and i < len(metas) and vec:
                    out.append((ids[i], list(vec), metas[i]))
        except Exception as e:
            logger.warning("Embedding learning memory failed: %s", e)

        return out

    def _text_based_gap_analysis(self) -> Dict[str, Any]:
        """Fallback gap analysis using text matching when embeddings unavailable."""
        gaps = {"sparse_regions": [], "isolated_points": [], "stale_clusters": [],
                "demand_gaps": self.get_demand_gaps(), "summary": {}}

        # Check learning examples for coverage
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            stats = mem.get_stats()

            for table, data in stats.items():
                if isinstance(data, dict) and data.get("count", 0) == 0:
                    gaps["sparse_regions"].append({
                        "topic": table, "neighbours_within_threshold": 0,
                        "severity": "high",
                    })
        except Exception:
            pass

        # Check flash cache coverage
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            fc_stats = fc.stats()
            if fc_stats.get("total_entries", 0) < 10:
                gaps["sparse_regions"].append({
                    "topic": "flash_cache", "neighbours_within_threshold": fc_stats.get("total_entries", 0),
                    "severity": "medium",
                })
        except Exception:
            pass

        total = len(gaps["sparse_regions"]) + len(gaps["demand_gaps"])
        gaps["summary"] = {
            "total_gaps": total,
            "method": "text_based_fallback",
            "note": "Embedding-based analysis unavailable — using text fallback",
        }
        return gaps

    def _cosine_distance(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 1.0
        min_len = min(len(a), len(b))
        a, b = a[:min_len], b[:min_len]
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 1.0
        return 1.0 - (dot / (mag_a * mag_b))

    def _save_gaps(self, gaps: Dict):
        GAPS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        (GAPS_DIR / f"gaps_{ts}.json").write_text(json.dumps(gaps, indent=2, default=str))


_instance = None

def get_reverse_knn() -> ReverseKNNOracle:
    global _instance
    if _instance is None:
        _instance = ReverseKNNOracle()
    return _instance


def scan_knowledge_gaps(k: int = 10, distance_threshold: float = 0.6, min_neighbours: int = 3) -> Dict[str, Any]:
    """Module-level entry: run neighbor-by-neighbor gap analysis (for brain API / learning memory)."""
    return get_reverse_knn().scan_knowledge_gaps(k=k, distance_threshold=distance_threshold, min_neighbours=min_neighbours)


def fill_gaps_from_sources(max_gaps: int = 5, auto_ingest: bool = True) -> Dict[str, Any]:
    """Run neighbor search then pull from API, web search, and FlashCache to fill gaps."""
    return get_reverse_knn().fill_gaps_actively(max_gaps=max_gaps, auto_ingest=auto_ingest)
