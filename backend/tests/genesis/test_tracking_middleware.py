import pytest
from unittest.mock import MagicMock, patch
from backend.genesis.tracking_middleware import track_file_operation, track_database_operation

@pytest.fixture
def mock_tracker():
    with patch('backend.genesis.tracking_middleware.SessionLocal'), \
         patch('backend.genesis.tracking_middleware.ComprehensiveTracker') as MockTracker:
             
        instance = MagicMock()
        mock_key = MagicMock()
        mock_key.key_id = "gk-123"
        instance._create_genesis_key.return_value = mock_key
        MockTracker.return_value = instance
        
        yield instance

def test_track_file_operation(mock_tracker):
    # Create decorated function
    @track_file_operation("upload")
    def do_upload(file_path):
        return "success"
        
    result = do_upload(file_path="/tmp/test.txt")
    
    assert result == "success"
    assert mock_tracker._create_genesis_key.call_count == 2
    
    # Check start key
    call_args_start = mock_tracker._create_genesis_key.call_args_list[0][1]
    assert call_args_start["where_location"] == "/tmp/test.txt"
    assert call_args_start["tags"] == ["file-operation", "upload"]
    
    # Check end key
    call_args_end = mock_tracker._create_genesis_key.call_args_list[1][1]
    assert call_args_end["parent_key_id"] == "gk-123"
    assert call_args_end["output_data"]["result"] == "success"

def test_track_file_operation_error(mock_tracker):
    @track_file_operation("read")
    def do_error(file_path):
        raise ValueError("test error")
        
    with pytest.raises(ValueError, match="test error"):
        do_error("/tmp/err.txt")
        
    # Start key + Error key
    assert mock_tracker._create_genesis_key.call_count == 2
    
    call_args_end = mock_tracker._create_genesis_key.call_args_list[1][1]
    assert call_args_end["is_error"] is True
    assert call_args_end["error_type"] == "ValueError"

def test_track_database_operation(mock_tracker):
    @track_database_operation("users", "INSERT")
    def do_insert():
        return 1
        
    result = do_insert()
    
    assert result == 1
    mock_tracker.track_database_change.assert_called_once_with(
        table_name="users",
        operation="INSERT",
        data_after={"result": "1"}
    )

if __name__ == "__main__":
    pytest.main(['-v', __file__])
