"""
Hebbian Learning for Brain Synapses.

"Neurons that fire together wire together."

Tracks which brains collaborate, strengthens successful connections,
weakens failed ones. Provides routing hints — prefer brains with
stronger synaptic weights for cross-brain orchestration.

This is NOT a P2P mesh protocol. It's a lightweight weight table
that sits on top of call_brain() and learns from Genesis key patterns.
"""

import time
import threading
import logging
import json
from collections import defaultdict
from typing import Dict, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DECAY_RATE = 0.01
STRENGTHEN_RATE = 0.05
WEAKEN_RATE = 0.03
MIN_WEIGHT = 0.1
MAX_WEIGHT = 2.0
INITIAL_WEIGHT = 0.5


class Synapse:
    """A weighted connection between two brains."""
    __slots__ = ("weight", "calls", "successes", "failures", "last_fired")

    def __init__(self):
        self.weight = INITIAL_WEIGHT
        self.calls = 0
        self.successes = 0
        self.failures = 0
        self.last_fired = time.time()

    def fire(self, success: bool):
        """Strengthen on success, weaken on failure."""
        self.calls += 1
        self.last_fired = time.time()
        if success:
            self.successes += 1
            self.weight = min(MAX_WEIGHT, self.weight + STRENGTHEN_RATE)
        else:
            self.failures += 1
            self.weight = max(MIN_WEIGHT, self.weight - WEAKEN_RATE)

    def decay(self):
        """Unused connections decay over time."""
        age = time.time() - self.last_fired
        if age > 300:
            self.weight = max(MIN_WEIGHT, self.weight - DECAY_RATE * (age / 300))

    def to_dict(self):
        return {
            "weight": round(self.weight, 3),
            "calls": self.calls,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": round(self.successes / self.calls, 3) if self.calls > 0 else 0,
            "last_fired": self.last_fired,
        }


class HebbianMesh:
    """
    The synaptic weight table for Grace's brain mesh.

    Usage:
        mesh = get_hebbian_mesh()
        mesh.record("chat", "ai", success=True)   # chat→ai synapse strengthens
        mesh.record("system", "ai", success=False) # system→ai weakens
        weights = mesh.get_weights()               # full weight table
        best = mesh.best_path("chat", ["ai", "system"]) # highest-weight target
    """

    def __init__(self):
        self._synapses: Dict[Tuple[str, str], Synapse] = {}
        self._lock = threading.Lock()

    def record(self, source: str, target: str, success: bool = True):
        """Record a brain-to-brain interaction."""
        key = (source, target)
        with self._lock:
            if key not in self._synapses:
                self._synapses[key] = Synapse()
            self._synapses[key].fire(success)

        try:
            from api._genesis_tracker import track
            syn = self._synapses[key]
            track(
                key_type="system_event",
                what=f"Synapse {source}→{target}: {'↑' if success else '↓'} w={syn.weight:.3f}",
                who="hebbian_mesh",
                tags=["hebbian", "synapse", source, target],
            )
        except Exception:
            pass

    def get_weight(self, source: str, target: str) -> float:
        """Get the synaptic weight between two brains."""
        key = (source, target)
        with self._lock:
            if key in self._synapses:
                return self._synapses[key].weight
        return INITIAL_WEIGHT

    def best_path(self, source: str, targets: list) -> Optional[str]:
        """Choose the target brain with the strongest synapse from source."""
        if not targets:
            return None
        with self._lock:
            weights = []
            for t in targets:
                key = (source, t)
                w = self._synapses[key].weight if key in self._synapses else INITIAL_WEIGHT
                weights.append((t, w))
        weights.sort(key=lambda x: -x[1])
        return weights[0][0]

    def get_weights(self) -> dict:
        """Get the full synaptic weight table."""
        with self._lock:
            # Decay all synapses
            for syn in self._synapses.values():
                syn.decay()

            result = {}
            for (source, target), syn in sorted(self._synapses.items()):
                if source not in result:
                    result[source] = {}
                result[source][target] = syn.to_dict()
            return result

    def get_strongest(self, n: int = 10) -> list:
        """Get the N strongest synapses."""
        with self._lock:
            all_synapses = [
                {"source": s, "target": t, **syn.to_dict()}
                for (s, t), syn in self._synapses.items()
            ]
        all_synapses.sort(key=lambda x: -x["weight"])
        return all_synapses[:n]

    def get_brain_connectivity(self, brain: str) -> dict:
        """Get all connections for a specific brain."""
        with self._lock:
            outgoing = {t: syn.to_dict() for (s, t), syn in self._synapses.items() if s == brain}
            incoming = {s: syn.to_dict() for (s, t), syn in self._synapses.items() if t == brain}
        return {"outgoing": outgoing, "incoming": incoming}


_mesh: Optional[HebbianMesh] = None


def get_hebbian_mesh() -> HebbianMesh:
    global _mesh
    if _mesh is None:
        _mesh = HebbianMesh()
    return _mesh
