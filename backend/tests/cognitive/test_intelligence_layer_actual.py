import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from backend.cognitive.intelligence_layer import (
    UnifiedIntelligenceLayer, PatternRecognitionEngine,
    DeepRepresentationEngine, NeuroSymbolicEngine, get_intelligence_layer
)

def test_singleton():
    il1 = get_intelligence_layer()
    il2 = get_intelligence_layer()
    assert il1 is il2

@patch("backend.cognitive.intelligence_layer.PatternRecognitionEngine._save_patterns")
@patch("backend.cognitive.intelligence_layer.DeepRepresentationEngine._save_features")
@patch("backend.cognitive.intelligence_layer.NeuroSymbolicEngine._save_rules")
def test_intelligence_layer_integration(mock_save_rules, mock_save_features, mock_save_patterns):
    il = UnifiedIntelligenceLayer()
    
    # Observe some loops to train the ML and DL engines
    for i in range(15):  # Need at least 10 observations to promote a rule
        il.observe_loop("test_loop", {"metric1": 10.0 + i}, "success")
        
    # ML Pattern detection
    patterns = il.ml.detect_patterns("test_loop")
    assert len(patterns) > 0
    assert patterns[0]["success_rate"] == 1.0
    
    # Prediction should use KNN logic for ML
    pred = il.predict("test_loop", {"metric1": 25.0})
    assert "ml_prediction" in pred
    assert pred["ml_prediction"]["prediction"] == "success"
    
    # Check if neuro-symbolic rule was promoted
    stats = il.ns.get_stats()
    assert stats["learned_rules"] > 0
    
    # DL features should be tracked
    assert "loop_test_loop" in il.dl._feature_store

def test_neuro_symbolic_engine_evaluate():
    ns = NeuroSymbolicEngine()
    ns._rules = []
    ns._learned_rules = []
    
    ns.add_rule("rule1", "status=error AND retry=true", "do_retry")
    ns.add_rule("rule2", "status=ok", "do_nothing", confidence=0.8)
    
    ctx1 = {"status": "error", "retry": "true"}
    res1 = ns.evaluate(ctx1)
    
    assert len(res1) == 1
    assert res1[0]["action"] == "do_retry"
    
    ctx2 = {"status": "ok"}
    res2 = ns.evaluate(ctx2)
    assert len(res2) == 1
    assert res2[0]["action"] == "do_nothing"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
