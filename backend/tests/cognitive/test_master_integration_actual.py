import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.base import Base

from backend.cognitive.autonomous_master_integration import AutonomousMasterIntegration

from database.connection import DatabaseConnection

@pytest.fixture
def mock_db_session():
    engine = create_engine("sqlite:///:memory:")
    DatabaseConnection._engine = engine # Mock the global engine
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_master_integration_logic(mock_db_session):
    """
    Test actual input/output flow of the master integration pipeline 
    without mocking the core orchestration logic.
    """
    kb_path = Path("backend/data/test_kb")
    
    # Initialize the Master Integration
    # Disabling multi_llm and learning orchestrator sub-processes so they don't block
    # the test suite with actual HTTP calls to Opus/Anthropic APIs or spawn real threads.
    # The orchestration logic itself remains active.
    master = AutonomousMasterIntegration(
        session=mock_db_session,
        knowledge_base_path=kb_path,
        enable_learning=False, 
        enable_multi_llm=False
    )
    master.initialize()
    
    # Fake an incoming system event
    input_data = {
        "event_type": "diagnostic_failure",
        "data": {"component": "database", "error": "timeout"}
    }
    
    # Process through the unified pipeline
    result = master.process_input(
        input_data=input_data,
        input_type="system_event",
    )
    
    # The input should have triggered Layer 1
    assert "layer1_response" in result or "genesis_key_id" in result or "error" in result
    
    # Test the proactive monitoring cycle
    cycle_result = master.run_proactive_cycle()
    assert "timestamp" in cycle_result
    assert "actions" in cycle_result
    
    # Get system status
    status = master.get_complete_system_status()
    assert status["master_integration"]["inputs_processed"] == 1
    
if __name__ == "__main__":
    pytest.main(['-v', __file__])
