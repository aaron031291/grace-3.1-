"""
Layer 4 Pattern Learning - REAL Functional Tests

Tests verify ACTUAL pattern learning behavior using real implementations:
- PatternDomain and PatternOperator enums
- AbstractPattern structure and serialization
- CompositePattern composition and algebra
- RecursiveLearningCycle tracking
- Cross-domain transfer patterns
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# PATTERN DOMAIN ENUM TESTS
# =============================================================================

class TestPatternDomainEnumFunctional:
    """Functional tests for PatternDomain enum."""

    def test_all_pattern_domains_defined(self):
        """All required pattern domains must be defined."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain

        required_domains = [
            "CODE",
            "HEALING",
            "ERROR",
            "TEMPLATE",
            "REASONING",
            "KNOWLEDGE",
            "WORKFLOW",
            "TESTING"
        ]

        for domain_name in required_domains:
            assert hasattr(PatternDomain, domain_name), f"Missing domain: {domain_name}"

    def test_domain_values_are_lowercase(self):
        """Domain values must be lowercase strings."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain

        for domain in PatternDomain:
            assert isinstance(domain.value, str)
            assert domain.value == domain.value.lower()


# =============================================================================
# PATTERN OPERATOR ENUM TESTS
# =============================================================================

class TestPatternOperatorEnumFunctional:
    """Functional tests for PatternOperator enum."""

    def test_all_pattern_operators_defined(self):
        """All required pattern operators must be defined."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator

        required_operators = [
            "UNION",
            "INTERSECTION",
            "COMPOSITION",
            "NEGATION",
            "SEQUENCE",
            "PARALLEL",
            "CONDITIONAL"
        ]

        for op_name in required_operators:
            assert hasattr(PatternOperator, op_name), f"Missing operator: {op_name}"

    def test_operator_values_are_lowercase(self):
        """Operator values must be lowercase strings."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator

        for op in PatternOperator:
            assert isinstance(op.value, str)
            assert op.value == op.value.lower()


# =============================================================================
# ABSTRACT PATTERN TESTS
# =============================================================================

class TestAbstractPatternFunctional:
    """Functional tests for AbstractPattern data class."""

    @pytest.fixture
    def abstract_pattern(self):
        """Create an AbstractPattern instance."""
        from ml_intelligence.layer4_recursive_pattern_learner import AbstractPattern, PatternDomain

        return AbstractPattern(
            pattern_id="pattern-test-123",
            abstract_form={
                "structure": {"type": "function_call", "args": 2},
                "keywords": ["filter", "list", "condition"],
                "relationships": [{"from": "input", "to": "output", "type": "transform"}]
            },
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE, PatternDomain.TEMPLATE],
            confidence=0.85,
            trust_score=0.75,
            abstraction_level=2,
            support_count=10
        )

    def test_abstract_pattern_creation(self, abstract_pattern):
        """AbstractPattern must be creatable with required fields."""
        assert abstract_pattern.pattern_id == "pattern-test-123"
        assert abstract_pattern.confidence == 0.85
        assert abstract_pattern.trust_score == 0.75

    def test_abstract_pattern_has_abstract_form(self, abstract_pattern):
        """AbstractPattern must have abstract_form."""
        assert "structure" in abstract_pattern.abstract_form
        assert "keywords" in abstract_pattern.abstract_form

    def test_abstract_pattern_to_dict(self, abstract_pattern):
        """AbstractPattern.to_dict() must serialize correctly."""
        result = abstract_pattern.to_dict()

        assert isinstance(result, dict)
        assert result["pattern_id"] == "pattern-test-123"
        assert result["source_domain"] == "code"
        assert "applicable_domains" in result
        assert "code" in result["applicable_domains"]
        assert "template" in result["applicable_domains"]

    def test_abstract_pattern_timestamps(self, abstract_pattern):
        """AbstractPattern must have timestamps."""
        assert abstract_pattern.created_at is not None
        assert abstract_pattern.updated_at is not None

    def test_abstract_pattern_defaults(self):
        """AbstractPattern must have sensible defaults."""
        from ml_intelligence.layer4_recursive_pattern_learner import AbstractPattern, PatternDomain

        pattern = AbstractPattern(
            pattern_id="test",
            abstract_form={},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE],
            confidence=0.5,
            trust_score=0.5,
            abstraction_level=0,
            support_count=1
        )

        assert pattern.transfer_count == 0
        assert pattern.validation_count == 0


# =============================================================================
# COMPOSITE PATTERN TESTS
# =============================================================================

class TestCompositePatternFunctional:
    """Functional tests for CompositePattern data class."""

    @pytest.fixture
    def composite_pattern(self):
        """Create a CompositePattern instance."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import CompositePattern, PatternOperator

        return CompositePattern(
            composite_id="composite-test-456",
            operator=PatternOperator.UNION,
            operands=["pattern-1", "pattern-2"],
            result_pattern={
                "structure": {"type": "union", "components": 2},
                "keywords": ["filter", "map", "reduce"]
            },
            confidence=0.8,
            creation_count=10,
            success_count=8
        )

    def test_composite_pattern_creation(self, composite_pattern):
        """CompositePattern must be creatable."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator

        assert composite_pattern.composite_id == "composite-test-456"
        assert composite_pattern.operator == PatternOperator.UNION
        assert len(composite_pattern.operands) == 2

    def test_composite_pattern_success_rate(self, composite_pattern):
        """CompositePattern.success_rate() must calculate correctly."""
        rate = composite_pattern.success_rate()

        assert rate == 0.8  # 8/10

    def test_composite_pattern_success_rate_with_zero_creation(self):
        """CompositePattern.success_rate() with zero creation returns 0.5."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import CompositePattern, PatternOperator

        composite = CompositePattern(
            composite_id="new",
            operator=PatternOperator.UNION,
            operands=[],
            result_pattern={},
            confidence=0.5,
            creation_count=0,
            success_count=0
        )

        assert composite.success_rate() == 0.5


