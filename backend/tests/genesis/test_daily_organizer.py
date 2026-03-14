import pytest
import os
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from backend.genesis.daily_organizer import GenesisKeyDailyOrganizer
from models.genesis_key_models import GenesisKeyType, GenesisKeyStatus

@pytest.fixture
def temp_organizer(tmp_path):
    layer1 = tmp_path / "layer_1"
    organizer = GenesisKeyDailyOrganizer(layer1_path=str(layer1))
    
    session = MagicMock()
    return organizer, tmp_path, session

def test_export_daily_keys(temp_organizer):
    organizer, tmp_path, session = temp_organizer
    
    k1 = MagicMock()
    k1.key_id = "gk-1"
    k1.key_type = GenesisKeyType.API_REQUEST
    k1.status = GenesisKeyStatus.ACTIVE
    k1.what_description = "API Call"
    k1.who_actor = "user1"
    k1.when_timestamp = datetime.now(timezone.utc)
    k1.where_location = "/api/v1/test"
    k1.why_reason = "testing"
    k1.how_method = "GET"
    k1.file_path = None
    k1.is_error = False
    k1.error_message = None
    k1.metadata_human = None
    
    k2 = MagicMock()
    k2.key_id = "gk-2"
    k2.key_type = GenesisKeyType.FIX
    k2.status = GenesisKeyStatus.ACTIVE
    k2.what_description = "Fixed bug"
    k2.who_actor = "agent1"
    k2.when_timestamp = datetime.now(timezone.utc)
    k2.where_location = "app.py"
    k2.why_reason = "bug"
    k2.how_method = "replace"
    k2.file_path = "app.py"
    k2.is_error = False
    k2.error_message = None
    k2.metadata_human = None
    
    # Mock query
    query_mock = MagicMock()
    session.query.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = [k1, k2]
    
    target = datetime.now(timezone.utc)
    res = organizer.export_daily_keys(target_date=target, session=session)
    
    assert res["exported"] is True
    assert res["total_keys"] == 2
    
    date_str = target.strftime("%Y-%m-%d")
    folder = tmp_path / "layer_1" / "genesis_keys" / date_str
    
    assert (folder / "metadata.json").exists()
    assert (folder / "DAILY_SUMMARY.md").exists()
    assert (folder / "all_keys.json").exists()
    assert (folder / "api_requests.json").exists()
    assert (folder / "fixes.json").exists()

def test_export_empty_day(temp_organizer):
    organizer, tmp_path, session = temp_organizer
    
    session.query.return_value.filter.return_value.all.return_value = []
    
    res = organizer.export_daily_keys(session=session)
    assert res["exported"] is False
    assert res["total_keys"] == 0

def test_list_organized_days(temp_organizer):
    organizer, tmp_path, session = temp_organizer
    
    # Create fake day folders
    (tmp_path / "layer_1" / "genesis_keys" / "2026-01-01").mkdir(parents=True)
    (tmp_path / "layer_1" / "genesis_keys" / "2026-01-02").mkdir(parents=True)
    
    days = organizer.list_organized_days()
    assert len(days) == 2
    assert "2026-01-02" in days

def test_get_daily_summary(temp_organizer):
    organizer, tmp_path, session = temp_organizer
    day_folder = tmp_path / "layer_1" / "genesis_keys" / "2026-01-01"
    day_folder.mkdir(parents=True)
    
    with open(day_folder / "metadata.json", "w") as f:
        json.dump({"test": "data"}, f)
        
    summary = organizer.get_daily_summary("2026-01-01")
    assert summary == {"test": "data"}
    
    assert organizer.get_daily_summary("2026-01-02") is None

if __name__ == "__main__":
    pytest.main(['-v', __file__])
