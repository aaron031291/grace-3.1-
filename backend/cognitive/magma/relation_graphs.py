"""
Magma Memory - Relation Graphs

Four interconnected graph types for rich memory relationships:
1. Semantic Graph - Meaning relationships between concepts
2. Temporal Graph - Time-based relationships and sequences
3. Causal Graph - Cause-effect relationships
4. Entity Graph - Entity relationships and co-occurrences

These graphs work together with the existing Memory Mesh to provide
graph-based retrieval and relationship traversal.

Classes:
- `RelationType`
- `GraphNode`
- `GraphEdge`
- `BaseRelationGraph`
- `SemanticGraph`
- `TemporalGraph`
- `CausalGraph`
- `EntityGraph`
- `MagmaRelationGraphs`

Key Methods:
- `add_node()`
- `add_edge()`
- `get_node()`
- `get_edge()`
- `get_neighbors()`
- `find_path()`
- `get_subgraph()`
- `calculate_node_importance()`
- `get_stats()`
- `add_concept()`
- `find_related_concepts()`
- `add_event()`
- `get_events_in_range()`
- `get_event_sequence()`
- `add_causal_link()`
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
import uuid
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class RelationType(Enum):
    """Types of relationships in the graphs."""
    # Semantic relations
    SEMANTIC_SIMILAR = "semantic_similar"
    SEMANTIC_RELATED = "semantic_related"
    SEMANTIC_PARENT = "semantic_parent"
    SEMANTIC_CHILD = "semantic_child"
    SEMANTIC_SYNONYM = "semantic_synonym"
    SEMANTIC_ANTONYM = "semantic_antonym"

    # Temporal relations
    TEMPORAL_BEFORE = "temporal_before"
    TEMPORAL_AFTER = "temporal_after"
    TEMPORAL_CONCURRENT = "temporal_concurrent"
    TEMPORAL_SEQUENCE = "temporal_sequence"
    TEMPORAL_CAUSED_BY = "temporal_caused_by"

    # Causal relations
    CAUSAL_CAUSES = "causal_causes"
    CAUSAL_CAUSED_BY = "causal_caused_by"
    CAUSAL_ENABLES = "causal_enables"
    CAUSAL_PREVENTS = "causal_prevents"
    CAUSAL_CORRELATES = "causal_correlates"

    # Entity relations
    ENTITY_INSTANCE_OF = "entity_instance_of"
    ENTITY_PART_OF = "entity_part_of"
    ENTITY_RELATED_TO = "entity_related_to"
    ENTITY_CO_OCCURS = "entity_co_occurs"
    ENTITY_REFERENCES = "entity_references"


@dataclass
class GraphNode:
    """A node in a relation graph."""
    id: str
    node_type: str  # concept, event, entity, memory
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    genesis_key_id: Optional[str] = None
    trust_score: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, GraphNode):
            return self.id == other.id
        return False


@dataclass
class GraphEdge:
    """An edge connecting two nodes in a relation graph."""
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    genesis_key_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __hash__(self):
        return hash(self.id)


class BaseRelationGraph:
    """
    Base class for relation graphs.

    Provides common graph operations:
    - Add/remove nodes and edges
    - Traverse relationships
    - Find paths between nodes
    - Calculate graph metrics
    """

    def __init__(self, graph_type: str):
        self.graph_type = graph_type
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)  # node_id -> set of edge_ids
        self.reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)  # target_id -> set of edge_ids

        logger.info(f"[MAGMA-{graph_type.upper()}] Initialized")

    def add_node(self, node: GraphNode) -> str:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        logger.debug(f"[MAGMA-{self.graph_type}] Added node: {node.id}")
        return node.id

    def add_edge(self, edge: GraphEdge) -> str:
        """Add an edge to the graph."""
        if edge.source_id not in self.nodes:
            raise ValueError(f"Source node {edge.source_id} not found")
        if edge.target_id not in self.nodes:
            raise ValueError(f"Target node {edge.target_id} not found")

        self.edges[edge.id] = edge
        self.adjacency[edge.source_id].add(edge.id)
        self.reverse_adjacency[edge.target_id].add(edge.id)

        logger.debug(f"[MAGMA-{self.graph_type}] Added edge: {edge.source_id} -> {edge.target_id}")
        return edge.id

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        """Get an edge by ID."""
        return self.edges.get(edge_id)

    def get_neighbors(
        self,
        node_id: str,
        relation_types: Optional[List[RelationType]] = None,
        direction: str = "outgoing"  # outgoing, incoming, both
    ) -> List[Tuple[GraphNode, GraphEdge]]:
        """
        Get neighboring nodes with their connecting edges.

        Args:
            node_id: Source node ID
            relation_types: Filter by relation types (None = all)
            direction: outgoing, incoming, or both

        Returns:
            List of (neighbor_node, connecting_edge) tuples
        """
        neighbors = []

        if direction in ("outgoing", "both"):
            for edge_id in self.adjacency.get(node_id, set()):
                edge = self.edges[edge_id]
                if relation_types is None or edge.relation_type in relation_types:
                    neighbor = self.nodes.get(edge.target_id)
                    if neighbor:
                        neighbors.append((neighbor, edge))

        if direction in ("incoming", "both"):
            for edge_id in self.reverse_adjacency.get(node_id, set()):
                edge = self.edges[edge_id]
                if relation_types is None or edge.relation_type in relation_types:
                    neighbor = self.nodes.get(edge.source_id)
                    if neighbor:
                        neighbors.append((neighbor, edge))

        return neighbors

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
        relation_types: Optional[List[RelationType]] = None
    ) -> Optional[List[Tuple[GraphNode, GraphEdge]]]:
        """
        Find shortest path between two nodes using BFS.

        Returns:
            List of (node, edge) tuples representing the path, or None if no path
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            return None

        if source_id == target_id:
            return [(self.nodes[source_id], None)]

        # BFS
        visited = {source_id}
        queue = [(source_id, [])]

        while queue:
            current_id, path = queue.pop(0)

            if len(path) >= max_depth:
                continue

            for neighbor, edge in self.get_neighbors(current_id, relation_types, "both"):
                if neighbor.id == target_id:
                    return path + [(self.nodes[current_id], edge), (neighbor, None)]

                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    queue.append((neighbor.id, path + [(self.nodes[current_id], edge)]))

        return None

    def get_subgraph(
        self,
        center_node_id: str,
        depth: int = 2,
        relation_types: Optional[List[RelationType]] = None
    ) -> Tuple[Dict[str, GraphNode], Dict[str, GraphEdge]]:
        """
        Extract a subgraph centered on a node.

        Returns:
            Tuple of (nodes_dict, edges_dict) for the subgraph
        """
        subgraph_nodes = {}
        subgraph_edges = {}

        to_visit = [(center_node_id, 0)]
        visited = set()

        while to_visit:
            node_id, current_depth = to_visit.pop(0)

            if node_id in visited or current_depth > depth:
                continue

            visited.add(node_id)
            node = self.nodes.get(node_id)
            if node:
                subgraph_nodes[node_id] = node

            if current_depth < depth:
                for neighbor, edge in self.get_neighbors(node_id, relation_types, "both"):
                    if edge:
                        subgraph_edges[edge.id] = edge
                    to_visit.append((neighbor.id, current_depth + 1))

        return subgraph_nodes, subgraph_edges

    def calculate_node_importance(self, node_id: str) -> float:
        """
        Calculate importance score based on connectivity and trust.

        Combines:
        - Degree centrality (number of connections)
        - Trust score
        - Edge weights
        """
        node = self.nodes.get(node_id)
        if not node:
            return 0.0

        # Degree centrality
        outgoing = len(self.adjacency.get(node_id, set()))
        incoming = len(self.reverse_adjacency.get(node_id, set()))
        total_nodes = max(len(self.nodes), 1)
        degree_centrality = (outgoing + incoming) / (2 * total_nodes)

        # Average edge weight
        all_edges = list(self.adjacency.get(node_id, set())) + list(self.reverse_adjacency.get(node_id, set()))
        avg_weight = sum(self.edges[e].weight for e in all_edges) / max(len(all_edges), 1)

        # Combined score
        importance = (0.4 * degree_centrality + 0.4 * node.trust_score + 0.2 * avg_weight)

        return importance

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "graph_type": self.graph_type,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "avg_degree": sum(len(adj) for adj in self.adjacency.values()) / max(len(self.nodes), 1),
            "relation_type_counts": self._count_relation_types()
        }

    def _count_relation_types(self) -> Dict[str, int]:
        """Count edges by relation type."""
        counts = defaultdict(int)
        for edge in self.edges.values():
            counts[edge.relation_type.value] += 1
        return dict(counts)


