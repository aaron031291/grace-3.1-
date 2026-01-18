"""
Enhanced Oracle Memory System

Unified memory with:
1. Multi-hop reasoning chains with evidence links
2. Calibration-based confidence (ECE tracking)
3. Feedback loops (outcome → learning → calibration)
4. Unified memory items across all types
5. Knowledge freshness decay
6. Priority queue: impact × uncertainty × freshness
7. Cross-source correlation
8. Pattern evolution tracking
"""

import logging
import asyncio
import json
import hashlib
import math
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# EVIDENCE & REASONING CHAINS
# =============================================================================

class EvidenceKind(str, Enum):
    """Types of evidence for reasoning chains."""
    RESEARCH = "research"
    PATTERN = "pattern"
    CODE = "code"
    EXTERNAL = "external"
    OUTCOME = "outcome"
    CORRELATION = "correlation"
    SIMULATION = "simulation"


@dataclass
class EvidenceItem:
    """A piece of evidence supporting a claim."""
    evidence_id: str
    kind: EvidenceKind
    ref_id: str
    snippet: Optional[str] = None
    weight: float = 1.0
    source: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.evidence_id,
            "kind": self.kind.value,
            "ref_id": self.ref_id,
            "snippet": self.snippet[:200] if self.snippet else None,
            "weight": self.weight,
            "source": self.source
        }


@dataclass
class ReasoningStep:
    """A step in multi-hop reasoning chain."""
    step: int
    claim: str
    supporting_evidence: List[str] = field(default_factory=list)
    confidence: float = 0.5
    method: str = "inference"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "claim": self.claim,
            "evidence": self.supporting_evidence,
            "confidence": self.confidence,
            "method": self.method
        }


@dataclass
class ReasoningChain:
    """Multi-hop reasoning chain with evidence."""
    chain_id: str
    hypothesis: str
    steps: List[ReasoningStep] = field(default_factory=list)
    evidence: List[EvidenceItem] = field(default_factory=list)
    final_confidence: float = 0.5
    verified: Optional[bool] = None
    verified_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "hypothesis": self.hypothesis,
            "steps": [s.to_dict() for s in self.steps],
            "evidence_count": len(self.evidence),
            "final_confidence": self.final_confidence,
            "verified": self.verified
        }


# =============================================================================
# CALIBRATION SYSTEM (ECE Tracking)
# =============================================================================

@dataclass
class CalibrationBucket:
    """A bucket for confidence calibration."""
    lower: float
    upper: float
    n: int = 0
    n_correct: int = 0
    sum_predicted: float = 0.0
    sum_observed: float = 0.0
    
    @property
    def avg_predicted(self) -> float:
        return self.sum_predicted / self.n if self.n > 0 else 0.0
    
    @property
    def avg_observed(self) -> float:
        return self.sum_observed / self.n if self.n > 0 else 0.0
    
    @property
    def accuracy(self) -> float:
        return self.n_correct / self.n if self.n > 0 else 0.0
    
    @property
    def calibration_error(self) -> float:
        return abs(self.avg_predicted - self.accuracy)


