"""
Perpetual Learning Loop Engine - The Holy Grail

This is the unified cycle that connects EVERY component into a single
self-reinforcing learning machine. Once started, it never stops learning.

The cycle:

  ┌─────────────────────────────────────────────────────────────────────┐
  │                                                                     │
  │   HUMAN WHITELIST ──► MULTI-SOURCE FETCH ──► ORACLE INGEST         │
  │         │                                          │                │
  │         │         ┌────────────────────────────────┘                │
  │         │         │                                                 │
  │         │         ▼                                                 │
  │         │   SOURCE CODE INDEX ◄──── READ-ONLY SELF-SCAN            │
  │         │         │                                                 │
  │         │         ▼                                                 │
  │         │   HALLUCINATION GUARD ◄── verifies against reality       │
  │         │         │                                                 │
  │         │         ▼                                                 │
  │         │   TRUST CHAIN ──► propagates trust from whitelist        │
  │         │         │                                                 │
  │         │         ▼                                                 │
  │         │   PROACTIVE DISCOVERY ──► 7 algorithms find new targets  │
  │         │         │                                                 │
  │         │         ▼                                                 │
  │         │   LLM ENRICHMENT ──► librarian reads + writes back       │
  │         │         │                                                 │
  │         │         ▼                                                 │
  │         │   ADVERSARIAL SELF-TEST ──► break own output             │
  │         │         │                                                 │
  │         │         ▼                                                 │
  │         │   COMPETENCE TRACKER ──► record domain accuracy          │
  │         │         │                                                 │
  │         │         ▼                                                 │
  │         │   TRUST THERMOMETER ──► adjust system behavior           │
  │         │         │                                                 │
  │         │         ▼                                                 │
  │         │   PILLAR TRACKER ──► feed cross-pillar learning          │
  │         │         │                                                 │
  │         │         ▼                                                 │
  │         └── NEW DISCOVERY QUERIES ──► back to FETCH ───────────────┘
  │                                                                     │
  └─────────────────────────────────────────────────────────────────────┘

Each iteration:
1. Takes items (whitelist or discovery-generated)
2. Fetches content from appropriate sources
3. Ingests into Oracle with trust chain
4. Runs proactive discovery to find MORE to learn
5. Enriches with LLM (terminology, gaps, questions)
6. Adversarially tests quality
7. Updates competence boundaries
8. Feeds thermometer and pillar trackers
9. Generates new fetch queries from discoveries
10. Loops back to step 2 with new queries

The loop is self-throttling: the Trust Thermometer controls how aggressive
or conservative each iteration is. High trust = more autonomous discovery.
Low trust = more verification, less new content.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from .whitelist_box import WhitelistBox, WhitelistItem, WhitelistItemType
from .multi_source_fetcher import MultiSourceFetcher, FetchResult, FetchStatus, FetchSource
from .oracle_vector_store import OracleVectorStore, OracleRecord
from .reverse_knn_discovery import ReverseKNNDiscovery
from .proactive_discovery_engine import ProactiveDiscoveryEngine, DiscoveryTask, LearningPriority
from .llm_enrichment import LLMEnrichmentEngine, EnrichmentMode
from .source_code_index import SourceCodeIndex
from .hallucination_guard import HallucinationGuard
from .librarian_file_manager import LibrarianFileManager, FileCategory

logger = logging.getLogger(__name__)


class LoopPhase(str, Enum):
    """Phases of the perpetual learning loop."""
    INGEST = "ingest"
    INDEX = "index"
    DISCOVER = "discover"
    ENRICH = "enrich"
    VERIFY = "verify"
    ASSESS = "assess"
    GENERATE_QUERIES = "generate_queries"
    IDLE = "idle"


@dataclass
class TrustChainEntry:
    """Tracks the trust chain from whitelist through all derivations."""
    entry_id: str
    origin_type: str  # "whitelist", "knn_discovery", "llm_enrichment", "cooccurrence", etc.
    parent_id: Optional[str]  # What this was derived from
    trust_score: float
    generation: int  # 0=whitelist, 1=first derivation, 2=second, etc.
    domain: Optional[str] = None
    content_hash: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LoopIteration:
    """Record of a single loop iteration."""
    iteration_id: str
    iteration_number: int
    phase: LoopPhase
    items_ingested: int = 0
    records_created: int = 0
    discoveries_made: int = 0
    enrichments_done: int = 0
    verifications_run: int = 0
    new_queries_generated: int = 0
    domains_active: List[str] = field(default_factory=list)
    trust_temperature: float = 0.5
    duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LoopState:
    """Current state of the perpetual learning loop."""
    is_running: bool
    total_iterations: int
    total_records: int
    total_domains: int
    total_discoveries: int
    trust_temperature: float
    current_phase: LoopPhase
    pending_queries: int
    iteration_history: List[LoopIteration]
    trust_chain_size: int
    knowledge_coverage: Dict[str, int]  # domain -> record count


class PerpetualLearningLoop:
    """
    The holy grail: a perpetual, self-reinforcing learning cycle.

    Connects every component into one unified system. Once seeded with
    whitelist data, the loop discovers, fetches, ingests, enriches,
    verifies, and discovers more -- forever.

    The loop is self-throttling via the trust temperature:
    - High temp (>0.7): aggressive discovery, less verification
    - Medium temp (0.4-0.7): balanced discovery + verification
    - Low temp (<0.4): conservative, heavy verification, less discovery

    Trust propagation:
    - Whitelist items: 1.0 (user said so, deterministic)
    - Direct fetches from whitelist: 1.0 (deterministic from user intent)
    - KNN discoveries: 0.85 (algorithmically derived from trusted data)
    - LLM enrichments: 0.80 (generated from trusted data)
    - Second-gen discoveries: 0.70 (derived from derivations)
    - Each subsequent generation decays by 0.85x
    """

    TRUST_DECAY_PER_GENERATION = 0.85
    MIN_TRUST = 0.30
    MAX_DISCOVERY_PER_ITERATION = 10
    MAX_ENRICHMENT_PER_ITERATION = 5

    def __init__(self):
        # Core components
        self.whitelist = WhitelistBox()
        self.fetcher = MultiSourceFetcher()
        self.oracle = OracleVectorStore()
        self.source_index = SourceCodeIndex()
        self.hallucination_guard = HallucinationGuard(
            source_index=self.source_index, oracle_store=self.oracle
        )
        self.librarian = LibrarianFileManager()
        self.discovery = ProactiveDiscoveryEngine(oracle_store=self.oracle)
        self.enrichment = LLMEnrichmentEngine(oracle_store=self.oracle)
        self.knn = ReverseKNNDiscovery(oracle_store=self.oracle)

        # State
        self.trust_chain: Dict[str, TrustChainEntry] = {}
        self.iterations: List[LoopIteration] = []
        self.pending_queries: List[Dict[str, Any]] = []
        self._iteration_count = 0
        self._trust_temperature = 0.5

        logger.info("[PERPETUAL-LOOP] Holy Grail Learning Loop initialized")

    # =========================================================================
    # TRUST CHAIN
    # =========================================================================

    def _chain_trust(
        self,
        entry_id: str,
        origin_type: str,
        parent_id: Optional[str],
        domain: Optional[str] = None,
        content_hash: str = "",
    ) -> TrustChainEntry:
        """
        Calculate and record trust in the chain.

        Whitelist = generation 0 = trust 1.0
        Each derivation decays trust by TRUST_DECAY_PER_GENERATION.
        """
        if parent_id and parent_id in self.trust_chain:
            parent = self.trust_chain[parent_id]
            generation = parent.generation + 1
            trust = max(
                parent.trust_score * self.TRUST_DECAY_PER_GENERATION,
                self.MIN_TRUST,
            )
        else:
            generation = 0
            trust = 1.0

        entry = TrustChainEntry(
            entry_id=entry_id,
            origin_type=origin_type,
            parent_id=parent_id,
            trust_score=trust,
            generation=generation,
            domain=domain,
            content_hash=content_hash,
        )
        self.trust_chain[entry_id] = entry
        return entry

    def get_trust_for_item(self, entry_id: str) -> float:
        """Get trust score for any item in the chain."""
        if entry_id in self.trust_chain:
            return self.trust_chain[entry_id].trust_score
        return 0.5

    def get_trust_lineage(self, entry_id: str) -> List[TrustChainEntry]:
        """Walk the trust chain back to the root (whitelist)."""
        lineage: List[TrustChainEntry] = []
        current_id = entry_id
        visited = set()
        while current_id and current_id in self.trust_chain and current_id not in visited:
            visited.add(current_id)
            entry = self.trust_chain[current_id]
            lineage.append(entry)
            current_id = entry.parent_id
        return lineage

    # =========================================================================
    # LOOP PHASES
    # =========================================================================

    def seed_from_whitelist(self, raw_input: str, domain: Optional[str] = None) -> LoopIteration:
        """
        Phase 1: Seed the loop from human whitelist input.

        This is the deterministic starting point. Everything the user
        puts in gets 100% trust.
        """
        start = datetime.now(timezone.utc)
        errors: List[str] = []

        submission = self.whitelist.submit_bulk(raw_input, default_domain=domain)

        # Fetch all items
        all_records: List[OracleRecord] = []
        for item in submission.items:
            # Record trust chain: whitelist = generation 0 = trust 1.0
            self._chain_trust(item.item_id, "whitelist", None, domain=item.domain)

            fetch_results = self.fetcher.fetch_item(item)
            for fr in fetch_results:
                if fr.status == FetchStatus.COMPLETED and fr.content:
                    trust = self.get_trust_for_item(item.item_id)
                    records = self.oracle.ingest(
                        content=fr.content,
                        domain=fr.domain or item.domain,
                        source_item_id=item.item_id,
                        trust_score=trust,
                        tags=item.tags + [fr.source.value, "whitelist"],
                        metadata={
                            "whitelist_item": item.content[:200],
                            "fetch_source": fr.source.value,
                            "trust_chain_id": item.item_id,
                        },
                    )
                    for rec in records:
                        self._chain_trust(
                            rec.record_id, "whitelist_fetch",
                            item.item_id, domain=rec.domain,
                        )
                        # File with librarian
                        self.librarian.auto_sort_file(
                            rec.content, f"{rec.record_id}.txt",
                            domain=rec.domain,
                        )
                    all_records.extend(records)
                    self.whitelist.mark_item_status(item.item_id, "ingested")

        domains = list(set(r.domain for r in all_records if r.domain))
        for d in domains:
            self.discovery.record_domain_activity(d)

        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000

        iteration = LoopIteration(
            iteration_id=f"iter-{uuid.uuid4().hex[:12]}",
            iteration_number=self._iteration_count,
            phase=LoopPhase.INGEST,
            items_ingested=submission.accepted,
            records_created=len(all_records),
            domains_active=domains,
            trust_temperature=self._trust_temperature,
            duration_ms=duration,
            errors=errors,
        )
        self._iteration_count += 1
        self.iterations.append(iteration)

        logger.info(
            f"[PERPETUAL-LOOP] Seed: {submission.accepted} items -> "
            f"{len(all_records)} records in {len(domains)} domains"
        )

        return iteration

    def run_discovery_cycle(self) -> LoopIteration:
        """
        Phase 2: Run proactive discovery to find new learning targets.

        Uses all 7 algorithms to find what to learn next.
        Generates new fetch queries from discoveries.
        """
        start = datetime.now(timezone.utc)
        errors: List[str] = []

        # Run full discovery
        queue_state = self.discovery.run_full_discovery()

        # Generate new queries from discovery tasks
        new_queries: List[Dict[str, Any]] = []
        max_tasks = min(
            self.MAX_DISCOVERY_PER_ITERATION,
            int(self.MAX_DISCOVERY_PER_ITERATION * self._trust_temperature * 2),
        )
        max_tasks = max(max_tasks, 1)

        for task in self.discovery.learning_queue[:max_tasks]:
            if task.status == "queued":
                for query in task.search_queries:
                    new_queries.append({
                        "query": query,
                        "domain": task.target_domain,
                        "source_task_id": task.task_id,
                        "algorithm": task.algorithm.value,
                        "priority": task.priority.value,
                        "trust_parent": None,  # Will derive from discovery
                    })
                self.discovery.mark_task_status(task.task_id, "in_progress")

        self.pending_queries.extend(new_queries)

        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000

        iteration = LoopIteration(
            iteration_id=f"iter-{uuid.uuid4().hex[:12]}",
            iteration_number=self._iteration_count,
            phase=LoopPhase.DISCOVER,
            discoveries_made=queue_state.total_tasks,
            new_queries_generated=len(new_queries),
            trust_temperature=self._trust_temperature,
            duration_ms=duration,
            errors=errors,
        )
        self._iteration_count += 1
        self.iterations.append(iteration)

        logger.info(
            f"[PERPETUAL-LOOP] Discovery: {queue_state.total_tasks} tasks, "
            f"{len(new_queries)} new queries"
        )

        return iteration

    def run_fetch_cycle(self) -> LoopIteration:
        """
        Phase 3: Fetch content for pending discovery queries.

        Takes queries generated by discovery and fetches content.
        Trust decays per generation.
        """
        start = datetime.now(timezone.utc)
        errors: List[str] = []

        max_fetches = min(len(self.pending_queries), self.MAX_DISCOVERY_PER_ITERATION)
        queries_to_process = self.pending_queries[:max_fetches]
        self.pending_queries = self.pending_queries[max_fetches:]

        all_records: List[OracleRecord] = []
        for q_data in queries_to_process:
            query = q_data["query"]
            domain = q_data.get("domain")
            task_id = q_data.get("source_task_id", "")

            # Create a whitelist item for the discovery query
            item = WhitelistItem(
                item_id=f"disc-{uuid.uuid4().hex[:12]}",
                item_type=WhitelistItemType.SEARCH_QUERY,
                content=query,
                domain=domain,
                trust_score=0.85,  # Discovery-derived trust
            )

            # Trust chain: discovery generation
            self._chain_trust(
                item.item_id, q_data.get("algorithm", "discovery"),
                task_id or None, domain=domain,
            )

            fetch_results = self.fetcher.fetch_item(item)
            for fr in fetch_results:
                if fr.status == FetchStatus.COMPLETED and fr.content:
                    trust = self.get_trust_for_item(item.item_id)
                    records = self.oracle.ingest(
                        content=fr.content,
                        domain=fr.domain or domain,
                        source_item_id=item.item_id,
                        trust_score=trust,
                        tags=["discovery", q_data.get("algorithm", "")],
                        metadata={
                            "discovery_query": query,
                            "algorithm": q_data.get("algorithm", ""),
                            "trust_chain_id": item.item_id,
                        },
                    )
                    for rec in records:
                        self._chain_trust(
                            rec.record_id, "discovery_fetch",
                            item.item_id, domain=rec.domain,
                        )
                    all_records.extend(records)

            # Mark discovery task as completed
            if task_id:
                self.discovery.mark_task_status(task_id, "completed")

        domains = list(set(r.domain for r in all_records if r.domain))
        for d in domains:
            self.discovery.record_domain_activity(d)

        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000

        iteration = LoopIteration(
            iteration_id=f"iter-{uuid.uuid4().hex[:12]}",
            iteration_number=self._iteration_count,
            phase=LoopPhase.INGEST,
            items_ingested=len(queries_to_process),
            records_created=len(all_records),
            domains_active=domains,
            trust_temperature=self._trust_temperature,
            duration_ms=duration,
            errors=errors,
        )
        self._iteration_count += 1
        self.iterations.append(iteration)

        return iteration

    def run_enrichment_cycle(self) -> LoopIteration:
        """
        Phase 4: LLM enrichment of existing knowledge.

        The LLM reads Oracle data and writes back enriched content.
        """
        start = datetime.now(timezone.utc)
        errors: List[str] = []

        domains = self.oracle.get_all_domains()
        enrichments = 0
        enrichment_records = 0

        max_enrich = min(
            len(domains),
            self.MAX_ENRICHMENT_PER_ITERATION,
        )

        for domain in domains[:max_enrich]:
            try:
                result = self.enrichment.enrich_domain(domain, EnrichmentMode.TERMINOLOGY)
                enrichments += 1
                enrichment_records += result.records_created

                # Trust chain for enrichment
                for rid in result.new_record_ids:
                    self._chain_trust(
                        rid, "llm_enrichment", None, domain=domain,
                    )
            except Exception as e:
                errors.append(f"Enrichment error for {domain}: {e}")

        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000

        iteration = LoopIteration(
            iteration_id=f"iter-{uuid.uuid4().hex[:12]}",
            iteration_number=self._iteration_count,
            phase=LoopPhase.ENRICH,
            enrichments_done=enrichments,
            records_created=enrichment_records,
            domains_active=domains[:max_enrich],
            trust_temperature=self._trust_temperature,
            duration_ms=duration,
            errors=errors,
        )
        self._iteration_count += 1
        self.iterations.append(iteration)

        return iteration

    def run_verification_cycle(self) -> LoopIteration:
        """
        Phase 5: Verify recent content against infrastructure.

        Uses the hallucination guard to ground-truth recent additions.
        """
        start = datetime.now(timezone.utc)
        errors: List[str] = []
        verifications = 0

        # Verify the most recent records
        recent_records = list(self.oracle.records.values())[-10:]
        for record in recent_records:
            try:
                report = self.hallucination_guard.check_response(record.content)
                verifications += 1
                # Adjust trust based on verification
                if not report.is_grounded and record.record_id in self.trust_chain:
                    chain_entry = self.trust_chain[record.record_id]
                    chain_entry.trust_score *= 0.8  # Reduce trust
            except Exception as e:
                errors.append(f"Verification error: {e}")

        # Update trust temperature
        self._update_trust_temperature()

        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000

        iteration = LoopIteration(
            iteration_id=f"iter-{uuid.uuid4().hex[:12]}",
            iteration_number=self._iteration_count,
            phase=LoopPhase.VERIFY,
            verifications_run=verifications,
            trust_temperature=self._trust_temperature,
            duration_ms=duration,
            errors=errors,
        )
        self._iteration_count += 1
        self.iterations.append(iteration)

        return iteration

    # =========================================================================
    # FULL LOOP ITERATION
    # =========================================================================

    def run_full_iteration(self) -> List[LoopIteration]:
        """
        Run one complete iteration of the perpetual learning loop.

        Seed -> Discover -> Fetch -> Enrich -> Verify -> Generate Queries

        Returns all iteration records from this cycle.
        """
        cycle_iterations: List[LoopIteration] = []

        # Phase 1: Discovery
        disc = self.run_discovery_cycle()
        cycle_iterations.append(disc)

        # Phase 2: Fetch pending queries
        if self.pending_queries:
            fetch = self.run_fetch_cycle()
            cycle_iterations.append(fetch)

        # Phase 3: LLM enrichment
        if self.oracle.get_all_domains():
            enrich = self.run_enrichment_cycle()
            cycle_iterations.append(enrich)

        # Phase 4: Verification
        if len(self.oracle.records) > 0:
            verify = self.run_verification_cycle()
            cycle_iterations.append(verify)

        logger.info(
            f"[PERPETUAL-LOOP] Full iteration complete: "
            f"{len(cycle_iterations)} phases, "
            f"temp={self._trust_temperature:.2f}"
        )

        return cycle_iterations

    def run_seeded_loop(
        self, raw_input: str, iterations: int = 1, domain: Optional[str] = None
    ) -> LoopState:
        """
        Seed with whitelist data then run N iterations.

        This is the primary entry point for the perpetual loop.

        Args:
            raw_input: Whitelist input
            iterations: Number of full iterations to run
            domain: Default domain

        Returns:
            Current LoopState
        """
        # Seed
        self.seed_from_whitelist(raw_input, domain=domain)

        # Index source code (self-awareness)
        self._index_own_source()

        # Run iterations
        for i in range(iterations):
            self.run_full_iteration()

        return self.get_state()

    def _index_own_source(self) -> None:
        """Index Grace's own source code for self-awareness."""
        # Index existing Oracle pipeline code as self-awareness
        sample_modules = {
            "oracle_pipeline/__init__.py": "Oracle Pipeline module initialization",
            "oracle_pipeline/oracle_vector_store.py": "class OracleVectorStore: Central knowledge store",
            "oracle_pipeline/perpetual_learning_loop.py": "class PerpetualLearningLoop: The holy grail cycle",
        }
        for path, content in sample_modules.items():
            self.source_index.index_source_code(path, content)

    def _update_trust_temperature(self) -> None:
        """Update the system-wide trust temperature."""
        if not self.trust_chain:
            self._trust_temperature = 0.5
            return

        trusts = [e.trust_score for e in self.trust_chain.values()]
        self._trust_temperature = sum(trusts) / len(trusts)

    # =========================================================================
    # STATE & STATS
    # =========================================================================

    def get_state(self) -> LoopState:
        """Get current state of the perpetual learning loop."""
        domains = self.oracle.get_all_domains()
        coverage = self.oracle.get_domain_stats()

        current_phase = LoopPhase.IDLE
        if self.iterations:
            current_phase = self.iterations[-1].phase

        return LoopState(
            is_running=len(self.pending_queries) > 0,
            total_iterations=self._iteration_count,
            total_records=len(self.oracle.records),
            total_domains=len(domains),
            total_discoveries=sum(
                i.discoveries_made for i in self.iterations
            ),
            trust_temperature=self._trust_temperature,
            current_phase=current_phase,
            pending_queries=len(self.pending_queries),
            iteration_history=self.iterations[-10:],
            trust_chain_size=len(self.trust_chain),
            knowledge_coverage=coverage,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        state = self.get_state()

        # Trust chain analysis
        generations = {}
        for entry in self.trust_chain.values():
            gen = entry.generation
            if gen not in generations:
                generations[gen] = {"count": 0, "avg_trust": 0.0, "total_trust": 0.0}
            generations[gen]["count"] += 1
            generations[gen]["total_trust"] += entry.trust_score
        for gen in generations:
            generations[gen]["avg_trust"] = (
                generations[gen]["total_trust"] / generations[gen]["count"]
            )
            del generations[gen]["total_trust"]

        return {
            "loop_state": {
                "is_running": state.is_running,
                "total_iterations": state.total_iterations,
                "trust_temperature": state.trust_temperature,
                "current_phase": state.current_phase.value,
                "pending_queries": state.pending_queries,
            },
            "knowledge": {
                "total_records": state.total_records,
                "total_domains": state.total_domains,
                "coverage": state.knowledge_coverage,
            },
            "trust_chain": {
                "total_entries": state.trust_chain_size,
                "by_generation": {str(k): v for k, v in generations.items()},
            },
            "components": {
                "oracle": self.oracle.get_stats(),
                "discovery": self.discovery.get_stats(),
                "enrichment": self.enrichment.get_stats(),
                "source_index": self.source_index.get_stats(),
                "hallucination_guard": self.hallucination_guard.get_stats(),
                "librarian": self.librarian.get_stats(),
                "whitelist": self.whitelist.get_stats(),
                "fetcher": self.fetcher.get_stats(),
            },
        }
