#!/usr/bin/env python3
"""
Magma Memory System - Full Test Suite (No pytest required)

Comprehensive tests for all Magma components:
1. Relation Graphs (Semantic, Temporal, Causal, Entity)
2. Intent Router
3. RRF Fusion
4. Topological Retrieval
5. Synaptic Ingestion
6. Async Consolidation
7. Causal Inference
8. MagmaMemory Integration

Run: python run_magma_tests.py
"""

import sys
import os
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestResult:
    """Stores test result."""
    def __init__(self, name: str, passed: bool, error: str = None):
        self.name = name
        self.passed = passed
        self.error = error


class TestRunner:
    """Simple test runner without pytest."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.current_class = ""

    def run_test(self, name: str, test_fn):
        """Run a single test."""
        try:
            test_fn()
            self.results.append(TestResult(name, True))
            print(f"  ✓ {name}")
        except AssertionError as e:
            self.results.append(TestResult(name, False, str(e)))
            print(f"  ✗ {name}: {e}")
        except Exception as e:
            self.results.append(TestResult(name, False, f"{type(e).__name__}: {e}"))
            print(f"  ✗ {name}: {type(e).__name__}: {e}")

    def print_summary(self):
        """Print test summary."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        print("\n" + "=" * 60)
        print(f"TEST RESULTS: {passed} passed, {failed} failed")
        print("=" * 60)

        if failed > 0:
            print("\nFailed tests:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.error}")

        return failed == 0


runner = TestRunner()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def assert_equal(a, b, msg=""):
    """Assert two values are equal."""
    if a != b:
        raise AssertionError(f"{msg}: Expected {b}, got {a}" if msg else f"Expected {b}, got {a}")

def assert_true(condition, msg="Condition should be true"):
    """Assert condition is true."""
    if not condition:
        raise AssertionError(msg)

def assert_false(condition, msg="Condition should be false"):
    """Assert condition is false."""
    if condition:
        raise AssertionError(msg)

def assert_in(item, container, msg=""):
    """Assert item is in container."""
    if item not in container:
        raise AssertionError(f"{msg}: {item} not in {container}" if msg else f"{item} not in container")

def assert_raises(exception_type, fn):
    """Assert function raises exception."""
    try:
        fn()
        raise AssertionError(f"Expected {exception_type.__name__} to be raised")
    except exception_type:
        pass

def assert_greater(a, b, msg=""):
    """Assert a > b."""
    if not a > b:
        raise AssertionError(f"{msg}: {a} not greater than {b}" if msg else f"{a} not greater than {b}")

def assert_is_not_none(val, msg="Value should not be None"):
    """Assert value is not None."""
    if val is None:
        raise AssertionError(msg)

def assert_is_none(val, msg="Value should be None"):
    """Assert value is None."""
    if val is not None:
        raise AssertionError(msg)


# =============================================================================
# TEST: Relation Graphs
# =============================================================================

