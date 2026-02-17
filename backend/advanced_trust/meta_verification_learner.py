"""
Meta-Learning on Verification

Grace should learn which verification strategies work best for which types
of data. "For code questions, checking GitHub repos is 90% reliable. For
factual claims, cross-referencing 3+ web sources works better. For
domain-specific questions, the knowledge base is more reliable than the web."

This shapes the verification pipeline dynamically.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class VerificationAttempt:
    """Record of a single verification attempt."""
    attempt_id: str
    strategy: str
    data_type: str
    domain: Optional[str]
    success: bool
    confidence_before: float
    confidence_after: float
    time_ms: float
    cost: float = 0.0  # API cost if any
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyProfile:
    """Performance profile of a verification strategy."""
    strategy: str
    total_attempts: int = 0
    successes: int = 0
    failures: int = 0
    success_rate: float = 0.0
    avg_confidence_improvement: float = 0.0
    avg_time_ms: float = 0.0
    avg_cost: float = 0.0
    reliability_score: float = 0.5
    last_used: Optional[datetime] = None

    # Per-domain performance
    domain_performance: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: {"successes": 0, "attempts": 0, "rate": 0.0})
    )

    # Per-data-type performance
    data_type_performance: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: {"successes": 0, "attempts": 0, "rate": 0.0})
    )


@dataclass
class StrategyRecommendation:
    """Recommended verification strategy for a query."""
    strategy: str
    confidence: float
    expected_success_rate: float
    expected_time_ms: float
    reason: str
    alternatives: List[Tuple[str, float]]  # (strategy, score)


class MetaVerificationLearner:
    """
    Learns which verification strategies work best for different data types
    and domains, then recommends the optimal strategy dynamically.

    Supported Strategies:
    - github_check: Check GitHub repositories
    - web_cross_reference: Cross-reference 3+ web sources
    - knowledge_base_lookup: Check internal knowledge base
    - expert_consensus: Check multiple expert sources
    - code_execution: Actually run code to verify
    - semantic_similarity: Compare against known-good embeddings
    - temporal_verification: Verify data is current
    - source_authority: Check source authority/reputation

    The learner tracks success rates per (strategy, domain, data_type) and
    recommends the best strategy for new queries.
    """

    DEFAULT_STRATEGIES = [
        "github_check",
        "web_cross_reference",
        "knowledge_base_lookup",
        "expert_consensus",
        "code_execution",
        "semantic_similarity",
        "temporal_verification",
        "source_authority",
    ]

    def __init__(self, strategies: Optional[List[str]] = None):
        self.strategies = strategies or self.DEFAULT_STRATEGIES
        self.profiles: Dict[str, StrategyProfile] = {
            s: StrategyProfile(strategy=s) for s in self.strategies
        }
        self.attempts: List[VerificationAttempt] = []
        logger.info(
            f"[META-VERIFY] Learner initialized with "
            f"{len(self.strategies)} strategies"
        )

    def record_attempt(
        self,
        strategy: str,
        data_type: str,
        domain: Optional[str],
        success: bool,
        confidence_before: float,
        confidence_after: float,
        time_ms: float,
        cost: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VerificationAttempt:
        """
        Record a verification attempt and update strategy profiles.

        Args:
            strategy: Strategy used
            data_type: Type of data (code, factual, domain_specific, etc.)
            domain: Domain of the data
            success: Whether verification was successful
            confidence_before: Confidence before verification
            confidence_after: Confidence after verification
            time_ms: Time taken in milliseconds
            cost: Cost of the verification (API costs etc.)
            metadata: Additional metadata

        Returns:
            VerificationAttempt record
        """
        attempt = VerificationAttempt(
            attempt_id=f"va-{uuid.uuid4().hex[:12]}",
            strategy=strategy,
            data_type=data_type,
            domain=domain,
            success=success,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            time_ms=time_ms,
            cost=cost,
            metadata=metadata or {},
        )
        self.attempts.append(attempt)

        # Ensure strategy profile exists
        if strategy not in self.profiles:
            self.profiles[strategy] = StrategyProfile(strategy=strategy)

        profile = self.profiles[strategy]
        profile.total_attempts += 1
        if success:
            profile.successes += 1
        else:
            profile.failures += 1

        profile.success_rate = (
            profile.successes / profile.total_attempts
        )
        profile.last_used = datetime.now(timezone.utc)

        # Update averages
        n = profile.total_attempts
        improvement = confidence_after - confidence_before
        profile.avg_confidence_improvement = (
            (profile.avg_confidence_improvement * (n - 1) + improvement) / n
        )
        profile.avg_time_ms = (
            (profile.avg_time_ms * (n - 1) + time_ms) / n
        )
        profile.avg_cost = (
            (profile.avg_cost * (n - 1) + cost) / n
        )

        # Calculate reliability score
        profile.reliability_score = self._calculate_reliability(profile)

        # Update domain performance
        if domain:
            dp = profile.domain_performance[domain]
            dp["attempts"] = dp.get("attempts", 0) + 1
            if success:
                dp["successes"] = dp.get("successes", 0) + 1
            dp["rate"] = dp["successes"] / dp["attempts"]

        # Update data type performance
        dtp = profile.data_type_performance[data_type]
        dtp["attempts"] = dtp.get("attempts", 0) + 1
        if success:
            dtp["successes"] = dtp.get("successes", 0) + 1
        dtp["rate"] = dtp["successes"] / dtp["attempts"]

        return attempt

    def recommend_strategy(
        self,
        data_type: str,
        domain: Optional[str] = None,
        max_time_ms: Optional[float] = None,
        max_cost: Optional[float] = None,
    ) -> StrategyRecommendation:
        """
        Recommend the best verification strategy for a query.

        Args:
            data_type: Type of data to verify
            domain: Domain of the data
            max_time_ms: Maximum acceptable time
            max_cost: Maximum acceptable cost

        Returns:
            StrategyRecommendation
        """
        scored_strategies: List[Tuple[str, float, str]] = []

        for strategy, profile in self.profiles.items():
            score, reason = self._score_strategy(
                profile, data_type, domain, max_time_ms, max_cost
            )
            scored_strategies.append((strategy, score, reason))

        # Sort by score (highest first)
        scored_strategies.sort(key=lambda x: x[1], reverse=True)

        best = scored_strategies[0]
        best_profile = self.profiles[best[0]]

        # Get domain-specific success rate if available
        expected_rate = best_profile.success_rate
        if domain and domain in best_profile.domain_performance:
            dp = best_profile.domain_performance[domain]
            if dp.get("attempts", 0) >= 3:
                expected_rate = dp["rate"]

        alternatives = [
            (s, score) for s, score, _ in scored_strategies[1:4]
        ]

        return StrategyRecommendation(
            strategy=best[0],
            confidence=min(best[1], 1.0),
            expected_success_rate=expected_rate,
            expected_time_ms=best_profile.avg_time_ms,
            reason=best[2],
            alternatives=alternatives,
        )

    def _score_strategy(
        self,
        profile: StrategyProfile,
        data_type: str,
        domain: Optional[str],
        max_time_ms: Optional[float],
        max_cost: Optional[float],
    ) -> Tuple[float, str]:
        """Score a strategy for a specific query context."""
        score = 0.0
        reasons = []

        # Base: reliability score (0.4 weight)
        score += profile.reliability_score * 0.4
        reasons.append(f"reliability={profile.reliability_score:.2f}")

        # Data type match (0.3 weight)
        if data_type in profile.data_type_performance:
            dtp = profile.data_type_performance[data_type]
            if dtp.get("attempts", 0) >= 3:
                type_score = dtp["rate"]
                score += type_score * 0.3
                reasons.append(f"type_match={type_score:.2f}")
            else:
                score += profile.success_rate * 0.15
                reasons.append("insufficient_type_data")
        else:
            score += profile.success_rate * 0.1
            reasons.append("no_type_data")

        # Domain match (0.2 weight)
        if domain and domain in profile.domain_performance:
            dp = profile.domain_performance[domain]
            if dp.get("attempts", 0) >= 3:
                domain_score = dp["rate"]
                score += domain_score * 0.2
                reasons.append(f"domain_match={domain_score:.2f}")
            else:
                score += profile.success_rate * 0.1
                reasons.append("insufficient_domain_data")
        else:
            score += profile.success_rate * 0.05
            reasons.append("no_domain_data")

        # Efficiency bonus (0.1 weight)
        if profile.total_attempts > 0:
            efficiency = profile.avg_confidence_improvement / max(
                profile.avg_time_ms, 1.0
            )
            efficiency_normalized = min(efficiency * 1000, 1.0)
            score += efficiency_normalized * 0.1

        # Time constraint penalty
        if max_time_ms and profile.avg_time_ms > max_time_ms:
            score *= 0.5
            reasons.append("time_penalty")

        # Cost constraint penalty
        if max_cost and profile.avg_cost > max_cost:
            score *= 0.5
            reasons.append("cost_penalty")

        # Cold start: never-used strategies get a small exploration bonus
        if profile.total_attempts == 0:
            score = 0.3
            reasons = ["exploration_bonus"]

        return score, "; ".join(reasons)

    def _calculate_reliability(self, profile: StrategyProfile) -> float:
        """Calculate reliability score for a strategy."""
        if profile.total_attempts == 0:
            return 0.5  # Unknown reliability

        # Weighted combination of success rate and confidence improvement
        success_component = profile.success_rate * 0.6
        improvement_component = max(
            0, min(1.0, profile.avg_confidence_improvement + 0.5)
        ) * 0.4

        # Recency bonus
        recency_bonus = 0.0
        if profile.last_used:
            days_since = (
                datetime.now(timezone.utc) - profile.last_used
            ).total_seconds() / 86400
            if days_since < 7:
                recency_bonus = 0.05

        return min(1.0, success_component + improvement_component + recency_bonus)

    def get_strategy_ranking(
        self, data_type: Optional[str] = None, domain: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """Get strategies ranked by performance."""
        rankings = []
        for name, profile in self.profiles.items():
            if data_type and data_type in profile.data_type_performance:
                dtp = profile.data_type_performance[data_type]
                score = dtp.get("rate", 0.0)
            elif domain and domain in profile.domain_performance:
                dp = profile.domain_performance[domain]
                score = dp.get("rate", 0.0)
            else:
                score = profile.reliability_score
            rankings.append((name, score))

        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings

    def get_stats(self) -> Dict[str, Any]:
        """Get learner statistics."""
        return {
            "total_attempts": len(self.attempts),
            "strategies": {
                name: {
                    "attempts": p.total_attempts,
                    "success_rate": p.success_rate,
                    "reliability": p.reliability_score,
                    "avg_time_ms": p.avg_time_ms,
                    "avg_confidence_improvement": p.avg_confidence_improvement,
                }
                for name, p in self.profiles.items()
                if p.total_attempts > 0
            },
            "best_overall": (
                max(
                    self.profiles.items(),
                    key=lambda x: x[1].reliability_score,
                )[0]
                if any(p.total_attempts > 0 for p in self.profiles.values())
                else None
            ),
        }
