import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.engine import CognitiveEngine, DecisionContext

def test_engine_begin_decision():
    engine = CognitiveEngine(enable_strict_mode=False)
    ctx = engine.begin_decision("problem", "goal", ["criteria 1"])
    
    assert ctx.decision_id in engine._active_contexts
    assert ctx.problem_statement == "problem"

def test_engine_ooda_flow():
    engine = CognitiveEngine(enable_strict_mode=False)
    ctx = engine.begin_decision("prob", "goal", [])
    
    engine.observe(ctx, {"key": "value"})
    assert "key" in ctx.ambiguity_ledger._entries
    
    # Needs to mock invariant validator to prevent failure
    with patch("backend.cognitive.engine.InvariantValidator") as MockValidator:
        mock_val = MagicMock()
        mock_val.validate_all.return_value = MagicMock(is_valid=True)
        engine.invariant_validator = mock_val
        
        engine.orient(ctx, {"safety_critical": False}, {})
        assert ctx.is_safety_critical is False
        
        def gen_alts():
            return [{"id": 1, "immediate_value": 10}, {"id": 2, "immediate_value": 5}]
            
        decision = engine.decide(ctx, gen_alts)
        assert decision["id"] == 1
        
        def dummy_action():
            return "done"
            
        res = engine.act(ctx, dummy_action)
        assert res == "done"

def test_enforce_decision_freeze():
    engine = CognitiveEngine(enable_strict_mode=False)
    ctx = engine.begin_decision("prob", "goal", [])
    
    assert engine.enforce_decision_freeze(ctx) is False

if __name__ == "__main__":
    pytest.main(['-v', __file__])
