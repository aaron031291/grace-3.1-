import pytest
from backend.cognitive.spindle_projection import SpindleProjection, get_spindle_projection

def test_apply_event_and_component_status():
    proj = SpindleProjection()
    
    event1 = {
        "topic": "spindle.test",
        "payload": {"component": "db", "action": "query"},
        "result": "EXECUTED",
        "proof_hash": "hash1",
        "timestamp": 1000.0,
        "sequence_id": 1,
    }
    proj._apply_event(event1)
    
    c_status = proj.get_component_status("db")
    assert c_status is not None
    assert c_status["last_action"] == "query"
    assert c_status["last_result"] == "EXECUTED"
    assert c_status["total_executions"] == 1
    assert c_status["success_rate"] == 1.0
    
    event2 = {
        "topic": "spindle.test",
        "payload": {"component": "db", "action": "update"},
        "result": "FAILED",
        "proof_hash": "hash2",
        "timestamp": 2000.0,
        "sequence_id": 2,
    }
    proj._apply_event(event2)
    
    c_status = proj.get_component_status("db")
    assert c_status["last_result"] == "FAILED"
    assert c_status["total_executions"] == 2
    assert c_status["success_rate"] == 0.5
    
    assert proj._last_sequence == 2

def test_audit_trail_and_stats():
    proj = SpindleProjection()
    proj._apply_event({"result": "SAT", "payload": {"component": "c1"}})
    proj._apply_event({"result": "UNSAT", "payload": {"component": "c2"}})
    
    stats = proj.get_verification_stats()
    assert stats["SAT"] == 1
    assert stats["UNSAT"] == 1
    assert stats["total"] == 2
    assert stats["sat_ratio"] == 0.5
    
    trail = proj.get_audit_trail()
    assert len(trail) == 2

if __name__ == "__main__":
    pytest.main(['-v', __file__])
