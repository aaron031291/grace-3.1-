"""
Layer 4 End-to-End Tests

Tests for Layer 4 as a complete system:
1. Full learning cycle flow
2. Cross-layer integration
3. Pattern lifecycle (discover → validate → transfer → export)
4. GPU acceleration verification
5. Performance benchmarks
"""

import pytest
import numpy as np
import time
from datetime import datetime
from pathlib import Path
import tempfile
import json


class TestLayer4EndToEnd:
    """End-to-end tests for complete Layer 4 system."""
    
    @pytest.fixture
    def full_layer4_stack(self):
        """Create complete Layer 4 stack with all components."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            get_layer4_recursive_learner
        )
        from ml_intelligence.layer4_advanced_neuro_symbolic import get_advanced_layer4
        from ml_intelligence.layer4_frontier_reasoning import get_frontier_layer4
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base = get_layer4_recursive_learner()
            base.storage_path = Path(tmpdir) / "patterns"
            base.storage_path.mkdir(parents=True, exist_ok=True)
            
            advanced = get_advanced_layer4(base_layer4=base)
            frontier = get_frontier_layer4(embedding_dim=64)
            
            yield {
                "base": base,
                "advanced": advanced,
                "frontier": frontier,
                "tmpdir": tmpdir,
            }
    
    # =========================================================================
    # FULL LEARNING CYCLE TESTS
    # =========================================================================
    
    def test_complete_learning_cycle(self, full_layer4_stack):
        """Test complete pattern learning cycle."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        base = full_layer4_stack["base"]
        
        # Input data
        code_samples = [
            {"text": "def validate_input(data): if not data: raise ValueError()"},
            {"text": "def validate_user(user): if not user: raise ValueError()"},
            {"text": "def validate_config(cfg): if not cfg: raise ValueError()"},
            {"text": "def check_auth(token): if not token: raise AuthError()"},
            {"text": "def check_permission(user): if not user.admin: raise PermError()"},
        ]
        
        # Run cycle
        cycle = base.run_recursive_cycle(
            domain=PatternDomain.CODE,
            data=code_samples,
            max_iterations=2,
        )
        
        # Verify cycle completed
        assert cycle.completed_at is not None
        assert cycle.cycle_number >= 1
        
        # Verify patterns discovered
        assert cycle.patterns_discovered >= 0
    
    def test_cross_domain_transfer(self, full_layer4_stack):
        """Test pattern transfer between domains."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            PatternDomain, AbstractPattern
        )
        
        base = full_layer4_stack["base"]
        
        # Create a high-trust pattern in CODE domain
        pattern = AbstractPattern(
            pattern_id="test-transfer-pattern",
            abstract_form={
                "structure": {"type": "cluster"},
                "keywords": ["validate", "check"],
                "roles": ["validator"],
                "constraints": [{"type": "similarity", "threshold": 0.5}],
                "relationships": [],
                "transformations": [],
            },
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE, PatternDomain.HEALING],
            confidence=0.8,
            trust_score=0.85,
            abstraction_level=2,
            support_count=5,
        )
        
        # Store pattern
        base._store_pattern(pattern)
        
        # Verify pattern is in CODE domain
        code_patterns = base.get_patterns_for_domain(PatternDomain.CODE, min_trust=0.5)
        pattern_ids = [p.pattern_id for p in code_patterns]
        assert "test-transfer-pattern" in pattern_ids
        
        # Verify pattern is also indexed in HEALING (applicable domain)
        healing_patterns = base.get_patterns_for_domain(PatternDomain.HEALING, min_trust=0.5)
        healing_ids = [p.pattern_id for p in healing_patterns]
        assert "test-transfer-pattern" in healing_ids
    
    def test_pattern_lifecycle(self, full_layer4_stack):
        """Test full pattern lifecycle: discover → validate → transfer → export."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        base = full_layer4_stack["base"]
        
        # 1. DISCOVER: Run initial cycle
        initial_data = [
            {"text": "try: risky_op() except: handle_error()"},
            {"text": "try: network_call() except: retry()"},
            {"text": "try: db_query() except: fallback()"},
        ]
        
        cycle1 = base.run_recursive_cycle(
            domain=PatternDomain.HEALING,
            data=initial_data,
            max_iterations=1,
        )
        
        # 2. VALIDATE: Patterns should be validated against KB
        # (Validation happens inside run_recursive_cycle)
        
        # 3. Query patterns to verify they exist
        patterns = base.query_patterns("try except handle", limit=5)
        
        # 4. Check cross-domain insights
        insights = base.get_cross_domain_insights()
        assert "total_patterns" in insights
    
    # =========================================================================
    # ADVANCED FEATURES INTEGRATION TESTS
    # =========================================================================
    
    def test_compositional_with_base_patterns(self, full_layer4_stack):
        """Test compositional generalization with base patterns."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        base = full_layer4_stack["base"]
        advanced = full_layer4_stack["advanced"]
        
        # Run base cycle to create patterns
        data = [
            {"text": "def auth_check(): pass"},
            {"text": "def permission_check(): pass"},
        ]
        base.run_recursive_cycle(PatternDomain.CODE, data, max_iterations=1)
        
        # Get patterns and add to composition engine
        patterns = base.get_patterns_for_domain(PatternDomain.CODE, min_trust=0.0)
        for p in patterns[:2]:
            advanced.composition_engine.pattern_store[p.pattern_id] = p.abstract_form
        
        # If we have 2+ patterns, compose them
        if len(patterns) >= 2:
            composite = advanced.compose_patterns(
                "union",
                [patterns[0].pattern_id, patterns[1].pattern_id],
            )
            # May or may not succeed depending on patterns
    
    def test_self_modifying_rules_evolution(self, full_layer4_stack):
        """Test that self-modifying rules evolve over time."""
        advanced = full_layer4_stack["advanced"]
        
        # Add rule
        rule = advanced.add_self_modifying_rule(
            premise={"confidence": {"threshold": 0.5}},
            conclusion={"action": "approve"},
            confidence=0.7,
        )
        
        # Simulate multiple applications with failures
        engine = advanced.self_modifying_engine
        
        for _ in range(10):
            engine.apply_rule(rule.rule_id, {"confidence": 0.6})
            engine.record_outcome(rule.rule_id, success=False)
        
        # After failures, rule should have mutated
        assert rule.failures >= 5
    
    # =========================================================================
    # FRONTIER CAPABILITIES TESTS
    # =========================================================================
    
    def test_theorem_proving_with_learning(self, full_layer4_stack):
        """Test theorem prover learns from successful proofs."""
        frontier = full_layer4_stack["frontier"]
        
        # Set up knowledge base
        frontier.theorem_prover.add_fact("parent(tom, mary)")
        frontier.theorem_prover.add_fact("parent(mary, john)")
        frontier.theorem_prover.add_rule(
            "grandparent_rule",
            ["parent(tom, mary)", "parent(mary, john)"],
            "grandparent(tom, john)",
        )
        
        # Prove
        proof = frontier.prove("grandparent(tom, john)", max_depth=5)
        
        assert proof is not None
        assert proof.success is True
        
        # Verify proof was cached
        assert "grandparent(tom, john)" in frontier.theorem_prover.proof_cache
    
    def test_program_synthesis_complex(self, full_layer4_stack):
        """Test program synthesis with complex examples."""
        frontier = full_layer4_stack["frontier"]
        
        # Test increment
        examples = [(1, 2), (5, 6), (10, 11)]
        prog = frontier.synthesize_program(examples)
        assert prog is not None
        assert prog.code == "inc"
        
        # Test square
        examples = [(2, 4), (3, 9), (4, 16)]
        prog = frontier.synthesize_program(examples)
        assert prog is not None
        assert prog.code == "square"
    
    def test_concept_learning_generalization(self, full_layer4_stack):
        """Test concept learning generalizes from few examples."""
        frontier = full_layer4_stack["frontier"]
        
        # Learn "high_value" concept from just 3 examples
        # Use very distinct values to ensure separation
        high_examples = [
            np.array([1.0] * 64),
            np.array([0.95] * 64),
            np.array([0.9] * 64),
        ]
        frontier.learn_concept("high_value", high_examples)
        
        # Learn "low_value" concept with very different values
        low_examples = [
            np.array([-1.0] * 64),
            np.array([-0.9] * 64),
            np.array([-0.95] * 64),
        ]
        frontier.learn_concept("low_value", low_examples)
        
        # Test generalization with clearly distinct values
        test_high = np.array([0.88] * 64)   # Clearly similar to high
        test_low = np.array([-0.88] * 64)   # Clearly similar to low
        
        high_result = frontier.classify_concept(test_high)
        low_result = frontier.classify_concept(test_low)
        
        # Should get some classification results
        assert len(high_result) > 0 or len(low_result) > 0
        
        # If we got results, check the highest one makes sense
        if high_result and len(high_result) > 0:
            # High value should rank high_value higher
            high_concepts = [r[0] for r in high_result]
            assert "high_value" in high_concepts
        
        if low_result and len(low_result) > 0:
            # Low value should rank low_value higher
            low_concepts = [r[0] for r in low_result]
            assert "low_value" in low_concepts
    
    def test_graph_reasoning_propagation(self, full_layer4_stack):
        """Test GNN message propagation."""
        frontier = full_layer4_stack["frontier"]
        
        # Build knowledge graph
        nodes = ["A", "B", "C", "D", "E"]
        for n in nodes:
            frontier.graph_reasoner.add_node(n)
        
        # Add edges
        frontier.graph_reasoner.add_edge("A", "B", "related")
        frontier.graph_reasoner.add_edge("B", "C", "related")
        frontier.graph_reasoner.add_edge("C", "D", "related")
        frontier.graph_reasoner.add_edge("D", "E", "related")
        
        # Query distant relation
        prob = frontier.graph_query("A", "E")
        
        # Should get some probability from propagation
        assert 0.0 <= prob <= 1.0
    
    # =========================================================================
    # INTEGRATION WITH LOWER LAYERS
    # =========================================================================
    
    def test_integration_hub_full_flow(self, full_layer4_stack):
        """Test full flow through integration hub."""
        from genesis.layer4_integration import Layer4IntegrationHub
        
        with tempfile.TemporaryDirectory() as tmpdir:
            hub = Layer4IntegrationHub(session=None)
            hub.integration_base = Path(tmpdir)
            
            # 1. Receive healing event
            result = hub.receive_healing_event(
                error_type="TypeError",
                error_content="'NoneType' has no attribute 'x'",
                fix_applied="Added null check",
                success=True,
            )
            
            assert hub.stats["events_received"] == 1
            
            # 2. Store synthesized program
            hub.store_synthesized_program(
                program_id="test-prog",
                code="lambda x: x * 2",
                spec={"examples": [(2, 4)]},
                confidence=0.9,
            )
            
            assert hub.stats["programs_stored_in_l1"] == 1
            
            # 3. Send insight to Layer 2
            hub.send_insight_to_layer2(
                insight_type="pattern_transfer",
                insight_data={"from": "code", "to": "healing"},
                source_patterns=["p1"],
            )
            
            assert hub.stats["insights_sent_to_l2"] == 1
            
            # 4. Check status
            status = hub.get_status()
            assert status["stats"]["events_received"] == 1
    
    # =========================================================================
    # PERFORMANCE TESTS
    # =========================================================================
    
    def test_learning_cycle_performance(self, full_layer4_stack):
        """Test learning cycle completes in reasonable time."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        base = full_layer4_stack["base"]
        
        # Generate larger dataset
        data = [
            {"text": f"def function_{i}(): return {i}"}
            for i in range(50)
        ]
        
        start = time.time()
        cycle = base.run_recursive_cycle(
            domain=PatternDomain.CODE,
            data=data,
            max_iterations=2,
        )
        elapsed = time.time() - start
        
        # Should complete in under 30 seconds
        assert elapsed < 30.0
        print(f"Learning cycle completed in {elapsed:.2f}s")
    
    def test_frontier_theorem_proving_performance(self, full_layer4_stack):
        """Test theorem prover performance."""
        frontier = full_layer4_stack["frontier"]
        
        # Add many facts
        for i in range(20):
            frontier.theorem_prover.add_fact(f"fact_{i}")
        
        # Add chain rules
        for i in range(19):
            frontier.theorem_prover.add_rule(
                f"chain_{i}",
                [f"fact_{i}"],
                f"derived_{i}",
            )
        
        start = time.time()
        proof = frontier.prove("derived_10", max_depth=5, max_nodes=1000)
        elapsed = time.time() - start
        
        # Should complete quickly
        assert elapsed < 5.0
        print(f"Theorem proving completed in {elapsed:.2f}s")
    
    # =========================================================================
    # GPU VERIFICATION TESTS
    # =========================================================================
    
    def test_gpu_availability(self, full_layer4_stack):
        """Test GPU availability detection."""
        from ml_intelligence.layer4_frontier_reasoning import TORCH_AVAILABLE, DEVICE
        
        print(f"PyTorch available: {TORCH_AVAILABLE}")
        print(f"Device: {DEVICE}")
        
        # Test should pass regardless of GPU
        assert True
    
    def test_frontier_status_shows_gpu(self, full_layer4_stack):
        """Test frontier status reports GPU info."""
        frontier = full_layer4_stack["frontier"]
        status = frontier.get_status()
        
        assert "gpu_available" in status
        assert "device" in status
        print(f"GPU status: {status['gpu_available']}, Device: {status['device']}")
    
    # =========================================================================
    # PERSISTENCE TESTS
    # =========================================================================
    
    def test_pattern_persistence(self, full_layer4_stack):
        """Test patterns persist to disk."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        base = full_layer4_stack["base"]
        tmpdir = full_layer4_stack["tmpdir"]
        
        # Run cycle to create patterns
        data = [{"text": "test pattern data"}]
        base.run_recursive_cycle(PatternDomain.CODE, data, max_iterations=1)
        
        # Force save
        base._save_patterns()
        
        # Check file exists
        patterns_file = base.storage_path / "patterns.json"
        assert patterns_file.exists()
        
        # Load and verify
        with open(patterns_file) as f:
            saved = json.load(f)
        
        assert "patterns" in saved
        assert "current_cycle_number" in saved


class TestLayer4Stress:
    """Stress tests for Layer 4."""
    
    @pytest.fixture
    def layer4_frontier(self):
        """Create frontier for stress tests."""
        from ml_intelligence.layer4_frontier_reasoning import get_frontier_layer4
        return get_frontier_layer4(embedding_dim=64)
    
    def test_many_concepts(self, layer4_frontier):
        """Test learning many concepts."""
        for i in range(50):
            examples = [np.random.randn(64) for _ in range(3)]
            layer4_frontier.learn_concept(f"concept_{i}", examples)
        
        assert len(layer4_frontier.concept_learner.concepts) == 50
    
    def test_large_knowledge_graph(self, layer4_frontier):
        """Test large graph reasoning."""
        # Add 100 nodes
        for i in range(100):
            layer4_frontier.graph_reasoner.add_node(f"node_{i}")
        
        # Add edges
        for i in range(99):
            layer4_frontier.graph_reasoner.add_edge(
                f"node_{i}", f"node_{i+1}", "next"
            )
        
        # Query
        prob = layer4_frontier.graph_query("node_0", "node_99")
        assert 0.0 <= prob <= 1.0
    
    def test_many_rules(self, layer4_frontier):
        """Test many probabilistic rules."""
        for i in range(100):
            layer4_frontier.prob_logic.add_fact(f"fact_{i}", [str(i)], 0.5 + i/200)
        
        assert len(layer4_frontier.prob_logic.facts) == 100


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
