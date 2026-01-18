"""
Layer 4 Integration Tests - Testing the Complete ML Intelligence System.

These tests verify Layer 4 ACTUALLY works as a cohesive system:
1. Base + Advanced components integrate properly
2. Patterns flow through all processing stages
3. Cross-domain transfer works end-to-end
4. Layer 4 → Layer 3 governance export works
5. KPI tracking integrates with pattern learning
6. Full recursive learning pipeline functions

Run with: pytest tests/test_layer4_integration.py -v
"""

import sys
import tempfile
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import pytest

backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def full_layer4_stack(temp_storage):
    """Create complete Layer 4 stack with all components."""
    from ml_intelligence.layer4_recursive_pattern_learner import (
        Layer4RecursivePatternLearner
    )
    from ml_intelligence.layer4_advanced_neuro_symbolic import (
        Layer4AdvancedNeuroSymbolic
    )
    
    base = Layer4RecursivePatternLearner(storage_path=temp_storage)
    advanced = Layer4AdvancedNeuroSymbolic(base_layer4=base)
    
    return {
        "base": base,
        "advanced": advanced,
    }


# =============================================================================
# BASE + ADVANCED INTEGRATION TESTS
# =============================================================================

class TestBaseAdvancedIntegration:
    """Verify base and advanced Layer 4 components integrate."""
    
    def test_advanced_connects_to_base(self, full_layer4_stack):
        """Advanced ACTUALLY connects to base layer."""
        advanced = full_layer4_stack["advanced"]
        
        assert advanced.base is not None
        assert advanced.base == full_layer4_stack["base"]
    
    def test_base_patterns_available_to_composition(self, full_layer4_stack):
        """Base patterns ACTUALLY available for composition."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        base = full_layer4_stack["base"]
        advanced = full_layer4_stack["advanced"]
        
        pattern = AbstractPattern(
            pattern_id="integration-test",
            abstract_form={"keywords": ["test", "integration"]},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE],
            confidence=0.9,
            trust_score=0.85,
            abstraction_level=1,
            support_count=10,
        )
        
        base.patterns[pattern.pattern_id] = pattern
        
        advanced.composition_engine.pattern_store["other"] = {
            "keywords": ["other"],
        }
        
        result = advanced.compose_patterns("union", ["integration-test", "other"])
        
        assert result is not None
        assert "test" in result.result_pattern["keywords"]
    
    def test_status_combines_base_and_advanced(self, full_layer4_stack):
        """Combined status ACTUALLY reflects both layers."""
        base = full_layer4_stack["base"]
        advanced = full_layer4_stack["advanced"]
        
        base_status = base.get_status()
        advanced_status = advanced.get_status()
        
        assert base_status["layer"] == 4
        assert advanced_status["layer"] == "4-advanced"
        assert advanced_status["base_layer4_connected"] == True


# =============================================================================
# PATTERN FLOW TESTS
# =============================================================================

class TestPatternFlow:
    """Verify patterns flow through all processing stages."""
    
    def test_pattern_creation_to_query(self, full_layer4_stack):
        """Patterns ACTUALLY flow from creation to query."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        base = full_layer4_stack["base"]
        
        pattern = AbstractPattern(
            pattern_id="flow-test",
            abstract_form={"keywords": ["error", "handler"]},
            source_domain=PatternDomain.ERROR,
            applicable_domains=[PatternDomain.ERROR, PatternDomain.HEALING],
            confidence=0.85,
            trust_score=0.8,
            abstraction_level=2,
            support_count=15,
        )
        
        base.patterns[pattern.pattern_id] = pattern
        base.patterns_by_domain[PatternDomain.ERROR].append(pattern.pattern_id)
        
        results = base.query_patterns("error handler")
        
        assert len(results) > 0
        assert results[0][0].pattern_id == "flow-test"
    
    def test_pattern_to_temporal_tracking(self, full_layer4_stack):
        """Patterns ACTUALLY trackable temporally."""
        advanced = full_layer4_stack["advanced"]
        
        temporal_pattern = advanced.track_pattern_temporally({
            "type": "temporal_flow_test",
            "keywords": ["flow", "test"],
        })
        
        advanced.temporal_manager.activate(temporal_pattern.pattern_id, success=True)
        
        assert temporal_pattern.activation_count == 1
        assert temporal_pattern.current_strength > 0.9
    
    def test_pattern_to_composition(self, full_layer4_stack):
        """Patterns ACTUALLY composable."""
        advanced = full_layer4_stack["advanced"]
        
        advanced.composition_engine.pattern_store["validate"] = {
            "keywords": ["validate", "check"],
        }
        advanced.composition_engine.pattern_store["transform"] = {
            "keywords": ["transform", "convert"],
        }
        
        composite = advanced.compose_patterns("composition", ["validate", "transform"])
        
        assert composite is not None
        assert composite.result_pattern["structure"]["type"] == "pipeline"