def test_relation_graphs():
    """Test all relation graph components."""
    print("\n[TEST SUITE] Relation Graphs")
    print("-" * 40)

    from cognitive.magma.relation_graphs import (
        MagmaRelationGraphs,
        SemanticGraph,
        TemporalGraph,
        CausalGraph,
        EntityGraph,
        GraphNode,
        GraphEdge,
        RelationType
    )

    sample_embedding = [0.1] * 384
    similar_embedding = [0.11] * 384

    # Test GraphNode
    def test_graph_node_creation():
        node = GraphNode(id="n1", node_type="concept", content="test")
        assert_equal(node.id, "n1")
        assert_equal(node.node_type, "concept")
        assert_equal(node.content, "test")
        assert_equal(node.trust_score, 0.5)
    runner.run_test("GraphNode creation", test_graph_node_creation)

    def test_graph_node_with_embedding():
        node = GraphNode(id="n2", node_type="concept", content="test", embedding=sample_embedding)
        assert_equal(len(node.embedding), 384)
    runner.run_test("GraphNode with embedding", test_graph_node_with_embedding)

    def test_graph_node_equality():
        n1 = GraphNode(id="same", node_type="a", content="x")
        n2 = GraphNode(id="same", node_type="b", content="y")
        assert_true(n1 == n2, "Nodes with same ID should be equal")
    runner.run_test("GraphNode equality", test_graph_node_equality)

    # Test GraphEdge
    def test_graph_edge_creation():
        edge = GraphEdge(id="e1", source_id="a", target_id="b", relation_type=RelationType.SEMANTIC_SIMILAR)
        assert_equal(edge.id, "e1")
        assert_equal(edge.weight, 1.0)
        assert_equal(edge.confidence, 0.5)
    runner.run_test("GraphEdge creation", test_graph_edge_creation)

    # Test SemanticGraph
    def test_semantic_graph_add_concept():
        graph = SemanticGraph()
        node_id = graph.add_concept("test concept", sample_embedding)
        assert_true(node_id.startswith("sem-"))
        assert_in(node_id, graph.nodes)
    runner.run_test("SemanticGraph add_concept", test_semantic_graph_add_concept)

    def test_semantic_graph_auto_linking():
        graph = SemanticGraph()
        graph.similarity_threshold = 0.5
        n1 = graph.add_concept("concept 1", sample_embedding)
        n2 = graph.add_concept("concept 2", similar_embedding)
        assert_true(len(graph.edges) >= 1, "Should auto-link similar concepts")
    runner.run_test("SemanticGraph auto-linking", test_semantic_graph_auto_linking)

    def test_cosine_similarity():
        graph = SemanticGraph()
        sim = graph._cosine_similarity([1, 0, 0], [1, 0, 0])
        assert_true(abs(sim - 1.0) < 0.01, "Identical vectors should have similarity 1.0")
        sim2 = graph._cosine_similarity([1, 0, 0], [0, 1, 0])
        assert_true(abs(sim2) < 0.01, "Orthogonal vectors should have similarity 0.0")
    runner.run_test("Cosine similarity", test_cosine_similarity)

    # Test TemporalGraph
    def test_temporal_graph_add_event():
        graph = TemporalGraph()
        now = datetime.utcnow()
        node_id = graph.add_event("test event", now)
        assert_true(node_id.startswith("temp-"))
        assert_in(node_id, graph.nodes)
    runner.run_test("TemporalGraph add_event", test_temporal_graph_add_event)

    def test_temporal_graph_auto_linking():
        graph = TemporalGraph()
        now = datetime.utcnow()
        n1 = graph.add_event("event 1", now - timedelta(minutes=5))
        n2 = graph.add_event("event 2", now)
        assert_true(len(graph.edges) >= 1, "Should auto-link temporal events")
    runner.run_test("TemporalGraph auto-linking", test_temporal_graph_auto_linking)

    def test_temporal_graph_range_query():
        graph = TemporalGraph()
        base = datetime.utcnow()
        for i in range(10):
            graph.add_event(f"event {i}", base + timedelta(hours=i))
        events = graph.get_events_in_range(base + timedelta(hours=3), base + timedelta(hours=7))
        assert_equal(len(events), 5)
    runner.run_test("TemporalGraph range query", test_temporal_graph_range_query)

    # Test CausalGraph
    def test_causal_graph_add_link():
        graph = CausalGraph()
        cause = GraphNode(id="cause", node_type="event", content="Rain")
        effect = GraphNode(id="effect", node_type="event", content="Wet ground")
        graph.add_node(cause)
        graph.add_node(effect)
        edge_id = graph.add_causal_link("cause", "effect", RelationType.CAUSAL_CAUSES, confidence=0.9)
        assert_true(edge_id.startswith("causal-edge-"))
    runner.run_test("CausalGraph add_causal_link", test_causal_graph_add_link)

    def test_causal_graph_invalid_relation():
        graph = CausalGraph()
        cause = GraphNode(id="a", node_type="event", content="A")
        effect = GraphNode(id="b", node_type="event", content="B")
        graph.add_node(cause)
        graph.add_node(effect)
        try:
            graph.add_causal_link("a", "b", RelationType.SEMANTIC_SIMILAR)
            raise AssertionError("Should have raised ValueError")
        except ValueError:
            pass
    runner.run_test("CausalGraph invalid relation", test_causal_graph_invalid_relation)

    def test_causal_graph_trace_chain():
        graph = CausalGraph()
        for nid in ["A", "B", "C", "D"]:
            graph.add_node(GraphNode(id=nid, node_type="event", content=nid))
        graph.add_causal_link("A", "B", RelationType.CAUSAL_CAUSES)
        graph.add_causal_link("B", "C", RelationType.CAUSAL_CAUSES)
        graph.add_causal_link("C", "D", RelationType.CAUSAL_CAUSES)
        chains = graph.trace_causal_chain("A", direction="effects", max_depth=5)
        assert_true(len(chains) >= 1, "Should find causal chain")
        longest = max(chains, key=len)
        assert_equal(len(longest), 4)
    runner.run_test("CausalGraph trace chain", test_causal_graph_trace_chain)

    # Test EntityGraph
    def test_entity_graph_add_entity():
        graph = EntityGraph()
        entity_id = graph.add_entity("John Doe", "person", {"age": 30})
        assert_true(entity_id.startswith("ent-"))
        assert_in(entity_id, graph.nodes)
    runner.run_test("EntityGraph add_entity", test_entity_graph_add_entity)

    def test_entity_graph_link_entities():
        graph = EntityGraph()
        p1 = graph.add_entity("Alice", "person")
        c1 = graph.add_entity("Acme", "company")
        edge_id = graph.link_entities(p1, c1, RelationType.ENTITY_PART_OF)
        assert_true(edge_id.startswith("ent-edge-"))
    runner.run_test("EntityGraph link_entities", test_entity_graph_link_entities)

    def test_entity_graph_co_occurrence():
        graph = EntityGraph()
        e1 = graph.add_entity("Python", "tech")
        e2 = graph.add_entity("ML", "concept")
        graph.record_co_occurrence(e1, e2, "article 1")
        graph.record_co_occurrence(e1, e2, "article 2")
        neighbors = graph.get_neighbors(e1, relation_types=[RelationType.ENTITY_CO_OCCURS])
        assert_true(len(neighbors) >= 1, "Should have co-occurrence edge")
    runner.run_test("EntityGraph co-occurrence", test_entity_graph_co_occurrence)

    # Test MagmaRelationGraphs
    def test_magma_graphs_init():
        graphs = MagmaRelationGraphs()
        assert_is_not_none(graphs.semantic)
        assert_is_not_none(graphs.temporal)
        assert_is_not_none(graphs.causal)
        assert_is_not_none(graphs.entity)
    runner.run_test("MagmaRelationGraphs init", test_magma_graphs_init)

    def test_magma_graphs_unified_stats():
        graphs = MagmaRelationGraphs()
        graphs.semantic.add_concept("c1", sample_embedding)
        graphs.temporal.add_event("e1", datetime.utcnow())
        stats = graphs.get_unified_stats()
        assert_in("semantic", stats)
        assert_in("total_nodes", stats)
        assert_greater(stats["total_nodes"], 0)
    runner.run_test("MagmaRelationGraphs unified stats", test_magma_graphs_unified_stats)


