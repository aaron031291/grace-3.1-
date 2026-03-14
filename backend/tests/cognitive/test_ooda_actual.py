import pytest
from backend.cognitive.ooda import OODALoop, OODAPhase

def test_ooda_loop_sequence():
    loop = OODALoop()
    
    assert loop.state.current_phase == OODAPhase.OBSERVE
    
    loop.observe({"fact": 1})
    assert loop.state.current_phase == OODAPhase.ORIENT
    
    loop.orient({"context": "test"}, {"constraint": "none"})
    assert loop.state.current_phase == OODAPhase.DECIDE
    
    loop.decide({"plan": "A"})
    assert loop.state.current_phase == OODAPhase.ACT
    
    def dummy_action():
        return "success"
        
    res = loop.act(dummy_action)
    assert res == "success"
    assert loop.state.current_phase == OODAPhase.COMPLETED
    assert loop.validate_completion() is True

def test_ooda_invalid_sequence():
    loop = OODALoop()
    with pytest.raises(ValueError):
        loop.orient({}, {})

if __name__ == "__main__":
    pytest.main(['-v', __file__])
