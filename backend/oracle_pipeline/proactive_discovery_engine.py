"""
Enhanced Proactive Discovery Engine

Goes far beyond basic KNN with multiple discovery algorithms that run
as background processes, continuously finding new things to learn.

Algorithms:
1. Reverse KNN - Domain neighbor graph (already built)
2. TF-IDF Concept Extraction - Extract key concepts, find gaps
3. Co-occurrence Mining - Domains that appear together frequently
4. Semantic Gap Detection - Find missing knowledge between connected domains
5. Trend Momentum Scoring - Weight recently active domains higher
6. Expertise Depth Scoring - Prioritize deepening vs broadening
7. Cross-Domain Transfer Detection - Find transferable concepts

The engine produces a prioritized learning queue that runs as a
background process. Over 6 months of continuous learning, Grace
builds comprehensive training data across all domains.
"""

import logging
import math
import uuid
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from enum import Enum

from .oracle_vector_store import OracleVectorStore

logger = logging.getLogger(__name__)


class DiscoveryAlgorithm(str, Enum):
    """Discovery algorithms available."""
    REVERSE_KNN = "reverse_knn"
    TFIDF_CONCEPT = "tfidf_concept"
    COOCCURRENCE = "cooccurrence"
    SEMANTIC_GAP = "semantic_gap"
    TREND_MOMENTUM = "trend_momentum"
    EXPERTISE_DEPTH = "expertise_depth"
    CROSS_DOMAIN_TRANSFER = "cross_domain_transfer"


class LearningPriority(str, Enum):
    """Priority levels for learning tasks."""
    CRITICAL = "critical"      # Fill knowledge gap immediately
    HIGH = "high"              # Important related domain
    MEDIUM = "medium"          # Good to learn
    LOW = "low"                # Nice to have
    BACKGROUND = "background"  # Long-term enrichment


@dataclass
class DiscoveryTask:
    """A proactive learning task discovered by the engine."""
    task_id: str
    algorithm: DiscoveryAlgorithm
    priority: LearningPriority
    target_domain: str
    description: str
    confidence: float
    search_queries: List[str]
    source_domains: List[str]
    estimated_value: float  # 0-1 how valuable this learning would be
    status: str = "queued"  # queued, in_progress, completed, skipped
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ConceptProfile:
    """Extracted concept profile for a domain."""
    domain: str
    concepts: Dict[str, float]  # concept -> weight
    total_words: int
    unique_concepts: int
    depth_score: float
    breadth_score: float


@dataclass
class LearningQueueState:
    """Current state of the learning queue."""
    total_tasks: int
    by_priority: Dict[str, int]
    by_algorithm: Dict[str, int]
    by_status: Dict[str, int]
    estimated_total_value: float
    next_task: Optional[DiscoveryTask]


