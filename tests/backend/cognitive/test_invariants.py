import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from backend.cognitive.engine import DecisionContext
from backend.cognitive.invariants import InvariantValidator
from backend.cognitive.ambiguity import AmbiguityLedger

@pytest.fixture
def validator():
    return InvariantValidator()

@pytest.fixture
def valid_context():
    ctx = DecisionContext(
        problem_statement="Test statement",
        goal="Test goal",
        success_criteria=["Test success"]
    )
    ctx.is_reversible = True
    ctx.alternative_paths = [{"path": "A"}, {"path": "B"}]
    ctx.selected_path = {"path": "A"}
    return ctx

def test_validate_all_happy_path(validator, valid_context):
    result = validator.validate_all(valid_context)
    assert result.is_valid is True
    assert len(result.violations) == 0

def test_invariant_1_ooda(validator, valid_context):
    valid_context.problem_statement = ""
    result = validator.validate_all(valid_context)
    assert not result.is_valid
    assert any("Invariant 1: No problem statement" in v for v in result.violations)

    valid_context.problem_statement = "Valid"
    valid_context.goal = ""
    result = validator.validate_all(valid_context)
    assert not result.is_valid
    assert any("Invariant 1: No goal defined" in v for v in result.violations)

def test_invariant_2_ambiguity(validator, valid_context):
    valid_context.is_reversible = False
    valid_context.ambiguity_ledger.add_unknown("blocker", blocking=True)
    
    result = validator.validate_all(valid_context)
    assert not result.is_valid
    assert any("Invariant 2: Blocking unknowns prevent irreversible action" in v for v in result.violations)

def test_invariant_3_reversibility(validator, valid_context):
    valid_context.is_reversible = False
    valid_context.reversibility_justification = None
    
    result = validator.validate_all(valid_context)
    assert not result.is_valid
    assert any("Invariant 3: Irreversible action requires explicit justification" in v for v in result.violations)

def test_invariant_4_determinism(validator, valid_context):
    valid_context.is_safety_critical = True
    valid_context.requires_determinism = False
    
    result = validator.validate_all(valid_context)
    assert not result.is_valid
    assert any("Invariant 4: Safety-critical operations must be deterministic" in v for v in result.violations)

def test_invariant_5_blast_radius(validator, valid_context):
    valid_context.impact_scope = "systemic"
    valid_context.success_criteria = []
    
    result = validator.validate_all(valid_context)
    assert not result.is_valid
    assert any("Invariant 5: Systemic changes require detailed success criteria" in v for v in result.violations)

def test_invariant_7_complexity(validator, valid_context):
    valid_context.complexity_score = 10
    valid_context.benefit_score = 5
    
    result = validator.validate_all(valid_context)
    # This one is a warning, not a violation based on code
    assert result.is_valid is True
    assert any("Invariant 7: Complexity (10) exceeds benefit (5)" in w for w in result.warnings)

def test_invariant_9_bounded_recursion(validator, valid_context):
    valid_context.recursion_depth = 5
    valid_context.max_recursion_depth = 3
    
    result = validator.validate_all(valid_context)
    assert not result.is_valid
    assert any("Invariant 9: Recursion depth limit exceeded" in v for v in result.violations)

def test_invariant_11_time_bounds(validator, valid_context):
    valid_context.decision_freeze_point = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    result = validator.validate_all(valid_context)
    assert not result.is_valid
    assert any("Invariant 11: Decision freeze point exceeded" in v for v in result.violations)

def test_invariant_12_forward_simulation(validator, valid_context):
    valid_context.alternative_paths = []
    
    result = validator.validate_all(valid_context)
    # Warning for no alternatives
    assert result.is_valid is True
    assert any("Invariant 12: No alternative paths considered" in w for w in result.warnings)
    
    valid_context.alternative_paths = [{"path": "A"}]
    valid_context.selected_path = None
    result = validator.validate_all(valid_context)
    # Violation if paths generated but none selected
    assert not result.is_valid
    assert any("Invariant 12: Alternative paths generated but none selected" in v for v in result.violations)

def test_validate_single_invariant(validator, valid_context):
    valid_context.is_reversible = False
    valid_context.reversibility_justification = None
    
    # Just validate invariant #3
    res_3 = validator.validate_invariant(3, valid_context)
    assert not res_3.is_valid
    assert any("Irreversible action requires justification" in v for v in res_3.violations)
    
    # Invariant 4 should still be valid
    res_4 = validator.validate_invariant(4, valid_context)
    assert res_4.is_valid
