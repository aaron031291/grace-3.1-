import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.auto_research import AutoResearchEngine, get_auto_research

def test_singleton():
    e1 = get_auto_research()
    e2 = get_auto_research()
    assert e1 is e2

@patch("backend.cognitive.auto_research.Path")
def test_analyse_folder(mock_path):
    # Mock folder
    mock_folder = MagicMock()
    mock_folder.exists.return_value = True
    mock_folder.name = "test_domain"
    
    mock_sub = MagicMock()
    mock_sub.is_dir.return_value = True
    mock_sub.name = "sub"
    
    mock_file = MagicMock()
    mock_file.is_file.return_value = True
    mock_file.name = "f.txt"
    mock_file.suffix = ".txt"
    mock_file.read_text.return_value = "hello"
    
    # Needs child items in iterdir
    mock_folder.iterdir.return_value = [mock_sub, mock_file]
    
    # Path('...') returns this folder
    mock_path.return_value.__truediv__.return_value = mock_folder
    
    engine = AutoResearchEngine()
    engine._reason_about_domain = MagicMock(return_value={"domain": "test", "research_queries": ["q"]})
    
    res = engine.analyse_folder("test_domain")
    
    assert res["folder_name"] == "test_domain"
    assert "sub" in res["subfolders"]
    assert "f.txt" in res["files"]

if __name__ == "__main__":
    pytest.main(['-v', __file__])
