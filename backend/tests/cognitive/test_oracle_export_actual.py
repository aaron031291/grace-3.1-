import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.oracle_export import get_oracle_export_path, export_learning_memory_to_oracle

def test_get_oracle_export_path():
    from pathlib import Path
    p = get_oracle_export_path(Path("my_kb"))
    assert p.as_posix() == "my_kb/layer_1/oracle"

@patch("database.session.session_scope")
@patch("backend.cognitive.oracle_export.get_oracle_export_path")
def test_export_learning_memory(mock_get_path, mock_session_scope):
    mock_dir = MagicMock()
    mock_get_path.return_value = mock_dir
    
    mock_session = MagicMock()
    mock_session_scope.return_value.__enter__.return_value = mock_session
    
    mock_row = MagicMock()
    mock_row.id = "123"
    mock_row.trust_score = 0.9
    mock_row.input_context = "{}"
    mock_row.expected_output = "{}"
    mock_row.source = "test"
    mock_row.example_type = "general"
    from datetime import datetime
    mock_row.updated_at = datetime.now()
    
    mock_session.query().filter().order_by().limit().all.return_value = [mock_row]
    
    res = export_learning_memory_to_oracle(limit=1, min_trust=0.5, kb_path=None)
    
    assert res["exported"] >= 0
    assert "paths" in res

if __name__ == "__main__":
    pytest.main(['-v', __file__])