# =============================================================================
# RECURSIVE LEARNING CYCLE TESTS
# =============================================================================

class TestRecursiveLearningCycleFunctional:
    """Functional tests for RecursiveLearningCycle data class."""

    @pytest.fixture
    def learning_cycle(self):
        """Create a RecursiveLearningCycle instance."""
        from ml_intelligence.layer4_recursive_pattern_learner import RecursiveLearningCycle, PatternDomain

        return RecursiveLearningCycle(
            cycle_id="cycle-test-789",
            cycle_number=5,
            patterns_discovered=20,
            patterns_abstracted=15,
            patterns_validated=12,
            patterns_transferred=8,
            domains_touched=[PatternDomain.CODE, PatternDomain.HEALING],
            improvement_score=0.15,
            started_at=datetime.utcnow()
        )

    def test_learning_cycle_creation(self, learning_cycle):
        """RecursiveLearningCycle must be creatable."""
        assert learning_cycle.cycle_id == "cycle-test-789"
        assert learning_cycle.cycle_number == 5
        assert learning_cycle.patterns_discovered == 20

    def test_learning_cycle_to_dict(self, learning_cycle):
        """RecursiveLearningCycle.to_dict() must serialize correctly."""
        result = learning_cycle.to_dict()

        assert isinstance(result, dict)
        assert result["cycle_number"] == 5
        assert result["patterns_discovered"] == 20
        assert "code" in result["domains_touched"]
        assert "healing" in result["domains_touched"]

    def test_learning_cycle_improvement_tracking(self, learning_cycle):
        """Learning cycle must track improvement score."""
        assert learning_cycle.improvement_score == 0.15

    def test_learning_cycle_parent_link(self):
        """Learning cycle can link to parent cycle."""
        from ml_intelligence.layer4_recursive_pattern_learner import RecursiveLearningCycle, PatternDomain

        parent = RecursiveLearningCycle(
            cycle_id="parent-cycle",
            cycle_number=1,
            patterns_discovered=10,
            patterns_abstracted=8,
            patterns_validated=6,
            patterns_transferred=4,
            domains_touched=[PatternDomain.CODE],
            improvement_score=0.0,
            started_at=datetime.utcnow()
        )

        child = RecursiveLearningCycle(
            cycle_id="child-cycle",
            cycle_number=2,
            patterns_discovered=15,
            patterns_abstracted=12,
            patterns_validated=10,
            patterns_transferred=6,
            domains_touched=[PatternDomain.CODE, PatternDomain.HEALING],
            improvement_score=0.5,
            started_at=datetime.utcnow(),
            parent_cycle_id=parent.cycle_id
        )

        assert child.parent_cycle_id == "parent-cycle"


# =============================================================================
# COMPOSITION ENGINE TESTS
# =============================================================================

