import pytest
import os
import json
from unittest.mock import MagicMock, patch
from backend.genesis.directory_hierarchy import DirectoryGenesisKey, get_directory_hierarchy

@pytest.fixture
def temp_hierarchy(tmp_path):
    # Mock genesis service
    with patch('backend.genesis.directory_hierarchy.get_genesis_service') as mock_gk:
        
        gk_inst = MagicMock()
        gk_mock_key = MagicMock()
        gk_mock_key.key_id = "gk-dir-123"
        gk_inst.create_key.return_value = gk_mock_key
        mock_gk.return_value = gk_inst
        
        base_path = tmp_path / "test_kb"
        base_path.mkdir()
        
        dh = DirectoryGenesisKey(base_path=str(base_path))
        yield dh, base_path, gk_inst

def test_initialization(temp_hierarchy):
    dh, base_path, gk_inst = temp_hierarchy
    assert os.path.exists(dh.metadata_file)
    assert dh.directory_keys["directories"] == {}

def test_create_directory_genesis_key(temp_hierarchy):
    dh, base_path, gk_inst = temp_hierarchy
    
    info = dh.create_directory_genesis_key("docs/api")
    
    assert info["path"] == "docs/api"
    assert "genesis_key" in info
    assert os.path.exists(os.path.join(base_path, "docs/api", ".genesis_key_info.md"))
    
    # Should be saved to metadata
    assert "docs/api" in dh.directory_keys["directories"]

def test_create_hierarchy(temp_hierarchy):
    dh, base_path, gk_inst = temp_hierarchy
    
    # Create some dummy directories
    (base_path / "root_dir").mkdir()
    (base_path / "root_dir" / "sub_dir").mkdir()
    (base_path / "root_dir" / "file.txt").write_text("hello")
    
    tree = dh.create_hierarchy("root_dir", scan_existing=True)
    
    assert "root_dir" in dh.directory_keys["directories"]
    assert "root_dir\\sub_dir" in dh.directory_keys["directories"] or "root_dir/sub_dir" in dh.directory_keys["directories"]
    assert tree["name"] == "root_dir"
    assert len(tree["subdirectories"]) == 1

def test_add_file_version(temp_hierarchy):
    dh, base_path, gk_inst = temp_hierarchy
    
    dh.create_directory_genesis_key("src")
    
    # Reset mock to test file version key creation
    gk_inst.create_key.reset_mock()
    gk_mock_key = MagicMock()
    gk_mock_key.key_id = "gk-file-123"
    gk_inst.create_key.return_value = gk_mock_key
    
    # Needs actual file to get size gracefully, or it just sets None. We'll set it up.
    (base_path / "src" / "app.py").write_text("code")
    
    res = dh.add_file_version("src", "app.py", version_note="Init")
    
    assert res["version_number"] == 1
    assert res["file_path"] == "src\\app.py" or res["file_path"] == "src/app.py"
    assert res["version_key"] == "gk-file-123"
    assert dh.directory_keys["directories"]["src"]["version_count"] == 1

def test_get_hierarchy_statistics(temp_hierarchy):
    dh, base_path, gk_inst = temp_hierarchy
    
    dh.create_directory_genesis_key("dir1")
    dh.create_directory_genesis_key("dir2")
    
    stats = dh.get_hierarchy_statistics()
    assert stats["total_directories"] == 2
    assert stats["total_versions"] == 0

if __name__ == "__main__":
    pytest.main(['-v', __file__])
