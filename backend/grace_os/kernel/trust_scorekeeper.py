"""
Grace OS — Trust Scorekeeper (Genesis Key System)

Global scoring system that tracks confidence at every checkpoint.
Records per-layer trust scores, computes aggregates, enforces threshold gates,
and maintains full audit history with time-based decay.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS = {
    "deploy": 85.0,
    "warn": 70.0,
    "abort": 50.0,
}

DEFAULT_LAYER_WEIGHTS = {
    "L1_Runtime": 0.8,
    "L2_Planning": 1.0,
    "L3_Proposer": 0.9,
    "L4_Evaluator": 1.0,
    "L5_Simulation": 1.1,
    "L6_Codegen": 1.0,
    "L7_Testing": 1.2,
    "L8_Verification": 1.2,
    "L9_Deployment": 1.0,
}

DECAY_RATE_PER_SECOND = 0.01  # 1% per second of inactivity


@dataclass
class ScoreEntry:
    """A single trust score record."""
    layer: str
    score: float
    timestamp: float = field(default_factory=time.time)
    message_type: str = ""
    message_id: str = ""


class TrustScorekeeper:
    """
    Tracks trust scores across all Grace OS layers within sessions.
    """

    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        layer_weights: Optional[Dict[str, float]] = None,
        decay_rate: float = DECAY_RATE_PER_SECOND,
    ):
        self.thresholds = thresholds or DEFAULT_THRESHOLDS.copy()
        self.layer_weights = layer_weights or DEFAULT_LAYER_WEIGHTS.copy()
        self.decay_rate = decay_rate

        # trace_id -> list of ScoreEntry
        self._history: Dict[str, List[ScoreEntry]] = {}

    def record_score(
        self,
        trace_id: str,
        layer: str,
        score: float,
        message_type: str = "",
        message_id: str = "",
    ):
        """Record a trust score from a layer for a given session."""
        if trace_id not in self._history:
            self._history[trace_id] = []

        entry = ScoreEntry(
            layer=layer,
            score=score,
            message_type=message_type,
            message_id=message_id,
        )
        self._history[trace_id].append(entry)

        logger.debug(
            f"[TrustScorekeeper] Recorded: {layer}={score:.1f} "
            f"(session={trace_id[:8]})"
        )

    def get_latest_scores(self, trace_id: str) -> Dict[str, float]:
        """Get the most recent score for each layer in a session."""
        entries = self._history.get(trace_id, [])
        latest: Dict[str, float] = {}
        for entry in entries:
            latest[entry.layer] = entry.score
        return latest

    def get_aggregate(self, trace_id: str, apply_decay: bool = False) -> float:
        """
        Compute weighted aggregate trust score for a session.
        Optionally applies time-based decay.
        """
        latest = self.get_latest_scores(trace_id)
        if not latest:
            return 0.0

        now = time.time()
        total_weighted = 0.0
        total_weight = 0.0

        for layer, score in latest.items():
            weight = self.layer_weights.get(layer, 1.0)

            if apply_decay:
                # Find the timestamp of this layer's last score
                entries = [
                    e for e in self._history.get(trace_id, [])
                    if e.layer == layer
                ]
                if entries:
                    age_seconds = now - entries[-1].timestamp
                    decay = max(0.0, 1.0 - (self.decay_rate * age_seconds))
                    score = score * decay

            total_weighted += score * weight
            total_weight += weight

        return total_weighted / total_weight if total_weight > 0 else 0.0

    def check_threshold(self, trace_id: str, gate_name: str) -> Tuple[bool, float]:
        """
        Check if a session meets a named threshold gate.
        Returns (passed, current_score).
        """
        threshold = self.thresholds.get(gate_name, 85.0)
        aggregate = self.get_aggregate(trace_id)
        passed = aggregate >= threshold
        return passed, aggregate

    def get_history(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get full score history for a session."""
        entries = self._history.get(trace_id, [])
        return [
            {
                "layer": e.layer,
                "score": e.score,
                "timestamp": e.timestamp,
                "message_type": e.message_type,
                "message_id": e.message_id,
            }
            for e in entries
        ]

    def get_all_sessions(self) -> List[str]:
        """List all tracked session trace IDs."""
        return list(self._history.keys())

    def clear_session(self, trace_id: str):
        """Remove all score data for a session."""
        if trace_id in self._history:
            del self._history[trace_id]
