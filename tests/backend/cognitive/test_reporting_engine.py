import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import json
import os

from backend.cognitive.reporting_engine import generate_report, _build_summary, _generate_nlp_report

@pytest.fixture
def mock_db_session():
    import sys
    sys.modules['cognitive.magma.grace_magma_system'] = MagicMock()
    sys.modules['backend.cognitive.magma.grace_magma_system'] = MagicMock()
    
    # Mocking a basic DB session with scalar and fetchall responses
    session = MagicMock()
    
    # Simple side effect to return different scalar values depending on the query
    def scalar_side_effect(*args, **kwargs):
        query_str = str(args[0])
        if "learning_examples" in query_str and "AVG" in query_str:
            return 0.85
        elif "learning_examples" in query_str:
            return 100
        elif "learning_patterns" in query_str:
            return 15
        elif "genesis_key" in query_str and "is_error" in query_str:
            return 2
        elif "genesis_key" in query_str:
            return 500
        elif "documents" in query_str and "SUM" in query_str:
            return 10485760  # 10 MB
        elif "documents" in query_str:
            return 50
        return 0
        
    def execute_side_effect(*args, **kwargs):
        mock_result = MagicMock()
        mock_result.scalar.side_effect = lambda: scalar_side_effect(*args, **kwargs)
        mock_result.fetchall.return_value = [("system", 400), ("user", 100)]
        return mock_result
        
    session.execute.side_effect = execute_side_effect
    return session

@patch('backend.cognitive.reporting_engine.get_report')
@patch('backend.cognitive.reporting_engine._report_integration')
@patch('backend.cognitive.reporting_engine._report_llm_usage')
@patch('backend.cognitive.reporting_engine._report_healing')
@patch('backend.cognitive.reporting_engine._report_trust')
@patch('backend.cognitive.reporting_engine.REPORTS_DIR')
@patch('backend.cognitive.reporting_engine._get_db')
def test_generate_report(mock_get_db, mock_reports_dir, mock_trust, mock_healing, mock_llm, mock_integration, mock_report, mock_db_session):
    # Setup mocks
    mock_get_db.return_value = mock_db_session
    
    # Mock trust engine report
    mock_trust.return_value = {"overall_trust": 85, "component_count": 10, "components": {}, "status": "active"}
    
    # Mock immune system report
    mock_healing.return_value = {"total_healing_actions": 3, "successful": 2, "failed": 1, "success_rate": 0.667, "status": "active"}
    
    # Mock LLM usage report
    mock_llm.return_value = {"total_calls": 1000, "total_errors": 50, "avg_latency_ms": 150, "error_rate": 0.05, "by_provider": {}, "status": "active"}
    
    # Mock integration health report
    mock_integration.return_value = {"total_components": 20, "healthy": 19, "broken": 1, "health_percent": 95, "status": "active"}
    
    # Mock file system path handling
    mock_path = MagicMock()
    mock_reports_dir.__truediv__.return_value = mock_path
    
    # Run the report generation
    report = generate_report(period="daily", days=1)
    
    # Verify report structure
    assert report["period"] == "daily"
    assert report["days_covered"] == 1
    assert "report_id" in report
    
    # Verify section data aggregation (testing our DB mocks and other service mocks)
    assert report["sections"]["trust"]["overall_trust"] == 85
    assert report["sections"]["learning"]["total_examples"] == 100
    assert report["sections"]["learning"]["avg_trust"] == 0.85
    assert report["sections"]["healing"]["success_rate"] == 0.667
    assert report["sections"]["llm_usage"]["total_calls"] == 1000
    assert report["sections"]["genesis_keys"]["total_keys"] == 500
    assert report["sections"]["genesis_keys"]["errors"] == 2
    assert report["sections"]["integration"]["broken"] == 1
    assert report["sections"]["documents"]["total_size_mb"] == 10.0
    
    # Verify summary calculations
    summary = report["summary"]
    assert "Trust score is healthy" in summary["improvements"]
    assert "1 broken integrations" in summary["problems"]
    assert summary["metrics"]["integration_health"] == 95
    assert summary["health_score"] > 50  # Should be positive based on our healthy mocks
    
    # Verify file writes occurred
    assert mock_path.write_text.call_count >= 2  # Once for .txt, once for .json

def test_build_summary_logic():
    # Test specific edge cases in summary building
    sections = {
        "trust": {"overall_trust": 40}, # low trust
        "healing": {"total_healing_actions": 10, "success_rate": 0.5}, # low healing
        "llm_usage": {"error_rate": 0.2}, # high error
        "integration": {"broken": 5, "health_percent": 40}, # broken integration
        "genesis_keys": {"recent_keys": 20, "errors": 10} # high errors
    }
    
    summary = _build_summary(sections)
    
    # We should have accumulated many problems and no improvements essentially
    assert len(summary["problems"]) == 5
    assert "Trust score is low: 40" in summary["problems"]
    assert "LLM error rate: 20.0%" in summary["problems"]
    assert "5 broken integrations" in summary["problems"]
    assert "10 genesis key errors" in summary["problems"]
    
    # Health score math: 
    # base 50 + ((40-50)*0.2) + ((40-50)*0.3) + ((0.5-0.5)*20) - (0.2*30) = 50 - 2 - 3 + 0 - 6 = 39.0
    assert summary["health_score"] == 39.0

def test_generate_nlp_report_format():
    mock_report = {
        "report_id": "test_123",
        "period": "daily",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "health_score": 90,
            "improvements": ["Things are great"],
            "problems": [],
            "metrics": {"total_knowledge": 500}
        },
        "sections": {
            "learning": {"status": "active", "total_examples": 500, "new_examples": 10},
            "llm_usage": {"status": "active", "total_calls": 1000, "avg_latency_ms": 150, "error_rate": 0.01}
        }
    }
    
    nlp_text = _generate_nlp_report(mock_report)
    
    # Check that the natural language string is generated as expected
    assert "# Grace System Report — Daily" in nlp_text
    assert "Overall Health Score: 90/100" in nlp_text
    assert "## What's Improved" in nlp_text
    assert "+ Things are great" in nlp_text
    assert "## Learning & Knowledge" in nlp_text
    assert "Total knowledge base: 500 examples" in nlp_text
    assert "## LLM Usage" in nlp_text
    assert "Total calls: 1000" in nlp_text
