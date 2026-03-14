import pytest
import time
from backend.cognitive.spindle_checkpoint import SpindleCheckpointManager, get_checkpoint_manager

def test_singleton():
    m1 = get_checkpoint_manager()
    m2 = get_checkpoint_manager()
    assert m1 is m2

def test_checkpoint_success():
    mgr = SpindleCheckpointManager()
    
    with mgr.checkpoint("test_db", "hash123") as cp:
        cp.state_snapshot["test_key"] = "test_val"
        
    assert cp.rolled_back is False
    assert mgr.stats["created"] == 1
    assert mgr.stats["committed"] == 1
    assert mgr.stats["rolled_back"] == 0

def test_checkpoint_rollback():
    mgr = SpindleCheckpointManager()
    
    custom_rollback_called = False
    def rollback_handler(cp):
        nonlocal custom_rollback_called
        custom_rollback_called = True
        
    mgr.register_rollback("custom_comp", rollback_handler)
    
    with pytest.raises(ValueError):
        with mgr.checkpoint("custom_comp", "hash456") as cp:
            raise ValueError("test error")
            
    assert cp.rolled_back is True
    assert custom_rollback_called is True
    assert mgr.stats["rolled_back"] == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