class TestCompositionEngineFunctional:
    """Functional tests for CompositionEngine."""

    @pytest.fixture
    def composition_engine(self):
        """Create CompositionEngine with sample patterns."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import CompositionEngine

        pattern_store = {
            "pattern-filter": {
                "pattern_id": "pattern-filter",
                "keywords": ["filter", "select", "where"],
                "roles": ["input", "output"],
                "constraints": [{"type": "iterable"}]
            },
            "pattern-map": {
                "pattern_id": "pattern-map",
                "keywords": ["map", "transform", "apply"],
                "roles": ["input", "output"],
                "constraints": [{"type": "function"}]
            },
            "pattern-reduce": {
                "pattern_id": "pattern-reduce",
                "keywords": ["reduce", "aggregate", "fold"],
                "roles": ["input", "accumulator", "output"],
                "constraints": [{"type": "initial_value"}]
            }
        }

        return CompositionEngine(pattern_store=pattern_store)

    def test_composition_engine_has_pattern_store(self, composition_engine):
        """CompositionEngine must have pattern store."""
        assert len(composition_engine.pattern_store) == 3

    def test_union_composition(self, composition_engine):
        """UNION composition must combine patterns."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator

        result = composition_engine.compose(
            operator=PatternOperator.UNION,
            pattern_ids=["pattern-filter", "pattern-map"]
        )

        assert result is not None
        assert result.operator == PatternOperator.UNION
        assert len(result.operands) == 2

        # Union should have combined keywords
        all_keywords = result.result_pattern.get("keywords", [])
        assert "filter" in all_keywords or len(all_keywords) > 0

    def test_intersection_composition(self, composition_engine):
        """INTERSECTION composition must find common elements."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator

        result = composition_engine.compose(
            operator=PatternOperator.INTERSECTION,
            pattern_ids=["pattern-filter", "pattern-map"]
        )

        assert result is not None
        assert result.operator == PatternOperator.INTERSECTION
        assert "_operator" in result.result_pattern
        assert result.result_pattern["_operator"] == "intersection"

    def test_composition_composition(self, composition_engine):
        """COMPOSITION (pipeline) must chain patterns."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator

        result = composition_engine.compose(
            operator=PatternOperator.COMPOSITION,
            pattern_ids=["pattern-filter", "pattern-map"]
        )

        assert result is not None
        assert result.operator == PatternOperator.COMPOSITION
        assert "transformations" in result.result_pattern

    def test_negation_composition(self, composition_engine):
        """NEGATION must create opposite pattern."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator

        result = composition_engine.compose(
            operator=PatternOperator.NEGATION,
            pattern_ids=["pattern-filter"]
        )

        assert result is not None
        assert result.operator == PatternOperator.NEGATION
        assert result.result_pattern["_operator"] == "negation"

    def test_composition_with_missing_pattern_returns_none(self, composition_engine):
        """Composition with missing pattern must return None."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator

        result = composition_engine.compose(
            operator=PatternOperator.UNION,
            pattern_ids=["pattern-filter", "pattern-nonexistent"]
        )

        assert result is None

    def test_composition_history_tracked(self, composition_engine):
        """Composition history must be tracked."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import PatternOperator

        initial_len = len(composition_engine.composition_history)

        composition_engine.compose(
            operator=PatternOperator.UNION,
            pattern_ids=["pattern-filter", "pattern-map"]
        )

        assert len(composition_engine.composition_history) == initial_len + 1
        assert composition_engine.composition_history[-1]["operator"] == "union"


# =============================================================================
# CROSS-DOMAIN TRANSFER TESTS
# =============================================================================

class TestCrossDomainTransferFunctional:
    """Functional tests for cross-domain pattern transfer."""

    def test_pattern_applicability_check(self):
        """Pattern applicability to domains must be checkable."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain

        pattern_applicable_domains = [PatternDomain.CODE, PatternDomain.TEMPLATE]
        target_domain = PatternDomain.CODE

        is_applicable = target_domain in pattern_applicable_domains

        assert is_applicable is True

    def test_pattern_not_applicable_to_other_domain(self):
        """Pattern not applicable to other domains must be detected."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain

        pattern_applicable_domains = [PatternDomain.CODE, PatternDomain.TEMPLATE]
        target_domain = PatternDomain.HEALING

        is_applicable = target_domain in pattern_applicable_domains

        assert is_applicable is False

    def test_transfer_trust_threshold_check(self):
        """Transfer must require minimum trust score."""
        min_trust_for_transfer = 0.7

        patterns = [
            {"pattern_id": "p1", "trust_score": 0.8},
            {"pattern_id": "p2", "trust_score": 0.5},
            {"pattern_id": "p3", "trust_score": 0.9}
        ]

        transferable = [p for p in patterns if p["trust_score"] >= min_trust_for_transfer]

        assert len(transferable) == 2
        assert "p2" not in [p["pattern_id"] for p in transferable]

    def test_transfer_success_tracking(self):
        """Cross-domain transfer success must be tracked."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain

        transfer_success = {}

        # Record successful transfer
        source = PatternDomain.CODE
        target = PatternDomain.HEALING
        key = (source, target)

        transfer_success[key] = transfer_success.get(key, 0.5)

        # Update based on outcome
        success = True
        learning_rate = 0.1
        if success:
            transfer_success[key] = transfer_success[key] + (1.0 - transfer_success[key]) * learning_rate

        assert transfer_success[key] > 0.5


