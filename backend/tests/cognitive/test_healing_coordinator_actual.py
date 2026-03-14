import pytest
from unittest.mock import patch, MagicMock
from backend.cognitive.healing_coordinator import HealingCoordinator, get_coordinator

def test_singleton():
    c1 = get_coordinator()
    c2 = get_coordinator()
    assert c1 is c2

@patch("backend.cognitive.healing_coordinator.HealingCoordinator._step_self_heal")
@patch("backend.cognitive.healing_coordinator.HealingCoordinator._record_outcome")
@patch("backend.cognitive.healing_coordinator.HealingCoordinator._publish_to_spindle")
def test_resolve_self_heal_success(m_pub, m_rec, m_heal):
    m_heal.return_value = {"step": "self_heal", "resolved": True}
    
    coord = HealingCoordinator()
    problem = {"component": "db", "description": "db down"}
    
    res = coord.resolve(problem)
    assert res["resolved"] is True
    assert res["resolution"] == "self_healing"
    assert len(res["steps"]) == 1
    assert m_rec.called

@patch("backend.cognitive.healing_coordinator.HealingCoordinator._step_self_heal")
@patch("backend.cognitive.healing_coordinator.HealingCoordinator._step_diagnose")
@patch("backend.cognitive.healing_coordinator.HealingCoordinator._step_agree_fix")
@patch("backend.cognitive.healing_coordinator.HealingCoordinator._step_code_fix")
def test_resolve_code_fix_success(m_code_fix, m_agree, m_diag, m_self_heal):
    m_self_heal.return_value = {"resolved": False}
    m_diag.return_value = {"grace": "diag1"}
    m_agree.return_value = {"fix_type": "code_fix"}
    m_code_fix.return_value = {"resolved": True, "fix": "fixed code"}
    
    coord = HealingCoordinator()
    problem = {"component": "logic", "description": "syntax error"}
    
    res = coord.resolve(problem)
    assert res["resolved"] is True
    assert res["resolution"] == "coding_agent"
    assert len(res["steps"]) == 4

if __name__ == "__main__":
    pytest.main(['-v', __file__])
