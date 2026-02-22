"""
Magma Memory - RRF Fusion (Reciprocal Rank Fusion)

Combines results from multiple retrieval sources:
1. Multiple relation graphs (semantic, temporal, causal, entity)
2. Vector similarity search
3. Keyword/BM25 search
4. Graph traversal results

RRF formula: score(d) = Σ 1 / (k + rank_i(d))
where k is a constant (typically 60) and rank_i(d) is the rank of document d in result list i.

This provides a robust way to merge rankings without requiring score normalization.

Classes:
- `RetrievalResult`
- `FusedResult`
- `FusionMethod`
- `RRFFusion`
- `WeightedRRFFusion`
- `CombSUMFusion`
- `CombMNZFusion`
- `InterleavingFusion`
- `MagmaFusion`

Key Methods:
- `fuse()`
- `set_source_weight()`
- `set_source_weights()`
- `fuse()`
- `fuse()`
- `fuse()`
- `fuse()`
- `fuse()`
- `fuse_with_limit()`
- `set_method()`
- `set_source_weight()`
- `create_retrieval_results()`
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from enum import Enum
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A single result from a retrieval source."""
    id: str
    content: str
    score: float  # Original score from source
    rank: int  # Rank within source (1-indexed)
    source: str  # Source name (e.g., "semantic_graph", "vector_search")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FusedResult:
    """A result after RRF fusion."""
    id: str
    content: str
    rrf_score: float  # Combined RRF score
    source_scores: Dict[str, float]  # Original scores by source
    source_ranks: Dict[str, int]  # Ranks by source
    sources: List[str]  # Sources that contributed
    metadata: Dict[str, Any] = field(default_factory=dict)


class FusionMethod(Enum):
    """Available fusion methods."""
    RRF = "rrf"  # Reciprocal Rank Fusion
    WEIGHTED_RRF = "weighted_rrf"  # RRF with source weights
    COMBSUM = "combsum"  # Sum of normalized scores
    COMBMNZ = "combmnz"  # CombSUM * number of sources
    BORDA = "borda"  # Borda count
    INTERLEAVING = "interleaving"  # Round-robin interleaving


class RRFFusion:
    """
    Reciprocal Rank Fusion implementation.

    Combines multiple ranked result lists into a single ranking.
    Robust to score scale differences between sources.
    """

    def __init__(self, k: int = 60):
        """
        Initialize RRF Fusion.

        Args:
            k: RRF constant (default 60, as per original paper)
        """
        self.k = k
        logger.info(f"[MAGMA-RRF] Initialized with k={k}")

    def fuse(
        self,
        result_lists: Dict[str, List[RetrievalResult]]
    ) -> List[FusedResult]:
        """
        Fuse multiple result lists using RRF.

        Args:
            result_lists: Dict mapping source name to list of results

        Returns:
            List of FusedResult sorted by RRF score (descending)
        """
        # Collect all unique document IDs
        doc_scores: Dict[str, float] = defaultdict(float)
        doc_source_scores: Dict[str, Dict[str, float]] = defaultdict(dict)
        doc_source_ranks: Dict[str, Dict[str, int]] = defaultdict(dict)
        doc_content: Dict[str, str] = {}
        doc_metadata: Dict[str, Dict[str, Any]] = defaultdict(dict)
        doc_sources: Dict[str, List[str]] = defaultdict(list)

        for source_name, results in result_lists.items():
            for result in results:
                # Calculate RRF contribution: 1 / (k + rank)
                rrf_contribution = 1.0 / (self.k + result.rank)
                doc_scores[result.id] += rrf_contribution

                # Track source information
                doc_source_scores[result.id][source_name] = result.score
                doc_source_ranks[result.id][source_name] = result.rank
                doc_content[result.id] = result.content
                doc_metadata[result.id].update(result.metadata)
                doc_sources[result.id].append(source_name)

        # Create fused results
        fused_results = []
        for doc_id, rrf_score in doc_scores.items():
            fused_results.append(FusedResult(
                id=doc_id,
                content=doc_content.get(doc_id, ""),
                rrf_score=rrf_score,
                source_scores=doc_source_scores[doc_id],
                source_ranks=doc_source_ranks[doc_id],
                sources=doc_sources[doc_id],
                metadata=doc_metadata[doc_id]
            ))

        # Sort by RRF score descending
        fused_results.sort(key=lambda x: x.rrf_score, reverse=True)

        logger.debug(
            f"[MAGMA-RRF] Fused {sum(len(r) for r in result_lists.values())} results "
            f"from {len(result_lists)} sources into {len(fused_results)} unique results"
        )

        return fused_results


