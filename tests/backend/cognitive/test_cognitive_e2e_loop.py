import pytest
import asyncio
import sys
import os
from typing import Dict, Any
from unittest.mock import patch, MagicMock

# Add project root to sys path so pytest can find backend imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Core Cognitive Models
from backend.cognitive_framework.events import CognitiveEvent
from backend.cognitive_framework.cognitive_framework import CognitiveFramework
from backend.cognitive_framework.cognitive_blueprint import OODALoopExecutor

# Core Subsystems to mock
from backend.core.clarity_framework import ClarityFramework
import backend.api._genesis_tracker

@pytest.fixture
def sample_cognitive_event():
    """Generates a high-risk error event simulating a subsystem crash."""
    return CognitiveEvent(
        id="evt_test_456",
        type="guardian.log_error",
        source_component="api_service",
        payload={"error": "SyntaxWarning in module", "stack_trace": "..."},
        severity=3,
        timestamp="2026-03-14T10:00:00Z"
    )

@pytest.mark.asyncio
async def test_cognitive_framework_e2e_pipeline(sample_cognitive_event):
    """
    Tests the full execution pipeline of Grace's Cognitive Framework:
    Event -> Consequence Engine -> Escalation -> OODA Blueprint -> Task Queue
    """
    
    # Setup Mocks so we don't hit live Event Bus / Database
    with patch("backend.core.clarity_framework.ClarityFramework.record_decision") as mock_clarity, \
         patch("backend.cognitive.event_bus.publish") as mock_bus_publish, \
         patch("backend.coding_agent.task_queue.submit") as mock_queue_submit, \
         patch("backend.api._genesis_tracker.track") as mock_track:
         
        # Mock Task Queue
        mock_queue_submit.return_value = "task_999"

        # Mock Event Bus Publish
        mock_bus_publish.return_value = None
        
        # Mock Clarity Framework Return
        mock_decision = MagicMock()
        mock_decision.id = "decision_123"
        mock_clarity.return_value = mock_decision

        # 1. Initialize the central framework
        framework = CognitiveFramework()

        # 2. Process the Event (Async Entry Point)
        result = await framework.process_event(sample_cognitive_event)

        # --------- Assertions for Pipeline Integrity ---------

        # Phase A: Governance and 5W1H Logging
        assert result["decision_id"] == "decision_123", "Clarity decision was not returned."
        
        # Ensure Phase 1-2 Blast Radius logic logged properly to Clarity
        mock_clarity.assert_called_once()
        clarity_args, clarity_kwargs = mock_clarity.call_args
        
        assert "what" in clarity_kwargs
        assert "Processed event guardian.log_error" in clarity_kwargs["what"]
        assert "who" in clarity_kwargs and clarity_kwargs["who"]["actor"] == "cognitive_framework"
        assert "where" in clarity_kwargs and "api_service" in clarity_kwargs["where"]["impacted_components"]
        assert "risk_score" in clarity_kwargs
        
        # Phase B: The OODA Loop and Chess Mode Integration
        # Ensure the Task Queue was called (i.e., Playbook routed correctly)
        mock_queue_submit.assert_called_once()
        
        queue_args, queue_kwargs = mock_queue_submit.call_args
        
        assert queue_kwargs["task_type"] == "playbook_execution"
        
        # Confirm OODA Context was generated and passed to the Coding Agent
        submitted_instructions = queue_kwargs["instructions"]
        submitted_context = queue_kwargs["context"]
        
        assert "ooda_context" in submitted_context, "Swarm Agents missing OODA context"
        ooda_context = submitted_context["ooda_context"]
        
        # 1. Orient & Observe check
        assert "orientation" in ooda_context
        assert ooda_context["orientation"]["original_problem"] == f"Needs coding or research resolution for event evt_test_456 (guardian.log_error)"
        assert "Must be reversible" in ooda_context["orientation"]["constraints"]
        
        # 2. Chess Mode Decision Check
        assert "chess_mode_decision" in ooda_context
        decision_data = ooda_context["chess_mode_decision"]
        
        assert "complexity_score" in decision_data
        assert "blast_radius" in decision_data
        assert "path_description" in decision_data
        # Ensure it chose the safest generated path (complex 0.2, blast 0.1)
        assert "Directly patch" in decision_data["path_description"]
        
        # 3. Sixteen Questions check
        assert "sixteen_questions_rubric" in ooda_context
        assert len(ooda_context["sixteen_questions_rubric"]) == 16
        assert "OODA Cognitive Pre-computation" in submitted_instructions

@pytest.mark.asyncio
async def test_ooda_loop_executor_direct():
    """
    Direct unit test of the Async OODA Loop execution.
    Ensures Chess mode generates evaluated paths and selects the lowest risk.
    """
    executor = OODALoopExecutor()
    
    problem = "Component auth_service is failing under load."
    event_ctx = {"region": "us-east"}
    
    # Run the executor
    result = await executor.process_and_act(problem, event_ctx)
    
    assert result["orientation"]["original_problem"] == problem
    assert result["orientation"]["ambient_context"] == event_ctx
    
    assert "Directly patch" in result["chess_mode_decision"]["path_description"]
    # The selected path logic demands the lowest (complexity + blast_radius).
    # Expected: 0.2 + 0.1 = 0.3
    assert result["chess_mode_decision"]["complexity_score"] == 0.2
    assert result["chess_mode_decision"]["blast_radius"] == 0.1
    
    # Verify the 16 Questions are present to bound the Coding Agents
    assert "1. Does it solve the explicit problem it was designed to solve?" in result["sixteen_questions_rubric"]
    assert "16. What new problems, risks, or trade-offs does it introduce?" in result["sixteen_questions_rubric"]
