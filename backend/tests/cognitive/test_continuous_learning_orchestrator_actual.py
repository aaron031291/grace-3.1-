import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from backend.cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

def test_init():
    orchestrator = ContinuousLearningOrchestrator()
    assert orchestrator.running is False
    assert orchestrator.stats["total_ingestions"] == 0

def test_should_run_ingestion():
    orchestrator = ContinuousLearningOrchestrator()
    orchestrator.config["ingestion_interval_seconds"] = 60
    
    # Never run before
    assert orchestrator._should_run_ingestion() is True
    
    # Just ran
    orchestrator.last_ingestion_check = datetime.now()
    assert orchestrator._should_run_ingestion() is False
    
    # Ran long time ago
    orchestrator.last_ingestion_check = datetime.now() - timedelta(seconds=100)
    assert orchestrator._should_run_ingestion() is True

def test_should_run_learning():
    orchestrator = ContinuousLearningOrchestrator()
    orchestrator.config["learning_cycle_interval_seconds"] = 300
    
    assert orchestrator._should_run_learning() is True
    orchestrator.last_learning_cycle = datetime.now()
    assert orchestrator._should_run_learning() is False

@patch("backend.cognitive.continuous_learning_orchestrator.ContinuousLearningOrchestrator.initialize_components")
@patch("threading.Thread")
def test_start_stop(mock_thread, mock_init):
    orchestrator = ContinuousLearningOrchestrator()
    mock_thread_instance = MagicMock()
    mock_thread.return_value = mock_thread_instance
    
    orchestrator.start()
    assert orchestrator.running is True
    mock_init.assert_called_once()
    mock_thread_instance.start.assert_called_once()
    
    orchestrator.stop()
    assert orchestrator.running is False
    mock_thread_instance.join.assert_called_once()

if __name__ == "__main__":
    pytest.main(['-v', __file__])
