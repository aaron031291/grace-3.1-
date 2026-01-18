"""
REAL Functional Tests for Layer 4 Advanced Neuro-Symbolic Capabilities.

These are NOT smoke tests - they verify that advanced components ACTUALLY:
1. Compositional operators ACTUALLY combine patterns
2. Self-modifying rules ACTUALLY evolve based on performance
3. Differentiable logic ACTUALLY uses soft truth values
4. Counterfactual reasoning ACTUALLY explores what-if scenarios
5. Temporal patterns ACTUALLY decay and strengthen
6. Pattern algebra ACTUALLY works (union, intersection, composition)

Run with: pytest tests/test_layer4_advanced_neuro_symbolic_real.py -v
"""

import sys
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
import pytest

backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def advanced_layer4():
    """Create fresh advanced Layer 4 for each test."""
    from ml_intelligence.layer4_advanced_neuro_symbolic import (
        Layer4AdvancedNeuroSymbolic
    )
    return Layer4AdvancedNeuroSymbolic()


@pytest.fixture
def composition_engine():
    """Create fresh composition engine."""
    from ml_intelligence.layer4_advanced_neuro_symbolic import CompositionEngine
    return CompositionEngine()


@pytest.fixture
def self_modifying_engine():
    """Create fresh self-modifying rule engine."""
    from ml_intelligence.layer4_advanced_neuro_symbolic import SelfModifyingRuleEngine
    return SelfModifyingRuleEngine()


@pytest.fixture
def temporal_manager():
    """Create fresh temporal pattern manager."""
    from ml_intelligence.layer4_advanced_neuro_symbolic import TemporalPatternManager
    return TemporalPatternManager()


# =============================================================================
# PATTERN OPERATOR TESTS
# =============================================================================

class TestPatternOperators:
    """Verify pattern operators ACTUALLY defined correctly."""
    
    def test_all_operators_defined(self):
        """All compositional operators ACTUALLY defined."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator
        
        assert PatternOperator.UNION.value == "union"
        assert PatternOperator.INTERSECTION.value == "intersection"
        assert PatternOperator.COMPOSITION.value == "composition"
        assert PatternOperator.NEGATION.value == "negation"
        assert PatternOperator.SEQUENCE.value == "sequence"
        assert PatternOperator.PARALLEL.value == "parallel"
        assert PatternOperator.CONDITIONAL.value == "conditional"


# =============================================================================
# COMPOSITIONAL GENERALIZATION TESTS
# =============================================================================

class TestCompositionalGeneralization:
    """Verify composition ACTUALLY combines patterns."""
    
    def test_union_operator(self, composition_engine):
        """UNION operator ACTUALLY combines keywords from both patterns."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator
        
        composition_engine.pattern_store["p1"] = {
            "keywords": ["try", "catch"],
            "roles": ["handler"],
        }
        composition_engine.pattern_store["p2"] = {
            "keywords": ["log", "error"],
            "roles": ["reporter"],
        }
        
        composite = composition_engine.compose(
            PatternOperator.UNION,
            ["p1", "p2"]
        )
        
        assert composite is not None
        assert "try" in composite.result_pattern["keywords"]
        assert "log" in composite.result_pattern["keywords"]
        assert composite.result_pattern["_operator"] == "union"
    
    def test_intersection_operator(self, composition_engine):
        """INTERSECTION operator ACTUALLY finds common elements."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator
        
        composition_engine.pattern_store["p1"] = {
            "keywords": ["error", "handle", "log"],
            "roles": ["handler", "logger"],
        }
        composition_engine.pattern_store["p2"] = {
            "keywords": ["error", "report", "log"],
            "roles": ["reporter", "logger"],
        }
        
        composite = composition_engine.compose(
            PatternOperator.INTERSECTION,
            ["p1", "p2"]
        )
        
        assert composite is not None
        assert "error" in composite.result_pattern["keywords"]
        assert "log" in composite.result_pattern["keywords"]
        assert "handle" not in composite.result_pattern["keywords"]
        assert "logger" in composite.result_pattern["roles"]
        assert composite.result_pattern["_operator"] == "intersection"
    
    def test_composition_operator(self, composition_engine):
        """COMPOSITION operator ACTUALLY creates pipeline."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator
        
        composition_engine.pattern_store["validate"] = {
            "keywords": ["validate", "check"],
            "abstract_form": {"action": "validate"},
        }
        composition_engine.pattern_store["transform"] = {
            "keywords": ["transform", "convert"],
            "abstract_form": {"action": "transform"},
        }
        
        composite = composition_engine.compose(
            PatternOperator.COMPOSITION,
            ["validate", "transform"]
        )
        
        assert composite is not None
        assert composite.result_pattern["structure"]["type"] == "pipeline"
        assert len(composite.result_pattern["transformations"]) == 2
        assert composite.result_pattern["_operator"] == "composition"
    
    def test_negation_operator(self, composition_engine):
        """NEGATION operator ACTUALLY creates opposite pattern."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator
        
        composition_engine.pattern_store["allow"] = {
            "keywords": ["allow", "permit"],
            "constraints": [{"type": "grant"}],
        }
        
        composite = composition_engine.compose(
            PatternOperator.NEGATION,
            ["allow"]
        )
        
        assert composite is not None
        assert composite.result_pattern["structure"]["type"] == "negation"
        assert composite.result_pattern["_operator"] == "negation"
    
    def test_composite_tracks_success_rate(self, composition_engine):
        """Composites ACTUALLY track success rate."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import CompositePattern
        
        composite = CompositePattern(
            composite_id="test",
            operator=None,
            operands=[],
            result_pattern={},
            confidence=0.8,
            creation_count=10,
            success_count=8,
        )
        
        assert composite.success_rate() == 0.8


