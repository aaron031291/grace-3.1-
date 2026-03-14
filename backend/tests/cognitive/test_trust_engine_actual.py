import pytest
from backend.cognitive.trust_engine import TrustEngine

def test_score_output():
    engine = TrustEngine()
    
    # good content
    output = "def good_code():\n    '''This is good'''\n    return True\n"
    res = engine.score_output("comp1", "Component 1", output, source="deterministic")
    
    assert res.trust_score >= 80

def test_score_poor_output():
    engine = TrustEngine()
    
    # bad content
    output = "eval('unsafe')\n TODO FIXME os.system('bad')\n"
    res = engine.score_output("comp2", "Component 2", output, source="unknown")
    
    assert res.trust_score < 70
    assert res.needs_remediation is True

def test_trigger_remediation():
    engine = TrustEngine()
    # Force low trust
    res = engine.score_output("comp_rem", "Component Rem", "eval('x') TODO TODO FIXME FIXME \n"*5, source="unknown")
    assert res.trust_score < 60
    
    rem_res = engine.trigger_remediation("comp_rem")
    assert rem_res["action"] == "coding_agent"
    
def test_get_system_trust():
    engine = TrustEngine()
    
    engine.score_output("c1", "Good", "def a(): '''good''' return 1", "deterministic")
    system_trust = engine.get_system_trust()
    
    assert system_trust["component_count"] == 1
    assert "c1" in system_trust["components"]

if __name__ == "__main__":
    pytest.main(['-v', __file__])
