"""
Tests for enhanced_consistency_checker.py logical relationship methods.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from cognitive.enhanced_consistency_checker import ConsistencyChecker


class TestExtractLogicalRelationships:
    """Tests for _extract_logical_relationships method."""

    @pytest.fixture
    def checker(self):
        return ConsistencyChecker(use_semantic_detection=False)

    def test_extracts_subject_verb_object_patterns(self, checker):
        """Test extraction of basic SVO patterns."""
        text = "Python is a programming language"
        relationships = checker._extract_logical_relationships(text)
        
        svo_rels = [r for r in relationships if r["type"] == "svo"]
        assert len(svo_rels) >= 1
        assert any(
            r["subject"].lower() == "python" and 
            r["predicate"] == "is" and 
            "programming" in r["object"].lower()
            for r in svo_rels
        )

    def test_extracts_numerical_comparisons(self, checker):
        """Test extraction of numerical comparison patterns."""
        test_cases = [
            ("X is greater than Y", "greater_than"),
            ("A is less than B", "less_than"),
            ("value equals 10", "equals"),
            ("count > limit", "greater_than"),
            ("price < budget", "less_than"),
        ]
        
        for text, expected_type in test_cases:
            relationships = checker._extract_logical_relationships(text)
            numerical_rels = [r for r in relationships if r["type"] == expected_type]
            assert len(numerical_rels) >= 1, f"Failed to extract {expected_type} from: {text}"

    def test_extracts_conditional_relationships(self, checker):
        """Test extraction of conditional (if-then) patterns."""
        test_cases = [
            "if condition is true, then action happens",
            "when user logs in, show dashboard",
            "A implies B",
        ]
        
        for text in test_cases:
            relationships = checker._extract_logical_relationships(text)
            conditional_rels = [r for r in relationships if r["type"] == "conditional"]
            assert len(conditional_rels) >= 1, f"Failed to extract conditional from: {text}"
            assert conditional_rels[0]["predicate"] == "implies"

    def test_extracts_negations(self, checker):
        """Test extraction of negation patterns."""
        test_cases = [
            "X is not valid",
            "feature isn't enabled",
            "system does not work",
            "no user has access",
        ]
        
        for text in test_cases:
            relationships = checker._extract_logical_relationships(text)
            negated_rels = [r for r in relationships if r.get("negated", False)]
            assert len(negated_rels) >= 1, f"Failed to extract negation from: {text}"

    def test_returns_correct_format(self, checker):
        """Test that returned relationships have correct structure."""
        text = "The system is active and X is greater than Y"
        relationships = checker._extract_logical_relationships(text)
        
        for rel in relationships:
            assert "type" in rel
            assert "subject" in rel
            assert "predicate" in rel
            assert "object" in rel
            assert "negated" in rel
            assert isinstance(rel["negated"], bool)

    def test_empty_input_returns_empty_list(self, checker):
        """Test that empty input returns empty list."""
        assert checker._extract_logical_relationships("") == []
        assert checker._extract_logical_relationships(None) == []
        assert checker._extract_logical_relationships("   ") == []


class TestAreLogicallyInconsistent:
    """Tests for _are_logically_inconsistent method."""

    @pytest.fixture
    def checker(self):
        return ConsistencyChecker(use_semantic_detection=False)

    def test_detects_negation_contradictions(self, checker):
        """Test detection of 'X is Y' vs 'X is not Y'."""
        rel1 = {"type": "svo", "subject": "x", "predicate": "is", "object": "y", "negated": False}
        rel2 = {"type": "svo", "subject": "x", "predicate": "is", "object": "y", "negated": True}
        
        assert checker._are_logically_inconsistent(rel1, rel2) is True

    def test_detects_opposite_predicates(self, checker):
        """Test detection of opposite predicates like enabled/disabled."""
        rel1 = {"type": "svo", "subject": "feature", "predicate": "enabled", "object": "", "negated": False}
        rel2 = {"type": "svo", "subject": "feature", "predicate": "disabled", "object": "", "negated": False}
        
        assert checker._are_logically_inconsistent(rel1, rel2) is True

    def test_detects_numerical_contradictions_greater_less(self, checker):
        """Test detection of 'X > Y' vs 'X < Y'."""
        rel1 = {"type": "greater_than", "subject": "x", "predicate": "greater_than", "object": "y", "negated": False}
        rel2 = {"type": "less_than", "subject": "x", "predicate": "less_than", "object": "y", "negated": False}
        
        assert checker._are_logically_inconsistent(rel1, rel2) is True

    def test_detects_numerical_contradictions_swapped_operands(self, checker):
        """Test detection of 'X > Y' vs 'Y > X' (contradictory ordering)."""
        rel1 = {"type": "greater_than", "subject": "x", "predicate": "greater_than", "object": "y", "negated": False}
        rel2 = {"type": "greater_than", "subject": "y", "predicate": "greater_than", "object": "x", "negated": False}
        
        assert checker._are_logically_inconsistent(rel1, rel2) is True

    def test_returns_false_for_consistent_pairs(self, checker):
        """Test that consistent relationships return False."""
        rel1 = {"type": "svo", "subject": "x", "predicate": "is", "object": "red", "negated": False}
        rel2 = {"type": "svo", "subject": "x", "predicate": "is", "object": "large", "negated": False}
        
        assert checker._are_logically_inconsistent(rel1, rel2) is False

    def test_returns_true_for_inconsistent_pairs(self, checker):
        """Test that inconsistent relationships return True."""
        rel1 = {"type": "svo", "subject": "config", "predicate": "valid", "object": "", "negated": False}
        rel2 = {"type": "svo", "subject": "config", "predicate": "invalid", "object": "", "negated": False}
        
        assert checker._are_logically_inconsistent(rel1, rel2) is True

    def test_x_is_y_vs_x_is_not_y_inconsistent(self, checker):
        """Specific test: 'X is Y' vs 'X is not Y' -> inconsistent."""
        rel1 = {"type": "svo", "subject": "x", "predicate": "is", "object": "y", "negated": False}
        rel2 = {"type": "svo", "subject": "x", "predicate": "is", "object": "y", "negated": True}
        
        assert checker._are_logically_inconsistent(rel1, rel2) is True

    def test_x_greater_y_vs_x_less_y_inconsistent(self, checker):
        """Specific test: 'X > Y' vs 'X < Y' -> inconsistent."""
        rel1 = {"type": "greater_than", "subject": "x", "predicate": "greater_than", "object": "y", "negated": False}
        rel2 = {"type": "less_than", "subject": "x", "predicate": "less_than", "object": "y", "negated": False}
        
        assert checker._are_logically_inconsistent(rel1, rel2) is True

    def test_x_enabled_vs_x_disabled_inconsistent(self, checker):
        """Specific test: 'X is enabled' vs 'X is disabled' -> inconsistent."""
        rel1 = {"type": "svo", "subject": "x", "predicate": "enabled", "object": "", "negated": False}
        rel2 = {"type": "svo", "subject": "x", "predicate": "disabled", "object": "", "negated": False}
        
        assert checker._are_logically_inconsistent(rel1, rel2) is True

    def test_x_is_y_vs_x_is_z_consistent(self, checker):
        """Specific test: 'X is Y' vs 'X is Z' (different Z) -> consistent (multiple attributes)."""
        rel1 = {"type": "svo", "subject": "x", "predicate": "is", "object": "fast", "negated": False}
        rel2 = {"type": "svo", "subject": "x", "predicate": "is", "object": "reliable", "negated": False}
        
        assert checker._are_logically_inconsistent(rel1, rel2) is False

    def test_handles_empty_relationships(self, checker):
        """Test that empty relationships return False."""
        assert checker._are_logically_inconsistent({}, {}) is False
        assert checker._are_logically_inconsistent(None, None) is False
        assert checker._are_logically_inconsistent({}, None) is False

    def test_active_vs_inactive_inconsistent(self, checker):
        """Test active/inactive as opposite predicates."""
        rel1 = {"type": "svo", "subject": "service", "predicate": "active", "object": "", "negated": False}
        rel2 = {"type": "svo", "subject": "service", "predicate": "inactive", "object": "", "negated": False}
        
        assert checker._are_logically_inconsistent(rel1, rel2) is True

    def test_true_vs_false_inconsistent(self, checker):
        """Test true/false as opposite predicates."""
        rel1 = {"type": "svo", "subject": "flag", "predicate": "true", "object": "", "negated": False}
        rel2 = {"type": "svo", "subject": "flag", "predicate": "false", "object": "", "negated": False}
        
        assert checker._are_logically_inconsistent(rel1, rel2) is True

    def test_different_subjects_consistent(self, checker):
        """Test that different subjects are consistent even with contradictory predicates."""
        rel1 = {"type": "svo", "subject": "x", "predicate": "enabled", "object": "", "negated": False}
        rel2 = {"type": "svo", "subject": "y", "predicate": "disabled", "object": "", "negated": False}
        
        assert checker._are_logically_inconsistent(rel1, rel2) is False
