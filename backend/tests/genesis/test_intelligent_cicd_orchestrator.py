import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from backend.genesis.intelligent_cicd_orchestrator import (
    IntelligentTestSelector,
    TestSelectionStrategy,
    WebhookEventProcessor,
    WebhookEvent,
    ClosedLoopFeedback,
    IntelligentCICDOrchestrator,
    TriggerSource,
    PipelineDecision,
    IntelligenceMode
)

def test_intelligent_test_selector():
    selector = IntelligentTestSelector()
    
    # Record some test results
    selector.record_test_result("test_foo", passed=True, duration=1.0, coverage=0.8)
    selector.record_test_result("test_bar", passed=False, duration=5.0, coverage=0.4)
    selector.record_test_result("test_baz", passed=True, duration=2.0, coverage=0.9)
    
    # test_bar failed so failure_recency is high
    assert selector.test_metrics["test_bar"].failure_recency == 1.0
    
    # Selection strategies
    all_tests = selector.select_tests(TestSelectionStrategy.ALL_TESTS)
    assert len(all_tests) == 3
    
    # Failure prediction should favor test_bar
    failure_tests = selector.select_tests(TestSelectionStrategy.FAILURE_PREDICTION)
    assert "test_bar" in failure_tests
    
    # Changed only impact analysis
    changed_tests = selector.select_tests(TestSelectionStrategy.CHANGED_ONLY, changed_files=["foo.py"])
    assert "test_foo" in changed_tests

@pytest.mark.asyncio
async def test_webhook_event_processor():
    processor = WebhookEventProcessor()
    
    mock_handler = AsyncMock(return_value={"actions": ["test_action"]})
    processor.register_handler("push", mock_handler)
    
    event = WebhookEvent(
        id="123", source="github", event_type="push",
        timestamp="2023-01-01", payload={"ref": "refs/heads/main"}
    )
    
    result = await processor.process_event(event)
    
    assert result["handlers_invoked"] == 1
    assert "test_action" in result["actions_triggered"]
    mock_handler.assert_called_once_with(event)
    assert event.processed is True

def test_closed_loop_feedback():
    feedback = ClosedLoopFeedback()
    
    # Record normal metrics
    for _ in range(15):
        feedback.record_metric("error_rate", 0.01)
        
    # Inject anomaly
    metric = feedback.record_metric("error_rate", 0.50)
    
    assert metric.trend == "degrading"
    
    # Should trigger anomaly response
    assert len(feedback.feedback_actions) > 0
    assert feedback.feedback_actions[-1]["metric_name"] == "error_rate"
    
    recommendation = feedback.get_trigger_recommendation()
    assert recommendation == TriggerSource.HEALTH_DEGRADATION

@pytest.mark.asyncio
async def test_orchestrator_decision_making():
    orchestrator = IntelligentCICDOrchestrator(intelligence_mode=IntelligenceMode.RULE_BASED)
    
    # PR trigger should result in TRIGGER_FULL or PARTIAL based on rules
    decision = await orchestrator.make_pipeline_decision(
        trigger_source=TriggerSource.GIT_PR,
        context={"changed_files": ["src/main.py"]}
    )
    
    assert decision.decision == PipelineDecision.TRIGGER_FULL
    assert decision.trigger_source == TriggerSource.GIT_PR
    assert decision.test_strategy == TestSelectionStrategy.IMPACT_ANALYSIS

@patch('backend.genesis.intelligent_cicd_orchestrator.get_intelligent_cicd_orchestrator')
@pytest.mark.asyncio
async def test_execute_decision(mock_get_orchestrator):
    orchestrator = IntelligentCICDOrchestrator()
    
    decision = MagicMock()
    decision.decision = PipelineDecision.SKIP
    decision.decision_id = "test-123"
    decision.genesis_key = "GK-123"
    
    result = await orchestrator.execute_decision(decision)
    assert result["status"] == "skipped"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
