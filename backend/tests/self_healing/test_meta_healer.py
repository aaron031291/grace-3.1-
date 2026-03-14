import pytest
import sys
import threading
from unittest.mock import patch, MagicMock
from backend.self_healing.meta_healer import execute_meta_heal, meta_heal, _is_healing

def test_execute_meta_heal_invalid_input():
    assert execute_meta_heal((None, None, None)) is False

def test_execute_meta_heal_no_target_file():
    # Construct a traceback with no "backend" file
    try:
        raise ValueError("test")
    except ValueError:
        exc_info = sys.exc_info()
        
    with patch("traceback.format_exception", return_value=["line 1", "line 2"]):
        assert execute_meta_heal(exc_info) is False

@patch("backend.self_healing.meta_healer.traceback.format_exception")
def test_execute_meta_heal_file_identified(mock_format_exc):
    # Mock traceback that has a backend file
    mock_format_exc.return_value = [
        "Traceback (most recent call last):\n",
        '  File "/path/to/backend/cognitive/test.py", line 10, in <module>\n',
        "ValueError: test error\n"
    ]
    
    try:
        raise ValueError("test")
    except ValueError:
        exc_info = sys.exc_info()
        
    # Simulate a failure in generating code to check the "could not generate" path
    with patch("backend.cognitive.qwen_coding_net.generate_code", side_effect=ImportError("No qwen")):
        assert execute_meta_heal(exc_info) is False

def test_meta_heal_decorator_success_path():
    @meta_heal
    def target_function():
        return "success"
        
    assert target_function() == "success"

@patch("backend.self_healing.meta_healer.execute_meta_heal")
def test_meta_heal_decorator_heals(mock_execute):
    mock_execute.return_value = True
    
    call_count = 0
    
    @meta_heal
    def target_function():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("First time failure")
        return "success"
        
    # Should raise error, execute_meta_heal returns True, then it retries and succeeds!
    assert target_function() == "success"
    assert call_count == 2
    assert mock_execute.call_count == 1

@patch("backend.self_healing.meta_healer.execute_meta_heal")
def test_meta_heal_decorator_fails_to_heal(mock_execute):
    mock_execute.return_value = False
    
    @meta_heal
    def target_function():
        raise ValueError("Permanent failure")
        
    with pytest.raises(ValueError, match="Permanent failure"):
        target_function()
    assert mock_execute.call_count == 1

def test_meta_heal_decorator_prevents_recursion():
    _is_healing.active = True
    
    @meta_heal
    def target_function():
        raise ValueError("Inner failure")
        
    try:
        with pytest.raises(ValueError):
            target_function()
    finally:
        _is_healing.active = False

if __name__ == "__main__":
    pytest.main(['-v', __file__])
