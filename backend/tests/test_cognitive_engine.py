"""
Tests for the cognitive engine and invariant enforcement.

These tests validate that the 12 invariants are properly enforced.
"""
import pytest
from datetime import datetime, timedelta

from cognitive.engine import CognitiveEngine, DecisionContext
from cognitive.ooda import OODALoop, OODAPhase
from cognitive.ambiguity import AmbiguityLedger, AmbiguityLevel
from cognitive.invariants import InvariantValidator
from cognitive.decision_log import DecisionLogger


# ==================== Test OODA Loop (Invariant 1) ====================

def test_ooda_loop_enforces_order():
    """Test that OODA loop enforces proper phase ordering."""
    ooda = OODALoop()

    # Should start in OBSERVE phase
    assert ooda.state.current_phase == OODAPhase.OBSERVE

    # Can observe
    ooda.observe({'fact': 'value'})
    assert ooda.state.current_phase == OODAPhase.ORIENT

    # Can orient
    ooda.orient({'context': 'data'}, {'constraint': 'value'})
    assert ooda.state.current_phase == OODAPhase.DECIDE

    # Can decide
    ooda.decide({'plan': 'action'})
    assert ooda.state.current_phase == OODAPhase.ACT

    # Can act
    result = ooda.act(lambda: "result")
    assert ooda.state.current_phase == OODAPhase.COMPLETED
    assert result == "result"

    # Should have valid history
    assert ooda.validate_completion()


def test_ooda_loop_prevents_skipping():
    """Test that OODA loop prevents skipping phases."""
    ooda = OODALoop()

    # Cannot skip to orient without observing
    # Already in OBSERVE, so move forward
    ooda.observe({'fact': 'value'})

    # Try to skip DECIDE
    with pytest.raises(ValueError, match="Cannot act"):
        ooda.act(lambda: "result")


def test_ooda_loop_prevents_direct_execution():
    """Test that actions cannot bypass OODA."""
    ooda = OODALoop()

    # Cannot act without going through observe/orient/decide
    with pytest.raises(ValueError, match="Cannot act"):
        ooda.act(lambda: "result")


# ==================== Test Ambiguity Accounting (Invariant 2) ====================

def test_ambiguity_ledger_tracks_levels():
    """Test that ambiguity ledger tracks all levels correctly."""
    ledger = AmbiguityLedger()

    # Add entries at each level
    ledger.add_known('fact1', 'value1')
    ledger.add_inferred('fact2', 'value2', confidence=0.8)
    ledger.add_assumed('fact3', 'value3', must_validate=True)
    ledger.add_unknown('fact4', blocking=True)

    # Verify counts
    assert len(ledger.get_by_level(AmbiguityLevel.KNOWN)) == 1
    assert len(ledger.get_by_level(AmbiguityLevel.INFERRED)) == 1
    assert len(ledger.get_by_level(AmbiguityLevel.ASSUMED)) == 1
    assert len(ledger.get_by_level(AmbiguityLevel.UNKNOWN)) == 1


def test_ambiguity_ledger_blocks_on_unknowns():
    """Test that blocking unknowns are properly tracked."""
    ledger = AmbiguityLedger()

    ledger.add_unknown('critical_data', blocking=True)
    ledger.add_unknown('optional_data', blocking=False)

    blocking = ledger.get_blocking_unknowns()
    assert len(blocking) == 1
    assert blocking[0].key == 'critical_data'


def test_ambiguity_promotion():
    """Test that unknowns can be promoted to known."""
    ledger = AmbiguityLedger()

    ledger.add_unknown('data', blocking=True)
    assert ledger.has_blocking_unknowns()

    ledger.promote_to_known('data', 'actual_value')
    assert not ledger.has_blocking_unknowns()

    entry = ledger.get('data')
    assert entry.level == AmbiguityLevel.KNOWN
    assert entry.value == 'actual_value'


# ==================== Test Reversibility (Invariant 3) ====================

def test_irreversible_requires_justification():
    """Test that irreversible actions require justification."""
    validator = InvariantValidator()

    context = DecisionContext(
        problem_statement="Delete data",
        goal="Remove data",
        success_criteria=["Data deleted"],
        is_reversible=False,
        reversibility_justification=None  # Missing!
    )

    result = validator.validate_all(context)
    assert not result.is_valid
    assert any("justification" in v.lower() for v in result.violations)


