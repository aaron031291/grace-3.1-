"""
Reverse kNN Oracle Discovery — Find What Grace DOESN'T Know

Not "find similar" but "find what's MISSING":
  - Knowledge gaps: topics with fewer than K neighbours (sparse regions)
  - Isolated knowledge: nearest neighbour is far away (disconnected facts)
  - Stale knowledge: clusters where all data is old (needs refresh)
  - Demand gaps: user queries with no good matches (supply vs demand)

Run nightly or on-demand. Results feed into idle learner and
knowledge expansion cycle to automatically fill gaps.
"""

import hashlib
import json
import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
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

        cutoff = (datetime.utcnow() - timedelta(days=90)).isoformat()
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

    def log_query(self, query: str, had_results: bool, best_score: float = 0.0):
        """Log a user query for demand-gap analysis."""
        self._query_log.append({
            "query": query,
            "had_results": had_results,
            "best_score": best_score,
            "timestamp": datetime.utcnow().isoformat(),
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
        """Load embeddings from vector DB or flash cache."""
        embeddings = []

        # Try Qdrant
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

        return embeddings

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
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        (GAPS_DIR / f"gaps_{ts}.json").write_text(json.dumps(gaps, indent=2, default=str))


_instance = None

def get_reverse_knn() -> ReverseKNNOracle:
    global _instance
    if _instance is None:
        _instance = ReverseKNNOracle()
    return _instance