class SemanticGraph(BaseRelationGraph):
    """
    Semantic Graph - Meaning relationships between concepts.

    Captures:
    - Similarity (cosine similarity > threshold)
    - Related concepts (co-occurrence, context)
    - Hierarchical relationships (parent/child)
    - Synonyms/Antonyms
    """

    def __init__(self):
        super().__init__("semantic")
        self.similarity_threshold = 0.7

    def add_concept(
        self,
        content: str,
        embedding: List[float],
        genesis_key_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add a concept node with automatic similarity linking."""
        node_id = f"sem-{uuid.uuid4().hex[:12]}"
        node = GraphNode(
            id=node_id,
            node_type="concept",
            content=content,
            embedding=embedding,
            genesis_key_id=genesis_key_id,
            metadata=metadata or {}
        )
        self.add_node(node)

        # Auto-link to similar concepts
        self._link_similar_concepts(node)

        return node_id

    def _link_similar_concepts(self, new_node: GraphNode):
        """Link new node to similar existing concepts."""
        if not new_node.embedding:
            return

        for existing_id, existing_node in self.nodes.items():
            if existing_id == new_node.id or not existing_node.embedding:
                continue

            similarity = self._cosine_similarity(new_node.embedding, existing_node.embedding)

            if similarity >= self.similarity_threshold:
                edge = GraphEdge(
                    id=f"sem-edge-{uuid.uuid4().hex[:8]}",
                    source_id=new_node.id,
                    target_id=existing_id,
                    relation_type=RelationType.SEMANTIC_SIMILAR,
                    weight=similarity,
                    confidence=similarity
                )
                self.add_edge(edge)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def find_related_concepts(
        self,
        concept_id: str,
        max_results: int = 10,
        min_similarity: float = 0.5
    ) -> List[Tuple[GraphNode, float]]:
        """Find concepts related to a given concept."""
        neighbors = self.get_neighbors(
            concept_id,
            relation_types=[RelationType.SEMANTIC_SIMILAR, RelationType.SEMANTIC_RELATED],
            direction="both"
        )

        # Sort by edge weight (similarity)
        results = [(node, edge.weight) for node, edge in neighbors if edge.weight >= min_similarity]
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:max_results]


class TemporalGraph(BaseRelationGraph):
    """
    Temporal Graph - Time-based relationships and sequences.

    Captures:
    - Before/After relationships
    - Concurrent events
    - Sequences of events
    - Time-based causation
    """

    def __init__(self):
        super().__init__("temporal")

    def add_event(
        self,
        content: str,
        timestamp: datetime,
        genesis_key_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add a temporal event node."""
        node_id = f"temp-{uuid.uuid4().hex[:12]}"
        node = GraphNode(
            id=node_id,
            node_type="event",
            content=content,
            genesis_key_id=genesis_key_id,
            metadata={**(metadata or {}), "timestamp": timestamp.isoformat()},
            created_at=timestamp
        )
        self.add_node(node)

        # Auto-link temporal relationships
        self._link_temporal_relationships(node, timestamp)

        return node_id

    def _link_temporal_relationships(self, new_node: GraphNode, timestamp: datetime):
        """Link new event to existing events based on time."""
        for existing_id, existing_node in self.nodes.items():
            if existing_id == new_node.id:
                continue

            existing_time_str = existing_node.metadata.get("timestamp")
            if not existing_time_str:
                continue

            existing_time = datetime.fromisoformat(existing_time_str)
            time_diff = (timestamp - existing_time).total_seconds()

            # Determine temporal relationship
            if abs(time_diff) < 60:  # Within 1 minute = concurrent
                relation = RelationType.TEMPORAL_CONCURRENT
                weight = 1.0
            elif time_diff > 0:  # New event is after existing
                relation = RelationType.TEMPORAL_AFTER
                weight = max(0.1, 1.0 - abs(time_diff) / 86400)  # Decay over 24 hours
            else:  # New event is before existing
                relation = RelationType.TEMPORAL_BEFORE
                weight = max(0.1, 1.0 - abs(time_diff) / 86400)

            # Only link if within reasonable time window (24 hours)
            if abs(time_diff) < 86400:
                edge = GraphEdge(
                    id=f"temp-edge-{uuid.uuid4().hex[:8]}",
                    source_id=new_node.id,
                    target_id=existing_id,
                    relation_type=relation,
                    weight=weight,
                    metadata={"time_diff_seconds": time_diff}
                )
                self.add_edge(edge)

    def get_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[GraphNode]:
        """Get all events within a time range."""
        events = []
        for node in self.nodes.values():
            timestamp_str = node.metadata.get("timestamp")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str)
                if start_time <= timestamp <= end_time:
                    events.append(node)

        events.sort(key=lambda n: n.metadata.get("timestamp", ""))
        return events

    def get_event_sequence(
        self,
        start_node_id: str,
        max_length: int = 10
    ) -> List[GraphNode]:
        """Get sequence of events following a start event."""
        sequence = []
        current_id = start_node_id
        visited = set()

        while len(sequence) < max_length and current_id not in visited:
            visited.add(current_id)
            node = self.nodes.get(current_id)
            if node:
                sequence.append(node)

            # Find next event in sequence
            neighbors = self.get_neighbors(
                current_id,
                relation_types=[RelationType.TEMPORAL_AFTER, RelationType.TEMPORAL_SEQUENCE],
                direction="outgoing"
            )

            if not neighbors:
                break

            # Take the most strongly connected next event
            neighbors.sort(key=lambda x: x[1].weight, reverse=True)
            current_id = neighbors[0][0].id

        return sequence


