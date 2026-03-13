import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from backend.cognitive.continuous_learning_orchestrator import ContinuousLearningOrchestrator

@pytest.fixture
def mock_orchestrator():
    # Make sure we don't start the real thread
    orchestrator = ContinuousLearningOrchestrator()
    
    # Mocking out the complex component initialization
    orchestrator.sandbox_lab = MagicMock()
    orchestrator.sandbox_lab.get_active_trials.return_value = []
    orchestrator.sandbox_lab.get_awaiting_approval.return_value = []
    orchestrator.sandbox_lab.list_experiments.return_value = []
    
    orchestrator.mirror_system = MagicMock()
    orchestrator.learning_orchestrator = MagicMock()
    
    orchestrator.ingestion_service = MagicMock()
    # Return a mocked doc id on ingest
    orchestrator.ingestion_service.ingest_text_fast.return_value = ("mock_doc_id_123", None)
    
    return orchestrator

def test_initialization():
    orchestrator = ContinuousLearningOrchestrator()
    assert orchestrator.running is False
    assert orchestrator.orchestrator_thread is None

@patch('backend.cognitive.continuous_learning_orchestrator.Path.glob')
@patch('backend.cognitive.continuous_learning_orchestrator.Path.exists')
@patch('backend.cognitive.continuous_learning_orchestrator.Path.is_file')
@patch('backend.cognitive.continuous_learning_orchestrator.Path.read_text')
def test_orchestration_loop_ingestion(mock_read, mock_is_file, mock_exists, mock_glob, mock_orchestrator):
    # Setup mock file system behavior to simulate finding a file to ingest
    mock_exists.return_value = True
    mock_is_file.return_value = True
    mock_glob.return_value = [MagicMock(suffix='.txt', name="test_doc.txt")]
    mock_read.return_value = "This is a test document."
    
    # Run the ingestion check manually instead of waiting for the thread sleep
    mock_orchestrator._run_ingestion_check()
    
    # Assert ingestion was called and queue was updated
    assert mock_orchestrator.stats["total_ingestions"] == 1
    assert len(mock_orchestrator.learning_queue) == 1
    assert mock_orchestrator.learning_queue[0]["document_id"] == "mock_doc_id_123"

def test_orchestration_loop_learning(mock_orchestrator):
    # Seed the learning queue
    mock_orchestrator.learning_queue = [
        {"document_id": "doc_1"},
        {"document_id": "doc_2"}
    ]
    
    mock_orchestrator._run_learning_cycle()
    
    # The loop should pop items off the learning queue 
    assert len(mock_orchestrator.learning_queue) == 0
    assert mock_orchestrator.stats["total_learning_cycles"] == 1
    assert mock_orchestrator.stats["knowledge_items_learned"] == 2

def test_orchestration_loop_mirror_observation(mock_orchestrator):
    # Mock the mirror system finding an opportunity
    mock_orchestrator.mirror_system.analyze_recent_operations.return_value = {
        "improvement_opportunities": [
            {
                "category": "performance", 
                "name": "Test Opt", 
                "description": "desc",
                "motivation": "Make it faster",
                "confidence": 0.95
            }
        ]
    }
    
    # Mock the sandbox proposal return object
    mock_exp = MagicMock()
    mock_exp.experiment_id = "exp_001"
    mock_orchestrator.sandbox_lab.propose_experiment.return_value = mock_exp
    
    mock_orchestrator._run_mirror_observation()
    
    # Assert mirror analyzed operations and proposed experiment
    mock_orchestrator.mirror_system.analyze_recent_operations.assert_called_once()
    mock_orchestrator.sandbox_lab.propose_experiment.assert_called_once()
    
    # Verify the stat counters
    assert mock_orchestrator.stats["total_mirror_observations"] == 1
    assert mock_orchestrator.stats["total_experiments_proposed"] == 1
    assert len(mock_orchestrator.experiment_ideas) == 1
    assert mock_orchestrator.experiment_ideas[0]["experiment_id"] == "exp_001"
