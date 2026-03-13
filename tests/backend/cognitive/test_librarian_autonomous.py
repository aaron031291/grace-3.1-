import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.cognitive.librarian_autonomous import AutonomousLibrarian

@pytest.fixture
def temp_kb(tmp_path):
    with patch('backend.cognitive.librarian_autonomous._get_kb', return_value=tmp_path):
        yield tmp_path

@pytest.fixture
def mock_modules():
    mocks = {
        'api._genesis_tracker': MagicMock(),
        'genesis.realtime': MagicMock(),
        'cognitive.magma_bridge': MagicMock(),
        'cognitive.auto_research': MagicMock(),
        'cognitive.flash_cache': MagicMock(),
        'cognitive.consensus_engine': MagicMock(),
        'cognitive.reverse_knn': MagicMock(),
        'cognitive.event_bus': MagicMock(),
        'llm_orchestrator.factory': MagicMock(),
        'llm_orchestrator.ollama_resolver': MagicMock(),
        'api.docs_library_api': MagicMock(),
        'ingestion.service': MagicMock()
    }
    with patch.dict('sys.modules', mocks):
        yield mocks

@pytest.fixture
def librarian(temp_kb, mock_modules):
    return AutonomousLibrarian()

def test_suggest_location(librarian):
    # Name-based matches
    assert librarian.suggest_location(Path("README.md")) == "documentation"
    assert librarian.suggest_location(Path("test_app.py")) == "tests"
    assert librarian.suggest_location(Path("config.json")) == "configuration"
    assert librarian.suggest_location(Path("security_policy.pdf")) == "governance/policies"
    
    # Extension-based matches
    assert librarian.suggest_location(Path("app.js")) == "code/javascript"
    assert librarian.suggest_location(Path("style.css")) == "code/web"  # first match in taxonomy
    assert librarian.suggest_location(Path("data.csv")) == "data/csv"

def test_organise_file(librarian, temp_kb):
    test_file = temp_kb / "test_file.py"
    test_file.write_text("def test_ok(): pass")
    
    result = librarian.organise_file(str(test_file.relative_to(temp_kb)))
    
    # Should be suggested as tests because of name starts with test
    assert result["action"] == "organised"
    assert result["directory"] == "tests"
    
    # Check it moved
    assert not test_file.exists()
    assert (temp_kb / "tests" / "test_file.py").exists()

def test_ensure_taxonomy(librarian, temp_kb):
    result = librarian.ensure_taxonomy()
    
    assert result["created"] > 0
    
    # Check some essential ones
    assert (temp_kb / "code" / "python").exists()
    assert (temp_kb / "documentation" / "guides").exists()
    assert (temp_kb / "governance" / "rules").exists()

def test_create_domain_environment(librarian, temp_kb):
    result = librarian.create_domain_environment("AI Ethics", "Rules for AI")
    
    assert result["created"] is True
    assert result["domain"] == "AI Ethics"
    
    domain_dir = temp_kb / "domains" / "ai_ethics"
    assert domain_dir.exists()
    
    # Check subdirs
    assert (domain_dir / "documents").exists()
    assert (domain_dir / "governance").exists()
    
    # Check config
    config_file = domain_dir / "domain_config.json"
    assert config_file.exists()
    config = json.loads(config_file.read_text())
    assert config["domain"] == "AI Ethics"

def test_smart_ingest_document(librarian, temp_kb, mock_modules):
    # Create a source file > 100 characters so LLM naming is triggered
    doc_path = temp_kb / "upload_123.md"
    long_content = "This document contains information about Python dictionaries. " * 5
    doc_path.write_text(long_content)
    
    # Mock LLM to return a nice filename and description
    llm_client = MagicMock()
    llm_client.generate.return_value = "python_dicts|Python dicts overview"
    mock_modules['llm_orchestrator.factory'].get_llm_client.return_value = llm_client
    
    # Mock flash cache giving concepts
    flash_cache = MagicMock()
    flash_cache.extract_keywords.return_value = ["python", "dictionary"]
    mock_modules['cognitive.flash_cache'].get_flash_cache.return_value = flash_cache
    
    result = librarian.smart_ingest_document(str(doc_path))
    
    assert result["processed"] is True
    assert "python_dicts" in result["new_name"]
    assert "documentation" in result["suggested_category"]  # Ext fallback .md -> documentation
    
    # File was moved
    assert not doc_path.exists()
    target_path = temp_kb / result["suggested_category"] / result["new_name"]
    assert target_path.exists()
    assert target_path.read_text() == long_content
