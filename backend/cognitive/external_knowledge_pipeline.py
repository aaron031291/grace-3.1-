"""
cognitive/external_knowledge_pipeline.py
───────────────────────────────────────────────────────────────────────
External Knowledge Pull Pipeline  (Phase 3.2)

Autonomous pipeline that detects knowledge gaps and fills them by
pulling from external sources (GitHub, StackOverflow, arXiv, Wikipedia,
Semantic Scholar, etc.).

Architecture:
  1. Gap Detection  → reverse_knn scans for sparse/stale knowledge regions
  2. Topic Ranking  → prioritise gaps by demand (user queries) + governance signals
  3. Source Fetch   → search.external_sources.fetch_all_external()
  4. Quality Filter → source reliability weighting + confidence filtering
  5. Ingestion      → unified memory + flash cache + optional vector DB
  6. Reporting      → event bus + genesis keys + KPI tracking

Source Reliability Weights (0-1):
  arxiv              → 0.85  (peer-reviewed research)
  semantic_scholar   → 0.85  (academic papers)
  github             → 0.75  (popular repos, code examples)
  stackoverflow      → 0.70  (community-vetted answers)
  wikipedia          → 0.70  (encyclopaedic, but can be edited)
  ietf_rfc           → 0.90  (official standards)
  mdn                → 0.80  (official Mozilla docs)
  pypi               → 0.60  (package metadata)
  npm                → 0.55  (package metadata)
  devto              → 0.50  (blog articles, variable quality)
  hackernews         → 0.45  (discussion, opinions)

Runs as a background thread, cycling every 30 minutes by default.
Uses TimeSense to adapt (less frequent at night).
"""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Source reliability weights ────────────────────────────────────────
SOURCE_RELIABILITY: Dict[str, float] = {
    "ietf_rfc": 0.90,
    "arxiv": 0.85,
    "semantic_scholar": 0.85,
    "mdn": 0.80,
    "github": 0.75,
    "stackoverflow": 0.70,
    "wikipedia": 0.70,
    "pypi": 0.60,
    "npm": 0.55,
    "devto": 0.50,
    "hackernews": 0.45,
}

# ── Configuration ─────────────────────────────────────────────────────
MIN_RELIABILITY_THRESHOLD = 0.40    # skip sources below this reliability
MAX_TOPICS_PER_CYCLE = 5            # max topics to fill per cycle
MAX_RESULTS_PER_SOURCE = 3          # max results per source per topic
CYCLE_INTERVAL_S = 1800             # 30 minutes between cycles
MIN_CONTENT_LENGTH = 50             # skip snippets shorter than this


