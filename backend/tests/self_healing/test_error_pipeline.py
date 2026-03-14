import pytest
from unittest.mock import patch, MagicMock
from backend.self_healing.error_pipeline import (
    classify_error, 
    ErrorPipeline, 
    _already_seen, 
    _SEEN_ERRORS,
    report_error,
    get_error_pipeline
)

def test_classify_error():
    assert classify_error(ConnectionError("Connection refused")) == "network"
    assert classify_error(AttributeError("object has no attribute 'foo'")) == "attribute"
    assert classify_error(ImportError("cannot import name 'X'")) == "import"
    assert classify_error(NameError("name 'x' is not defined")) == "name"
    assert classify_error(TypeError("takes 1 positional argument")) == "type"
    assert classify_error(ValueError("invalid literal for int()")) == "value"
    assert classify_error(Exception("UndefinedTable: users does not exist")) == "schema"
    assert classify_error(Exception("Something completely unknown")) == "unknown"

def test_already_seen_deduplication():
    _SEEN_ERRORS.clear()
    key = "TestError::test.module"
    
    assert _already_seen(key) is False
    assert _already_seen(key) is True
    assert _already_seen("DifferentError::test.module") is False

@patch("backend.self_healing.error_pipeline.ErrorPipeline.handle")
def test_report_error_convenience(mock_handle):
    exc = ValueError("test")
    report_error(exc, module="test_module", function="test_func")
    mock_handle.assert_called_once_with(exc, None, "test_module", "test_func")

def test_error_pipeline_handle_queueing():
    _SEEN_ERRORS.clear()
    pipeline = get_error_pipeline()
    
    # Drain queue first
    while not pipeline._task_queue.empty():
        pipeline._task_queue.get_nowait()
        
    exc = AttributeError("test error")
    pipeline.handle(exc, module="test_module")
    
    assert not pipeline._task_queue.empty()
    item = pipeline._task_queue.get_nowait()
    assert item["error_class"] == "attribute"
    assert item["exc_type"] == "AttributeError"
    
@patch("backend.self_healing.error_pipeline.ErrorPipeline._heal_schema")
def test_pipeline_process_schema_routing(mock_heal_schema):
    mock_heal_schema.return_value = (True, "Fixed schema")
    
    pipeline = get_error_pipeline()
    payload = {
        "error_class": "schema",
        "exc_str": "UndefinedTable: users",
        "location": "db.py",
        "exc_type": "Exception",
        "tb": "",
        "timestamp": "2023-01-01T00:00:00Z",
        "context": {}
    }
    
    # Needs patches for telemetry and memory to avoid side effects
    with patch("backend.self_healing.error_pipeline._TELEMETRY_OK", False):
        with patch.object(pipeline, '_record_learning'):
            pipeline._process(payload)
            mock_heal_schema.assert_called_once_with(payload)

if __name__ == "__main__":
    pytest.main(['-v', __file__])
