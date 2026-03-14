import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from backend.genesis.adaptive_cicd import (
    AdaptiveCICD,
    PipelineTrustLevel,
    AdaptiveTriggerReason,
    GovernanceAction
)

def test_trust_score_calculation():
    adaptive = AdaptiveCICD()
    pipeline_id = "test-pipeline"
    
    # Untrusted initially
    score = adaptive.calculate_trust_score(pipeline_id)
    assert score.trust_level == PipelineTrustLevel.UNTRUSTED
    assert score.score == 0.0
    
    # Record some successful results (needs >20 for VERIFIED, let's do 22)
    for _ in range(22):
        adaptive.record_run_result(pipeline_id, "success", 10.0)
        
    score = adaptive.calculate_trust_score(pipeline_id)
    assert score.trust_level == PipelineTrustLevel.VERIFIED
    assert score.score == 1.0

def test_kpi_calculation():
    adaptive = AdaptiveCICD()
    pipeline_id = "test-pipeline"
    
    # Add varying duration runs
    adaptive.record_run_result(pipeline_id, "success", 10.0, {"test_pass_rate": 0.9, "coverage": 85.0})
    adaptive.record_run_result(pipeline_id, "failed", 50.0, {"is_retry": True})
    adaptive.record_run_result(pipeline_id, "success", 20.0, {"test_pass_rate": 1.0, "coverage": 90.0})

    kpis = adaptive.calculate_kpis(pipeline_id)
    assert kpis.success_rate == pytest.approx(0.6666, 0.01)
    assert kpis.test_pass_rate == pytest.approx(0.95, 0.01)
    assert kpis.retry_rate == pytest.approx(0.3333, 0.01)

@patch('backend.genesis.adaptive_cicd.get_adaptive_cicd')
@pytest.mark.asyncio
async def test_get_llm_recommendation(mock_get_adaptive):
    adaptive = AdaptiveCICD()
    
    # Default without mocking orchestrator will fallback to rules
    rec = adaptive._rule_based_recommendation("pipeline_abc", {})
    assert rec["action"] == "sandbox"
    assert rec["risk"] == "high"

@pytest.mark.asyncio
async def test_governance_request():
    import sys
    # Mock the module before importing
    mock_api = MagicMock()
    sys.modules['api'] = mock_api
    mock_gov_api = MagicMock()
    mock_submit = AsyncMock()
    mock_gov_api.submit_governance_request = mock_submit
    sys.modules['api.governance_api'] = mock_gov_api

    adaptive = AdaptiveCICD()
    pipeline_id = "test-gov"
    
    trigger_mock = MagicMock()
    trigger_mock.id = "trig123"
    trigger_mock.pipeline_id = pipeline_id
    trigger_mock.reason = AdaptiveTriggerReason.SECURITY_CONCERN
    trigger_mock.governance_action = GovernanceAction.SECURITY_CHANGE
    trigger_mock.llm_recommendation = '{"risk": "critical", "action": "proceed"}'
    
    req = await adaptive.request_governance_approval(trigger_mock)
    assert req.action == GovernanceAction.SECURITY_CHANGE
    assert req.status == "pending"
    assert req.requires_response is True
    
    approved_req = adaptive.approve_governance_request(req.id, "admin", True)
    assert approved_req.status == "approved"
    assert approved_req.reviewer == "admin"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
