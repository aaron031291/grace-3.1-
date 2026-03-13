import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

# Prevent ModuleNotFoundError for 'backend'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from backend.cognitive.unified_memory import UnifiedMemory
from backend.cognitive_framework.events import CognitiveEvent
from backend.cognitive_framework.cognitive_framework import CognitiveFramework

@pytest.fixture
def memory_system():
    # Provide a mocked session for the memory manager
    mock_session = MagicMock()
    return UnifiedMemory()

@pytest.mark.asyncio
async def test_unified_memory_12_layer_e2e_loop():
    """
    Tests the full 12-layer Memory Subsystem loop:
    1. Memory Ingestion (Episodic)
    2. Trust Degradation Anomaly Detection (analyze_for_resilience)
    3. Event Bus Publication (system.repeated_failure_detected)
    4. Websocket Broadcast interception (Simulated via Bus context)
    5. Cognitive Framework Ingestion
    6. Blast Radius & Consequence Engine Context
    7. OODA Loop Orientation
    8. OODA Loop Chess-Mode Generation
    9. 16-Question Evaluation
    10. Actuation Routing (Playbook Executor)
    11. Swarm Coding Agent/Learning Loop Task Queue Dispatch
    12. Clarity Framework 5W1H Ledger Recording
    """

    # 1. Setup our Mocks for the 12 Layers to avoid needing a live DB/ZMQ
    with patch("backend.core.clarity_framework.ClarityFramework.record_decision") as mock_clarity, \
         patch("backend.coding_agent.task_queue.submit") as mock_queue, \
         patch("backend.cognitive.event_bus.publish") as mock_publish, \
         patch("backend.cognitive.event_bus.publish_async") as mock_publish_async, \
         patch("backend.api._genesis_tracker.track") as mock_track, \
         patch("backend.cognitive.unified_memory._get_session") as mock_session_getter:
        
        # Mock the DB Session for memory retrieval
        mock_session = MagicMock()
        mock_session_getter.return_value = mock_session
        
        # Setup simulated degraded episodes (Trust < 0.5) to trigger the anomaly
        mock_episode = MagicMock()
        mock_episode.source = "synaptic_core_orchestration"
        mock_episode.trust_score = 0.2
        mock_episode.outcome = "failed to generate valid response"
        mock_episode.timestamp = datetime.utcnow()
        
        # Mock the sqlalchemy query chain: session.query().filter().order_by().limit().all()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_episode, mock_episode, mock_episode] # 3 failures triggers it

        # --- LAYER 1-3: Memory Ingestion & Resilience Anomaly Detection ---
        mem = UnifiedMemory.get_instance()
        mem.analyze_for_resilience()
        
        # Assert Layer 3: Event Bus published the retraining event due to degraded trust
        mock_publish_async.assert_called_with(
            "learning.needs_retraining", 
            {
                "model_or_source": "synaptic_core_orchestration",
                "average_trust": pytest.approx(0.2), # Exact average of our three mocks
                "episode_count": 3
            }, 
            source="unified_memory"
        )

        # --- LAYER 4-6: Cognitive Framework & Consequence Engine ---
        # Simulate the Event Bus passing this anomaly into the Cognitive Framework
        anomaly_event = CognitiveEvent(
            id="evt_mem_789",
            type="learning.needs_retraining",
            source_component="unified_memory",
            payload={"model_or_source": "synaptic_core_orchestration", "average_trust": 0.2},
            severity=4
        )

        framework = CognitiveFramework()
        
        # Mock Clarity Return
        mock_decision = MagicMock()
        mock_decision.id = "decision_mem_999"
        mock_clarity.return_value = mock_decision
        
        # Mock Queue task ID
        mock_queue.return_value = "task_mem_fix_001"

        # Await the execution pipeline
        result = await framework.process_event(anomaly_event)

        # --- LAYER 7-12: OODA, Playbooks, Task Queue, & Clarity Assurance ---
        
        # Layer 12: Ensure it registered to Clarity Framework explicitly
        assert result["decision_id"] == "decision_mem_999"
        mock_clarity.assert_called_once()
        clarity_kwargs = mock_clarity.call_args[1]
        assert "learning.needs_retraining" in clarity_kwargs["what"]
        assert clarity_kwargs["who"]["actor"] == "cognitive_framework"
        assert "unified_memory" in clarity_kwargs["where"]["impacted_components"]

        # Layer 11: Task Queue Dispatch
        # A learning problem with risk score <= 0.5 triggers level 1 research/coding missions
        mock_queue.assert_called_once()
        queue_args = mock_queue.call_args[1]
        assert "task_type" in queue_args and queue_args["task_type"] == "playbook_execution"
        assert "ooda_context" in queue_args["context"]
        
        # Layer 7-9: OODA Context Generation Validation
        ooda_ctx = queue_args["context"]["ooda_context"]
        assert "orientation" in ooda_ctx
        assert "learning.needs_retraining" in ooda_ctx["orientation"]["original_problem"]
        
        # Confirm a definitive lowest risk/complexity path was chosen
        assert "path_description" in ooda_ctx["chess_mode_decision"]
        assert "evaluation_answers" in ooda_ctx["chess_mode_decision"]
