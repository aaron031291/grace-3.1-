import pytest
from unittest.mock import MagicMock, patch
import json
import time

from backend.cognitive.loop_orchestrator import (
    LoopOrchestrator,
    COMPOSITE_LOOPS,
    get_loop_orchestrator
)

def test_singleton_instance():
    lo1 = get_loop_orchestrator()
    lo2 = LoopOrchestrator.get_instance()
    assert lo1 is lo2

def test_get_available_composites():
    lo = get_loop_orchestrator()
    composites = lo.get_available_composites()
    
    assert len(composites) > 0
    assert any(c["id"] == "code_write" for c in composites)
    assert any(c["id"] == "data_ingest" for c in composites)

def test_execute_composite_success():
    import sys
    sys.modules["cognitive.circuit_breaker"] = MagicMock()
    sys.modules["cognitive.circuit_breaker"].enter_loop.return_value = True
    sys.modules["cognitive.circuit_breaker"].exit_loop.return_value = True
    sys.modules["cognitive.event_bus"] = MagicMock()
    sys.modules["api._genesis_tracker"] = MagicMock()
    
    lo = get_loop_orchestrator()
    lo._execute_single_loop = MagicMock(return_value={"executed": True})
    
    res = lo.execute_composite("code_write", {"initial": "value"})
    
    assert res.composite_id == "code_write"
    assert res.loops_executed == len(COMPOSITE_LOOPS["code_write"]["loops"])
    assert res.loops_passed == res.loops_executed
    assert res.verdict == "pass"

def test_execute_composite_partial_failure():
    import sys
    sys.modules["cognitive.circuit_breaker"] = MagicMock()
    sys.modules["cognitive.circuit_breaker"].enter_loop.return_value = True
    sys.modules["cognitive.circuit_breaker"].exit_loop.return_value = True
    sys.modules["cognitive.event_bus"] = MagicMock()
    sys.modules["api._genesis_tracker"] = MagicMock()
    
    lo = get_loop_orchestrator()
    
    # Fail on second loop
    fails = False
    def side_effect(loop_id, ctx):
        nonlocal fails
        if fails:
            raise RuntimeError("Boom")
        fails = True
        return {"ok": True}
        
    lo._execute_single_loop = MagicMock(side_effect=side_effect)
    
    res = lo.execute_composite("data_ingest", {})
    
    assert res.composite_id == "data_ingest"
    assert res.loops_executed == len(COMPOSITE_LOOPS["data_ingest"]["loops"])
    assert res.loops_failed > 0
    assert res.loops_passed > 0
    assert res.verdict == "partial"

def test_execute_composite_circuit_breaker():
    import sys
    sys.modules["cognitive.circuit_breaker"] = MagicMock()
    sys.modules["cognitive.circuit_breaker"].enter_loop.return_value = False
    
    lo = get_loop_orchestrator()
    res = lo.execute_composite("deploy_safe", {})
    
    # All loops hit circuit breaker and return error
    assert res.loops_executed == len(COMPOSITE_LOOPS["deploy_safe"]["loops"])
    assert res.loops_passed == 0
    assert res.loops_failed == res.loops_executed
    assert res.verdict == "fail"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
