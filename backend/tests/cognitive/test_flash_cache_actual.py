import pytest
import os
import json
from unittest.mock import MagicMock
from backend.cognitive.flash_cache import FlashCache, FlashCacheEntry

@pytest.fixture
def temp_cache(tmp_path):
    db_path = str(tmp_path / "test_flash.db")
    cache = FlashCache(db_path=db_path)
    yield cache
    if os.path.exists(db_path):
        os.remove(db_path)

def test_flash_cache_register_and_lookup(temp_cache):
    uri = "https://example.com/doc"
    entry_id = temp_cache.register(
        source_uri=uri,
        source_name="Example Doc",
        keywords=["test", "documentation", "example"],
        trust_score=0.9
    )
    
    assert entry_id is not None
    
    # Test Lookup
    results = temp_cache.lookup(keyword="documentation")
    assert len(results) == 1
    assert results[0]["id"] == entry_id
    assert results[0]["source_uri"] == uri
    
    # Another keyword
    results_many = temp_cache.lookup(keywords=["example", "fake"])
    assert len(results_many) == 1
    
def test_flash_cache_search(temp_cache):
    temp_cache.register(
        source_uri="http://test.com/1",
        summary="A machine learning overview",
        keywords=["ml", "ai"]
    )
    temp_cache.register(
        source_uri="http://test.com/2",
        summary="Data science details",
        keywords=["data", "science"]
    )
    
    res = temp_cache.search("machine learning")
    assert len(res) == 1
    assert "ml" in res[0]["keywords"]

def test_flash_cache_stream_content(temp_cache, monkeypatch):
    entry_id = temp_cache.register(
        source_uri="http://mock.com/api/data",
        headers={"Authorization": "Bearer token"}
    )
    
    import requests
    class MockResponse:
        def __init__(self):
            self.headers = {"Content-Type": "application/json"}
        def raise_for_status(self):
            pass
        def iter_content(self, chunk_size):
            yield b'{"key":"value"}'
            
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: MockResponse())
    
    res = temp_cache.stream_content(entry_id)
    assert res["entry_id"] == entry_id
    assert "data" in res
    assert res["data"] == {"key": "value"}

def test_flash_cache_validate(temp_cache, monkeypatch):
    entry_id = temp_cache.register(source_uri="http://mock.com/valid")
    
    import requests
    class MockHeadResp:
        def __init__(self):
            self.status_code = 200
            self.headers = {"Content-Type": "text/html", "Content-Length": "100"}
            
    monkeypatch.setattr(requests, "head", lambda *args, **kwargs: MockHeadResp())
    
    val = temp_cache.validate(entry_id)
    assert val["valid"] is True
    assert val["status_code"] == 200

def test_flash_cache_predict_keywords(temp_cache):
    temp_cache.register(source_uri="http://mock1", keywords=["python", "programming", "code"])
    temp_cache.register(source_uri="http://mock2", keywords=["python", "asyncio", "testing"])
    
    preds = temp_cache.predict_keywords("python", depth=1)
    
    kws = [p["keyword"] for p in preds]
    assert "programming" in kws
    assert "asyncio" in kws
    assert "python" not in kws

if __name__ == "__main__":
    pytest.main(['-v', __file__])
