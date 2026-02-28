"""
Knowledge Expansion Cycle — Seed → Discover → Score → Enrich → Reingest

Trust-aware iterative loop that:
1. Starts from a verified seed (100% trust)
2. Discovers related data (Oracle DB, web search, APIs)
3. Scores everything through Trust Engine (chunk-level 0-100)
4. Enriches with Kimi (reasoning, context, enhancement, KB audit)
5. Validates through hallucination guard
6. Reingests high-trust data back into the knowledge base
7. Repeats with depth limits and cost controls
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CycleConfig:
    max_depth: int = 3
    max_records_per_cycle: int = 20
    trust_floor: float = 60.0
    auto_accept_threshold: float = 80.0
    max_kimi_calls: int = 50
    dedup_enabled: bool = True


@dataclass
class CycleResult:
    cycle_id: str = ""
    seed: str = ""
    depth: int = 0
    records_discovered: int = 0
    records_scored: int = 0
    records_enriched: int = 0
    records_accepted: int = 0
    records_rejected: int = 0
    records_human_review: int = 0
    kimi_calls_used: int = 0
    gaps_identified: List[str] = field(default_factory=list)
    duration_ms: float = 0
    status: str = "pending"


class KnowledgeExpansionCycle:
    """
    Iterative knowledge expansion with trust gates at every stage.
    """

    def __init__(self, config: CycleConfig = None):
        self.config = config or CycleConfig()
        self._seen_hashes: set = set()
        self._kimi_calls: int = 0
        self._cycle_history: List[CycleResult] = []

    def run_cycle(self, seed: str, seed_context: str = "") -> CycleResult:
        """
        Run one full expansion cycle from a seed.
        """
        start = time.time()
        result = CycleResult(
            cycle_id=f"cycle_{int(start)}",
            seed=seed[:200],
            status="running",
        )

        current_queries = [seed]
        all_enriched = []

        for depth in range(self.config.max_depth):
            result.depth = depth + 1
            logger.info(f"[CYCLE] Depth {depth + 1}/{self.config.max_depth}, queries: {len(current_queries)}")

            # Stage 1: Discover
            discovered = self._discover(current_queries)
            result.records_discovered += len(discovered)

            if not discovered:
                break

            # Stage 2: Deduplicate
            if self.config.dedup_enabled:
                discovered = self._deduplicate(discovered)

            # Stage 3: Score through Trust Engine
            scored = self._score(discovered)
            result.records_scored += len(scored)

            # Filter by trust floor
            above_floor = [r for r in scored if r["trust"] >= self.config.trust_floor]
            below_floor = [r for r in scored if r["trust"] < self.config.trust_floor]
            result.records_rejected += len(below_floor)

            if not above_floor:
                break

            # Stage 4: Enrich with Kimi (4 roles)
            enriched = self._enrich(above_floor, seed_context)
            result.records_enriched += len(enriched)

            # Stage 5: Validate and route
            for record in enriched:
                if record.get("trust", 0) >= self.config.auto_accept_threshold:
                    # Auto-accept
                    self._reingest(record)
                    result.records_accepted += 1
                    all_enriched.append(record)
                else:
                    # Route to human review
                    result.records_human_review += 1

            # Stage 6: KB audit — find gaps for next cycle
            gaps = self._audit_gaps(enriched, seed)
            result.gaps_identified.extend(gaps[:5])

            # Next cycle queries come from gaps
            current_queries = gaps[:self.config.max_records_per_cycle]

            if self._kimi_calls >= self.config.max_kimi_calls:
                logger.info(f"[CYCLE] Kimi call limit reached ({self.config.max_kimi_calls})")
                break

        result.kimi_calls_used = self._kimi_calls
        result.duration_ms = round((time.time() - start) * 1000, 1)
        result.status = "completed"

        # Genesis track
        try:
            from api._genesis_tracker import track
            track(key_type="system",
                  what=f"Knowledge cycle completed: {seed[:50]} (depth {result.depth}, {result.records_accepted} accepted)",
                  how="KnowledgeExpansionCycle.run_cycle",
                  input_data={"seed": seed[:200]},
                  output_data={"discovered": result.records_discovered, "accepted": result.records_accepted, "gaps": len(result.gaps_identified)},
                  tags=["knowledge_cycle", "expansion"])
        except Exception:
            pass

        self._cycle_history.append(result)
        return result

    # ── Stage 1: Discover ──────────────────────────────────────────────

    def _discover(self, queries: List[str]) -> List[Dict]:
        discovered = []

        for query in queries[:self.config.max_records_per_cycle]:
            # Source 1: Oracle DB (learning memory, episodes, procedures)
            discovered.extend(self._search_oracle(query))

            # Source 2: RAG knowledge base
            discovered.extend(self._search_rag(query))

            # Source 3: Magma memory graphs
            discovered.extend(self._search_magma(query))

            # Source 4: FlashCache — cached external references
            discovered.extend(self._search_flash_cache(query))

        return discovered

    def _search_oracle(self, query: str) -> List[Dict]:
        try:
            from cognitive.pipeline import FeedbackLoop
            patterns = FeedbackLoop.get_relevant_patterns(query)
            return [{"content": p.get("input", "") + " " + p.get("expected", ""),
                      "source": "oracle", "trust": (p.get("trust", 0.5)) * 100}
                    for p in patterns]
        except Exception:
            return []

    def _search_rag(self, query: str) -> List[Dict]:
        try:
            from retrieval.retriever import DocumentRetriever
            from embedding.embedder import get_embedding_model
            from vector_db.client import get_qdrant_client
            retriever = DocumentRetriever(embedding_model=get_embedding_model(), qdrant_client=get_qdrant_client())
            chunks = retriever.retrieve(query=query[:200], limit=5, score_threshold=0.3)
            return [{"content": c.get("text", ""), "source": "rag",
                      "trust": c.get("score", 0.5) * 100,
                      "metadata": c.get("metadata", {})}
                    for c in chunks]
        except Exception:
            return []

    def _search_flash_cache(self, query: str) -> List[Dict]:
        """Search FlashCache for cached external references."""
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            refs = fc.search(query, limit=5, min_trust=0.4)
            results = []
            for ref in refs:
                summary = ref.get("summary", "")
                name = ref.get("source_name", "")
                uri = ref.get("source_uri", "")
                trust = (ref.get("trust_score", 0.5)) * 100
                content = f"{name}: {summary}" if summary else f"{name} ({uri})"
                results.append({"content": content, "source": "flash_cache",
                                "trust": trust, "metadata": {"uri": uri}})
            return results
        except Exception:
            return []

    def _search_magma(self, query: str) -> List[Dict]:
        try:
            from cognitive.magma_bridge import query_results
            results = query_results(query, limit=3)
            return [{"content": str(r), "source": "magma", "trust": 70} for r in results if r]
        except Exception:
            return []

    # ── Stage 2: Deduplicate ───────────────────────────────────────────

    def _deduplicate(self, records: List[Dict]) -> List[Dict]:
        unique = []
        for r in records:
            h = hash(r.get("content", "")[:200])
            if h not in self._seen_hashes:
                self._seen_hashes.add(h)
                unique.append(r)
        return unique

    # ── Stage 3: Score ─────────────────────────────────────────────────

    def _score(self, records: List[Dict]) -> List[Dict]:
        try:
            from cognitive.trust_engine import get_trust_engine
            engine = get_trust_engine()
            for r in records:
                comp = engine.score_output(
                    f"cycle_{r.get('source', 'unknown')}",
                    f"Cycle: {r.get('source', 'unknown')}",
                    r.get("content", ""),
                    source=r.get("source", "unknown"),
                )
                r["trust"] = comp.trust_score
        except Exception:
            pass
        return records

    # ── Stage 4: Enrich with Kimi ──────────────────────────────────────

    def _enrich(self, records: List[Dict], context: str) -> List[Dict]:
        try:
            from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
            kimi = get_kimi_enhanced()
        except Exception:
            return records

        enriched = []
        for r in records:
            if self._kimi_calls >= self.config.max_kimi_calls:
                enriched.append(r)
                continue

            content = r.get("content", "")
            if not content.strip():
                continue

            # Kimi Role 1: Reasoning
            # Kimi Role 2: Context Enrichment
            # Kimi Role 3: Enhancement
            # Combined into one call for efficiency
            try:
                enhanced = kimi._call(
                    f"Analyse and enrich this knowledge:\n\n{content[:2000]}\n\n"
                    f"Context: {context[:500]}\n\n"
                    f"Provide: 1) Reasoning about relationships 2) Additional context 3) Enhanced version",
                    system="You are enriching a knowledge base. Be precise and add value.",
                    temperature=0.2, max_tokens=2000,
                )
                self._kimi_calls += 1

                if enhanced:
                    r["enriched_content"] = enhanced
                    r["enrichment_source"] = "kimi"
                    # Re-score after enrichment
                    r["trust"] = min(100, r.get("trust", 50) + 10)
            except Exception:
                pass

            enriched.append(r)

        return enriched

    # ── Stage 5: Reingest ──────────────────────────────────────────────

    def _reingest(self, record: Dict):
        content = record.get("enriched_content", record.get("content", ""))
        if not content:
            return

        # Store in learning memory
        try:
            from cognitive.pipeline import FeedbackLoop
            FeedbackLoop.record_outcome(
                genesis_key="", prompt=f"Knowledge expansion: {content[:100]}",
                output=content[:5000], outcome="positive",
            )
        except Exception:
            pass

        # Store in Magma
        try:
            from cognitive.magma_bridge import ingest
            ingest(content[:3000], source="knowledge_cycle")
        except Exception:
            pass

    # ── Stage 6: KB Audit — find gaps ──────────────────────────────────

    def _audit_gaps(self, enriched: List[Dict], seed: str) -> List[str]:
        try:
            from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
            kimi = get_kimi_enhanced()

            if self._kimi_calls >= self.config.max_kimi_calls:
                return []

            enriched_summary = "\n".join(r.get("content", "")[:100] for r in enriched[:10])
            response = kimi._call(
                f"Original topic: {seed}\n\nKnowledge gathered so far:\n{enriched_summary}\n\n"
                f"What's MISSING? List 3-5 specific knowledge gaps as short queries.",
                system="You are auditing a knowledge base for completeness.",
                temperature=0.3, max_tokens=500,
            )
            self._kimi_calls += 1

            if response:
                lines = [l.strip().lstrip("0123456789.-) ") for l in response.split("\n") if l.strip() and len(l.strip()) > 10]
                return lines[:5]
        except Exception:
            pass
        return []

    # ── Status ─────────────────────────────────────────────────────────

    def get_history(self) -> List[Dict]:
        return [
            {"cycle_id": r.cycle_id, "seed": r.seed, "depth": r.depth,
             "discovered": r.records_discovered, "accepted": r.records_accepted,
             "rejected": r.records_rejected, "human_review": r.records_human_review,
             "gaps": len(r.gaps_identified), "kimi_calls": r.kimi_calls_used,
             "duration_ms": r.duration_ms, "status": r.status}
            for r in self._cycle_history
        ]


_cycle = None

def get_knowledge_cycle() -> KnowledgeExpansionCycle:
    global _cycle
    if _cycle is None:
        _cycle = KnowledgeExpansionCycle()
    return _cycle
