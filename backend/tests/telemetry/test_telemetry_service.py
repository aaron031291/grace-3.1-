import pytest
from unittest.mock import MagicMock, patch
from telemetry.telemetry_service import TelemetryService, get_telemetry_service
from models.telemetry_models import OperationType, OperationStatus

@pytest.fixture
def mock_session():
    session = MagicMock()
    return session

@pytest.fixture
def telemetry_service(mock_session):
    return TelemetryService(session=mock_session)

def test_get_telemetry_service(mock_session):
    service = get_telemetry_service(session=mock_session)
    assert isinstance(service, TelemetryService)
    assert service.session == mock_session

def test_track_operation_success(telemetry_service, mock_session):
    with telemetry_service.track_operation(
        operation_type=OperationType.INGESTION,
        operation_name="test_op",
        input_data={"test": "data"}
    ) as run_id:
        assert isinstance(run_id, str)
        assert len(run_id) > 0
    
    assert mock_session.add.call_count >= 1
    assert mock_session.commit.call_count >= 2

def test_track_operation_failure(telemetry_service, mock_session):
    with pytest.raises(ValueError):
        with telemetry_service.track_operation(
            operation_type=OperationType.INGESTION,
            operation_name="test_op_fail"
        ) as run_id:
            raise ValueError("Test error")
    
    assert mock_session.commit.call_count >= 2

def test_record_tokens(telemetry_service, mock_session):
    mock_op = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_op
    
    telemetry_service.record_tokens("run-123", input_tokens=10, output_tokens=20)
    
    assert mock_op.input_tokens == 10
    assert mock_op.output_tokens == 20
    mock_session.commit.assert_called_once()

def test_record_confidence(telemetry_service, mock_session):
    mock_op = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_op
    
    telemetry_service.record_confidence("run-456", confidence_score=0.9, contradiction_detected=True)
    
    assert mock_op.confidence_score == 0.9
    assert mock_op.contradiction_detected is True
    mock_session.commit.assert_called_once()
