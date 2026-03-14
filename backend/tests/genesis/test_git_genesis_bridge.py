import pytest
import os
import subprocess
from unittest.mock import MagicMock, patch
from backend.genesis.git_genesis_bridge import GitGenesisBridge, get_git_genesis_bridge

@pytest.fixture
def temp_bridge(tmp_path):
    bridge = GitGenesisBridge(repo_path=str(tmp_path))
    return bridge, tmp_path

def test_run_git_command(temp_bridge):
    bridge, tmp_path = temp_bridge
    
    with patch('subprocess.run') as mock_run:
        mock_result = MagicMock()
        mock_result.stdout = "output\n"
        mock_run.return_value = mock_result
        
        output = bridge._run_git_command(['log'])
        assert output == "output"
        mock_run.assert_called_once()
        
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, ['git'])
        mock_run.side_effect.stderr = "error"
        output = bridge._run_git_command(['log'])
        assert output is None

def test_get_last_commit_info(temp_bridge):
    bridge, tmp_path = temp_bridge
    
    with patch.object(bridge, '_run_git_command') as mock_run:
        mock_run.side_effect = [
            "abc1234",
            "Initial commit",
            "testuser",
            "test@example.com",
            "1612345678"
        ]
        
        info = bridge.get_last_commit_info()
        assert info["sha"] == "abc1234"
        assert info["message"] == "Initial commit"
        assert info["author"] == "testuser"
        assert info["timestamp"] == 1612345678

def test_get_files_changed_in_last_commit(temp_bridge):
    bridge, tmp_path = temp_bridge
    
    with patch.object(bridge, '_run_git_command') as mock_run:
        mock_run.return_value = "file1.txt\nfile2.py"
        files = bridge.get_files_changed_in_last_commit()
        assert files == ["file1.txt", "file2.py"]

def test_sync_git_commit_to_genesis_keys(temp_bridge):
    bridge, tmp_path = temp_bridge
    
    with patch.object(bridge, 'get_last_commit_info') as mock_info, \
         patch.object(bridge, 'get_files_changed_in_last_commit') as mock_files, \
         patch.object(bridge, '_get_symbiotic_vc') as mock_symbiotic, \
         patch('os.path.exists') as mock_exists:
         
        mock_info.return_value = {"sha": "abc", "author_email": "x@x", "message": "msg", "author": "author"}
        mock_files.return_value = ["test.txt"]
        mock_exists.return_value = True
        
        symbiotic_mock = MagicMock()
        symbiotic_mock.track_file_change.return_value = {"operation_genesis_key": "gk-abc", "version_number": 1}
        mock_symbiotic.return_value = symbiotic_mock
        
        res = bridge.sync_git_commit_to_genesis_keys()
        assert res["status"] == "success"
        assert res["files_tracked"] == 1
        assert res["genesis_keys"][0]["genesis_key"] == "gk-abc"

def test_create_post_commit_hook(temp_bridge):
    bridge, tmp_path = temp_bridge
    
    res = bridge.create_post_commit_hook()
    assert res is True
    
    hook_path = tmp_path / ".git" / "hooks" / "post-commit"
    assert hook_path.exists()
    
def test_auto_commit_genesis_tracked_files(temp_bridge):
    bridge, tmp_path = temp_bridge
    
    with patch.object(bridge, '_run_git_command') as mock_run:
        mock_run.return_value = "abc"
        res = bridge.auto_commit_genesis_tracked_files("msg", ["a.txt"])
        assert res == "abc"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