# =============================================================================
# TEST: Intent Router
# =============================================================================

def test_intent_router():
    """Test intent router components."""
    print("\n[TEST SUITE] Intent Router")
    print("-" * 40)

    from cognitive.magma.intent_router import (
        IntentAwareRouter,
        IntentClassifier,
        AnchorIdentifier,
        GraphSelector,
        QueryIntent,
        AnchorType
    )

    def test_intent_classifier_factual():
        classifier = IntentClassifier()
        primary_intent, secondary_intents, conf = classifier.classify("What is Python?")
        assert_equal(primary_intent, QueryIntent.DEFINITION)  # "What is" maps to DEFINITION
    runner.run_test("IntentClassifier factual query", test_intent_classifier_factual)

    def test_intent_classifier_temporal():
        classifier = IntentClassifier()
        primary_intent, secondary_intents, conf = classifier.classify("What happened after the meeting?")
        assert_equal(primary_intent, QueryIntent.TEMPORAL_SEQUENCE)
    runner.run_test("IntentClassifier temporal query", test_intent_classifier_temporal)

    def test_intent_classifier_causal():
        classifier = IntentClassifier()
        primary_intent, secondary_intents, conf = classifier.classify("What causes this?")
        assert_equal(primary_intent, QueryIntent.CAUSE)
    runner.run_test("IntentClassifier causal query", test_intent_classifier_causal)

    def test_intent_classifier_exploratory():
        classifier = IntentClassifier()
        primary_intent, secondary_intents, conf = classifier.classify("Tell me something")
        assert_equal(primary_intent, QueryIntent.EXPLORE)  # Default fallback
    runner.run_test("IntentClassifier exploratory query", test_intent_classifier_exploratory)

    def test_anchor_identifier():
        identifier = AnchorIdentifier()
        anchors = identifier.identify("Find information about machine learning and Python programming")
        assert_true(len(anchors) >= 1, "Should identify anchors")
    runner.run_test("AnchorIdentifier basic", test_anchor_identifier)

    def test_graph_selector():
        selector = GraphSelector()
        graphs = selector.select(QueryIntent.DEFINITION, [])  # DEFINITION instead of FACTUAL
        assert_in("semantic", graphs)
    runner.run_test("GraphSelector factual", test_graph_selector)

    def test_graph_selector_temporal():
        selector = GraphSelector()
        graphs = selector.select(QueryIntent.TEMPORAL_SEQUENCE, [])  # Use actual enum value
        assert_in("temporal", graphs)
    runner.run_test("GraphSelector temporal", test_graph_selector_temporal)

    def test_router_analyze_query():
        router = IntentAwareRouter()
        analysis = router.analyze_query("What causes climate change?")
        assert_is_not_none(analysis)
        assert_is_not_none(analysis.primary_intent)  # primary_intent, not intent
        assert_is_not_none(analysis.target_graphs)
    runner.run_test("IntentAwareRouter analyze_query", test_router_analyze_query)

    def test_router_causal_query():
        router = IntentAwareRouter()
        analysis = router.analyze_query("What causes rain to flood?")
        assert_equal(analysis.primary_intent, QueryIntent.CAUSE)  # primary_intent, CAUSE not CAUSAL
        assert_in("causal", analysis.target_graphs)
    runner.run_test("IntentAwareRouter causal query", test_router_causal_query)


