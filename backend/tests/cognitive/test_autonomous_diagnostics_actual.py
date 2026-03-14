import pytest
from backend.cognitive.autonomous_diagnostics import AutonomousDiagnostics

def test_diagnostics_singleton():
    d1 = AutonomousDiagnostics.get_instance()
    d2 = AutonomousDiagnostics.get_instance()
    assert d1 is d2

def test_diagnostics_on_startup(monkeypatch):
    diag = AutonomousDiagnostics()
    
    # Mock smoke_test
    def mock_smoke_test():
        return {
            "checks": [
                {"name": "test_pass", "passed": True, "detail": "ok"},
                {"name": "test_fail", "passed": False, "detail": "failed dummy check"}
            ],
            "passed": 1,
            "failed": 1,
            "status": "partial"
        }
    import cognitive.test_framework as tf
    monkeypatch.setattr(tf, "smoke_test", mock_smoke_test)
    
    # Mock predictives
    monkeypatch.setattr(diag, "_check_early_warnings", lambda: [])
    # Mock auto fix
    monkeypatch.setattr(diag, "_attempt_fix", lambda n, d: {"fixed": True, "action": "Restarted"})
    # Mock save
    monkeypatch.setattr(diag, "_save_diagnostic", lambda r: None)
    
    res = diag.on_startup()
    assert res["event"] == "startup"
    assert res["healthy"] == 1
    assert res["total"] == 2
    assert len(res["checks"]) == 1 # only logs failures to "checks" list in startup logic
    assert res["checks"][0]["system"] == "test_fail"
    assert res["checks"][0]["auto_fixed"] is True
    assert res["checks"][0]["action"] == "Restarted"

def test_diagnostics_on_error(monkeypatch):
    diag = AutonomousDiagnostics()
    
    # Mock try_fix
    monkeypatch.setattr(diag, "_attempt_fix", lambda c, m: {"fixed": False, "action": "Logged"})
    monkeypatch.setattr(diag, "_log_failure", lambda t, m, f, c: None)
    monkeypatch.setattr(diag, "consensus_diagnose", lambda t, m: {"consensus_diagnosis": "It's broken"})
    
    # Add fake history to trigger consensus
    diag._failure_history = [{"error_type": "MemoryError"}] * 3
    
    res = diag.on_error("MemoryError", "Out of memory", "UnifiedMemory")
    
    assert res["event"] == "error"
    assert res["error_type"] == "MemoryError"
    assert res["recurring"] is True
    assert res["occurrence_count"] >= 3
    assert "consensus_diagnosis" in res
    assert "plain_english" in res
    assert "Grace asked Kimi" in res["plain_english"]

if __name__ == "__main__":
    pytest.main(['-v', __file__])