class ConfidenceCalibrator:
    """
    Tracks and calibrates confidence scores.
    
    Uses Expected Calibration Error (ECE) to measure and correct
    overconfidence/underconfidence per insight type.
    """
    
    def __init__(self, n_buckets: int = 10):
        self.n_buckets = n_buckets
        self.bucket_width = 1.0 / n_buckets
        
        # Buckets per insight type
        self._buckets: Dict[str, List[CalibrationBucket]] = defaultdict(
            lambda: [
                CalibrationBucket(lower=i/n_buckets, upper=(i+1)/n_buckets)
                for i in range(n_buckets)
            ]
        )
        
        # Calibration coefficients per type (linear: p_cal = a*p + b)
        self._coefficients: Dict[str, Tuple[float, float]] = {}
        
        # History for trend analysis
        self._history: List[Dict] = []
    
    def get_bucket_index(self, confidence: float) -> int:
        """Get bucket index for a confidence score."""
        idx = int(confidence / self.bucket_width)
        return min(idx, self.n_buckets - 1)
    
    def record_outcome(
        self,
        insight_type: str,
        predicted_confidence: float,
        was_correct: bool
    ):
        """Record an outcome for calibration."""
        buckets = self._buckets[insight_type]
        idx = self.get_bucket_index(predicted_confidence)
        
        buckets[idx].n += 1
        buckets[idx].sum_predicted += predicted_confidence
        buckets[idx].sum_observed += 1.0 if was_correct else 0.0
        if was_correct:
            buckets[idx].n_correct += 1
        
        # Record history
        self._history.append({
            "type": insight_type,
            "predicted": predicted_confidence,
            "observed": 1.0 if was_correct else 0.0,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Trim history
        if len(self._history) > 10000:
            self._history = self._history[-5000:]
        
        # Update calibration coefficients periodically
        if buckets[idx].n % 50 == 0:
            self._update_coefficients(insight_type)
    
    def calibrate(self, insight_type: str, raw_confidence: float) -> float:
        """Apply calibration to raw confidence score."""
        if insight_type not in self._coefficients:
            return raw_confidence
        
        a, b = self._coefficients[insight_type]
        calibrated = a * raw_confidence + b
        return max(0.01, min(0.99, calibrated))
    
    def _update_coefficients(self, insight_type: str):
        """Update calibration coefficients using linear regression."""
        buckets = self._buckets[insight_type]
        
        # Collect data points
        x_vals, y_vals, weights = [], [], []
        for bucket in buckets:
            if bucket.n >= 5:  # Need minimum samples
                x_vals.append(bucket.avg_predicted)
                y_vals.append(bucket.accuracy)
                weights.append(bucket.n)
        
        if len(x_vals) < 3:
            return
        
        # Weighted linear regression
        sum_w = sum(weights)
        sum_wx = sum(w * x for w, x in zip(weights, x_vals))
        sum_wy = sum(w * y for w, y in zip(weights, y_vals))
        sum_wxx = sum(w * x * x for w, x in zip(weights, x_vals))
        sum_wxy = sum(w * x * y for w, x, y in zip(weights, x_vals, y_vals))
        
        denom = sum_w * sum_wxx - sum_wx * sum_wx
        if abs(denom) < 1e-10:
            return
        
        a = (sum_w * sum_wxy - sum_wx * sum_wy) / denom
        b = (sum_wy - a * sum_wx) / sum_w
        
        # Sanity check
        if 0.5 < a < 2.0 and -0.5 < b < 0.5:
            self._coefficients[insight_type] = (a, b)
    
    def compute_ece(self, insight_type: str = None) -> float:
        """Compute Expected Calibration Error."""
        if insight_type:
            buckets = self._buckets[insight_type]
        else:
            # Aggregate all buckets
            all_buckets = []
            for type_buckets in self._buckets.values():
                all_buckets.extend(type_buckets)
            buckets = all_buckets
        
        total_n = sum(b.n for b in buckets)
        if total_n == 0:
            return 0.0
        
        ece = sum(b.n * b.calibration_error for b in buckets) / total_n
        return ece
    
    def get_calibration_report(self) -> Dict[str, Any]:
        """Get full calibration report."""
        report = {
            "overall_ece": self.compute_ece(),
            "by_type": {},
            "coefficients": self._coefficients,
            "history_size": len(self._history)
        }
        
        for insight_type, buckets in self._buckets.items():
            total_n = sum(b.n for b in buckets)
            total_correct = sum(b.n_correct for b in buckets)
            
            report["by_type"][insight_type] = {
                "ece": self.compute_ece(insight_type),
                "total_predictions": total_n,
                "accuracy": total_correct / total_n if total_n > 0 else 0,
                "buckets": [
                    {
                        "range": f"{b.lower:.1f}-{b.upper:.1f}",
                        "n": b.n,
                        "accuracy": b.accuracy,
                        "avg_predicted": b.avg_predicted
                    }
                    for b in buckets if b.n > 0
                ]
            }
        
        return report


# =============================================================================
# UNIFIED MEMORY ITEM
# =============================================================================

class MemoryItemType(str, Enum):
    """Types of memory items."""
    RESEARCH = "research"
    PATTERN = "pattern"
    INSIGHT = "insight"
    OUTCOME = "outcome"
    SIMULATION = "simulation"
    CORRELATION = "correlation"
    TEMPLATE = "template"
    EXTERNAL = "external"


@dataclass
class UnifiedMemoryItem:
    """
    Unified memory item that can represent any knowledge.
    
    All memory goes through this format for consistent:
    - Indexing
    - Retrieval
    - Freshness decay
    - Priority scoring
    """
    memory_id: str
    item_type: MemoryItemType
    title: str
    content: str
    
    # Evidence and reasoning
    evidence: List[EvidenceItem] = field(default_factory=list)
    reasoning_chain: Optional[ReasoningChain] = None
    
    # Confidence and calibration
    raw_confidence: float = 0.5
    calibrated_confidence: float = 0.5
    
    # Freshness
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_validated: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    freshness_half_life_days: float = 30.0
    
    # Usage and impact
    usage_count: int = 0
    impact_score: float = 0.5
    
    # Source tracking
    source: Optional[str] = None
    source_url: Optional[str] = None
    genesis_key_id: Optional[str] = None
    
    # Correlation
    correlated_with: List[str] = field(default_factory=list)
    correlation_confidence: float = 0.0
    
    # Version tracking
    version: int = 1
    previous_versions: List[Dict] = field(default_factory=list)
    
    # Tags and metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Embedding (cached)
    embedding: Optional[List[float]] = None
    
    @property
    def freshness(self) -> float:
        """Compute freshness score with exponential decay."""
        reference_time = self.last_validated or self.created_at
        days_old = (datetime.utcnow() - reference_time).total_seconds() / 86400
        return math.exp(-days_old / self.freshness_half_life_days)
    
    @property
    def priority_score(self) -> float:
        """Compute priority: impact × uncertainty × freshness × usage."""
        uncertainty = 1.0 - self.calibrated_confidence
        usage_factor = math.log1p(self.usage_count) / 10.0 + 0.5
        freshness_penalty = 1.0 - (self.freshness * 0.5)  # Stale items get priority
        
        return self.impact_score * uncertainty * freshness_penalty * usage_factor
    
    def record_access(self):
        """Record an access to this memory."""
        self.last_accessed = datetime.utcnow()
        self.usage_count += 1
    
    def update_version(self, new_content: str, new_confidence: float):
        """Create new version while preserving history."""
        self.previous_versions.append({
            "version": self.version,
            "content": self.content[:500],
            "confidence": self.calibrated_confidence,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Trim history
        if len(self.previous_versions) > 10:
            self.previous_versions = self.previous_versions[-10:]
        
        self.version += 1
        self.content = new_content
        self.raw_confidence = new_confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "type": self.item_type.value,
            "title": self.title,
            "content": self.content[:500],
            "raw_confidence": self.raw_confidence,
            "calibrated_confidence": self.calibrated_confidence,
            "freshness": self.freshness,
            "priority_score": self.priority_score,
            "usage_count": self.usage_count,
            "impact_score": self.impact_score,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "version": self.version,
            "correlated_with": self.correlated_with[:5],
            "tags": self.tags
        }


# =============================================================================
# IMPACT SCORING
# =============================================================================

class ImpactCategory(str, Enum):
    """Impact categories ordered by importance."""
    SECURITY = "security"
    CASCADING = "cascading"
    DEPENDENCY = "dependency"
    FAILURE = "failure"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    PATTERN = "pattern"
    STYLE = "style"


IMPACT_WEIGHTS = {
    ImpactCategory.SECURITY: 1.0,
    ImpactCategory.CASCADING: 0.95,
    ImpactCategory.DEPENDENCY: 0.85,
    ImpactCategory.FAILURE: 0.8,
    ImpactCategory.PERFORMANCE: 0.7,
    ImpactCategory.ARCHITECTURE: 0.65,
    ImpactCategory.PATTERN: 0.5,
    ImpactCategory.STYLE: 0.3,
}


def compute_impact_score(
    tags: List[str],
    content: str,
    affected_files: List[str] = None
) -> float:
    """Compute impact score based on content analysis."""
    score = 0.5  # Default
    
    content_lower = content.lower()
    
    # Check for high-impact keywords
    if any(kw in content_lower for kw in ["security", "vulnerability", "exploit", "cve"]):
        score = max(score, IMPACT_WEIGHTS[ImpactCategory.SECURITY])
    
    if any(kw in content_lower for kw in ["cascade", "propagate", "chain", "domino"]):
        score = max(score, IMPACT_WEIGHTS[ImpactCategory.CASCADING])
    
    if any(kw in content_lower for kw in ["dependency", "package", "version", "upgrade"]):
        score = max(score, IMPACT_WEIGHTS[ImpactCategory.DEPENDENCY])
    
    if any(kw in content_lower for kw in ["error", "exception", "crash", "failure"]):
        score = max(score, IMPACT_WEIGHTS[ImpactCategory.FAILURE])
    
    if any(kw in content_lower for kw in ["performance", "latency", "memory", "cpu"]):
        score = max(score, IMPACT_WEIGHTS[ImpactCategory.PERFORMANCE])
    
    # Check tags
    for tag in tags:
        tag_lower = tag.lower()
        for category in ImpactCategory:
            if category.value in tag_lower:
                score = max(score, IMPACT_WEIGHTS[category])
    
    # Boost for many affected files
    if affected_files and len(affected_files) > 5:
        score = min(1.0, score * 1.2)
    
    return score


# =============================================================================
# CROSS-SOURCE CORRELATION
# =============================================================================

@dataclass
class CorrelationCluster:
    """A cluster of correlated memory items."""
    cluster_id: str
    canonical_claim: str
    member_ids: List[str] = field(default_factory=list)
    sources: Set[str] = field(default_factory=set)
    combined_confidence: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_member(self, memory_id: str, source: str, confidence: float):
        """Add a member and update combined confidence."""
        if memory_id not in self.member_ids:
            self.member_ids.append(memory_id)
            self.sources.add(source)
            
            # Independent corroboration increases confidence
            # P(A) from multiple independent sources
            n_sources = len(self.sources)
            if n_sources > 1:
                # Each independent source increases confidence
                self.combined_confidence = min(
                    0.99,
                    1.0 - (1.0 - self.combined_confidence) * (1.0 - confidence * 0.3)
                )


class CrossSourceCorrelator:
    """
    Correlates knowledge from multiple sources.
    
    Detects when GitHub, StackOverflow, and research papers
    all say the same thing → higher confidence.
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self._clusters: Dict[str, CorrelationCluster] = {}
        self._item_to_cluster: Dict[str, str] = {}
    
    async def correlate_item(
        self,
        memory_item: UnifiedMemoryItem,
        existing_items: List[UnifiedMemoryItem],
        embedder=None
    ) -> Optional[CorrelationCluster]:
        """Find or create correlation cluster for an item."""
        if not embedder or memory_item.embedding is None:
            return None
        
        best_match = None
        best_similarity = 0.0
        
        # Find most similar existing item
        for existing in existing_items:
            if existing.embedding is None:
                continue
            
            # Cosine similarity
            import numpy as np
            a = np.array(memory_item.embedding)
            b = np.array(existing.embedding)
            similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)
            
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_match = existing
        
        if best_match:
            # Add to existing cluster or create new one
            if best_match.memory_id in self._item_to_cluster:
                cluster_id = self._item_to_cluster[best_match.memory_id]
                cluster = self._clusters[cluster_id]
            else:
                # Create new cluster
                cluster = CorrelationCluster(
                    cluster_id=f"CORR-{uuid.uuid4().hex[:8]}",
                    canonical_claim=best_match.title
                )
                cluster.add_member(
                    best_match.memory_id,
                    best_match.source or "unknown",
                    best_match.calibrated_confidence
                )
                self._clusters[cluster.cluster_id] = cluster
                self._item_to_cluster[best_match.memory_id] = cluster.cluster_id
            
            # Add new item to cluster
            cluster.add_member(
                memory_item.memory_id,
                memory_item.source or "unknown",
                memory_item.calibrated_confidence
            )
            self._item_to_cluster[memory_item.memory_id] = cluster.cluster_id
            
            # Update correlation links
            memory_item.correlated_with = cluster.member_ids.copy()
            memory_item.correlation_confidence = cluster.combined_confidence
            
            return cluster
        
        return None
    
    def get_correlation_stats(self) -> Dict[str, Any]:
        """Get correlation statistics."""
        multi_source = [c for c in self._clusters.values() if len(c.sources) > 1]
        
        return {
            "total_clusters": len(self._clusters),
            "multi_source_clusters": len(multi_source),
            "avg_cluster_size": sum(len(c.member_ids) for c in self._clusters.values()) / max(1, len(self._clusters)),
            "top_clusters": [
                {
                    "id": c.cluster_id,
                    "claim": c.canonical_claim,
                    "members": len(c.member_ids),
                    "sources": list(c.sources),
                    "confidence": c.combined_confidence
                }
                for c in sorted(multi_source, key=lambda x: x.combined_confidence, reverse=True)[:10]
            ]
        }


# =============================================================================
# ENHANCED MEMORY STORE
# =============================================================================

class EnhancedOracleMemory:
    """
    Enhanced Oracle Memory System.
    
    Combines:
    - Unified memory items
    - Confidence calibration
    - Cross-source correlation
    - Priority-based learning
    - Freshness decay
    - Multi-hop reasoning
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        vector_db=None
    ):
        self.storage_path = storage_path or Path("knowledge_base/oracle/memory")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._vector_db = vector_db
        
        # Memory store
        self._memory: Dict[str, UnifiedMemoryItem] = {}
        
        # Calibration
        self.calibrator = ConfidenceCalibrator(n_buckets=10)
        
        # Correlation
        self.correlator = CrossSourceCorrelator(similarity_threshold=0.85)
        
        # Reasoning chains
        self._reasoning_chains: Dict[str, ReasoningChain] = {}
        
        # Priority queue for learning
        self._learning_priority_queue: List[str] = []
        
        # Query deduplication
        self._recent_queries: Set[str] = set()
        
        # Stats
        self._stats = {
            "total_items": 0,
            "outcomes_recorded": 0,
            "correlations_found": 0,
            "reasoning_chains": 0
        }
        
        # Load persisted state
        self._load_state()
        
        logger.info("[ENHANCED-MEMORY] Oracle memory initialized")
    
    # =========================================================================
    # MEMORY OPERATIONS
    # =========================================================================
    
    async def store(
        self,
        item: UnifiedMemoryItem,
        embedder=None
    ) -> UnifiedMemoryItem:
        """Store a memory item with calibration and correlation."""
        # Compute impact score
        item.impact_score = compute_impact_score(
            item.tags,
            item.content,
            item.metadata.get("affected_files", [])
        )
        
        # Apply calibration
        item.calibrated_confidence = self.calibrator.calibrate(
            item.item_type.value,
            item.raw_confidence
        )
        
        # Generate embedding
        if embedder and item.embedding is None:
            try:
                text = f"{item.title} {item.content[:500]}"
                item.embedding = await embedder.embed(text)
            except Exception as e:
                logger.debug(f"[ENHANCED-MEMORY] Embedding failed: {e}")
        
        # Cross-source correlation
        if item.embedding:
            existing = list(self._memory.values())
            cluster = await self.correlator.correlate_item(item, existing, embedder)
            if cluster:
                self._stats["correlations_found"] += 1
                logger.debug(f"[ENHANCED-MEMORY] Correlated with cluster {cluster.cluster_id}")
        
        # Store
        self._memory[item.memory_id] = item
        self._stats["total_items"] = len(self._memory)
        
        # Update priority queue
        self._update_priority_queue()
        
        # Index in vector DB
        if self._vector_db and item.embedding:
            await self._index_item(item)
        
        # Persist
        self._persist_item(item)
        
        return item
    
    async def retrieve(
        self,
        query: str,
        item_types: List[MemoryItemType] = None,
        limit: int = 10,
        min_confidence: float = 0.0,
        embedder=None
    ) -> List[UnifiedMemoryItem]:
        """Retrieve memory items by semantic similarity."""
        results = []
        
        if self._vector_db and embedder:
            try:
                embedding = await embedder.embed(query)
                
                # Build filter
                filter_dict = {}
                if item_types:
                    filter_dict["type"] = {"$in": [t.value for t in item_types]}
                
                search_results = await self._vector_db.search(
                    collection_name="oracle_memory",
                    query_vector=embedding,
                    limit=limit * 2,  # Over-fetch to filter
                    query_filter=filter_dict if filter_dict else None
                )
                
                for result in search_results:
                    if result.id in self._memory:
                        item = self._memory[result.id]
                        if item.calibrated_confidence >= min_confidence:
                            item.record_access()
                            results.append(item)
                            if len(results) >= limit:
                                break
                
            except Exception as e:
                logger.debug(f"[ENHANCED-MEMORY] Vector search failed: {e}")
        
        # Fallback to keyword search
        if not results:
            query_lower = query.lower()
            scored = []
            for item in self._memory.values():
                if item_types and item.item_type not in item_types:
                    continue
                if item.calibrated_confidence < min_confidence:
                    continue
                
                # Simple keyword matching
                score = 0
                if query_lower in item.title.lower():
                    score += 2
                if query_lower in item.content.lower():
                    score += 1
                
                if score > 0:
                    scored.append((item, score))
            
            scored.sort(key=lambda x: (x[1], x[0].priority_score), reverse=True)
            results = [item for item, _ in scored[:limit]]
            
            for item in results:
                item.record_access()
        
        return results
    
    async def retrieve_evidence_chain(
        self,
        query: str,
        max_hops: int = 3,
        embedder=None
    ) -> ReasoningChain:
        """Build multi-hop evidence chain for a query."""
        chain = ReasoningChain(
            chain_id=f"CHAIN-{uuid.uuid4().hex[:8]}",
            hypothesis=query
        )
        
        current_query = query
        visited_ids = set()
        
        for hop in range(max_hops):
            # Retrieve relevant items
            items = await self.retrieve(
                current_query,
                limit=3,
                embedder=embedder
            )
            
            for item in items:
                if item.memory_id in visited_ids:
                    continue
                visited_ids.add(item.memory_id)
                
                # Add evidence
                evidence = EvidenceItem(
                    evidence_id=f"EV-{uuid.uuid4().hex[:6]}",
                    kind=EvidenceKind(item.item_type.value) if item.item_type.value in [e.value for e in EvidenceKind] else EvidenceKind.EXTERNAL,
                    ref_id=item.memory_id,
                    snippet=item.content[:200],
                    weight=item.calibrated_confidence,
                    source=item.source
                )
                chain.evidence.append(evidence)
                
                # Add reasoning step
                step = ReasoningStep(
                    step=hop + 1,
                    claim=f"Evidence from {item.source}: {item.title}",
                    supporting_evidence=[evidence.evidence_id],
                    confidence=item.calibrated_confidence,
                    method="semantic_retrieval"
                )
                chain.steps.append(step)
                
                # Use item content to refine next query
                if hop < max_hops - 1 and item.tags:
                    current_query = f"{query} {' '.join(item.tags[:3])}"
        
        # Compute final confidence
        if chain.evidence:
            chain.final_confidence = sum(e.weight for e in chain.evidence) / len(chain.evidence)
        
        # Store chain
        self._reasoning_chains[chain.chain_id] = chain
        self._stats["reasoning_chains"] = len(self._reasoning_chains)
        
        return chain
    
    # =========================================================================
    # OUTCOME FEEDBACK LOOP
    # =========================================================================
    
    async def record_outcome(
        self,
        memory_id: str,
        was_correct: bool,
        actual_outcome: Optional[str] = None
    ):
        """Record outcome for calibration and learning."""
        if memory_id not in self._memory:
            return
        
        item = self._memory[memory_id]
        
        # Update calibration
        self.calibrator.record_outcome(
            item.item_type.value,
            item.raw_confidence,
            was_correct
        )
        
        # Update item
        item.last_validated = datetime.utcnow()
        
        if was_correct:
            # Reinforce
            item.raw_confidence = min(0.99, item.raw_confidence + 0.02)
        else:
            # Penalize
            item.raw_confidence = max(0.1, item.raw_confidence - 0.05)
        
        # Re-calibrate
        item.calibrated_confidence = self.calibrator.calibrate(
            item.item_type.value,
            item.raw_confidence
        )
        
        # Store outcome as memory item
        outcome_item = UnifiedMemoryItem(
            memory_id=f"OUTCOME-{uuid.uuid4().hex[:8]}",
            item_type=MemoryItemType.OUTCOME,
            title=f"Outcome: {item.title}",
            content=f"Prediction was {'correct' if was_correct else 'incorrect'}. {actual_outcome or ''}",
            raw_confidence=1.0,
            source="internal",
            tags=["outcome", "verification", item.item_type.value],
            metadata={
                "original_memory_id": memory_id,
                "was_correct": was_correct,
                "original_confidence": item.raw_confidence
            }
        )
        outcome_item.correlated_with = [memory_id]
        
        await self.store(outcome_item)
        
        self._stats["outcomes_recorded"] += 1
        
        logger.info(f"[ENHANCED-MEMORY] Recorded outcome for {memory_id}: {'correct' if was_correct else 'incorrect'}")
    
    # =========================================================================
    # PRIORITY QUEUE
    # =========================================================================
    
    def _update_priority_queue(self):
        """Update priority queue based on impact × uncertainty × freshness."""
        scored = []
        for item in self._memory.values():
            scored.append((item.memory_id, item.priority_score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        self._learning_priority_queue = [id for id, _ in scored[:100]]
    
    def get_priority_items(self, limit: int = 10) -> List[UnifiedMemoryItem]:
        """Get highest priority items for learning/expansion."""
        items = []
        for memory_id in self._learning_priority_queue[:limit]:
            if memory_id in self._memory:
                items.append(self._memory[memory_id])
        return items
    
    def get_expansion_targets(self) -> List[Dict[str, Any]]:
        """Get items that need expansion (high uncertainty, high impact, stale)."""
        targets = []
        
        for item in self._memory.values():
            # Target criteria
            uncertainty = 1.0 - item.calibrated_confidence
            staleness = 1.0 - item.freshness
            
            if uncertainty > 0.4 or staleness > 0.5:
                targets.append({
                    "memory_id": item.memory_id,
                    "title": item.title,
                    "source": item.source,
                    "uncertainty": uncertainty,
                    "staleness": staleness,
                    "impact": item.impact_score,
                    "priority": item.priority_score,
                    "suggested_query": f"{item.title} {' '.join(item.tags[:3])}"
                })
        
        targets.sort(key=lambda x: x["priority"], reverse=True)
        return targets[:20]
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    def _persist_item(self, item: UnifiedMemoryItem):
        """Persist item to disk."""
        try:
            file_path = self.storage_path / f"{item.memory_id}.json"
            data = item.to_dict()
            data["embedding"] = None  # Don't persist embedding
            
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"[ENHANCED-MEMORY] Persist failed: {e}")
    
    async def _index_item(self, item: UnifiedMemoryItem):
        """Index item in vector DB."""
        if not self._vector_db or not item.embedding:
            return
        
        try:
            await self._vector_db.upsert(
                collection_name="oracle_memory",
                points=[{
                    "id": item.memory_id,
                    "vector": item.embedding,
                    "payload": {
                        "type": item.item_type.value,
                        "title": item.title,
                        "source": item.source,
                        "confidence": item.calibrated_confidence,
                        "impact": item.impact_score,
                        "freshness": item.freshness
                    }
                }]
            )
        except Exception as e:
            logger.debug(f"[ENHANCED-MEMORY] Index failed: {e}")
    
    def _load_state(self):
        """Load persisted state."""
        try:
            # Load calibration state
            cal_path = self.storage_path / "calibration.json"
            if cal_path.exists():
                with open(cal_path) as f:
                    data = json.load(f)
                    self.calibrator._coefficients = {
                        k: tuple(v) for k, v in data.get("coefficients", {}).items()
                    }
        except Exception as e:
            logger.debug(f"[ENHANCED-MEMORY] Load state failed: {e}")
    
    def save_state(self):
        """Save calibration and correlation state."""
        try:
            cal_path = self.storage_path / "calibration.json"
            with open(cal_path, "w") as f:
                json.dump({
                    "coefficients": self.calibrator._coefficients,
                    "report": self.calibrator.get_calibration_report()
                }, f, indent=2)
            
            corr_path = self.storage_path / "correlations.json"
            with open(corr_path, "w") as f:
                json.dump(self.correlator.get_correlation_stats(), f, indent=2)
                
        except Exception as e:
            logger.warning(f"[ENHANCED-MEMORY] Save state failed: {e}")
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        return {
            **self._stats,
            "calibration": self.calibrator.get_calibration_report(),
            "correlation": self.correlator.get_correlation_stats(),
            "priority_queue_size": len(self._learning_priority_queue),
            "by_type": {
                t.value: len([i for i in self._memory.values() if i.item_type == t])
                for t in MemoryItemType
            },
            "avg_confidence": sum(i.calibrated_confidence for i in self._memory.values()) / max(1, len(self._memory)),
            "avg_freshness": sum(i.freshness for i in self._memory.values()) / max(1, len(self._memory))
        }


# =============================================================================
# SINGLETON
# =============================================================================

_enhanced_memory_instance: Optional[EnhancedOracleMemory] = None


def get_enhanced_oracle_memory(
    storage_path: Optional[Path] = None,
    vector_db=None
) -> EnhancedOracleMemory:
    """Get singleton enhanced oracle memory."""
    global _enhanced_memory_instance
    
    if _enhanced_memory_instance is None:
        _enhanced_memory_instance = EnhancedOracleMemory(
            storage_path=storage_path,
            vector_db=vector_db
        )
    
    return _enhanced_memory_instance
