import pytest
from backend.cognitive.circuit_breaker import enter_loop, exit_loop, protected_call, get_loop_status

def test_circuit_breaker_enter_exit():
    loop_name = "test_enter_exit_loop"
    
    assert enter_loop(loop_name) is True
    exit_loop(loop_name)

def test_circuit_breaker_max_depth():
    loop_name = "healing_homeostasis" # Max depth is 5
    
    # Need to clean up depths because of globals potentially altered by other tests
    while not enter_loop(loop_name):
        exit_loop(loop_name)
    exit_loop(loop_name)
    
    # We should be able to enter 5 times
    for _ in range(5):
        assert enter_loop(loop_name) is True
        
    # The 6th should be False
    assert enter_loop(loop_name) is False
    
    # Reset
    for _ in range(5):
        exit_loop(loop_name)

def test_protected_call():
    loop_name = "test_loop_unknown"
    def my_func():
        return "success"
        
    res = protected_call(loop_name, my_func)
    assert res == "success"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