class ExternalKnowledgePipeline:
    """
    Autonomous pipeline that detects knowledge gaps and fills them
    from external sources with source reliability scoring.
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._fetch_history: List[Dict[str, Any]] = []
        self._max_history = 300
        self._total_fetches = 0
        self._total_ingested = 0
        self._total_rejected = 0
        self._total_cycles = 0
        self._last_cycle_time: Optional[str] = None

    # ── Start / Stop ──────────────────────────────────────────────────

    def start(self) -> bool:
        """Start the external knowledge pull background loop."""
        if self._running:
            logger.info("[EXT-KNOWLEDGE] Already running")
            return False
        self._running = True
        self._thread = threading.Thread(
            target=self._pipeline_loop,
            daemon=True,
            name="grace-ext-knowledge",
        )
        self._thread.start()
        logger.info("[EXT-KNOWLEDGE] ✅ External knowledge pipeline started (cycle every %ds)", CYCLE_INTERVAL_S)
        return True

    def stop(self):
        """Stop the background pipeline."""
        self._running = False
        logger.info("[EXT-KNOWLEDGE] Pipeline stopped")

    # ── Main Pipeline Loop ────────────────────────────────────────────

    def _pipeline_loop(self):
        """Background loop: detect gaps → fetch → filter → ingest."""
        time.sleep(60)  # let startup settle
        while self._running:
            try:
                self._run_cycle()
            except Exception as e:
                logger.error("[EXT-KNOWLEDGE] Cycle error: %s", e)

            interval = self._get_adaptive_interval()
            time.sleep(interval)

    def _get_adaptive_interval(self) -> int:
        """Use TimeSense to adapt cycle interval."""
        try:
            from cognitive.time_sense import TimeSense
            ctx = TimeSense.now_context()
            if ctx.get("period") == "late_night":
                return 7200  # 2 hours at night
            if ctx.get("is_business_hours"):
                return 900   # 15 min during business hours
        except Exception:
            pass
        return CYCLE_INTERVAL_S

    # ── Core Cycle ────────────────────────────────────────────────────

    def _run_cycle(self):
        """One complete gap-detect → fetch → filter → ingest cycle."""
        self._total_cycles += 1
        self._last_cycle_time = datetime.now(timezone.utc).isoformat()
        cycle_start = time.monotonic()

        # Step 1: Detect knowledge gaps
        topics = self._detect_gaps()
        if not topics:
            logger.debug("[EXT-KNOWLEDGE] No knowledge gaps detected this cycle")
            return

        logger.info("[EXT-KNOWLEDGE] 📚 Cycle %d: processing %d gap topics", self._total_cycles, len(topics))

        cycle_results = []
        for topic in topics[:MAX_TOPICS_PER_CYCLE]:
            result = self._process_topic(topic)
            cycle_results.append(result)

        # Publish cycle summary
        ingested = sum(r.get("ingested", 0) for r in cycle_results)
        rejected = sum(r.get("rejected", 0) for r in cycle_results)
        elapsed = time.monotonic() - cycle_start

        try:
            from cognitive.event_bus import publish_async
            publish_async("knowledge.external_pull_completed", {
                "cycle": self._total_cycles,
                "topics_processed": len(cycle_results),
                "total_ingested": ingested,
                "total_rejected": rejected,
                "elapsed_s": round(elapsed, 1),
            }, source="external_knowledge_pipeline")
        except Exception:
            pass

        # KPI tracking
        try:
            from cognitive.trust_engine import get_trust_engine
            te = get_trust_engine()
            te.record_kpi("external_knowledge", "requests")
            if ingested > 0:
                te.record_kpi("external_knowledge", "successes")
        except Exception:
            pass

        # Genesis tracking
        try:
            from api._genesis_tracker import track
            track(
                key_type="system_event",
                what=f"External knowledge pull: {ingested} items ingested from {len(cycle_results)} topics",
                how="ExternalKnowledgePipeline._run_cycle",
                output_data={
                    "cycle": self._total_cycles,
                    "ingested": ingested,
                    "rejected": rejected,
                    "topics": [r.get("topic", "") for r in cycle_results],
                },
                tags=["knowledge", "external_pull", "phase_3.2"],
            )
        except Exception:
            pass

    def _detect_gaps(self) -> List[str]:
        """Detect knowledge gaps using reverse kNN + demand gaps + governance signals."""
        topics = []

        # Source 1: Reverse kNN gap analysis
        try:
            from cognitive.reverse_knn import ReverseKNNOracle
            oracle = ReverseKNNOracle()
            suggestions = oracle.suggest_expansion_topics(limit=MAX_TOPICS_PER_CYCLE)
            topics.extend(suggestions)
        except Exception as e:
            logger.debug("[EXT-KNOWLEDGE] Reverse kNN unavailable: %s", e)

        # Source 2: Demand gaps from query log
        try:
            from cognitive.reverse_knn import ReverseKNNOracle
            oracle = ReverseKNNOracle()
            demand = oracle.get_demand_gaps()
            for gap in demand[:3]:
                topic = gap.get("topic", "")
                if topic and topic not in topics:
                    topics.append(topic)
        except Exception:
            pass

        # Source 3: Governance signals — low-trust components
        try:
            from cognitive.trust_engine import get_trust_engine
            te = get_trust_engine()
            system_trust = te.get_system_trust()
            for comp_id, comp_data in system_trust.get("components", {}).items():
                trust = comp_data.get("trust", 100)
                if trust < 70:
                    # This component needs help — create a topic from its name
                    topic = comp_data.get("name", comp_id).replace("_", " ")
                    if topic and topic not in topics:
                        topics.append(f"{topic} best practices")
        except Exception:
            pass

        # Deduplicate
        seen = set()
        unique = []
        for t in topics:
            key = t.lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(t)

        return unique[:MAX_TOPICS_PER_CYCLE]

    def _process_topic(self, topic: str) -> Dict[str, Any]:
        """Fetch, filter, and ingest external knowledge for a single topic."""
        result = {
            "topic": topic,
            "fetched": 0,
            "ingested": 0,
            "rejected": 0,
            "sources_used": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Fetch from all external sources
        try:
            from search.external_sources import fetch_all_external
            github_token = None
            try:
                from settings import settings
                github_token = getattr(settings, "GITHUB_TOKEN", None) or None
            except Exception:
                pass

            hits = fetch_all_external(
                topic,
                max_per_source=MAX_RESULTS_PER_SOURCE,
                github_token=github_token,
            )
            result["fetched"] = len(hits)
            self._total_fetches += len(hits)
        except Exception as e:
            logger.warning("[EXT-KNOWLEDGE] Fetch failed for '%s': %s", topic, e)
            return result

        # Filter and ingest
        for hit in hits:
            source = hit.get("source", "unknown")
            reliability = SOURCE_RELIABILITY.get(source, 0.3)
            snippet = hit.get("snippet", "")
            title = hit.get("title", "")

            # Quality filter: skip low-reliability sources
            if reliability < MIN_RELIABILITY_THRESHOLD:
                result["rejected"] += 1
                self._total_rejected += 1
                continue

            # Quality filter: skip empty/tiny content
            if len(snippet) < MIN_CONTENT_LENGTH:
                result["rejected"] += 1
                self._total_rejected += 1
                continue

            # Ingest
            success = self._ingest_item(topic, hit, reliability)
            if success:
                result["ingested"] += 1
                self._total_ingested += 1
                if source not in result["sources_used"]:
                    result["sources_used"].append(source)
            else:
                result["rejected"] += 1
                self._total_rejected += 1

        # Record in history
        with self._lock:
            self._fetch_history.append(result)
            if len(self._fetch_history) > self._max_history:
                self._fetch_history = self._fetch_history[-self._max_history:]

        logger.info(
            "[EXT-KNOWLEDGE] Topic '%s': fetched=%d, ingested=%d, rejected=%d",
            topic, result["fetched"], result["ingested"], result["rejected"],
        )

        return result

    def _ingest_item(self, topic: str, hit: Dict, reliability: float) -> bool:
        """Ingest a single external knowledge item into Grace's memory."""
        source = hit.get("source", "unknown")
        title = hit.get("title", "")
        snippet = hit.get("snippet", "")
        link = hit.get("link", "")

        content = f"{title}\n\n{snippet}" if title else snippet

        # Trust score is based on source reliability
        trust_score = reliability

        # Store in unified memory as a learning example
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            mem.store_learning(
                input_ctx=f"External knowledge: {topic}",
                expected=content[:5000],
                trust=trust_score,
                source=f"external_{source}",
                example_type="external_knowledge",
            )
        except Exception as e:
            logger.debug("[EXT-KNOWLEDGE] Unified memory store failed: %s", e)
            return False

        # Also register in FlashCache for fast lookup
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            fc.register(
                source_uri=link or f"external://{source}/{topic}",
                source_type=source,
                source_name=(title or topic)[:100],
                keywords=fc.extract_keywords(f"{topic} {snippet[:200]}"),
                summary=snippet[:500],
                trust_score=trust_score,
            )
        except Exception:
            pass

        return True

    # ── Manual Trigger ────────────────────────────────────────────────

    def pull_topic(self, topic: str) -> Dict[str, Any]:
        """Manually pull external knowledge for a specific topic."""
        return self._process_topic(topic)

    def force_cycle(self) -> Dict[str, Any]:
        """Manually trigger a full gap-detect + fetch cycle."""
        try:
            self._run_cycle()
            return {
                "status": "completed",
                "cycle": self._total_cycles,
                "total_ingested": self._total_ingested,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Status ────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get pipeline status for API/dashboard."""
        with self._lock:
            recent = self._fetch_history[-10:] if self._fetch_history else []
        return {
            "running": self._running,
            "total_cycles": self._total_cycles,
            "total_fetches": self._total_fetches,
            "total_ingested": self._total_ingested,
            "total_rejected": self._total_rejected,
            "last_cycle": self._last_cycle_time,
            "recent_fetches": recent,
            "source_reliability": SOURCE_RELIABILITY,
        }

    def get_fetch_history(self, limit: int = 50) -> List[Dict]:
        """Return recent fetch history."""
        with self._lock:
            return list(reversed(self._fetch_history[-limit:]))


# ── Singleton ─────────────────────────────────────────────────────────
_pipeline: Optional[ExternalKnowledgePipeline] = None

def get_external_knowledge_pipeline() -> ExternalKnowledgePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = ExternalKnowledgePipeline()
    return _pipeline
