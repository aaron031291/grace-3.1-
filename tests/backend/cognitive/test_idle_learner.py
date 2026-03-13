import pytest
import time
from unittest.mock import MagicMock, patch

from backend.cognitive.idle_learner import IdleLearner, CODING_CURRICULUM

@pytest.fixture
def mock_modules():
    mocks = {
        'cognitive.time_sense': MagicMock(),
        'llm_orchestrator.kimi_enhanced': MagicMock(),
        'cognitive.magma_bridge': MagicMock(),
        'api._genesis_tracker': MagicMock(),
        'cognitive.librarian_autonomous': MagicMock(),
        'database.session': MagicMock()
    }
    with patch.dict('sys.modules', mocks):
        yield mocks

@pytest.fixture
def learner(mock_modules):
    return IdleLearner()

def test_is_idle(learner):
    learner.mark_activity()
    
    # Just marked, not idle (default 300s)
    assert learner.is_idle() is False
    
    # 5 seconds threshold
    assert learner.is_idle(5) is False
    
    # Hack the timer
    learner._last_activity = time.time() - 400
    assert learner.is_idle() is True

def test_should_learn(learner, mock_modules):
    learner._last_activity = time.time() - 400
    
    # TimeSense mock
    time_sense = MagicMock()
    time_sense.now_context.return_value = {"is_business_hours": False}
    mock_modules['cognitive.time_sense'].TimeSense = time_sense
    
    assert learner.should_learn() is True
    
    # Business hours and only idle for 400s (needs 600s)
    time_sense.now_context.return_value = {"is_business_hours": True}
    assert learner.should_learn() is False
    
    # Business hours but idle for 700s
    learner._last_activity = time.time() - 700
    assert learner.should_learn() is True
    
    # Prevent overlapping learning
    learner._is_learning = True
    assert learner.should_learn() is False

def test_learn_next_curriculum(learner, mock_modules):
    learner._last_activity = time.time() - 700
    
    kimi_mock = MagicMock()
    kimi_mock.teach_topic.return_value = {"knowledge": "def handler(): pass"}
    mock_modules['llm_orchestrator.kimi_enhanced'].get_kimi_enhanced.return_value = kimi_mock
    
    # We should learn topic 0
    topic_0 = CODING_CURRICULUM[0]["topic"]
    
    res = learner.learn_next()
    
    assert res is not None
    assert res["success"] is True
    assert res["topic"] == topic_0
    
    # Status should reflect 1 topic taught, index 1
    status = learner.get_status()
    assert status["topics_taught"] == 1
    assert "1/" in status["curriculum_progress"]

def test_identify_gaps(learner, mock_modules):
    db_mock = MagicMock()
    
    # Define fetchall response
    # SQL query returns tuples of (input_context,)
    db_mock.execute.return_value.fetchall.return_value = [
        ("Gap concerning auth",),
        ("Gap concerning routing",)
    ]
    
    with patch('backend.cognitive.idle_learner._get_db', return_value=db_mock):
        gaps = learner._identify_gaps()
        
    assert len(gaps) == 2
    assert gaps[0] == "Gap concerning auth"

def test_learn_from_gap(learner, mock_modules):
    learner._last_activity = time.time() - 700
    
    # Fast forward to the end of the curriculum
    learner._current_index = len(CODING_CURRICULUM)
    
    kimi_mock = MagicMock()
    kimi_mock.teach_topic.return_value = {"knowledge": "Fixing the gap"}
    mock_modules['llm_orchestrator.kimi_enhanced'].get_kimi_enhanced.return_value = kimi_mock
    
    # Mock identify_gaps to return a gap
    with patch.object(learner, '_identify_gaps', return_value=["Fix auth"]):
        res = learner.learn_next()  # Should hit index bound, call gap
        
    assert res is not None
    assert "How to handle: Fix auth" in res["topic"]
    assert res["category"] == "gap_fill"
