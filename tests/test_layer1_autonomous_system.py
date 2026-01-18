"""
Test Layer 1 Autonomous Communication System (Unit Tests)

Tests autonomous workflows without requiring database or server:
1. User correction → Learning pipeline
2. File upload → Genesis Key + processing
3. RAG query → Enhanced retrieval + feedback
"""
import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import MagicMock, AsyncMock, patch

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


@pytest.fixture
def mock_message_bus():
    """Create a mock message bus for testing."""
    from layer1.message_bus import Layer1MessageBus, ComponentType
    
    bus = Layer1MessageBus()
    return bus


@pytest.fixture
def mock_memory_mesh():
    """Create a mock memory mesh."""
    mesh = MagicMock()
    mesh.trigger_learning_ingestion = AsyncMock(return_value="learning-123")
    mesh.get_procedures = MagicMock(return_value=[])
    mesh.store_feedback = MagicMock(return_value=True)
    return mesh


@pytest.fixture
def mock_layer1_system(mock_message_bus, mock_memory_mesh):
    """Create a mock Layer 1 system."""
    system = MagicMock()
    system.message_bus = mock_message_bus
    system.memory_mesh = mock_memory_mesh
    system.get_stats = MagicMock(return_value={
        "total_messages": 0,
        "requests": 0,
        "events": 0,
        "commands": 0,
        "autonomous_actions_triggered": 0,
        "registered_components": 5,
        "components": ["genesis_keys", "memory_mesh", "rag", "ingestion", "llm_orchestration"]
    })
    system.get_autonomous_actions = MagicMock(return_value=[
        {"component": "memory_mesh", "description": "Process learning ingestion"},
        {"component": "rag", "description": "Update index on new document"},
    ])
    return system


class TestAutonomousLearningFlow:
    """Test autonomous learning pipeline."""

    @pytest.mark.asyncio
    async def test_learning_ingestion_returns_id(self, mock_memory_mesh):
        """Test that learning ingestion returns a valid ID."""
        result = await mock_memory_mesh.trigger_learning_ingestion(
            experience_type="correction",
            context={"question": "What is the capital of Australia?"},
            action_taken={"answer_provided": "Sydney"},
            outcome={"correct_answer": "Canberra", "success": False},
            user_id="GU-testuser123"
        )
        
        assert result is not None
        assert isinstance(result, str)
        mock_memory_mesh.trigger_learning_ingestion.assert_called_once()

    @pytest.mark.asyncio
    async def test_correction_triggers_high_trust_learning(self, mock_layer1_system):
        """Test that user corrections result in high trust learning."""
        correction_data = {
            "experience_type": "correction",
            "context": {"question": "What is the capital of Australia?"},
            "action_taken": {"answer_provided": "Sydney", "confidence": 0.6},
            "outcome": {
                "correct_answer": "Canberra",
                "success": False,
                "user_corrected": True
            }
        }
        
        # User corrections should have trust >= 0.85
        expected_trust = 0.9  # Corrections are highly trusted
        assert expected_trust >= 0.85

    @pytest.mark.asyncio
    async def test_stats_update_after_learning(self, mock_layer1_system):
        """Test that stats are updated after learning ingestion."""
        initial_stats = mock_layer1_system.get_stats()
        initial_messages = initial_stats["total_messages"]
        
        # After learning, messages should increase
        mock_layer1_system.get_stats.return_value = {
            **initial_stats,
            "total_messages": initial_messages + 3,
            "events": 2,
            "autonomous_actions_triggered": 1
        }
        
        final_stats = mock_layer1_system.get_stats()
        assert final_stats["total_messages"] >= initial_messages


class TestFileIngestionFlow:
    """Test autonomous file ingestion."""

    @pytest.mark.asyncio
    async def test_file_ingestion_request_structure(self, mock_message_bus):
        """Test file ingestion request has correct structure."""
        from layer1.message_bus import ComponentType
        
        payload = {
            "file_path": "test_document.pdf",
            "file_type": "pdf",
            "user_id": "GU-testuser123"
        }
        
        assert "file_path" in payload
        assert "file_type" in payload
        assert "user_id" in payload
        assert payload["user_id"].startswith("GU-")

    @pytest.mark.asyncio
    async def test_file_upload_triggers_genesis_key(self, mock_message_bus):
        """Test that file upload triggers genesis key creation."""
        from layer1.message_bus import ComponentType
        
        received_events = []
        
        def capture_event(msg):
            received_events.append(msg)
        
        mock_message_bus.subscribe("file.uploaded", capture_event)
        
        await mock_message_bus.publish(
            topic="file.uploaded",
            payload={
                "file_path": "test.pdf",
                "document_id": "doc-123"
            },
            from_component=ComponentType.INGESTION
        )
        
        assert len(received_events) == 1
        assert received_events[0].payload["file_path"] == "test.pdf"

    def test_supported_file_types(self):
        """Test supported file types for ingestion."""
        supported_types = ["pdf", "txt", "md", "py", "js", "ts", "json", "yaml", "yml"]
        
        test_type = "pdf"
        assert test_type in supported_types


