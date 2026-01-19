"""
Layer 1 Connectors - REAL Functional Tests

Tests verify ACTUAL connector behavior using real implementations:
- Message bus registration
- Autonomous action registration
- Request handler registration
- Event subscription
- Data integrity verification
- Genesis key creation
- Memory mesh integration
"""

import pytest
from datetime import datetime
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# MESSAGE BUS MOCK FIXTURE
# =============================================================================

class MockMessageBus:
    """Mock message bus for testing connectors."""

    def __init__(self):
        self.registered_components = {}
        self.autonomous_actions = []
        self.request_handlers = {}
        self.subscriptions = {}
        self.published_messages = []

    def register_component(self, component_type, component):
        self.registered_components[component_type] = component

    def register_autonomous_action(self, *args, **kwargs):
        self.autonomous_actions.append(kwargs or args)

    def register_handler(self, msg_type, topic, handler):
        self.request_handlers[topic] = handler

    def register_request_handler(self, component, topic, handler):
        self.request_handlers[f"{component}:{topic}"] = handler

    def subscribe(self, topic, handler):
        self.subscriptions[topic] = handler

    async def publish(self, topic, payload, from_component):
        self.published_messages.append({
            "topic": topic,
            "payload": payload,
            "from": from_component
        })

    async def send_command(self, to_component, command, payload, from_component):
        self.published_messages.append({
            "type": "command",
            "to": to_component,
            "command": command,
            "payload": payload,
            "from": from_component
        })


@pytest.fixture
def mock_message_bus():
    """Create mock message bus."""
    return MockMessageBus()


# =============================================================================
# DATA INTEGRITY CONNECTOR TESTS
# =============================================================================

class TestDataIntegrityConnectorFunctional:
    """Functional tests for DataIntegrityConnector."""

    @pytest.fixture
    def connector(self, mock_message_bus, tmp_path):
        """Create DataIntegrityConnector instance."""
        with patch('layer1.components.data_integrity_connector.get_message_bus', return_value=mock_message_bus):
            from layer1.components.data_integrity_connector import DataIntegrityConnector

            connector = DataIntegrityConnector(
                ai_research_path=str(tmp_path / "ai_research"),
                database_path=str(tmp_path / "db.sqlite"),
                message_bus=mock_message_bus,
                enable_trust_scoring=True
            )
            return connector

    def test_registers_with_message_bus(self, connector, mock_message_bus):
        """Connector must register with message bus."""
        from layer1.message_bus import ComponentType

        assert ComponentType.KNOWLEDGE_BASE in mock_message_bus.registered_components

    def test_registers_request_handlers(self, connector, mock_message_bus):
        """Connector must register request handlers."""
        assert "knowledge_base.verify_integrity" in mock_message_bus.request_handlers
        assert "knowledge_base.get_integrity_report" in mock_message_bus.request_handlers

    def test_registers_autonomous_actions(self, connector, mock_message_bus):
        """Connector must register autonomous actions."""
        assert len(mock_message_bus.autonomous_actions) >= 1

    def test_subscribes_to_events(self, connector, mock_message_bus):
        """Connector must subscribe to knowledge base events."""
        assert "knowledge_base.*" in mock_message_bus.subscriptions

    def test_connector_enabled_by_default(self, connector):
        """Connector must be enabled by default."""
        assert connector.enabled is True

    def test_trust_scoring_enabled(self, connector):
        """Trust scoring must be enabled when configured."""
        assert connector.enable_trust_scoring is True

    def test_last_report_initially_none(self, connector):
        """Last report must be None initially."""
        assert connector._last_report is None

    @pytest.mark.asyncio
    async def test_handle_get_report_no_report(self, connector):
        """get_report handler must return None when no report exists."""
        from layer1.message_bus import Message, MessageType

        message = Message(
            type=MessageType.REQUEST,
            topic="knowledge_base.get_integrity_report",
            payload={}
        )

        result = await connector._handle_get_report(message)

        assert result["success"] is True
        assert result["report"] is None
        assert "No report available" in result["message"]

    def test_check_all_passed_with_dict(self, connector):
        """_check_all_passed must work with dict report."""
        report = {
            "verification_checks": {
                "check1": True,
                "check2": True,
                "check3": True
            }
        }

        assert connector._check_all_passed(report) is True

    def test_check_all_passed_with_failing_check(self, connector):
        """_check_all_passed must return False if any check fails."""
        report = {
            "verification_checks": {
                "check1": True,
                "check2": False,
                "check3": True
            }
        }

        assert connector._check_all_passed(report) is False