# =============================================================================
# TEST: RRF Fusion
# =============================================================================

def test_rrf_fusion():
    """Test RRF fusion components."""
    print("\n[TEST SUITE] RRF Fusion")
    print("-" * 40)

    from cognitive.magma.rrf_fusion import (
        MagmaFusion,
        RRFFusion,
        WeightedRRFFusion,
        CombSUMFusion,
        CombMNZFusion,
        RetrievalResult,
        FusionMethod
    )

    # Create sample results as dict (source_name -> list of results)
    def make_results():
        return {
            "semantic": [
                RetrievalResult(id="r1", content="content1", score=0.9, rank=1, source="semantic", metadata={"test": True}),
                RetrievalResult(id="r2", content="content2", score=0.8, rank=2, source="semantic", metadata={}),
                RetrievalResult(id="r3", content="content3", score=0.7, rank=3, source="semantic", metadata={}),
            ],
            "temporal": [
                RetrievalResult(id="r2", content="content2", score=0.85, rank=1, source="temporal", metadata={}),
                RetrievalResult(id="r4", content="content4", score=0.75, rank=2, source="temporal", metadata={}),
                RetrievalResult(id="r1", content="content1", score=0.65, rank=3, source="temporal", metadata={}),
            ]
        }

    def test_rrf_fusion_basic():
        fusion = RRFFusion()
        results = make_results()
        fused = fusion.fuse(results)
        assert_true(len(fused) >= 1, "Should produce fused results")
        assert_true(fused[0].rrf_score > 0, "Fused results should have positive scores")
    runner.run_test("RRFFusion basic", test_rrf_fusion_basic)

    def test_rrf_fusion_ranking():
        fusion = RRFFusion()
        results = make_results()
        fused = fusion.fuse(results)
        # Results appearing in multiple lists should rank higher
        ids = [r.id for r in fused[:3]]
        assert_in("r1", ids, "r1 in both lists should rank high")
        assert_in("r2", ids, "r2 in both lists should rank high")
    runner.run_test("RRFFusion ranking", test_rrf_fusion_ranking)

    def test_weighted_rrf():
        fusion = WeightedRRFFusion()
        results = make_results()
        weights = {"semantic": 2.0, "temporal": 1.0}
        fused = fusion.fuse(results, weights=weights)  # param is 'weights' not 'source_weights'
        assert_true(len(fused) >= 1, "Should produce weighted fused results")
    runner.run_test("WeightedRRFFusion", test_weighted_rrf)

    def test_combsum_fusion():
        fusion = CombSUMFusion()
        results = make_results()
        fused = fusion.fuse(results)
        assert_true(len(fused) >= 1, "CombSUM should produce results")
    runner.run_test("CombSUMFusion", test_combsum_fusion)

    def test_combmnz_fusion():
        fusion = CombMNZFusion()
        results = make_results()
        fused = fusion.fuse(results)
        assert_true(len(fused) >= 1, "CombMNZ should produce results")
        # Items in multiple lists should be boosted
        multi_list_item = next((r for r in fused if r.id in ["r1", "r2"]), None)
        assert_is_not_none(multi_list_item, "Should have items from multiple lists")
    runner.run_test("CombMNZFusion", test_combmnz_fusion)

    def test_magma_fusion():
        fusion = MagmaFusion()
        results = make_results()
        fused = fusion.fuse(results, method=FusionMethod.RRF)
        assert_true(len(fused) >= 1, "MagmaFusion should work with RRF")
        fused2 = fusion.fuse(results, method=FusionMethod.WEIGHTED_RRF)
        assert_true(len(fused2) >= 1, "MagmaFusion should work with WeightedRRF")
    runner.run_test("MagmaFusion methods", test_magma_fusion)

    def test_empty_results():
        fusion = RRFFusion()
        fused = fusion.fuse({})  # Empty dict, not empty list
        assert_equal(len(fused), 0, "Empty input should produce empty output")
    runner.run_test("RRFFusion empty input", test_empty_results)


# =============================================================================
# TEST: Topological Retrieval
# =============================================================================

