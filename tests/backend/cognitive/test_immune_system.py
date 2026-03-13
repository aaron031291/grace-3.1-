import pytest
import time
from unittest.mock import patch, MagicMock
from backend.cognitive.immune_system import GraceImmuneSystem, Anomaly, AnomalyType, ComponentSnapshot

# Pre-emptively mock the genesis tracker so that importing it doesn't trigger a SQLAlchemy load cascade
import sys
sys.modules['backend.api'] = MagicMock()
sys.modules['backend.api._genesis_tracker'] = MagicMock()
sys.modules['api._genesis_tracker'] = MagicMock()

@pytest.fixture
def immune_system():
    # Instantiate directly to avoid singleton state issues across tests
    with patch('cognitive.event_bus.subscribe'), \
         patch('genesis.realtime.get_realtime_engine'):
        return GraceImmuneSystem()

@patch('backend.cognitive.immune_system.GraceImmuneSystem.scan')
def test_daemon_loop(mock_scan, immune_system):
    # Verify the daemon loop can start and stop
    assert not immune_system._is_running
    immune_system.start_background_loop()
    assert immune_system._is_running
    assert immune_system._background_thread is not None
    assert immune_system._background_thread.is_alive()
    
    immune_system.stop_background_loop()
    assert not immune_system._is_running
    # Give the thread a moment to join
    time.sleep(0.1)
    assert not immune_system._background_thread.is_alive()

@patch('backend.cognitive.immune_system.GraceImmuneSystem._execute_healing')
@patch('backend.cognitive.immune_system.GraceImmuneSystem._get_component_trust')
def test_doubt_mechanism(mock_trust, mock_execute, immune_system):
    # Mock high disruption, low severity to trigger doubt mechanism
    anomaly = Anomaly(
        anomaly_type=AnomalyType.PERFORMANCE_DEGRADATION,
        severity=0.4,
        component="api_server",
        description="Slow response",
        healing_actions=["restart"]
    )
    
    # We don't want trust to be the bottleneck here
    mock_trust.return_value = 100
    
    with patch('backend.cognitive.immune_system.GraceImmuneSystem._calculate_healing_cost') as mock_cost:
        # Cost disruption > severity
        mock_cost.return_value = {"disruption": 0.8, "recovery_seconds": 8}
        
        result = immune_system._diagnose_and_heal(anomaly, time_ctx={"is_business_hours": True})
        
        assert result["action"] == "deferred"
        assert "Healing cost" in result["reason"]
        mock_execute.assert_not_called()

@patch('time.sleep')
@patch('cognitive.trust_engine.get_trust_engine')
@patch('cognitive.pipeline.FeedbackLoop.record_outcome')
@patch('cognitive.magma_bridge.store_pattern')
@patch('cognitive.magma_bridge.store_decision')
@patch('cognitive.magma_bridge.ingest')
@patch('backend.api._genesis_tracker.track')
@patch('cognitive.self_healing.get_healer')
@patch('cognitive.consensus_engine.queue_autonomous_query')
@patch('backend.cognitive.immune_system.GraceImmuneSystem._get_component_trust')
def test_rollback_mechanism(mock_trust, mock_queue_query, mock_get_healer, mock_track, mock_ingest, mock_store_dec, mock_store_pat, mock_feedback, mock_trust_engine, mock_sleep, immune_system):
    # Setup anomaly
    anomaly = Anomaly(
        anomaly_type=AnomalyType.MEMORY_LEAK,
        severity=0.8,
        component="memory",
        description="High memory usage",
        healing_actions=["gc_collect"]
    )
    
    mock_trust.return_value = 80
    
    mock_healer = MagicMock()
    mock_get_healer.return_value = mock_healer
    
    # Mock _check_component to return identical health before and after (no improvement)
    # This simulates a failed heal requiring a rollback
    pre_snap = ComponentSnapshot(name="memory", health_score=50, status="degraded")
    post_snap = ComponentSnapshot(name="memory", health_score=50, status="degraded")
    
    with patch('backend.cognitive.immune_system.GraceImmuneSystem._check_component', side_effect=[pre_snap, post_snap]):
        result = immune_system._execute_healing(anomaly, "gc_collect", time_ctx={})
        
        # Should be marked as failed since health didn't improve
        assert result["success"] is False
        assert result["health_before"] == 50
        assert result["health_after"] == 50
        
        # Should have escalated to consensus since severity >= 0.6 and it failed
        mock_queue_query.assert_called_once()
        
        # Verify it was added to the playbook as a failure
        assert len(immune_system._healing_playbook) == 1
        assert immune_system._healing_playbook[0].success is False

@patch('backend.cognitive.immune_system.time.sleep')
@patch('cognitive.trust_engine.get_trust_engine')
@patch('cognitive.pipeline.FeedbackLoop.record_outcome')
@patch('cognitive.magma_bridge.store_pattern')
@patch('cognitive.magma_bridge.store_decision')
@patch('cognitive.magma_bridge.ingest')
@patch('backend.api._genesis_tracker.track')
@patch('backend.cognitive.immune_system.GraceImmuneSystem._get_component_trust')
@patch('backend.cognitive.immune_system.GraceImmuneSystem._check_component')
@patch('cognitive.self_healing.get_healer')
def test_successful_healing_creates_vaccination_flag(mock_get_healer, mock_check, mock_trust, mock_track, mock_ingest, mock_store_dec, mock_store_pat, mock_feedback, mock_trust_engine, mock_sleep, immune_system):
    mock_trust.return_value = 80
    anomaly = Anomaly(
        anomaly_type=AnomalyType.SERVICE_DOWN,
        severity=0.9,
        component="qdrant",
        description="Qdrant offline",
        healing_actions=["reconnect"]
    )
    
    # Needs to report improvement
    pre_snap = ComponentSnapshot(name="qdrant", health_score=0, status="down")
    post_snap = ComponentSnapshot(name="qdrant", health_score=95, status="healthy")
    
    # Call it 3 times to trigger the vaccination flag
    for i in range(3):
        mock_check.side_effect = [pre_snap, post_snap]
        result = immune_system._execute_healing(anomaly, "reconnect", time_ctx={})
        
        assert result["success"] is True
        
        if i < 2:
            assert not result["vaccination_needed"]
        else:
            assert result["vaccination_needed"] is True
            assert "needs root cause fix" in result["vaccination"]
