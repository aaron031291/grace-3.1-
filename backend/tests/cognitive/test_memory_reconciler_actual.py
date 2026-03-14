import pytest
import sys
from unittest.mock import MagicMock
from backend.cognitive.memory_reconciler import MemoryReconciler, get_reconciler

def test_atomic_get():
    # Setup mocks
    mock_fc = MagicMock()
    mock_fc.lookup.return_value = [{"id": 1, "last_accessed": "2030-01-01T00:00:00Z"}]
    
    mock_ghost = MagicMock()
    mock_ghost._cache = [{"content": "hello_world", "ts": "2025-01-01T00:00:00Z"}]
    
    mock_unified = MagicMock()
    mock_unified.search_all.return_value = {"total": 1, "items": [{"created_at": "2020-01-01T00:00:00Z"}]}
    
    # Inject into sys.modules
    sys.modules["cognitive.flash_cache"] = MagicMock()
    sys.modules["cognitive.flash_cache"].get_flash_cache.return_value = mock_fc
    
    sys.modules["cognitive.ghost_memory"] = MagicMock()
    sys.modules["cognitive.ghost_memory"].get_ghost_memory.return_value = mock_ghost
    
    sys.modules["cognitive.unified_memory"] = MagicMock()
    sys.modules["cognitive.unified_memory"].get_unified_memory.return_value = mock_unified
    
    reconciler = MemoryReconciler()
    res = reconciler.atomic_get("hello")
    
    # Should sort by timestamp inverted and return the freshest, which is 2030 (flash_cache)
    assert res is not None
    assert res["source"] == "flash_cache"

def test_atomic_set():
    mock_fc = MagicMock()
    mock_fc.extract_keywords.return_value = ["test"]
    mock_ghost = MagicMock()
    mock_ghost._task_id = "test_task"
    mock_unified = MagicMock()
    
    sys.modules["cognitive.flash_cache"].get_flash_cache.return_value = mock_fc
    sys.modules["cognitive.ghost_memory"].get_ghost_memory.return_value = mock_ghost
    sys.modules["cognitive.unified_memory"].get_unified_memory.return_value = mock_unified
    
    reconciler = MemoryReconciler()
    res = reconciler.atomic_set("key", "value")
    
    assert "flash_cache" in res["stored_in"]
    assert "unified_memory" in res["stored_in"]
    assert "ghost_memory" in res["stored_in"]
    
def test_atomic_evict():
    mock_fc = MagicMock()
    mock_fc.lookup.return_value = [{"id": 1, "source_name": "target_key"}]
    
    sys.modules["cognitive.flash_cache"].get_flash_cache.return_value = mock_fc
    
    reconciler = MemoryReconciler()
    res = reconciler.atomic_evict("target_key")
    
    assert "flash_cache" in res["evicted_from"]
    mock_fc.remove.assert_called_with(1)
    
def test_reconcile():
    mock_fc = MagicMock()
    mock_fc.stats.return_value = {"total_entries": 10}
    
    mock_ghost = MagicMock()
    mock_ghost._cache = [1, 2, 3] # len = 3
    
    mock_unified = MagicMock()
    mock_unified.get_stats.return_value = {"a": {"count": 7}, "b": "ignore"}
    
    sys.modules["cognitive.flash_cache"].get_flash_cache.return_value = mock_fc
    sys.modules["cognitive.ghost_memory"].get_ghost_memory.return_value = mock_ghost
    sys.modules["cognitive.unified_memory"].get_unified_memory.return_value = mock_unified
    
    reconciler = MemoryReconciler()
    stats = reconciler.reconcile()
    
    assert stats["flash_cache"] == 10
    assert stats["ghost_memory"] == 3
    assert stats["unified_memory"] == 7
    assert stats["total"] == 20

def test_get_reconciler_singleton():
    r1 = get_reconciler()
    r2 = get_reconciler()
    assert r1 is r2

if __name__ == "__main__":
    pytest.main(['-v', __file__])