def test_topological_retrieval():
    """Test topological retrieval components."""
    print("\n[TEST SUITE] Topological Retrieval")
    print("-" * 40)

    from cognitive.magma.relation_graphs import MagmaRelationGraphs, GraphNode, RelationType
    from cognitive.magma.topological_retrieval import (
        AdaptiveTopologicalRetriever,
        GraphTraverser,
        TraversalPolicy,
        TraversalConfig
    )
    from cognitive.magma.intent_router import IntentAwareRouter

    sample_embedding = [0.1] * 384

    def test_graph_traverser_bfs():
        graphs = MagmaRelationGraphs()
        # Create simple graph
        n1 = graphs.semantic.add_concept("center", sample_embedding)
        n2 = graphs.semantic.add_concept("neighbor1", [0.11] * 384)
        n3 = graphs.semantic.add_concept("neighbor2", [0.12] * 384)

        traverser = GraphTraverser(graphs)  # Takes MagmaRelationGraphs
        config = TraversalConfig(max_depth=2)
        result = traverser.bfs_traverse(n1, graphs.semantic, config)  # bfs_traverse not bfs
        assert_true(len(result.nodes) >= 1, "BFS should visit nodes")
    runner.run_test("GraphTraverser BFS", test_graph_traverser_bfs)

    def test_traverser_best_first():
        graphs = MagmaRelationGraphs()
        n1 = graphs.semantic.add_concept("start", sample_embedding)
        for i in range(5):
            graphs.semantic.add_concept(f"node{i}", [0.1 + i*0.01] * 384)

        traverser = GraphTraverser(graphs)
        config = TraversalConfig(max_depth=3)
        result = traverser.best_first_traverse(n1, graphs.semantic, config)  # best_first_traverse
        assert_true(len(result.nodes) >= 1, "Best-first should visit nodes")
    runner.run_test("GraphTraverser best_first", test_traverser_best_first)

    def test_adaptive_retriever():
        graphs = MagmaRelationGraphs()
        n1 = graphs.semantic.add_concept("query concept", sample_embedding)

        retriever = AdaptiveTopologicalRetriever(graphs)
        router = IntentAwareRouter()
        analysis = router.analyze_query("What is this concept?")

        results = retriever.retrieve(analysis)
        # May be empty if no anchor match, but should not error
        assert_is_not_none(results)
    runner.run_test("AdaptiveTopologicalRetriever", test_adaptive_retriever)

    def test_traversal_config():
        config = TraversalConfig(
            max_depth=5,
            max_nodes=100,
            min_edge_weight=0.3,  # min_edge_weight not min_weight
            relation_types=None   # relation_types not follow_relations
        )
        assert_equal(config.max_depth, 5)
        assert_equal(config.max_nodes, 100)
    runner.run_test("TraversalConfig", test_traversal_config)


# =============================================================================
# TEST: Synaptic Ingestion
# =============================================================================

def test_synaptic_ingestion():
    """Test synaptic ingestion components."""
    print("\n[TEST SUITE] Synaptic Ingestion")
    print("-" * 40)

    from cognitive.magma.relation_graphs import MagmaRelationGraphs
    from cognitive.magma.synaptic_ingestion import (
        SynapticIngestionPipeline,
        EventSegmenter,
        SemanticLinker,
        TemporalLinker,
        EntityLinker,
        CausalLinker,
        SegmentType,
        Segment
    )

    sample_embedding = [0.1] * 384
    def mock_embed(text):
        return [0.1 + hash(text) % 100 / 1000] * 384

    def test_event_segmenter():
        segmenter = EventSegmenter()
        segments = segmenter.segment("First sentence. Second sentence. Third sentence.")
        assert_true(len(segments) >= 1, "Should produce segments")
    runner.run_test("EventSegmenter basic", test_event_segmenter)

    def test_segmenter_paragraph():
        segmenter = EventSegmenter()
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        segments = segmenter.segment(text)
        assert_true(len(segments) >= 2, "Should segment by paragraph")
    runner.run_test("EventSegmenter paragraphs", test_segmenter_paragraph)

    def test_semantic_linker():
        graphs = MagmaRelationGraphs()
        linker = SemanticLinker(graphs)  # No embedding_fn param
        # Add a node first
        graphs.semantic.add_concept("existing concept", sample_embedding)
        segment = Segment(id="seg-test", content="new related concept", segment_type=SegmentType.SENTENCE, start_pos=0, end_pos=19)
        result = linker.link_segment(segment, embedding=sample_embedding)  # link_segment not link
        # May or may not create edges depending on similarity
        assert_is_not_none(result)
    runner.run_test("SemanticLinker", test_semantic_linker)

    def test_temporal_linker():
        graphs = MagmaRelationGraphs()
        linker = TemporalLinker(graphs)
        from datetime import datetime
        segment = Segment(id="seg-test", content="This happened yesterday", segment_type=SegmentType.SENTENCE, start_pos=0, end_pos=22)
        result = linker.link_segment(segment, timestamp=datetime.utcnow())  # link_segment not link
        # Creates temporal node
        assert_is_not_none(result)
    runner.run_test("TemporalLinker", test_temporal_linker)

    def test_entity_linker():
        graphs = MagmaRelationGraphs()
        linker = EntityLinker(graphs)
        segment = Segment(id="seg-test", content="John Smith met with Microsoft", segment_type=SegmentType.SENTENCE, start_pos=0, end_pos=30, entities=["John Smith", "Microsoft"])
        result = linker.link_entities(segment)  # link_entities not link
        # Should create entity nodes
        assert_is_not_none(result)
    runner.run_test("EntityLinker", test_entity_linker)

    def test_causal_linker():
        graphs = MagmaRelationGraphs()
        linker = CausalLinker(graphs)
        segment = Segment(id="seg-test", content="Rain causes flooding", segment_type=SegmentType.SENTENCE, start_pos=0, end_pos=20)
        edges = linker.link_causal_relations(segment)  # link_causal_relations not link
        # Should detect causal relationship
        assert_true(len(edges) >= 1, "Should detect causal pattern")
    runner.run_test("CausalLinker basic", test_causal_linker)

    def test_causal_linker_leads_to():
        graphs = MagmaRelationGraphs()
        linker = CausalLinker(graphs)
        segment = Segment(id="seg-test2", content="Smoking leads to lung cancer", segment_type=SegmentType.SENTENCE, start_pos=0, end_pos=28)
        edges = linker.link_causal_relations(segment)
        assert_true(len(edges) >= 1, "Should detect 'leads to' pattern")
    runner.run_test("CausalLinker leads_to", test_causal_linker_leads_to)

    def test_pipeline_ingest():
        graphs = MagmaRelationGraphs()
        pipeline = SynapticIngestionPipeline(graphs, embedding_fn=mock_embed)
        result = pipeline.ingest("Machine learning causes better predictions. This enables automation.")
        assert_is_not_none(result)
        assert_true(len(result.segments) >= 1, "Should create segments")  # len(segments) not segments_created
    runner.run_test("SynapticIngestionPipeline", test_pipeline_ingest)

    def test_pipeline_with_genesis_key():
        graphs = MagmaRelationGraphs()
        pipeline = SynapticIngestionPipeline(graphs, embedding_fn=mock_embed)
        result = pipeline.ingest("Test content", genesis_key_id="GK-TEST123")
        assert_equal(result.genesis_key_id, "GK-TEST123")
    runner.run_test("Pipeline with genesis key", test_pipeline_with_genesis_key)


