import pytest
import time
from backend.cognitive.idle_learner import IdleLearner, get_idle_learner

def test_singleton():
    i1 = get_idle_learner()
    i2 = get_idle_learner()
    assert i1 is i2

def test_is_idle():
    learner = IdleLearner()
    learner.mark_activity()
    assert learner.is_idle(idle_threshold_seconds=10) is False
    
    # fake last activity
    learner._last_activity = time.time() - 20
    assert learner.is_idle(idle_threshold_seconds=10) is True

def test_should_learn():
    learner = IdleLearner()
    learner.mark_activity()
    
    # Not idle
    assert learner.should_learn() is False
    
    # Idle
    learner._last_activity = time.time() - 600
    assert learner.should_learn() is True

if __name__ == "__main__":
    pytest.main(['-v', __file__])
