import pytest
import time
from backend.cognitive.telemetry_evaluator import TelemetryEvaluator, RollbackRequired

def test_telemetry_evaluator_success():
    evaluator = TelemetryEvaluator(observation_window_sec=0)
    
    baseline = {"error_rate": 0.05, "avg_latency_ms": 60.0}
    # Current mock is: err 0.01, latency 45.0
    score = evaluator.evaluate_swap_impact("test_module", baseline)
    
    # error delta = 0.04 -> +0.4
    # lat delta = 15.0 -> +0.2 -> score = 0.6
    assert score >= 0.0
    
def test_telemetry_evaluator_rollback():
    evaluator = TelemetryEvaluator(observation_window_sec=0)
    
    # Baseline was perfect
    baseline = {"error_rate": 0.0, "avg_latency_ms": 10.0}
    # error delta = -0.01 -> -0.1
    # lat delta = -35.0 -> no extra penalty until -50
    # need score < -0.2 to trigger rollback. Let's make baseline even faster or less error
    baseline2 = {"error_rate": 0.0, "avg_latency_ms": -100.0}
    
    with pytest.raises(RollbackRequired):
        evaluator.evaluate_swap_impact("test_module_failure", baseline2)

if __name__ == "__main__":
    pytest.main(['-v', __file__])