# =============================================================================
# TEST: Async Consolidation
# =============================================================================

def test_async_consolidation():
    """Test async consolidation components."""
    print("\n[TEST SUITE] Async Consolidation")
    print("-" * 40)

    from cognitive.magma.relation_graphs import MagmaRelationGraphs
    from cognitive.magma.async_consolidation import (
        AsyncOperationQueue,
        NeighborRetriever,
        ContextSynthesizer,
        ConsolidationWorker,
        OperationType,
        OperationPriority
    )
    from cognitive.magma.rrf_fusion import RetrievalResult

    sample_embedding = [0.1] * 384

    def test_operation_queue():
        queue = AsyncOperationQueue()
        queue.enqueue(OperationType.LINK, {"content": "test"}, OperationPriority.HIGH)  # LINK not LINK_SEMANTIC
        queue.enqueue(OperationType.INGEST, {"content": "test2"}, OperationPriority.LOW)  # INGEST not LINK_TEMPORAL
        sizes = queue.get_queue_sizes()
        total = sum(sizes.values())
        assert_true(total >= 2, "Should have 2 operations queued")
    runner.run_test("AsyncOperationQueue enqueue", test_operation_queue)

    def test_queue_dequeue():
        queue = AsyncOperationQueue()
        queue.enqueue(OperationType.LINK, {"id": 1}, OperationPriority.LOW)
        queue.enqueue(OperationType.CONSOLIDATE, {"id": 2}, OperationPriority.HIGH)
        # High priority should come first
        op = queue.dequeue()
        assert_equal(op.priority, OperationPriority.HIGH)
    runner.run_test("AsyncOperationQueue priority", test_queue_dequeue)

    def test_neighbor_retriever():
        graphs = MagmaRelationGraphs()
        n1 = graphs.semantic.add_concept("center", sample_embedding)
        n2 = graphs.semantic.add_concept("neighbor", [0.11] * 384)

        retriever = NeighborRetriever(graphs)
        neighbors = retriever.get_neighbors(n1, "semantic", max_neighbors=10)  # max_neighbors not max_depth
        assert_is_not_none(neighbors)
    runner.run_test("NeighborRetriever", test_neighbor_retriever)

    def test_context_synthesizer():
        synthesizer = ContextSynthesizer()
        results = [
            RetrievalResult(id="r1", content="First piece of content", score=0.9, rank=1, source="semantic", metadata={}),
            RetrievalResult(id="r2", content="Second piece of content", score=0.8, rank=2, source="temporal", metadata={}),
        ]
        context = synthesizer.synthesize(results, "test query")
        assert_in("First piece", context)
        assert_in("Second piece", context)
    runner.run_test("ContextSynthesizer basic", test_context_synthesizer)

    def test_context_synthesizer_with_query():
        synthesizer = ContextSynthesizer()
        results = [
            RetrievalResult(id="r1", content="Content about Python", score=0.9, rank=1, source="semantic", metadata={}),
        ]
        context = synthesizer.synthesize(results, "What is Python?")
        assert_in("Query:", context)
        assert_in("Python", context)
    runner.run_test("ContextSynthesizer with query", test_context_synthesizer_with_query)

    def test_consolidation_worker_init():
        graphs = MagmaRelationGraphs()
        queue = AsyncOperationQueue()
        worker = ConsolidationWorker(graphs, queue)
        assert_false(worker._running, "Worker should not start automatically")  # _running not running
    runner.run_test("ConsolidationWorker init", test_consolidation_worker_init)


