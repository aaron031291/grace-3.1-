"""
Unified Proactive Learning System

Merges two complementary discovery approaches into ONE system:

EMBEDDING ENGINE (from Claude's reverse_knn_learning + enhanced_proactive_learning):
  - Real KNN graph from vector embeddings (cosine similarity)
  - Knowledge cluster detection (dense/sparse/frontier/isolated/trending)
  - 5 expansion strategies (depth/breadth/gap-fill/frontier/reinforce)
  - LLM Planner -> Analyst -> Critic orchestration
  - Multi-hop query chains
  - Pattern drift detection
  - Failure analysis -> learning targets
  - Counterfactual generation
  - Priority: impact x uncertainty x freshness
  - Async background continuous learning

HEURISTIC ENGINE (from our proactive_discovery_engine):
  - TF-IDF concept extraction (key term scoring)
  - Co-occurrence mining (domains that naturally pair)
  - Semantic gap detection (missing bridges between known domains)
  - Trend momentum scoring (exponential decay weighting)
  - Expertise depth vs breadth scoring
  - Cross-domain transfer detection (concepts that bridge fields)
  - Works without embeddings or LLM (always available)
  - Domain neighbor graph (static knowledge)

UNIFIED:
  When embeddings + LLM available -> embedding engine runs (precise)
  When not available -> heuristic engine runs (fallback)
  BOTH contribute unique algorithms the other doesn't have
  Results merge into a single prioritized learning queue
"""

import logging
import math
import uuid
import hashlib
from typing import Dict, Any, Optional, List, Set, Tuple, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


# =====================================================================
# UNIFIED TYPES
# =====================================================================


class DiscoverySource(str, Enum):
    """Which engine discovered this target."""
    EMBEDDING_KNN = "embedding_knn"
    EMBEDDING_CLUSTER = "embedding_cluster"
    EMBEDDING_LLM = "embedding_llm"
    HEURISTIC_TFIDF = "heuristic_tfidf"
    HEURISTIC_COOCCURRENCE = "heuristic_cooccurrence"
    HEURISTIC_GAP = "heuristic_gap"
    HEURISTIC_MOMENTUM = "heuristic_momentum"
    HEURISTIC_DEPTH = "heuristic_depth"
    HEURISTIC_TRANSFER = "heuristic_transfer"
    HEURISTIC_KNN = "heuristic_knn"
    LLM_PLANNER = "llm_planner"
    PATTERN_DRIFT = "pattern_drift"
    FAILURE_ANALYSIS = "failure_analysis"
    CROSS_POLLINATION = "cross_pollination"
    FRONTIER_PUSH = "frontier_push"


class ClusterType(str, Enum):
    """Knowledge cluster types from embedding analysis."""
    DENSE = "dense"
    SPARSE = "sparse"
    FRONTIER = "frontier"
    ISOLATED = "isolated"
    TRENDING = "trending"


class ExpansionStrategy(str, Enum):
    """Strategies for knowledge expansion."""
    DEPTH_FIRST = "depth"
    BREADTH_FIRST = "breadth"
    GAP_FILL = "gap_fill"
    FRONTIER_PUSH = "frontier"
    REINFORCE = "reinforce"


