"""
Tests for backend.cognitive.magma — real logic, no external deps.
"""
import pytest
from datetime import datetime, timedelta

from cognitive.magma.relation_graphs import (
    BaseRelationGraph, SemanticGraph, TemporalGraph, CausalGraph,
    EntityGraph, MagmaRelationGraphs, GraphNode, GraphEdge, RelationType,
)
from cognitive.magma.intent_router import (
    IntentClassifier, AnchorIdentifier, GraphSelector, RetrievalPolicySelector,
    IntentAwareRouter, QueryIntent, AnchorType, Anchor,
)
from cognitive.magma.rrf_fusion import (
    RRFFusion, WeightedRRFFusion, CombSUMFusion, CombMNZFusion,
    InterleavingFusion, MagmaFusion, RetrievalResult, FusionMethod,
)
from cognitive.magma.causal_inference import (
    CausalPatternDetector, LLMCausalInferencer, CausalRelationStrength,
)


# ═══════════════════════════════════════════════════════════════════════
# Relation Graphs
# ═══════════════════════════════════════════════════════════════════════

class TestBaseRelationGraph:
    def test_add_node_and_get(self):
        g = BaseRelationGraph("test")
        n = GraphNode(id="n1", node_type="concept", content="hello")
        g.add_node(n)
        assert g.get_node("n1") is n

    def test_add_edge_validates_nodes(self):
        g = BaseRelationGraph("test")
        g.add_node(GraphNode(id="a", node_type="c", content="A"))
        edge = GraphEdge(id="e1", source_id="a", target_id="b",
                         relation_type=RelationType.SEMANTIC_SIMILAR)
        with pytest.raises(ValueError, match="Target node"):
            g.add_edge(edge)

    def test_get_neighbors_outgoing(self):
        g = BaseRelationGraph("test")
        g.add_node(GraphNode(id="a", node_type="c", content="A"))
        g.add_node(GraphNode(id="b", node_type="c", content="B"))
        g.add_edge(GraphEdge(id="e1", source_id="a", target_id="b",
                             relation_type=RelationType.SEMANTIC_SIMILAR))
        nbrs = g.get_neighbors("a", direction="outgoing")
        assert len(nbrs) == 1 and nbrs[0][0].id == "b"

    def test_get_neighbors_incoming(self):
        g = BaseRelationGraph("test")
        g.add_node(GraphNode(id="a", node_type="c", content="A"))
        g.add_node(GraphNode(id="b", node_type="c", content="B"))
        g.add_edge(GraphEdge(id="e1", source_id="a", target_id="b",
                             relation_type=RelationType.SEMANTIC_SIMILAR))
        nbrs = g.get_neighbors("b", direction="incoming")
        assert len(nbrs) == 1 and nbrs[0][0].id == "a"

    def test_find_path_same_node(self):
        g = BaseRelationGraph("test")
        g.add_node(GraphNode(id="a", node_type="c", content="A"))
        path = g.find_path("a", "a")
        assert len(path) == 1 and path[0][0].id == "a"

    def test_find_path_two_hops(self):
        g = BaseRelationGraph("test")
        for nid in ("a", "b", "c"):
            g.add_node(GraphNode(id=nid, node_type="c", content=nid))
        g.add_edge(GraphEdge(id="e1", source_id="a", target_id="b",
                             relation_type=RelationType.SEMANTIC_RELATED))
        g.add_edge(GraphEdge(id="e2", source_id="b", target_id="c",
                             relation_type=RelationType.SEMANTIC_RELATED))
        path = g.find_path("a", "c")
        assert path is not None
        assert path[-1][0].id == "c"

    def test_node_importance_isolated(self):
        g = BaseRelationGraph("test")
        g.add_node(GraphNode(id="a", node_type="c", content="A", trust_score=0.8))
        imp = g.calculate_node_importance("a")
        # degree_centrality=0, trust=0.8, avg_weight=0 → 0.4*0 + 0.4*0.8 + 0.2*0
        assert abs(imp - 0.32) < 1e-6


class TestSemanticGraph:
    def test_auto_link_similar(self):
        sg = SemanticGraph()
        sg.similarity_threshold = 0.9
        sg.add_concept("cat", embedding=[1, 0, 0], metadata={})
        sg.add_concept("kitten", embedding=[0.99, 0.1, 0], metadata={})
        # Cosine similarity ~0.995 → should link
        assert len(sg.edges) >= 1

    def test_no_link_dissimilar(self):
        sg = SemanticGraph()
        sg.similarity_threshold = 0.9
        sg.add_concept("cat", embedding=[1, 0, 0], metadata={})
        sg.add_concept("car", embedding=[0, 0, 1], metadata={})
        assert len(sg.edges) == 0


