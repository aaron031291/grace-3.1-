"""
Magma Memory - Adaptive Topological Retrieval

Graph-based retrieval with adaptive traversal policies:
1. Starts from anchor nodes identified by Intent Router
2. Traverses relation graphs based on retrieval policy
3. Adapts traversal depth and breadth based on result quality
4. Combines graph traversal with vector similarity

Traversal Policies:
- BFS (Breadth-First): Explore neighbors at each level
- DFS (Depth-First): Deep exploration of single paths
- Best-First: Follow highest-weight edges
- Adaptive: Dynamically adjust based on results
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from enum import Enum
import logging
from collections import deque
import heapq

from cognitive.magma.relation_graphs import (
    MagmaRelationGraphs,
    GraphNode,
    GraphEdge,
    RelationType,
    BaseRelationGraph
)
from cognitive.magma.intent_router import QueryAnalysis, Anchor, AnchorType
from cognitive.magma.rrf_fusion import RetrievalResult

logger = logging.getLogger(__name__)


class TraversalPolicy(Enum):
    """Graph traversal policies."""
    BFS = "bfs"  # Breadth-first search
    DFS = "dfs"  # Depth-first search
    BEST_FIRST = "best_first"  # Greedy best-first
    BIDIRECTIONAL = "bidirectional"  # From multiple anchors
    ADAPTIVE = "adaptive"  # Dynamically adjust
    SEMANTIC_SPREAD = "semantic_spread"  # Spread through semantic links
    CAUSAL_CHAIN = "causal_chain"  # Follow causal paths
    TEMPORAL_WINDOW = "temporal_window"  # Time-bounded


@dataclass
class TraversalConfig:
    """Configuration for graph traversal."""
    max_depth: int = 3
    max_nodes: int = 100
    min_edge_weight: float = 0.1
    min_node_trust: float = 0.3
    beam_width: int = 10  # For best-first
    adaptive_threshold: float = 0.5  # Quality threshold for adaptation
    relation_types: Optional[List[RelationType]] = None  # Filter by relation types


@dataclass
class TraversalState:
    """State during traversal."""
    visited: Set[str] = field(default_factory=set)
    frontier: List[str] = field(default_factory=list)
    results: List[Tuple[GraphNode, float, List[GraphEdge]]] = field(default_factory=list)
    depth: int = 0
    total_explored: int = 0


@dataclass
class TraversalResult:
    """Result of a graph traversal."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    paths: List[List[Tuple[GraphNode, GraphEdge]]]
    scores: Dict[str, float]  # node_id -> relevance score
    metadata: Dict[str, Any] = field(default_factory=dict)


