"""
Layer 4 Component Tests

Tests for each Layer 4 component:
1. Base: Recursive Pattern Learner
2. Advanced: Neuro-Symbolic Extensions
3. Frontier: GPU-Accelerated Reasoning
4. Integration Hub: Layer connections
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json
import tempfile
from pathlib import Path


# ============================================================================
# 1. BASE LAYER 4 TESTS (Recursive Pattern Learner)
# ============================================================================

class TestLayer4Base:
    """Tests for Layer4RecursivePatternLearner."""
    
    @pytest.fixture
    def layer4_base(self):
        """Create base Layer 4 instance."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            get_layer4_recursive_learner,
            PatternDomain,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            learner = get_layer4_recursive_learner()
            learner.storage_path = Path(tmpdir)
            yield learner
    
    def test_initialization(self, layer4_base):
        """Test Layer 4 base initializes correctly."""
        assert layer4_base is not None
        assert layer4_base.min_confidence == 0.6
        assert layer4_base.min_trust_for_transfer == 0.7
        assert layer4_base.max_abstraction_level == 5
    
    def test_pattern_domains_exist(self):
        """Test all pattern domains are defined."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        domains = list(PatternDomain)
        assert len(domains) == 8
        assert PatternDomain.CODE in domains
        assert PatternDomain.HEALING in domains
        assert PatternDomain.ERROR in domains
        assert PatternDomain.TEMPLATE in domains
    
    def test_run_recursive_cycle(self, layer4_base):
        """Test running a recursive learning cycle."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        data = [
            {"text": "def add(a, b): return a + b"},
            {"text": "def subtract(a, b): return a - b"},
            {"text": "def multiply(a, b): return a * b"},
        ]
        
        cycle = layer4_base.run_recursive_cycle(
            domain=PatternDomain.CODE,
            data=data,
            max_iterations=1,
        )
        
        assert cycle is not None
        assert cycle.cycle_number >= 1
        assert cycle.patterns_discovered >= 0
        assert cycle.completed_at is not None
    
    def test_get_patterns_for_domain(self, layer4_base):
        """Test retrieving patterns by domain."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        patterns = layer4_base.get_patterns_for_domain(
            domain=PatternDomain.CODE,
            min_trust=0.0,
            limit=10,
        )
        
        assert isinstance(patterns, list)
    
    def test_query_patterns(self, layer4_base):
        """Test querying patterns by text."""
        results = layer4_base.query_patterns(
            query="authentication login",
            limit=5,
        )
        
        assert isinstance(results, list)
    
    def test_cross_domain_insights(self, layer4_base):
        """Test getting cross-domain insights."""
        insights = layer4_base.get_cross_domain_insights()
        
        assert "total_patterns" in insights
        assert "patterns_by_domain" in insights
        assert "transfer_success_rates" in insights
    
    def test_status(self, layer4_base):
        """Test getting Layer 4 status."""
        status = layer4_base.get_status()
        
        assert status["layer"] == 4
        assert "total_patterns" in status
        assert "total_cycles" in status
    
    def test_abstract_pattern_dataclass(self):
        """Test AbstractPattern dataclass."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        pattern = AbstractPattern(
            pattern_id="test-123",
            abstract_form={"keywords": ["test"]},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE, PatternDomain.TEMPLATE],
            confidence=0.8,
            trust_score=0.75,
            abstraction_level=2,
            support_count=5,
        )
        
        assert pattern.pattern_id == "test-123"
        assert pattern.confidence == 0.8
        
        # Test to_dict
        d = pattern.to_dict()
        assert d["pattern_id"] == "test-123"
        assert d["source_domain"] == "code"


# ============================================================================
# 2. ADVANCED LAYER 4 TESTS (Neuro-Symbolic Extensions)
# ============================================================================

