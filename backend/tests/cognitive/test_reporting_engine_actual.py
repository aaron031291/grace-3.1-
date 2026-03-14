import pytest
from unittest.mock import patch, MagicMock
from backend.cognitive.reporting_engine import _build_summary, _calculate_health_score

def test_build_summary():
    sections = {
        "trust": {"overall_trust": 85},
        "healing": {"success_rate": 0.9, "total_healing_actions": 10},
        "llm_usage": {"error_rate": 0.05, "total_calls": 100},
        "integration": {"health_percent": 95, "broken": 0},
        "genesis_keys": {"errors": 2, "recent_keys": 50}
    }
    summary = _build_summary(sections)
    
    assert len(summary["improvements"]) > 0
    assert len(summary["problems"]) == 0
    assert summary["metrics"]["trust_score"] == 85
    assert summary["health_score"] > 50

def test_calculate_health_score():
    sections = {
        "trust": {"overall_trust": 90},
        "integration": {"health_percent": 100},
        "healing": {"success_rate": 1.0, "total_healing_actions": 5},
        "llm_usage": {"error_rate": 0.0}
    }
    score = _calculate_health_score(sections)
    assert score > 80

if __name__ == "__main__":
    pytest.main(['-v', __file__])
