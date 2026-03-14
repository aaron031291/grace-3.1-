import pytest
from backend.cognitive.examples import (
    ingest_single_file,
    rag_query_with_cognitive,
    migrate_database,
    batch_process_documents,
    select_embedding_strategy,
    resolve_user_query_ambiguity
)

def test_ingest_single_file():
    res = ingest_single_file("test.txt")
    assert res["status"] == "success"
    assert res["filepath"] == "test.txt"

def test_rag_query_with_cognitive():
    res = rag_query_with_cognitive("Test query?", 123)
    assert "response" in res
    assert "confidence" in res
    assert "strategy_used" in res

def test_migrate_database(monkeypatch):
    from backend.cognitive.engine import CognitiveEngine
    class MockResult:
        is_valid = True
    
    mock_engine = CognitiveEngine
    original_validate = mock_engine.act

    # We can just monkeypatch enable_strict_mode to False inside __init__
    original_init = CognitiveEngine.__init__
    def mock_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.enable_strict_mode = False
    
    monkeypatch.setattr(CognitiveEngine, "__init__", mock_init)

    res1 = migrate_database("mig1", dry_run=True)
    assert res1["status"] == "dry_run"
    assert res1["would_execute"] is True
    
    # Normally we do not run the actual migration if it's mocked, but in example it just returns dict
    res2 = migrate_database("mig2", dry_run=False)
    assert res2["status"] == "success"
    assert "tables_affected" in res2

def test_batch_process_documents(monkeypatch):
    from backend.cognitive.engine import CognitiveEngine
    
    original_init = CognitiveEngine.__init__
    def mock_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.enable_strict_mode = False
    
    monkeypatch.setattr(CognitiveEngine, "__init__", mock_init)

    res = batch_process_documents("/tmp/test", max_depth=0)
    assert isinstance(res, dict)
    assert "warning" in res
    assert "Recursion depth limit" in res["warning"]

def test_select_embedding_strategy():
    res = select_embedding_strategy("pdf", 1024)
    assert "strategy" in res
    assert "model" in res
    assert "dimensions" in res

def test_resolve_user_query_ambiguity():
    res1 = resolve_user_query_ambiguity("it broke")
    assert res1["status"] == "needs_clarification"
    assert "unknowns" in res1
    
    res2 = resolve_user_query_ambiguity("the server broke")
    assert res2["status"] == "clear"
    assert res2["can_proceed"] is True

if __name__ == "__main__":
    pytest.main(['-v', __file__])
