import pytest
from pydantic import ValidationError
from backend.core.clarity_framework import ClarityFramework, ClarityDecision

def test_clarity_framework_valid_record():
    decision = ClarityFramework.record_decision(
        what="Self Healing Triggered",
        why="High latency on API",
        who={"actor": "proactive_engine"},
        where={"component": "system_health_api"},
        how={"playbook": "restart_service"},
        risk_score=0.4,
        related_ids=["alert_123"]
    )
    
    assert isinstance(decision, ClarityDecision)
    assert decision.what == "Self Healing Triggered"
    assert decision.risk_score == 0.4
    assert decision.id.startswith("decision_")
    
    # Check singleton buffer
    recent = ClarityFramework.get_recent_decisions()
    assert len(recent) > 0
    assert recent[0]["id"] == decision.id
    assert isinstance(recent[0]["when"], str) # ISO string format for UI validation

def test_clarity_framework_invalid_record():
    with pytest.raises(ValidationError):
        # Missing fields or invalid types
        ClarityFramework.record_decision(
            what="Invalid decision",
            why=None, # Invalid type, must be str
            who={"actor": "test"},
            where={},
            how=None, # Invalid type, must be dict
            risk_score=1.5, # Validation should fail here too: risk_score must be <= 1.0
        )

def test_clarity_framework_buffer_limit():
    # Clear buffer for isolated test
    ClarityFramework._recent_decisions.clear()
    
    for i in range(55):
        ClarityFramework.record_decision(
            what=f"Decision {i}",
            why="Testing buffer limit",
            who={"actor": "test"},
            where={},
            how={},
            risk_score=0.1
        )
        
    recent = ClarityFramework.get_recent_decisions()
    assert len(recent) == 50  # Caps at _MAX_DECISIONS
    # The first element in the list is the most recently added via insert(0, ...)
    assert recent[0]["what"] == "Decision 54"
