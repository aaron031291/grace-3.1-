"""
Unified Intelligence Layer — ML/DL/Neuro-Symbolic Integration

The top of Grace's cognitive stack. Below Genesis Keys (provenance),
above the cognitive pipeline (reasoning). This layer synthesises data
from ALL 12 named system loops into structured learning signals.

Architecture (bottom to top):
  ┌─────────────────────────────────────────────────────────────┐
  │  ML/DL Intelligence Layer (THIS MODULE)                     │
  │  ├── Pattern Recognition Engine (ML)                        │
  │  ├── Deep Representation Learning (DL)                      │
  │  ├── Neuro-Symbolic Reasoning (hybrid)                      │
  │  └── Loop Data Synthesiser (feeds from all 12 loops)        │
  ├─────────────────────────────────────────────────────────────┤
  │  Cognitive Pipeline (9-stage reasoning)                      │
  ├─────────────────────────────────────────────────────────────┤
  │  Consensus Engine (multi-model roundtable)                   │
  ├─────────────────────────────────────────────────────────────┤
  │  Trust Engine + Immune System (verification)                 │
  ├─────────────────────────────────────────────────────────────┤
  │  Unified Memory (episodic + procedural + flash + magma)      │
  ├─────────────────────────────────────────────────────────────┤
  │  Genesis Keys (provenance tracking)                          │
  └─────────────────────────────────────────────────────────────┘

The 12 named loops feed data continuously:
  - Homeostasis loops → system stability patterns
  - Learning loops → knowledge acquisition patterns
  - Healing loops → failure/recovery patterns
  - Trust loops → reliability patterns
  - Knowledge loops → information flow patterns

Three sub-systems at the same hierarchical level:
  1. ML (Pattern Recognition): Statistical patterns from loop metrics
  2. DL (Deep Representations): Embeddings and feature learning
  3. Neuro-Symbolic (Hybrid Reasoning): Rules + learned patterns
"""

import json
import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "intelligence_layer"


# ── ML: Pattern Recognition Engine ───────────────────────────────────

