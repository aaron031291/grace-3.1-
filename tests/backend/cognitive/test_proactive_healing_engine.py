import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from backend.cognitive.proactive_healing_engine import ProactiveHealingEngine, SeverityLevel, HealingOutcome, ProactiveCategory

@pytest.fixture
def test_engine():
    engine = ProactiveHealingEngine(check_interval_seconds=1, trend_window_size=5, enable_kimi_diagnosis=False)
    # Don't start the background thread, we'll test the inner logic directly
    return engine

@patch('backend.cognitive.proactive_healing_engine.ProactiveHealingEngine._verify_with_stress_test')
@patch('backend.cognitive.proactive_healing_engine.ProactiveHealingEngine._take_snapshot')
@patch('backend.cognitive.proactive_healing_engine.ProactiveHealingEngine._vaccinate')
@patch('backend.cognitive.proactive_healing_engine.ProactiveHealingEngine._record_healing_outcome')
@patch('backend.cognitive.proactive_healing_engine.ProactiveHealingEngine._send_notification')
@patch('backend.cognitive.proactive_healing_engine.ProactiveHealingEngine._broadcast_healing_event')
@patch('backend.cognitive.proactive_healing_engine.ProactiveHealingEngine._log_to_telemetry')
def test_healing_orchestration_cycle(
    mock_telemetry, mock_broadcast, mock_notify, mock_record, mock_vaccinate, mock_snapshot, mock_stress, test_engine
):
    """Verify the engine orchestrates the full healing cycle safely."""
    # Setup happy path
    mock_stress.return_value = True  # Stress test passes
    
    issue = {
        "category": ProactiveCategory.CONNECTION_HEALTH,
        "service": "database",
        "severity": SeverityLevel.CRITICAL,
        "message": "Simulated database connection failure",
        "healable": True,
        "heal_action": "database_reconnect",
    }
    
    with patch.object(test_engine, '_execute_heal') as mock_execute:
        mock_execute.return_value = {"success": True, "message": "Simulated heal successful"}
        
        result = test_engine._handle_issue(issue, time_ctx={"is_business_hours": False})
        
        assert result["outcome"] == HealingOutcome.HEALED
        mock_snapshot.assert_called_once_with("database_reconnect")
        mock_execute.assert_called_once()
        mock_stress.assert_called_once_with("database_reconnect")
        mock_record.assert_called_once()
        mock_vaccinate.assert_called_once()
        mock_notify.assert_called_once()
        mock_broadcast.assert_called_once()
        mock_telemetry.assert_called_once()

@patch('backend.cognitive.proactive_healing_engine.ProactiveHealingEngine._broadcast_healing_event')
@patch('backend.cognitive.proactive_healing_engine.ProactiveHealingEngine._log_to_telemetry')
def test_circuit_breaker_prevents_loops(mock_telemetry, mock_broadcast, test_engine):
    """Verify that if a circuit breaker is tripped, healing is deferred to prevent infinite loops."""
    issue = {
        "category": ProactiveCategory.CONNECTION_HEALTH,
        "service": "database",
        "severity": SeverityLevel.WARNING,
        "message": "Looping failure",
        "healable": True,
        "heal_action": "database_reconnect",
    }
    
    with patch('backend.cognitive.proactive_healing_engine.ProactiveHealingEngine._enter_circuit_breaker') as mock_cb:
        mock_cb.return_value = False  # Circuit breaker tripped
        
        with patch.object(test_engine, '_execute_heal') as mock_execute:
            result = test_engine._handle_issue(issue, time_ctx={})
            
            assert result["outcome"] == HealingOutcome.DEFERRED
            assert "Circuit breaker tripped" in result.get("reason", "")
            mock_execute.assert_not_called()
            mock_broadcast.assert_not_called()

@patch('backend.cognitive.proactive_healing_engine.ProactiveHealingEngine._broadcast_healing_event')
def test_delegates_to_immune_system(mock_broadcast, test_engine):
    """Assert it correctly delegates repairs to the Immune System."""
    with patch('backend.cognitive.immune_system.GraceImmuneSystem') as MockImmuneClass:
        mock_immune_instance = MockImmuneClass.return_value
        mock_immune_instance.scan.return_value = {"healing_actions": ["A", "B"]}
        
        # Inject the mock into the engine (bypassing lazy load if needed)
        test_engine._immune = mock_immune_instance
        
        # We test the direct heal execution method handling delegation
        result = test_engine._execute_heal("immune_adaptive_scan", {})
        
        assert result["success"] is True
        assert "2 actions" in result["message"]
        mock_immune_instance.scan.assert_called_once()

@patch('backend.cognitive.proactive_healing_engine.ProactiveHealingEngine._broadcast_healing_event')
def test_delegates_to_diagnostic_machine(mock_broadcast, test_engine):
    """Assert it correctly delegates deep repairs to the Diagnostic Machine."""
    with patch('diagnostic_machine.diagnostic_engine.DiagnosticEngine') as MockDiagClass:
        mock_diag_instance = MockDiagClass.return_value
        mock_diag_instance.run_diagnostic_cycle.return_value = {"diagnosis": "complete"}
        
        result = test_engine._execute_heal("forensic_root_cause", {})
        
        assert result["success"] is True
        assert "Forensic analysis complete" in result["message"]
        mock_diag_instance.run_diagnostic_cycle.assert_called_once()