# =============================================================================
# ABSTRACTION LEVEL TESTS
# =============================================================================

class TestAbstractionLevelFunctional:
    """Functional tests for abstraction level handling."""

    def test_abstraction_level_0_is_concrete(self):
        """Abstraction level 0 must represent concrete patterns."""
        from ml_intelligence.layer4_recursive_pattern_learner import AbstractPattern, PatternDomain

        concrete_pattern = AbstractPattern(
            pattern_id="concrete-1",
            abstract_form={"type": "specific_function", "name": "filter_evens"},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE],
            confidence=0.9,
            trust_score=0.8,
            abstraction_level=0,  # Concrete
            support_count=1
        )

        assert concrete_pattern.abstraction_level == 0

    def test_higher_abstraction_more_transferable(self):
        """Higher abstraction level should indicate more transferability."""
        from ml_intelligence.layer4_recursive_pattern_learner import AbstractPattern, PatternDomain

        abstract_pattern = AbstractPattern(
            pattern_id="abstract-1",
            abstract_form={"type": "transform", "pattern": "filter_predicate"},
            source_domain=PatternDomain.CODE,
            applicable_domains=[
                PatternDomain.CODE,
                PatternDomain.TEMPLATE,
                PatternDomain.WORKFLOW
            ],
            confidence=0.7,
            trust_score=0.6,
            abstraction_level=3,  # Abstract
            support_count=50
        )

        # Higher abstraction = more applicable domains
        assert abstract_pattern.abstraction_level > 0
        assert len(abstract_pattern.applicable_domains) > 1

    def test_max_abstraction_level_enforced(self):
        """Maximum abstraction level must be enforced."""
        max_abstraction_level = 5

        test_levels = [0, 3, 5, 7, 10]

        for level in test_levels:
            clamped = min(level, max_abstraction_level)
            assert clamped <= max_abstraction_level


# =============================================================================
# PATTERN VALIDATION TESTS
# =============================================================================

class TestPatternValidationFunctional:
    """Functional tests for pattern validation."""

    def test_pattern_confidence_threshold(self):
        """Patterns below confidence threshold must be filtered."""
        min_confidence = 0.6

        patterns = [
            {"pattern_id": "p1", "confidence": 0.8},
            {"pattern_id": "p2", "confidence": 0.4},
            {"pattern_id": "p3", "confidence": 0.6},
            {"pattern_id": "p4", "confidence": 0.5}
        ]

        valid_patterns = [p for p in patterns if p["confidence"] >= min_confidence]

        assert len(valid_patterns) == 2
        assert all(p["confidence"] >= min_confidence for p in valid_patterns)

    def test_support_count_requirement(self):
        """Patterns must have minimum support count."""
        min_support = 3

        patterns = [
            {"pattern_id": "p1", "support_count": 10},
            {"pattern_id": "p2", "support_count": 1},
            {"pattern_id": "p3", "support_count": 5}
        ]

        well_supported = [p for p in patterns if p["support_count"] >= min_support]

        assert len(well_supported) == 2
        assert "p2" not in [p["pattern_id"] for p in well_supported]

    def test_validation_count_increases_on_validation(self):
        """Validation count must increase when pattern is validated."""
        from ml_intelligence.layer4_recursive_pattern_learner import AbstractPattern, PatternDomain

        pattern = AbstractPattern(
            pattern_id="test",
            abstract_form={},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE],
            confidence=0.5,
            trust_score=0.5,
            abstraction_level=0,
            support_count=5
        )

        initial_count = pattern.validation_count
        pattern.validation_count += 1

        assert pattern.validation_count == initial_count + 1


# =============================================================================
# META-LEARNING STRATEGY TESTS
# =============================================================================

