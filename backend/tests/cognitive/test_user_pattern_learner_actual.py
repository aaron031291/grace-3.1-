import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.user_pattern_learner import UserPatternLearner, get_user_learner

def test_singleton_or_factory():
    learner1 = get_user_learner("user_1")
    learner2 = get_user_learner("user_1")
    
    assert learner1.user_id == "user_1"
    assert learner2.user_id == "user_1"

@patch("backend.cognitive.user_pattern_learner.session_scope")
def test_observe_interaction(mock_scope):
    # Mock session
    mock_session = MagicMock()
    mock_scope.return_value.__enter__.return_value = mock_session
    
    learner = UserPatternLearner("u1")
    res = learner.observe_interaction(
        message="can you write a function for me?",
        response="```python\ndef a(): pass\n```"
    )
    
    assert res["user_id"] == "u1"
    assert res["interaction_logged"] is True
    # Should have triggered some pattern updates (verbosity, response pref, etc.)
    # At least 1 pattern logic executed, but exact number depends on mocked session
    # We just ensure it executed the db logic
    assert mock_session.add.called

@patch("backend.cognitive.user_pattern_learner.session_scope")
def test_get_adaptation_hints(mock_scope):
    # Setup mock profile
    mock_session = MagicMock()
    mock_scope.return_value.__enter__.return_value = mock_session
    
    # Mock the patterns query to return some dominant patterns
    mock_pattern1 = MagicMock()
    mock_pattern1.pattern_type = "communication_verbosity"
    mock_pattern1.pattern_key = "concise"
    mock_pattern1.confidence = 0.9
    mock_pattern1.observation_count = 5
    mock_pattern1.last_observed = None
    
    mock_session.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = [mock_pattern1]
    
    learner = UserPatternLearner("u1")
    hints = learner.get_adaptation_hints()
    
    assert "length" in hints
    assert "short and direct" in hints["length"]

if __name__ == "__main__":
    pytest.main(['-v', __file__])