class GraphTraverser:
    """
    Base graph traversal implementation.

    Provides common traversal algorithms for relation graphs.
    """

    def __init__(self, graphs: MagmaRelationGraphs):
        """
        Initialize traverser.

        Args:
            graphs: MagmaRelationGraphs instance
        """
        self.graphs = graphs
        logger.info("[MAGMA-TRAVERSAL] GraphTraverser initialized")

    def bfs_traverse(
        self,
        start_node_id: str,
        graph: BaseRelationGraph,
        config: TraversalConfig
    ) -> TraversalResult:
        """
        Breadth-first traversal from a starting node.

        Args:
            start_node_id: Starting node ID
            graph: Graph to traverse
            config: Traversal configuration

        Returns:
            TraversalResult with discovered nodes
        """
        start_node = graph.get_node(start_node_id)
        if not start_node:
            return TraversalResult([], [], [], {})

        visited: Set[str] = {start_node_id}
        queue = deque([(start_node_id, 0, [])])  # (node_id, depth, path)
        results_nodes: List[GraphNode] = [start_node]
        results_edges: List[GraphEdge] = []
        all_paths: List[List[Tuple[GraphNode, GraphEdge]]] = []
        scores: Dict[str, float] = {start_node_id: 1.0}

        while queue and len(results_nodes) < config.max_nodes:
            current_id, depth, path = queue.popleft()

            if depth >= config.max_depth:
                continue

            neighbors = graph.get_neighbors(
                current_id,
                relation_types=config.relation_types,
                direction="both"
            )

            for neighbor, edge in neighbors:
                if neighbor.id in visited:
                    continue

                if edge.weight < config.min_edge_weight:
                    continue

                if neighbor.trust_score < config.min_node_trust:
                    continue

                visited.add(neighbor.id)
                results_nodes.append(neighbor)
                results_edges.append(edge)

                # Calculate score based on depth and edge weight
                score = (1.0 / (depth + 2)) * edge.weight * neighbor.trust_score
                scores[neighbor.id] = score

                new_path = path + [(neighbor, edge)]
                all_paths.append(new_path)

                queue.append((neighbor.id, depth + 1, new_path))

        return TraversalResult(
            nodes=results_nodes,
            edges=results_edges,
            paths=all_paths,
            scores=scores,
            metadata={"method": "bfs", "start": start_node_id, "depth_reached": config.max_depth}
        )

    def best_first_traverse(
        self,
        start_node_id: str,
        graph: BaseRelationGraph,
        config: TraversalConfig,
        score_fn: Optional[Callable[[GraphNode, GraphEdge], float]] = None
    ) -> TraversalResult:
        """
        Best-first traversal prioritizing highest-scoring paths.

        Args:
            start_node_id: Starting node ID
            graph: Graph to traverse
            config: Traversal configuration
            score_fn: Optional custom scoring function

        Returns:
            TraversalResult with discovered nodes
        """
        start_node = graph.get_node(start_node_id)
        if not start_node:
            return TraversalResult([], [], [], {})

        # Default scoring: edge weight * node trust
        if score_fn is None:
            score_fn = lambda n, e: e.weight * n.trust_score if e else n.trust_score

        visited: Set[str] = {start_node_id}
        # Priority queue: (-score, node_id, depth, path)
        heap = [(-1.0, start_node_id, 0, [])]
        results_nodes: List[GraphNode] = []
        results_edges: List[GraphEdge] = []
        all_paths: List[List[Tuple[GraphNode, GraphEdge]]] = []
        scores: Dict[str, float] = {}

        while heap and len(results_nodes) < config.max_nodes:
            neg_score, current_id, depth, path = heapq.heappop(heap)
            current_score = -neg_score

            current_node = graph.get_node(current_id)
            if current_node:
                results_nodes.append(current_node)
                scores[current_id] = current_score

                if path:
                    all_paths.append(path)
                    results_edges.extend([e for _, e in path if e])

            if depth >= config.max_depth:
                continue

            neighbors = graph.get_neighbors(
                current_id,
                relation_types=config.relation_types,
                direction="both"
            )

            # Sort by score and take beam_width best
            scored_neighbors = []
            for neighbor, edge in neighbors:
                if neighbor.id in visited:
                    continue
                if edge.weight < config.min_edge_weight:
                    continue

                neighbor_score = score_fn(neighbor, edge) * current_score
                scored_neighbors.append((neighbor_score, neighbor, edge))

            scored_neighbors.sort(key=lambda x: x[0], reverse=True)

            for neighbor_score, neighbor, edge in scored_neighbors[:config.beam_width]:
                visited.add(neighbor.id)
                new_path = path + [(neighbor, edge)]
                heapq.heappush(heap, (-neighbor_score, neighbor.id, depth + 1, new_path))

        return TraversalResult(
            nodes=results_nodes,
            edges=results_edges,
            paths=all_paths,
            scores=scores,
            metadata={"method": "best_first", "start": start_node_id}
        )

    def bidirectional_traverse(
        self,
        anchor_ids: List[str],
        graph: BaseRelationGraph,
        config: TraversalConfig
    ) -> TraversalResult:
        """
        Bidirectional traversal from multiple anchor nodes.

        Explores from all anchors simultaneously to find connecting paths.

        Args:
            anchor_ids: List of anchor node IDs
            graph: Graph to traverse
            config: Traversal configuration

        Returns:
            TraversalResult with discovered nodes and connecting paths
        """
        all_nodes: List[GraphNode] = []
        all_edges: List[GraphEdge] = []
        all_paths: List[List[Tuple[GraphNode, GraphEdge]]] = []
        all_scores: Dict[str, float] = {}

        # Track nodes discovered from each anchor
        anchor_discoveries: Dict[str, Set[str]] = {aid: {aid} for aid in anchor_ids}

        # BFS from each anchor
        for anchor_id in anchor_ids:
            result = self.bfs_traverse(anchor_id, graph, config)
            all_nodes.extend(result.nodes)
            all_edges.extend(result.edges)

            for node in result.nodes:
                anchor_discoveries[anchor_id].add(node.id)

            # Merge scores
            for node_id, score in result.scores.items():
                if node_id in all_scores:
                    all_scores[node_id] = max(all_scores[node_id], score)
                else:
                    all_scores[node_id] = score

        # Find intersection points (nodes discovered from multiple anchors)
        intersection_nodes = set()
        for i, aid1 in enumerate(anchor_ids):
            for aid2 in anchor_ids[i+1:]:
                common = anchor_discoveries[aid1] & anchor_discoveries[aid2]
                intersection_nodes.update(common)

        # Boost scores for intersection nodes
        for node_id in intersection_nodes:
            if node_id in all_scores:
                all_scores[node_id] *= 1.5  # Bonus for being on multiple paths

        # Deduplicate
        seen_ids = set()
        unique_nodes = []
        for node in all_nodes:
            if node.id not in seen_ids:
                seen_ids.add(node.id)
                unique_nodes.append(node)

        seen_edge_ids = set()
        unique_edges = []
        for edge in all_edges:
            if edge.id not in seen_edge_ids:
                seen_edge_ids.add(edge.id)
                unique_edges.append(edge)

        return TraversalResult(
            nodes=unique_nodes,
            edges=unique_edges,
            paths=all_paths,
            scores=all_scores,
            metadata={
                "method": "bidirectional",
                "anchors": anchor_ids,
                "intersection_count": len(intersection_nodes)
            }
        )