class CausalGraph(BaseRelationGraph):
    """
    Causal Graph - Cause-effect relationships.

    Captures:
    - Direct causation (A causes B)
    - Enabling conditions (A enables B)
    - Preventing conditions (A prevents B)
    - Correlations (A correlates with B)
    """

    def __init__(self):
        super().__init__("causal")

    def add_causal_link(
        self,
        cause_id: str,
        effect_id: str,
        relation: RelationType,
        confidence: float = 0.5,
        evidence: Optional[List[str]] = None,
        genesis_key_id: Optional[str] = None
    ) -> str:
        """Add a causal relationship between nodes."""
        if relation not in [
            RelationType.CAUSAL_CAUSES,
            RelationType.CAUSAL_CAUSED_BY,
            RelationType.CAUSAL_ENABLES,
            RelationType.CAUSAL_PREVENTS,
            RelationType.CAUSAL_CORRELATES
        ]:
            raise ValueError(f"Invalid causal relation type: {relation}")

        edge = GraphEdge(
            id=f"causal-edge-{uuid.uuid4().hex[:8]}",
            source_id=cause_id,
            target_id=effect_id,
            relation_type=relation,
            weight=confidence,
            confidence=confidence,
            genesis_key_id=genesis_key_id,
            metadata={"evidence": evidence or []}
        )

        return self.add_edge(edge)

    def get_causes(self, effect_id: str) -> List[Tuple[GraphNode, float]]:
        """Get all causes of an effect."""
        neighbors = self.get_neighbors(
            effect_id,
            relation_types=[RelationType.CAUSAL_CAUSES, RelationType.CAUSAL_CAUSED_BY],
            direction="incoming"
        )
        return [(node, edge.confidence) for node, edge in neighbors]

    def get_effects(self, cause_id: str) -> List[Tuple[GraphNode, float]]:
        """Get all effects of a cause."""
        neighbors = self.get_neighbors(
            cause_id,
            relation_types=[RelationType.CAUSAL_CAUSES],
            direction="outgoing"
        )
        return [(node, edge.confidence) for node, edge in neighbors]

    def trace_causal_chain(
        self,
        start_id: str,
        direction: str = "effects",  # effects or causes
        max_depth: int = 5
    ) -> List[List[GraphNode]]:
        """
        Trace causal chains from a starting node.

        Returns list of causal chains (each chain is a list of nodes).
        """
        chains = []

        def trace(current_id: str, current_chain: List[GraphNode], depth: int):
            if depth >= max_depth:
                if len(current_chain) > 1:
                    chains.append(current_chain.copy())
                return

            node = self.nodes.get(current_id)
            if not node:
                return

            current_chain.append(node)

            if direction == "effects":
                next_nodes = self.get_effects(current_id)
            else:
                next_nodes = self.get_causes(current_id)

            if not next_nodes:
                if len(current_chain) > 1:
                    chains.append(current_chain.copy())
            else:
                for next_node, confidence in next_nodes:
                    if next_node.id not in [n.id for n in current_chain]:
                        trace(next_node.id, current_chain, depth + 1)

            current_chain.pop()

        trace(start_id, [], 0)
        return chains


