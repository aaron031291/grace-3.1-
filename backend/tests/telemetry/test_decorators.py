import pytest
from unittest.mock import MagicMock, patch
from telemetry.decorators import track_operation, track_tokens, track_confidence
from models.telemetry_models import OperationType

@pytest.fixture
def mock_telemetry():
    with patch('telemetry.decorators.get_telemetry_service') as mock_get_telemetry:
        telemetry = MagicMock()
        telemetry.track_operation.return_value.__enter__.return_value = "test-run-id"
        mock_get_telemetry.return_value = telemetry
        yield telemetry

def test_track_operation_basic(mock_telemetry):
    @track_operation(OperationType.INGESTION)
    def simple_func(x, y):
        return x + y

    result = simple_func(2, 3)
    assert result == 5
    mock_telemetry.track_operation.assert_called_once()
    kwargs = mock_telemetry.track_operation.call_args[1]
    assert kwargs['operation_type'] == OperationType.INGESTION
    assert kwargs['operation_name'] == 'simple_func'

def test_track_operation_with_outputs_and_kwargs(mock_telemetry):
    @track_operation(OperationType.INGESTION, capture_inputs=True, capture_outputs=True)
    def complex_func(a, b=2, *, c=3):
        return a + b + c

    result = complex_func(1, c=4)
    assert result == 7
    mock_telemetry.track_operation.assert_called_once()

def test_track_tokens(mock_telemetry):
    @track_tokens
    def token_func(run_id=None):
        return {"input_tokens": 10, "output_tokens": 20, "result": "ok"}
    
    res = token_func(run_id="run-123")
    assert res["result"] == "ok"
    mock_telemetry.record_tokens.assert_called_once_with(run_id="run-123", input_tokens=10, output_tokens=20)

def test_track_confidence(mock_telemetry):
    @track_confidence
    def conf_func(run_id=None):
        return {"confidence_score": 0.95, "contradiction_detected": True, "result": "ok"}
    
    res = conf_func(run_id="run-456")
    assert res["result"] == "ok"
    mock_telemetry.record_confidence.assert_called_once_with(
        run_id="run-456", confidence_score=0.95, contradiction_detected=True
    )
