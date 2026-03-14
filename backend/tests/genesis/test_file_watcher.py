import pytest
import os
import time
from unittest.mock import MagicMock, patch
from watchdog.events import FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
from backend.genesis.file_watcher import GenesisFileWatcher, FileWatcherService

@pytest.fixture
def temp_watcher(tmp_path):
    watcher = GenesisFileWatcher(str(tmp_path))
    
    mock_vc = MagicMock()
    mock_vc.track_file_change.return_value = {"operation_genesis_key": "gk-1"}
    watcher.symbiotic_vc = mock_vc
    
    yield watcher, tmp_path, mock_vc

def test_should_ignore(temp_watcher):
    watcher, tmp_path, mock_vc = temp_watcher
    
    assert watcher._should_ignore("/workspace/src/test.pyc") is True
    assert watcher._should_ignore("/workspace/.git/config") is True
    assert watcher._should_ignore("/workspace/logs/app.log") is True
    assert watcher._should_ignore("/workspace/layer_1/genesis_key/test.json") is True
    assert watcher._should_ignore("/workspace/GU-123/profile.json") is True
    
    assert watcher._should_ignore("/workspace/src/main.py") is False

def test_debounce(temp_watcher):
    watcher, tmp_path, mock_vc = temp_watcher
    
    file_path = "/workspace/src/app.py"
    
    # First time, not debounced
    assert watcher._is_debounced(file_path) is False
    
    # Immediately after, should be debounced
    assert watcher._is_debounced(file_path) is True
    
    # Fake time passing
    watcher.last_modified[file_path] -= 3.0
    
    # Should not be debounced anymore
    assert watcher._is_debounced(file_path) is False

def test_on_modified(temp_watcher):
    watcher, tmp_path, mock_vc = temp_watcher
    
    # We must patch _HARD_IGNORE_FRAGMENTS and _should_ignore logic temporarily 
    # since tmp_path is in AppData/Temp which is hard-ignored.
    watcher._HARD_IGNORE_FRAGMENTS = tuple()
    
    test_file = tmp_path / "test.py"
    test_file.write_text("code")
    
    event = FileModifiedEvent(src_path=str(test_file))
    watcher.on_modified(event)
    
    mock_vc.track_file_change.assert_called_once()
    assert watcher.files_tracked == 1

def test_on_created(temp_watcher):
    watcher, tmp_path, mock_vc = temp_watcher
    
    watcher._HARD_IGNORE_FRAGMENTS = tuple()
    
    test_file = tmp_path / "new.py"
    # File needs content to be tracked by on_created
    test_file.write_text("Hello")
    
    event = FileCreatedEvent(src_path=str(test_file))
    watcher.on_created(event)
    
    mock_vc.track_file_change.assert_called_once()
    
def test_file_watcher_service():
    service = FileWatcherService()
    
    with patch('backend.genesis.file_watcher.Observer') as mock_obs:
        mock_inst = MagicMock()
        mock_obs.return_value = mock_inst
        
        # Start
        started = service.start_watching("/tmp/watch")
        assert started is True
        assert "/tmp/watch" in service.observers
        mock_inst.schedule.assert_called_once()
        mock_inst.start.assert_called_once()
        
        # Start again should fail
        started2 = service.start_watching("/tmp/watch")
        assert started2 is False
        
        # Get stats
        stats = service.get_statistics()
        assert stats["active_watchers"] == 1
        
        # Stop
        stopped = service.stop_watching("/tmp/watch")
        assert stopped is True
        assert "/tmp/watch" not in service.observers
        mock_inst.stop.assert_called_once()

if __name__ == "__main__":
    pytest.main(['-v', __file__])