# =============================================================================
# TEST: Causal Inference
# =============================================================================

def test_causal_inference():
    """Test causal inference components."""
    print("\n[TEST SUITE] Causal Inference")
    print("-" * 40)

    from cognitive.magma.relation_graphs import MagmaRelationGraphs, GraphNode, RelationType
    from cognitive.magma.causal_inference import (
        LLMCausalInferencer,
        CausalPatternDetector,
        CausalRelationStrength
    )

    def test_pattern_detector_causes():
        detector = CausalPatternDetector()
        claims = detector.detect("Rain causes flooding")
        assert_true(len(claims) >= 1, "Should detect 'causes' pattern")
        assert_equal(claims[0].relation_type, RelationType.CAUSAL_CAUSES)
    runner.run_test("CausalPatternDetector causes", test_pattern_detector_causes)

    def test_pattern_detector_leads_to():
        detector = CausalPatternDetector()
        claims = detector.detect("Smoking leads to cancer")
        assert_true(len(claims) >= 1, "Should detect 'leads to' pattern")
    runner.run_test("CausalPatternDetector leads_to", test_pattern_detector_leads_to)

    def test_pattern_detector_prevents():
        detector = CausalPatternDetector()
        claims = detector.detect("Vaccination prevents disease")
        assert_true(len(claims) >= 1, "Should detect 'prevents' pattern")
        assert_equal(claims[0].relation_type, RelationType.CAUSAL_PREVENTS)
    runner.run_test("CausalPatternDetector prevents", test_pattern_detector_prevents)

    def test_pattern_detector_enables():
        detector = CausalPatternDetector()
        claims = detector.detect("Education enables success")
        assert_true(len(claims) >= 1, "Should detect 'enables' pattern")
    runner.run_test("CausalPatternDetector enables", test_pattern_detector_enables)

    def test_pattern_detector_strength():
        detector = CausalPatternDetector()
        # Strong causation
        strong = detector.detect("Gravity directly causes objects to fall")
        assert_true(len(strong) >= 1)
        assert_equal(strong[0].strength, CausalRelationStrength.STRONG)  # "directly causes" is STRONG
        # Weak/correlation (is associated with)
        weak = detector.detect("Stress is associated with headaches")
        assert_true(len(weak) >= 1)
        assert_equal(weak[0].strength, CausalRelationStrength.WEAK)  # "is associated with" is WEAK
    runner.run_test("CausalPatternDetector strength", test_pattern_detector_strength)

    def test_llm_inferencer_init():
        graphs = MagmaRelationGraphs()
        inferencer = LLMCausalInferencer(graphs)
        assert_is_not_none(inferencer.pattern_detector)
    runner.run_test("LLMCausalInferencer init", test_llm_inferencer_init)

    def test_llm_inferencer_infer():
        graphs = MagmaRelationGraphs()
        inferencer = LLMCausalInferencer(graphs)
        claims = inferencer.infer_causation("Exercise causes better health")
        assert_true(len(claims) >= 1, "Should infer causal claims")
    runner.run_test("LLMCausalInferencer infer", test_llm_inferencer_infer)

    def test_llm_inferencer_store():
        graphs = MagmaRelationGraphs()
        inferencer = LLMCausalInferencer(graphs)
        claims = inferencer.infer_causation("Rain causes flooding")
        edge_ids = inferencer.store_claims(claims)
        assert_true(len(edge_ids) >= 1, "Should store claims in graph")
        assert_true(len(graphs.causal.edges) >= 1, "Graph should have edges")
    runner.run_test("LLMCausalInferencer store", test_llm_inferencer_store)

    def test_llm_inferencer_trace_chain():
        graphs = MagmaRelationGraphs()
        inferencer = LLMCausalInferencer(graphs)
        # Store a chain
        inferencer.store_claims(inferencer.infer_causation("Rain causes flooding"))
        inferencer.store_claims(inferencer.infer_causation("Flooding causes damage"))
        chains = inferencer.trace_causal_chain("rain")
        # May or may not find complete chain depending on linking
        assert_is_not_none(chains)
    runner.run_test("LLMCausalInferencer trace", test_llm_inferencer_trace_chain)

    def test_llm_inferencer_explain():
        graphs = MagmaRelationGraphs()
        inferencer = LLMCausalInferencer(graphs)
        inferencer.store_claims(inferencer.infer_causation("Study causes learning"))
        explanation = inferencer.explain_causation("study", "learning")
        assert_is_not_none(explanation)
        assert_is_not_none(explanation.explanation)
    runner.run_test("LLMCausalInferencer explain", test_llm_inferencer_explain)


