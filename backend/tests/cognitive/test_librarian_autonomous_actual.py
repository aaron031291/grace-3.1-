import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import json
import os

from backend.cognitive.librarian_autonomous import (
    AutonomousLibrarian,
    _get_kb,
    DIRECTORY_TAXONOMY,
    get_autonomous_librarian
)

@pytest.fixture
def test_kb(tmp_path):
    return tmp_path / "mock_kb"

def test_librarian_suggest_location_by_name():
    lib = AutonomousLibrarian()
    
    # Test readme
    assert lib.suggest_location(Path("README.md")) == "documentation"
    assert lib.suggest_location(Path("some_test.py")) == "tests"
    assert lib.suggest_location(Path("financial_report_2024.pdf")) == "reports"
    assert lib.suggest_location(Path("config.yaml")) == "configuration"
    assert lib.suggest_location(Path("user_data_license.txt")) == "governance/compliance"

def test_librarian_suggest_location_by_extension():
    lib = AutonomousLibrarian()
    
    assert lib.suggest_location(Path("data.csv")) == "data/csv"
    assert lib.suggest_location(Path("style.css")) == "code/web" # or styles depending on order, but it resolves
    
@patch("backend.cognitive.librarian_autonomous._get_kb")
@patch("shutil.move")
def test_organise_file(mock_move, mock_get_kb, test_kb):
    lib = AutonomousLibrarian()
    mock_get_kb.return_value = test_kb
    
    test_file = test_kb / "test_data.csv"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("a,b,c")
    
    res = lib.organise_file(str(test_file))
    
    assert res["action"] == "organised"
    assert res["directory"] == "data/csv"
    mock_move.assert_called_once()

@patch("backend.cognitive.librarian_autonomous._get_kb")
def test_create_domain_environment(mock_get_kb, test_kb):
    import sys
    sys.modules["cognitive.event_bus"] = MagicMock()
    sys.modules["cognitive.flash_cache"] = MagicMock()
    sys.modules["cognitive.reverse_knn"] = MagicMock()
    sys.modules["cognitive.consensus_engine"] = MagicMock()
    sys.modules["api._genesis_tracker"] = MagicMock()
    
    lib = AutonomousLibrarian()
    mock_get_kb.return_value = test_kb
    
    res = lib.create_domain_environment("MarsRover", "Control system for rover")
    
    assert res["created"] is True
    assert res["domain"] == "MarsRover"
    
    domain_path = test_kb / "domains" / "marsrover"
    assert domain_path.exists()
    assert (domain_path / "documents").exists()
    assert (domain_path / "code").exists()
    assert (domain_path / "domain_config.json").exists()

if __name__ == "__main__":
    pytest.main(['-v', __file__])
