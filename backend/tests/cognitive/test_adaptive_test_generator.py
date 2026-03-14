import pytest
import os
import json
from unittest.mock import patch, MagicMock
from backend.cognitive.adaptive_test_generator import generate_tests_for_module, _generate_basic_test

def test_adaptive_generator_basic():
    func_stub = {
        "name": "mock_func",
        "args": [],
        "docstring": "mock doc",
        "returns": "bool",
        "line": 1,
        "body_lines": 5
    }
    code = _generate_basic_test(func_stub, "some.module.path")
    assert "mock_func" in code
    assert "callable(mock_func)" in code

@patch('backend.cognitive.adaptive_test_generator.publish')
@patch('backend.cognitive.adaptive_test_generator._extract_functions')
@patch('pathlib.Path.read_text')
@patch('pathlib.Path.exists')
def test_generate_tests_event_firing(mock_exists, mock_read, mock_extract, mock_publish):
    mock_exists.return_value = True
    mock_read.return_value = "def mock_func(): pass"
    mock_extract.return_value = [] # no functions to generate tests for initially
    
    result = generate_tests_for_module("some/fake/module.py")
    
    # Needs to publish start and completed. BUT because there are no functions, it returns early.
    # So it should only publish "testing.adaptive_generation_started"
    assert mock_publish.call_count >= 1
    call_topics = [call.args[0] for call in mock_publish.mock_calls]
    assert "testing.adaptive_generation_started" in call_topics

if __name__ == '__main__':
    pytest.main(['-v', __file__])
