import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from backend.cognitive.engine import CognitiveEngine, DecisionContext
from backend.cognitive.ambiguity import AmbiguityLedger

def test_engine_ooda_happy_path():
    # Mocking DecisionLogger to prevent file writes
    mock_logger = MagicMock()
    
    engine = CognitiveEngine(decision_logger=mock_logger, enable_strict_mode=True)
    
    # 1. Begin Decision
    ctx = engine.begin_decision(
        problem_statement="Test feature implementation",
        goal="Add OODA tests",
        success_criteria=["Tests pass"]
    )
    assert ctx.decision_id in engine.get_active_decisions()[0].decision_id

    # 2. Observe
    engine.observe(ctx, {
        "status": "ready",
        "unknown_var": None,
        "inferred_var": {"inferred": True, "value": "guess", "confidence": 0.6}
    })
    assert ctx.ambiguity_ledger.get("status").value == "ready"
    assert ctx.ambiguity_ledger.get("unknown_var") is not None
    assert ctx.ambiguity_ledger.get("inferred_var") is not None

    # 3. Orient
    engine.orient(ctx, 
                  constraints={"safety_critical": False, "impact_scope": "local"},
                  context_info={"environment": "test"})
    assert not ctx.is_safety_critical
    assert ctx.impact_scope == "local"

    # 4. Decide
    def mock_generater():
        return [
            {"path": "A", "immediate_value": 10, "simplicity": 0.9, "reversibility": 1.0},
            {"path": "B", "immediate_value": 5, "simplicity": 0.5, "reversibility": 0.5}
        ]
    
    best_path = engine.decide(ctx, generate_alternatives=mock_generater)
    assert best_path["path"] == "A"
    assert ctx.selected_path["alternative"]["path"] == "A"

    # 5. Act
    with patch.object(engine.invariant_validator, 'validate_all') as mock_val:
        v_result = MagicMock()
        v_result.is_valid = True
        mock_val.return_value = v_result
        
        def mock_action():
            return "SUCCESS"
            
        result = engine.act(ctx, action=mock_action)
        assert result == "SUCCESS"
        assert ctx.metadata["action_status"] == "success"

    # 6. Finalize
    engine.finalize_decision(ctx)
    assert ctx.decision_id not in [d.decision_id for d in engine.get_active_decisions()]

def test_engine_strict_mode_blocks_unknowns():
    mock_logger = MagicMock()
    engine = CognitiveEngine(decision_logger=mock_logger, enable_strict_mode=True)
    
    ctx = engine.begin_decision("Irreversible DB drop", "Drop", ["Drop complete"])
    ctx.is_reversible = False  # Irreversible action
    
    # Observe blocking unknown
    ctx.ambiguity_ledger.add_unknown("db_connected_users", blocking=True)
    engine.observe(ctx, {})
    
    # Orient should raise ValueError due to strict mode + blocking unknowns + irreversible
    with pytest.raises(ValueError, match="Blocking unknowns prevent irreversible action"):
        engine.orient(ctx, constraints={}, context_info={})

def test_engine_strict_mode_blocks_act_validation():
    mock_logger = MagicMock()
    engine = CognitiveEngine(decision_logger=mock_logger, enable_strict_mode=True)
    
    ctx = engine.begin_decision("Violate invariants", "Break stuff", [])
    
    with patch.object(engine.invariant_validator, 'validate_all') as mock_val:
        v_result = MagicMock()
        v_result.is_valid = False
        v_result.violations = ["Recursion depth exceeded"]
        mock_val.return_value = v_result
        
        with pytest.raises(ValueError, match="Invariant validation failed"):
            engine.act(ctx, action=lambda: "BAD")

def test_engine_decision_freeze():
    mock_logger = MagicMock()
    engine = CognitiveEngine(decision_logger=mock_logger)
    
    ctx = engine.begin_decision("Time test", "Time", [])
    ctx.decision_freeze_point = datetime.now(timezone.utc) - timedelta(minutes=1)
    
    assert engine.enforce_decision_freeze(ctx) is True
    
    ctx.decision_freeze_point = datetime.now(timezone.utc) + timedelta(minutes=10)
    assert engine.enforce_decision_freeze(ctx) is False
