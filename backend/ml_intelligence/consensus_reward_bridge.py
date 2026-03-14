"""
Consensus → RL Reward Bridge

Closes the reinforcement loop by feeding consensus results
into the Multi-Armed Bandit system as reward signals.

When consensus quorum is committed:
  - Agreement-dominant: positive reward for participating models/topics
  - Disagreement-dominant: inverted reward (negative signal)
  - Confidence maps to reward magnitude
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ConsensusRewardBridge:
    """Bridges consensus quorum events to RL reward updates."""

    _instance = None
    _started = False

    @classmethod
    def get_instance(cls) -> "ConsensusRewardBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self):
        """Subscribe to consensus events on the event bus."""
        if self._started:
            return
        self._started = True
        try:
            from cognitive.event_bus import subscribe
            subscribe("consensus.quorum_committed", self._on_quorum_committed)
            subscribe("consensus.completed", self._on_consensus_completed)
            logger.info("[RL-BRIDGE] Subscribed to consensus events for reward updates")
        except Exception as e:
            logger.warning(f"[RL-BRIDGE] Failed to subscribe to event bus: {e}")

    def _on_quorum_committed(self, event: Dict[str, Any]):
        """Process a committed quorum packet as a reward signal."""
        try:
            data = event.get("data", event)
            confidence = data.get("confidence", 0.5)
            passed = data.get("passed", False)
            models = data.get("models", [])

            reward = self._compute_reward(confidence, passed)
            self._feed_bandit(models, reward)
            self._feed_trust_scorekeeper(models, reward)
        except Exception as e:
            logger.debug(f"[RL-BRIDGE] Quorum reward processing error: {e}")

    def _on_consensus_completed(self, event: Dict[str, Any]):
        """Process consensus completion with agreement/disagreement ratio."""
        try:
            data = event.get("data", event)
            agreements = data.get("agreements", 0)
            disagreements = data.get("disagreements", 0)
            confidence = data.get("confidence", 0.5)
            models = data.get("models", [])

            if isinstance(agreements, list):
                agreements = len(agreements)
            if isinstance(disagreements, list):
                disagreements = len(disagreements)

            total = agreements + disagreements
            if total == 0:
                return

            # Reward inversion: disagreement-dominant → negative signal
            agreement_ratio = agreements / total
            if agreement_ratio >= 0.5:
                reward = confidence * agreement_ratio
            else:
                reward = -confidence * (1.0 - agreement_ratio) * 0.5

            self._feed_bandit(models, reward)
        except Exception as e:
            logger.debug(f"[RL-BRIDGE] Consensus reward processing error: {e}")

    def _compute_reward(self, confidence: float, passed: bool) -> float:
        """Compute reward from confidence and verification status."""
        base = confidence if passed else confidence * 0.3
        return max(-1.0, min(1.0, base))

    def _feed_bandit(self, models: list, reward: float):
        """Feed reward to the Multi-Armed Bandit for each model topic."""
        try:
            from ml_intelligence.multi_armed_bandit import get_bandit
            bandit = get_bandit()
            for model_id in models:
                topic_id = f"model_{model_id}"
                if topic_id not in bandit.arms:
                    bandit.add_arm(topic_id, f"Model: {model_id}")
                arm = bandit.arms[topic_id]
                # Ensure pulls >= 1 so update_reward won't divide by zero
                if arm.pulls == 0:
                    arm.pulls = 1
                # Normalize reward to [0, 1] for bandit
                normalized = max(0.0, min(1.0, (reward + 1.0) / 2.0))
                bandit.update_reward(topic_id, normalized)
            logger.debug(f"[RL-BRIDGE] Fed reward={reward:.3f} to bandit for {len(models)} models")
        except Exception as e:
            logger.debug(f"[RL-BRIDGE] Bandit update failed: {e}")

    def _feed_trust_scorekeeper(self, models: list, reward: float):
        """Also update the trust scorekeeper with reward signals."""
        try:
            from core.intelligence import AdaptiveTrust
            for mid in models:
                AdaptiveTrust.record_outcome(
                    model_id=mid,
                    success=reward > 0,
                    confidence=abs(reward),
                )
        except Exception:
            pass


def get_consensus_reward_bridge() -> ConsensusRewardBridge:
    return ConsensusRewardBridge.get_instance()
