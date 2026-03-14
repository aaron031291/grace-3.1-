import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from backend.cognitive.invariants import InvariantValidator, ValidationResult

def create_mock_context():
    context = MagicMock()
    context.problem_statement = "Fix memory leak"
    context.goal = "Keep memory below 80%"
    
    ledger = MagicMock()
    ledger.has_blocking_unknowns.return_value = False
    context.ambiguity_ledger = ledger
    
    context.is_reversible = True
    context.reversibility_justification = ""
    context.is_safety_critical = False
    context.requires_determinism = False
    context.impact_scope = "local"
    context.success_criteria = []
    context.metadata = {}
    context.complexity_score = 0
    context.benefit_score = 1
    context.recursion_depth = 0
    context.max_recursion_depth = 5
    context.iteration_count = 0
    context.max_iterations = 10
    context.preserves_future_options = True
    context.future_flexibility_metric = 1.0
    context.decision_freeze_point = None
    context.alternative_paths = []
    context.selected_path = None
    
    return context

def test_validate_all_healthy():
    validator = InvariantValidator()
    context = create_mock_context()
    
    res = validator.validate_all(context)
    # The only issue is warning for alternative paths
    assert res.is_valid is True
    assert len(res.violations) == 0

def test_validate_all_missing_problem():
    validator = InvariantValidator()
    context = create_mock_context()
    context.problem_statement = ""
    
    res = validator.validate_all(context)
    assert res.is_valid is False
    assert "Invariant 1: No problem statement (OODA Observe missing)" in res.violations

def test_validate_invariant_specific():
    validator = InvariantValidator()
    context = create_mock_context()
    context.is_safety_critical = True
    context.requires_determinism = False
    
    res = validator.validate_invariant(4, context)
    assert res.is_valid is False
    assert "Safety-critical operations must be deterministic" in res.violations

if __name__ == "__main__":
    pytest.main(['-v', __file__])