def test_blocking_unknowns_prevent_irreversible():
    """Test that blocking unknowns prevent irreversible actions."""
    validator = InvariantValidator()

    context = DecisionContext(
        problem_statement="Delete data",
        goal="Remove data",
        success_criteria=["Data deleted"],
        is_reversible=False,
        reversibility_justification="Test deletion"
    )

    context.ambiguity_ledger.add_unknown('backup_exists', blocking=True)

    result = validator.validate_all(context)
    assert not result.is_valid
    assert any("blocking unknowns" in v.lower() for v in result.violations)


# ==================== Test Bounded Recursion (Invariant 9) ====================

def test_recursion_depth_limit_enforced():
    """Test that recursion depth limits are enforced."""
    validator = InvariantValidator()

    context = DecisionContext(
        problem_statement="Process nested data",
        goal="Complete processing",
        success_criteria=["All data processed"],
        recursion_depth=3,
        max_recursion_depth=3
    )

    result = validator.validate_all(context)
    assert not result.is_valid
    assert any("recursion depth" in v.lower() for v in result.violations)


def test_iteration_limit_enforced():
    """Test that iteration limits are enforced."""
    validator = InvariantValidator()

    context = DecisionContext(
        problem_statement="Iterate over data",
        goal="Process all items",
        success_criteria=["All items processed"],
        iteration_count=5,
        max_iterations=5
    )

    result = validator.validate_all(context)
    assert not result.is_valid
    assert any("iteration limit" in v.lower() for v in result.violations)


# ==================== Test Time-Bounded Reasoning (Invariant 11) ====================

def test_decision_freeze_point_enforced():
    """Test that decision freeze points are enforced."""
    validator = InvariantValidator()

    context = DecisionContext(
        problem_statement="Make decision",
        goal="Decide on action",
        success_criteria=["Decision made"],
        decision_freeze_point=datetime.utcnow() - timedelta(seconds=1)  # Past
    )

    result = validator.validate_all(context)
    assert not result.is_valid
    assert any("freeze point" in v.lower() for v in result.violations)


# ==================== Test Forward Simulation (Invariant 12) ====================

def test_alternative_paths_required():
    """Test that alternative paths are considered (warning)."""
    validator = InvariantValidator()

    context = DecisionContext(
        problem_statement="Execute action",
        goal="Complete action",
        success_criteria=["Action completed"],
        alternative_paths=[]  # No alternatives!
    )

    result = validator.validate_all(context)
    # Should have warning (not violation)
    assert any("alternative" in w.lower() for w in result.warnings)


def test_chess_mode_path_selection():
    """Test that path selection works in chess mode."""
    engine = CognitiveEngine()

    context = engine.begin_decision(
        problem_statement="Select strategy",
        goal="Choose optimal path",
        success_criteria=["Path selected"]
    )

    engine.observe(context, {'data': 'value'})
    engine.orient(context, {}, {})

    def generate_alternatives():
        return [
            {
                'name': 'fast_path',
                'immediate_value': 0.5,
                'future_options': 1.0,
                'simplicity': 1.0,
                'reversibility': 1.0,
                'complexity': 0.1
            },
            {
                'name': 'optimal_path',
                'immediate_value': 1.0,
                'future_options': 0.8,
                'simplicity': 0.7,
                'reversibility': 1.0,
                'complexity': 0.3
            }
        ]

    selected = engine.decide(context, generate_alternatives)

    # Should select path with highest score
    assert selected is not None
    assert 'name' in selected


# ==================== Test Cognitive Engine Integration ====================