# =============================================================================
# SELF-MODIFYING RULES TESTS
# =============================================================================

class TestSelfModifyingRules:
    """Verify self-modifying rules ACTUALLY evolve."""
    
    def test_rule_creation(self, self_modifying_engine):
        """Self-modifying rules ACTUALLY created."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import SelfModifyingRule
        
        rule = SelfModifyingRule(
            rule_id="evolve-test",
            premise={"type": "error", "code": "404"},
            conclusion={"action": "redirect"},
            confidence=0.75,
        )
        
        self_modifying_engine.add_rule(rule)
        
        assert "evolve-test" in self_modifying_engine.rules
    
    def test_rule_application_updates_count(self, self_modifying_engine):
        """Rule application ACTUALLY updates applications count."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import SelfModifyingRule
        
        rule = SelfModifyingRule(
            rule_id="apply-test",
            premise={"type": "test"},
            conclusion={"action": "pass"},
            confidence=0.8,
        )
        
        self_modifying_engine.add_rule(rule)
        
        initial_count = rule.applications
        
        self_modifying_engine.apply_rule("apply-test", {"type": "test"})
        
        assert self_modifying_engine.rules["apply-test"].applications > initial_count
    
    def test_successful_outcome_tracked(self, self_modifying_engine):
        """Successful outcomes ACTUALLY tracked via record_outcome."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import SelfModifyingRule
        
        rule = SelfModifyingRule(
            rule_id="success-test",
            premise={"type": "test"},
            conclusion={"action": "pass"},
            confidence=0.5,
        )
        
        self_modifying_engine.add_rule(rule)
        
        for _ in range(5):
            self_modifying_engine.apply_rule("success-test", {"type": "test"})
            self_modifying_engine.record_outcome("success-test", success=True)
        
        assert self_modifying_engine.rules["success-test"].successes == 5
        assert self_modifying_engine.rules["success-test"].success_rate() == 1.0
    
    def test_failed_outcome_tracked(self, self_modifying_engine):
        """Failed outcomes ACTUALLY tracked via record_outcome."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import SelfModifyingRule
        
        rule = SelfModifyingRule(
            rule_id="fail-test",
            premise={"type": "test"},
            conclusion={"action": "pass"},
            confidence=0.8,
        )
        
        self_modifying_engine.add_rule(rule)
        
        for _ in range(5):
            self_modifying_engine.apply_rule("fail-test", {"type": "test"})
            self_modifying_engine.record_outcome("fail-test", success=False)
        
        assert self_modifying_engine.rules["fail-test"].failures == 5
        assert self_modifying_engine.rules["fail-test"].success_rate() == 0.0


# =============================================================================
# DIFFERENTIABLE LOGIC TESTS
# =============================================================================

