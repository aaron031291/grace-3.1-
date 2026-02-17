"""
Confidence Cascading Engine - Data Provenance Chain Trust Propagation

When a source is found unreliable, everything derived from that source
gets its trust downgraded automatically. Like pulling a thread -- one
verification failure cascades through the entire dependency chain.

Uses Genesis Keys' parent_key_id to walk the provenance chain.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class CascadeDirection(str, Enum):
    """Direction of trust cascade."""
    DOWNSTREAM = "downstream"  # Source -> all derived items
    UPSTREAM = "upstream"  # Derived item -> its sources


class CascadeReason(str, Enum):
    """Reason for the cascade."""
    SOURCE_UNRELIABLE = "source_unreliable"
    VERIFICATION_FAILED = "verification_failed"
    CONTRADICTION_DETECTED = "contradiction_detected"
    MANUAL_DOWNGRADE = "manual_downgrade"
    STALE_DATA = "stale_data"
    UPSTREAM_DEGRADED = "upstream_degraded"


@dataclass
class ProvenanceNode:
    """A node in the provenance graph."""
    node_id: str
    source_id: Optional[str] = None
    trust_score: float = 0.5
    original_trust_score: float = 0.5
    data_type: str = "unknown"
    domain: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_verified: Optional[datetime] = None
    children: List[str] = field(default_factory=list)
    parents: List[str] = field(default_factory=list)
    cascade_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CascadeResult:
    """Result of a trust cascade operation."""
    cascade_id: str
    trigger_node_id: str
    reason: CascadeReason
    direction: CascadeDirection
    nodes_affected: int
    trust_changes: Dict[str, Tuple[float, float]]  # node_id -> (old, new)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    depth_reached: int = 0


class ConfidenceCascadeEngine:
    """
    Manages trust propagation through data provenance chains.

    When Source A is found unreliable, everything learned FROM Source A
    has its trust downgraded automatically. The Genesis Keys track
    provenance via parent_key_id, so the chain exists.

    Features:
    - Build and maintain provenance graph
    - Cascade trust downgrades downstream
    - Cascade trust upgrades when sources are re-verified
    - Track cascade history for audit
    - Dampen cascades to prevent runaway degradation
    """

    # Damping factor: how much trust loss propagates per hop
    DEFAULT_DAMPING = 0.7
    # Minimum trust floor (never cascade below this)
    TRUST_FLOOR = 0.05
    # Maximum cascade depth
    MAX_CASCADE_DEPTH = 10

    def __init__(
        self,
        damping_factor: float = DEFAULT_DAMPING,
        trust_floor: float = TRUST_FLOOR,
        max_depth: int = MAX_CASCADE_DEPTH,
    ):
        self.damping_factor = damping_factor
        self.trust_floor = trust_floor
        self.max_depth = max_depth
        self.nodes: Dict[str, ProvenanceNode] = {}
        self.cascade_log: List[CascadeResult] = []
        self._source_index: Dict[str, Set[str]] = defaultdict(set)
        logger.info("[CASCADE] Confidence Cascade Engine initialized")

    def register_node(
        self,
        node_id: str,
        trust_score: float = 0.5,
        source_id: Optional[str] = None,
        data_type: str = "unknown",
        domain: Optional[str] = None,
        parent_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProvenanceNode:
        """
        Register a data item in the provenance graph.

        Args:
            node_id: Unique identifier for this data item
            trust_score: Initial trust score
            source_id: Source identifier (e.g., URL, document ID)
            data_type: Type of data (document, chunk, fact, inference)
            domain: Knowledge domain
            parent_ids: IDs of parent nodes this was derived from
            metadata: Additional metadata

        Returns:
            ProvenanceNode
        """
        node = ProvenanceNode(
            node_id=node_id,
            source_id=source_id,
            trust_score=trust_score,
            original_trust_score=trust_score,
            data_type=data_type,
            domain=domain,
            metadata=metadata or {},
        )

        if parent_ids:
            node.parents = list(parent_ids)
            for pid in parent_ids:
                if pid in self.nodes:
                    self.nodes[pid].children.append(node_id)
                self._source_index[pid].add(node_id)

        if source_id:
            self._source_index[source_id].add(node_id)

        self.nodes[node_id] = node
        return node

    def add_derivation(self, parent_id: str, child_id: str) -> bool:
        """
        Record that child_id was derived from parent_id.

        Args:
            parent_id: The source node
            child_id: The derived node

        Returns:
            True if link was added successfully
        """
        if parent_id not in self.nodes or child_id not in self.nodes:
            return False

        if child_id not in self.nodes[parent_id].children:
            self.nodes[parent_id].children.append(child_id)
        if parent_id not in self.nodes[child_id].parents:
            self.nodes[child_id].parents.append(parent_id)

        self._source_index[parent_id].add(child_id)
        return True

    def cascade_trust_downgrade(
        self,
        node_id: str,
        new_trust: float,
        reason: CascadeReason = CascadeReason.SOURCE_UNRELIABLE,
    ) -> CascadeResult:
        """
        Cascade a trust downgrade through the provenance chain.

        When a node's trust drops, all downstream nodes get proportionally
        degraded with damping per hop.

        Args:
            node_id: The node whose trust has dropped
            new_trust: The new trust score for this node
            reason: Reason for the cascade

        Returns:
            CascadeResult with all affected nodes
        """
        if node_id not in self.nodes:
            return CascadeResult(
                cascade_id=f"cascade-{uuid.uuid4().hex[:12]}",
                trigger_node_id=node_id,
                reason=reason,
                direction=CascadeDirection.DOWNSTREAM,
                nodes_affected=0,
                trust_changes={},
            )

        node = self.nodes[node_id]
        old_trust = node.trust_score

        if new_trust >= old_trust:
            return CascadeResult(
                cascade_id=f"cascade-{uuid.uuid4().hex[:12]}",
                trigger_node_id=node_id,
                reason=reason,
                direction=CascadeDirection.DOWNSTREAM,
                nodes_affected=0,
                trust_changes={},
            )

        trust_drop = old_trust - new_trust
        trust_drop_ratio = trust_drop / max(old_trust, 0.01)

        # Apply to trigger node
        node.trust_score = new_trust
        trust_changes: Dict[str, Tuple[float, float]] = {
            node_id: (old_trust, new_trust)
        }

        # BFS cascade through children
        visited: Set[str] = {node_id}
        queue: List[Tuple[str, int, float]] = []

        for child_id in node.children:
            if child_id not in visited:
                queue.append((child_id, 1, trust_drop_ratio))

        max_depth_reached = 0

        while queue:
            current_id, depth, propagated_ratio = queue.pop(0)

            if depth > self.max_depth:
                continue
            if current_id in visited:
                continue
            if current_id not in self.nodes:
                continue

            visited.add(current_id)
            current_node = self.nodes[current_id]

            # Calculate damped trust drop
            damped_ratio = propagated_ratio * self.damping_factor
            child_old_trust = current_node.trust_score
            child_drop = child_old_trust * damped_ratio
            child_new_trust = max(
                child_old_trust - child_drop, self.trust_floor
            )

            if abs(child_old_trust - child_new_trust) > 0.001:
                current_node.trust_score = child_new_trust
                trust_changes[current_id] = (child_old_trust, child_new_trust)

                current_node.cascade_history.append({
                    "cascade_from": node_id,
                    "reason": reason.value,
                    "old_trust": child_old_trust,
                    "new_trust": child_new_trust,
                    "depth": depth,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                max_depth_reached = max(max_depth_reached, depth)

                # Continue cascade to children
                for grandchild_id in current_node.children:
                    if grandchild_id not in visited:
                        queue.append(
                            (grandchild_id, depth + 1, damped_ratio)
                        )

        result = CascadeResult(
            cascade_id=f"cascade-{uuid.uuid4().hex[:12]}",
            trigger_node_id=node_id,
            reason=reason,
            direction=CascadeDirection.DOWNSTREAM,
            nodes_affected=len(trust_changes),
            trust_changes=trust_changes,
            depth_reached=max_depth_reached,
        )

        self.cascade_log.append(result)
        logger.info(
            f"[CASCADE] Downgrade from {node_id}: "
            f"{len(trust_changes)} nodes affected, depth={max_depth_reached}"
        )

        return result

    def cascade_trust_upgrade(
        self,
        node_id: str,
        new_trust: float,
        reason: CascadeReason = CascadeReason.VERIFICATION_FAILED,
    ) -> CascadeResult:
        """
        Cascade a trust upgrade (re-verification success).

        When a previously degraded source is re-verified, downstream
        nodes can recover some trust.

        Args:
            node_id: The re-verified node
            new_trust: New (higher) trust score
            reason: Reason for upgrade

        Returns:
            CascadeResult
        """
        if node_id not in self.nodes:
            return CascadeResult(
                cascade_id=f"cascade-{uuid.uuid4().hex[:12]}",
                trigger_node_id=node_id,
                reason=reason,
                direction=CascadeDirection.DOWNSTREAM,
                nodes_affected=0,
                trust_changes={},
            )

        node = self.nodes[node_id]
        old_trust = node.trust_score

        if new_trust <= old_trust:
            return CascadeResult(
                cascade_id=f"cascade-{uuid.uuid4().hex[:12]}",
                trigger_node_id=node_id,
                reason=reason,
                direction=CascadeDirection.DOWNSTREAM,
                nodes_affected=0,
                trust_changes={},
            )

        trust_gain_ratio = (new_trust - old_trust) / max(1.0 - old_trust, 0.01)

        node.trust_score = new_trust
        trust_changes: Dict[str, Tuple[float, float]] = {
            node_id: (old_trust, new_trust)
        }

        visited: Set[str] = {node_id}
        queue: List[Tuple[str, int, float]] = []

        for child_id in node.children:
            if child_id not in visited:
                queue.append((child_id, 1, trust_gain_ratio))

        max_depth_reached = 0

        while queue:
            current_id, depth, propagated_ratio = queue.pop(0)

            if depth > self.max_depth:
                continue
            if current_id in visited:
                continue
            if current_id not in self.nodes:
                continue

            visited.add(current_id)
            current_node = self.nodes[current_id]

            damped_ratio = propagated_ratio * self.damping_factor
            child_old_trust = current_node.trust_score
            # Recover towards original trust
            recovery_room = current_node.original_trust_score - child_old_trust
            child_gain = recovery_room * damped_ratio
            child_new_trust = min(
                child_old_trust + child_gain,
                current_node.original_trust_score,
            )

            if abs(child_new_trust - child_old_trust) > 0.001:
                current_node.trust_score = child_new_trust
                trust_changes[current_id] = (child_old_trust, child_new_trust)
                max_depth_reached = max(max_depth_reached, depth)

                for grandchild_id in current_node.children:
                    if grandchild_id not in visited:
                        queue.append(
                            (grandchild_id, depth + 1, damped_ratio)
                        )

        result = CascadeResult(
            cascade_id=f"cascade-{uuid.uuid4().hex[:12]}",
            trigger_node_id=node_id,
            reason=reason,
            direction=CascadeDirection.DOWNSTREAM,
            nodes_affected=len(trust_changes),
            trust_changes=trust_changes,
            depth_reached=max_depth_reached,
        )

        self.cascade_log.append(result)
        logger.info(
            f"[CASCADE] Upgrade from {node_id}: "
            f"{len(trust_changes)} nodes affected, depth={max_depth_reached}"
        )

        return result

    def get_provenance_chain(self, node_id: str) -> List[str]:
        """
        Walk the provenance chain upstream to find all ancestors.

        Args:
            node_id: Starting node

        Returns:
            List of ancestor node IDs (closest first)
        """
        chain: List[str] = []
        visited: Set[str] = set()
        queue = [node_id]

        while queue:
            current = queue.pop(0)
            if current in visited or current not in self.nodes:
                continue
            visited.add(current)
            if current != node_id:
                chain.append(current)
            for parent_id in self.nodes[current].parents:
                queue.append(parent_id)

        return chain

    def get_downstream_nodes(self, node_id: str) -> List[str]:
        """
        Get all downstream (derived) nodes from a given node.

        Args:
            node_id: Starting node

        Returns:
            List of descendant node IDs
        """
        descendants: List[str] = []
        visited: Set[str] = set()
        queue = [node_id]

        while queue:
            current = queue.pop(0)
            if current in visited or current not in self.nodes:
                continue
            visited.add(current)
            if current != node_id:
                descendants.append(current)
            for child_id in self.nodes[current].children:
                queue.append(child_id)

        return descendants

    def get_node_trust(self, node_id: str) -> float:
        """Get current trust score for a node."""
        if node_id in self.nodes:
            return self.nodes[node_id].trust_score
        return 0.5

    def get_cascade_history(
        self, limit: int = 50
    ) -> List[CascadeResult]:
        """Get recent cascade history."""
        return self.cascade_log[-limit:]

    def get_affected_by_source(self, source_id: str) -> List[str]:
        """Get all nodes affected by a particular source."""
        return list(self._source_index.get(source_id, set()))

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        trust_scores = [n.trust_score for n in self.nodes.values()]
        return {
            "total_nodes": len(self.nodes),
            "total_cascades": len(self.cascade_log),
            "average_trust": (
                sum(trust_scores) / len(trust_scores) if trust_scores else 0.5
            ),
            "min_trust": min(trust_scores) if trust_scores else 0.5,
            "max_trust": max(trust_scores) if trust_scores else 0.5,
            "damping_factor": self.damping_factor,
            "max_depth": self.max_depth,
        }
