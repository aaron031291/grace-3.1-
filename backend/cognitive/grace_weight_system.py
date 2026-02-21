"""
Grace Weight System

Trust scores, confidence scores, and KPIs ARE Grace's weights.

In an LLM:
  weights = learned parameters that map inputs to outputs
  training = adjusting weights based on loss (gradient descent)
  inference = forward pass through weighted connections

In Grace:
  weights = trust/confidence/quality scores on every piece of knowledge
  training = outcomes flow back to adjust scores (success -> increase, failure -> decrease)
  inference = query highest-weighted match from compiled knowledge

This module treats the 121 trust/confidence/score fields across
Grace's system as a unified weight space that gets adjusted
continuously based on outcomes.

THE WEIGHT ARCHITECTURE:

  Layer 1: KNOWLEDGE WEIGHTS
    - CompiledFact.confidence       (how reliable is this fact)
    - CompiledProcedure.confidence  (how reliable is this procedure)
    - CompiledDecisionRule.confidence (how reliable is this rule)
    - DistilledKnowledge.confidence (how reliable is this LLM output)
    - DocumentChunk.confidence_score (how trustworthy is this chunk)

  Layer 2: PATTERN WEIGHTS
    - ExtractedPattern.confidence_score (how reliable is this pattern)
    - ExtractedPattern.utility_score    (how useful is this pattern)
    - ReasoningPath.success_rate        (how often does this reasoning work)
    - LearningPattern.trust_score       (how trustworthy is this pattern)

  Layer 3: SOURCE WEIGHTS
    - Source reliability scores        (official_docs=0.95, user_generated=0.50)
    - Model accuracy weights           (which LLM is most accurate per domain)
    - Domain confidence                 (how well does Grace know this domain)

  Layer 4: SYSTEM WEIGHTS (KPIs as loss function)
    - Hallucination rate               (lower = better)
    - Success rate                     (higher = better)
    - Autonomy ratio                   (higher = less LLM dependency)
    - User satisfaction                (feedback ratio)

  BACKPROPAGATION:
    When a response succeeds:
      → Increase confidence on the knowledge used
      → Increase trust on the pattern applied
      → Increase source reliability
      → KPIs improve

    When a response fails:
      → Decrease confidence on the knowledge used
      → Decrease trust on the pattern
      → Decrease source reliability
      → KPIs degrade → triggers learning adjustments
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class WeightUpdate:
    """A single weight adjustment."""
    target: str         # what's being adjusted (fact, pattern, source, etc.)
    target_id: str      # specific ID
    field: str          # which weight field
    old_value: float
    new_value: float
    reason: str         # why the adjustment
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WeightSnapshot:
    """Snapshot of system weights at a point in time."""
    timestamp: datetime
    knowledge_weights: Dict[str, float]
    pattern_weights: Dict[str, float]
    source_weights: Dict[str, float]
    kpi_weights: Dict[str, float]
    overall_health: float


class GraceWeightSystem:
    """
    Unified weight management across all of Grace's subsystems.

    Treats trust/confidence/KPI scores as adjustable weights.
    Provides backpropagation-like updates when outcomes are known.
    Tracks weight changes over time for learning analysis.
    """

    # Source reliability weights (adjustable based on track record)
    DEFAULT_SOURCE_WEIGHTS = {
        "official_docs": 0.95,
        "academic_paper": 0.90,
        "verified_tutorial": 0.85,
        "trusted_blog": 0.75,
        "community_qa": 0.65,
        "user_generated": 0.50,
        "llm_generated": 0.60,
        "distilled_verified": 0.85,
        "distilled_unverified": 0.50,
        "pattern_derived": 0.70,
        "unverified": 0.30,
    }

    # Adjustment rates (learning rate equivalent)
    LEARNING_RATES = {
        "success": 0.05,       # How much to boost on success
        "failure": -0.08,      # How much to reduce on failure (asymmetric - failures matter more)
        "user_positive": 0.10, # User upvote boost
        "user_negative": -0.15,# User downvote penalty (trust user judgment heavily)
        "validation": 0.03,    # Cross-validation confirmation
        "contradiction": -0.10,# Contradiction detected
    }

    def __init__(self, session: Session):
        self.session = session
        self._update_history: List[WeightUpdate] = []
        self._source_weights = dict(self.DEFAULT_SOURCE_WEIGHTS)
        self._snapshots: List[WeightSnapshot] = []

        logger.info("[WEIGHTS] Grace weight system initialized")

    def propagate_outcome(
        self,
        outcome: str,
        knowledge_ids: Optional[List[str]] = None,
        pattern_ids: Optional[List[str]] = None,
        source_type: Optional[str] = None,
        interaction_id: Optional[str] = None,
    ):
        """
        Propagate an outcome back through the weight system.

        This is Grace's backpropagation:
        - Success → increase weights on everything that contributed
        - Failure → decrease weights on everything that contributed

        Args:
            outcome: "success", "failure", "user_positive", "user_negative"
            knowledge_ids: IDs of knowledge entries that were used
            pattern_ids: IDs of patterns that were applied
            source_type: Type of source that produced this
            interaction_id: ID of the interaction for tracking
        """
        rate = self.LEARNING_RATES.get(outcome, 0.0)
        if rate == 0:
            return

        updates = []

        # Update knowledge weights
        if knowledge_ids:
            updates.extend(self._update_knowledge_weights(knowledge_ids, rate))

        # Update pattern weights
        if pattern_ids:
            updates.extend(self._update_pattern_weights(pattern_ids, rate))

        # Update source weights
        if source_type and source_type in self._source_weights:
            old = self._source_weights[source_type]
            new = max(0.05, min(0.99, old + rate * 0.5))
            self._source_weights[source_type] = new
            updates.append(WeightUpdate(
                target="source", target_id=source_type,
                field="reliability", old_value=old, new_value=new,
                reason=f"Outcome: {outcome}",
            ))

        self._update_history.extend(updates)

        if updates:
            self.session.flush()

            from cognitive.learning_hook import track_learning_event
            track_learning_event(
                "weight_update",
                f"Propagated '{outcome}': {len(updates)} weight adjustments",
                data={
                    "outcome": outcome,
                    "adjustments": len(updates),
                    "knowledge_updated": len(knowledge_ids or []),
                    "patterns_updated": len(pattern_ids or []),
                },
            )

    def _update_knowledge_weights(
        self, knowledge_ids: List[str], rate: float
    ) -> List[WeightUpdate]:
        """Update confidence weights on compiled knowledge."""
        updates = []

        try:
            from cognitive.knowledge_compiler import CompiledFact, DistilledKnowledge

            for kid in knowledge_ids:
                # Try facts
                fact = self.session.query(CompiledFact).filter(
                    CompiledFact.id == int(kid) if kid.isdigit() else CompiledFact.subject == kid
                ).first()
                if fact:
                    old = fact.confidence
                    fact.confidence = max(0.0, min(1.0, old + rate))
                    updates.append(WeightUpdate(
                        target="fact", target_id=str(fact.id),
                        field="confidence", old_value=old, new_value=fact.confidence,
                        reason=f"Rate: {rate:+.3f}",
                    ))

                # Try distilled knowledge
                distilled = self.session.query(DistilledKnowledge).filter(
                    DistilledKnowledge.query_hash == kid
                ).first()
                if distilled:
                    old = distilled.confidence
                    distilled.confidence = max(0.0, min(1.0, old + rate))
                    if rate > 0:
                        distilled.times_validated += 1
                        if distilled.times_validated >= 3:
                            distilled.is_verified = True
                    else:
                        distilled.times_invalidated += 1
                        distilled.is_verified = False
                    updates.append(WeightUpdate(
                        target="distilled", target_id=kid,
                        field="confidence", old_value=old, new_value=distilled.confidence,
                        reason=f"Rate: {rate:+.3f}",
                    ))

        except Exception as e:
            logger.debug(f"[WEIGHTS] Knowledge update error: {e}")

        return updates

    def _update_pattern_weights(
        self, pattern_ids: List[str], rate: float
    ) -> List[WeightUpdate]:
        """Update confidence weights on extracted patterns."""
        updates = []

        try:
            from models.llm_tracking_models import ExtractedPattern

            for pid in pattern_ids:
                pattern = self.session.query(ExtractedPattern).filter(
                    ExtractedPattern.pattern_id == pid
                ).first()
                if pattern:
                    old = pattern.confidence_score
                    pattern.confidence_score = max(0.0, min(1.0, old + rate))

                    if rate > 0:
                        pattern.times_succeeded += 1
                    else:
                        pattern.times_failed += 1

                    total = pattern.times_succeeded + pattern.times_failed
                    if total > 0:
                        pattern.success_rate = pattern.times_succeeded / total

                    pattern.can_replace_llm = (
                        pattern.confidence_score >= 0.85 and
                        pattern.success_rate >= 0.9 and
                        pattern.times_observed >= 6
                    )

                    updates.append(WeightUpdate(
                        target="pattern", target_id=pid,
                        field="confidence_score", old_value=old,
                        new_value=pattern.confidence_score,
                        reason=f"Rate: {rate:+.3f}, can_replace={pattern.can_replace_llm}",
                    ))

        except Exception as e:
            logger.debug(f"[WEIGHTS] Pattern update error: {e}")

        return updates

    def get_source_weight(self, source_type: str) -> float:
        """Get current weight for a source type."""
        return self._source_weights.get(source_type, 0.5)

    def get_weight_snapshot(self) -> WeightSnapshot:
        """Capture current state of all weights."""
        knowledge_weights = {}
        pattern_weights = {}

        try:
            from cognitive.knowledge_compiler import CompiledFact, DistilledKnowledge, CompiledProcedure

            facts = self.session.query(CompiledFact).limit(100).all()
            for f in facts:
                knowledge_weights[f"fact:{f.subject}:{f.predicate}"] = f.confidence

            distilled = self.session.query(DistilledKnowledge).filter(
                DistilledKnowledge.confidence >= 0.5
            ).limit(100).all()
            for d in distilled:
                knowledge_weights[f"distilled:{d.query_hash}"] = d.confidence

        except Exception:
            pass

        try:
            from models.llm_tracking_models import ExtractedPattern
            patterns = self.session.query(ExtractedPattern).limit(50).all()
            for p in patterns:
                pattern_weights[p.pattern_id] = p.confidence_score
        except Exception:
            pass

        kpi_weights = self._calculate_kpis()

        overall = (
            (sum(knowledge_weights.values()) / max(len(knowledge_weights), 1)) * 0.3 +
            (sum(pattern_weights.values()) / max(len(pattern_weights), 1)) * 0.3 +
            kpi_weights.get("success_rate", 0.5) * 0.2 +
            (1.0 - kpi_weights.get("hallucination_rate", 0.5)) * 0.2
        ) if knowledge_weights or pattern_weights else 0.0

        snapshot = WeightSnapshot(
            timestamp=datetime.now(timezone.utc),
            knowledge_weights=knowledge_weights,
            pattern_weights=pattern_weights,
            source_weights=dict(self._source_weights),
            kpi_weights=kpi_weights,
            overall_health=round(overall, 3),
        )

        self._snapshots.append(snapshot)
        return snapshot

    def _calculate_kpis(self) -> Dict[str, float]:
        """Calculate KPIs as the loss function."""
        kpis = {
            "success_rate": 0.5,
            "hallucination_rate": 0.5,
            "autonomy_ratio": 0.0,
            "user_satisfaction": 0.5,
        }

        try:
            from cognitive.llm_interaction_tracker import get_llm_interaction_tracker
            tracker = get_llm_interaction_tracker(self.session)
            stats = tracker.get_interaction_stats(time_window_hours=24)

            outcomes = stats.get("outcomes", {})
            if stats.get("total", 0) > 0:
                kpis["success_rate"] = outcomes.get("success_rate", 0.5)
        except Exception:
            pass

        try:
            from cognitive.llm_dependency_reducer import get_llm_dependency_reducer
            reducer = get_llm_dependency_reducer(self.session)
            trend = reducer.get_dependency_trend(days=7)
            kpis["autonomy_ratio"] = 1.0 - trend.get("current_dependency", 1.0)
        except Exception:
            pass

        return kpis

    def get_stats(self) -> Dict[str, Any]:
        """Get weight system statistics."""
        return {
            "total_weight_updates": len(self._update_history),
            "source_weights": dict(self._source_weights),
            "learning_rates": dict(self.LEARNING_RATES),
            "recent_updates": [
                {
                    "target": u.target,
                    "field": u.field,
                    "old": round(u.old_value, 3),
                    "new": round(u.new_value, 3),
                    "reason": u.reason,
                }
                for u in self._update_history[-10:]
            ],
            "snapshots_taken": len(self._snapshots),
            "current_kpis": self._calculate_kpis(),
        }


_weight_system: Optional[GraceWeightSystem] = None


def get_grace_weight_system(session: Session) -> GraceWeightSystem:
    """Get or create the Grace weight system singleton."""
    global _weight_system
    if _weight_system is None:
        _weight_system = GraceWeightSystem(session)
    return _weight_system