class EntityGraph(BaseRelationGraph):
    """
    Entity Graph - Entity relationships and co-occurrences.

    Captures:
    - Instance-of relationships
    - Part-of relationships
    - Entity co-occurrences
    - References between entities
    """

    def __init__(self):
        super().__init__("entity")

    def add_entity(
        self,
        name: str,
        entity_type: str,
        attributes: Optional[Dict] = None,
        genesis_key_id: Optional[str] = None
    ) -> str:
        """Add an entity node."""
        node_id = f"ent-{uuid.uuid4().hex[:12]}"
        node = GraphNode(
            id=node_id,
            node_type="entity",
            content=name,
            genesis_key_id=genesis_key_id,
            metadata={
                "entity_type": entity_type,
                "attributes": attributes or {}
            }
        )
        self.add_node(node)
        return node_id

    def link_entities(
        self,
        entity1_id: str,
        entity2_id: str,
        relation: RelationType,
        confidence: float = 0.5,
        context: Optional[str] = None
    ) -> str:
        """Link two entities with a relationship."""
        if relation not in [
            RelationType.ENTITY_INSTANCE_OF,
            RelationType.ENTITY_PART_OF,
            RelationType.ENTITY_RELATED_TO,
            RelationType.ENTITY_CO_OCCURS,
            RelationType.ENTITY_REFERENCES
        ]:
            raise ValueError(f"Invalid entity relation type: {relation}")

        edge = GraphEdge(
            id=f"ent-edge-{uuid.uuid4().hex[:8]}",
            source_id=entity1_id,
            target_id=entity2_id,
            relation_type=relation,
            weight=confidence,
            confidence=confidence,
            metadata={"context": context} if context else {}
        )

        return self.add_edge(edge)

    def record_co_occurrence(
        self,
        entity1_id: str,
        entity2_id: str,
        context: str
    ):
        """Record that two entities co-occurred in a context."""
        # Check if co-occurrence edge already exists
        existing_edge = None
        for edge_id in self.adjacency.get(entity1_id, set()):
            edge = self.edges[edge_id]
            if edge.target_id == entity2_id and edge.relation_type == RelationType.ENTITY_CO_OCCURS:
                existing_edge = edge
                break

        if existing_edge:
            # Increment co-occurrence count
            existing_edge.weight += 0.1
            contexts = existing_edge.metadata.get("contexts", [])
            contexts.append(context)
            existing_edge.metadata["contexts"] = contexts[-10:]  # Keep last 10
        else:
            # Create new co-occurrence
            self.link_entities(
                entity1_id,
                entity2_id,
                RelationType.ENTITY_CO_OCCURS,
                confidence=0.5,
                context=context
            )

    def get_entity_cluster(
        self,
        entity_id: str,
        min_co_occurrence: float = 0.3
    ) -> List[GraphNode]:
        """Get cluster of frequently co-occurring entities."""
        neighbors = self.get_neighbors(
            entity_id,
            relation_types=[RelationType.ENTITY_CO_OCCURS, RelationType.ENTITY_RELATED_TO],
            direction="both"
        )

        cluster = [node for node, edge in neighbors if edge.weight >= min_co_occurrence]
        cluster.sort(key=lambda n: self.calculate_node_importance(n.id), reverse=True)

        return cluster


