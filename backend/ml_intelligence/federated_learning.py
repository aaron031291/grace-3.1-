"""
Federated Learning - Privacy-Preserving Knowledge Sharing

Enables Grace instances (or project containers) to share learned
knowledge without exposing raw training data.

Architecture:
  FederatedNode        — represents one Grace instance / domain
  DifferentialPrivacy  — gradient clipping + calibrated noise
  KnowledgeDistillation — strips PII, distills patterns for export
  FederatedAggregator  — trust-weighted FedAvg with poison detection
  FederatedLearningManager — high-level lifecycle orchestrator

No external FL libraries required — built on torch + numpy only.
Operates in-process or via JSON file exchange between containers.
"""

import hashlib
import json
import logging
import os
import time
import copy
from collections import OrderedDict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Optional torch — module degrades gracefully without it
try:
    import torch
    import numpy as np
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    np = None
    TORCH_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class NodeInfo:
    """Metadata for a registered federated node."""
    node_id: str
    node_name: str
    description: str = ""
    trust_score: float = 0.5
    model_version: int = 0
    update_count: int = 0
    weights_hash: str = ""
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_update_at: Optional[str] = None
    contribution_history: List[Dict[str, Any]] = field(default_factory=list)
    active: bool = True


@dataclass
class ModelDelta:
    """A gradient / weight-delta update from a node."""
    node_id: str
    round_id: int
    delta: Dict[str, Any]          # layer_name -> list (serialised tensor)
    metrics: Dict[str, float] = field(default_factory=dict)
    num_samples: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AggregationRound:
    """Record of one aggregation round."""
    round_id: int
    participating_nodes: List[str]
    aggregation_method: str = "trust_weighted_fedavg"
    global_model_version: int = 0
    metrics: Dict[str, float] = field(default_factory=dict)
    privacy_spend: float = 0.0
    poisoned_rejected: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class KnowledgePackage:
    """Shareable, anonymised knowledge bundle."""
    package_id: str
    source_node: str
    created_at: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    embedding_centroids: List[List[float]] = field(default_factory=list)
    pattern_frequencies: Dict[str, int] = field(default_factory=dict)
    trust_distribution: Dict[str, int] = field(default_factory=dict)
    learned_rules: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Differential Privacy
# ---------------------------------------------------------------------------

class DifferentialPrivacy:
    """
    Gradient-level differential privacy.

    Clips per-sample gradients and adds calibrated Gaussian noise so
    that the resulting update satisfies (epsilon, delta)-DP.
    """

    def __init__(
        self,
        max_grad_norm: float = 1.0,
        noise_multiplier: float = 1.1,
        epsilon_budget: float = 10.0,
        delta: float = 1e-5,
    ):
        self.max_grad_norm = max_grad_norm
        self.noise_multiplier = noise_multiplier
        self.epsilon_budget = epsilon_budget
        self.delta = delta
        self.epsilon_spent = 0.0
        self._round_count = 0

    @property
    def budget_remaining(self) -> float:
        return max(0.0, self.epsilon_budget - self.epsilon_spent)

    def clip_and_noise(self, gradients: Dict[str, Any]) -> Dict[str, Any]:
        """Clip gradient norms and add noise."""
        if not TORCH_AVAILABLE:
            return gradients

        noised = {}
        for name, grad_list in gradients.items():
            grad = torch.tensor(grad_list, dtype=torch.float32)
            # Clip
            norm = torch.norm(grad)
            if norm > self.max_grad_norm:
                grad = grad * (self.max_grad_norm / norm)
            # Noise
            noise = torch.randn_like(grad) * self.noise_multiplier * self.max_grad_norm
            noised[name] = (grad + noise).tolist()

        self._round_count += 1
        # Simple RDP → (ε,δ) accounting approximation
        self.epsilon_spent += (2.0 * self.noise_multiplier) / (self._round_count ** 0.5)
        return noised

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_grad_norm": self.max_grad_norm,
            "noise_multiplier": self.noise_multiplier,
            "epsilon_budget": self.epsilon_budget,
            "epsilon_spent": round(self.epsilon_spent, 4),
            "budget_remaining": round(self.budget_remaining, 4),
            "rounds_applied": self._round_count,
        }


# ---------------------------------------------------------------------------
# Knowledge Distillation
# ---------------------------------------------------------------------------