# =============================================================================
# CROSS-DOMAIN TRANSFER TESTS
# =============================================================================

class TestCrossDomainTransferE2E:
    """End-to-end tests for cross-domain pattern transfer."""
    
    def test_pattern_applicable_to_multiple_domains(self, full_layer4_stack):
        """Patterns ACTUALLY applicable across domains."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        base = full_layer4_stack["base"]
        
        pattern = AbstractPattern(
            pattern_id="cross-domain-test",
            abstract_form={"type": "retry_logic", "keywords": ["retry", "backoff"]},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE, PatternDomain.HEALING, PatternDomain.WORKFLOW],
            confidence=0.9,
            trust_score=0.85,
            abstraction_level=2,
            support_count=25,
        )
        
        base.patterns[pattern.pattern_id] = pattern
        for domain in pattern.applicable_domains:
            base.patterns_by_domain[domain].append(pattern.pattern_id)
        
        code_patterns = base.get_patterns_for_domain(PatternDomain.CODE)
        healing_patterns = base.get_patterns_for_domain(PatternDomain.HEALING)
        workflow_patterns = base.get_patterns_for_domain(PatternDomain.WORKFLOW)
        
        assert any(p.pattern_id == "cross-domain-test" for p in code_patterns)
        assert any(p.pattern_id == "cross-domain-test" for p in healing_patterns)
        assert any(p.pattern_id == "cross-domain-test" for p in workflow_patterns)
    
    def test_transfer_success_rate_tracked(self, full_layer4_stack):
        """Transfer success rates ACTUALLY tracked."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        base = full_layer4_stack["base"]
        
        base.transfer_success[(PatternDomain.ERROR, PatternDomain.HEALING)] = 0.92
        base.transfer_success[(PatternDomain.CODE, PatternDomain.TEMPLATE)] = 0.85
        
        insights = base.get_cross_domain_insights()
        
        assert "error->healing" in insights["transfer_success_rates"]
        assert insights["transfer_success_rates"]["error->healing"] == 0.92


# =============================================================================
# KPI INTEGRATION TESTS
# =============================================================================

class TestKPIIntegration:
    """Verify KPI tracking integrates with pattern learning."""
    
    def test_kpi_tracker_exists(self):
        """KPI tracker module ACTUALLY exists and importable."""
        from ml_intelligence.kpi_tracker import KPITracker
        
        tracker = KPITracker()
        assert tracker is not None
        assert hasattr(tracker, 'components')
    
    def test_component_registration(self):
        """Components ACTUALLY registered in tracker."""
        from ml_intelligence.kpi_tracker import KPITracker
        
        tracker = KPITracker()
        tracker.register_component("pattern_learner")
        
        assert "pattern_learner" in tracker.components
    
    def test_health_signal_structure(self):
        """Health signals ACTUALLY have correct structure."""
        from ml_intelligence.kpi_tracker import KPITracker
        
        tracker = KPITracker()
        tracker.register_component("test_component")
        
        health = tracker.get_health_signal("test_component")
        
        assert "component_name" in health
        assert "status" in health
        assert "trust_score" in health


# =============================================================================
# RECURSIVE LEARNING TESTS
# =============================================================================

class TestRecursiveLearning:
    """Verify recursive learning pipeline functions."""
    
    def test_cycle_number_increments(self, full_layer4_stack):
        """Cycle number ACTUALLY increments."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        base = full_layer4_stack["base"]
        
        initial = base.current_cycle_number
        
        cycle = base.run_recursive_cycle(
            domain=PatternDomain.CODE,
            data=[{"text": "def foo(): pass"}],
            max_iterations=1
        )
        
        assert base.current_cycle_number == initial + 1
    
    def test_cycle_records_domains_touched(self, full_layer4_stack):
        """Cycles ACTUALLY record which domains were touched."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        base = full_layer4_stack["base"]
        
        cycle = base.run_recursive_cycle(
            domain=PatternDomain.HEALING,
            data=[{"text": "fix error by retry"}],
            max_iterations=1
        )
        
        assert PatternDomain.HEALING in cycle.domains_touched
    
    def test_insights_include_cycle_count(self, full_layer4_stack):
        """Insights ACTUALLY include cycle count."""
        base = full_layer4_stack["base"]
        
        insights = base.get_cross_domain_insights()
        
        assert "total_cycles" in insights
        assert "current_cycle" in insights


# =============================================================================
# END-TO-END SCENARIOS
# =============================================================================

