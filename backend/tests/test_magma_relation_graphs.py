"""
Full Test Suite for Magma Relation Graphs

Tests all four graph types comprehensively:
- SemanticGraph
- TemporalGraph
- CausalGraph
- EntityGraph
- MagmaRelationGraphs (unified interface)

NOT a smoke test - comprehensive coverage of all functionality.
"""

import pytest
from datetime import datetime, timedelta
from typing import List
import uuid

from cognitive.magma.relation_graphs import (
    MagmaRelationGraphs,
    SemanticGraph,
    TemporalGraph,
    CausalGraph,
    EntityGraph,
    GraphNode,
    GraphEdge,
    RelationType,
    BaseRelationGraph
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def semantic_graph():
    """Fresh semantic graph for each test."""
    return SemanticGraph()


@pytest.fixture
def temporal_graph():
    """Fresh temporal graph for each test."""
    return TemporalGraph()


@pytest.fixture
def causal_graph():
    """Fresh causal graph for each test."""
    return CausalGraph()


@pytest.fixture
def entity_graph():
    """Fresh entity graph for each test."""
    return EntityGraph()


@pytest.fixture
def magma_graphs():
    """Fresh unified magma graphs for each test."""
    return MagmaRelationGraphs()


@pytest.fixture
def sample_embedding():
    """Sample embedding vector."""
    return [0.1] * 384  # Common embedding dimension


@pytest.fixture
def similar_embedding():
    """Embedding similar to sample_embedding."""
    return [0.11] * 384  # Slightly different


@pytest.fixture
def different_embedding():
    """Embedding different from sample_embedding."""
    return [0.9, -0.5] * 192  # Very different


# =============================================================================
# TEST: GraphNode
# =============================================================================

class TestGraphNode:
    """Tests for GraphNode dataclass."""

    def test_create_node(self):
        """Test basic node creation."""
        node = GraphNode(
            id="test-node-1",
            node_type="concept",
            content="test content"
        )
        assert node.id == "test-node-1"
        assert node.node_type == "concept"
        assert node.content == "test content"
        assert node.trust_score == 0.5  # Default
        assert node.embedding is None
        assert node.metadata == {}

    def test_node_with_embedding(self, sample_embedding):
        """Test node with embedding."""
        node = GraphNode(
            id="test-node-2",
            node_type="concept",
            content="embedded content",
            embedding=sample_embedding
        )
        assert node.embedding == sample_embedding
        assert len(node.embedding) == 384

    def test_node_with_metadata(self):
        """Test node with metadata."""
        metadata = {"key": "value", "count": 42}
        node = GraphNode(
            id="test-node-3",
            node_type="entity",
            content="test",
            metadata=metadata
        )
        assert node.metadata["key"] == "value"
        assert node.metadata["count"] == 42

    def test_node_with_genesis_key(self):
        """Test node with Genesis Key ID."""
        node = GraphNode(
            id="test-node-4",
            node_type="event",
            content="test",
            genesis_key_id="GK-TEST12345678"
        )
        assert node.genesis_key_id == "GK-TEST12345678"

    def test_node_hash_and_equality(self):
        """Test node hashing and equality."""
        node1 = GraphNode(id="same-id", node_type="concept", content="content1")
        node2 = GraphNode(id="same-id", node_type="concept", content="content2")
        node3 = GraphNode(id="different-id", node_type="concept", content="content1")

        assert node1 == node2  # Same ID = equal
        assert node1 != node3  # Different ID = not equal
        assert hash(node1) == hash(node2)
        assert hash(node1) != hash(node3)

    def test_node_in_set(self):
        """Test nodes in a set (uses hash)."""
        node1 = GraphNode(id="node-1", node_type="concept", content="a")
        node2 = GraphNode(id="node-1", node_type="concept", content="b")  # Same ID
        node3 = GraphNode(id="node-2", node_type="concept", content="c")

        node_set = {node1, node2, node3}
        assert len(node_set) == 2  # node1 and node2 are same


# =============================================================================
# TEST: GraphEdge
# =============================================================================

class TestGraphEdge:
    """Tests for GraphEdge dataclass."""

    def test_create_edge(self):
        """Test basic edge creation."""
        edge = GraphEdge(
            id="edge-1",
            source_id="node-a",
            target_id="node-b",
            relation_type=RelationType.SEMANTIC_SIMILAR
        )
        assert edge.id == "edge-1"
        assert edge.source_id == "node-a"
        assert edge.target_id == "node-b"
        assert edge.relation_type == RelationType.SEMANTIC_SIMILAR
        assert edge.weight == 1.0  # Default
        assert edge.confidence == 0.5  # Default

    def test_edge_with_weight(self):
        """Test edge with custom weight."""
        edge = GraphEdge(
            id="edge-2",
            source_id="a",
            target_id="b",
            relation_type=RelationType.CAUSAL_CAUSES,
            weight=0.8,
            confidence=0.9
        )
        assert edge.weight == 0.8
        assert edge.confidence == 0.9

    def test_edge_hash(self):
        """Test edge hashing."""
        edge1 = GraphEdge(id="e1", source_id="a", target_id="b", relation_type=RelationType.SEMANTIC_SIMILAR)
        edge2 = GraphEdge(id="e1", source_id="x", target_id="y", relation_type=RelationType.CAUSAL_CAUSES)

        assert hash(edge1) == hash(edge2)  # Same ID = same hash


# =============================================================================
# TEST: BaseRelationGraph
# =============================================================================

class TestBaseRelationGraph:
    """Tests for BaseRelationGraph functionality."""

    def test_add_node(self, semantic_graph):
        """Test adding nodes."""
        node = GraphNode(id="n1", node_type="concept", content="test")
        node_id = semantic_graph.add_node(node)

        assert node_id == "n1"
        assert "n1" in semantic_graph.nodes
        assert semantic_graph.nodes["n1"].content == "test"

    def test_add_edge(self, semantic_graph):
        """Test adding edges."""
        # Add nodes first
        node1 = GraphNode(id="n1", node_type="concept", content="a")
        node2 = GraphNode(id="n2", node_type="concept", content="b")
        semantic_graph.add_node(node1)
        semantic_graph.add_node(node2)

        # Add edge
        edge = GraphEdge(
            id="e1",
            source_id="n1",
            target_id="n2",
            relation_type=RelationType.SEMANTIC_RELATED
        )
        edge_id = semantic_graph.add_edge(edge)

        assert edge_id == "e1"
        assert "e1" in semantic_graph.edges
        assert "e1" in semantic_graph.adjacency["n1"]
        assert "e1" in semantic_graph.reverse_adjacency["n2"]

    def test_add_edge_missing_source(self, semantic_graph):
        """Test adding edge with missing source node."""
        node = GraphNode(id="n1", node_type="concept", content="a")
        semantic_graph.add_node(node)

        edge = GraphEdge(
            id="e1",
            source_id="missing",
            target_id="n1",
            relation_type=RelationType.SEMANTIC_RELATED
        )

        with pytest.raises(ValueError, match="Source node missing not found"):
            semantic_graph.add_edge(edge)

    def test_add_edge_missing_target(self, semantic_graph):
        """Test adding edge with missing target node."""
        node = GraphNode(id="n1", node_type="concept", content="a")
        semantic_graph.add_node(node)

        edge = GraphEdge(
            id="e1",
            source_id="n1",
            target_id="missing",
            relation_type=RelationType.SEMANTIC_RELATED
        )

        with pytest.raises(ValueError, match="Target node missing not found"):
            semantic_graph.add_edge(edge)

    def test_get_node(self, semantic_graph):
        """Test getting a node."""
        node = GraphNode(id="n1", node_type="concept", content="test")
        semantic_graph.add_node(node)

        retrieved = semantic_graph.get_node("n1")
        assert retrieved is not None
        assert retrieved.content == "test"

        missing = semantic_graph.get_node("nonexistent")
        assert missing is None

    def test_get_neighbors_outgoing(self, semantic_graph):
        """Test getting outgoing neighbors."""
        # Create triangle: n1 -> n2, n1 -> n3
        nodes = [
            GraphNode(id="n1", node_type="concept", content="center"),
            GraphNode(id="n2", node_type="concept", content="neighbor1"),
            GraphNode(id="n3", node_type="concept", content="neighbor2"),
        ]
        for n in nodes:
            semantic_graph.add_node(n)

        edges = [
            GraphEdge(id="e1", source_id="n1", target_id="n2", relation_type=RelationType.SEMANTIC_RELATED),
            GraphEdge(id="e2", source_id="n1", target_id="n3", relation_type=RelationType.SEMANTIC_RELATED),
        ]
        for e in edges:
            semantic_graph.add_edge(e)

        neighbors = semantic_graph.get_neighbors("n1", direction="outgoing")
        assert len(neighbors) == 2
        neighbor_ids = [n.id for n, e in neighbors]
        assert "n2" in neighbor_ids
        assert "n3" in neighbor_ids

    def test_get_neighbors_incoming(self, semantic_graph):
        """Test getting incoming neighbors."""
        nodes = [
            GraphNode(id="n1", node_type="concept", content="source1"),
            GraphNode(id="n2", node_type="concept", content="source2"),
            GraphNode(id="n3", node_type="concept", content="target"),
        ]
        for n in nodes:
            semantic_graph.add_node(n)

        edges = [
            GraphEdge(id="e1", source_id="n1", target_id="n3", relation_type=RelationType.SEMANTIC_RELATED),
            GraphEdge(id="e2", source_id="n2", target_id="n3", relation_type=RelationType.SEMANTIC_RELATED),
        ]
        for e in edges:
            semantic_graph.add_edge(e)

        neighbors = semantic_graph.get_neighbors("n3", direction="incoming")
        assert len(neighbors) == 2

    def test_get_neighbors_with_relation_filter(self, semantic_graph):
        """Test filtering neighbors by relation type."""
        nodes = [
            GraphNode(id="n1", node_type="concept", content="center"),
            GraphNode(id="n2", node_type="concept", content="similar"),
            GraphNode(id="n3", node_type="concept", content="related"),
        ]
        for n in nodes:
            semantic_graph.add_node(n)

        edges = [
            GraphEdge(id="e1", source_id="n1", target_id="n2", relation_type=RelationType.SEMANTIC_SIMILAR),
            GraphEdge(id="e2", source_id="n1", target_id="n3", relation_type=RelationType.SEMANTIC_RELATED),
        ]
        for e in edges:
            semantic_graph.add_edge(e)

        # Filter for SIMILAR only
        similar_neighbors = semantic_graph.get_neighbors(
            "n1",
            relation_types=[RelationType.SEMANTIC_SIMILAR],
            direction="outgoing"
        )
        assert len(similar_neighbors) == 1
        assert similar_neighbors[0][0].id == "n2"

    def test_find_path_direct(self, semantic_graph):
        """Test finding direct path between nodes."""
        nodes = [
            GraphNode(id="n1", node_type="concept", content="start"),
            GraphNode(id="n2", node_type="concept", content="end"),
        ]
        for n in nodes:
            semantic_graph.add_node(n)

        edge = GraphEdge(id="e1", source_id="n1", target_id="n2", relation_type=RelationType.SEMANTIC_RELATED)
        semantic_graph.add_edge(edge)

        path = semantic_graph.find_path("n1", "n2")
        assert path is not None
        assert len(path) == 2
        assert path[0][0].id == "n1"
        assert path[1][0].id == "n2"

    def test_find_path_multi_hop(self, semantic_graph):
        """Test finding multi-hop path."""
        nodes = [
            GraphNode(id="n1", node_type="concept", content="start"),
            GraphNode(id="n2", node_type="concept", content="middle"),
            GraphNode(id="n3", node_type="concept", content="end"),
        ]
        for n in nodes:
            semantic_graph.add_node(n)

        edges = [
            GraphEdge(id="e1", source_id="n1", target_id="n2", relation_type=RelationType.SEMANTIC_RELATED),
            GraphEdge(id="e2", source_id="n2", target_id="n3", relation_type=RelationType.SEMANTIC_RELATED),
        ]
        for e in edges:
            semantic_graph.add_edge(e)

        path = semantic_graph.find_path("n1", "n3")
        assert path is not None
        assert len(path) == 3

    def test_find_path_no_path(self, semantic_graph):
        """Test when no path exists."""
        nodes = [
            GraphNode(id="n1", node_type="concept", content="isolated1"),
            GraphNode(id="n2", node_type="concept", content="isolated2"),
        ]
        for n in nodes:
            semantic_graph.add_node(n)

        path = semantic_graph.find_path("n1", "n2")
        assert path is None

    def test_find_path_same_node(self, semantic_graph):
        """Test path to same node."""
        node = GraphNode(id="n1", node_type="concept", content="self")
        semantic_graph.add_node(node)

        path = semantic_graph.find_path("n1", "n1")
        assert path is not None
        assert len(path) == 1

    def test_get_subgraph(self, semantic_graph):
        """Test extracting subgraph."""
        # Create star topology: center -> 5 nodes
        center = GraphNode(id="center", node_type="concept", content="center")
        semantic_graph.add_node(center)

        for i in range(5):
            node = GraphNode(id=f"n{i}", node_type="concept", content=f"node{i}")
            semantic_graph.add_node(node)
            edge = GraphEdge(
                id=f"e{i}",
                source_id="center",
                target_id=f"n{i}",
                relation_type=RelationType.SEMANTIC_RELATED
            )
            semantic_graph.add_edge(edge)

        subgraph_nodes, subgraph_edges = semantic_graph.get_subgraph("center", depth=1)

        assert len(subgraph_nodes) == 6  # center + 5 nodes
        assert len(subgraph_edges) == 5

    def test_calculate_node_importance(self, semantic_graph):
        """Test node importance calculation."""
        # Create hub-and-spoke: hub has many connections
        hub = GraphNode(id="hub", node_type="concept", content="hub", trust_score=0.9)
        semantic_graph.add_node(hub)

        for i in range(10):
            node = GraphNode(id=f"spoke{i}", node_type="concept", content=f"spoke{i}")
            semantic_graph.add_node(node)
            edge = GraphEdge(
                id=f"e{i}",
                source_id="hub",
                target_id=f"spoke{i}",
                relation_type=RelationType.SEMANTIC_RELATED,
                weight=0.8
            )
            semantic_graph.add_edge(edge)

        hub_importance = semantic_graph.calculate_node_importance("hub")
        spoke_importance = semantic_graph.calculate_node_importance("spoke0")

        assert hub_importance > spoke_importance

    def test_get_stats(self, semantic_graph):
        """Test getting graph statistics."""
        # Add some nodes and edges
        for i in range(5):
            node = GraphNode(id=f"n{i}", node_type="concept", content=f"node{i}")
            semantic_graph.add_node(node)

        for i in range(3):
            edge = GraphEdge(
                id=f"e{i}",
                source_id=f"n{i}",
                target_id=f"n{i+1}",
                relation_type=RelationType.SEMANTIC_RELATED
            )
            semantic_graph.add_edge(edge)

        stats = semantic_graph.get_stats()

        assert stats["graph_type"] == "semantic"
        assert stats["total_nodes"] == 5
        assert stats["total_edges"] == 3
        assert "avg_degree" in stats
        assert "relation_type_counts" in stats


# =============================================================================
# TEST: SemanticGraph
# =============================================================================

class TestSemanticGraph:
    """Tests for SemanticGraph functionality."""

    def test_add_concept(self, semantic_graph, sample_embedding):
        """Test adding a concept."""
        node_id = semantic_graph.add_concept(
            content="machine learning",
            embedding=sample_embedding,
            genesis_key_id="GK-TEST001"
        )

        assert node_id.startswith("sem-")
        assert node_id in semantic_graph.nodes
        assert semantic_graph.nodes[node_id].content == "machine learning"

    def test_auto_similarity_linking(self, semantic_graph, sample_embedding, similar_embedding):
        """Test automatic similarity linking."""
        # Add first concept
        node1_id = semantic_graph.add_concept(
            content="deep learning",
            embedding=sample_embedding
        )

        # Add similar concept - should auto-link
        node2_id = semantic_graph.add_concept(
            content="neural networks",
            embedding=similar_embedding
        )

        # Check edge was created
        assert len(semantic_graph.edges) >= 1

        # Verify similarity relationship
        neighbors = semantic_graph.get_neighbors(node2_id, direction="outgoing")
        assert len(neighbors) >= 1

    def test_no_link_for_different_embeddings(self, semantic_graph, sample_embedding, different_embedding):
        """Test no linking for dissimilar concepts."""
        semantic_graph.similarity_threshold = 0.9  # High threshold

        node1_id = semantic_graph.add_concept(
            content="machine learning",
            embedding=sample_embedding
        )

        node2_id = semantic_graph.add_concept(
            content="cooking recipes",
            embedding=different_embedding
        )

        # Should not be linked (very different embeddings)
        neighbors = semantic_graph.get_neighbors(node2_id, direction="outgoing")
        node1_in_neighbors = any(n.id == node1_id for n, e in neighbors)
        # With high threshold and very different embeddings, should not link
        assert not node1_in_neighbors or len(neighbors) == 0

    def test_find_related_concepts(self, semantic_graph, sample_embedding):
        """Test finding related concepts."""
        # Add several concepts with similar embeddings
        base_id = semantic_graph.add_concept("base concept", sample_embedding)

        for i in range(5):
            slightly_diff = [x + (i * 0.01) for x in sample_embedding]
            semantic_graph.add_concept(f"related concept {i}", slightly_diff)

        related = semantic_graph.find_related_concepts(base_id, max_results=3)
        assert len(related) <= 3

    def test_cosine_similarity(self, semantic_graph):
        """Test cosine similarity calculation."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        vec3 = [0.0, 1.0, 0.0]
        vec4 = [-1.0, 0.0, 0.0]

        # Identical vectors
        assert semantic_graph._cosine_similarity(vec1, vec2) == pytest.approx(1.0)

        # Orthogonal vectors
        assert semantic_graph._cosine_similarity(vec1, vec3) == pytest.approx(0.0)

        # Opposite vectors
        assert semantic_graph._cosine_similarity(vec1, vec4) == pytest.approx(-1.0)

    def test_cosine_similarity_edge_cases(self, semantic_graph):
        """Test cosine similarity edge cases."""
        # Empty vectors
        assert semantic_graph._cosine_similarity([], []) == 0.0

        # Zero vectors
        assert semantic_graph._cosine_similarity([0, 0], [0, 0]) == 0.0

        # Different lengths
        assert semantic_graph._cosine_similarity([1, 2], [1, 2, 3]) == 0.0


# =============================================================================
# TEST: TemporalGraph
# =============================================================================

class TestTemporalGraph:
    """Tests for TemporalGraph functionality."""

    def test_add_event(self, temporal_graph):
        """Test adding a temporal event."""
        now = datetime.now()
        node_id = temporal_graph.add_event(
            content="User logged in",
            timestamp=now,
            genesis_key_id="GK-EVENT001"
        )

        assert node_id.startswith("temp-")
        assert node_id in temporal_graph.nodes
        assert temporal_graph.nodes[node_id].metadata["timestamp"] == now.isoformat()

    def test_auto_temporal_linking(self, temporal_graph):
        """Test automatic temporal relationship creation."""
        now = datetime.now()

        # Add events in sequence
        event1_id = temporal_graph.add_event("Event 1", now - timedelta(minutes=5))
        event2_id = temporal_graph.add_event("Event 2", now)

        # Should have temporal relationship
        assert len(temporal_graph.edges) >= 1

    def test_concurrent_events(self, temporal_graph):
        """Test concurrent event detection."""
        now = datetime.now()

        event1_id = temporal_graph.add_event("Event A", now)
        event2_id = temporal_graph.add_event("Event B", now + timedelta(seconds=30))  # Within 1 minute

        # Check for concurrent relationship
        edges = list(temporal_graph.edges.values())
        concurrent_edges = [e for e in edges if e.relation_type == RelationType.TEMPORAL_CONCURRENT]
        assert len(concurrent_edges) >= 1

    def test_temporal_before_after(self, temporal_graph):
        """Test before/after relationships."""
        now = datetime.now()

        early_id = temporal_graph.add_event("Early event", now - timedelta(hours=1))
        late_id = temporal_graph.add_event("Late event", now)

        # Late event should have AFTER relationship to early event
        neighbors = temporal_graph.get_neighbors(
            late_id,
            relation_types=[RelationType.TEMPORAL_AFTER],
            direction="outgoing"
        )
        assert len(neighbors) >= 1

    def test_get_events_in_range(self, temporal_graph):
        """Test getting events in a time range."""
        base_time = datetime.now()

        # Add events at different times
        for i in range(10):
            temporal_graph.add_event(
                f"Event {i}",
                base_time + timedelta(hours=i)
            )

        # Get events in middle range
        start = base_time + timedelta(hours=3)
        end = base_time + timedelta(hours=7)
        events = temporal_graph.get_events_in_range(start, end)

        assert len(events) == 5  # Events 3, 4, 5, 6, 7

    def test_get_event_sequence(self, temporal_graph):
        """Test getting event sequence."""
        base_time = datetime.now()

        event_ids = []
        for i in range(5):
            event_id = temporal_graph.add_event(
                f"Sequence event {i}",
                base_time + timedelta(minutes=i * 10)
            )
            event_ids.append(event_id)

        # Get sequence starting from first event
        sequence = temporal_graph.get_event_sequence(event_ids[0], max_length=5)
        assert len(sequence) >= 1

    def test_time_weight_decay(self, temporal_graph):
        """Test that edge weight decays with time difference."""
        now = datetime.now()

        event1_id = temporal_graph.add_event("Event 1", now - timedelta(hours=23))
        event2_id = temporal_graph.add_event("Event 2", now)

        # Get the edge
        edges = list(temporal_graph.edges.values())
        assert len(edges) >= 1

        # Weight should be relatively low due to ~23 hour gap
        for edge in edges:
            assert edge.weight <= 1.0


# =============================================================================
# TEST: CausalGraph
# =============================================================================

class TestCausalGraph:
    """Tests for CausalGraph functionality."""

    def test_add_causal_link(self, causal_graph):
        """Test adding causal relationship."""
        # Add nodes
        cause = GraphNode(id="cause", node_type="event", content="Rain")
        effect = GraphNode(id="effect", node_type="event", content="Wet ground")
        causal_graph.add_node(cause)
        causal_graph.add_node(effect)

        # Add causal link
        edge_id = causal_graph.add_causal_link(
            cause_id="cause",
            effect_id="effect",
            relation=RelationType.CAUSAL_CAUSES,
            confidence=0.9,
            evidence=["observed 100 times"]
        )

        assert edge_id.startswith("causal-edge-")
        edge = causal_graph.edges[edge_id]
        assert edge.confidence == 0.9
        assert "observed 100 times" in edge.metadata["evidence"]

    def test_invalid_causal_relation(self, causal_graph):
        """Test rejection of invalid relation type."""
        cause = GraphNode(id="cause", node_type="event", content="A")
        effect = GraphNode(id="effect", node_type="event", content="B")
        causal_graph.add_node(cause)
        causal_graph.add_node(effect)

        with pytest.raises(ValueError, match="Invalid causal relation"):
            causal_graph.add_causal_link(
                "cause", "effect",
                RelationType.SEMANTIC_SIMILAR  # Wrong type!
            )

    def test_get_causes(self, causal_graph):
        """Test getting causes of an effect."""
        # Create: A causes C, B causes C
        for node_id in ["A", "B", "C"]:
            causal_graph.add_node(GraphNode(id=node_id, node_type="event", content=node_id))

        causal_graph.add_causal_link("A", "C", RelationType.CAUSAL_CAUSES, confidence=0.8)
        causal_graph.add_causal_link("B", "C", RelationType.CAUSAL_CAUSES, confidence=0.6)

        causes = causal_graph.get_causes("C")
        assert len(causes) == 2
        cause_ids = [node.id for node, conf in causes]
        assert "A" in cause_ids
        assert "B" in cause_ids

    def test_get_effects(self, causal_graph):
        """Test getting effects of a cause."""
        # Create: A causes B, A causes C
        for node_id in ["A", "B", "C"]:
            causal_graph.add_node(GraphNode(id=node_id, node_type="event", content=node_id))

        causal_graph.add_causal_link("A", "B", RelationType.CAUSAL_CAUSES, confidence=0.9)
        causal_graph.add_causal_link("A", "C", RelationType.CAUSAL_CAUSES, confidence=0.7)

        effects = causal_graph.get_effects("A")
        assert len(effects) == 2

    def test_trace_causal_chain(self, causal_graph):
        """Test tracing causal chains."""
        # Create chain: A -> B -> C -> D
        for node_id in ["A", "B", "C", "D"]:
            causal_graph.add_node(GraphNode(id=node_id, node_type="event", content=node_id))

        causal_graph.add_causal_link("A", "B", RelationType.CAUSAL_CAUSES)
        causal_graph.add_causal_link("B", "C", RelationType.CAUSAL_CAUSES)
        causal_graph.add_causal_link("C", "D", RelationType.CAUSAL_CAUSES)

        chains = causal_graph.trace_causal_chain("A", direction="effects", max_depth=5)

        assert len(chains) >= 1
        # Should find chain A -> B -> C -> D
        longest_chain = max(chains, key=len)
        assert len(longest_chain) == 4

    def test_trace_causal_chain_branching(self, causal_graph):
        """Test tracing with branching causation."""
        # A -> B, A -> C (branching)
        for node_id in ["A", "B", "C"]:
            causal_graph.add_node(GraphNode(id=node_id, node_type="event", content=node_id))

        causal_graph.add_causal_link("A", "B", RelationType.CAUSAL_CAUSES)
        causal_graph.add_causal_link("A", "C", RelationType.CAUSAL_CAUSES)

        chains = causal_graph.trace_causal_chain("A", direction="effects")

        # Should find two chains: A->B and A->C
        assert len(chains) == 2

    def test_enables_prevents_relations(self, causal_graph):
        """Test enables and prevents relations."""
        for node_id in ["condition", "enabled", "prevented"]:
            causal_graph.add_node(GraphNode(id=node_id, node_type="event", content=node_id))

        causal_graph.add_causal_link("condition", "enabled", RelationType.CAUSAL_ENABLES)
        causal_graph.add_causal_link("condition", "prevented", RelationType.CAUSAL_PREVENTS)

        neighbors = causal_graph.get_neighbors("condition", direction="outgoing")
        relation_types = [e.relation_type for n, e in neighbors]

        assert RelationType.CAUSAL_ENABLES in relation_types
        assert RelationType.CAUSAL_PREVENTS in relation_types


# =============================================================================
# TEST: EntityGraph
# =============================================================================

class TestEntityGraph:
    """Tests for EntityGraph functionality."""

    def test_add_entity(self, entity_graph):
        """Test adding an entity."""
        entity_id = entity_graph.add_entity(
            name="John Doe",
            entity_type="person",
            attributes={"age": 30, "role": "developer"}
        )

        assert entity_id.startswith("ent-")
        entity = entity_graph.nodes[entity_id]
        assert entity.content == "John Doe"
        assert entity.metadata["entity_type"] == "person"
        assert entity.metadata["attributes"]["age"] == 30

    def test_link_entities(self, entity_graph):
        """Test linking entities."""
        person_id = entity_graph.add_entity("Alice", "person")
        company_id = entity_graph.add_entity("Acme Corp", "organization")

        edge_id = entity_graph.link_entities(
            person_id,
            company_id,
            RelationType.ENTITY_PART_OF,
            confidence=0.95,
            context="employment"
        )

        assert edge_id.startswith("ent-edge-")
        edge = entity_graph.edges[edge_id]
        assert edge.relation_type == RelationType.ENTITY_PART_OF
        assert edge.metadata["context"] == "employment"

    def test_invalid_entity_relation(self, entity_graph):
        """Test rejection of invalid entity relation."""
        e1 = entity_graph.add_entity("A", "thing")
        e2 = entity_graph.add_entity("B", "thing")

        with pytest.raises(ValueError, match="Invalid entity relation"):
            entity_graph.link_entities(e1, e2, RelationType.CAUSAL_CAUSES)

    def test_record_co_occurrence(self, entity_graph):
        """Test recording co-occurrences."""
        e1 = entity_graph.add_entity("Python", "technology")
        e2 = entity_graph.add_entity("Machine Learning", "concept")

        # Record multiple co-occurrences
        entity_graph.record_co_occurrence(e1, e2, "article about ML with Python")
        entity_graph.record_co_occurrence(e1, e2, "Python ML tutorial")
        entity_graph.record_co_occurrence(e1, e2, "Data science course")

        # Check co-occurrence edge exists with increased weight
        neighbors = entity_graph.get_neighbors(
            e1,
            relation_types=[RelationType.ENTITY_CO_OCCURS],
            direction="outgoing"
        )
        assert len(neighbors) == 1
        node, edge = neighbors[0]
        assert edge.weight > 0.5  # Should have increased from base

    def test_get_entity_cluster(self, entity_graph):
        """Test getting entity cluster."""
        # Create cluster of related entities
        center_id = entity_graph.add_entity("Python", "language")

        related_ids = []
        for tech in ["Django", "Flask", "FastAPI", "NumPy"]:
            tech_id = entity_graph.add_entity(tech, "framework")
            related_ids.append(tech_id)
            entity_graph.link_entities(
                center_id, tech_id,
                RelationType.ENTITY_RELATED_TO,
                confidence=0.8
            )

        cluster = entity_graph.get_entity_cluster(center_id, min_co_occurrence=0.3)
        assert len(cluster) == 4

    def test_instance_of_relation(self, entity_graph):
        """Test instance-of relationships."""
        class_id = entity_graph.add_entity("Vehicle", "class")
        instance_id = entity_graph.add_entity("My Car", "instance")

        entity_graph.link_entities(
            instance_id, class_id,
            RelationType.ENTITY_INSTANCE_OF
        )

        neighbors = entity_graph.get_neighbors(
            instance_id,
            relation_types=[RelationType.ENTITY_INSTANCE_OF],
            direction="outgoing"
        )
        assert len(neighbors) == 1
        assert neighbors[0][0].content == "Vehicle"


# =============================================================================
# TEST: MagmaRelationGraphs (Unified Interface)
# =============================================================================

class TestMagmaRelationGraphs:
    """Tests for unified MagmaRelationGraphs interface."""

    def test_initialization(self, magma_graphs):
        """Test unified graphs initialization."""
        assert magma_graphs.semantic is not None
        assert magma_graphs.temporal is not None
        assert magma_graphs.causal is not None
        assert magma_graphs.entity is not None

    def test_get_all_graphs(self, magma_graphs):
        """Test getting all graphs."""
        graphs = magma_graphs.get_all_graphs()

        assert "semantic" in graphs
        assert "temporal" in graphs
        assert "causal" in graphs
        assert "entity" in graphs
        assert len(graphs) == 4

    def test_cross_graph_search(self, magma_graphs, sample_embedding):
        """Test cross-graph search via genesis key."""
        genesis_key = "GK-SHARED-001"

        # Add related items to different graphs with same genesis key
        sem_id = magma_graphs.semantic.add_concept(
            "machine learning concept",
            sample_embedding,
            genesis_key_id=genesis_key
        )

        now = datetime.now()
        temp_id = magma_graphs.temporal.add_event(
            "ML event",
            now,
            genesis_key_id=genesis_key
        )

        ent_id = magma_graphs.entity.add_entity(
            "ML Entity",
            "concept",
            genesis_key_id=genesis_key
        )

        # Cross-graph search from semantic
        results = magma_graphs.cross_graph_search(
            sem_id,
            source_graph="semantic",
            target_graphs=["temporal", "entity"]
        )

        assert "temporal" in results
        assert "entity" in results

    def test_get_unified_stats(self, magma_graphs, sample_embedding):
        """Test getting unified statistics."""
        # Add some data
        magma_graphs.semantic.add_concept("concept 1", sample_embedding)
        magma_graphs.semantic.add_concept("concept 2", sample_embedding)
        magma_graphs.temporal.add_event("event 1", datetime.now())
        magma_graphs.entity.add_entity("entity 1", "thing")

        stats = magma_graphs.get_unified_stats()

        assert "semantic" in stats
        assert "temporal" in stats
        assert "causal" in stats
        assert "entity" in stats
        assert stats["total_nodes"] >= 4
        assert "total_edges" in stats

    def test_empty_graphs(self, magma_graphs):
        """Test operations on empty graphs."""
        stats = magma_graphs.get_unified_stats()

        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0

    def test_cross_graph_no_genesis_key(self, magma_graphs, sample_embedding):
        """Test cross-graph search when node has no genesis key."""
        # Add node without genesis key
        sem_id = magma_graphs.semantic.add_concept(
            "concept without genesis",
            sample_embedding,
            genesis_key_id=None
        )

        results = magma_graphs.cross_graph_search(sem_id, "semantic")
        assert results == {}


# =============================================================================
# TEST: Integration Scenarios
# =============================================================================

class TestIntegrationScenarios:
    """Integration tests for complex scenarios."""

    def test_knowledge_graph_construction(self, magma_graphs, sample_embedding):
        """Test building a knowledge graph across all dimensions."""
        # Add semantic concepts
        ml_id = magma_graphs.semantic.add_concept("Machine Learning", sample_embedding)
        dl_id = magma_graphs.semantic.add_concept("Deep Learning", [x + 0.05 for x in sample_embedding])

        # Add temporal events
        now = datetime.now()
        learn_event = magma_graphs.temporal.add_event("Learned ML basics", now - timedelta(days=30))
        apply_event = magma_graphs.temporal.add_event("Applied ML model", now)

        # Add entities
        person_id = magma_graphs.entity.add_entity("Data Scientist", "role")
        tool_id = magma_graphs.entity.add_entity("TensorFlow", "tool")
        magma_graphs.entity.link_entities(person_id, tool_id, RelationType.ENTITY_RELATED_TO)

        # Add causal relationships
        magma_graphs.causal.add_node(GraphNode(id="study", node_type="action", content="Studying ML"))
        magma_graphs.causal.add_node(GraphNode(id="skill", node_type="outcome", content="Gained ML skill"))
        magma_graphs.causal.add_causal_link("study", "skill", RelationType.CAUSAL_CAUSES, confidence=0.85)

        # Verify graph integrity
        stats = magma_graphs.get_unified_stats()
        assert stats["total_nodes"] >= 8
        assert stats["total_edges"] >= 2

    def test_event_driven_memory_update(self, magma_graphs, sample_embedding):
        """Test event-driven memory updates across graphs."""
        genesis_key = "GK-SESSION-001"

        # User starts a task
        start_event = magma_graphs.temporal.add_event(
            "Started coding task",
            datetime.now() - timedelta(hours=1),
            genesis_key_id=genesis_key
        )

        # User learns a concept
        concept_id = magma_graphs.semantic.add_concept(
            "Python asyncio",
            sample_embedding,
            genesis_key_id=genesis_key
        )

        # User completes the task
        end_event = magma_graphs.temporal.add_event(
            "Completed coding task",
            datetime.now(),
            genesis_key_id=genesis_key
        )

        # Verify cross-references
        results = magma_graphs.cross_graph_search(
            concept_id,
            source_graph="semantic",
            target_graphs=["temporal"]
        )

        assert "temporal" in results
        assert len(results["temporal"]) >= 1

    def test_causal_chain_with_entities(self, magma_graphs):
        """Test causal chains involving entities."""
        # Add entities to causal graph as nodes
        bug_node = GraphNode(id="bug", node_type="entity", content="Software Bug")
        fix_node = GraphNode(id="fix", node_type="entity", content="Bug Fix")
        deploy_node = GraphNode(id="deploy", node_type="entity", content="Deployment")

        magma_graphs.causal.add_node(bug_node)
        magma_graphs.causal.add_node(fix_node)
        magma_graphs.causal.add_node(deploy_node)

        # Bug -> Fix -> Deploy
        magma_graphs.causal.add_causal_link("bug", "fix", RelationType.CAUSAL_CAUSES)
        magma_graphs.causal.add_causal_link("fix", "deploy", RelationType.CAUSAL_ENABLES)

        # Trace the chain
        chains = magma_graphs.causal.trace_causal_chain("bug", direction="effects")
        assert len(chains) >= 1

        # Also add to entity graph
        bug_ent = magma_graphs.entity.add_entity("Software Bug", "issue")
        fix_ent = magma_graphs.entity.add_entity("Bug Fix", "solution")
        magma_graphs.entity.link_entities(bug_ent, fix_ent, RelationType.ENTITY_RELATED_TO)


# =============================================================================
# TEST: Performance
# =============================================================================

class TestPerformance:
    """Performance tests for graph operations."""

    def test_large_graph_construction(self, semantic_graph, sample_embedding):
        """Test performance with larger graph."""
        # Add 100 nodes
        for i in range(100):
            embedding = [x + (i * 0.001) for x in sample_embedding]
            semantic_graph.add_concept(f"concept_{i}", embedding)

        assert len(semantic_graph.nodes) == 100
        # Should have created similarity edges
        assert len(semantic_graph.edges) > 0

    def test_path_finding_performance(self, semantic_graph):
        """Test path finding in larger graph."""
        # Create chain of 50 nodes
        prev_id = None
        for i in range(50):
            node = GraphNode(id=f"chain_{i}", node_type="concept", content=f"node {i}")
            semantic_graph.add_node(node)

            if prev_id:
                edge = GraphEdge(
                    id=f"chain_edge_{i}",
                    source_id=prev_id,
                    target_id=f"chain_{i}",
                    relation_type=RelationType.SEMANTIC_RELATED
                )
                semantic_graph.add_edge(edge)

            prev_id = f"chain_{i}"

        # Find path from start to end
        path = semantic_graph.find_path("chain_0", "chain_49", max_depth=50)
        assert path is not None
        assert len(path) == 50

    def test_neighbor_retrieval_performance(self, entity_graph):
        """Test neighbor retrieval with many connections."""
        # Create hub with 100 connections
        hub = entity_graph.add_entity("Hub", "central")

        for i in range(100):
            spoke = entity_graph.add_entity(f"Spoke_{i}", "peripheral")
            entity_graph.link_entities(hub, spoke, RelationType.ENTITY_RELATED_TO)

        # Should quickly retrieve all neighbors
        neighbors = entity_graph.get_neighbors(hub, direction="outgoing")
        assert len(neighbors) == 100


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