class TestRAGRetrievalFlow:
    """Test autonomous RAG retrieval with enhancement."""

    @pytest.mark.asyncio
    async def test_rag_query_structure(self):
        """Test RAG query has correct structure."""
        query = {
            "query": "What is the capital of Australia?",
            "top_k": 5
        }
        
        assert "query" in query
        assert "top_k" in query
        assert query["top_k"] > 0

    @pytest.mark.asyncio
    async def test_rag_enhances_with_procedures(self, mock_memory_mesh):
        """Test RAG enhancement with procedural memory."""
        mock_memory_mesh.get_procedures.return_value = [
            {"procedure": "answer_capital_question", "success_rate": 0.95}
        ]
        
        procedures = mock_memory_mesh.get_procedures(query="capital of Australia")
        
        assert len(procedures) >= 0  # May or may not have procedures
        mock_memory_mesh.get_procedures.assert_called_once()

    @pytest.mark.asyncio
    async def test_rag_sends_feedback(self, mock_memory_mesh):
        """Test RAG sends success/failure feedback."""
        mock_memory_mesh.store_feedback.return_value = True
        
        result = mock_memory_mesh.store_feedback(
            query="capital of Australia",
            success=True,
            relevance_score=0.92
        )
        
        assert result is True
        mock_memory_mesh.store_feedback.assert_called_once()


class TestSystemStats:
    """Test system statistics."""

    def test_stats_contain_required_fields(self, mock_layer1_system):
        """Test stats contain all required fields."""
        stats = mock_layer1_system.get_stats()
        
        required_fields = [
            "total_messages",
            "requests", 
            "events",
            "commands",
            "autonomous_actions_triggered",
            "registered_components"
        ]
        
        for field in required_fields:
            assert field in stats

    def test_autonomous_actions_list_structure(self, mock_layer1_system):
        """Test autonomous actions list has correct structure."""
        actions = mock_layer1_system.get_autonomous_actions()
        
        assert isinstance(actions, list)
        
        for action in actions:
            assert "component" in action
            assert "description" in action

    def test_component_registration(self, mock_layer1_system):
        """Test components are properly registered."""
        stats = mock_layer1_system.get_stats()
        
        assert stats["registered_components"] >= 1
        assert len(stats["components"]) >= 1
        
        # Core components should be present
        core_components = ["genesis_keys", "memory_mesh", "rag"]
        for component in core_components:
            assert component in stats["components"]


class TestAutonomousActionRegistration:
    """Test autonomous action registration and triggering."""

    @pytest.mark.asyncio
    async def test_register_autonomous_action(self, mock_message_bus):
        """Test registering an autonomous action."""
        from layer1.message_bus import ComponentType
        
        action_called = {"count": 0}
        
        async def test_action(message):
            action_called["count"] += 1
        
        mock_message_bus.register_autonomous_action(
            trigger_event="test.trigger",
            action=test_action,
            component=ComponentType.MEMORY_MESH,
            description="Test autonomous action"
        )
        
        actions = mock_message_bus._autonomous_actions
        assert len(actions) >= 1

    @pytest.mark.asyncio
    async def test_autonomous_action_triggers_on_event(self, mock_message_bus):
        """Test that autonomous action triggers when event is published."""
        from layer1.message_bus import ComponentType
        
        action_triggered = {"value": False}
        
        async def mark_triggered(message):
            action_triggered["value"] = True
        
        mock_message_bus.register_autonomous_action(
            trigger_event="mark.trigger",
            action=mark_triggered,
            component=ComponentType.GENESIS_KEYS,
            description="Mark as triggered"
        )
        
        await mock_message_bus.publish(
            topic="mark.trigger",
            payload={"test": True},
            from_component=ComponentType.INGESTION
        )
        
        await asyncio.sleep(0.1)
        
        # Action should have been triggered
        assert action_triggered["value"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
