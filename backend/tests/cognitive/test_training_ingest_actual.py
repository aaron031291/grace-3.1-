import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.training_ingest import _split_sections, ingest_training_corpus

def test_split_sections():
    content = "\n## TITLE 1\nBODY 1\n## TITLE 2\nBODY 2"
    sec = _split_sections(content)
    assert len(sec) == 2
    assert sec[0] == ("TITLE 1", "BODY 1")
    assert sec[1] == ("TITLE 2", "BODY 2")

@patch("backend.cognitive.training_ingest.CORPUS_DIR")
def test_ingest_no_corpus(mock_dir):
    mock_dir.exists.return_value = False
    
    res = ingest_training_corpus()
    assert res["status"] == "no_corpus"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