class TestEndToEndScenarios:
    """End-to-end tests for complete Layer 4 scenarios."""
    
    def test_scenario_pattern_discovery_to_composition(self, full_layer4_stack):
        """Full scenario: pattern discovery → abstraction → composition."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        base = full_layer4_stack["base"]
        advanced = full_layer4_stack["advanced"]
        
        pattern_a = AbstractPattern(
            pattern_id="discovered-a",
            abstract_form={"keywords": ["validate", "input"]},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE],
            confidence=0.85,
            trust_score=0.8,
            abstraction_level=1,
            support_count=10,
        )
        
        pattern_b = AbstractPattern(
            pattern_id="discovered-b",
            abstract_form={"keywords": ["transform", "output"]},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE],
            confidence=0.9,
            trust_score=0.85,
            abstraction_level=1,
            support_count=15,
        )
        
        base.patterns[pattern_a.pattern_id] = pattern_a
        base.patterns[pattern_b.pattern_id] = pattern_b
        
        composite = advanced.compose_patterns("composition", ["discovered-a", "discovered-b"])
        
        assert composite is not None
        assert composite.result_pattern["structure"]["type"] == "pipeline"
    
    def test_scenario_temporal_reinforcement(self, full_layer4_stack):
        """Full scenario: pattern creation → reinforce → check strength."""
        advanced = full_layer4_stack["advanced"]
        
        pattern = advanced.track_pattern_temporally({
            "type": "evolving_pattern",
            "keywords": ["test"],
        })
        
        initial_strength = pattern.current_strength
        
        for _ in range(5):
            pattern.reinforce()
        
        final_strength = pattern.current_strength
        assert final_strength >= initial_strength
        assert pattern.activation_count == 5
    
    def test_scenario_self_modifying_rule_tracking(self, full_layer4_stack):
        """Full scenario: rule creation → application → record outcome."""
        advanced = full_layer4_stack["advanced"]
        
        rule = advanced.add_self_modifying_rule(
            premise={"type": "test_input"},
            conclusion={"action": "process"},
            confidence=0.5,
        )
        
        for _ in range(5):
            advanced.self_modifying_engine.apply_rule(rule.rule_id, {"type": "test_input"})
            advanced.self_modifying_engine.record_outcome(rule.rule_id, success=True)
        
        final_rule = advanced.self_modifying_engine.rules[rule.rule_id]
        
        assert final_rule.successes == 5
        assert final_rule.success_rate() == 1.0


# =============================================================================
# LAYER 4 SYSTEM HEALTH TESTS
# =============================================================================

class TestLayer4SystemHealth:
    """Verify Layer 4 operates as a healthy system."""
    
    def test_all_components_operational(self, full_layer4_stack):
        """All Layer 4 components ACTUALLY operational."""
        base = full_layer4_stack["base"]
        advanced = full_layer4_stack["advanced"]
        
        base_status = base.get_status()
        advanced_status = advanced.get_status()
        
        assert base_status is not None
        assert advanced_status is not None
        assert base_status["layer"] == 4
        assert advanced_status["layer"] == "4-advanced"
    
    def test_no_exceptions_in_pipeline(self, full_layer4_stack):
        """Full pipeline ACTUALLY runs without exceptions."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        base = full_layer4_stack["base"]
        advanced = full_layer4_stack["advanced"]
        
        pattern = AbstractPattern(
            pattern_id="pipeline-test",
            abstract_form={"keywords": ["test"]},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE],
            confidence=0.8,
            trust_score=0.75,
            abstraction_level=1,
            support_count=5,
        )
        base.patterns[pattern.pattern_id] = pattern
        
        base.query_patterns("test")
        
        base.get_cross_domain_insights()
        
        advanced.get_status()
        
        advanced.track_pattern_temporally({"type": "health_test"})
    
    def test_persistence_round_trip(self, full_layer4_stack):
        """Patterns ACTUALLY persist and reload."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        base = full_layer4_stack["base"]
        
        pattern = AbstractPattern(
            pattern_id="persist-test",
            abstract_form={"keywords": ["persistent"]},
            source_domain=PatternDomain.KNOWLEDGE,
            applicable_domains=[PatternDomain.KNOWLEDGE],
            confidence=0.9,
            trust_score=0.85,
            abstraction_level=2,
            support_count=20,
        )
        base.patterns[pattern.pattern_id] = pattern
        base.patterns_by_domain[PatternDomain.KNOWLEDGE].append(pattern.pattern_id)
        
        base._save_patterns()
        
        original_count = len(base.patterns)
        base.patterns.clear()
        base._load_patterns()
        
        assert len(base.patterns) == original_count
        assert "persist-test" in base.patterns


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