class TestLayer4Advanced:
    """Tests for Layer4AdvancedNeuroSymbolic."""
    
    @pytest.fixture
    def layer4_advanced(self):
        """Create advanced Layer 4 instance."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import get_advanced_layer4
        return get_advanced_layer4()
    
    def test_initialization(self, layer4_advanced):
        """Test advanced Layer 4 initializes correctly."""
        assert layer4_advanced is not None
        assert layer4_advanced.composition_engine is not None
        assert layer4_advanced.self_modifying_engine is not None
        assert layer4_advanced.differentiable_logic is not None
    
    def test_composition_engine(self, layer4_advanced):
        """Test compositional generalization."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator
        
        # Add patterns
        layer4_advanced.composition_engine.pattern_store["p1"] = {
            "keywords": ["auth", "login"],
            "roles": ["validator"],
        }
        layer4_advanced.composition_engine.pattern_store["p2"] = {
            "keywords": ["auth", "token"],
            "roles": ["generator"],
        }
        
        # Test UNION
        composite = layer4_advanced.compose_patterns("union", ["p1", "p2"])
        assert composite is not None
        assert "auth" in composite.result_pattern.get("keywords", [])
        
        # Test INTERSECTION
        composite = layer4_advanced.compose_patterns("intersection", ["p1", "p2"])
        assert composite is not None
    
    def test_self_modifying_rule(self, layer4_advanced):
        """Test self-modifying rules."""
        rule = layer4_advanced.add_self_modifying_rule(
            premise={"error_type": "import"},
            conclusion={"action": "add_import"},
            confidence=0.8,
        )
        
        assert rule is not None
        assert rule.generation == 0
        assert rule.confidence == 0.8
        assert rule.mutation_rate == 0.1
    
    def test_soft_reasoning(self, layer4_advanced):
        """Test differentiable logic."""
        subject_emb = np.random.randn(128)
        object_emb = np.random.randn(128)
        
        truth, chain = layer4_advanced.soft_reason(
            "related_to",
            subject_emb,
            object_emb,
        )
        
        assert 0.0 <= truth <= 1.0
        assert isinstance(chain, list)
    
    def test_counterfactual_reasoning(self, layer4_advanced):
        """Test counterfactual what-if analysis."""
        original = {"bugs": 5, "tests": 10}
        intervention = {"bugs": 0}
        
        cf = layer4_advanced.what_if(
            original_state=original,
            intervention=intervention,
            outcome_fn=lambda s: s.get("tests", 0) - s.get("bugs", 0),
        )
        
        assert cf is not None
        assert cf.outcome_difference == 5  # (10-0) - (10-5) = 5
        assert cf.counterfactual_state["bugs"] == 0
    
    def test_temporal_pattern(self, layer4_advanced):
        """Test temporal pattern tracking."""
        pattern = layer4_advanced.track_pattern_temporally({"type": "test"})
        
        assert pattern is not None
        assert pattern.current_strength == 1.0
        assert pattern.version == 1
    
    def test_status(self, layer4_advanced):
        """Test advanced status."""
        status = layer4_advanced.get_status()
        
        assert status["layer"] == "4-advanced"
        assert "components" in status
        assert "composition_engine" in status["components"]


# ============================================================================
# 3. FRONTIER LAYER 4 TESTS (GPU-Accelerated)
# ============================================================================

