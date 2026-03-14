import pytest
from unittest.mock import MagicMock, patch
from telemetry.replay_service import ReplayService, get_replay_service
from models.telemetry_models import OperationLog, OperationStatus, OperationType

@pytest.fixture
def mock_session():
    session = MagicMock()
    return session

@pytest.fixture
def replay_service(mock_session):
    return ReplayService(session=mock_session)

def test_get_replay_service(mock_session):
    service = get_replay_service(session=mock_session)
    assert isinstance(service, ReplayService)
    assert service.session == mock_session

def test_replay_operation_success(replay_service, mock_session):
    original_op = MagicMock()
    original_op.run_id = "test-run-123"
    original_op.operation_type = OperationType.INGESTION
    original_op.operation_name = "test_op"
    original_op.metadata = {"inputs": {"x": 1, "y": 2}}
    original_op.duration_ms = 100
    original_op.status = OperationStatus.COMPLETED
    
    replay_op = MagicMock()
    replay_op.status = OperationStatus.COMPLETED
    replay_op.duration_ms = 90
    
    def mock_query(*args):
        query_mock = MagicMock()
        def mock_filter(*args):
            filter_mock = MagicMock()
            def mock_first():
                if mock_query.call_count == 1:
                    return original_op
                return replay_op
            filter_mock.first = mock_first
            return filter_mock
        query_mock.filter = mock_filter
        return query_mock
    
    mock_query.call_count = 0
    def side_effect_query(*args):
        mock_query.call_count += 1
        query_mock = MagicMock()
        def mock_filter(*args):
            filter_mock = MagicMock()
            if mock_query.call_count == 1:
                filter_mock.first.return_value = original_op
            else:
                filter_mock.first.return_value = replay_op
            return filter_mock
        query_mock.filter = mock_filter
        return query_mock

    mock_session.query.side_effect = side_effect_query

    def sample_func(x, y):
        return x + y

    with patch('telemetry.telemetry_service.get_telemetry_service') as mock_get_telemetry:
        mock_telemetry = MagicMock()
        mock_telemetry.track_operation.return_value.__enter__.return_value = "replay-run-456"
        mock_get_telemetry.return_value = mock_telemetry
        
        replay_record = replay_service.replay_operation(
            original_run_id="test-run-123",
            operation_func=sample_func,
            reason="test_reason"
        )
        
        assert replay_record.original_run_id == "test-run-123"
        assert replay_record.replay_run_id == "replay-run-456"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

def test_replay_operation_not_found(replay_service, mock_session):
    mock_session.query.return_value.filter.return_value.first.return_value = None
    
    with pytest.raises(ValueError, match="Operation test-not-found not found"):
        replay_service.replay_operation(
            original_run_id="test-not-found",
            operation_func=lambda: None
        )

def test_replay_operation_no_inputs(replay_service, mock_session):
    original_op = MagicMock()
    original_op.metadata = {}
    mock_session.query.return_value.filter.return_value.first.return_value = original_op
    
    with pytest.raises(ValueError, match="does not have stored inputs"):
        replay_service.replay_operation(
            original_run_id="test-run-123",
            operation_func=lambda: None
        )
