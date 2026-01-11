"""
Multi-Armed Bandit System - Intelligent Exploration/Exploitation

Optimizes learning topic selection using bandit algorithms.
Balances exploring new topics vs exploiting known high-value topics.

Algorithms Implemented:
- UCB1 (Upper Confidence Bound)
- Thompson Sampling (Bayesian)
- Epsilon-Greedy
- Contextual Bandits
- Exp3 (Exponential-weight algorithm for Exploration and Exploitation)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json
import os
from enum import Enum


class BanditAlgorithm(Enum):
    """Available bandit algorithms"""
    UCB1 = "ucb1"
    THOMPSON_SAMPLING = "thompson_sampling"
    EPSILON_GREEDY = "epsilon_greedy"
    CONTEXTUAL = "contextual"
    EXP3 = "exp3"


@dataclass
class TopicArm:
    """A bandit arm representing a learning topic"""
    topic_id: str
    topic_name: str

    # Statistics
    pulls: int = 0
    total_reward: float = 0.0
    mean_reward: float = 0.0

    # Thompson Sampling (Beta distribution parameters)
    successes: int = 1  # Prior: Beta(1, 1)
    failures: int = 1

    # Contextual features
    features: Dict[str, float] = field(default_factory=dict)

    # Metadata
    last_pulled: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class BanditContext:
    """Context for contextual bandits"""
    knowledge_gaps: Dict[str, float]  # topic_id -> gap size
    recent_failures: List[str]  # Recent failed topics
    user_interests: Dict[str, float]  # topic_id -> interest score
    time_of_day: int  # Hour of day (0-23)
    learning_velocity: float  # Recent learning rate


class MultiArmedBandit:
    """
    Multi-Armed Bandit for learning topic selection

    Optimally balances exploration (trying new topics) with
    exploitation (focusing on proven valuable topics)
    """

    def __init__(
        self,
        algorithm: BanditAlgorithm = BanditAlgorithm.THOMPSON_SAMPLING,
        epsilon: float = 0.1,  # For epsilon-greedy
        ucb_c: float = 2.0,  # For UCB1
        exp3_gamma: float = 0.1,  # For Exp3
        context_weight: float = 0.3,  # For contextual bandits
        save_path: str = None
    ):
        self.algorithm = algorithm
        self.epsilon = epsilon
        self.ucb_c = ucb_c
        self.exp3_gamma = exp3_gamma
        self.context_weight = context_weight

        # Arms (topics)
        self.arms: Dict[str, TopicArm] = {}

        # Total pulls across all arms
        self.total_pulls = 0

        # Exp3 weights
        self.exp3_weights = {}

        # Contextual bandit linear model (simple ridge regression)
        self.contextual_weights = defaultdict(float)

        # Statistics
        self.selection_history = []
        self.reward_history = []

        # Persistence
        self.save_path = save_path or os.path.join(
            os.path.dirname(__file__), '..', 'models', 'bandit_state.json'
        )

        # Load previous state if exists
        self.load_state()

    def add_arm(
        self,
        topic_id: str,
        topic_name: str,
        features: Dict[str, float] = None
    ):
        """
        Add a new arm (learning topic)

        Args:
            topic_id: Unique topic identifier
            topic_name: Human-readable topic name
            features: Contextual features for this topic
        """
        if topic_id not in self.arms:
            self.arms[topic_id] = TopicArm(
                topic_id=topic_id,
                topic_name=topic_name,
                features=features or {}
            )
            # Initialize Exp3 weight
            self.exp3_weights[topic_id] = 1.0

    def select_arm(
        self,
        context: Optional[BanditContext] = None,
        exclude_topics: List[str] = None
    ) -> str:
        """
        Select which topic to learn next

        Args:
            context: Optional context for contextual bandits
            exclude_topics: Topics to exclude from selection

        Returns:
            Selected topic_id
        """
        if not self.arms:
            raise ValueError("No arms available")

        # Filter excluded topics
        available_arms = {
            topic_id: arm
            for topic_id, arm in self.arms.items()
            if topic_id not in (exclude_topics or [])
        }

        if not available_arms:
            raise ValueError("No available arms after exclusions")

        # Select based on algorithm
        if self.algorithm == BanditAlgorithm.UCB1:
            selected_id = self._select_ucb1(available_arms)
        elif self.algorithm == BanditAlgorithm.THOMPSON_SAMPLING:
            selected_id = self._select_thompson_sampling(available_arms)
        elif self.algorithm == BanditAlgorithm.EPSILON_GREEDY:
            selected_id = self._select_epsilon_greedy(available_arms)
        elif self.algorithm == BanditAlgorithm.CONTEXTUAL:
            selected_id = self._select_contextual(available_arms, context)
        elif self.algorithm == BanditAlgorithm.EXP3:
            selected_id = self._select_exp3(available_arms)
        else:
            # Default to Thompson Sampling
            selected_id = self._select_thompson_sampling(available_arms)

        # Update statistics
        self.total_pulls += 1
        self.arms[selected_id].pulls += 1
        self.arms[selected_id].last_pulled = datetime.now()

        self.selection_history.append({
            'topic_id': selected_id,
            'timestamp': datetime.now().isoformat(),
            'algorithm': self.algorithm.value
        })

        return selected_id

    def _select_ucb1(self, available_arms: Dict[str, TopicArm]) -> str:
        """
        UCB1 algorithm: Upper Confidence Bound

        Formula: mean_reward + c * sqrt(ln(total_pulls) / arm_pulls)
        """
        ucb_scores = {}

        for topic_id, arm in available_arms.items():
            if arm.pulls == 0:
                # Infinite exploration bonus for unpulled arms
                ucb_scores[topic_id] = float('inf')
            else:
                exploration_bonus = self.ucb_c * np.sqrt(
                    np.log(self.total_pulls + 1) / arm.pulls
                )
                ucb_scores[topic_id] = arm.mean_reward + exploration_bonus

        # Select arm with highest UCB score
        return max(ucb_scores, key=ucb_scores.get)

    def _select_thompson_sampling(self, available_arms: Dict[str, TopicArm]) -> str:
        """
        Thompson Sampling: Bayesian approach

        Sample from Beta distribution for each arm, select highest sample
        """
        samples = {}

        for topic_id, arm in available_arms.items():
            # Sample from Beta(successes, failures)
            sample = np.random.beta(arm.successes, arm.failures)
            samples[topic_id] = sample

        return max(samples, key=samples.get)

    def _select_epsilon_greedy(self, available_arms: Dict[str, TopicArm]) -> str:
        """
        Epsilon-Greedy: Explore with probability epsilon, else exploit
        """
        if np.random.random() < self.epsilon:
            # Explore: random selection
            return np.random.choice(list(available_arms.keys()))
        else:
            # Exploit: select best mean reward
            return max(available_arms, key=lambda k: available_arms[k].mean_reward)

    def _select_contextual(
        self,
        available_arms: Dict[str, TopicArm],
        context: Optional[BanditContext]
    ) -> str:
        """
        Contextual Bandit: Use context to inform selection

        Combines base reward with context-weighted features
        """
        if context is None:
            # Fall back to Thompson Sampling without context
            return self._select_thompson_sampling(available_arms)

        scores = {}

        for topic_id, arm in available_arms.items():
            # Base score from Thompson Sampling
            base_score = np.random.beta(arm.successes, arm.failures)

            # Context score
            context_score = 0.0

            # Knowledge gap bonus
            if topic_id in context.knowledge_gaps:
                context_score += context.knowledge_gaps[topic_id] * 0.4

            # Recent failure bonus (learn from mistakes)
            if topic_id in context.recent_failures:
                context_score += 0.3

            # User interest bonus
            if topic_id in context.user_interests:
                context_score += context.user_interests[topic_id] * 0.2

            # Learning velocity adjustment
            context_score *= (1.0 + context.learning_velocity * 0.1)

            # Combine scores
            scores[topic_id] = (
                (1 - self.context_weight) * base_score +
                self.context_weight * context_score
            )

        return max(scores, key=scores.get)

    def _select_exp3(self, available_arms: Dict[str, TopicArm]) -> str:
        """
        Exp3: Exponential-weight algorithm for Exploration and Exploitation

        Good for adversarial/non-stationary environments
        """
        # Normalize weights into probabilities
        total_weight = sum(
            self.exp3_weights[topic_id]
            for topic_id in available_arms.keys()
        )

        probabilities = {
            topic_id: (
                (1 - self.exp3_gamma) * (self.exp3_weights[topic_id] / total_weight) +
                self.exp3_gamma / len(available_arms)
            )
            for topic_id in available_arms.keys()
        }

        # Sample from distribution
        topic_ids = list(probabilities.keys())
        probs = [probabilities[tid] for tid in topic_ids]

        selected_id = np.random.choice(topic_ids, p=probs)

        return selected_id

    def update_reward(
        self,
        topic_id: str,
        reward: float,
        context: Optional[BanditContext] = None
    ):
        """
        Update arm statistics based on observed reward

        Args:
            topic_id: Topic that was selected
            reward: Observed reward (0.0 to 1.0)
            context: Optional context used during selection
        """
        if topic_id not in self.arms:
            return

        arm = self.arms[topic_id]

        # Update reward statistics
        arm.total_reward += reward
        arm.mean_reward = arm.total_reward / arm.pulls

        # Update Thompson Sampling parameters
        if reward >= 0.5:
            arm.successes += 1
        else:
            arm.failures += 1

        # Update Exp3 weights
        if self.algorithm == BanditAlgorithm.EXP3:
            # Estimated reward
            prob = (
                (1 - self.exp3_gamma) * (self.exp3_weights[topic_id] / sum(self.exp3_weights.values())) +
                self.exp3_gamma / len(self.arms)
            )
            estimated_reward = reward / prob

            # Update weight
            self.exp3_weights[topic_id] *= np.exp(
                self.exp3_gamma * estimated_reward / len(self.arms)
            )

        # Update contextual weights if applicable
        if self.algorithm == BanditAlgorithm.CONTEXTUAL and context is not None:
            self._update_contextual_weights(topic_id, reward, context)

        # Record reward history
        self.reward_history.append({
            'topic_id': topic_id,
            'reward': reward,
            'timestamp': datetime.now().isoformat()
        })

        # Auto-save
        if len(self.reward_history) % 10 == 0:
            self.save_state()

    def _update_contextual_weights(
        self,
        topic_id: str,
        reward: float,
        context: BanditContext
    ):
        """Update contextual bandit weights (simple online learning)"""
        # Learning rate
        lr = 0.01

        # Prediction error
        arm = self.arms[topic_id]
        prediction = arm.mean_reward
        error = reward - prediction

        # Update weights for context features
        for feature_name, feature_value in arm.features.items():
            self.contextual_weights[feature_name] += lr * error * feature_value

    def get_arm_stats(self, topic_id: str) -> Dict:
        """Get statistics for a specific arm"""
        if topic_id not in self.arms:
            return {}

        arm = self.arms[topic_id]

        return {
            'topic_id': arm.topic_id,
            'topic_name': arm.topic_name,
            'pulls': arm.pulls,
            'mean_reward': arm.mean_reward,
            'total_reward': arm.total_reward,
            'success_rate': arm.successes / (arm.successes + arm.failures),
            'last_pulled': arm.last_pulled.isoformat() if arm.last_pulled else None
        }

    def get_all_stats(self) -> Dict:
        """Get statistics for all arms"""
        return {
            'total_pulls': self.total_pulls,
            'num_arms': len(self.arms),
            'algorithm': self.algorithm.value,
            'arms': {
                topic_id: self.get_arm_stats(topic_id)
                for topic_id in self.arms
            },
            'top_performers': self._get_top_performers(k=5)
        }

    def _get_top_performers(self, k: int = 5) -> List[Dict]:
        """Get top k performing arms"""
        sorted_arms = sorted(
            self.arms.values(),
            key=lambda arm: arm.mean_reward,
            reverse=True
        )

        return [
            {
                'topic_id': arm.topic_id,
                'topic_name': arm.topic_name,
                'mean_reward': arm.mean_reward,
                'pulls': arm.pulls
            }
            for arm in sorted_arms[:k]
        ]

    def recommend_next_topics(
        self,
        k: int = 3,
        context: Optional[BanditContext] = None,
        exclude_topics: List[str] = None
    ) -> List[Tuple[str, float]]:
        """
        Recommend top k topics to learn next

        Args:
            k: Number of recommendations
            context: Optional context
            exclude_topics: Topics to exclude

        Returns:
            List of (topic_id, score) tuples
        """
        available_arms = {
            topic_id: arm
            for topic_id, arm in self.arms.items()
            if topic_id not in (exclude_topics or [])
        }

        if not available_arms:
            return []

        # Calculate scores for all arms
        scores = {}

        if self.algorithm == BanditAlgorithm.UCB1:
            for topic_id, arm in available_arms.items():
                if arm.pulls == 0:
                    scores[topic_id] = float('inf')
                else:
                    exploration_bonus = self.ucb_c * np.sqrt(
                        np.log(self.total_pulls + 1) / arm.pulls
                    )
                    scores[topic_id] = arm.mean_reward + exploration_bonus

        elif self.algorithm == BanditAlgorithm.THOMPSON_SAMPLING:
            # Sample multiple times and average
            for topic_id, arm in available_arms.items():
                samples = [
                    np.random.beta(arm.successes, arm.failures)
                    for _ in range(100)
                ]
                scores[topic_id] = np.mean(samples)

        else:
            # Default to mean reward
            scores = {
                topic_id: arm.mean_reward
                for topic_id, arm in available_arms.items()
            }

        # Sort by score
        sorted_topics = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        return sorted_topics[:k]

    def save_state(self):
        """Save bandit state to disk"""
        state = {
            'algorithm': self.algorithm.value,
            'total_pulls': self.total_pulls,
            'arms': {
                topic_id: {
                    'topic_id': arm.topic_id,
                    'topic_name': arm.topic_name,
                    'pulls': arm.pulls,
                    'total_reward': arm.total_reward,
                    'mean_reward': arm.mean_reward,
                    'successes': arm.successes,
                    'failures': arm.failures,
                    'features': arm.features,
                    'last_pulled': arm.last_pulled.isoformat() if arm.last_pulled else None,
                    'created_at': arm.created_at.isoformat()
                }
                for topic_id, arm in self.arms.items()
            },
            'exp3_weights': self.exp3_weights,
            'contextual_weights': dict(self.contextual_weights),
            'selection_history': self.selection_history[-1000:],  # Last 1000
            'reward_history': self.reward_history[-1000:]  # Last 1000
        }

        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
        with open(self.save_path, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self):
        """Load bandit state from disk"""
        if not os.path.exists(self.save_path):
            return False

        with open(self.save_path, 'r') as f:
            state = json.load(f)

        self.total_pulls = state.get('total_pulls', 0)

        # Restore arms
        for topic_id, arm_data in state.get('arms', {}).items():
            arm = TopicArm(
                topic_id=arm_data['topic_id'],
                topic_name=arm_data['topic_name'],
                pulls=arm_data['pulls'],
                total_reward=arm_data['total_reward'],
                mean_reward=arm_data['mean_reward'],
                successes=arm_data['successes'],
                failures=arm_data['failures'],
                features=arm_data.get('features', {}),
                last_pulled=datetime.fromisoformat(arm_data['last_pulled']) if arm_data.get('last_pulled') else None,
                created_at=datetime.fromisoformat(arm_data['created_at'])
            )
            self.arms[topic_id] = arm

        self.exp3_weights = state.get('exp3_weights', {})
        self.contextual_weights = defaultdict(float, state.get('contextual_weights', {}))
        self.selection_history = state.get('selection_history', [])
        self.reward_history = state.get('reward_history', [])

        return True


# Singleton instance
_bandit_instance = None


def get_bandit(
    algorithm: BanditAlgorithm = BanditAlgorithm.THOMPSON_SAMPLING
) -> MultiArmedBandit:
    """Get singleton bandit instance"""
    global _bandit_instance

    if _bandit_instance is None:
        _bandit_instance = MultiArmedBandit(algorithm=algorithm)

    return _bandit_instance