class ProactiveDiscoveryEngine:
    """
    Enhanced discovery engine with 7 algorithms for continuous learning.

    Runs as background process. Over 6 months of data accumulation,
    Grace builds comprehensive training data by:

    1. Reverse KNN: Follow domain neighbor graph
    2. TF-IDF Concepts: Extract key terms, find domains with missing terms
    3. Co-occurrence: Domains that naturally go together
    4. Semantic Gap: Missing bridges between known domains
    5. Trend Momentum: Weight recent learning activity
    6. Expertise Depth: Balance depth vs breadth
    7. Cross-Domain Transfer: Concepts that transfer across fields
    """

    # Domain neighbor graph for Reverse KNN
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

    # Concept transfer map: concepts that bridge domains
    CONCEPT_TRANSFERS = {
        "optimization": ["ai_ml", "business", "devops", "mathematics"],
        "automation": ["devops", "ai_ml", "business", "testing"],
        "patterns": ["python", "javascript", "architecture", "ai_ml"],
        "security": ["devops", "networking", "cryptography", "compliance"],
        "testing": ["python", "javascript", "devops", "quality"],
        "scalability": ["devops", "architecture", "databases", "cloud"],
        "data_structures": ["python", "rust", "algorithms", "databases"],
        "networking": ["devops", "security", "cloud", "distributed_systems"],
        "concurrency": ["rust", "go", "python", "distributed_systems"],
        "visualization": ["data_science", "web_development", "analytics"],
    }

    # Domain co-occurrence pairs (naturally learned together)
    COOCCURRENCE_PAIRS = [
        ("python", "ai_ml", 0.9),
        ("devops", "kubernetes", 0.85),
        ("javascript", "react", 0.8),
        ("ai_ml", "mathematics", 0.8),
        ("security", "cryptography", 0.75),
        ("sales_marketing", "psychology", 0.7),
        ("data_science", "statistics", 0.85),
        ("rust", "systems_programming", 0.8),
        ("business", "finance", 0.65),
        ("web_development", "javascript", 0.85),
    ]

    def __init__(
        self,
        oracle_store: Optional[OracleVectorStore] = None,
        max_queue_size: int = 100,
    ):
        self.oracle_store = oracle_store
        self.max_queue_size = max_queue_size
        self.learning_queue: List[DiscoveryTask] = []
        self._domain_activity: Dict[str, List[datetime]] = defaultdict(list)
        self._concept_profiles: Dict[str, ConceptProfile] = {}
        logger.info("[PROACTIVE] Enhanced Discovery Engine initialized")

    # =========================================================================
    # ALGORITHM 1: TF-IDF CONCEPT EXTRACTION
    # =========================================================================

    def extract_concepts(self, domain: str) -> ConceptProfile:
        """
        Extract key concepts from a domain using TF-IDF-like scoring.

        Finds the most important terms in a domain and scores them
        by frequency and uniqueness (terms rare in other domains
        are weighted higher).
        """
        domain_content = self._get_domain_content(domain)
        all_content = self._get_all_content()

        # Word frequency in domain
        domain_words = self._tokenize(domain_content)
        domain_freq = Counter(domain_words)
        total_domain_words = len(domain_words)

        # Document frequency across all domains (how many domains use this word)
        all_domains = self._get_all_domains()
        doc_freq: Dict[str, int] = defaultdict(int)
        for d in all_domains:
            d_content = self._get_domain_content(d)
            d_words = set(self._tokenize(d_content))
            for w in d_words:
                doc_freq[w] += 1

        total_domains = max(len(all_domains), 1)

        # TF-IDF scoring
        concepts: Dict[str, float] = {}
        for word, freq in domain_freq.items():
            tf = freq / max(total_domain_words, 1)
            idf = math.log((total_domains + 1) / (doc_freq.get(word, 0) + 1)) + 1
            concepts[word] = tf * idf

        # Sort by score and keep top concepts
        sorted_concepts = dict(
            sorted(concepts.items(), key=lambda x: x[1], reverse=True)[:50]
        )

        profile = ConceptProfile(
            domain=domain,
            concepts=sorted_concepts,
            total_words=total_domain_words,
            unique_concepts=len(sorted_concepts),
            depth_score=min(total_domain_words / 1000, 1.0),
            breadth_score=len(sorted_concepts) / 50,
        )

        self._concept_profiles[domain] = profile
        return profile

    # =========================================================================
    # ALGORITHM 2: CO-OCCURRENCE MINING
    # =========================================================================

    def find_cooccurrences(self) -> List[DiscoveryTask]:
        """
        Find domains that naturally co-occur but aren't yet learned.

        If user knows Python but not AI/ML, and those co-occur at 0.9,
        suggest learning AI/ML with high priority.
        """
        known_domains = set(self._get_all_domains())
        tasks: List[DiscoveryTask] = []

        for domain_a, domain_b, strength in self.COOCCURRENCE_PAIRS:
            if domain_a in known_domains and domain_b not in known_domains:
                priority = (
                    LearningPriority.HIGH if strength >= 0.8
                    else LearningPriority.MEDIUM
                )
                tasks.append(DiscoveryTask(
                    task_id=f"cooc-{uuid.uuid4().hex[:12]}",
                    algorithm=DiscoveryAlgorithm.COOCCURRENCE,
                    priority=priority,
                    target_domain=domain_b,
                    description=(
                        f"'{domain_b}' naturally co-occurs with known "
                        f"'{domain_a}' (strength: {strength:.0%})"
                    ),
                    confidence=strength,
                    search_queries=[
                        f"{domain_b} fundamentals for {domain_a} developers",
                        f"best {domain_b} resources",
                    ],
                    source_domains=[domain_a],
                    estimated_value=strength,
                ))
            elif domain_b in known_domains and domain_a not in known_domains:
                priority = (
                    LearningPriority.HIGH if strength >= 0.8
                    else LearningPriority.MEDIUM
                )
                tasks.append(DiscoveryTask(
                    task_id=f"cooc-{uuid.uuid4().hex[:12]}",
                    algorithm=DiscoveryAlgorithm.COOCCURRENCE,
                    priority=priority,
                    target_domain=domain_a,
                    description=(
                        f"'{domain_a}' naturally co-occurs with known "
                        f"'{domain_b}' (strength: {strength:.0%})"
                    ),
                    confidence=strength,
                    search_queries=[
                        f"{domain_a} fundamentals for {domain_b} developers",
                        f"best {domain_a} resources",
                    ],
                    source_domains=[domain_b],
                    estimated_value=strength,
                ))

        return tasks

    # =========================================================================
    # ALGORITHM 3: SEMANTIC GAP DETECTION
    # =========================================================================

    def detect_semantic_gaps(self) -> List[DiscoveryTask]:
        """
        Find missing bridges between known domains.

        If user knows Python AND AI/ML but not Mathematics,
        and Mathematics bridges them, that's a semantic gap.
        """
        known_domains = set(self._get_all_domains())
        tasks: List[DiscoveryTask] = []

        # For each unknown domain, check if it bridges two known domains
        all_domain_names = set()
        for d, neighbors in self.DOMAIN_NEIGHBORS.items():
            all_domain_names.add(d)
            all_domain_names.update(neighbors)

        for candidate in all_domain_names:
            if candidate in known_domains:
                continue

            # Find how many known domains this candidate bridges
            bridge_count = 0
            bridge_domains: List[str] = []
            for known in known_domains:
                neighbors = self.DOMAIN_NEIGHBORS.get(known, [])
                if candidate in neighbors:
                    bridge_count += 1
                    bridge_domains.append(known)

            if bridge_count >= 2:
                confidence = min(bridge_count * 0.3, 0.95)
                tasks.append(DiscoveryTask(
                    task_id=f"gap-{uuid.uuid4().hex[:12]}",
                    algorithm=DiscoveryAlgorithm.SEMANTIC_GAP,
                    priority=LearningPriority.HIGH,
                    target_domain=candidate,
                    description=(
                        f"'{candidate}' bridges {bridge_count} known domains: "
                        f"{', '.join(bridge_domains[:3])}. "
                        f"Learning it connects existing knowledge."
                    ),
                    confidence=confidence,
                    search_queries=[
                        f"{candidate} connecting {bridge_domains[0]} and {bridge_domains[1]}",
                        f"{candidate} fundamentals",
                    ],
                    source_domains=bridge_domains,
                    estimated_value=confidence,
                ))

        return tasks

    # =========================================================================
    # ALGORITHM 4: TREND MOMENTUM SCORING
    # =========================================================================

    def record_domain_activity(self, domain: str) -> None:
        """Record learning activity for a domain."""
        self._domain_activity[domain].append(datetime.now(timezone.utc))

    def score_trend_momentum(self) -> List[Tuple[str, float]]:
        """
        Score domains by recent learning momentum.

        Domains with recent activity get higher momentum scores.
        Exponential decay: recent activity counts more.
        """
        now = datetime.now(timezone.utc)
        scored: List[Tuple[str, float]] = []

        for domain, timestamps in self._domain_activity.items():
            if not timestamps:
                continue
            score = 0.0
            for ts in timestamps:
                days_ago = (now - ts).total_seconds() / 86400
                score += math.exp(-days_ago / 30)  # 30-day half-life
            scored.append((domain, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def suggest_momentum_based(self) -> List[DiscoveryTask]:
        """Suggest learning based on momentum (deepen active domains)."""
        momentum = self.score_trend_momentum()
        tasks: List[DiscoveryTask] = []

        for domain, score in momentum[:5]:
            if score > 0.5:
                tasks.append(DiscoveryTask(
                    task_id=f"mom-{uuid.uuid4().hex[:12]}",
                    algorithm=DiscoveryAlgorithm.TREND_MOMENTUM,
                    priority=LearningPriority.MEDIUM,
                    target_domain=domain,
                    description=(
                        f"Active learning momentum in '{domain}' "
                        f"(score: {score:.2f}). Deepen knowledge."
                    ),
                    confidence=min(score / 5, 0.9),
                    search_queries=[
                        f"advanced {domain} techniques",
                        f"{domain} best practices 2025",
                    ],
                    source_domains=[domain],
                    estimated_value=min(score / 5, 0.9),
                ))

        return tasks

    # =========================================================================
    # ALGORITHM 5: EXPERTISE DEPTH SCORING
    # =========================================================================

    def score_expertise_depth(self) -> Dict[str, Dict[str, float]]:
        """
        Score each domain's depth vs breadth.

        Returns recommendation on whether to go deeper or broader.
        """
        scores: Dict[str, Dict[str, float]] = {}

        for domain in self._get_all_domains():
            profile = self._concept_profiles.get(domain)
            if not profile:
                profile = self.extract_concepts(domain)

            # Depth: total words / expected depth
            depth = profile.depth_score
            # Breadth: unique concepts / expected breadth
            breadth = profile.breadth_score

            if depth > breadth * 1.5:
                recommendation = "broaden"
                balance = breadth / max(depth, 0.01)
            elif breadth > depth * 1.5:
                recommendation = "deepen"
                balance = depth / max(breadth, 0.01)
            else:
                recommendation = "balanced"
                balance = 1.0

            scores[domain] = {
                "depth": depth,
                "breadth": breadth,
                "balance": balance,
                "recommendation": recommendation,
            }

        return scores

    # =========================================================================
    # ALGORITHM 6: CROSS-DOMAIN TRANSFER DETECTION
    # =========================================================================

    def detect_transferable_concepts(self) -> List[DiscoveryTask]:
        """
        Find concepts that transfer across domains.

        "Optimization" applies to AI/ML, business, DevOps, math.
        If user knows optimization in AI/ML, suggest learning it
        in the business context too.
        """
        known_domains = set(self._get_all_domains())
        tasks: List[DiscoveryTask] = []

        for concept, domains in self.CONCEPT_TRANSFERS.items():
            known_with_concept = [d for d in domains if d in known_domains]
            unknown_with_concept = [d for d in domains if d not in known_domains]

            if known_with_concept and unknown_with_concept:
                for target in unknown_with_concept[:2]:
                    tasks.append(DiscoveryTask(
                        task_id=f"xfer-{uuid.uuid4().hex[:12]}",
                        algorithm=DiscoveryAlgorithm.CROSS_DOMAIN_TRANSFER,
                        priority=LearningPriority.MEDIUM,
                        target_domain=target,
                        description=(
                            f"Concept '{concept}' transfers from "
                            f"{', '.join(known_with_concept[:2])} to '{target}'"
                        ),
                        confidence=0.7,
                        search_queries=[
                            f"{concept} in {target}",
                            f"{target} {concept} techniques",
                        ],
                        source_domains=known_with_concept,
                        estimated_value=0.65,
                        metadata={"transfer_concept": concept},
                    ))

        return tasks

    # =========================================================================
    # MASTER DISCOVERY: RUN ALL ALGORITHMS
    # =========================================================================

    def run_full_discovery(self) -> LearningQueueState:
        """
        Run all 7 discovery algorithms and build a prioritized learning queue.

        Returns the current state of the learning queue.
        """
        all_tasks: List[DiscoveryTask] = []

        # 1. Reverse KNN (already done in reverse_knn_discovery module)
        knn_tasks = self._run_reverse_knn()
        all_tasks.extend(knn_tasks)

        # 2. Co-occurrence Mining
        cooc_tasks = self.find_cooccurrences()
        all_tasks.extend(cooc_tasks)

        # 3. Semantic Gap Detection
        gap_tasks = self.detect_semantic_gaps()
        all_tasks.extend(gap_tasks)

        # 4. Trend Momentum
        momentum_tasks = self.suggest_momentum_based()
        all_tasks.extend(momentum_tasks)

        # 5. Cross-Domain Transfer
        transfer_tasks = self.detect_transferable_concepts()
        all_tasks.extend(transfer_tasks)

        # Deduplicate by target domain
        seen_domains: Set[str] = set()
        unique_tasks: List[DiscoveryTask] = []
        for task in all_tasks:
            if task.target_domain not in seen_domains:
                seen_domains.add(task.target_domain)
                unique_tasks.append(task)

        # Sort by priority and confidence
        priority_order = {
            LearningPriority.CRITICAL: 0,
            LearningPriority.HIGH: 1,
            LearningPriority.MEDIUM: 2,
            LearningPriority.LOW: 3,
            LearningPriority.BACKGROUND: 4,
        }
        unique_tasks.sort(
            key=lambda t: (priority_order[t.priority], -t.confidence)
        )

        # Limit queue size
        self.learning_queue = unique_tasks[:self.max_queue_size]

        logger.info(
            f"[PROACTIVE] Full discovery: {len(self.learning_queue)} tasks "
            f"from {len(all_tasks)} candidates"
        )

        return self.get_queue_state()

    def _run_reverse_knn(self) -> List[DiscoveryTask]:
        """Run reverse KNN algorithm."""
        known = set(self._get_all_domains())
        tasks: List[DiscoveryTask] = []

        for domain in known:
            neighbors = self.DOMAIN_NEIGHBORS.get(domain, [])
            for neighbor in neighbors:
                if neighbor not in known:
                    tasks.append(DiscoveryTask(
                        task_id=f"knn-{uuid.uuid4().hex[:12]}",
                        algorithm=DiscoveryAlgorithm.REVERSE_KNN,
                        priority=LearningPriority.MEDIUM,
                        target_domain=neighbor,
                        description=f"KNN neighbor of '{domain}'",
                        confidence=0.6,
                        search_queries=[f"{neighbor} tutorial", f"best {neighbor} resources"],
                        source_domains=[domain],
                        estimated_value=0.6,
                    ))

        return tasks

    # =========================================================================
    # QUEUE MANAGEMENT
    # =========================================================================

    def get_next_task(self) -> Optional[DiscoveryTask]:
        """Get the next task from the learning queue."""
        for task in self.learning_queue:
            if task.status == "queued":
                return task
        return None

    def mark_task_status(self, task_id: str, status: str) -> bool:
        """Update task status."""
        for task in self.learning_queue:
            if task.task_id == task_id:
                task.status = status
                return True
        return False

    def get_queue_state(self) -> LearningQueueState:
        """Get current state of the learning queue."""
        by_priority: Dict[str, int] = defaultdict(int)
        by_algorithm: Dict[str, int] = defaultdict(int)
        by_status: Dict[str, int] = defaultdict(int)
        total_value = 0.0

        for task in self.learning_queue:
            by_priority[task.priority.value] += 1
            by_algorithm[task.algorithm.value] += 1
            by_status[task.status] += 1
            total_value += task.estimated_value

        return LearningQueueState(
            total_tasks=len(self.learning_queue),
            by_priority=dict(by_priority),
            by_algorithm=dict(by_algorithm),
            by_status=dict(by_status),
            estimated_total_value=total_value,
            next_task=self.get_next_task(),
        )

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_domain_content(self, domain: str) -> str:
        """Get concatenated content for a domain."""
        if self.oracle_store:
            records = self.oracle_store.search_by_domain(domain, limit=50)
            return " ".join(r.content for r in records)
        return ""

    def _get_all_content(self) -> str:
        """Get all content across all domains."""
        if self.oracle_store:
            return " ".join(r.content for r in self.oracle_store.records.values())
        return ""

    def _get_all_domains(self) -> List[str]:
        """Get all known domains."""
        if self.oracle_store:
            return self.oracle_store.get_all_domains()
        return list(self._domain_activity.keys())

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization: lowercase, split, filter short words."""
        words = text.lower().split()
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "and", "or", "but", "if", "then", "else", "when", "at",
            "by", "for", "with", "about", "against", "between", "through",
            "to", "from", "in", "on", "of", "it", "its", "this", "that",
            "these", "those", "not", "no", "nor", "so", "very", "just",
        }
        return [
            w.strip(".,!?:;()[]{}\"'")
            for w in words
            if len(w) > 2 and w not in stop_words
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        state = self.get_queue_state()
        return {
            "queue_size": state.total_tasks,
            "by_priority": state.by_priority,
            "by_algorithm": state.by_algorithm,
            "by_status": state.by_status,
            "estimated_total_value": state.estimated_total_value,
            "concept_profiles": len(self._concept_profiles),
            "active_domains": len(self._domain_activity),
        }
