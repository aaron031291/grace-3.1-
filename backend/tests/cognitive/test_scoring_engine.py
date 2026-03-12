import pytest
from backend.cognitive.scoring_engine import get_trust_aggregator, TrustScoreAggregator

def test_trust_aggregator_initialization():
    aggregator = get_trust_aggregator(threshold=8.0)
    assert aggregator.failure_threshold == 8.0
    assert "L7_SMT" in aggregator.layers
    
def test_normalize_score():
    aggregator = TrustScoreAggregator()
    assert aggregator.normalize_score(0.5, 1.0) == 5.0
    assert aggregator.normalize_score(0.9, 1.0) == 9.0
    assert aggregator.normalize_score(1.0, 1.0) == 10.0
    assert aggregator.normalize_score(0.0, 1.0) == 0.0

def test_evaluate_pipeline_success():
    aggregator = get_trust_aggregator(threshold=7.5)
    
    layer_scores = {
        "L1_Ingestion": 9.5,
        "L3_LLM": 8.0,
        "L7_SMT": 10.0
    }
    
    result = aggregator.evaluate_pipeline(layer_scores)
    assert result["passed"] is True
    assert len(result["failed_layers"]) == 0
    assert result["overall_score"] == 9.17  # (9.5 + 8.0 + 10.0) / 3

def test_evaluate_pipeline_failure_smt():
    aggregator = get_trust_aggregator(threshold=7.5)
    
    layer_scores = {
        "L1_Ingestion": 9.0,
        "L3_LLM": 8.0,
        "L7_SMT": 0.0  # Failed threshold
    }
    
    result = aggregator.evaluate_pipeline(layer_scores)
    assert result["passed"] is False
    assert len(result["failed_layers"]) == 1
    assert result["failed_layers"][0]["layer"] == "L7_SMT"
    assert result["failed_layers"][0]["score"] == 0.0

def test_evaluate_pipeline_failure_multiple():
    aggregator = get_trust_aggregator(threshold=7.5)
    
    layer_scores = {
        "L1_Ingestion": 5.0,  # Failed
        "L3_LLM": 6.0,        # Failed
        "L7_SMT": 10.0
    }
    
    result = aggregator.evaluate_pipeline(layer_scores)
    assert result["passed"] is False
    assert len(result["failed_layers"]) == 2
