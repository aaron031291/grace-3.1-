import pytest
import os
import json
from unittest.mock import MagicMock, patch
from backend.genesis.repo_scanner import RepoScanner, scan_and_save_repo

@pytest.fixture
def temp_repo(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    
    (repo_path / "src").mkdir()
    (repo_path / "src" / "main.py").write_text("print('hello')")
    
    (repo_path / "tests").mkdir()
    (repo_path / "tests" / "test_main.py").write_text("def test_main(): pass")
    
    # Excluded folder
    (repo_path / ".git").mkdir()
    (repo_path / ".git" / "config").write_text("cfg")
    
    return str(repo_path)

def test_repo_scanner_basic(temp_repo, tmp_path):
    scanner = RepoScanner(temp_repo)
    result = scanner.scan_repository()
    
    assert result["statistics"]["total_directories"] == 3 # root, src, tests
    assert result["statistics"]["total_files"] == 2
    assert ".git" not in result["directories"]
    assert "src/main.py" in result["files"] or "src\\main.py" in result["files"]

def test_save_immutable_memory(temp_repo, tmp_path):
    scanner = RepoScanner(temp_repo)
    scanner.scan_repository()
    
    out_file = str(tmp_path / "mem.json")
    scanner.save_immutable_memory(out_file)
    
    assert os.path.exists(out_file)
    with open(out_file, "r") as f:
        data = json.load(f)
        assert data["statistics"]["total_files"] == 2

def test_find_by_genesis_key(temp_repo):
    scanner = RepoScanner(temp_repo)
    scanner.scan_repository()
    
    file_path = "src/main.py" if "src/main.py" in scanner.immutable_memory["files"] else "src\\main.py"
    gk = scanner.immutable_memory["files"][file_path]["genesis_key"]
    
    found = scanner.find_by_genesis_key(gk)
    assert found["type"] == "file"
    assert found["info"]["name"] == "main.py"

@patch('backend.genesis.repo_scanner.RepoScanner.integrate_with_version_tracking')
def test_scan_and_save_repo(mock_track, temp_repo, tmp_path):
    mock_track.return_value = {"tracked": 2}
    
    result = scan_and_save_repo(temp_repo, integrate_version_tracking=True)
    
    assert "version_tracking" in result
    assert result["version_tracking"]["tracked"] == 2
    mock_track.assert_called_once()
    
if __name__ == "__main__":
    pytest.main(['-v', __file__])
