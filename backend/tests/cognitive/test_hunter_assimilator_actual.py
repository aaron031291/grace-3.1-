import pytest
from unittest.mock import patch, MagicMock
from backend.cognitive.hunter_assimilator import HunterAssimilator, get_hunter

def test_singleton():
    h1 = get_hunter()
    h2 = get_hunter()
    assert h1 is h2

def test_is_hunter_request():
    hunter = HunterAssimilator()
    assert hunter.is_hunter_request("please HUNTER this code") is True
    assert hunter.is_hunter_request("please run this code") is False

def test_step_parse():
    hunter = HunterAssimilator()
    
    code = "```filepath: test.py\ndef a(): pass\n```"
    res = hunter._step_parse(code, "test desc")
    
    assert res["step"] == "parse"
    assert "test.py" in res["files"]

@patch("backend.cognitive.hunter_assimilator.HunterAssimilator._step_parse")
@patch("backend.cognitive.hunter_assimilator.HunterAssimilator._step_kimi_analyse")
@patch("backend.cognitive.hunter_assimilator.HunterAssimilator._step_pipeline_verify")
@patch("backend.cognitive.hunter_assimilator.HunterAssimilator._step_code_review")
@patch("backend.cognitive.hunter_assimilator.HunterAssimilator._step_trust_score")
@patch("backend.cognitive.hunter_assimilator.HunterAssimilator._step_healing_precheck")
@patch("backend.cognitive.hunter_assimilator.HunterAssimilator._step_write_files")
@patch("backend.cognitive.hunter_assimilator.HunterAssimilator._step_librarian_organise")
@patch("backend.cognitive.hunter_assimilator.HunterAssimilator._step_handshake")
@patch("backend.cognitive.hunter_assimilator.HunterAssimilator._step_contradiction_check")
@patch("backend.cognitive.hunter_assimilator.HunterAssimilator._step_feed_learning")
@patch("backend.cognitive.hunter_assimilator.HunterAssimilator._step_immune_postcheck")
@patch("backend.cognitive.hunter_assimilator.HunterAssimilator._step_update_kpi")
def test_assimilate(mock_update_kpi, mock_immune, mock_feed, mock_contradiction, mock_handshake, mock_librarian, mock_write, mock_heal, mock_trust, mock_review, mock_pipeline, mock_kimi, mock_parse):
    hunter = HunterAssimilator()
    
    mock_parse.return_value = {"files": ["file1.py"], "schemas": []}
    mock_review.return_value = {"issues": []}
    mock_write.return_value = {"written": []}
    mock_trust.return_value = {"trust": 85}
    
    res = hunter.assimilate("print('test')", "test code")
    
    assert res.status == "complete"
    assert res.trust_score == 85
    assert len(res.files_created) == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
