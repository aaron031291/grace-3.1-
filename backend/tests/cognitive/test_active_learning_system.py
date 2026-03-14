import pytest
from unittest.mock import patch, MagicMock
from backend.cognitive.active_learning_system import GraceActiveLearningSystem

@pytest.fixture
def mock_learning_system():
    session_mock = MagicMock()
    retriever_mock = MagicMock()
    knowledge_base_path = MagicMock()
    
    with patch('backend.cognitive.active_learning_system.PredictiveContextLoader'):
        system = GraceActiveLearningSystem(session_mock, retriever_mock, knowledge_base_path)
        return system

@patch('backend.cognitive.active_learning_system.publish')
def test_active_learning_study_topic(mock_publish, mock_learning_system):
    mock_learning_system.predictive_loader.process_query.return_value = {
        'ready_topics': ['related_topic'],
        'statistics': {'cache_hit': False}
    }
    mock_learning_system._find_relevant_training_materials = MagicMock(return_value=[])
    mock_learning_system._extract_key_concepts = MagicMock(return_value=[])
    mock_learning_system._prioritize_learning_focus = MagicMock(return_value=['concept A'])
    mock_learning_system._store_learning_examples = MagicMock(return_value=[])

    result = mock_learning_system.study_topic("Python", ["Learn syntax"])
    
    # Check if events fired
    assert mock_publish.call_count == 2
    topics = [call.args[0] for call in mock_publish.mock_calls]
    assert "learning.study_started" in topics
    assert "learning.study_completed" in topics
    assert result["topic"] == "Python"
    assert result["focus_areas"] == ["concept A"]

if __name__ == '__main__':
    pytest.main(['-v', __file__])
