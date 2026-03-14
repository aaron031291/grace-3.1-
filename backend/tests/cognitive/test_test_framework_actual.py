import pytest
from backend.cognitive.test_framework import _build_smoke_summary

def test_build_smoke_summary():
    # All passed
    results_pass = {
        "passed": 5,
        "failed": 0,
        "checks": [{"name": "A", "passed": True}]
    }
    summ_pass = _build_smoke_summary(results_pass)
    assert "All 5 checks passed" in summ_pass
    
    # 1 failed
    results_fail = {
        "passed": 4,
        "failed": 1,
        "checks": [{"name": "A", "passed": True}, {"name": "B", "passed": False}]
    }
    summ_fail = _build_smoke_summary(results_fail)
    assert "4/5 checks passed" in summ_fail
    assert "B" in summ_fail

if __name__ == "__main__":
    pytest.main(['-v', __file__])
