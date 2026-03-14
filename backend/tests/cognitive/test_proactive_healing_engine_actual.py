import pytest
import sys
from unittest.mock import MagicMock, patch
from backend.cognitive.proactive_healing_engine import ProactiveHealingEngine, ProactiveCategory, SeverityLevel

def test_engine_initialization():
    engine = ProactiveHealingEngine(check_interval_seconds=10)
    assert not engine.is_running
    assert len(engine._capabilities) == 30

def test_analyze_trends():
    engine = ProactiveHealingEngine()
    
    # 1. Test memory spike
    for _ in range(5):
        engine._memory_samples.append(80) # older
    for _ in range(5):
        engine._memory_samples.append(90) # recent
        
    predictions = engine._analyze_trends({})
    mem_pred = [p for p in predictions if p["category"] == ProactiveCategory.MEMORY_TREND]
    assert len(mem_pred) > 0
    assert mem_pred[0]["severity"] == SeverityLevel.CRITICAL
    
    # 2. Test error spike
    # keep memory samples to avoid early return in trend checking
    for _ in range(5):
        engine._error_counts.append(0)
    for _ in range(4):
        engine._error_counts.append(5)
    engine._error_counts.append(10)
    
    predictions = engine._analyze_trends({})
    err_pred = [p for p in predictions if p["category"] == ProactiveCategory.ERROR_PATTERN]
    assert len(err_pred) > 0
    assert err_pred[0]["severity"] == SeverityLevel.CRITICAL

def test_handle_prediction():
    engine = ProactiveHealingEngine(enable_auto_heal=True)
    engine._handle_issue = MagicMock()
    
    pred = {
        "category": ProactiveCategory.ERROR_PATTERN,
        "severity": SeverityLevel.CRITICAL,
        "recommended_action": "forensic_root_cause"
    }
    
    engine._handle_prediction(pred, {})
    engine._handle_issue.assert_called_once()
    assert pred["proactive"] is True
    assert pred["heal_action"] == "forensic_root_cause"

def test_handle_issue_circuit_breaker():
    engine = ProactiveHealingEngine(enable_auto_heal=True)
    sys.modules["cognitive.circuit_breaker"] = MagicMock()
    sys.modules["cognitive.circuit_breaker"].enter_loop.return_value = False
    
    issue = {
        "healable": True,
        "heal_action": "connection_pool_reset",
        "severity": SeverityLevel.WARNING
    }
    
    res = engine._handle_issue(issue, {})
    assert res["outcome"] == "deferred"
    assert "Circuit breaker tripped" in res["reason"]

if __name__ == "__main__":
    pytest.main(['-v', __file__])