class MagmaRelationGraphs:
    """
    Unified interface for all Magma relation graphs.

    Coordinates:
    - Semantic Graph
    - Temporal Graph
    - Causal Graph
    - Entity Graph

    Provides cross-graph queries and unified retrieval.
    """

    def __init__(self):
        self.semantic = SemanticGraph()
        self.temporal = TemporalGraph()
        self.causal = CausalGraph()
        self.entity = EntityGraph()

        logger.info("[MAGMA] Relation Graphs initialized")

    def get_all_graphs(self) -> Dict[str, BaseRelationGraph]:
        """Get all relation graphs."""
        return {
            "semantic": self.semantic,
            "temporal": self.temporal,
            "causal": self.causal,
            "entity": self.entity
        }

    def cross_graph_search(
        self,
        query_node_id: str,
        source_graph: str,
        target_graphs: Optional[List[str]] = None,
        max_depth: int = 2
    ) -> Dict[str, List[GraphNode]]:
        """
        Search across multiple graphs starting from a node.

        Uses genesis_key_id to link nodes across graphs.
        """
        if target_graphs is None:
            target_graphs = ["semantic", "temporal", "causal", "entity"]

        results = {}
        graphs = self.get_all_graphs()
        source = graphs.get(source_graph)

        if not source:
            return results

        node = source.get_node(query_node_id)
        if not node or not node.genesis_key_id:
            return results

        # Find related nodes in other graphs via genesis_key_id
        for graph_name in target_graphs:
            if graph_name == source_graph:
                continue

            graph = graphs.get(graph_name)
            if not graph:
                continue

            related = []
            for other_node in graph.nodes.values():
                if other_node.genesis_key_id == node.genesis_key_id:
                    # Same genesis key - direct link
                    related.append(other_node)
                    # Also get neighbors
                    neighbors = graph.get_neighbors(other_node.id, direction="both")
                    related.extend([n for n, e in neighbors])

            results[graph_name] = list(set(related))[:20]  # Dedupe and limit

        return results

    def get_unified_stats(self) -> Dict[str, Any]:
        """Get statistics for all graphs."""
        return {
            "semantic": self.semantic.get_stats(),
            "temporal": self.temporal.get_stats(),
            "causal": self.causal.get_stats(),
            "entity": self.entity.get_stats(),
            "total_nodes": sum(
                len(g.nodes) for g in self.get_all_graphs().values()
            ),
            "total_edges": sum(
                len(g.edges) for g in self.get_all_graphs().values()
            )
        }