class TestLayer4Frontier:
    """Tests for Layer4FrontierReasoning."""
    
    @pytest.fixture
    def layer4_frontier(self):
        """Create frontier Layer 4 instance."""
        from ml_intelligence.layer4_frontier_reasoning import get_frontier_layer4
        return get_frontier_layer4(embedding_dim=64)  # Smaller for tests
    
    def test_initialization(self, layer4_frontier):
        """Test frontier Layer 4 initializes correctly."""
        assert layer4_frontier is not None
        assert layer4_frontier.theorem_prover is not None
        assert layer4_frontier.structure_mapper is not None
        assert layer4_frontier.prob_logic is not None
        assert layer4_frontier.program_synth is not None
        assert layer4_frontier.meta_reasoner is not None
        assert layer4_frontier.abductive is not None
        assert layer4_frontier.concept_learner is not None
        assert layer4_frontier.graph_reasoner is not None
        assert layer4_frontier.memory is not None
    
    def test_neural_theorem_proving(self, layer4_frontier):
        """Test neural theorem prover."""
        # Add facts and rules
        layer4_frontier.theorem_prover.add_fact("human(socrates)")
        layer4_frontier.theorem_prover.add_rule(
            "mortality",
            ["human(socrates)"],
            "mortal(socrates)",
        )
        
        # Prove
        proof = layer4_frontier.prove("mortal(socrates)")
        
        assert proof is not None
        assert proof.goal == "mortal(socrates)"
    
    def test_analogical_reasoning(self, layer4_frontier):
        """Test structure mapping."""
        # Add domains
        layer4_frontier.structure_mapper.add_domain("solar", [
            {"type": "entity", "name": "sun"},
            {"type": "entity", "name": "planet"},
            {"type": "relation", "name": "orbits", "arguments": ["planet", "sun"]},
        ])
        layer4_frontier.structure_mapper.add_domain("atom", [
            {"type": "entity", "name": "nucleus"},
            {"type": "entity", "name": "electron"},
            {"type": "relation", "name": "orbits", "arguments": ["electron", "nucleus"]},
        ])
        
        mapping = layer4_frontier.find_analogy("solar", "atom")
        
        assert mapping is not None
        assert mapping.score > 0
    
    def test_program_synthesis(self, layer4_frontier):
        """Test neural program synthesis."""
        examples = [
            (2, 4),
            (3, 6),
            (5, 10),
        ]
        
        program = layer4_frontier.synthesize_program(examples)
        
        assert program is not None
        assert program.code == "double"
        assert program.passes_examples is True
    
    def test_concept_learning(self, layer4_frontier):
        """Test few-shot concept learning."""
        # Learn concept
        positive_examples = [
            np.ones(64) * 0.5,
            np.ones(64) * 0.6,
            np.ones(64) * 0.7,
        ]
        layer4_frontier.learn_concept("positive", positive_examples)
        
        # Classify
        test_emb = np.ones(64) * 0.55
        results = layer4_frontier.classify_concept(test_emb)
        
        assert len(results) > 0
        assert results[0][0] == "positive"
    
    def test_meta_reasoning(self, layer4_frontier):
        """Test meta-reasoning strategy selection."""
        strategy = layer4_frontier.select_strategy("theorem_proving", complexity=0.8)
        
        assert strategy is not None
    
    def test_abductive_reasoning(self, layer4_frontier):
        """Test abductive explanation."""
        # Add pattern
        layer4_frontier.abductive.add_explanation_pattern(
            condition={"cause": "memory_leak"},
            explains={"symptom": "slow"},
            probability=0.7,
        )
        
        # Add observation
        layer4_frontier.abductive.add_observation({"symptom": "slow"})
        
        # Get explanation
        hypothesis = layer4_frontier.abductive.best_explanation()
        
        # May or may not find explanation depending on matching
        assert hypothesis is None or hypothesis.probability > 0
    
    def test_graph_neural_reasoning(self, layer4_frontier):
        """Test GNN reasoning."""
        layer4_frontier.graph_reasoner.add_node("A")
        layer4_frontier.graph_reasoner.add_node("B")
        layer4_frontier.graph_reasoner.add_edge("A", "B", "related")
        
        prob = layer4_frontier.graph_query("A", "B")
        
        assert 0.0 <= prob <= 1.0
    
    def test_memory_augmented_reasoning(self, layer4_frontier):
        """Test differentiable memory."""
        steps = [np.random.randn(64) for _ in range(5)]
        query = np.random.randn(64)
        
        result = layer4_frontier.reason_with_memory(steps, query)
        
        assert result.shape == (64,)
    
    def test_probabilistic_logic(self, layer4_frontier):
        """Test probabilistic facts and rules."""
        layer4_frontier.prob_logic.add_fact("rain", ["today"], 0.7)
        layer4_frontier.prob_logic.add_rule("wet", ["rain"], 0.9)
        
        prob = layer4_frontier.query_probability("rain", ["today"])
        
        assert prob == 0.7
    
    def test_status(self, layer4_frontier):
        """Test frontier status."""
        status = layer4_frontier.get_status()
        
        assert status["layer"] == "4-frontier"
        assert "gpu_available" in status
        assert "components" in status


