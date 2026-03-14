import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.spindle_executor import SpindleExecutor, get_spindle_executor

def test_singleton():
    ex1 = get_spindle_executor()
    ex2 = get_spindle_executor()
    assert ex1 is ex2

# We mock out circuit breaker to allow execution
@patch("backend.cognitive.spindle_executor.enter_loop", return_value=True)
@patch("backend.cognitive.spindle_executor.exit_loop")
def test_execute_invalid_proof(mock_exit, mock_enter):
    executor = SpindleExecutor()
    mock_proof = MagicMock()
    mock_proof.is_valid = False
    mock_proof.constraint_hash = "hash123"
    mock_proof.reason = "invalid"
    
    res = executor.execute(mock_proof)
    assert res.success is False
    assert res.action_taken == "rejected"
    assert "invalid" in res.error

@patch("backend.cognitive.spindle_executor.enter_loop", return_value=True)
@patch("backend.cognitive.spindle_executor.exit_loop")
def test_execute_database_query(mock_exit, mock_enter):
    from backend.cognitive.braille_compiler import BrailleDictionary as BD
    executor = SpindleExecutor()
    mock_proof = MagicMock()
    mock_proof.is_valid = True
    mock_proof.domain_mask = BD.DOMAIN_DATABASE
    mock_proof.intent_mask = BD.INTENT_QUERY
    mock_proof.constraint_hash = "db_hash"
    
    res = executor.execute(mock_proof)
    assert res.success is True
    assert "database_query" in res.action_taken

if __name__ == "__main__":
    pytest.main(['-v', __file__])