class PatternRecognitionEngine:
    """
    Statistical pattern recognition from loop execution data.
    Learns: what works, what fails, what improves, what degrades.
    """

    def __init__(self):
        self._patterns: Dict[str, List[Dict]] = defaultdict(list)
        self._load_patterns()

    def observe(self, loop_name: str, metrics: Dict[str, float], outcome: str):
        """Record an observation from a loop execution."""
        observation = {
            "timestamp": datetime.utcnow().isoformat(),
            "loop": loop_name,
            "metrics": metrics,
            "outcome": outcome,  # success, failure, improvement, degradation
        }
        self._patterns[loop_name].append(observation)
        if len(self._patterns[loop_name]) > 1000:
            self._patterns[loop_name] = self._patterns[loop_name][-500:]
        self._save_patterns()

    def detect_patterns(self, loop_name: str = None) -> List[Dict[str, Any]]:
        """Detect statistical patterns from observations."""
        detected = []

        loops = [loop_name] if loop_name else list(self._patterns.keys())
        for ln in loops:
            obs = self._patterns.get(ln, [])
            if len(obs) < 3:
                continue

            outcomes = [o["outcome"] for o in obs]
            success_rate = outcomes.count("success") / len(outcomes) if outcomes else 0
            improvement_rate = outcomes.count("improvement") / len(outcomes) if outcomes else 0

            # Trend detection (last 10 vs previous 10)
            if len(obs) >= 20:
                recent = obs[-10:]
                previous = obs[-20:-10]
                recent_success = sum(1 for o in recent if o["outcome"] == "success") / 10
                prev_success = sum(1 for o in previous if o["outcome"] == "success") / 10
                trend = "improving" if recent_success > prev_success else "degrading" if recent_success < prev_success else "stable"
            else:
                trend = "insufficient_data"

            # Metric correlation
            metric_trends = {}
            if obs:
                latest = obs[-1].get("metrics", {})
                earliest = obs[0].get("metrics", {})
                for key in latest:
                    if key in earliest and earliest[key] != 0:
                        delta = ((latest[key] - earliest[key]) / abs(earliest[key])) * 100
                        metric_trends[key] = round(delta, 2)

            detected.append({
                "loop": ln,
                "observations": len(obs),
                "success_rate": round(success_rate, 3),
                "improvement_rate": round(improvement_rate, 3),
                "trend": trend,
                "metric_trends": metric_trends,
                "pattern_type": "ml_statistical",
            })

        return detected

    def predict_outcome(self, loop_name: str, current_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Predict likely outcome based on historical patterns (simple kNN-style)."""
        obs = self._patterns.get(loop_name, [])
        if len(obs) < 5:
            return {"prediction": "unknown", "confidence": 0, "reason": "insufficient_data"}

        # Find most similar past observations by metric distance
        similarities = []
        for o in obs[-100:]:
            past_metrics = o.get("metrics", {})
            common_keys = set(current_metrics.keys()) & set(past_metrics.keys())
            if not common_keys:
                continue
            distance = sum((current_metrics[k] - past_metrics.get(k, 0)) ** 2 for k in common_keys)
            distance = math.sqrt(distance) if distance > 0 else 0
            similarities.append((distance, o["outcome"]))

        if not similarities:
            return {"prediction": "unknown", "confidence": 0}

        similarities.sort(key=lambda x: x[0])
        k = min(5, len(similarities))
        neighbors = similarities[:k]

        outcome_votes = defaultdict(int)
        for dist, outcome in neighbors:
            weight = 1 / (dist + 0.001)
            outcome_votes[outcome] += weight

        predicted = max(outcome_votes, key=outcome_votes.get)
        total_weight = sum(outcome_votes.values())
        confidence = outcome_votes[predicted] / total_weight if total_weight > 0 else 0

        return {
            "prediction": predicted,
            "confidence": round(confidence, 3),
            "neighbors_used": k,
            "pattern_type": "ml_knn",
        }

    def _load_patterns(self):
        path = DATA_DIR / "ml_patterns.json"
        if path.exists():
            try:
                self._patterns = defaultdict(list, json.loads(path.read_text()))
            except Exception:
                pass

    def _save_patterns(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "ml_patterns.json").write_text(
            json.dumps(dict(self._patterns), indent=2, default=str)
        )


# ── DL: Deep Representation Learning ─────────────────────────────────

class DeepRepresentationEngine:
    """
    Learns dense representations (embeddings) from system behaviour.
    When a proper embedding model is available, this creates vector
    representations of:
      - Loop execution patterns
      - Component interaction signatures
      - Failure/success fingerprints

    Without GPU: uses statistical feature vectors as a proxy.
    With GPU: uses the embedding model for true deep representations.
    """

    def __init__(self):
        self._feature_store: Dict[str, List[float]] = {}
        self._load_features()

    def compute_features(self, entity: str, data: Dict[str, Any]) -> List[float]:
        """Compute a feature vector for an entity (loop, component, action)."""
        features = []

        # Numeric features
        for key in sorted(data.keys()):
            val = data[key]
            if isinstance(val, (int, float)):
                features.append(float(val))
            elif isinstance(val, bool):
                features.append(1.0 if val else 0.0)
            elif isinstance(val, str):
                features.append(float(len(val)))
            elif isinstance(val, list):
                features.append(float(len(val)))

        # Normalise to unit length
        magnitude = math.sqrt(sum(f * f for f in features)) if features else 1.0
        if magnitude > 0:
            features = [f / magnitude for f in features]

        self._feature_store[entity] = features
        self._save_features()
        return features

    def similarity(self, entity_a: str, entity_b: str) -> float:
        """Cosine similarity between two entity feature vectors."""
        vec_a = self._feature_store.get(entity_a, [])
        vec_b = self._feature_store.get(entity_b, [])
        if not vec_a or not vec_b:
            return 0.0

        min_len = min(len(vec_a), len(vec_b))
        vec_a = vec_a[:min_len]
        vec_b = vec_b[:min_len]

        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = math.sqrt(sum(a * a for a in vec_a))
        mag_b = math.sqrt(sum(b * b for b in vec_b))

        if mag_a == 0 or mag_b == 0:
            return 0.0
        return round(dot / (mag_a * mag_b), 4)

    def find_similar(self, entity: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Find the most similar entities to the given one."""
        if entity not in self._feature_store:
            return []

        similarities = []
        for other in self._feature_store:
            if other == entity:
                continue
            sim = self.similarity(entity, other)
            similarities.append((other, sim))

        similarities.sort(key=lambda x: -x[1])
        return similarities[:top_k]

    def _load_features(self):
        path = DATA_DIR / "dl_features.json"
        if path.exists():
            try:
                self._feature_store = json.loads(path.read_text())
            except Exception:
                pass

    def _save_features(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "dl_features.json").write_text(
            json.dumps(self._feature_store, indent=2)
        )


# ── Neuro-Symbolic: Hybrid Reasoning ─────────────────────────────────

class NeuroSymbolicEngine:
    """
    Combines learned patterns (neural/statistical) with explicit rules
    (symbolic) for robust reasoning. At the same hierarchical level as
    ML and DL — they interconnect.

    Rules come from:
      - Governance documents (uploaded laws)
      - System invariants (coded constraints)
      - Learned patterns that achieved >90% success rate

    Neural signals come from:
      - ML pattern recognition engine
      - DL feature representations
      - Trust engine scores
    """

    def __init__(self):
        self._rules: List[Dict[str, Any]] = []
        self._learned_rules: List[Dict[str, Any]] = []
        self._load_rules()

    def add_rule(self, name: str, condition: str, action: str,
                 source: str = "explicit", confidence: float = 1.0):
        """Add a symbolic rule."""
        rule = {
            "name": name,
            "condition": condition,
            "action": action,
            "source": source,
            "confidence": confidence,
            "created_at": datetime.utcnow().isoformat(),
            "times_applied": 0,
            "times_correct": 0,
        }
        self._rules.append(rule)
        self._save_rules()

    def promote_pattern_to_rule(self, pattern: Dict[str, Any]):
        """
        When an ML pattern achieves >90% success rate, promote it
        to a neuro-symbolic rule for deterministic application.
        """
        if pattern.get("success_rate", 0) < 0.9:
            return None

        rule = {
            "name": f"learned_{pattern['loop']}_{len(self._learned_rules)}",
            "condition": f"loop={pattern['loop']} AND trend={pattern.get('trend', 'stable')}",
            "action": f"apply_pattern(success_rate={pattern['success_rate']})",
            "source": "ml_promoted",
            "confidence": pattern["success_rate"],
            "created_at": datetime.utcnow().isoformat(),
            "original_pattern": pattern,
            "times_applied": 0,
            "times_correct": 0,
        }
        self._learned_rules.append(rule)
        self._save_rules()
        return rule

    def evaluate(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate all rules against current context.
        Returns applicable rules ranked by confidence.
        """
        applicable = []
        all_rules = self._rules + self._learned_rules

        for rule in all_rules:
            if self._condition_matches(rule["condition"], context):
                applicable.append({
                    "rule_name": rule["name"],
                    "action": rule["action"],
                    "confidence": rule["confidence"],
                    "source": rule["source"],
                })

        applicable.sort(key=lambda x: -x["confidence"])
        return applicable

    def _condition_matches(self, condition: str, context: Dict[str, Any]) -> bool:
        """Simple condition matching against context."""
        parts = condition.split(" AND ")
        for part in parts:
            if "=" in part:
                key, val = part.split("=", 1)
                key = key.strip()
                val = val.strip()
                ctx_val = str(context.get(key, ""))
                if ctx_val != val:
                    return False
        return True

    def get_stats(self) -> Dict[str, Any]:
        return {
            "explicit_rules": len(self._rules),
            "learned_rules": len(self._learned_rules),
            "total": len(self._rules) + len(self._learned_rules),
        }

    def _load_rules(self):
        path = DATA_DIR / "neuro_symbolic_rules.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self._rules = data.get("explicit", [])
                self._learned_rules = data.get("learned", [])
            except Exception:
                pass

    def _save_rules(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "neuro_symbolic_rules.json").write_text(json.dumps({
            "explicit": self._rules,
            "learned": self._learned_rules,
        }, indent=2, default=str))


# ── Unified Intelligence Layer ────────────────────────────────────────

class UnifiedIntelligenceLayer:
    """
    The top-level intelligence synthesiser. Combines ML, DL, and
    neuro-symbolic reasoning into a single coherent intelligence output.

    Called by:
      - Central Orchestrator (for decision-making)
      - Pipeline (for enriched generation)
      - Consensus Engine (for informed synthesis)
      - Reporting Engine (for intelligence metrics)
    """

    _instance = None

    def __init__(self):
        self.ml = PatternRecognitionEngine()
        self.dl = DeepRepresentationEngine()
        self.ns = NeuroSymbolicEngine()

    @classmethod
    def get_instance(cls) -> "UnifiedIntelligenceLayer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def observe_loop(self, loop_name: str, metrics: Dict[str, float], outcome: str):
        """
        Record a loop execution observation.
        Feeds ML pattern recognition AND DL feature learning simultaneously.
        """
        self.ml.observe(loop_name, metrics, outcome)
        self.dl.compute_features(f"loop_{loop_name}", metrics)

        # Check if any patterns should be promoted to neuro-symbolic rules
        patterns = self.ml.detect_patterns(loop_name)
        for p in patterns:
            if p.get("success_rate", 0) >= 0.9 and p.get("observations", 0) >= 10:
                self.ns.promote_pattern_to_rule(p)

    def predict(self, loop_name: str, metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Unified prediction combining ML + DL + Neuro-Symbolic.
        """
        # ML prediction
        ml_pred = self.ml.predict_outcome(loop_name, metrics)

        # Neuro-symbolic rules
        ns_rules = self.ns.evaluate({"loop": loop_name, **{str(k): str(v) for k, v in metrics.items()}})

        # DL similarity
        self.dl.compute_features(f"query_{loop_name}", metrics)
        similar = self.dl.find_similar(f"query_{loop_name}", top_k=3)

        # Synthesise
        confidence = ml_pred.get("confidence", 0)
        if ns_rules:
            confidence = max(confidence, ns_rules[0]["confidence"])

        return {
            "ml_prediction": ml_pred,
            "symbolic_rules": ns_rules[:3],
            "similar_entities": similar,
            "unified_confidence": round(confidence, 3),
            "recommendation": ml_pred.get("prediction", "unknown"),
        }

    def collect_loop_data(self) -> Dict[str, Any]:
        """
        Collect current data from all 12 named loops for learning.
        Called periodically by the reporting engine.
        """
        from cognitive.circuit_breaker import get_loop_status
        loop_status = get_loop_status()

        data = {}
        for loop_name, status in loop_status.items():
            metrics = {
                "executions": status.get("total_executions", 0),
                "breaks": status.get("total_breaks", 0),
                "current_depth": status.get("current_depth", 0),
            }

            # Determine outcome
            break_rate = metrics["breaks"] / max(metrics["executions"], 1)
            if break_rate > 0.1:
                outcome = "degradation"
            elif metrics["executions"] > 0:
                outcome = "success"
            else:
                outcome = "idle"

            self.observe_loop(loop_name, metrics, outcome)
            data[loop_name] = {"metrics": metrics, "outcome": outcome}

        return data

    def get_intelligence_summary(self) -> Dict[str, Any]:
        """Full intelligence layer summary for dashboards and reports."""
        ml_patterns = self.ml.detect_patterns()
        ns_stats = self.ns.get_stats()

        return {
            "ml": {
                "patterns_detected": len(ml_patterns),
                "patterns": ml_patterns,
            },
            "dl": {
                "entities_tracked": len(self.dl._feature_store),
            },
            "neuro_symbolic": ns_stats,
            "layer_status": "active",
        }

    def add_governance_rule(self, name: str, condition: str, action: str):
        """Add an explicit governance rule to the neuro-symbolic layer."""
        self.ns.add_rule(name, condition, action, source="governance", confidence=1.0)


def get_intelligence_layer() -> UnifiedIntelligenceLayer:
    return UnifiedIntelligenceLayer.get_instance()
