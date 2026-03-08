import pytest
import os
import sys

# Add backend to path so test can run from anywhere
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from cognitive.telemetry_evaluator import TelemetryEvaluator, RollbackRequired
from verification.context_shadower import shadower
from ml_intelligence.kpi_tracker import get_kpi_tracker, reset_kpi_tracker

@pytest.fixture(autouse=True)
def run_before_and_after_tests():
    """Fixture to execute asserts before and after a test is run"""
    reset_kpi_tracker()
    yield

def test_telemetry_reports_success_to_kpis():
    evaluator = TelemetryEvaluator(observation_window_sec=0)
    baseline = {"error_rate": 0.05, "avg_latency_ms": 100.0}
    
    # Mock current metrics to show improvement
    def good_metrics():
        return {"error_rate": 0.01, "avg_latency_ms": 40.0}
        
    evaluator._gather_current_metrics = good_metrics
    score = evaluator.evaluate_swap_impact("test_module", baseline)
    
    # Verify the score > 0
    assert score > 0.0 
    
    # Verify it posted to the KPI tracker
    tracker = get_kpi_tracker()
    kpi = tracker.get_component_kpis("context_evolution")
    assert kpi is not None
    assert kpi.get_kpi("successes").count == 1
    assert kpi.get_kpi("requests").count == 1
    assert kpi.get_trust_score() > 0.05 # Normalization (1/11 = 0.09) so this passes

def test_telemetry_reports_failure_to_kpis():
    evaluator = TelemetryEvaluator(observation_window_sec=0)
    baseline = {"error_rate": 0.01, "avg_latency_ms": 45.0}
    
    # Mock current metrics to show massive degradation
    def bad_metrics():
        return {"error_rate": 0.50, "avg_latency_ms": 200.0}
        
    evaluator._gather_current_metrics = bad_metrics
    
    with pytest.raises(RollbackRequired):
        evaluator.evaluate_swap_impact("test_module", baseline)
        
    # Verify it posted the failure to the KPI tracker
    tracker = get_kpi_tracker()
    kpi = tracker.get_component_kpis("context_evolution")
    assert kpi is not None
    assert kpi.get_kpi("failures").count == 1
    assert kpi.get_kpi("requests").count == 1
    assert kpi.get_trust_score() < 0.5 # Failure drops it below the 0.5 neutral

def test_shadower_identifies_high_risk_files():
    assert shadower._is_high_risk("C:/grace/backend/memory_tables/schema.json") is True
    assert shadower._is_high_risk("C:/grace/backend/governance/inline_approval_engine.py") is True
    assert shadower._is_high_risk("C:/grace/backend/api/validation_api.py") is True
    assert shadower._is_high_risk("C:/grace/backend/settings.py") is True
    
    assert shadower._is_high_risk("C:/grace/backend/utils/string_formatter.py") is False
    assert shadower._is_high_risk("C:/grace/backend/some_random_file.py") is False
