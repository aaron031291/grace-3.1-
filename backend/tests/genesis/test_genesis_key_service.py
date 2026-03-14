import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from genesis.genesis_key_service import GenesisKeyService
from models.genesis_key_models import GenesisKeyType, GenesisKeyStatus, UserProfile, GenesisKey, FixSuggestion

@pytest.fixture
def mock_session():
    return MagicMock()

@pytest.fixture
def service(mock_session):
    return GenesisKeyService(session=mock_session)

def test_generate_user_id(service):
    user_id_1 = service.generate_user_id("test@example.com")
    user_id_2 = service.generate_user_id("test@example.com")
    assert user_id_1 == user_id_2
    assert user_id_1.startswith("GU-")
    
    user_id_3 = service.generate_user_id()
    assert user_id_3.startswith("GU-")

def test_get_or_create_user_existing(service, mock_session):
    mock_user = UserProfile(user_id="GU-123", username="test")
    mock_session.query().filter().first.return_value = mock_user
    
    user = service.get_or_create_user(user_id="GU-123")
    assert user == mock_user
    mock_session.add.assert_not_called()

def test_get_or_create_user_new(service, mock_session):
    mock_session.query().filter().first.return_value = None
    
    user = service.get_or_create_user(email="new@example.com")
    assert user.email == "new@example.com"
    assert "GU-" in user.user_id
    mock_session.add.assert_called_once()

@patch('genesis.genesis_key_service.get_kb_integration')
@patch('genesis.genesis_key_service.datetime')
def test_create_key(mock_datetime, mock_kb, service, mock_session):
    # Setup mock returns
    mock_session.query().filter().first.return_value = None
    mock_datetime.now.return_value = datetime(2023, 1, 1)
    
    key = service.create_key(
        key_type=GenesisKeyType.SYSTEM_EVENT,
        what_description="Test event",
        who_actor="System",
        where_location="test_module",
        user_id="GU-123"
    )
    
    assert key.key_id.startswith("GK-")
    assert key.what_description == "Test event"
    assert key.status == GenesisKeyStatus.ACTIVE
    
    # Session add should be called via begin_nested block
    mock_session.add.assert_called()

def test_create_fix_suggestion(service, mock_session):
    suggestion = service.create_fix_suggestion(
        genesis_key_id="GK-123",
        suggestion_type="code_fix",
        title="Fix NPE",
        description="Fix NoneType error",
        severity="high"
    )
    
    assert suggestion.suggestion_id.startswith("FS-")
    assert suggestion.genesis_key_id == "GK-123"
    mock_session.add.assert_called_once()

@patch.object(GenesisKeyService, 'create_key')
def test_apply_fix(mock_create, service, mock_session):
    mock_suggestion = FixSuggestion(
        suggestion_id="FS-123", genesis_key_id="GK-123", title="Test fix"
    )
    mock_original_key = GenesisKey(
        key_id="GK-123", what_description="Original error"
    )
    mock_fix_key = GenesisKey(key_id="GK-456")
    
    mock_create.return_value = mock_fix_key
    
    # Query logic mock
    def query_side_effect(*args):
        mock_query = MagicMock()
        if args[0] == FixSuggestion:
            mock_query.filter().first.return_value = mock_suggestion
        else:
            mock_query.filter().first.return_value = mock_original_key
        return mock_query
    
    mock_session.query.side_effect = query_side_effect
    
    result = service.apply_fix("FS-123", "User")
    assert result == mock_fix_key
    assert mock_original_key.fix_applied is True
    assert mock_original_key.status == GenesisKeyStatus.FIXED

if __name__ == "__main__":
    pytest.main(['-v', __file__])