class WeightedRRFFusion:
    """
    Weighted RRF Fusion.

    Extends RRF by allowing different weights for different sources.
    """

    def __init__(self, k: int = 60, default_weight: float = 1.0):
        """
        Initialize Weighted RRF Fusion.

        Args:
            k: RRF constant
            default_weight: Default weight for sources without explicit weight
        """
        self.k = k
        self.default_weight = default_weight
        self.source_weights: Dict[str, float] = {}

        logger.info(f"[MAGMA-WRRF] Initialized with k={k}")

    def set_source_weight(self, source: str, weight: float):
        """Set weight for a specific source."""
        self.source_weights[source] = weight

    def set_source_weights(self, weights: Dict[str, float]):
        """Set weights for multiple sources."""
        self.source_weights.update(weights)

    def fuse(
        self,
        result_lists: Dict[str, List[RetrievalResult]],
        weights: Optional[Dict[str, float]] = None
    ) -> List[FusedResult]:
        """
        Fuse multiple result lists using weighted RRF.

        Args:
            result_lists: Dict mapping source name to list of results
            weights: Optional per-query weights (overrides instance weights)

        Returns:
            List of FusedResult sorted by weighted RRF score (descending)
        """
        # Use provided weights or fall back to instance weights
        active_weights = weights if weights else self.source_weights

        # Collect scores with weights
        doc_scores: Dict[str, float] = defaultdict(float)
        doc_source_scores: Dict[str, Dict[str, float]] = defaultdict(dict)
        doc_source_ranks: Dict[str, Dict[str, int]] = defaultdict(dict)
        doc_content: Dict[str, str] = {}
        doc_metadata: Dict[str, Dict[str, Any]] = defaultdict(dict)
        doc_sources: Dict[str, List[str]] = defaultdict(list)

        for source_name, results in result_lists.items():
            weight = active_weights.get(source_name, self.default_weight)

            for result in results:
                # Weighted RRF contribution
                rrf_contribution = weight * (1.0 / (self.k + result.rank))
                doc_scores[result.id] += rrf_contribution

                doc_source_scores[result.id][source_name] = result.score
                doc_source_ranks[result.id][source_name] = result.rank
                doc_content[result.id] = result.content
                doc_metadata[result.id].update(result.metadata)
                doc_sources[result.id].append(source_name)

        # Create fused results
        fused_results = []
        for doc_id, rrf_score in doc_scores.items():
            fused_results.append(FusedResult(
                id=doc_id,
                content=doc_content.get(doc_id, ""),
                rrf_score=rrf_score,
                source_scores=doc_source_scores[doc_id],
                source_ranks=doc_source_ranks[doc_id],
                sources=doc_sources[doc_id],
                metadata=doc_metadata[doc_id]
            ))

        fused_results.sort(key=lambda x: x.rrf_score, reverse=True)

        return fused_results


