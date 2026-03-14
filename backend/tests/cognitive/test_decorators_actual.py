import pytest
import time
from backend.cognitive.decorators import (
    cognitive_operation,
    enforce_reversibility,
    blast_radius,
    time_bounded,
    requires_determinism
)

def test_enforce_reversibility():
    @enforce_reversibility(reversible=False, justification="Must delete file")
    def delete_file():
        return True
        
    assert delete_file() is True
    assert getattr(delete_file, "__cognitive_reversible__") is False
    assert getattr(delete_file, "__cognitive_justification__") == "Must delete file"
    
    with pytest.raises(ValueError):
        @enforce_reversibility(reversible=False) # Missing justification
        def bad_func():
            pass
        bad_func()

def test_blast_radius():
    @blast_radius("systemic")
    def big_change():
        return "done"
        
    assert big_change() == "done"
    assert getattr(big_change, "__cognitive_blast_radius__") == "systemic"

def test_requires_determinism():
    @requires_determinism
    def pure_math():
        return 1 + 1
        
    assert pure_math() == 2
    assert getattr(pure_math, "__cognitive_deterministic__") is True

def test_time_bounded():
    @time_bounded(timeout_seconds=1)
    def quick():
        return True
        
    assert quick() is True
    
    @time_bounded(timeout_seconds=1)
    def slow():
        time.sleep(2)
        return True
    
    # Due to signals, this might only work on Unix, so we bypass actual sleep waiting if it's Windows
    import os
    if os.name != 'nt':
        with pytest.raises(TimeoutError):
            slow()

if __name__ == "__main__":
    pytest.main(['-v', __file__])