class TestTemporalGraph:
    def test_concurrent_events(self):
        tg = TemporalGraph()
        now = datetime(2025, 1, 1, 12, 0, 0)
        tg.add_event("event A", now)
        tg.add_event("event B", now + timedelta(seconds=30))  # within 60s
        assert any(e.relation_type == RelationType.TEMPORAL_CONCURRENT
                    for e in tg.edges.values())

    def test_events_in_range(self):
        tg = TemporalGraph()
        t1 = datetime(2025, 1, 1, 10, 0, 0)
        t2 = datetime(2025, 1, 1, 12, 0, 0)
        t3 = datetime(2025, 1, 1, 14, 0, 0)
        tg.add_event("morning", t1)
        tg.add_event("noon", t2)
        tg.add_event("afternoon", t3)
        found = tg.get_events_in_range(
            datetime(2025, 1, 1, 11, 0, 0),
            datetime(2025, 1, 1, 13, 0, 0)
        )
        assert len(found) == 1 and "noon" in found[0].content


class TestCausalGraph:
    def test_add_causal_link(self):
        cg = CausalGraph()
        cg.add_node(GraphNode(id="c1", node_type="cause", content="rain"))
        cg.add_node(GraphNode(id="e1", node_type="effect", content="flood"))
        eid = cg.add_causal_link("c1", "e1", RelationType.CAUSAL_CAUSES, 0.9)
        assert eid in cg.edges

    def test_invalid_relation_rejected(self):
        cg = CausalGraph()
        cg.add_node(GraphNode(id="c1", node_type="cause", content="rain"))
        cg.add_node(GraphNode(id="e1", node_type="effect", content="flood"))
        with pytest.raises(ValueError, match="Invalid causal relation"):
            cg.add_causal_link("c1", "e1", RelationType.SEMANTIC_SIMILAR)

    def test_get_effects(self):
        cg = CausalGraph()
        cg.add_node(GraphNode(id="c1", node_type="cause", content="rain"))
        cg.add_node(GraphNode(id="e1", node_type="effect", content="flood"))
        cg.add_causal_link("c1", "e1", RelationType.CAUSAL_CAUSES, 0.8)
        effects = cg.get_effects("c1")
        assert len(effects) == 1 and effects[0][0].content == "flood"


class TestEntityGraph:
    def test_add_and_link(self):
        eg = EntityGraph()
        id1 = eg.add_entity("Python", "language")
        id2 = eg.add_entity("Django", "framework")
        eg.link_entities(id1, id2, RelationType.ENTITY_RELATED_TO)
        assert len(eg.edges) == 1

    def test_co_occurrence_increments(self):
        eg = EntityGraph()
        id1 = eg.add_entity("Alice", "person")
        id2 = eg.add_entity("Bob", "person")
        eg.record_co_occurrence(id1, id2, "meeting 1")
        eg.record_co_occurrence(id1, id2, "meeting 2")
        edge = list(eg.edges.values())[0]
        assert edge.weight > 0.5  # initial 0.5 + increment


class TestMagmaRelationGraphs:
    def test_unified_stats(self):
        mrg = MagmaRelationGraphs()
        stats = mrg.get_unified_stats()
        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0

    def test_get_all_graphs_keys(self):
        mrg = MagmaRelationGraphs()
        keys = set(mrg.get_all_graphs().keys())
        assert keys == {"semantic", "temporal", "causal", "entity"}


# ═══════════════════════════════════════════════════════════════════════
# Intent Router
# ═══════════════════════════════════════════════════════════════════════

class TestIntentClassifier:
    def test_definition_intent(self):
        ic = IntentClassifier()
        intent, _, _ = ic.classify("What is machine learning?")
        assert intent == QueryIntent.DEFINITION

    def test_cause_intent(self):
        ic = IntentClassifier()
        intent, _, _ = ic.classify("What causes database failures?")
        assert intent in (QueryIntent.CAUSE, QueryIntent.REASON)

    def test_unknown_defaults_explore(self):
        ic = IntentClassifier()
        intent, _, conf = ic.classify("xyzzy foobar blah")
        assert intent == QueryIntent.EXPLORE
        assert conf == 0.3