class CombSUMFusion:
    """
    CombSUM fusion method.

    Combines results by summing normalized scores.
    Requires score normalization (min-max by default).
    """

    def __init__(self, normalize: bool = True):
        """
        Initialize CombSUM Fusion.

        Args:
            normalize: Whether to normalize scores before combining
        """
        self.normalize = normalize
        logger.info("[MAGMA-COMBSUM] Initialized")

    def fuse(
        self,
        result_lists: Dict[str, List[RetrievalResult]]
    ) -> List[FusedResult]:
        """
        Fuse using CombSUM.

        Args:
            result_lists: Dict mapping source name to list of results

        Returns:
            List of FusedResult sorted by combined score (descending)
        """
        # Normalize scores within each source if needed
        normalized_lists = {}
        if self.normalize:
            for source, results in result_lists.items():
                if not results:
                    normalized_lists[source] = []
                    continue

                scores = [r.score for r in results]
                min_score = min(scores)
                max_score = max(scores)
                score_range = max_score - min_score if max_score != min_score else 1.0

                normalized = []
                for r in results:
                    norm_score = (r.score - min_score) / score_range
                    normalized.append(RetrievalResult(
                        id=r.id,
                        content=r.content,
                        score=norm_score,
                        rank=r.rank,
                        source=r.source,
                        metadata=r.metadata
                    ))
                normalized_lists[source] = normalized
        else:
            normalized_lists = result_lists

        # Sum scores
        doc_scores: Dict[str, float] = defaultdict(float)
        doc_source_scores: Dict[str, Dict[str, float]] = defaultdict(dict)
        doc_source_ranks: Dict[str, Dict[str, int]] = defaultdict(dict)
        doc_content: Dict[str, str] = {}
        doc_metadata: Dict[str, Dict[str, Any]] = defaultdict(dict)
        doc_sources: Dict[str, List[str]] = defaultdict(list)

        for source_name, results in normalized_lists.items():
            for result in results:
                doc_scores[result.id] += result.score
                doc_source_scores[result.id][source_name] = result.score
                doc_source_ranks[result.id][source_name] = result.rank
                doc_content[result.id] = result.content
                doc_metadata[result.id].update(result.metadata)
                doc_sources[result.id].append(source_name)

        # Create fused results
        fused_results = []
        for doc_id, combined_score in doc_scores.items():
            fused_results.append(FusedResult(
                id=doc_id,
                content=doc_content.get(doc_id, ""),
                rrf_score=combined_score,  # Using rrf_score field for combined score
                source_scores=doc_source_scores[doc_id],
                source_ranks=doc_source_ranks[doc_id],
                sources=doc_sources[doc_id],
                metadata=doc_metadata[doc_id]
            ))

        fused_results.sort(key=lambda x: x.rrf_score, reverse=True)

        return fused_results


class CombMNZFusion:
    """
    CombMNZ fusion method.

    CombSUM multiplied by number of sources that returned the document.
    Rewards documents found by multiple sources.
    """

    def __init__(self, normalize: bool = True):
        """
        Initialize CombMNZ Fusion.

        Args:
            normalize: Whether to normalize scores before combining
        """
        self.combsum = CombSUMFusion(normalize=normalize)
        logger.info("[MAGMA-COMBMNZ] Initialized")

    def fuse(
        self,
        result_lists: Dict[str, List[RetrievalResult]]
    ) -> List[FusedResult]:
        """
        Fuse using CombMNZ.

        Args:
            result_lists: Dict mapping source name to list of results

        Returns:
            List of FusedResult sorted by CombMNZ score (descending)
        """
        # Get CombSUM results first
        combsum_results = self.combsum.fuse(result_lists)

        # Multiply by number of sources
        for result in combsum_results:
            num_sources = len(result.sources)
            result.rrf_score = result.rrf_score * num_sources

        # Re-sort
        combsum_results.sort(key=lambda x: x.rrf_score, reverse=True)

        return combsum_results


class InterleavingFusion:
    """
    Interleaving fusion method.

    Round-robin interleaving of results from different sources.
    Good for diversity and fair representation.
    """

    def __init__(self):
        logger.info("[MAGMA-INTERLEAVE] Initialized")

    def fuse(
        self,
        result_lists: Dict[str, List[RetrievalResult]]
    ) -> List[FusedResult]:
        """
        Fuse using interleaving.

        Args:
            result_lists: Dict mapping source name to list of results

        Returns:
            List of FusedResult in interleaved order
        """
        # Track seen documents
        seen: Set[str] = set()
        fused_results = []

        # Convert to list of iterators
        sources = list(result_lists.keys())
        iterators = {s: iter(result_lists[s]) for s in sources}
        exhausted = {s: False for s in sources}

        rank = 1
        while not all(exhausted.values()):
            for source in sources:
                if exhausted[source]:
                    continue

                try:
                    result = next(iterators[source])

                    # Skip duplicates
                    if result.id in seen:
                        continue

                    seen.add(result.id)

                    fused_results.append(FusedResult(
                        id=result.id,
                        content=result.content,
                        rrf_score=1.0 / rank,  # Assign decreasing score by position
                        source_scores={source: result.score},
                        source_ranks={source: result.rank},
                        sources=[source],
                        metadata=result.metadata
                    ))
                    rank += 1

                except StopIteration:
                    exhausted[source] = True

        return fused_results


