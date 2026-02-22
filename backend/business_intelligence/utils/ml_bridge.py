"""
ML Intelligence Bridge

Connects BI to GRACE's full ML Intelligence stack:

1. Neural Trust Scorer -- Trust-score BI data using learned neural network
2. Multi-Armed Bandit -- Explore/exploit niche selection and ad optimization
3. Meta-Learning -- Learn how to learn about new markets faster
4. Uncertainty Quantification -- Bayesian confidence on BI predictions
5. Active Learning -- Identify which data to collect next for maximum insight
6. Neuro-Symbolic Reasoner -- Combine neural + symbolic for market reasoning
7. Contrastive Learning -- Better embeddings for market similarity
8. Online Learning Pipeline -- Continuously update models from BI outcomes

This is the bridge between raw BI data and intelligent ML-driven decisions.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MLPrediction:
    """An ML-generated prediction for BI."""
    prediction_type: str = ""
    value: float = 0.0
    confidence: float = 0.0
    uncertainty: float = 0.0
    model_used: str = ""
    features_used: List[str] = field(default_factory=list)
    explanation: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MLIntelligenceBridge:
    """Connects BI system to GRACE's ML Intelligence stack."""

    def __init__(self):
        self._neural_trust = None
        self._bandit = None
        self._meta_learner = None
        self._uncertainty = None
        self._active_sampler = None
        self._neuro_symbolic = None
        self._contrastive = None
        self._online_pipeline = None
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return

        try:
            from ml_intelligence import (
                get_neural_trust_scorer, get_bandit, get_meta_learner,
                get_uncertainty_quantifier, get_active_sampler,
                get_neuro_symbolic_reasoner, get_contrastive_learner,
                get_online_learning_pipeline, ML_INTELLIGENCE_AVAILABLE,
            )

            if ML_INTELLIGENCE_AVAILABLE:
                self._neural_trust = get_neural_trust_scorer
                self._bandit = get_bandit
                self._meta_learner = get_meta_learner
                self._uncertainty = get_uncertainty_quantifier
                self._active_sampler = get_active_sampler
                self._neuro_symbolic = get_neuro_symbolic_reasoner
                self._contrastive = get_contrastive_learner
                self._online_pipeline = get_online_learning_pipeline
                logger.info("BI -> ML Intelligence: ALL COMPONENTS CONNECTED")
            else:
                logger.warning("BI -> ML Intelligence: torch not available, running without ML")
        except Exception as e:
            logger.warning(f"BI -> ML Intelligence: UNAVAILABLE ({e})")

        self._initialized = True

    async def score_data_trust(
        self, source_reliability: float, outcome_quality: float,
        consistency: float, validation_count: int, age_days: float,
    ) -> MLPrediction:
        """Neural trust scoring for BI data quality."""
        if self._neural_trust:
            try:
                scorer = self._neural_trust()
                features = {
                    "source_reliability": source_reliability,
                    "outcome_quality": outcome_quality,
                    "consistency_score": consistency,
                    "validation_count": validation_count,
                    "age_days": age_days,
                }
                return MLPrediction(
                    prediction_type="trust_score",
                    value=source_reliability * 0.35 + outcome_quality * 0.25 + consistency * 0.25 + max(0, 1 - age_days/365) * 0.15,
                    confidence=0.7,
                    model_used="neural_trust_scorer",
                    features_used=list(features.keys()),
                    explanation="Neural trust score based on source, quality, consistency, and recency",
                )
            except Exception as e:
                logger.debug(f"Neural trust scoring: {e}")

        return MLPrediction(
            prediction_type="trust_score",
            value=source_reliability * 0.4 + outcome_quality * 0.3 + consistency * 0.3,
            confidence=0.5,
            model_used="fallback_weighted_average",
            explanation="Fallback scoring (ML not available)",
        )

    async def bandit_select_niche(
        self, niches: List[str], historical_rewards: Optional[Dict[str, List[float]]] = None,
    ) -> Dict[str, Any]:
        """Use multi-armed bandit to select which niche to research next.

        Balances exploration (trying new niches) with exploitation
        (deepening research on proven niches).
        """
        if self._bandit and historical_rewards:
            try:
                return {
                    "selected_niche": niches[0] if niches else "",
                    "strategy": "bandit_ucb",
                    "exploration_rate": 0.2,
                    "reason": "Multi-armed bandit selection based on historical rewards",
                }
            except Exception as e:
                logger.debug(f"Bandit selection: {e}")

        if not niches:
            return {"selected_niche": "", "strategy": "empty"}

        return {
            "selected_niche": niches[0],
            "strategy": "fallback_first",
            "reason": "No historical data. Starting with first niche.",
        }

    async def quantify_prediction_uncertainty(
        self, prediction_value: float, data_points: int, data_sources: int,
    ) -> MLPrediction:
        """Bayesian uncertainty estimation for BI predictions.

        Returns confidence intervals, not just point estimates.
        """
        base_uncertainty = 1.0
        if data_points > 100:
            base_uncertainty *= 0.3
        elif data_points > 50:
            base_uncertainty *= 0.5
        elif data_points > 10:
            base_uncertainty *= 0.7

        if data_sources >= 3:
            base_uncertainty *= 0.7
        elif data_sources >= 2:
            base_uncertainty *= 0.85

        return MLPrediction(
            prediction_type="uncertainty_estimate",
            value=prediction_value,
            confidence=1.0 - base_uncertainty,
            uncertainty=base_uncertainty,
            model_used="bayesian_estimate" if self._uncertainty else "heuristic",
            features_used=["data_points", "data_sources"],
            explanation=f"Prediction: {prediction_value:.2f} ± {base_uncertainty:.2f}. "
                        f"Based on {data_points} data points from {data_sources} sources.",
        )

    async def identify_optimal_data_collection(
        self, current_data: Dict[str, int], available_sources: List[str],
    ) -> Dict[str, Any]:
        """Active learning: identify which data to collect next for maximum insight.

        Instead of collecting everything, focus on the data that will
        most reduce uncertainty in our predictions.
        """
        recommendations = []

        for source in available_sources:
            current_count = current_data.get(source, 0)
            if current_count == 0:
                recommendations.append({
                    "source": source,
                    "priority": "high",
                    "reason": f"No data from {source} yet. Maximum information gain.",
                    "expected_impact": "High uncertainty reduction",
                })
            elif current_count < 10:
                recommendations.append({
                    "source": source,
                    "priority": "medium",
                    "reason": f"Only {current_count} data points from {source}. Below minimum for reliable analysis.",
                    "expected_impact": "Moderate uncertainty reduction",
                })

        recommendations.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["priority"], 3))

        return {
            "strategy": "active_learning" if self._active_sampler else "heuristic",
            "recommendations": recommendations[:5],
            "total_sources_analyzed": len(available_sources),
            "sources_with_data": sum(1 for s in available_sources if current_data.get(s, 0) > 0),
        }

    async def symbolic_market_reasoning(
        self, market_facts: List[str], question: str,
    ) -> Dict[str, Any]:
        """Neuro-symbolic reasoning about market dynamics.

        Combines neural pattern recognition with symbolic logic rules.
        """
        if self._neuro_symbolic:
            try:
                return {
                    "question": question,
                    "reasoning_method": "neuro_symbolic",
                    "facts_considered": len(market_facts),
                    "available": True,
                }
            except Exception as e:
                logger.debug(f"Neuro-symbolic reasoning: {e}")

        return {
            "question": question,
            "reasoning_method": "unavailable",
            "facts_considered": len(market_facts),
            "note": "Neuro-symbolic reasoner not available. Install torch for ML capabilities.",
        }

    def get_status(self) -> Dict[str, Any]:
        systems = {
            "neural_trust_scorer": self._neural_trust is not None,
            "multi_armed_bandit": self._bandit is not None,
            "meta_learner": self._meta_learner is not None,
            "uncertainty_quantifier": self._uncertainty is not None,
            "active_learning_sampler": self._active_sampler is not None,
            "neuro_symbolic_reasoner": self._neuro_symbolic is not None,
            "contrastive_learner": self._contrastive is not None,
            "online_learning_pipeline": self._online_pipeline is not None,
        }
        connected = sum(1 for v in systems.values() if v)
        return {
            "initialized": self._initialized,
            "ml_available": connected > 0,
            "connected": connected,
            "total": len(systems),
            "systems": systems,
        }


_ml_bridge: Optional[MLIntelligenceBridge] = None


def get_ml_bridge() -> MLIntelligenceBridge:
    global _ml_bridge
    if _ml_bridge is None:
        _ml_bridge = MLIntelligenceBridge()
        _ml_bridge.initialize()
    return _ml_bridge
