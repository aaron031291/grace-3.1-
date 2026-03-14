import pytest
from backend.cognitive.user_intent_override import get_override_system

def test_override_analyse_destructive():
    system = get_override_system()
    res = system.analyse("Please delete the database")
    
    assert res.parsed_action == "destructive_operation"
    assert res.blast_radius == "system-wide"
    assert res.override_token is not None

def test_override_execute():
    system = get_override_system()
    res = system.analyse("skip the verification pipeline")
    
    token = res.override_token
    assert token is not None
    
    exec_res = system.execute_override(token)
    assert exec_res["executed"] is True
    
    # Try again
    exec_res_2 = system.execute_override(token)
    assert exec_res_2["executed"] is False

if __name__ == "__main__":
    pytest.main(['-v', __file__])
