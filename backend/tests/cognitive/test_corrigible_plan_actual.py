import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.corrigible_plan import CorrigiblePlan, get_corrigible_plan

def test_singleton():
    p1 = get_corrigible_plan()
    assert isinstance(p1, CorrigiblePlan)

def test_prove_geometric_safety():
    plan = CorrigiblePlan()
    plan.z3_solver = None
    
    with patch("backend.cognitive.corrigible_plan.time.time", side_effect=[0, 0.01]):
        res = plan._prove_geometric_safety("test_ast")
        assert res is True
        
def test_prove_geometric_safety_fails():
    plan = CorrigiblePlan()
    plan.z3_solver = None
    
    with patch("backend.cognitive.corrigible_plan.time.time", side_effect=[0, 0.01]):
        res = plan._prove_geometric_safety("")
        assert res is False

@patch("backend.cognitive.corrigible_plan.CorrigiblePlan._prove_geometric_safety")
@patch("core.dynamic_dictionary.get_dynamic_dictionary")
def test_draft_autonomous_action(mock_get_dict, mock_prove):
    plan = CorrigiblePlan()
    
    mock_dict = MagicMock()
    mock_dict.lookup_word.return_value = "braille_mock"
    mock_get_dict.return_value = mock_dict
    
    mock_prove.return_value = True
    
    res = plan.draft_autonomous_action("health check failed")
    assert res is not None
    assert res["action_type"] == "heal"
    assert res["braille_intent"] == "braille_mock"
    assert res["status"] == "provably_safe"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
