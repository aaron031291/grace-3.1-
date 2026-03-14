import pytest
from unittest.mock import MagicMock
from backend.cognitive.episodic_memory import EpisodicBuffer, Episode

def test_record_episode():
    # Use a mock session
    session = MagicMock()
    buffer = EpisodicBuffer(session=session)
    
    ep = buffer.record_episode(
        problem="Test problem",
        action={"a": 1},
        outcome={"b": 2},
        predicted_outcome={"b": 3},
    )
    
    assert session.add.called
    assert session.commit.called
    assert ep.problem == "Test problem"
    # Action and outcome are JSON strings
    assert '"a": 1' in ep.action or "'a': 1" in ep.action or '{"a": "1"}' in ep.action or '{"a": 1}' in ep.action
    assert ep.prediction_error > 0.0

def test_calculate_prediction_error():
    buffer = EpisodicBuffer(session=MagicMock())
    
    err = buffer._calculate_prediction_error({"a": 1}, {"a": 1})
    assert err == 0.0
    
    err2 = buffer._calculate_prediction_error({"a": 1}, {"a": 2})
    assert err2 == 1.0

if __name__ == "__main__":
    pytest.main(['-v', __file__])