class TestAnchorIdentifier:
    def test_extracts_entity(self):
        ai = AnchorIdentifier()
        anchors = ai.identify("Tell me about Python programming")
        entity_texts = [a.text for a in anchors if a.anchor_type == AnchorType.ENTITY]
        assert "Python" in entity_texts

    def test_extracts_time(self):
        ai = AnchorIdentifier()
        anchors = ai.identify("What happened yesterday?")
        time_anchors = [a for a in anchors if a.anchor_type == AnchorType.TIME]
        assert len(time_anchors) >= 1

    def test_extracts_quoted(self):
        ai = AnchorIdentifier()
        anchors = ai.identify('Find documents about "neural networks"')
        concept_anchors = [a for a in anchors if a.anchor_type == AnchorType.CONCEPT]
        assert any("neural networks" in a.text for a in concept_anchors)


class TestGraphSelector:
    def test_definition_selects_semantic(self):
        gs = GraphSelector()
        graphs = gs.select(QueryIntent.DEFINITION, [])
        assert "semantic" in graphs

    def test_cause_selects_causal(self):
        gs = GraphSelector()
        graphs = gs.select(QueryIntent.CAUSE, [])
        assert "causal" in graphs

    def test_time_anchor_adds_temporal(self):
        gs = GraphSelector()
        anchors = [Anchor("2025", AnchorType.TIME, 0, 4)]
        graphs = gs.select(QueryIntent.DEFINITION, anchors)
        assert "temporal" in graphs


class TestRetrievalPolicySelector:
    def test_temporal_intent_returns_temporal_window(self):
        ps = RetrievalPolicySelector()
        assert ps.select(QueryIntent.TEMPORAL_SEQUENCE, [], []) == "temporal_window"

    def test_cause_intent_returns_causal_chain(self):
        ps = RetrievalPolicySelector()
        assert ps.select(QueryIntent.CAUSE, [], []) == "causal_chain"


class TestIntentAwareRouter:
    def test_analyze_returns_query_analysis(self):
        router = IntentAwareRouter()
        analysis = router.analyze_query("What is Python?")
        assert analysis.primary_intent == QueryIntent.DEFINITION
        assert "semantic" in analysis.target_graphs

    def test_route_returns_dict(self):
        router = IntentAwareRouter()
        result = router.route("Compare Java and Python")
        assert result["intent"] == "comparison"
        assert isinstance(result["anchors"], list)


# ═══════════════════════════════════════════════════════════════════════
# RRF Fusion
# ═══════════════════════════════════════════════════════════════════════

def _make_results(source, ids_scores):
    return [
        RetrievalResult(id=id_, content=f"doc {id_}", score=s, rank=r + 1, source=source)
        for r, (id_, s) in enumerate(ids_scores)
    ]


class TestRRFFusion:
    def test_single_source(self):
        rrf = RRFFusion(k=60)
        results = rrf.fuse({"s1": _make_results("s1", [("a", 0.9), ("b", 0.7)])})
        assert len(results) == 2
        assert results[0].id == "a"  # rank 1 → higher RRF

    def test_multi_source_boosts_overlap(self):
        rrf = RRFFusion(k=60)
        results = rrf.fuse({
            "s1": _make_results("s1", [("a", 0.9), ("b", 0.7)]),
            "s2": _make_results("s2", [("b", 0.8), ("c", 0.6)]),
        })
        # "b" appears in both sources → boosted
        b_result = next(r for r in results if r.id == "b")
        a_result = next(r for r in results if r.id == "a")
        assert b_result.rrf_score > a_result.rrf_score

    def test_rrf_formula_exact(self):
        rrf = RRFFusion(k=60)
        results = rrf.fuse({"s1": _make_results("s1", [("x", 1.0)])})
        expected = 1.0 / (60 + 1)
        assert abs(results[0].rrf_score - expected) < 1e-9


class TestWeightedRRFFusion:
    def test_weight_amplifies(self):
        wrrf = WeightedRRFFusion(k=60)
        r1 = _make_results("s1", [("a", 0.9)])
        r2 = _make_results("s2", [("b", 0.9)])
        # s2 weighted 10x
        results = wrrf.fuse({"s1": r1, "s2": r2}, weights={"s1": 1.0, "s2": 10.0})
        assert results[0].id == "b"


class TestCombMNZFusion:
    def test_multi_source_multiplies_by_count(self):
        fusion = CombMNZFusion()
        results = fusion.fuse({
            "s1": _make_results("s1", [("a", 0.9), ("b", 0.5)]),
            "s2": _make_results("s2", [("a", 0.8), ("c", 0.4)]),
        })
        a_result = next(r for r in results if r.id == "a")
        b_result = next(r for r in results if r.id == "b")
        # "a" appears in 2 sources → multiplied by 2; "b" in 1 → multiplied by 1
        assert a_result.rrf_score > b_result.rrf_score


