import pytest
import time
from backend.cognitive.central_orchestrator import CentralOrchestrator, SystemState
from backend.cognitive.circuit_breaker import enter_loop, exit_loop, protected_call, get_loop_status, _call_depths

def test_central_orchestrator_state():
    """Test global state updates without mocking."""
    orc = CentralOrchestrator()
    orc.state.update("test_module", {"status": "running"})
    
    data = orc.state.get("test_module")
    assert data["status"] == "running"
    assert "last_updated" in data
    
    # Task routing
    res = orc.route_task("code_generation", {"prompt": "hello"})
    assert res["routed_to"] == "pipeline"
    assert len(orc.state.get_active_tasks()) == 1
    
def test_circuit_breaker_logic():
    """Test circuit breaker recursion depth prevention natively."""
    # Ensure starting cleanly
    _call_depths["test_loop"] = 0
    
    def recursive_call(depth):
        if not enter_loop("test_loop"):
            return False
        try:
            if depth > 0:
                return recursive_call(depth - 1)
            return True
        finally:
            exit_loop("test_loop")
            
    # test_loop is not in NAMED_LOOPS so max_depth defaults to 5
    # Requesting depth 10 -> will fail
    assert recursive_call(10) is False
    
    # Ensure depth counter decremental correctly after failure
    assert _call_depths["test_loop"] == 0
    
    # Requesting depth 3 -> will succeed
    assert recursive_call(3) is True
    assert _call_depths["test_loop"] == 0

if __name__ == "__main__":
    pytest.main(['-v', __file__])
