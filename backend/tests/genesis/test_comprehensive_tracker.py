import pytest
from unittest.mock import MagicMock
from backend.genesis.comprehensive_tracker import ComprehensiveTracker
from models.genesis_key_models import GenesisKeyType

@pytest.fixture
def mock_db():
    db = MagicMock()
    # Mock for filtering
    query_mock = MagicMock()
    db.query.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.all.return_value = []
    
    return db

@pytest.fixture
def tracker(mock_db):
    return ComprehensiveTracker(db_session=mock_db, user_id="test_user", session_id="test_sess")

def test_track_user_input(tracker, mock_db):
    tracker.track_user_input("hello", "text", {"meta": "data"})
    assert mock_db.add.called
    assert mock_db.commit.called

def test_track_user_upload(tracker, mock_db):
    tracker.track_user_upload("test.txt", "/tmp/test.txt", 100, "text/plain")
    assert mock_db.add.called
    assert mock_db.commit.called
    
def test_track_ai_response(tracker, mock_db):
    tracker.track_ai_response("hi", "hello there", "gpt-4", 100)
    assert mock_db.add.called
    assert mock_db.commit.called
    
def test_track_ai_code_generation(tracker, mock_db):
    tracker.track_ai_code_generation("test.py", "print('hello')", "python", "testing", "gpt-4")
    assert mock_db.add.called
    assert mock_db.commit.called

def test_track_coding_agent_action(tracker, mock_db):
    tracker.track_coding_agent_action("refactor", "refactored x", ["x.py"], {"success": True})
    assert mock_db.add.called
    assert mock_db.commit.called

def test_track_external_api_call(tracker, mock_db):
    tracker.track_external_api_call("github", "/users", "GET")
    assert mock_db.add.called
    assert mock_db.commit.called

def test_track_web_fetch(tracker, mock_db):
    tracker.track_web_fetch("http://example.com", "<html>", "text/html", 200, "search")
    assert mock_db.add.called
    assert mock_db.commit.called

def test_track_file_ingestion(tracker, mock_db):
    tracker.track_file_ingestion("doc.pdf", "/tmp/doc.pdf", 1, 10, 10)
    assert mock_db.add.called
    assert mock_db.commit.called
    
def test_track_librarian_action(tracker, mock_db):
    tracker.track_librarian_action(1, "categorize", ["tag1"], 5, ["rule1"])
    assert mock_db.add.called
    assert mock_db.commit.called

def test_track_database_change(tracker, mock_db):
    tracker.track_database_change("users", "INSERT", 1, None, {"name": "test"})
    assert mock_db.add.called
    assert mock_db.commit.called
    
def test_track_system_event(tracker, mock_db):
    tracker.track_system_event("startup", "System started")
    assert mock_db.add.called
    assert mock_db.commit.called

if __name__ == "__main__":
    pytest.main(['-v', __file__])
