import pytest
from unittest.mock import patch, MagicMock
from cognitive.architecture_compass import ArchitectureCompass
from cognitive.architecture_proposer import ArchitectureProposer

@patch('cognitive.architecture_compass.publish')
@patch('pathlib.Path.glob')
@patch('pathlib.Path.exists')
def test_compass_publish(mock_exists, mock_glob, mock_publish):
    mock_exists.return_value = True
    # mock empty list to not parse files
    mock_glob.return_value = []
    
    compass = ArchitectureCompass()
    compass.build()
    
    # Should publish that it finished building
    assert mock_publish.call_count >= 1
    topics = [c.args[0] for c in mock_publish.mock_calls]
    assert "architecture.compass_built" in topics

@patch('cognitive.architecture_proposer.publish')
@patch('cognitive.architecture_proposer.get_llm_client')
@patch('cognitive.architecture_proposer.get_llm_for_task')
def test_proposer_publish(mock_get_llm_task, mock_get_llm_client, mock_publish):
    # Mock LLM prediction to JSON
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"need_score": 9.5, "connections": [], "value_proposition": "test"}'
    mock_get_llm_client.return_value = mock_llm
    mock_get_llm_task.return_value = mock_llm
    
    proposer = ArchitectureProposer()
    spec = {"name": "TestComponent", "description": "foo", "capabilities": ["bar"]}
    
    # Needs to patch get_compass so we don't try to build the real one
    with patch('cognitive.architecture_compass.get_compass') as mock_get_compass:
        mock_compass = MagicMock()
        mock_compass.diagnose.return_value = {"total_components": 1}
        mock_compass.find_for.return_value = []
        mock_get_compass.return_value = mock_compass
        
        proposal = proposer.propose(spec)
        assert proposal["score"] == 9.5
        
        assert mock_publish.call_count >= 1
        topics = [c.args[0] for c in mock_publish.mock_calls]
        assert "architecture.proposal_created" in topics

if __name__ == '__main__':
    pytest.main(['-v', __file__])
