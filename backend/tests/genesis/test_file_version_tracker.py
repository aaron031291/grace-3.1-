import pytest
import os
import json
from unittest.mock import patch, MagicMock
from backend.genesis.file_version_tracker import FileVersionTracker

@pytest.fixture
def mock_session():
    session = MagicMock()
    session.begin_nested.return_value.__enter__.return_value = MagicMock()
    return session

@pytest.fixture
def temp_tracker(tmp_path, mock_session):
    # Use tmp_path to simulate a file system without affecting actual files
    tracker = FileVersionTracker(base_path=str(tmp_path), session=mock_session)
    return tracker

def test_metadata_creation(temp_tracker, tmp_path):
    metadata_file = os.path.join(tmp_path, ".genesis_file_versions.json")
    assert os.path.exists(metadata_file)
    with open(metadata_file, 'r') as f:
        data = json.load(f)
        assert "version" in data
        assert "files" in data

def test_track_file_version_new_file(temp_tracker, tmp_path):
    # Create a test file in the tmp_path
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello World!")
    
    with patch('backend.genesis.file_version_tracker.get_genesis_service') as mock_genesis:
        genesis_service = MagicMock()
        mock_key = MagicMock()
        mock_key.key_id = "GK-VER-1"
        genesis_service.create_key.return_value = mock_key
        mock_genesis.return_value = genesis_service
        
        result = temp_tracker.track_file_version(
            file_genesis_key="FILE-123",
            file_path="test.txt",
            user_id="user-1"
        )
        
        assert result["changed"] is True
        assert result["version_number"] == 1
        assert result["file_genesis_key"] == "FILE-123"
        assert result["genesis_key_db_id"] == "GK-VER-1"
        
        # Verify it's in metadata
        files = temp_tracker.version_metadata["files"]
        assert "FILE-123" in files
        assert len(files["FILE-123"]["versions"]) == 1

def test_track_file_version_unchanged(temp_tracker, tmp_path):
    # Create file
    test_file = tmp_path / "test2.txt"
    test_file.write_text("Hello World!")
    
    with patch('backend.genesis.file_version_tracker.get_genesis_service') as mock_genesis:
        genesis_service = MagicMock()
        mock_key = MagicMock()
        mock_key.key_id = "GK-VER-1"
        genesis_service.create_key.return_value = mock_key
        mock_genesis.return_value = genesis_service
        
        # First track
        temp_tracker.track_file_version(
            file_genesis_key="FILE-456",
            file_path="test2.txt"
        )
        
        # Second track - should detect no changes
        result2 = temp_tracker.track_file_version(
            file_genesis_key="FILE-456",
            file_path="test2.txt"
        )
        
        assert result2["changed"] is False
        assert result2["version_number"] == 1
        # create_key should only have been called once
        genesis_service.create_key.assert_called_once()

def test_get_file_versions(temp_tracker, tmp_path):
    test_file = tmp_path / "test3.txt"
    test_file.write_text("Initial")
    
    with patch('backend.genesis.file_version_tracker.get_genesis_service') as mock_genesis:
        genesis_service = MagicMock()
        genesis_service.create_key.return_value = MagicMock(key_id="GK")
        mock_genesis.return_value = genesis_service
        
        temp_tracker.track_file_version("FILE-789", "test3.txt")
        
        # Change file
        test_file.write_text("Modified")
        temp_tracker.track_file_version("FILE-789", "test3.txt")
        
        # Test Getters
        latest = temp_tracker.get_latest_version("FILE-789")
        assert latest["version_number"] == 2
        
        v1 = temp_tracker.get_version_details("FILE-789", 1)
        assert v1["version_number"] == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
