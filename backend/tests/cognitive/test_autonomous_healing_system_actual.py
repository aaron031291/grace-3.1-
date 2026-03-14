import pytest
from backend.cognitive.autonomous_healing_system import AutonomousHealingSystem, HealthStatus, AnomalyType, TrustLevel, HealingAction

class DummySession:
    pass

def test_autonomous_healing_system_initialization():
    ahs = AutonomousHealingSystem(session=DummySession(), trust_level=TrustLevel.MEDIUM_RISK_AUTO, simulation_mode=True)
    assert ahs.current_health == HealthStatus.HEALTHY
    assert len(ahs.anomalies_detected) == 0
    assert ahs.trust_scores[HealingAction.BUFFER_CLEAR] == 0.9

if __name__ == "__main__":
    pytest.main(['-v', __file__])
