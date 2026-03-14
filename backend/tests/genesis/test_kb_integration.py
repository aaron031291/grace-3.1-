import pytest
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from backend.genesis.kb_integration import GenesisKBIntegration
from models.genesis_key_models import GenesisKeyType

@pytest.fixture
def temp_kb(tmp_path):
    kb_path = tmp_path / "knowledge_base"
    return GenesisKBIntegration(kb_base_path=str(kb_path))

def test_initialization(temp_kb, tmp_path):
    assert os.path.exists(temp_kb.genesis_key_path)
    assert os.path.exists(os.path.join(temp_kb.genesis_key_path, "README.md"))

def test_save_genesis_key_dict(temp_kb):
    key_dict = {
        "user_id": "test_user",
        "session_id": "sess_123",
        "key_type": "FILE_OPERATION",
        "what_description": "Test operation",
        "when_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    file_path = temp_kb.save_genesis_key(key_dict)
    
    assert file_path is not None
    assert os.path.exists(file_path)
    assert "test_user" in file_path
    assert "session_sess_123.json" in file_path
    
    with open(file_path, "r") as f:
        data = json.load(f)
        assert data["user_id"] == "test_user"
        assert len(data["keys"]) == 1
        assert data["keys"][0]["key_type"] == "FILE_OPERATION"

def test_save_genesis_key_no_session(temp_kb):
    key_dict = {
        "user_id": "test_user_2",
        "key_type": "INPUT",
        # no session_id
    }
    
    file_path = temp_kb.save_genesis_key(key_dict)
    
    assert file_path is not None
    assert "keys_" in file_path

def test_save_user_profile(temp_kb):
    profile = {"name": "Test Name", "role": "admin"}
    file_path = temp_kb.save_user_profile("test_user_3", profile)
    
    assert file_path is not None
    assert "profile.json" in file_path
    
    with open(file_path, "r") as f:
        data = json.load(f)
        assert data["name"] == "Test Name"
        assert "last_updated" in data

def test_create_user_summary(temp_kb):
    # Save a few keys with session_id accessible directly in the key or in context_data
    # kb_integration's get_user_keys strips out root metadata, so we need it inside the key
    temp_kb.save_genesis_key({
        "user_id": "test_summary",
        "key_type": "INPUT",
        "context_data": {"session_id": "sess_A"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    temp_kb.save_genesis_key({
        "user_id": "test_summary",
        "key_type": "ERROR",
        "is_error": True,
        "context_data": {"session_id": "sess_B"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    summary = temp_kb.create_user_summary("test_summary")
    
    assert summary["total_keys"] == 2
    assert summary["total_errors"] == 1
    assert "sess_A" in summary["active_sessions"]
    assert "sess_B" in summary["active_sessions"]
    assert summary["key_types"]["INPUT"] == 1
    assert summary["key_types"]["ERROR"] == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
