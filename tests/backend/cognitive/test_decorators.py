import pytest
from unittest.mock import patch, MagicMock
from backend.cognitive.decorators import (
    cognitive_operation,
    with_ambiguity_tracking,
    enforce_reversibility,
    blast_radius,
    time_bounded,
    requires_determinism
)

@patch('backend.cognitive.decorators.CognitiveEngine')
def test_cognitive_operation_decorator(mock_engine_cls):
    mock_engine = MagicMock()
    mock_engine_cls.return_value = mock_engine
    
    # Setup mocks for internal OODA flow
    mock_engine.act.return_value = "Result"
    
    @cognitive_operation("test_op", is_reversible=False)
    def my_func(a, b=2):
        return a + b
    
    res = my_func(5, b=10)
    
    assert res == "Result"
    assert mock_engine.begin_decision.called
    assert mock_engine.observe.called
    assert mock_engine.orient.called
    assert mock_engine.decide.called
    assert mock_engine.act.called
    assert mock_engine.finalize_decision.called

@patch('backend.cognitive.engine.CognitiveEngine')
def test_with_ambiguity_tracking(mock_engine_cls):
    mock_engine = MagicMock()
    mock_ctx = MagicMock()
    mock_engine.get_active_decisions.return_value = [mock_ctx]
    mock_engine_cls.return_value = mock_engine
    
    @with_ambiguity_tracking
    def process_data(data=None):
        return True
        
    process_data(data=None)
    
    # It should add unknown for data=None
    mock_ctx.ambiguity_ledger.add_unknown.assert_called_once()
    args, kwargs = mock_ctx.ambiguity_ledger.add_unknown.call_args
    assert args[0] == "data"

def test_enforce_reversibility():
    @enforce_reversibility(reversible=False, justification="Must happen")
    def action1():
        return 1
        
    assert action1() == 1
    assert getattr(action1, "__cognitive_reversible__") is False
    assert getattr(action1, "__cognitive_justification__") == "Must happen"
    
    with pytest.raises(ValueError, match="requires justification"):
        @enforce_reversibility(reversible=False, justification=None)
        def action2():
            pass
        action2()

def test_blast_radius():
    @blast_radius("systemic")
    def systemic_action():
        return "BOOM"
        
    assert systemic_action() == "BOOM"
    assert getattr(systemic_action, "__cognitive_blast_radius__") == "systemic"

def test_requires_determinism():
    @requires_determinism
    def safe_action():
        return True
        
    assert safe_action() is True
    assert getattr(safe_action, "__cognitive_deterministic__") is True

@patch('signal.SIGALRM', 14, create=True)
@patch('signal.signal', create=True)
@patch('signal.alarm', create=True)
def test_time_bounded(mock_alarm, mock_signal):
    # Mocking signal so it runs on Windows
    @time_bounded(timeout_seconds=5)
    def fast_action():
        return "Fast"
        
    assert fast_action() == "Fast"
    mock_alarm.assert_called()
    mock_signal.assert_called()