# ============================================================================
# 4. INTEGRATION HUB TESTS
# ============================================================================

class TestLayer4Integration:
    """Tests for Layer4IntegrationHub."""
    
    @pytest.fixture
    def integration_hub(self):
        """Create integration hub."""
        from genesis.layer4_integration import Layer4IntegrationHub
        
        with tempfile.TemporaryDirectory() as tmpdir:
            hub = Layer4IntegrationHub(session=None)
            hub.integration_base = Path(tmpdir)
            yield hub
    
    def test_initialization(self, integration_hub):
        """Test integration hub initializes."""
        assert integration_hub is not None
        assert integration_hub.stats["events_received"] == 0
    
    def test_receive_healing_event(self, integration_hub):
        """Test receiving healing events."""
        result = integration_hub.receive_healing_event(
            error_type="ImportError",
            error_content="No module named xyz",
            fix_applied="pip install xyz",
            success=True,
        )
        
        assert result is not None
        assert "patterns_learned" in result
        assert integration_hub.stats["events_received"] == 1
    
    def test_receive_code_analysis(self, integration_hub):
        """Test receiving code analysis."""
        result = integration_hub.receive_code_analysis(
            file_path="/path/to/file.py",
            analysis_data={"functions": 5, "classes": 2},
        )
        
        assert result is not None
        assert "patterns_extracted" in result
    
    def test_export_pattern_caching(self, integration_hub):
        """Test pattern caching when Layer 3 unavailable."""
        result = integration_hub.export_pattern_to_governance(
            pattern_id="test-pattern",
            pattern_data={"type": "test"},
            trust_score=0.95,
        )
        
        # Should cache since no L3 connection
        assert result is False
        
        cache_file = integration_hub.integration_base / "l3_pending.json"
        assert cache_file.exists()
    
    def test_send_insight_to_layer2(self, integration_hub):
        """Test sending insights to Layer 2."""
        result = integration_hub.send_insight_to_layer2(
            insight_type="cross_domain",
            insight_data={"source": "code", "target": "healing"},
            source_patterns=["p1", "p2"],
        )
        
        assert result is True
        assert integration_hub.stats["insights_sent_to_l2"] == 1
    
    def test_store_synthesized_program(self, integration_hub):
        """Test storing synthesized programs."""
        result = integration_hub.store_synthesized_program(
            program_id="prog-123",
            code="double(x)",
            spec={"examples": [(2, 4)]},
            confidence=0.9,
        )
        
        # Should succeed (stores locally even if L1 connection fails)
        assert result is True
        assert integration_hub.stats["programs_stored_in_l1"] == 1
        
        # Verify local file was created
        prog_file = integration_hub.integration_base / "synthesized_programs" / "prog-123.json"
        assert prog_file.exists()
    
    def test_store_learned_concept(self, integration_hub):
        """Test storing learned concepts."""
        result = integration_hub.store_learned_concept(
            concept_name="error_pattern",
            concept_data={"prototype": [0.1, 0.2, 0.3]},
        )
        
        # Should succeed (stores locally even if L1 connection fails)
        assert result is True
        assert integration_hub.stats["concepts_stored_in_l1"] == 1
        
        # Verify local file was created
        concept_file = integration_hub.integration_base / "learned_concepts" / "error_pattern.json"
        assert concept_file.exists()
    
    def test_status(self, integration_hub):
        """Test integration status."""
        status = integration_hub.get_status()
        
        assert "stats" in status
        assert "layer4_base_connected" in status


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