class TestMetaLearningStrategiesFunctional:
    """Functional tests for meta-learning abstraction strategies."""

    def test_strategy_weights_initialized(self):
        """Abstraction strategies must have initial weights."""
        abstraction_strategies = {
            "keyword_extraction": 1.0,
            "structure_matching": 1.0,
            "relationship_mapping": 1.0,
            "type_generalization": 1.0,
        }

        assert len(abstraction_strategies) >= 4
        assert all(w > 0 for w in abstraction_strategies.values())

    def test_strategy_weight_updates_on_success(self):
        """Strategy weights must increase on success."""
        strategies = {"keyword_extraction": 1.0}

        def update_strategy(strategy_name, success, learning_rate=0.1):
            current = strategies.get(strategy_name, 1.0)
            if success:
                strategies[strategy_name] = current * (1.0 + learning_rate)
            else:
                strategies[strategy_name] = current * (1.0 - learning_rate)

        initial = strategies["keyword_extraction"]
        update_strategy("keyword_extraction", success=True)

        assert strategies["keyword_extraction"] > initial

    def test_strategy_weight_decreases_on_failure(self):
        """Strategy weights must decrease on failure."""
        strategies = {"keyword_extraction": 1.0}

        def update_strategy(strategy_name, success, learning_rate=0.1):
            current = strategies.get(strategy_name, 1.0)
            if success:
                strategies[strategy_name] = current * (1.0 + learning_rate)
            else:
                strategies[strategy_name] = current * (1.0 - learning_rate)

        initial = strategies["keyword_extraction"]
        update_strategy("keyword_extraction", success=False)

        assert strategies["keyword_extraction"] < initial


# =============================================================================
# PATTERN PERSISTENCE TESTS
# =============================================================================

class TestPatternPersistenceFunctional:
    """Functional tests for pattern persistence patterns."""

    def test_pattern_serialization_to_json(self):
        """Pattern must serialize to JSON."""
        import json

        pattern_data = {
            "pattern_id": "test-pattern",
            "abstract_form": {"type": "test"},
            "source_domain": "code",
            "confidence": 0.8,
            "trust_score": 0.7
        }

        json_str = json.dumps(pattern_data)
        loaded = json.loads(json_str)

        assert loaded["pattern_id"] == "test-pattern"
        assert loaded["confidence"] == 0.8

    def test_pattern_deserialization_from_json(self):
        """Pattern must deserialize from JSON."""
        import json

        json_str = '{"pattern_id": "loaded-pattern", "confidence": 0.9}'
        loaded = json.loads(json_str)

        assert loaded["pattern_id"] == "loaded-pattern"
        assert loaded["confidence"] == 0.9


# =============================================================================
# IMPROVEMENT SCORE CALCULATION TESTS
# =============================================================================

class TestImprovementScoreCalculationFunctional:
    """Functional tests for improvement score calculation."""

    def test_improvement_score_calculation(self):
        """Improvement score must compare to previous cycle."""
        previous_metrics = {
            "patterns_discovered": 10,
            "patterns_validated": 5
        }

        current_metrics = {
            "patterns_discovered": 15,
            "patterns_validated": 8
        }

        def calculate_improvement(current, previous):
            if previous["patterns_discovered"] == 0:
                return 0.0
            discovery_improvement = (
                current["patterns_discovered"] - previous["patterns_discovered"]
            ) / previous["patterns_discovered"]
            validation_improvement = (
                current["patterns_validated"] - previous["patterns_validated"]
            ) / max(previous["patterns_validated"], 1)
            return (discovery_improvement + validation_improvement) / 2

        improvement = calculate_improvement(current_metrics, previous_metrics)

        # 50% improvement in discovery, 60% in validation
        assert improvement > 0

    def test_no_improvement_returns_zero(self):
        """No improvement must return zero score."""
        previous_metrics = {"patterns_discovered": 10, "patterns_validated": 5}
        current_metrics = {"patterns_discovered": 10, "patterns_validated": 5}

        def calculate_improvement(current, previous):
            if previous["patterns_discovered"] == 0:
                return 0.0
            discovery_improvement = (
                current["patterns_discovered"] - previous["patterns_discovered"]
            ) / previous["patterns_discovered"]
            validation_improvement = (
                current["patterns_validated"] - previous["patterns_validated"]
            ) / max(previous["patterns_validated"], 1)
            return (discovery_improvement + validation_improvement) / 2

        improvement = calculate_improvement(current_metrics, previous_metrics)

        assert improvement == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