class MagmaFusion:
    """
    Unified fusion interface for Magma retrieval.

    Supports multiple fusion methods and provides utilities for
    combining results from different Magma retrieval sources.
    """

    def __init__(
        self,
        method: FusionMethod = FusionMethod.RRF,
        rrf_k: int = 60,
        source_weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize Magma Fusion.

        Args:
            method: Fusion method to use
            rrf_k: K constant for RRF methods
            source_weights: Optional weights for weighted methods
        """
        self.method = method
        self.rrf_k = rrf_k
        self.source_weights = source_weights or {}

        # Initialize appropriate fusers
        self._fusers = {
            FusionMethod.RRF: RRFFusion(k=rrf_k),
            FusionMethod.WEIGHTED_RRF: WeightedRRFFusion(k=rrf_k),
            FusionMethod.COMBSUM: CombSUMFusion(normalize=True),
            FusionMethod.COMBMNZ: CombMNZFusion(normalize=True),
            FusionMethod.INTERLEAVING: InterleavingFusion(),
        }

        if source_weights:
            self._fusers[FusionMethod.WEIGHTED_RRF].set_source_weights(source_weights)

        logger.info(f"[MAGMA-FUSION] Initialized with method={method.value}")

    def fuse(
        self,
        result_lists: Dict[str, List[RetrievalResult]],
        method: Optional[FusionMethod] = None
    ) -> List[FusedResult]:
        """
        Fuse result lists.

        Args:
            result_lists: Dict mapping source name to list of results
            method: Override fusion method for this call

        Returns:
            List of FusedResult
        """
        active_method = method or self.method
        fuser = self._fusers.get(active_method)

        if not fuser:
            raise ValueError(f"Unknown fusion method: {active_method}")

        if active_method == FusionMethod.WEIGHTED_RRF and self.source_weights:
            return fuser.fuse(result_lists, self.source_weights)

        return fuser.fuse(result_lists)

    def fuse_with_limit(
        self,
        result_lists: Dict[str, List[RetrievalResult]],
        limit: int = 10,
        method: Optional[FusionMethod] = None
    ) -> List[FusedResult]:
        """
        Fuse and return top N results.

        Args:
            result_lists: Dict mapping source name to list of results
            limit: Maximum number of results to return
            method: Override fusion method

        Returns:
            List of top FusedResult
        """
        results = self.fuse(result_lists, method)
        return results[:limit]

    def set_method(self, method: FusionMethod):
        """Change the fusion method."""
        self.method = method

    def set_source_weight(self, source: str, weight: float):
        """Set weight for a source."""
        self.source_weights[source] = weight
        self._fusers[FusionMethod.WEIGHTED_RRF].set_source_weight(source, weight)

    @staticmethod
    def create_retrieval_results(
        items: List[Dict[str, Any]],
        source: str,
        id_key: str = "id",
        content_key: str = "content",
        score_key: str = "score"
    ) -> List[RetrievalResult]:
        """
        Helper to convert raw results to RetrievalResult objects.

        Args:
            items: List of result dicts
            source: Source name
            id_key: Key for document ID
            content_key: Key for content
            score_key: Key for score

        Returns:
            List of RetrievalResult
        """
        results = []
        for rank, item in enumerate(items, start=1):
            results.append(RetrievalResult(
                id=str(item.get(id_key, f"{source}_{rank}")),
                content=str(item.get(content_key, "")),
                score=float(item.get(score_key, 1.0 / rank)),
                rank=rank,
                source=source,
                metadata={k: v for k, v in item.items()
                         if k not in [id_key, content_key, score_key]}
            ))
        return results
