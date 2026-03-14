import pytest
from unittest.mock import patch, MagicMock
from backend.cognitive.autonomous_diagnostics import AutonomousDiagnostics
from backend.cognitive.autonomous_healing_loop import heal_content

@patch('backend.cognitive.autonomous_diagnostics.publish')
@patch('backend.cognitive.test_framework.smoke_test')
def test_diagnostics_startup(mock_smoke_test, mock_publish):
    mock_smoke_test.return_value = {"passed": 2, "failed": 0, "status": "green", "checks": []}
    
    diag = AutonomousDiagnostics()
    with patch('backend.cognitive.autonomous_diagnostics.AutonomousDiagnostics._check_early_warnings', return_value=[]):
        result = diag.on_startup()
    
    assert mock_publish.call_count >= 1
    topics = [c.args[0] for c in mock_publish.mock_calls]
    assert "diagnostics.startup_completed" in topics

@patch('backend.cognitive.autonomous_healing_loop.publish')
@patch('pathlib.Path.write_text')
@patch('pathlib.Path.exists')
@patch('backend.cognitive.circuit_breaker.enter_loop')
@patch('backend.cognitive.circuit_breaker.exit_loop')
@patch('backend.cognitive.autonomous_healing_loop._score_content')
def test_healing_loop_flow(mock_score, mock_exit, mock_enter, mock_exists, mock_write, mock_publish):
    mock_enter.return_value = True
    mock_exists.return_value = True
    mock_score.side_effect = [5.0, 8.0]
    
    source_content = "def test():\n    pass\n"
    
    with patch('backend.cognitive.autonomous_healing_loop._surgical_heal', return_value="def healed():\n    pass\n"):
        result = heal_content("test.py", source_content, ["syntax error"])
        
        assert result["success"] == True
        topics = [c.args[0] for c in mock_publish.mock_calls]
        assert "healing.autonomous_started" in topics
        assert "healing.autonomous_completed" in topics

if __name__ == '__main__':
    pytest.main(['-v', __file__])
