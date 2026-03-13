import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.cognitive.auto_research import AutoResearchEngine

@pytest.fixture
def temp_kb(tmp_path):
    with patch('backend.cognitive.auto_research._get_kb', return_value=tmp_path):
        yield tmp_path

@pytest.fixture
def mock_kimi():
    kimi_mock = MagicMock()
    # Provide canned JSON responses or predictions depending on prompt
    def call_side_effect(prompt, *args, **kwargs):
        if "reason about what this domain" in prompt or "Based on the folder name" in prompt:
            return '```json\n{"domain": "Testing", "topics": ["Mocks"], "research_queries": ["Pytest Mocking"], "suggested_subfolders": ["fixtures"]}\n```'
        elif "Research this topic" in prompt:
            return "This is a detailed research response about Pytest Mocking."
        elif "Predict the next" in prompt:
            return "1. Advanced Fixtures\n2. MagicMock specs\n3. Side effects"
        return ""
        
    kimi_mock._call.side_effect = call_side_effect
    
    # Patching inside the module due to local imports
    with patch.dict('sys.modules', {
        'llm_orchestrator.kimi_enhanced': MagicMock(get_kimi_enhanced=MagicMock(return_value=kimi_mock))
    }):
        yield kimi_mock

@pytest.fixture
def research_engine(temp_kb, mock_kimi):
    # Mock all the other lazy-imported modules
    with patch.dict('sys.modules', {
        'api._genesis_tracker': MagicMock(),
        'cognitive.magma_bridge': MagicMock(),
        'retrieval.retriever': MagicMock(),
        'embedding.embedder': MagicMock(),
        'vector_db.client': MagicMock()
    }):
        yield AutoResearchEngine()

def test_analyse_folder(research_engine, temp_kb):
    test_folder = temp_kb / "python_testing"
    test_folder.mkdir()
    (test_folder / "sub1").mkdir()
    (test_folder / "test_file.py").write_text("def test_foo(): pass")
    
    analysis = research_engine.analyse_folder("python_testing")
    
    assert analysis["folder_name"] == "python_testing"
    assert "sub1" in analysis["subfolders"]
    assert "test_file.py" in analysis["files"]
    assert "def test_foo()" in analysis["content_preview"]
    assert analysis["topics"]["domain"] == "Testing"
    assert analysis["suggested_research"] == ["Pytest Mocking"]

def test_run_research_cycle(research_engine, temp_kb):
    result = research_engine.run_research_cycle("python_testing", max_queries=1)
    
    assert result["folder"] == "python_testing"
    assert result["version"] == "v1"
    assert result["queries"] == ["Pytest Mocking"]
    assert result["files_created"] == 1
    
    # Check that predictions were parsed
    assert "Advanced Fixtures" in result["predicted_next"]
    assert "MagicMock specs" in result["predicted_next"]
    assert "Side effects" in result["predicted_next"]
    
    # Check that research output was written
    research_dir = temp_kb / "python_testing" / "research_v1"
    assert research_dir.exists()
    
    files = list(research_dir.iterdir())
    assert len(files) == 1
    content = files[0].read_text()
    assert "This is a detailed research response about Pytest Mocking." in content
    
    # Check that subfolder was created
    assert (temp_kb / "python_testing" / "fixtures").exists()
    assert "fixtures" in result["subfolders_created"]

def test_predict_next_topics(research_engine, mock_kimi):
    # Isolated test for parsing Kimi logic in prediction
    results = {"results": [{"query": "Mocks"}]}
    analysis = {"topics": {"domain": "Testing"}}
    
    predictions = research_engine._predict_next_topics(analysis, results)
    
    assert predictions == ["Advanced Fixtures", "MagicMock specs", "Side effects"]
