import pytest
from unittest.mock import patch, MagicMock
from backend.genesis.symbiotic_version_control import SymbioticVersionControl
from models.genesis_key_models import GenesisKey, GenesisKeyType

@pytest.fixture
def mock_session():
    session = MagicMock()
    # Mock begin_nested context manager
    session.begin_nested.return_value.__enter__.return_value = MagicMock()
    return session

@pytest.fixture
def symbiotic(mock_session, tmp_path):
    with patch('os.makedirs'):
        return SymbioticVersionControl(base_path=str(tmp_path), session=mock_session)

@patch('backend.genesis.symbiotic_version_control.session_scope')
@patch('backend.genesis.symbiotic_version_control.get_genesis_service')
@patch('backend.genesis.symbiotic_version_control.get_file_version_tracker')
def test_track_file_change(mock_get_tracker, mock_get_genesis, mock_session_scope, symbiotic):
    # Setup session context manager mock
    session_mock = MagicMock()
    session_mock.begin_nested.return_value.__enter__.return_value = MagicMock()
    mock_session_scope.return_value.__enter__.return_value = session_mock

    # Mock Genesis Service
    genesis_service = MagicMock()
    mock_key = GenesisKey(
        key_id="GK-123",
        context_data={}
    )
    genesis_service.create_key.return_value = mock_key
    mock_get_genesis.return_value = genesis_service

    # Mock Version Tracker
    tracker = MagicMock()
    tracker.track_file_version.return_value = {
        "changed": True,
        "version_key_id": "VK-123",
        "version_number": 2
    }
    mock_get_tracker.return_value = tracker

    result = symbiotic.track_file_change(
        file_path="src/main.py",
        user_id="user-1",
        change_description="Updated logic"
    )

    assert result["changed"] is True
    assert result["operation_genesis_key"] == "GK-123"
    assert "FILE-" in result["file_genesis_key"]
    assert result["version_key_id"] == "VK-123"
    assert result["symbiotic"] is True

    # Check key updates
    assert mock_key.context_data["version_key_id"] == "VK-123"
    session_mock.refresh.assert_called_with(mock_key)

if __name__ == "__main__":
    pytest.main(['-v', __file__])
