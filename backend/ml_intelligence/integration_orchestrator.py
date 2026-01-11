"""
ML Intelligence Integration Orchestrator

Integrates all ML/DL components with Grace's existing autonomous learning system.

Features:
- Replaces rule-based trust scoring with neural trust scorer
- Adds online learning to embedding models
- Uses bandit algorithms for topic selection
- Applies meta-learning for hyperparameter optimization
- Provides uncertainty estimates for predictions
- Selects optimal training examples via active learning
- Improves representations with contrastive learning
"""

import sys
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_intelligence import (
    get_neural_trust_scorer,
    get_bandit,
    get_meta_learner,
    get_uncertainty_quantifier,
    get_active_sampler,
    BanditAlgorithm,
    BanditContext,
    SamplingStrategy
)


class MLIntelligenceOrchestrator:
    """
    Main orchestrator for ML Intelligence integration

    Coordinates all ML/DL components with existing systems
    """

    def __init__(self):
        # Initialize components
        self.neural_trust_scorer = None
        self.bandit = None
        self.meta_learner = None
        self.uncertainty_quantifier = None
        self.active_sampler = None

        # Integration state
        self.enabled_features = {
            'neural_trust_scoring': True,
            'bandit_exploration': True,
            'meta_learning': True,
            'uncertainty_estimation': True,
            'active_learning': True
        }

        # Statistics
        self.stats = {
            'neural_trust_predictions': 0,
            'bandit_selections': 0,
            'meta_learning_recommendations': 0,
            'uncertainty_estimates': 0,
            'active_samples_selected': 0
        }

    def initialize(self):
        """Initialize all ML components"""
        try:
            # Neural Trust Scorer
            if self.enabled_features['neural_trust_scoring']:
                self.neural_trust_scorer = get_neural_trust_scorer()
                print("[ML Intelligence] Neural Trust Scorer initialized")

            # Multi-Armed Bandit for topic selection
            if self.enabled_features['bandit_exploration']:
                self.bandit = get_bandit(algorithm=BanditAlgorithm.THOMPSON_SAMPLING)
                print("[ML Intelligence] Multi-Armed Bandit initialized (Thompson Sampling)")

            # Meta-Learning
            if self.enabled_features['meta_learning']:
                self.meta_learner = get_meta_learner()
                print("[ML Intelligence] Meta-Learning Module initialized")

            print("[ML Intelligence] All components initialized successfully")

        except Exception as e:
            print(f"[ML Intelligence] Initialization error: {e}")
            raise

    def compute_trust_score(
        self,
        learning_example: Dict,
        use_neural: bool = True,
        fallback_to_rules: bool = True
    ) -> Tuple[float, Optional[float]]:
        """
        Compute trust score for learning example

        Args:
            learning_example: Learning example dict
            use_neural: Whether to use neural scorer
            fallback_to_rules: Whether to fallback to rule-based if neural fails

        Returns:
            (trust_score, uncertainty)
        """
        if use_neural and self.neural_trust_scorer and self.enabled_features['neural_trust_scoring']:
            try:
                trust_score, uncertainty = self.neural_trust_scorer.predict_trust(
                    learning_example,
                    return_uncertainty=True
                )

                self.stats['neural_trust_predictions'] += 1

                return trust_score, uncertainty

            except Exception as e:
                print(f"[ML Intelligence] Neural trust scoring failed: {e}")

                if fallback_to_rules:
                    # Fallback to rule-based scoring
                    return self._rule_based_trust_score(learning_example), None
                else:
                    raise

        else:
            # Use rule-based scoring
            return self._rule_based_trust_score(learning_example), None

    def _rule_based_trust_score(self, learning_example: Dict) -> float:
        """Fallback rule-based trust scoring"""
        source_reliability = learning_example.get('source_reliability', 0.5)
        outcome_quality = learning_example.get('outcome_quality', 0.5)
        consistency_score = learning_example.get('consistency_score', 0.5)
        validation_count = learning_example.get('times_validated', 0)
        invalidation_count = learning_example.get('times_invalidated', 0)

        # Simple weighted average
        validation_score = validation_count / max(validation_count + invalidation_count, 1)

        trust_score = (
            source_reliability * 0.4 +
            outcome_quality * 0.3 +
            consistency_score * 0.2 +
            validation_score * 0.1
        )

        # Recency decay
        created_at = learning_example.get('created_at', datetime.now())
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        age_days = (datetime.now() - created_at).days
        decay_rate = np.log(2) / 90  # 90-day half-life
        recency_weight = np.exp(-decay_rate * age_days)

        return trust_score * recency_weight

    def update_trust_from_outcome(
        self,
        learning_example: Dict,
        outcome_success: bool
    ):
        """
        Update trust model based on observed outcome

        Args:
            learning_example: Learning example that was used
            outcome_success: Whether outcome was successful
        """
        if self.neural_trust_scorer and self.enabled_features['neural_trust_scoring']:
            try:
                self.neural_trust_scorer.update_from_outcome(
                    learning_example,
                    outcome_success,
                    perform_training=True
                )

                # Save model periodically
                if self.stats['neural_trust_predictions'] % 100 == 0:
                    self.neural_trust_scorer.save_model()

            except Exception as e:
                print(f"[ML Intelligence] Trust update failed: {e}")

    def select_next_learning_topic(
        self,
        available_topics: List[Dict],
        context: Optional[Dict] = None,
        exclude_topics: List[str] = None
    ) -> str:
        """
        Select next topic to learn using bandit algorithm

        Args:
            available_topics: List of topic dicts with 'topic_id', 'topic_name', 'features'
            context: Optional context dict for contextual bandits
            exclude_topics: Topic IDs to exclude

        Returns:
            Selected topic_id
        """
        if not self.bandit or not self.enabled_features['bandit_exploration']:
            # Random selection fallback
            available = [t for t in available_topics if t['topic_id'] not in (exclude_topics or [])]
            if available:
                return np.random.choice([t['topic_id'] for t in available])
            return available_topics[0]['topic_id']

        try:
            # Register all topics as arms
            for topic in available_topics:
                self.bandit.add_arm(
                    topic_id=topic['topic_id'],
                    topic_name=topic.get('topic_name', topic['topic_id']),
                    features=topic.get('features', {})
                )

            # Build bandit context if provided
            bandit_context = None
            if context:
                bandit_context = BanditContext(
                    knowledge_gaps=context.get('knowledge_gaps', {}),
                    recent_failures=context.get('recent_failures', []),
                    user_interests=context.get('user_interests', {}),
                    time_of_day=datetime.now().hour,
                    learning_velocity=context.get('learning_velocity', 1.0)
                )

            # Select using bandit algorithm
            selected_topic_id = self.bandit.select_arm(
                context=bandit_context,
                exclude_topics=exclude_topics
            )

            self.stats['bandit_selections'] += 1

            return selected_topic_id

        except Exception as e:
            print(f"[ML Intelligence] Bandit selection failed: {e}")
            # Fallback to random
            available = [t for t in available_topics if t['topic_id'] not in (exclude_topics or [])]
            if available:
                return np.random.choice([t['topic_id'] for t in available])
            return available_topics[0]['topic_id']

    def update_topic_reward(
        self,
        topic_id: str,
        success: bool,
        context: Optional[Dict] = None
    ):
        """
        Update bandit with observed reward for topic

        Args:
            topic_id: Topic that was learned
            success: Whether learning was successful
            context: Optional context
        """
        if self.bandit and self.enabled_features['bandit_exploration']:
            try:
                reward = 1.0 if success else 0.0

                # Build context if provided
                bandit_context = None
                if context:
                    bandit_context = BanditContext(
                        knowledge_gaps=context.get('knowledge_gaps', {}),
                        recent_failures=context.get('recent_failures', []),
                        user_interests=context.get('user_interests', {}),
                        time_of_day=datetime.now().hour,
                        learning_velocity=context.get('learning_velocity', 1.0)
                    )

                self.bandit.update_reward(topic_id, reward, bandit_context)

            except Exception as e:
                print(f"[ML Intelligence] Bandit reward update failed: {e}")

    def get_learning_recommendations(
        self,
        task_type: str,
        task_metadata: Dict = None
    ) -> Dict:
        """
        Get meta-learning recommendations for learning approach

        Args:
            task_type: Type of learning task
            task_metadata: Additional task metadata

        Returns:
            Dict with hyperparameter recommendations
        """
        if not self.meta_learner or not self.enabled_features['meta_learning']:
            # Return default recommendations
            return {
                'suggested_hyperparams': {
                    'learning_rate': 0.001,
                    'batch_size': 32,
                    'num_epochs': 10,
                    'dropout': 0.2,
                    'weight_decay': 1e-4
                },
                'best_known_configs': [],
                'num_historical_examples': 0
            }

        try:
            recommendations = self.meta_learner.get_learning_recommendations(
                task_type,
                task_metadata
            )

            self.stats['meta_learning_recommendations'] += 1

            return recommendations

        except Exception as e:
            print(f"[ML Intelligence] Meta-learning recommendation failed: {e}")
            return {
                'suggested_hyperparams': {
                    'learning_rate': 0.001,
                    'batch_size': 32,
                    'num_epochs': 10
                },
                'error': str(e)
            }

    def get_uncertainty_estimate(
        self,
        model,
        input_data,
        num_samples: int = 50
    ) -> Dict:
        """
        Get uncertainty estimate for prediction

        Args:
            model: Neural network model
            input_data: Input tensor
            num_samples: Number of MC samples

        Returns:
            Dict with prediction and uncertainty info
        """
        if not self.enabled_features['uncertainty_estimation']:
            return {
                'prediction': None,
                'uncertainty': None,
                'is_reliable': True
            }

        try:
            # Lazy initialization of uncertainty quantifier
            if self.uncertainty_quantifier is None:
                from ml_intelligence import UncertaintyQuantifier
                self.uncertainty_quantifier = UncertaintyQuantifier(
                    model,
                    method='mc_dropout'
                )

            estimate = self.uncertainty_quantifier.predict_with_uncertainty(
                input_data,
                num_samples=num_samples
            )

            self.stats['uncertainty_estimates'] += 1

            return {
                'prediction': estimate.prediction,
                'epistemic_uncertainty': estimate.epistemic_uncertainty,
                'aleatoric_uncertainty': estimate.aleatoric_uncertainty,
                'total_uncertainty': estimate.total_uncertainty,
                'confidence_interval': estimate.confidence_interval,
                'is_reliable': estimate.is_reliable
            }

        except Exception as e:
            print(f"[ML Intelligence] Uncertainty estimation failed: {e}")
            return {
                'prediction': None,
                'uncertainty': None,
                'error': str(e)
            }

    def select_training_examples(
        self,
        unlabeled_pool,
        n_samples: int,
        model=None,
        strategy: SamplingStrategy = SamplingStrategy.UNCERTAINTY
    ) -> List[int]:
        """
        Select most valuable training examples

        Args:
            unlabeled_pool: Pool of unlabeled examples (tensor)
            n_samples: Number of examples to select
            model: Model for uncertainty estimation
            strategy: Sampling strategy

        Returns:
            List of selected indices
        """
        if not self.enabled_features['active_learning'] or model is None:
            # Random selection fallback
            import torch
            if isinstance(unlabeled_pool, torch.Tensor):
                indices = np.random.choice(unlabeled_pool.size(0), size=n_samples, replace=False)
                return indices.tolist()
            return list(range(min(n_samples, len(unlabeled_pool))))

        try:
            # Lazy initialization of active sampler
            if self.active_sampler is None:
                from ml_intelligence import ActiveLearningSampler
                self.active_sampler = ActiveLearningSampler(
                    model,
                    strategy=strategy
                )

            selected_indices = self.active_sampler.select_samples(
                unlabeled_pool,
                n_samples
            )

            self.stats['active_samples_selected'] += len(selected_indices)

            return selected_indices

        except Exception as e:
            print(f"[ML Intelligence] Active learning selection failed: {e}")
            # Fallback to random
            import torch
            if isinstance(unlabeled_pool, torch.Tensor):
                indices = np.random.choice(unlabeled_pool.size(0), size=n_samples, replace=False)
                return indices.tolist()
            return list(range(min(n_samples, len(unlabeled_pool))))

    def get_statistics(self) -> Dict:
        """Get ML Intelligence statistics"""
        stats = {
            'enabled_features': self.enabled_features,
            'usage_stats': self.stats.copy()
        }

        # Add component-specific stats
        if self.neural_trust_scorer:
            stats['neural_trust_scorer'] = self.neural_trust_scorer.get_stats()

        if self.bandit:
            stats['bandit'] = self.bandit.get_all_stats()

        return stats

    def save_all_models(self):
        """Save all ML models"""
        try:
            if self.neural_trust_scorer:
                self.neural_trust_scorer.save_model()
                print("[ML Intelligence] Neural trust scorer saved")

            if self.bandit:
                self.bandit.save_state()
                print("[ML Intelligence] Bandit state saved")

            if self.meta_learner:
                self.meta_learner.save_state()
                print("[ML Intelligence] Meta-learner state saved")

            print("[ML Intelligence] All models saved successfully")

        except Exception as e:
            print(f"[ML Intelligence] Save failed: {e}")


# Singleton instance
_orchestrator_instance = None


def get_ml_orchestrator() -> MLIntelligenceOrchestrator:
    """Get singleton ML Intelligence orchestrator"""
    global _orchestrator_instance

    if _orchestrator_instance is None:
        _orchestrator_instance = MLIntelligenceOrchestrator()
        _orchestrator_instance.initialize()

    return _orchestrator_instance


# Convenience function for direct integration
def enhance_learning_memory_with_ml():
    """
    Integrate ML Intelligence with existing learning memory system

    Call this during system initialization to enable ML enhancements
    """
    try:
        orchestrator = get_ml_orchestrator()

        print("[ML Intelligence] Enhanced learning memory system with ML/DL components")
        print("[ML Intelligence] Features enabled:")
        for feature, enabled in orchestrator.enabled_features.items():
            status = "✓" if enabled else "✗"
            print(f"  {status} {feature}")

        return orchestrator

    except Exception as e:
        print(f"[ML Intelligence] Enhancement failed: {e}")
        return None
