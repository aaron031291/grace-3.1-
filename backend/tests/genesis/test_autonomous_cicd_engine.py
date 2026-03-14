import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from backend.genesis.autonomous_cicd_engine import (
    AutonomousCICDEngine,
    AutonomyLevel,
    AutonomousTriggerType,
    ActionRisk,
    AutonomousEvent,
    get_autonomous_cicd_engine
)

@pytest.fixture
def engine():
    return AutonomousCICDEngine(autonomy_level=AutonomyLevel.MEDIUM_AUTONOMY)

@pytest.mark.asyncio
async def test_on_file_change(engine):
    with patch.object(engine, '_execute_decision', new_callable=AsyncMock) as mock_execute:
        # Test low risk automatic decision
        decision = await engine.on_file_change("src/main.py", "modified")
        assert decision is not None
        assert decision.action == "run_tests"
        assert decision.risk_level == ActionRisk.LOW
        assert decision.approved is True
        
        # execution_mode should be "auto" because LOW risk maps to LOW_AUTONOMY
        # and current runs at MEDIUM_AUTONOMY
        assert decision.execution_mode == "auto"
        mock_execute.assert_called_once()

@pytest.mark.asyncio
async def test_high_risk_requires_higher_autonomy(engine):
    with patch.object(engine, '_execute_decision', new_callable=AsyncMock) as mock_execute:
        event = AutonomousEvent(
            id="test-event-1",
            event_type=AutonomousTriggerType.FILE_CHANGE,
            timestamp="2023-01-01",
            source="test",
            payload={}
        )
        
        # Create an event that leads to HIGH risk
        with patch.object(engine, '_analyze_event', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = ("deploy_production", ActionRisk.HIGH, 0.9, "test")
            decision = await engine.process_event(event)
            
            # Since engine is MEDIUM_AUTONOMY, HIGH risk should not be approved for auto execution
            assert decision.approved is False
            assert decision.execution_mode == "manual"
            mock_execute.assert_not_called()

@pytest.mark.asyncio
async def test_record_outcome(engine):
    event = AutonomousEvent(
        id="test-event-2",
        event_type=AutonomousTriggerType.SCHEDULED,
        timestamp="2023-01-01",
        source="test",
        payload={}
    )
    with patch.object(engine, '_execute_decision', new_callable=AsyncMock):
        decision = await engine.process_event(event)
        
        initial_trust = engine.action_trust.get(decision.action)
        
        # Test success increases trust
        engine.record_outcome(decision.decision_id, success=True)
        assert engine.action_trust.get(decision.action) > initial_trust

@pytest.mark.asyncio
async def test_manual_approval(engine):
    event = AutonomousEvent(
        id="test-event-3",
        event_type=AutonomousTriggerType.FILE_CHANGE,
        timestamp="2023-01-01",
        source="test",
        payload={}
    )
    with patch.object(engine, '_execute_decision', new_callable=AsyncMock) as mock_execute:
        with patch.object(engine, '_analyze_event', new_callable=AsyncMock) as mock_analyze:
            # Force high risk to make it manual
            mock_analyze.return_value = ("deploy_production", ActionRisk.HIGH, 0.9, "test")
            decision = await engine.process_event(event)
            
            assert decision.approved is False
            
            # Manually approve
            approved_decision = await engine.approve_decision(decision.decision_id)
            assert approved_decision.approved is True
            assert approved_decision.execution_mode == "manual_approved"
            mock_execute.assert_called_once()

if __name__ == "__main__":
    pytest.main(['-v', __file__])