class AdaptiveTopologicalRetriever:
    """
    Adaptive graph-based retrieval system.

    Combines:
    - Query analysis from Intent Router
    - Graph traversal with adaptive policies
    - Result ranking and fusion
    """

    def __init__(self, graphs: MagmaRelationGraphs):
        """
        Initialize adaptive retriever.

        Args:
            graphs: MagmaRelationGraphs instance
        """
        self.graphs = graphs
        self.traverser = GraphTraverser(graphs)

        logger.info("[MAGMA-RETRIEVAL] AdaptiveTopologicalRetriever initialized")

    def retrieve(
        self,
        analysis: QueryAnalysis,
        config: Optional[TraversalConfig] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant nodes based on query analysis.

        Args:
            analysis: QueryAnalysis from Intent Router
            config: Optional traversal configuration

        Returns:
            List of RetrievalResult objects
        """
        config = config or TraversalConfig()

        # Select traversal policy based on analysis
        policy = self._select_policy(analysis)

        # Get target graphs
        target_graphs = self._get_target_graphs(analysis)

        # Find anchor nodes in graphs
        anchor_node_ids = self._find_anchor_nodes(analysis.anchors, target_graphs)

        if not anchor_node_ids:
            logger.warning("[MAGMA-RETRIEVAL] No anchor nodes found in graphs")
            return []

        # Execute traversal based on policy
        all_results: List[RetrievalResult] = []

        for graph_name, graph in target_graphs.items():
            graph_anchors = anchor_node_ids.get(graph_name, [])
            if not graph_anchors:
                continue

            traversal_result = self._execute_traversal(
                policy, graph_anchors, graph, config, analysis
            )

            # Convert to RetrievalResults
            for node in traversal_result.nodes:
                score = traversal_result.scores.get(node.id, 0.5)
                all_results.append(RetrievalResult(
                    id=node.id,
                    content=node.content,
                    score=score,
                    rank=0,  # Will be assigned after sorting
                    source=f"{graph_name}_graph",
                    metadata={
                        "node_type": node.node_type,
                        "trust_score": node.trust_score,
                        "genesis_key_id": node.genesis_key_id,
                        **node.metadata
                    }
                ))

        # Sort by score and assign ranks
        all_results.sort(key=lambda x: x.score, reverse=True)
        for i, result in enumerate(all_results, start=1):
            result.rank = i

        logger.info(
            f"[MAGMA-RETRIEVAL] Retrieved {len(all_results)} results using {policy.value} policy"
        )

        return all_results

    def _select_policy(self, analysis: QueryAnalysis) -> TraversalPolicy:
        """Select traversal policy based on query analysis."""
        policy_map = {
            "graph_traversal": TraversalPolicy.BEST_FIRST,
            "causal_chain": TraversalPolicy.CAUSAL_CHAIN,
            "temporal_window": TraversalPolicy.TEMPORAL_WINDOW,
            "multi_graph_union": TraversalPolicy.BFS,
            "multi_graph_intersection": TraversalPolicy.BIDIRECTIONAL,
            "hybrid": TraversalPolicy.ADAPTIVE,
        }

        return policy_map.get(analysis.retrieval_policy, TraversalPolicy.BFS)

    def _get_target_graphs(self, analysis: QueryAnalysis) -> Dict[str, BaseRelationGraph]:
        """Get target graphs based on analysis."""
        graph_map = {
            "semantic": self.graphs.semantic,
            "temporal": self.graphs.temporal,
            "causal": self.graphs.causal,
            "entity": self.graphs.entity,
        }

        return {
            name: graph for name, graph in graph_map.items()
            if name in analysis.target_graphs
        }

    def _find_anchor_nodes(
        self,
        anchors: List[Anchor],
        target_graphs: Dict[str, BaseRelationGraph]
    ) -> Dict[str, List[str]]:
        """
        Find nodes matching anchors in target graphs.

        Uses content matching since we don't have embeddings here.
        """
        anchor_node_ids: Dict[str, List[str]] = {}

        for graph_name, graph in target_graphs.items():
            matching_ids = []

            for anchor in anchors:
                anchor_lower = anchor.text.lower()

                for node_id, node in graph.nodes.items():
                    if anchor_lower in node.content.lower():
                        matching_ids.append(node_id)

            if matching_ids:
                anchor_node_ids[graph_name] = matching_ids

        return anchor_node_ids

    def _execute_traversal(
        self,
        policy: TraversalPolicy,
        anchor_ids: List[str],
        graph: BaseRelationGraph,
        config: TraversalConfig,
        analysis: QueryAnalysis
    ) -> TraversalResult:
        """Execute traversal with selected policy."""
        if policy == TraversalPolicy.BFS:
            # BFS from first anchor
            return self.traverser.bfs_traverse(anchor_ids[0], graph, config)

        elif policy == TraversalPolicy.BEST_FIRST:
            # Best-first from first anchor
            return self.traverser.best_first_traverse(anchor_ids[0], graph, config)

        elif policy == TraversalPolicy.BIDIRECTIONAL:
            # Bidirectional from all anchors
            return self.traverser.bidirectional_traverse(anchor_ids, graph, config)

        elif policy == TraversalPolicy.CAUSAL_CHAIN:
            # Follow causal relationships
            config.relation_types = [
                RelationType.CAUSAL_CAUSES,
                RelationType.CAUSAL_CAUSED_BY,
                RelationType.CAUSAL_ENABLES,
            ]
            return self.traverser.best_first_traverse(anchor_ids[0], graph, config)

        elif policy == TraversalPolicy.TEMPORAL_WINDOW:
            # Follow temporal relationships
            config.relation_types = [
                RelationType.TEMPORAL_BEFORE,
                RelationType.TEMPORAL_AFTER,
                RelationType.TEMPORAL_SEQUENCE,
            ]
            return self.traverser.bfs_traverse(anchor_ids[0], graph, config)

        elif policy == TraversalPolicy.ADAPTIVE:
            # Adaptive: start with BFS, switch to best-first if results are poor
            bfs_result = self.traverser.bfs_traverse(anchor_ids[0], graph, config)

            # Check result quality
            avg_score = sum(bfs_result.scores.values()) / max(len(bfs_result.scores), 1)

            if avg_score < config.adaptive_threshold and len(bfs_result.nodes) < 5:
                # Try best-first for potentially better results
                return self.traverser.best_first_traverse(anchor_ids[0], graph, config)

            return bfs_result

        else:
            # Default to BFS
            return self.traverser.bfs_traverse(anchor_ids[0], graph, config)

    def retrieve_neighbors(
        self,
        node_id: str,
        graph_name: str,
        max_depth: int = 2,
        max_neighbors: int = 20
    ) -> List[RetrievalResult]:
        """
        Simple neighbor retrieval for a specific node.

        Args:
            node_id: Source node ID
            graph_name: Target graph name
            max_depth: Maximum traversal depth
            max_neighbors: Maximum neighbors to return

        Returns:
            List of RetrievalResult for neighbors
        """
        graph_map = {
            "semantic": self.graphs.semantic,
            "temporal": self.graphs.temporal,
            "causal": self.graphs.causal,
            "entity": self.graphs.entity,
        }

        graph = graph_map.get(graph_name)
        if not graph:
            return []

        config = TraversalConfig(max_depth=max_depth, max_nodes=max_neighbors)
        result = self.traverser.bfs_traverse(node_id, graph, config)

        # Convert to RetrievalResults
        retrieval_results = []
        for i, node in enumerate(result.nodes[1:], start=1):  # Skip the source node
            score = result.scores.get(node.id, 0.5)
            retrieval_results.append(RetrievalResult(
                id=node.id,
                content=node.content,
                score=score,
                rank=i,
                source=f"{graph_name}_neighbors",
                metadata={"node_type": node.node_type, "trust_score": node.trust_score}
            ))

        return retrieval_results