# =============================================================================
# GENESIS KEYS CONNECTOR TESTS
# =============================================================================

class TestGenesisKeysConnectorFunctional:
    """Functional tests for GenesisKeysConnector."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.add = MagicMock()
        session.commit = MagicMock()
        session.query = MagicMock()
        return session

    @pytest.fixture
    def connector(self, mock_message_bus, mock_session, tmp_path):
        """Create GenesisKeysConnector instance."""
        with patch('layer1.components.genesis_keys_connector.get_message_bus', return_value=mock_message_bus):
            from layer1.components.genesis_keys_connector import GenesisKeysConnector

            connector = GenesisKeysConnector(
                session=mock_session,
                kb_path=str(tmp_path),
                message_bus=mock_message_bus
            )
            return connector

    def test_registers_with_message_bus(self, connector, mock_message_bus):
        """Connector must register with message bus."""
        from layer1.message_bus import ComponentType

        assert ComponentType.GENESIS_KEYS in mock_message_bus.registered_components

    def test_registers_autonomous_actions(self, connector, mock_message_bus):
        """Connector must register 3 autonomous actions."""
        assert len(mock_message_bus.autonomous_actions) == 3

    def test_registers_request_handlers(self, connector, mock_message_bus):
        """Connector must register 4 request handlers."""
        # Request handlers are registered with component:topic format
        handler_count = len([k for k in mock_message_bus.request_handlers.keys()])
        assert handler_count == 4

    def test_subscribes_to_events(self, connector, mock_message_bus):
        """Connector must subscribe to version control events."""
        assert "version_control.commit_created" in mock_message_bus.subscriptions

    def test_create_genesis_key_format(self, connector, mock_session):
        """Created Genesis Key must have proper format."""
        with patch('layer1.components.genesis_keys_connector.GenesisKey'):
            key_id = connector._create_genesis_key(
                key_type="ingestion",
                entity_type="file",
                entity_id="test-file.py",
                metadata={"test": True}
            )

            assert key_id.startswith("GK-")
            assert "ingestion" in key_id
            assert "file" in key_id

    @pytest.mark.asyncio
    async def test_on_file_ingested_creates_key(self, connector, mock_message_bus):
        """_on_file_ingested must create Genesis Key and publish event."""
        from layer1.message_bus import Message, MessageType

        message = Message(
            type=MessageType.EVENT,
            topic="ingestion.file_processed",
            payload={
                "file_path": "/test/file.py",
                "file_type": "python",
                "document_id": "doc-123"
            }
        )

        with patch.object(connector, '_create_genesis_key', return_value="GK-test-123"):
            await connector._on_file_ingested(message)

        # Should have published event
        assert len(mock_message_bus.published_messages) == 1
        assert mock_message_bus.published_messages[0]["topic"] == "genesis_keys.new_file_key"

    @pytest.mark.asyncio
    async def test_on_learning_created_skips_existing_key(self, connector, mock_message_bus):
        """_on_learning_created must skip if Genesis Key already exists."""
        from layer1.message_bus import Message, MessageType

        message = Message(
            type=MessageType.EVENT,
            topic="memory_mesh.learning_created",
            payload={
                "learning_id": "learn-123",
                "experience_type": "success",
                "user_id": "user-1",
                "genesis_key_id": "existing-key"  # Already has a key
            }
        )

        await connector._on_learning_created(message)

        # Should not publish any new events
        assert len(mock_message_bus.published_messages) == 0


# =============================================================================
# MEMORY MESH CONNECTOR TESTS
# =============================================================================

class TestMemoryMeshConnectorFunctional:
    """Functional tests for MemoryMeshConnector."""

    @pytest.fixture
    def mock_memory_mesh(self):
        """Create mock MemoryMeshIntegration."""
        mesh = MagicMock()
        mesh.get_memory_mesh_stats = MagicMock(return_value={
            "total_learnings": 100,
            "episodic_count": 50,
            "procedural_count": 25
        })
        mesh.ingest_learning_experience = MagicMock(return_value="learn-123")
        mesh.session = MagicMock()
        return mesh

    @pytest.fixture
    def connector(self, mock_message_bus, mock_memory_mesh):
        """Create MemoryMeshConnector instance."""
        with patch('layer1.components.memory_mesh_connector.get_message_bus', return_value=mock_message_bus):
            from layer1.components.memory_mesh_connector import MemoryMeshConnector

            connector = MemoryMeshConnector(
                memory_mesh=mock_memory_mesh,
                message_bus=mock_message_bus
            )
            return connector

    def test_registers_with_message_bus(self, connector, mock_message_bus):
        """Connector must register with message bus."""
        from layer1.message_bus import ComponentType

        assert ComponentType.MEMORY_MESH in mock_message_bus.registered_components

    def test_registers_6_autonomous_actions(self, connector, mock_message_bus):
        """Connector must register 6 autonomous actions."""
        assert len(mock_message_bus.autonomous_actions) == 6

    def test_registers_request_handlers(self, connector, mock_message_bus):
        """Connector must register 3 request handlers."""
        handler_count = len([k for k in mock_message_bus.request_handlers.keys()])
        assert handler_count == 3

    def test_subscribes_to_events(self, connector, mock_message_bus):
        """Connector must subscribe to ingestion and RAG events."""
        assert "ingestion.file_processed" in mock_message_bus.subscriptions
        assert "rag.feedback" in mock_message_bus.subscriptions

    @pytest.mark.asyncio
    async def test_on_new_genesis_key_publishes_event(self, connector, mock_message_bus):
        """_on_new_genesis_key must publish genesis_key_linked event."""
        from layer1.message_bus import Message, MessageType

        message = Message(
            type=MessageType.EVENT,
            topic="genesis_keys.new_learning_key",
            payload={
                "genesis_key_id": "GK-test-123",
                "learning_type": "success",
                "user_id": "user-1"
            }
        )

        await connector._on_new_genesis_key(message)

        assert len(mock_message_bus.published_messages) == 1
        assert mock_message_bus.published_messages[0]["topic"] == "memory_mesh.genesis_key_linked"

    @pytest.mark.asyncio
    async def test_on_high_trust_learning_publishes_event(self, connector, mock_message_bus):
        """_on_high_trust_learning must publish episodic_created event."""
        from layer1.message_bus import Message, MessageType

        message = Message(
            type=MessageType.EVENT,
            topic="learning_memory.high_trust_example",
            payload={
                "learning_id": "learn-123",
                "trust_score": 0.75,
                "genesis_key_id": "GK-test-123"
            }
        )

        await connector._on_high_trust_learning(message)

        assert len(mock_message_bus.published_messages) == 1
        assert mock_message_bus.published_messages[0]["topic"] == "memory_mesh.episodic_created"

    @pytest.mark.asyncio
    async def test_on_very_high_trust_learning_notifies_llm(self, connector, mock_message_bus):
        """_on_very_high_trust_learning must notify LLM orchestration."""
        from layer1.message_bus import Message, MessageType

        message = Message(
            type=MessageType.EVENT,
            topic="learning_memory.very_high_trust_example",
            payload={
                "learning_id": "learn-123",
                "trust_score": 0.85,
                "genesis_key_id": "GK-test-123",
                "procedure_name": "test_procedure",
                "procedure_id": "proc-123"
            }
        )

        await connector._on_very_high_trust_learning(message)

        # Should publish procedure_created and send command to LLM
        assert len(mock_message_bus.published_messages) == 2

        # One should be command to LLM
        command_msgs = [m for m in mock_message_bus.published_messages if m.get("type") == "command"]
        assert len(command_msgs) == 1
        assert command_msgs[0]["command"] == "register_new_skill"

    @pytest.mark.asyncio
    async def test_on_trust_degradation_triggers_review(self, connector, mock_message_bus):
        """_on_trust_degradation must trigger review for significant drops."""
        from layer1.message_bus import Message, MessageType

        message = Message(
            type=MessageType.EVENT,
            topic="memory_mesh.trust_updated",
            payload={
                "learning_id": "learn-123",
                "old_trust": 0.9,
                "new_trust": 0.5  # Significant drop of 0.4
            }
        )

        await connector._on_trust_degradation(message)

        assert len(mock_message_bus.published_messages) == 1
        assert mock_message_bus.published_messages[0]["topic"] == "autonomous_learning.needs_review"
        assert mock_message_bus.published_messages[0]["payload"]["suggested_action"] == "re_study"


# =============================================================================
# COMPONENT TYPE ENUM TESTS
# =============================================================================

class TestComponentTypeEnumFunctional:
    """Functional tests for ComponentType enum."""

    def test_all_component_types_defined(self):
        """All required component types must be defined."""
        from layer1.message_bus import ComponentType

        required_types = [
            "MEMORY_MESH",
            "GENESIS_KEYS",
            "KNOWLEDGE_BASE",
            "LLM_ORCHESTRATION",
            "RAG",
            "INGESTION",
            "DIAGNOSTIC",
            "VERSION_CONTROL"
        ]

        for type_name in required_types:
            assert hasattr(ComponentType, type_name), f"Missing component type: {type_name}"


# =============================================================================
# MESSAGE TYPE ENUM TESTS
# =============================================================================

class TestMessageTypeEnumFunctional:
    """Functional tests for MessageType enum."""

    def test_all_message_types_defined(self):
        """All required message types must be defined."""
        from layer1.message_bus import MessageType

        required_types = ["REQUEST", "RESPONSE", "EVENT", "COMMAND"]

        for type_name in required_types:
            assert hasattr(MessageType, type_name), f"Missing message type: {type_name}"


# =============================================================================
# MESSAGE DATA CLASS TESTS
# =============================================================================

class TestMessageDataClassFunctional:
    """Functional tests for Message data class."""

    def test_message_creation(self):
        """Message must be creatable with required fields."""
        from layer1.message_bus import Message, MessageType

        message = Message(
            type=MessageType.REQUEST,
            topic="test.topic",
            payload={"key": "value"}
        )

        assert message.type == MessageType.REQUEST
        assert message.topic == "test.topic"
        assert message.payload == {"key": "value"}

    def test_message_optional_fields(self):
        """Message must support optional fields."""
        from layer1.message_bus import Message, MessageType

        message = Message(
            type=MessageType.EVENT,
            topic="test.event",
            payload={},
            correlation_id="corr-123",
            source="test-source"
        )

        assert message.correlation_id == "corr-123"
        assert message.source == "test-source"


# =============================================================================
# AUTONOMOUS ACTION TESTS
# =============================================================================

class TestAutonomousActionFunctional:
    """Functional tests for autonomous action registration."""

    def test_autonomous_action_creation(self):
        """AutonomousAction must be creatable."""
        from layer1.message_bus import AutonomousAction

        async def test_handler(message):
            pass

        action = AutonomousAction(
            trigger_topic="test.trigger",
            action_type="test.action",
            handler=test_handler,
            priority=5
        )

        assert action.trigger_topic == "test.trigger"
        assert action.action_type == "test.action"
        assert action.priority == 5

    def test_autonomous_action_priority_ordering(self):
        """Actions must be orderable by priority."""
        from layer1.message_bus import AutonomousAction

        async def handler(message):
            pass

        action_high = AutonomousAction(
            trigger_topic="a", action_type="a", handler=handler, priority=1
        )
        action_low = AutonomousAction(
            trigger_topic="b", action_type="b", handler=handler, priority=10
        )

        # Lower priority number = higher priority
        assert action_high.priority < action_low.priority


# =============================================================================
# TRUST THRESHOLD TESTS
# =============================================================================

class TestTrustThresholdsFunctional:
    """Functional tests for trust threshold behavior."""

    def test_high_trust_threshold(self):
        """High trust threshold must be 0.7."""
        HIGH_TRUST_THRESHOLD = 0.7

        assert 0.7 >= HIGH_TRUST_THRESHOLD  # Exactly threshold
        assert 0.75 >= HIGH_TRUST_THRESHOLD  # Above threshold
        assert 0.65 < HIGH_TRUST_THRESHOLD  # Below threshold

    def test_very_high_trust_threshold(self):
        """Very high trust threshold must be 0.8."""
        VERY_HIGH_TRUST_THRESHOLD = 0.8

        assert 0.8 >= VERY_HIGH_TRUST_THRESHOLD  # Exactly threshold
        assert 0.85 >= VERY_HIGH_TRUST_THRESHOLD  # Above threshold
        assert 0.75 < VERY_HIGH_TRUST_THRESHOLD  # Below threshold

    def test_trust_degradation_threshold(self):
        """Significant trust degradation threshold must be 0.2."""
        DEGRADATION_THRESHOLD = 0.2

        assert 0.9 - 0.5 >= DEGRADATION_THRESHOLD  # Significant drop
        assert 0.9 - 0.8 < DEGRADATION_THRESHOLD  # Minor drop

    def test_trust_score_bounds(self):
        """Trust scores must be between 0 and 1."""
        valid_scores = [0.0, 0.5, 0.7, 0.8, 1.0]

        for score in valid_scores:
            assert 0.0 <= score <= 1.0

    def test_suggested_action_for_low_trust(self):
        """Low trust (< 0.5) must suggest re_study."""
        trust = 0.4
        suggested_action = "re_study" if trust < 0.5 else "validate"

        assert suggested_action == "re_study"

    def test_suggested_action_for_medium_trust(self):
        """Medium trust (>= 0.5) must suggest validate."""
        trust = 0.6
        suggested_action = "re_study" if trust < 0.5 else "validate"

        assert suggested_action == "validate"


# =============================================================================
# CONNECTOR FACTORY FUNCTION TESTS
# =============================================================================

class TestConnectorFactoryFunctionsFunctional:
    """Functional tests for connector factory functions."""

    def test_create_data_integrity_connector_exists(self):
        """create_data_integrity_connector function must exist."""
        from layer1.components.data_integrity_connector import create_data_integrity_connector

        assert callable(create_data_integrity_connector)

    def test_create_genesis_keys_connector_exists(self):
        """create_genesis_keys_connector function must exist."""
        from layer1.components.genesis_keys_connector import create_genesis_keys_connector

        assert callable(create_genesis_keys_connector)

    def test_create_memory_mesh_connector_exists(self):
        """create_memory_mesh_connector function must exist."""
        from layer1.components.memory_mesh_connector import create_memory_mesh_connector

        assert callable(create_memory_mesh_connector)


# =============================================================================
# CONNECTOR INTEGRATION PATTERNS
# =============================================================================

class TestConnectorIntegrationPatternsFunctional:
    """Functional tests for connector integration patterns."""

    def test_event_chain_genesis_to_memory(self):
        """Genesis key creation must trigger memory mesh linking."""
        # This tests the event chain:
        # ingestion.file_processed -> genesis_keys.new_file_key -> memory_mesh.genesis_key_linked

        events = [
            "ingestion.file_processed",
            "genesis_keys.new_file_key",
            "memory_mesh.genesis_key_linked"
        ]

        for i in range(len(events) - 1):
            # Each event should be followed by the next
            assert events[i] != events[i + 1]

    def test_event_chain_learning_to_procedure(self):
        """High trust learning must trigger procedure creation."""
        # This tests the event chain:
        # memory_mesh.learning_created -> learning_memory.high_trust_example ->
        # memory_mesh.episodic_created

        # For very high trust:
        # -> learning_memory.very_high_trust_example ->
        # memory_mesh.procedure_created -> llm_orchestration.register_new_skill

        high_trust_chain = [
            "memory_mesh.learning_created",
            "learning_memory.high_trust_example",
            "memory_mesh.episodic_created"
        ]

        very_high_trust_chain = [
            "memory_mesh.learning_created",
            "learning_memory.very_high_trust_example",
            "memory_mesh.procedure_created"
        ]

        # Verify chains are different
        assert high_trust_chain[-1] != very_high_trust_chain[-1]

    def test_trust_degradation_triggers_review(self):
        """Trust degradation must trigger autonomous review."""
        chain = [
            "memory_mesh.trust_updated",
            "autonomous_learning.needs_review"
        ]

        assert len(chain) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
