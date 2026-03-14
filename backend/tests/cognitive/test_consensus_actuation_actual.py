import pytest
from backend.cognitive.consensus_actuation import ConsensusActuation

def test_consensus_actuation_low_trust():
    actuation = ConsensusActuation(min_trust_required=0.8)
    result = actuation.execute_action({"action_type": "execute_shell_command"}, "Test", 0.5)
    
    assert result["status"] == "blocked"
    assert result["reason"] == "insufficient_trust_score"

def test_consensus_actuation_blocked_command():
    actuation = ConsensusActuation(min_trust_required=0.5)
    
    # Needs to bypass guardian gate
    class MockGuardianGate:
        def authorize(self, *args, **kwargs):
            return {"authorized": True}
    
    import guardian.action_gate as ag
    import sys
    
    class GuardianMockModule:
        def get_action_gate(self):
            return MockGuardianGate()
            
    sys.modules["guardian.action_gate"] = GuardianMockModule()

    payload = {
        "action_type": "execute_shell_command",
        "params": {"command": "rm -rf /test"}
    }
    
    result = actuation.execute_action(payload, "Decision", 0.9)
    assert result["status"] == "blocked"
    assert "blocked keyword" in result["reason"]

def test_consensus_actuation_dry_run_coding(monkeypatch):
    actuation = ConsensusActuation(min_trust_required=0.5)
    
    # Mock guardian gate internally
    monkeypatch.setattr(actuation, "execute_action", lambda p, d, t: actuation._submit_coding_task(p.get("params", {})))
    
    payload = {
        "action_type": "submit_coding_task",
        "params": {
            "instructions": "Fix the bug",
            "dry_run": True
        }
    }
    
    result = actuation.execute_action(payload, "Desc", 0.9)
    assert result["status"] == "success"
    assert result["task_id"] == "dry_run_simulation"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