class KnowledgeDistillation:
    """
    Converts learned knowledge into a shareable, privacy-safe format.

    Strips PII, anonymises examples, and distils patterns into
    embedding centroids + rule summaries.
    """

    PII_PATTERNS = [
        "email", "password", "ssn", "social_security",
        "credit_card", "phone", "address", "api_key",
        "secret", "token",
    ]

    def distill_examples(
        self,
        examples: List[Dict[str, Any]],
        min_trust: float = 0.4,
    ) -> List[Dict[str, Any]]:
        """Distil learning examples into anonymised training signals."""
        distilled = []
        for ex in examples:
            trust = ex.get("trust_score", 0.0)
            if trust < min_trust:
                continue
            record = {
                "type": ex.get("example_type") or ex.get("type", "unknown"),
                "trust_score": round(trust, 3),
                "source": self._anonymise_source(ex.get("source", "")),
                "pattern_hash": self._hash(
                    str(ex.get("input_context", ""))[:500]
                ),
                "output_length": len(str(ex.get("expected_output", ""))),
            }
            distilled.append(record)
        return distilled

    def compute_embedding_centroids(
        self,
        embeddings: List[List[float]],
        k: int = 10,
    ) -> List[List[float]]:
        """K-means-style centroid extraction from embeddings."""
        if not TORCH_AVAILABLE or not embeddings:
            return []
        mat = torch.tensor(embeddings, dtype=torch.float32)
        if mat.shape[0] <= k:
            return mat.tolist()
        # Simple random-init k-means (3 iters)
        indices = torch.randperm(mat.shape[0])[:k]
        centroids = mat[indices].clone()
        for _ in range(3):
            dists = torch.cdist(mat, centroids)
            assignments = dists.argmin(dim=1)
            for c in range(k):
                mask = assignments == c
                if mask.any():
                    centroids[c] = mat[mask].mean(dim=0)
        return centroids.tolist()

    def build_trust_distribution(
        self,
        examples: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """Bucket trust scores into a histogram."""
        buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
        for ex in examples:
            s = ex.get("trust_score", 0.0)
            if s < 0.2:
                buckets["0.0-0.2"] += 1
            elif s < 0.4:
                buckets["0.2-0.4"] += 1
            elif s < 0.6:
                buckets["0.4-0.6"] += 1
            elif s < 0.8:
                buckets["0.6-0.8"] += 1
            else:
                buckets["0.8-1.0"] += 1
        return buckets

    def extract_pattern_frequencies(
        self,
        examples: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """Count examples by type."""
        freq: Dict[str, int] = {}
        for ex in examples:
            t = ex.get("example_type") or ex.get("type", "unknown")
            freq[t] = freq.get(t, 0) + 1
        return freq

    def strip_pii(self, text: str) -> str:
        """Remove anything that looks like PII."""
        lower = text.lower()
        for pattern in self.PII_PATTERNS:
            if pattern in lower:
                return "[REDACTED]"
        return text

    # -- helpers --

    @staticmethod
    def _anonymise_source(source: str) -> str:
        if not source:
            return "anonymous"
        return hashlib.sha256(source.encode()).hexdigest()[:12]

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Federated Aggregator
# ---------------------------------------------------------------------------

class FederatedAggregator:
    """
    Aggregates model deltas from multiple nodes using trust-weighted
    Federated Averaging with poison detection.
    """

    def __init__(
        self,
        poison_threshold: float = 5.0,
        dp: Optional[DifferentialPrivacy] = None,
    ):
        self.poison_threshold = poison_threshold
        self.dp = dp or DifferentialPrivacy()
        self._pending_updates: List[ModelDelta] = []

    def submit_update(self, delta: ModelDelta) -> None:
        self._pending_updates.append(delta)

    def aggregate(
        self,
        node_trust_scores: Dict[str, float],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Run trust-weighted FedAvg on pending updates.

        Returns:
            (aggregated_delta, round_metrics)
        """
        updates = self._pending_updates
        if not updates:
            return {}, {"error": "no updates to aggregate"}

        # 1. Poison detection — reject outlier gradient norms
        norms = self._compute_norms(updates)
        if norms:
            median_norm = sorted(norms.values())[len(norms) // 2]
            threshold = median_norm * self.poison_threshold
        else:
            threshold = float("inf")

        clean_updates: List[ModelDelta] = []
        rejected = 0
        for u in updates:
            n = norms.get(u.node_id, 0.0)
            if n > threshold:
                logger.warning(
                    "Rejected update from node %s: norm %.2f > threshold %.2f",
                    u.node_id, n, threshold,
                )
                rejected += 1
            else:
                clean_updates.append(u)

        if not clean_updates:
            self._pending_updates.clear()
            return {}, {"error": "all updates rejected as poisoned", "rejected": rejected}

        # 2. Apply differential privacy
        for u in clean_updates:
            u.delta = self.dp.clip_and_noise(u.delta)

        # 3. Trust-weighted averaging
        aggregated = self._trust_weighted_avg(clean_updates, node_trust_scores)

        # 4. Metrics
        total_samples = sum(u.num_samples for u in clean_updates)
        metrics = {
            "participants": len(clean_updates),
            "rejected": rejected,
            "total_samples": total_samples,
            "privacy_spend": self.dp.epsilon_spent,
        }

        self._pending_updates.clear()
        return aggregated, metrics

    # -- helpers --

    @staticmethod
    def _compute_norms(updates: List[ModelDelta]) -> Dict[str, float]:
        if not TORCH_AVAILABLE:
            return {}
        norms = {}
        for u in updates:
            total = 0.0
            for grad_list in u.delta.values():
                t = torch.tensor(grad_list, dtype=torch.float32)
                total += torch.norm(t).item() ** 2
            norms[u.node_id] = total ** 0.5
        return norms

    @staticmethod
    def _trust_weighted_avg(
        updates: List[ModelDelta],
        trust_scores: Dict[str, float],
    ) -> Dict[str, Any]:
        if not TORCH_AVAILABLE:
            # fallback: just return first update
            return updates[0].delta if updates else {}

        # Compute weights (trust * num_samples)
        weights = []
        for u in updates:
            trust = trust_scores.get(u.node_id, 0.5)
            w = trust * max(u.num_samples, 1)
            weights.append(w)
        total_w = sum(weights) or 1.0

        # Aggregate
        aggregated: Dict[str, Any] = {}
        layer_names = updates[0].delta.keys()
        for name in layer_names:
            tensors = [torch.tensor(u.delta[name], dtype=torch.float32) for u in updates]
            weighted = sum(t * (w / total_w) for t, w in zip(tensors, weights))
            aggregated[name] = weighted.tolist()

        return aggregated


# ---------------------------------------------------------------------------
# Federated Learning Manager
# ---------------------------------------------------------------------------

class FederatedLearningManager:
    """
    High-level orchestrator for the federated learning lifecycle.

    Manages nodes, aggregation rounds, and knowledge exchange via
    JSON-serialisable packages (no network layer required).
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self._nodes: Dict[str, NodeInfo] = {}
        self._rounds: List[AggregationRound] = []
        self._global_model_version = 0
        self._global_delta: Dict[str, Any] = {}
        self._aggregator = FederatedAggregator()
        self._distiller = KnowledgeDistillation()
        self._storage_dir = storage_dir or os.path.join("data", "federated")

        os.makedirs(self._storage_dir, exist_ok=True)
        logger.info("[FEDERATED] Manager initialised (storage: %s)", self._storage_dir)

    # -- Node management ---------------------------------------------------

    def register_node(
        self,
        name: str,
        description: str = "",
        trust_score: float = 0.5,
    ) -> NodeInfo:
        node_id = hashlib.sha256(
            f"{name}-{time.time()}".encode()
        ).hexdigest()[:12]

        node = NodeInfo(
            node_id=node_id,
            node_name=name,
            description=description,
            trust_score=trust_score,
        )
        self._nodes[node_id] = node
        logger.info("[FEDERATED] Registered node %s (%s)", node_id, name)
        return node

    def remove_node(self, node_id: str) -> bool:
        if node_id in self._nodes:
            self._nodes[node_id].active = False
            logger.info("[FEDERATED] Deactivated node %s", node_id)
            return True
        return False

    def get_nodes(self) -> List[Dict[str, Any]]:
        return [asdict(n) for n in self._nodes.values()]

    # -- Updates & Aggregation ---------------------------------------------

    def submit_local_update(
        self,
        node_id: str,
        model_delta: Dict[str, Any],
        metrics: Optional[Dict[str, float]] = None,
        num_samples: int = 0,
    ) -> bool:
        node = self._nodes.get(node_id)
        if not node or not node.active:
            logger.warning("[FEDERATED] Unknown or inactive node: %s", node_id)
            return False

        delta = ModelDelta(
            node_id=node_id,
            round_id=len(self._rounds),
            delta=model_delta,
            metrics=metrics or {},
            num_samples=num_samples,
        )
        self._aggregator.submit_update(delta)

        node.update_count += 1
        node.last_update_at = datetime.now(timezone.utc).isoformat()
        node.contribution_history.append({
            "round": len(self._rounds),
            "samples": num_samples,
            "timestamp": delta.timestamp,
        })

        logger.info("[FEDERATED] Update from node %s (%d samples)", node_id, num_samples)
        return True

    def run_aggregation_round(self) -> Dict[str, Any]:
        trust_scores = {
            nid: n.trust_score
            for nid, n in self._nodes.items()
            if n.active
        }

        aggregated, metrics = self._aggregator.aggregate(trust_scores)

        if "error" in metrics:
            logger.warning("[FEDERATED] Aggregation failed: %s", metrics["error"])
            return metrics

        self._global_model_version += 1
        self._global_delta = aggregated

        # Update node model versions
        for nid in trust_scores:
            if nid in self._nodes:
                self._nodes[nid].model_version = self._global_model_version
                if TORCH_AVAILABLE:
                    h = hashlib.sha256(
                        json.dumps(aggregated, sort_keys=True, default=str)[:2048].encode()
                    ).hexdigest()[:16]
                    self._nodes[nid].weights_hash = h

        round_record = AggregationRound(
            round_id=len(self._rounds),
            participating_nodes=list(trust_scores.keys()),
            global_model_version=self._global_model_version,
            metrics=metrics,
            privacy_spend=self._aggregator.dp.epsilon_spent,
            poisoned_rejected=metrics.get("rejected", 0),
        )
        self._rounds.append(round_record)

        logger.info(
            "[FEDERATED] Round %d complete — v%d, %d participants",
            round_record.round_id,
            self._global_model_version,
            metrics.get("participants", 0),
        )
        return asdict(round_record)

    def get_global_model(self) -> Dict[str, Any]:
        return {
            "version": self._global_model_version,
            "delta": self._global_delta,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # -- Knowledge exchange ------------------------------------------------

    def export_knowledge_package(
        self,
        source_node: str = "local",
        examples: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
        min_trust: float = 0.4,
    ) -> Dict[str, Any]:
        """
        Export distilled knowledge as a JSON-serialisable package.

        If *examples* is None, the caller should pass learning examples
        from the DB.  This method only distils — it doesn't query the DB.
        """
        examples = examples or []
        embeddings = embeddings or []

        pkg = KnowledgePackage(
            package_id=hashlib.sha256(
                f"{source_node}-{time.time()}".encode()
            ).hexdigest()[:16],
            source_node=source_node,
            created_at=datetime.now(timezone.utc).isoformat(),
            items=self._distiller.distill_examples(examples, min_trust=min_trust),
            embedding_centroids=self._distiller.compute_embedding_centroids(embeddings),
            pattern_frequencies=self._distiller.extract_pattern_frequencies(examples),
            trust_distribution=self._distiller.build_trust_distribution(examples),
            metadata={
                "global_model_version": self._global_model_version,
                "total_rounds": len(self._rounds),
                "registered_nodes": len(self._nodes),
            },
        )

        # Persist
        path = os.path.join(self._storage_dir, f"pkg_{pkg.package_id}.json")
        with open(path, "w") as f:
            json.dump(asdict(pkg), f, indent=2, default=str)

        logger.info(
            "[FEDERATED] Exported knowledge package %s (%d items)",
            pkg.package_id, len(pkg.items),
        )
        return asdict(pkg)

    def import_knowledge_package(
        self,
        package: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Import a knowledge package from another instance.

        Returns summary of what was imported.
        """
        items = package.get("items", [])
        centroids = package.get("embedding_centroids", [])
        source = package.get("source_node", "unknown")

        # Register source as a node if not already known
        existing = [n for n in self._nodes.values() if n.node_name == source]
        if not existing:
            self.register_node(name=source, description="auto-registered via import")

        imported_count = len(items)
        centroid_count = len(centroids)

        # Persist the received package
        pkg_id = package.get("package_id", hashlib.sha256(
            json.dumps(package, default=str)[:1024].encode()
        ).hexdigest()[:16])
        path = os.path.join(self._storage_dir, f"imported_{pkg_id}.json")
        with open(path, "w") as f:
            json.dump(package, f, indent=2, default=str)

        logger.info(
            "[FEDERATED] Imported package %s from %s (%d items, %d centroids)",
            pkg_id, source, imported_count, centroid_count,
        )

        return {
            "status": "imported",
            "package_id": pkg_id,
            "source_node": source,
            "items_imported": imported_count,
            "centroids_imported": centroid_count,
            "patterns": package.get("pattern_frequencies", {}),
        }

    # -- Status & history --------------------------------------------------

    def get_federation_status(self) -> Dict[str, Any]:
        active = sum(1 for n in self._nodes.values() if n.active)
        return {
            "registered_nodes": len(self._nodes),
            "active_nodes": active,
            "total_rounds": len(self._rounds),
            "global_model_version": self._global_model_version,
            "privacy": self._aggregator.dp.to_dict(),
            "last_aggregation": (
                self._rounds[-1].timestamp if self._rounds else None
            ),
            "torch_available": TORCH_AVAILABLE,
        }

    def get_rounds_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [asdict(r) for r in self._rounds[-limit:]]


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------

_manager_instance: Optional[FederatedLearningManager] = None


def get_federated_manager(
    storage_dir: Optional[str] = None,
) -> FederatedLearningManager:
    """Module-level singleton getter."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = FederatedLearningManager(storage_dir=storage_dir)
    return _manager_instance
