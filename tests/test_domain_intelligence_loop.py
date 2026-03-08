import pytest
import ast
import sys
import os
from pathlib import Path

# Add backend to path so test can run from anywhere
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from verification.constitutional_interpreter import ConstitutionalInterpreter, ConstitutionalViolation
from cognitive.telemetry_evaluator import TelemetryEvaluator, RollbackRequired

def test_interpreter_detects_forbidden_modules():
    interpreter = ConstitutionalInterpreter()
    
    # 1. os.system is forbidden
    bad_code = """
import os
def hack():
    os.system("rm -rf /")
"""
    with pytest.raises(ConstitutionalViolation) as exc:
        interpreter.verify_contract(bad_code, "test_bad")
    assert "os" in str(exc.value)

    # 2. subprocess is forbidden
    bad_code2 = """
from subprocess import Popen
def run_command():
    Popen(["ls", "-la"])
"""
    with pytest.raises(ConstitutionalViolation) as exc:
        interpreter.verify_contract(bad_code2, "test_bad2")
    assert "subprocess" in str(exc.value)

def test_interpreter_detects_bad_operations():
    interpreter = ConstitutionalInterpreter()
    
    # Bare except
    bad_code = """
def do_thing():
    try:
        x = 1 / 0
    except:
        pass
"""
    with pytest.raises(ConstitutionalViolation) as exc:
        interpreter.verify_contract(bad_code, "test_bad")
    assert "Bare 'except:'" in str(exc.value)

    # Infinite loop
    bad_code2 = """
def spin():
    while True:
        pass
"""
    with pytest.raises(ConstitutionalViolation) as exc:
        interpreter.verify_contract(bad_code2, "test_bad2")
    assert "while True" in str(exc.value)

def test_interpreter_allows_safe_code():
    interpreter = ConstitutionalInterpreter()
    safe_code = """
def safe_math(a: int, b: int) -> int:
    try:
        return a + b
    except ValueError:
        return 0
"""
    assert interpreter.verify_contract(safe_code, "test_safe") is True


def test_telemetry_evaluator_triggers_rollback():
    evaluator = TelemetryEvaluator(observation_window_sec=0) # Instant for testing
    
    baseline = {"error_rate": 0.01, "avg_latency_ms": 45.0}
    
    # Mock current metrics to be completely degraded
    def bad_metrics():
        return {"error_rate": 0.50, "avg_latency_ms": 200.0}
        
    evaluator._gather_current_metrics = bad_metrics
    
    with pytest.raises(RollbackRequired) as exc:
        evaluator.evaluate_swap_impact("test_module", baseline)
    assert "Metrics degraded" in str(exc.value)

def test_telemetry_evaluator_approves_improvement():
    evaluator = TelemetryEvaluator(observation_window_sec=0)
    
    baseline = {"error_rate": 0.05, "avg_latency_ms": 100.0}
    
    # Mock current metrics to show improvement
    def good_metrics():
        return {"error_rate": 0.01, "avg_latency_ms": 40.0}
        
    evaluator._gather_current_metrics = good_metrics
    
    score = evaluator.evaluate_swap_impact("test_module", baseline)
    assert score > 0.0 # Score should reflect positive optimization