class TestInterleavingFusion:
    def test_round_robin_order(self):
        fusion = InterleavingFusion()
        results = fusion.fuse({
            "s1": _make_results("s1", [("a", 0.9), ("c", 0.7)]),
            "s2": _make_results("s2", [("b", 0.8), ("d", 0.6)]),
        })
        ids = [r.id for r in results]
        assert ids[0] == "a" and ids[1] == "b"

    def test_deduplication(self):
        fusion = InterleavingFusion()
        results = fusion.fuse({
            "s1": _make_results("s1", [("a", 0.9)]),
            "s2": _make_results("s2", [("a", 0.8)]),
        })
        assert len(results) == 1


class TestMagmaFusion:
    def test_fuse_with_limit(self):
        mf = MagmaFusion(method=FusionMethod.RRF)
        results = mf.fuse_with_limit({
            "s1": _make_results("s1", [("a", 0.9), ("b", 0.8), ("c", 0.7)]),
        }, limit=2)
        assert len(results) == 2

    def test_create_retrieval_results_helper(self):
        items = [{"id": "d1", "content": "hello", "score": 0.9, "extra": "yes"}]
        rrs = MagmaFusion.create_retrieval_results(items, "test")
        assert rrs[0].id == "d1" and rrs[0].rank == 1
        assert rrs[0].metadata == {"extra": "yes"}


# ═══════════════════════════════════════════════════════════════════════
# Causal Inference
# ═══════════════════════════════════════════════════════════════════════

class TestCausalPatternDetector:
    def test_detects_causes(self):
        cpd = CausalPatternDetector()
        claims = cpd.detect("Smoking causes lung cancer")
        assert len(claims) >= 1
        assert claims[0].cause == "smoking"
        assert "lung cancer" in claims[0].effect

    def test_detects_prevents(self):
        cpd = CausalPatternDetector()
        claims = cpd.detect("Vaccines prevent disease")
        assert any(c.relation_type == RelationType.CAUSAL_PREVENTS for c in claims)

    def test_deduplicates(self):
        cpd = CausalPatternDetector()
        # Both "causes" and "leads to" patterns match same cause/effect pair
        claims = cpd.detect("Smoking causes cancer. Smoking leads to cancer.")
        causes = [c for c in claims if c.cause == "smoking" and c.effect == "cancer"]
        # Dedup key is (cause, effect) so only one survives
        assert len(causes) == 1

    def test_skips_short_matches(self):
        cpd = CausalPatternDetector()
        claims = cpd.detect("It causes an effect")
        # "it" is only 2 chars → should be skipped
        assert not any(c.cause == "it" for c in claims)


class TestLLMCausalInferencer:
    def test_infer_without_llm(self):
        graphs = MagmaRelationGraphs()
        inf = LLMCausalInferencer(graphs)
        claims = inf.infer_causation("Rain causes flooding")
        assert len(claims) >= 1

    def test_store_and_trace(self):
        graphs = MagmaRelationGraphs()
        inf = LLMCausalInferencer(graphs)
        claims = inf.infer_causation("Deforestation causes erosion")
        inf.store_claims(claims)
        # Now nodes should exist in causal graph
        assert len(graphs.causal.nodes) >= 2
        assert len(graphs.causal.edges) >= 1

    def test_explain_with_chain(self):
        graphs = MagmaRelationGraphs()
        inf = LLMCausalInferencer(graphs)
        claims = inf.infer_causation("Drought causes famine")
        inf.store_claims(claims)
        explanation = inf.explain_causation("drought", "famine")
        assert "drought" in explanation.cause
        assert "famine" in explanation.effect

    def test_validate_unsupported_claim(self):
        graphs = MagmaRelationGraphs()
        inf = LLMCausalInferencer(graphs)
        from cognitive.magma.causal_inference import CausalClaim
        claim = CausalClaim(
            id="c1", cause="aliens", effect="weather",
            relation_type=RelationType.CAUSAL_CAUSES,
            strength=CausalRelationStrength.WEAK,
            confidence=0.3, evidence="aliens cause weather",
            source_text="aliens cause weather"
        )
        valid, conf, reason = inf.validate_claim(claim)
        assert valid is False
        assert "No supporting evidence" in reason
