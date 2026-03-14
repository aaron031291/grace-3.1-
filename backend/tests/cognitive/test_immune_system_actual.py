import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.immune_system import GraceImmuneSystem, ComponentSnapshot, AnomalyType

def test_immune_system_init():
    with patch("cognitive.event_bus.subscribe"):
        sys = GraceImmuneSystem()
        assert sys._scan_interval == 300
        assert not sys._is_running

def test_detect_anomalies():
    sys = GraceImmuneSystem()
    snapshots = [
        ComponentSnapshot(name="memory", health_score=50, status="stressed", metrics={"percent": 95}),
        ComponentSnapshot(name="api_server", health_score=0, status="down")
    ]
    sys._baselines = {"memory": {"health": 90}, "api_server": {"health": 100}}
    
    anomalies = sys._detect_anomalies(snapshots)
    
    assert len(anomalies) >= 2
    types = [a.anomaly_type for a in anomalies]
    assert AnomalyType.SERVICE_DOWN in types
    assert AnomalyType.MEMORY_LEAK in types

@patch("backend.cognitive.immune_system.GraceImmuneSystem._observe_all_components")
@patch("backend.cognitive.immune_system.GraceImmuneSystem._analyze_genesis_keys")
@patch("backend.cognitive.event_bus.publish_async")
def test_scan(mock_publish, mock_analyze, mock_observe):
    sys = GraceImmuneSystem()
    
    mock_observe.return_value = [
        ComponentSnapshot(name="api_server", health_score=100, status="healthy", metrics={})
    ]
    mock_analyze.return_value = {"available": False}
    
    result = sys.scan()
    assert result["overall_health"]["status"] != "unknown"
    assert len(result["snapshots"]) == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
