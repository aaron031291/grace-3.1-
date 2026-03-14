import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
from models.genesis_key_models import GenesisKey, GenesisKeyType
from backend.cognitive.autonomous_healing_system import AutonomousHealingSystem, TrustLevel, HealthStatus, AnomalyType

@pytest.fixture
def mock_db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_autonomous_healing_actual_logic(mock_db_session):
    """
    Test the actual logical workflow of the Autonomous Healing System.
    Validates health assessment, anomaly detection, and decision making 
    without mocking the core implementation.
    """
    system = AutonomousHealingSystem(
        session=mock_db_session,
        repo_path=Path("."),
        trust_level=TrustLevel.FULL_AUTONOMY,
        enable_learning=False,
        simulation_mode=True
    )
    
    # 1. Inject some fake errors into the DB to trigger the ERROR_SPIKE anomaly
    now = datetime.now(timezone.utc)
    for i in range(15):
        gk = GenesisKey(
            key_id=f"test-error-{i}",
            key_type=GenesisKeyType.ERROR,
            created_at=now - timedelta(minutes=i),
            what_description="Simulated timeout exception",
            context_data={"file_path": "backend/api/router.py"}
        )
        mock_db_session.add(gk)
    mock_db_session.commit()
    
    # 2. Assess System Health
    # Should detect the 15 errors as an ERROR_SPIKE and the identical file paths as PERFORMANCE_DEGRADATION
    assessment = system.assess_system_health()
    
    assert assessment["recent_errors"] == 15
    assert len(assessment["anomalies_detected"]) > 0
    
    anomaly_types = [a["type"] for a in assessment["anomalies"]]
    assert AnomalyType.ERROR_SPIKE in anomaly_types
    assert AnomalyType.PERFORMANCE_DEGRADATION in anomaly_types
    
    # 3. Decide Healing Actions
    decisions = system.decide_healing_actions(assessment["anomalies"])
    
    assert len(decisions) == len(assessment["anomalies"])
    for decision in decisions:
        assert decision["execution_mode"] == "autonomous" # Because we set FULL_AUTONOMY
        assert "healing_action" in decision
    
    # 4. Run full monitoring cycle
    cycle_result = system.run_monitoring_cycle()
    
    assert "health_status" in cycle_result
    assert cycle_result["health_status"] in [HealthStatus.WARNING.value, HealthStatus.CRITICAL.value, HealthStatus.DEGRADED.value]

if __name__ == "__main__":
    pytest.main(['-v', __file__])
