import pytest
import os
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from backend.genesis.archival_service import ArchivalService
from models.genesis_key_models import GenesisKeyType, GenesisKeyStatus, GenesisKeyArchive

@pytest.fixture
def temp_archival(tmp_path):
    # Setup mock session
    session = MagicMock()
    
    query_mock = MagicMock()
    session.query.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    
    # Needs to return a mock GenesisKeyArchive for get_archive_for_date
    mock_archive = MagicMock(spec=GenesisKeyArchive)
    query_mock.first.return_value = mock_archive
    query_mock.all.return_value = [mock_archive]
    
    service = ArchivalService(archive_base_path=str(tmp_path), session=session)
    return service, tmp_path, session

def test_archive_daily_keys(temp_archival):
    service, tmp_path, session = temp_archival
    
    # Mock keys
    k1 = MagicMock()
    k1.key_type = GenesisKeyType.FILE_OPERATION
    k1.status = GenesisKeyStatus.ACTIVE
    k1.is_error = False
    k1.user_id = "user1"
    k1.file_path = "test.py"
    k1.when_timestamp = datetime.now(timezone.utc) - timedelta(hours=12)
    k1.who_actor = "actor1"
    
    k2 = MagicMock()
    k2.key_type = GenesisKeyType.FIX
    k2.status = GenesisKeyStatus.ACTIVE
    k2.is_error = True
    k2.error_type = "ValueError"
    k2.user_id = "user1"
    k2.file_path = "test.py"
    k2.when_timestamp = datetime.now(timezone.utc) - timedelta(hours=6)
    k2.who_actor = "actor1"
    
    query_mock = session.query.return_value.filter.return_value
    query_mock.all.return_value = [k1, k2]
    
    target = datetime.now(timezone.utc)
    
    # Run
    res = service.archive_daily_keys(target_date=target, session=session)
    
    assert res is not None
    assert res.key_count == 2
    assert res.error_count == 1
    assert res.fix_count == 1
    
    # Should be saved
    date_str = target.strftime('%Y-%m-%d')
    assert os.path.exists(tmp_path / date_str)
    
    # Check if files generated
    assert os.path.exists(tmp_path / date_str / f"genesis_keys_{date_str}.json")
    assert os.path.exists(tmp_path / date_str / f"report_{date_str}.txt")
    assert os.path.exists(tmp_path / date_str / f"data_{date_str}.json")

def test_get_archive_for_date(temp_archival):
    service, tmp_path, session = temp_archival
    
    target = datetime.now()
    res = service.get_archive_for_date(target, session)
    assert res is not None

def test_list_archives(temp_archival):
    service, tmp_path, session = temp_archival
    
    mock_archive = MagicMock()
    session.query.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_archive]
    
    res = service.list_archives(session=session)
    assert len(res) == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