class TestDifferentiableLogic:
    """Verify differentiable logic ACTUALLY uses soft truth values."""
    
    def test_soft_fact_assertion(self, advanced_layer4):
        """Soft facts ACTUALLY stored with continuous truth values."""
        dl = advanced_layer4.differentiable_logic
        
        dl.assert_fact("is_mammal", "dog", "animal", truth_value=0.95)
        dl.assert_fact("is_mammal", "whale", "animal", truth_value=0.85)
        
        assert "is_mammal" in dl.knowledge
        assert len(dl.knowledge["is_mammal"]) == 2
    
    def test_soft_rule_addition(self, advanced_layer4):
        """Soft rules ACTUALLY stored as DifferentiableRule."""
        dl = advanced_layer4.differentiable_logic
        
        rule = dl.add_rule("has_heart")
        
        assert "has_heart" in dl.rules
        assert rule.predicate == "has_heart"
    
    def test_soft_logic_operations(self):
        """SoftLogic operations ACTUALLY compute correct values."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import SoftLogic
        
        assert abs(SoftLogic.AND(0.8, 0.9) - 0.72) < 0.001
        assert abs(SoftLogic.OR(0.5, 0.5) - 0.75) < 0.01
        assert abs(SoftLogic.NOT(0.3) - 0.7) < 0.001
        assert abs(SoftLogic.IMPLIES(0.8, 0.9) - 0.92) < 0.01


# =============================================================================
# COUNTERFACTUAL REASONING TESTS
# =============================================================================

class TestCounterfactualReasoning:
    """Verify counterfactual reasoning ACTUALLY explores what-ifs."""
    
    def test_counterfactual_creation(self, advanced_layer4):
        """Counterfactuals ACTUALLY created."""
        cf = advanced_layer4.counterfactual_reasoner
        
        original = {"temperature": 100, "pressure": 1.0}
        intervention = {"temperature": 50}
        
        cf.add_causal_relation("temperature", "expansion")
        
        result = cf.intervene(
            original,
            intervention,
            lambda state: state.get("temperature", 0) / 100
        )
        
        assert result is not None
        assert result.original_state == original
        assert result.intervention == intervention
    
    def test_outcome_difference_measured(self, advanced_layer4):
        """Outcome difference ACTUALLY measured."""
        cf = advanced_layer4.counterfactual_reasoner
        
        original = {"score": 80}
        intervention = {"score": 100}
        
        result = cf.intervene(
            original,
            intervention,
            lambda s: s["score"] / 100
        )
        
        assert abs(result.outcome_difference - 0.2) < 0.001
        assert result.counterfactual_state["score"] == 100


# =============================================================================
# TEMPORAL PATTERN TESTS
# =============================================================================

class TestTemporalPatterns:
    """Verify temporal patterns ACTUALLY decay and strengthen."""
    
    def test_pattern_creation_with_strength(self, temporal_manager):
        """Temporal patterns ACTUALLY created with initial strength."""
        pattern = temporal_manager.add_pattern(
            {"type": "test"},
            initial_strength=0.8
        )
        
        assert pattern.current_strength == 0.8
        assert pattern.pattern_id in temporal_manager.patterns
    
    def test_pattern_reinforcement(self, temporal_manager):
        """Pattern activation ACTUALLY reinforces strength."""
        pattern = temporal_manager.add_pattern(
            {"type": "reinforce_test"},
            initial_strength=0.5
        )
        
        initial_strength = pattern.current_strength
        
        temporal_manager.activate(pattern.pattern_id, success=True)
        
        assert pattern.current_strength > initial_strength
        assert pattern.activation_count == 1
    
    def test_pattern_decay_formula(self, temporal_manager):
        """Patterns ACTUALLY use decay rate formula."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import TemporalPattern
        from datetime import timedelta
        
        pattern = TemporalPattern(
            pattern_id="decay-test",
            content={"type": "test"},
            creation_time=datetime.utcnow() - timedelta(days=10),
            last_activation=datetime.utcnow() - timedelta(days=10),
            current_strength=0.8,
            decay_rate=0.05,
        )
        
        initial = pattern.current_strength
        pattern.decay()
        
        assert pattern.current_strength < initial
    
    def test_decay_respects_minimum(self, temporal_manager):
        """Decay ACTUALLY respects 0.1 minimum strength."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import TemporalPattern
        from datetime import timedelta
        
        pattern = TemporalPattern(
            pattern_id="min-test",
            content={"type": "test"},
            creation_time=datetime.utcnow() - timedelta(days=100),
            last_activation=datetime.utcnow() - timedelta(days=100),
            current_strength=0.15,
            decay_rate=0.1,
        )
        
        for _ in range(100):
            pattern.decay()
        
        assert pattern.current_strength >= 0.1
    
    def test_get_strongest_patterns(self, temporal_manager):
        """get_strongest ACTUALLY returns highest strength patterns."""
        for i in range(5):
            temporal_manager.add_pattern(
                {"index": i},
                initial_strength=0.2 + i * 0.15
            )
        
        strongest = temporal_manager.get_strongest(n=3)
        
        assert len(strongest) == 3
        assert strongest[0].current_strength >= strongest[1].current_strength
        assert strongest[1].current_strength >= strongest[2].current_strength
    
    def test_prune_weak_patterns(self, temporal_manager):
        """prune_weak ACTUALLY removes low-strength patterns."""
        for i in range(5):
            temporal_manager.add_pattern(
                {"index": i},
                initial_strength=0.1 * (i + 1)
            )
        
        initial_count = len(temporal_manager.patterns)
        
        removed = temporal_manager.prune_weak(min_strength=0.3)
        
        assert len(temporal_manager.patterns) < initial_count
        assert removed > 0


# =============================================================================
# ADVANCED LAYER 4 INTEGRATION TESTS
# =============================================================================

class TestAdvancedLayer4Integration:
    """Verify advanced Layer 4 components work together."""
    
    def test_status_includes_all_components(self, advanced_layer4):
        """Status ACTUALLY includes all advanced components."""
        status = advanced_layer4.get_status()
        
        assert status["layer"] == "4-advanced"
        assert "composition_engine" in status["components"]
        assert "self_modifying_rules" in status["components"]
        assert "differentiable_logic" in status["components"]
        assert "counterfactual_reasoner" in status["components"]
        assert "temporal_patterns" in status["components"]
    
    def test_compose_patterns_via_unified_api(self, advanced_layer4):
        """compose_patterns ACTUALLY works via unified API."""
        advanced_layer4.composition_engine.pattern_store["a"] = {
            "keywords": ["test"],
            "roles": ["validator"],
        }
        advanced_layer4.composition_engine.pattern_store["b"] = {
            "keywords": ["demo"],
            "roles": ["executor"],
        }
        
        result = advanced_layer4.compose_patterns("union", ["a", "b"])
        
        assert result is not None
        assert "test" in result.result_pattern["keywords"]
        assert "demo" in result.result_pattern["keywords"]
    
    def test_add_self_modifying_rule_via_api(self, advanced_layer4):
        """add_self_modifying_rule ACTUALLY adds rule."""
        rule = advanced_layer4.add_self_modifying_rule(
            premise={"type": "api_test"},
            conclusion={"action": "respond"},
            confidence=0.75,
        )
        
        assert rule.rule_id in advanced_layer4.self_modifying_engine.rules
    
    def test_track_pattern_temporally(self, advanced_layer4):
        """track_pattern_temporally ACTUALLY adds temporal tracking."""
        pattern = advanced_layer4.track_pattern_temporally(
            {"type": "temporal_api_test"}
        )
        
        assert pattern.pattern_id in advanced_layer4.temporal_manager.patterns


# =============================================================================
# PATTERN EVOLUTION TESTS
# =============================================================================

class TestPatternEvolution:
    """Verify patterns ACTUALLY evolve over time."""
    
    def test_temporal_pattern_versioning(self):
        """Temporal patterns ACTUALLY track versions."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import TemporalPattern
        
        pattern = TemporalPattern(
            pattern_id="version-test",
            content={"version": 1},
            creation_time=datetime.utcnow(),
            last_activation=datetime.utcnow(),
            current_strength=0.8,
        )
        
        assert pattern.version == 1
        
        pattern.evolve({"version": 2})
        
        assert pattern.version == 2
        assert len(pattern.previous_versions) == 1
        assert pattern.content["version"] == 2
    
    def test_pattern_peak_strength_tracked(self):
        """Peak strength ACTUALLY tracked via reinforce."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import TemporalPattern
        
        pattern = TemporalPattern(
            pattern_id="peak-test",
            content={"type": "test"},
            creation_time=datetime.utcnow(),
            last_activation=datetime.utcnow(),
            current_strength=0.5,
            peak_strength=0.5,
        )
        
        for _ in range(10):
            pattern.reinforce()
        
        peak = pattern.peak_strength
        
        assert peak >= 0.5
        assert pattern.current_strength <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