def test_full_decision_cycle():
    """Test complete decision cycle with all invariants."""
    engine = CognitiveEngine(enable_strict_mode=True)

    context = engine.begin_decision(
        problem_statement="Process document",
        goal="Ingest and index document",
        success_criteria=[
            "Document parsed",
            "Chunks created",
            "Vectors stored"
        ]
    )

    # OBSERVE
    engine.observe(context, {
        'filepath': '/path/to/doc.pdf',
        'file_size': 1024000
    })

    # Track ambiguity
    context.ambiguity_ledger.add_known('filepath', '/path/to/doc.pdf')
    context.ambiguity_ledger.add_inferred(
        'chunk_count',
        100,
        confidence=0.7
    )

    # ORIENT
    engine.orient(context, {
        'safety_critical': False,
        'impact_scope': 'local'
    }, {
        'system_ready': True
    })

    # DECIDE
    def generate_alternatives():
        return [{
            'name': 'standard_ingestion',
            'immediate_value': 1.0,
            'future_options': 1.0,
            'simplicity': 1.0,
            'reversibility': 1.0,
            'complexity': 0.2
        }]

    selected = engine.decide(context, generate_alternatives)

    # ACT
    def action():
        return {'status': 'success', 'chunks': 10}

    result = engine.act(context, action)

    assert result['status'] == 'success'

    # Finalize
    engine.finalize_decision(context)

    # Should no longer be active
    assert context.decision_id not in [c.decision_id for c in engine.get_active_decisions()]


def test_decision_logging():
    """Test that all decisions are logged."""
    logger = DecisionLogger()
    engine = CognitiveEngine(decision_logger=logger, enable_strict_mode=False)

    context = engine.begin_decision(
        problem_statement="Test logging",
        goal="Verify logs created",
        success_criteria=["Logs exist"]
    )

    # Check that start was logged
    logs = logger.get_decision_log(context.decision_id)
    assert len(logs) > 0
    assert logs[0]['event'] == 'decision_start'

    engine.observe(context, {'test': 'data'})
    engine.orient(context, {}, {})

    def generate_alternatives():
        return [{'name': 'test', 'immediate_value': 1.0, 'future_options': 1.0,
                 'simplicity': 1.0, 'reversibility': 1.0, 'complexity': 0.1}]

    engine.decide(context, generate_alternatives)

    # Check alternatives logged
    logs = logger.get_decision_log(context.decision_id)
    assert any(log['event'] == 'alternatives_considered' for log in logs)

    engine.act(context, lambda: "result")

    # Check completion logged
    logs = logger.get_decision_log(context.decision_id)
    assert any(log['event'] == 'decision_complete' for log in logs)


def test_strict_mode_enforcement():
    """Test that strict mode enforces all invariants."""
    engine = CognitiveEngine(enable_strict_mode=True)

    context = engine.begin_decision(
        problem_statement="Test strict enforcement",
        goal="Verify strict mode",
        success_criteria=["Invariants enforced"],
        is_reversible=False  # Irreversible
    )

    # Add blocking unknown
    context.ambiguity_ledger.add_unknown('critical_data', blocking=True)

    engine.observe(context, {'test': 'data'})

    # Should raise error in strict mode
    with pytest.raises(ValueError, match="Blocking unknowns"):
        engine.orient(context, {}, {})


# ==================== Test Simplicity Constraint (Invariant 7) ====================

def test_complexity_must_justify_benefit():
    """Test that complexity requires measurable benefit."""
    validator = InvariantValidator()

    context = DecisionContext(
        problem_statement="Complex operation",
        goal="Complete operation",
        success_criteria=["Operation done"],
        complexity_score=5.0,
        benefit_score=2.0  # Complexity exceeds benefit!
    )

    result = validator.validate_all(context)
    # Should have warning
    assert any("complexity" in w.lower() and "benefit" in w.lower() for w in result.warnings)


# ==================== Test Optionality (Invariant 10) ====================

def test_optionality_scoring():
    """Test that future options are weighted in scoring."""
    engine = CognitiveEngine()

    context = DecisionContext(
        problem_statement="Test",
        goal="Test",
        success_criteria=["Test"]
    )

    # Path with high future options should score higher
    alt1 = {
        'immediate_value': 0.5,
        'future_options': 1.0,
        'simplicity': 1.0,
        'reversibility': 1.0,
        'complexity': 0.1
    }

    alt2 = {
        'immediate_value': 0.8,
        'future_options': 0.2,  # Low future options
        'simplicity': 1.0,
        'reversibility': 1.0,
        'complexity': 0.1
    }

    score1 = engine._score_alternative(context, alt1)
    score2 = engine._score_alternative(context, alt2)

    # Path with better future options should score higher
    assert score1 > score2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