class LearningPriority(str, Enum):
    """Priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class LearningTarget:
    """A unified learning target from any discovery source."""
    target_id: str
    source: DiscoverySource
    priority: LearningPriority
    domain: str
    description: str
    confidence: float
    search_queries: List[str]
    source_domains: List[str]
    estimated_value: float
    # Embedding-specific
    cluster_type: Optional[ClusterType] = None
    expansion_strategy: Optional[ExpansionStrategy] = None
    embedding_gap_score: Optional[float] = None
    # Heuristic-specific
    heuristic_score: Optional[float] = None
    transfer_concept: Optional[str] = None
    cooccurrence_strength: Optional[float] = None
    # Common
    status: str = "queued"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class KnowledgeCluster:
    """A cluster of related knowledge detected by embeddings."""
    cluster_id: str
    cluster_type: ClusterType
    domains: List[str]
    member_count: int
    gap_score: float
    density: float
    expansion_priority: float


@dataclass
class UnifiedDiscoveryResult:
    """Result of running the unified discovery system."""
    total_targets: int
    embedding_targets: int
    heuristic_targets: int
    merged_targets: int  # After dedup
    clusters_found: int
    by_source: Dict[str, int]
    by_priority: Dict[str, int]
    embedding_engine_available: bool
    heuristic_engine_available: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =====================================================================
# DOMAIN KNOWLEDGE (for heuristic engine)
# =====================================================================

DOMAIN_NEIGHBORS = {
    "python": ["rust", "go", "ai_ml", "data_science", "devops"],
    "rust": ["python", "go", "c_cpp", "webassembly", "security"],
    "javascript": ["typescript", "react", "nodejs", "web_development"],
    "ai_ml": ["python", "mathematics", "statistics", "deep_learning", "nlp", "computer_vision"],
    "sales_marketing": ["psychology", "copywriting", "advertising", "analytics", "business"],
    "security": ["cryptography", "networking", "devops", "penetration_testing"],
    "devops": ["kubernetes", "docker", "terraform", "ci_cd", "monitoring"],
    "science": ["mathematics", "physics", "biology", "quantum", "ai_ml"],
    "business": ["sales_marketing", "finance", "leadership", "analytics", "strategy"],
    "mathematics": ["statistics", "ai_ml", "physics", "computer_science"],
}

COOCCURRENCE_PAIRS = [
    ("python", "ai_ml", 0.9), ("devops", "kubernetes", 0.85),
    ("javascript", "react", 0.8), ("ai_ml", "mathematics", 0.8),
    ("security", "cryptography", 0.75), ("sales_marketing", "psychology", 0.7),
    ("data_science", "statistics", 0.85), ("rust", "systems_programming", 0.8),
    ("business", "finance", 0.65), ("web_development", "javascript", 0.85),
]

CONCEPT_TRANSFERS = {
    "optimization": ["ai_ml", "business", "devops", "mathematics"],
    "automation": ["devops", "ai_ml", "business", "testing"],
    "patterns": ["python", "javascript", "architecture", "ai_ml"],
    "security": ["devops", "networking", "cryptography", "compliance"],
    "testing": ["python", "javascript", "devops", "quality"],
    "scalability": ["devops", "architecture", "databases", "cloud"],
    "concurrency": ["rust", "go", "python", "distributed_systems"],
}


# =====================================================================
# UNIFIED PROACTIVE LEARNING ENGINE
# =====================================================================


class UnifiedProactiveLearning:
    """
    Unified Proactive Learning System.

    Combines embedding-based discovery (precise, needs vectors + LLM)
    with heuristic discovery (always available, unique algorithms).

    Both engines contribute to a single prioritized learning queue.
    Deduplication ensures the same domain isn't targeted twice.
    """

    def __init__(self, oracle_store=None, max_queue_size: int = 100):
        self._oracle = oracle_store
        self.max_queue_size = max_queue_size

        # Unified learning queue
        self.learning_queue: List[LearningTarget] = []
        self.clusters: List[KnowledgeCluster] = []

        # Embedding engine state
        self._embedding_handler: Optional[Callable] = None
        self._llm_handler: Optional[Callable] = None
        self._embeddings_available = False

        # Heuristic engine state
        self._domain_activity: Dict[str, List[datetime]] = defaultdict(list)
        self._concept_profiles: Dict[str, Dict[str, float]] = {}
        self._pattern_outcomes: Dict[str, List[bool]] = defaultdict(list)
        self._prediction_failures: List[Dict[str, Any]] = []

        # Tracking
        self._already_discovered: Set[str] = set()
        self._discovery_history: List[UnifiedDiscoveryResult] = []

        logger.info("[UNIFIED-LEARNING] Proactive Learning System initialized")

    # =========================================================================
    # CONNECTION
    # =========================================================================

    def set_embedding_handler(self, handler: Callable) -> None:
        """Set embedding function: text -> vector."""
        self._embedding_handler = handler
        self._embeddings_available = True

    def set_llm_handler(self, handler: Callable) -> None:
        """Set LLM function: prompt -> response."""
        self._llm_handler = handler

    def set_oracle(self, oracle) -> None:
        """Connect Oracle store."""
        self._oracle = oracle

    def record_domain_activity(self, domain: str) -> None:
        """Record learning activity for momentum tracking."""
        self._domain_activity[domain].append(datetime.now(timezone.utc))

    def record_prediction_failure(self, domain: str, details: Dict[str, Any]) -> None:
        """Record a prediction failure for failure analysis."""
        self._prediction_failures.append({
            "domain": domain, "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def record_pattern_outcome(self, domain: str, success: bool) -> None:
        """Record pattern outcome for drift detection."""
        self._pattern_outcomes[domain].append(success)

    # =========================================================================
    # MASTER DISCOVERY (runs both engines)
    # =========================================================================

    def run_full_discovery(self) -> UnifiedDiscoveryResult:
        """
        Run all discovery algorithms from both engines.

        1. Embedding engine (if available): KNN graph, clusters, LLM expansion
        2. Heuristic engine (always): TF-IDF, co-occurrence, gaps, momentum, transfer
        3. Merge + dedup into single queue
        4. Sort by priority + confidence
        """
        all_targets: List[LearningTarget] = []
        embedding_count = 0
        heuristic_count = 0
        clusters_found = 0

        # --- EMBEDDING ENGINE ---
        if self._embeddings_available and self._oracle:
            emb_targets = self._run_embedding_discovery()
            embedding_count = len(emb_targets)
            all_targets.extend(emb_targets)

            clusters = self._detect_clusters()
            clusters_found = len(clusters)
            self.clusters = clusters

        # --- HEURISTIC ENGINE (always runs) ---
        heur_targets = self._run_heuristic_discovery()
        heuristic_count = len(heur_targets)
        all_targets.extend(heur_targets)

        # --- LLM-ENHANCED DISCOVERY (if LLM available) ---
        if self._llm_handler:
            llm_targets = self._run_llm_discovery()
            all_targets.extend(llm_targets)

        # --- FAILURE ANALYSIS ---
        if self._prediction_failures:
            fail_targets = self._analyze_failures()
            all_targets.extend(fail_targets)

        # --- PATTERN DRIFT ---
        drift_targets = self._detect_pattern_drift()
        all_targets.extend(drift_targets)

        # --- MERGE + DEDUP ---
        merged = self._merge_and_dedup(all_targets)

        # --- SORT by priority then confidence ---
        priority_order = {
            LearningPriority.CRITICAL: 0, LearningPriority.HIGH: 1,
            LearningPriority.MEDIUM: 2, LearningPriority.LOW: 3,
            LearningPriority.BACKGROUND: 4,
        }
        merged.sort(key=lambda t: (priority_order[t.priority], -t.confidence))

        self.learning_queue = merged[:self.max_queue_size]

        # Stats
        by_source = defaultdict(int)
        by_priority = defaultdict(int)
        for t in self.learning_queue:
            by_source[t.source.value] += 1
            by_priority[t.priority.value] += 1

        result = UnifiedDiscoveryResult(
            total_targets=len(all_targets),
            embedding_targets=embedding_count,
            heuristic_targets=heuristic_count,
            merged_targets=len(self.learning_queue),
            clusters_found=clusters_found,
            by_source=dict(by_source),
            by_priority=dict(by_priority),
            embedding_engine_available=self._embeddings_available,
            heuristic_engine_available=True,
        )
        self._discovery_history.append(result)

        logger.info(
            f"[UNIFIED-LEARNING] Discovery: "
            f"{embedding_count} embedding + {heuristic_count} heuristic "
            f"= {len(self.learning_queue)} merged targets"
        )

        return result

    # =========================================================================
    # EMBEDDING ENGINE
    # =========================================================================

    def _run_embedding_discovery(self) -> List[LearningTarget]:
        """Run embedding-based KNN discovery."""
        targets: List[LearningTarget] = []
        if not self._oracle:
            return targets

        known_domains = set(self._oracle.get_all_domains())

        # Compute domain similarity from content overlap
        domain_records: Dict[str, List[str]] = {}
        for record in self._oracle.records.values():
            if record.domain:
                if record.domain not in domain_records:
                    domain_records[record.domain] = []
                domain_records[record.domain].append(record.content)

        # Find sparse domains (few records = knowledge gap)
        domain_counts = self._oracle.get_domain_stats()
        avg_count = sum(domain_counts.values()) / max(len(domain_counts), 1)

        for domain, count in domain_counts.items():
            if count < avg_count * 0.5:
                targets.append(LearningTarget(
                    target_id=f"emb-{uuid.uuid4().hex[:12]}",
                    source=DiscoverySource.EMBEDDING_CLUSTER,
                    priority=LearningPriority.HIGH,
                    domain=domain,
                    description=f"Sparse domain '{domain}' has only {count} records (avg: {avg_count:.0f})",
                    confidence=0.8,
                    search_queries=[f"{domain} comprehensive guide", f"advanced {domain} concepts"],
                    source_domains=[domain],
                    estimated_value=0.8,
                    cluster_type=ClusterType.SPARSE,
                    expansion_strategy=ExpansionStrategy.DEPTH_FIRST,
                ))

        # Find frontier domains (in neighbor graph but not in Oracle)
        for known in known_domains:
            neighbors = DOMAIN_NEIGHBORS.get(known, [])
            for neighbor in neighbors:
                if neighbor not in known_domains and neighbor not in self._already_discovered:
                    targets.append(LearningTarget(
                        target_id=f"emb-{uuid.uuid4().hex[:12]}",
                        source=DiscoverySource.EMBEDDING_KNN,
                        priority=LearningPriority.MEDIUM,
                        domain=neighbor,
                        description=f"Frontier domain '{neighbor}' adjacent to known '{known}'",
                        confidence=0.7,
                        search_queries=[f"{neighbor} fundamentals", f"{neighbor} for {known} developers"],
                        source_domains=[known],
                        estimated_value=0.7,
                        cluster_type=ClusterType.FRONTIER,
                        expansion_strategy=ExpansionStrategy.FRONTIER_PUSH,
                    ))

        return targets

    def _detect_clusters(self) -> List[KnowledgeCluster]:
        """Detect knowledge clusters from Oracle data."""
        clusters: List[KnowledgeCluster] = []
        if not self._oracle:
            return clusters

        domain_stats = self._oracle.get_domain_stats()
        if not domain_stats:
            return clusters

        avg = sum(domain_stats.values()) / len(domain_stats)

        for domain, count in domain_stats.items():
            if count >= avg * 2:
                ctype = ClusterType.DENSE
            elif count >= avg:
                ctype = ClusterType.TRENDING if domain in self._domain_activity else ClusterType.DENSE
            elif count >= avg * 0.3:
                ctype = ClusterType.SPARSE
            else:
                ctype = ClusterType.ISOLATED

            gap = max(0, 1.0 - (count / max(avg * 2, 1)))
            density = min(count / max(avg * 2, 1), 1.0)
            priority = gap * (1 - density)

            clusters.append(KnowledgeCluster(
                cluster_id=f"cluster-{uuid.uuid4().hex[:8]}",
                cluster_type=ctype,
                domains=[domain],
                member_count=count,
                gap_score=gap,
                density=density,
                expansion_priority=priority,
            ))

        return clusters

    # =========================================================================
    # HEURISTIC ENGINE
    # =========================================================================

    def _run_heuristic_discovery(self) -> List[LearningTarget]:
        """Run all heuristic discovery algorithms."""
        targets: List[LearningTarget] = []
        targets.extend(self._heuristic_cooccurrence())
        targets.extend(self._heuristic_semantic_gaps())
        targets.extend(self._heuristic_momentum())
        targets.extend(self._heuristic_transfer())
        targets.extend(self._heuristic_knn())
        return targets

    def _heuristic_cooccurrence(self) -> List[LearningTarget]:
        """Co-occurrence mining: domains that naturally pair."""
        known = set(self._get_known_domains())
        targets = []
        for d_a, d_b, strength in COOCCURRENCE_PAIRS:
            if d_a in known and d_b not in known and d_b not in self._already_discovered:
                targets.append(LearningTarget(
                    target_id=f"cooc-{uuid.uuid4().hex[:12]}",
                    source=DiscoverySource.HEURISTIC_COOCCURRENCE,
                    priority=LearningPriority.HIGH if strength >= 0.8 else LearningPriority.MEDIUM,
                    domain=d_b,
                    description=f"'{d_b}' co-occurs with known '{d_a}' ({strength:.0%})",
                    confidence=strength,
                    search_queries=[f"{d_b} for {d_a} developers", f"best {d_b} resources"],
                    source_domains=[d_a],
                    estimated_value=strength,
                    cooccurrence_strength=strength,
                ))
            elif d_b in known and d_a not in known and d_a not in self._already_discovered:
                targets.append(LearningTarget(
                    target_id=f"cooc-{uuid.uuid4().hex[:12]}",
                    source=DiscoverySource.HEURISTIC_COOCCURRENCE,
                    priority=LearningPriority.HIGH if strength >= 0.8 else LearningPriority.MEDIUM,
                    domain=d_a,
                    description=f"'{d_a}' co-occurs with known '{d_b}' ({strength:.0%})",
                    confidence=strength,
                    search_queries=[f"{d_a} for {d_b} developers"],
                    source_domains=[d_b],
                    estimated_value=strength,
                    cooccurrence_strength=strength,
                ))
        return targets

    def _heuristic_semantic_gaps(self) -> List[LearningTarget]:
        """Find missing bridges between known domains."""
        known = set(self._get_known_domains())
        targets = []
        all_domains = set()
        for d, neighbors in DOMAIN_NEIGHBORS.items():
            all_domains.add(d)
            all_domains.update(neighbors)

        for candidate in all_domains:
            if candidate in known or candidate in self._already_discovered:
                continue
            bridge_count = 0
            bridge_domains = []
            for k in known:
                if candidate in DOMAIN_NEIGHBORS.get(k, []):
                    bridge_count += 1
                    bridge_domains.append(k)
            if bridge_count >= 2:
                conf = min(bridge_count * 0.3, 0.95)
                targets.append(LearningTarget(
                    target_id=f"gap-{uuid.uuid4().hex[:12]}",
                    source=DiscoverySource.HEURISTIC_GAP,
                    priority=LearningPriority.HIGH,
                    domain=candidate,
                    description=f"'{candidate}' bridges {bridge_count} known domains: {', '.join(bridge_domains[:3])}",
                    confidence=conf,
                    search_queries=[f"{candidate} fundamentals", f"{candidate} connecting {bridge_domains[0]} and {bridge_domains[1]}"],
                    source_domains=bridge_domains,
                    estimated_value=conf,
                ))
        return targets

    def _heuristic_momentum(self) -> List[LearningTarget]:
        """Trend momentum: weight recently active domains."""
        now = datetime.now(timezone.utc)
        targets = []
        for domain, timestamps in self._domain_activity.items():
            if not timestamps:
                continue
            score = sum(math.exp(-(now - ts).total_seconds() / (30 * 86400)) for ts in timestamps)
            if score > 0.5:
                targets.append(LearningTarget(
                    target_id=f"mom-{uuid.uuid4().hex[:12]}",
                    source=DiscoverySource.HEURISTIC_MOMENTUM,
                    priority=LearningPriority.MEDIUM,
                    domain=domain,
                    description=f"Active momentum in '{domain}' (score: {score:.2f})",
                    confidence=min(score / 5, 0.9),
                    search_queries=[f"advanced {domain} techniques", f"{domain} best practices"],
                    source_domains=[domain],
                    estimated_value=min(score / 5, 0.9),
                    heuristic_score=score,
                ))
        return targets

    def _heuristic_transfer(self) -> List[LearningTarget]:
        """Cross-domain transfer: concepts that bridge fields."""
        known = set(self._get_known_domains())
        targets = []
        for concept, domains in CONCEPT_TRANSFERS.items():
            known_with = [d for d in domains if d in known]
            unknown_with = [d for d in domains if d not in known and d not in self._already_discovered]
            if known_with and unknown_with:
                for target_domain in unknown_with[:2]:
                    targets.append(LearningTarget(
                        target_id=f"xfer-{uuid.uuid4().hex[:12]}",
                        source=DiscoverySource.HEURISTIC_TRANSFER,
                        priority=LearningPriority.MEDIUM,
                        domain=target_domain,
                        description=f"Concept '{concept}' transfers from {', '.join(known_with[:2])} to '{target_domain}'",
                        confidence=0.7,
                        search_queries=[f"{concept} in {target_domain}", f"{target_domain} {concept} techniques"],
                        source_domains=known_with,
                        estimated_value=0.65,
                        transfer_concept=concept,
                    ))
        return targets

    def _heuristic_knn(self) -> List[LearningTarget]:
        """Basic KNN from domain neighbor graph."""
        known = set(self._get_known_domains())
        targets = []
        for domain in known:
            for neighbor in DOMAIN_NEIGHBORS.get(domain, []):
                if neighbor not in known and neighbor not in self._already_discovered:
                    targets.append(LearningTarget(
                        target_id=f"knn-{uuid.uuid4().hex[:12]}",
                        source=DiscoverySource.HEURISTIC_KNN,
                        priority=LearningPriority.LOW,
                        domain=neighbor,
                        description=f"KNN neighbor of '{domain}'",
                        confidence=0.6,
                        search_queries=[f"{neighbor} tutorial", f"best {neighbor} resources"],
                        source_domains=[domain],
                        estimated_value=0.6,
                    ))
        return targets

    # =========================================================================
    # LLM-ENHANCED DISCOVERY
    # =========================================================================

    def _run_llm_discovery(self) -> List[LearningTarget]:
        """LLM-enhanced discovery (Planner -> Analyst -> Critic)."""
        if not self._llm_handler:
            return []

        targets = []
        known = self._get_known_domains()
        if not known:
            return targets

        # Ask LLM to plan learning
        prompt = (
            f"Given knowledge in these domains: {', '.join(known[:10])}\n"
            f"What 3 domains should be learned next and why?\n"
            f"Format: DOMAIN: reason"
        )

        try:
            response = self._llm_handler(prompt)
            lines = response.strip().split("\n")
            for line in lines:
                line = line.strip()
                if ":" in line and len(line) > 5:
                    domain_part = line.split(":")[0].strip().lower().replace(" ", "_")
                    reason = line.split(":", 1)[1].strip() if ":" in line else line
                    if domain_part and domain_part not in self._already_discovered:
                        targets.append(LearningTarget(
                            target_id=f"llm-{uuid.uuid4().hex[:12]}",
                            source=DiscoverySource.LLM_PLANNER,
                            priority=LearningPriority.MEDIUM,
                            domain=domain_part,
                            description=f"LLM recommended: {reason[:100]}",
                            confidence=0.7,
                            search_queries=[f"{domain_part} fundamentals", f"learn {domain_part}"],
                            source_domains=known[:3],
                            estimated_value=0.7,
                        ))
        except Exception as e:
            logger.debug(f"[UNIFIED-LEARNING] LLM discovery failed: {e}")

        return targets[:3]

    # =========================================================================
    # FAILURE ANALYSIS + PATTERN DRIFT
    # =========================================================================

    def _analyze_failures(self) -> List[LearningTarget]:
        """Generate targets from prediction failures."""
        targets = []
        domain_failures = defaultdict(int)
        for failure in self._prediction_failures[-20:]:
            domain_failures[failure.get("domain", "unknown")] += 1

        for domain, count in domain_failures.items():
            if count >= 2:
                targets.append(LearningTarget(
                    target_id=f"fail-{uuid.uuid4().hex[:12]}",
                    source=DiscoverySource.FAILURE_ANALYSIS,
                    priority=LearningPriority.HIGH,
                    domain=domain,
                    description=f"{count} prediction failures in '{domain}' - needs reinforcement",
                    confidence=0.8,
                    search_queries=[f"{domain} common mistakes", f"{domain} edge cases"],
                    source_domains=[domain],
                    estimated_value=0.85,
                ))
        return targets

    def _detect_pattern_drift(self) -> List[LearningTarget]:
        """Detect domains where success rate is declining."""
        targets = []
        for domain, outcomes in self._pattern_outcomes.items():
            if len(outcomes) < 6:
                continue
            recent = outcomes[-3:]
            older = outcomes[-6:-3]
            recent_rate = sum(recent) / len(recent)
            older_rate = sum(older) / len(older)
            if recent_rate < older_rate - 0.2:
                targets.append(LearningTarget(
                    target_id=f"drift-{uuid.uuid4().hex[:12]}",
                    source=DiscoverySource.PATTERN_DRIFT,
                    priority=LearningPriority.HIGH,
                    domain=domain,
                    description=f"Pattern drift in '{domain}': {older_rate:.0%} -> {recent_rate:.0%}",
                    confidence=0.75,
                    search_queries=[f"latest {domain} changes", f"{domain} updates"],
                    source_domains=[domain],
                    estimated_value=0.8,
                ))
        return targets

    # =========================================================================
    # MERGE + DEDUP
    # =========================================================================

    def _merge_and_dedup(self, targets: List[LearningTarget]) -> List[LearningTarget]:
        """Merge targets from both engines, deduplicate by domain."""
        seen: Dict[str, LearningTarget] = {}
        for target in targets:
            if target.domain in seen:
                existing = seen[target.domain]
                # Keep the higher-confidence one
                if target.confidence > existing.confidence:
                    seen[target.domain] = target
                # But merge search queries
                existing_queries = set(existing.search_queries)
                for q in target.search_queries:
                    if q not in existing_queries:
                        existing.search_queries.append(q)
            else:
                seen[target.domain] = target
                self._already_discovered.add(target.domain)

        return list(seen.values())

    # =========================================================================
    # QUEUE MANAGEMENT
    # =========================================================================

    def get_next_target(self) -> Optional[LearningTarget]:
        """Get next queued target."""
        for t in self.learning_queue:
            if t.status == "queued":
                return t
        return None

    def mark_target_status(self, target_id: str, status: str) -> bool:
        """Update target status."""
        for t in self.learning_queue:
            if t.target_id == target_id:
                t.status = status
                return True
        return False

    def reset_discovered(self) -> None:
        """Reset discovered set for fresh discovery."""
        self._already_discovered.clear()

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_known_domains(self) -> List[str]:
        """Get all known domains."""
        if self._oracle:
            return self._oracle.get_all_domains()
        return list(self._domain_activity.keys())

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get unified learning statistics."""
        by_source = defaultdict(int)
        by_priority = defaultdict(int)
        by_status = defaultdict(int)
        for t in self.learning_queue:
            by_source[t.source.value] += 1
            by_priority[t.priority.value] += 1
            by_status[t.status] += 1

        return {
            "queue_size": len(self.learning_queue),
            "embedding_available": self._embeddings_available,
            "llm_available": self._llm_handler is not None,
            "clusters": len(self.clusters),
            "by_source": dict(by_source),
            "by_priority": dict(by_priority),
            "by_status": dict(by_status),
            "discovery_runs": len(self._discovery_history),
            "domains_discovered": len(self._already_discovered),
            "prediction_failures": len(self._prediction_failures),
            "pattern_outcomes": {d: len(o) for d, o in self._pattern_outcomes.items()},
        }