# =============================================================================
# TEST: MagmaMemory Integration
# =============================================================================

def test_magma_memory():
    """Test MagmaMemory unified interface."""
    print("\n[TEST SUITE] MagmaMemory Integration")
    print("-" * 40)

    from cognitive.magma import MagmaMemory

    def mock_embed(text):
        return [0.1 + hash(text) % 100 / 1000] * 384

    def mock_llm(prompt):
        return f"[LLM Response to: {prompt[:30]}...]"

    def test_magma_init():
        magma = MagmaMemory(embedding_fn=mock_embed, llm_fn=mock_llm)
        assert_is_not_none(magma.graphs)
        assert_is_not_none(magma.router)
        assert_is_not_none(magma.fusion)
        assert_is_not_none(magma.retriever)
        assert_is_not_none(magma.ingestion)
    runner.run_test("MagmaMemory init", test_magma_init)

    def test_magma_ingest():
        magma = MagmaMemory(embedding_fn=mock_embed)
        result = magma.ingest("Machine learning causes better predictions")
        assert_is_not_none(result)
        assert_true(len(result.segments) >= 1, "Should create segments")  # len(segments) not segments_created
    runner.run_test("MagmaMemory ingest", test_magma_ingest)

    def test_magma_ingest_with_genesis():
        magma = MagmaMemory(embedding_fn=mock_embed)
        result = magma.ingest("Test content", genesis_key_id="GK-TEST123")
        assert_equal(result.genesis_key_id, "GK-TEST123")
    runner.run_test("MagmaMemory ingest with genesis", test_magma_ingest_with_genesis)

    def test_magma_query():
        magma = MagmaMemory(embedding_fn=mock_embed)
        magma.ingest("Python is a programming language")
        magma.ingest("Machine learning uses algorithms")
        results = magma.query("What is Python?")
        assert_is_not_none(results)
    runner.run_test("MagmaMemory query", test_magma_query)

    def test_magma_get_context():
        magma = MagmaMemory(embedding_fn=mock_embed)
        magma.ingest("Python programming language")
        results = magma.query("Python")
        context = magma.get_context(results, "What is Python?")
        assert_is_not_none(context)
        assert_true(isinstance(context, str))
    runner.run_test("MagmaMemory get_context", test_magma_get_context)

    def test_magma_infer_causation():
        magma = MagmaMemory(embedding_fn=mock_embed)
        claims = magma.infer_causation("Rain causes flooding")
        assert_true(len(claims) >= 1, "Should find causal claims")
    runner.run_test("MagmaMemory infer_causation", test_magma_infer_causation)

    def test_magma_explain():
        magma = MagmaMemory(embedding_fn=mock_embed)
        magma.ingest("Rain causes wet ground")
        explanation = magma.explain("rain", "wet ground")
        assert_is_not_none(explanation)
    runner.run_test("MagmaMemory explain", test_magma_explain)

    def test_magma_get_stats():
        magma = MagmaMemory(embedding_fn=mock_embed)
        magma.ingest("Test content for stats")
        stats = magma.get_stats()
        assert_in("graphs", stats)
        assert_in("queue", stats)
    runner.run_test("MagmaMemory get_stats", test_magma_get_stats)

    def test_magma_full_workflow():
        """Test complete workflow: ingest -> query -> context."""
        magma = MagmaMemory(embedding_fn=mock_embed)

        # Ingest knowledge
        magma.ingest("Python is a versatile programming language")
        magma.ingest("Machine learning enables intelligent systems")
        magma.ingest("Deep learning causes breakthrough in AI")

        # Query
        results = magma.query("What enables AI?")

        # Get context
        context = magma.get_context(results, "What enables AI?")

        # Infer causation
        claims = magma.infer_causation("Training causes model improvement")

        # All should work without error
        assert_is_not_none(context)
    runner.run_test("MagmaMemory full workflow", test_magma_full_workflow)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run all tests."""
    print("=" * 60)
    print("MAGMA MEMORY SYSTEM - FULL TEST SUITE")
    print("=" * 60)

    start_time = datetime.now()

    try:
        test_relation_graphs()
        test_intent_router()
        test_rrf_fusion()
        test_topological_retrieval()
        test_synaptic_ingestion()
        test_async_consolidation()
        test_causal_inference()
        test_magma_memory()
    except ImportError as e:
        print(f"\n[IMPORT ERROR] {e}")
        print("Make sure you're running from the backend directory")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] {e}")
        traceback.print_exc()
        return False

    elapsed = (datetime.now() - start_time).total_seconds()

    success = runner.print_summary()
    print(f"\nCompleted in {elapsed:.2f}s")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
