import pytest
from backend.cognitive.corrigible_plan import CorrigiblePlan

def test_corrigible_plan_draft_autonomous_action(monkeypatch):
    """Test drafting an action mapped to the dynamic dictionary."""
    class MockSemanticDict:
        def lookup_word(self, word):
            if word == "heal":
                return "101010"
            return None
            
    import core.dynamic_dictionary as dd
    monkeypatch.setattr(dd, "get_dynamic_dictionary", lambda: MockSemanticDict())
    
    plan = CorrigiblePlan()
    # Mock Z3 check since Z3 might not be installed or behaving correctly in CI
    monkeypatch.setattr(plan, "_prove_geometric_safety", lambda mask: True)
    
    result = plan.draft_autonomous_action("system failed health check")
    
    assert result is not None
    assert result["action_type"] == "heal"
    assert result["braille_intent"] == "101010"
    assert result["status"] == "provably_safe"
    assert "AST_DELTA_MASK:[101010]_TARGET:" in result["ast_mask"]

def test_corrigible_plan_no_mapping(monkeypatch):
    class MockSemanticDict:
        def lookup_word(self, word):
            return None
            
    import backend.core.dynamic_dictionary as dd
    monkeypatch.setattr(dd, "get_dynamic_dictionary", lambda: MockSemanticDict())
    
    plan = CorrigiblePlan()
    result = plan.draft_autonomous_action("unknown trigger")
    assert result is None

if __name__ == "__main__":
    pytest.main(['-v', __file__])
