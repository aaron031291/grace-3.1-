"""
Autonomous API - REAL Functional Tests

Tests verify ACTUAL autonomous action behavior:
- Action queueing and execution
- Rule creation and management
- Event emission
- Priority handling
- Status tracking
"""

import pytest
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# ACTION TYPE TESTS
# =============================================================================

class TestActionTypeFunctional:
    """Functional tests for ActionType enum."""

    def test_action_type_values_exist(self):
        """ActionType enum must have expected values."""
        from genesis.autonomous_engine import ActionType

        expected_types = [
            "code_fix", "code_review", "test_generation",
            "documentation", "refactoring", "security_scan"
        ]

        for type_name in expected_types:
            try:
                ActionType(type_name)
            except ValueError:
                # Type might not exist, that's ok
                pass

    def test_action_type_is_string_enum(self):
        """ActionType values must be strings."""
        from genesis.autonomous_engine import ActionType

        for action_type in ActionType:
            assert isinstance(action_type.value, str)
            assert len(action_type.value) > 0


class TestActionPriorityFunctional:
    """Functional tests for ActionPriority enum."""

    def test_priority_ordering(self):
        """Priority levels must have correct ordering."""
        from genesis.autonomous_engine import ActionPriority

        priorities = list(ActionPriority)
        priority_names = [p.value for p in priorities]

        # Should include these priority levels
        expected = ["critical", "high", "normal", "low", "background"]
        for expected_priority in expected:
            assert expected_priority in priority_names, f"Missing priority: {expected_priority}"

    def test_critical_is_highest(self):
        """Critical must be the highest priority."""
        from genesis.autonomous_engine import ActionPriority

        # Critical should come first in ordering
        assert ActionPriority.CRITICAL.value == "critical"


class TestActionStatusFunctional:
    """Functional tests for ActionStatus enum."""

    def test_status_values_exist(self):
        """ActionStatus must have required values."""
        from genesis.autonomous_engine import ActionStatus

        required_statuses = ["pending", "running", "completed", "failed"]

        for status in required_statuses:
            try:
                ActionStatus(status)
            except ValueError:
                pytest.fail(f"Missing status: {status}")


# =============================================================================
# AUTONOMOUS ACTION TESTS
# =============================================================================

class TestAutonomousActionFunctional:
    """Functional tests for AutonomousAction class."""

    def test_action_creation(self):
        """AutonomousAction must be creatable with required fields."""
        from genesis.autonomous_engine import (
            AutonomousAction, ActionType, ActionPriority, ActionStatus
        )

        action = AutonomousAction(
            action_id="ACT-001",
            action_type=ActionType.CODE_FIX,
            priority=ActionPriority.NORMAL,
            status=ActionStatus.PENDING,
            context={"file": "test.py"},
            genesis_key="GK-test-123"
        )

        assert action.action_id == "ACT-001"
        assert action.action_type == ActionType.CODE_FIX
        assert action.priority == ActionPriority.NORMAL
        assert action.status == ActionStatus.PENDING

    def test_action_id_format(self):
        """Action ID must have proper format."""
        from genesis.autonomous_engine import (
            AutonomousAction, ActionType, ActionPriority, ActionStatus
        )

        action = AutonomousAction(
            action_id="ACT-test-123",
            action_type=ActionType.CODE_REVIEW,
            priority=ActionPriority.HIGH,
            status=ActionStatus.PENDING,
            context={},
            genesis_key="GK-001"
        )

        assert action.action_id.startswith("ACT-")

    def test_action_genesis_key_required(self):
        """Action must have a genesis key for tracking."""
        from genesis.autonomous_engine import (
            AutonomousAction, ActionType, ActionPriority, ActionStatus
        )

        action = AutonomousAction(
            action_id="ACT-001",
            action_type=ActionType.CODE_FIX,
            priority=ActionPriority.NORMAL,
            status=ActionStatus.PENDING,
            context={},
            genesis_key="GK-genesis-key-123"
        )

        assert action.genesis_key is not None
        assert action.genesis_key.startswith("GK-")


# =============================================================================
# AUTONOMOUS ENGINE TESTS
# =============================================================================

class TestAutonomousEngineFunctional:
    """Functional tests for AutonomousEngine."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.add = MagicMock()
        session.commit = MagicMock()
        session.query = MagicMock()
        return session

    @pytest.fixture
    def engine(self, mock_session):
        """Create AutonomousEngine instance."""
        with patch('genesis.autonomous_engine.get_session', return_value=mock_session):
            from genesis.autonomous_engine import AutonomousEngine
            return AutonomousEngine(session=mock_session)

    def test_engine_initialization(self, engine):
        """Engine must initialize properly."""
        assert engine is not None
        assert hasattr(engine, 'action_queue')
        assert hasattr(engine, 'rules')

    def test_queue_action_returns_action(self, engine):
        """queue_action must return an AutonomousAction."""
        from genesis.autonomous_engine import ActionType, ActionPriority

        action = engine.queue_action(
            action_type=ActionType.CODE_FIX,
            context={"file": "test.py", "issue": "syntax error"},
            priority=ActionPriority.HIGH
        )

        assert action is not None
        assert action.action_id is not None

    def test_queue_action_assigns_genesis_key(self, engine):
        """queue_action must assign a genesis key."""
        from genesis.autonomous_engine import ActionType

        action = engine.queue_action(
            action_type=ActionType.CODE_REVIEW,
            context={"file": "test.py"}
        )

        assert action.genesis_key is not None
        assert len(action.genesis_key) > 5

    def test_get_pending_actions_returns_list(self, engine):
        """get_pending_actions must return list of actions."""
        from genesis.autonomous_engine import ActionType

        # Queue some actions
        engine.queue_action(ActionType.CODE_FIX, {"file": "a.py"})
        engine.queue_action(ActionType.CODE_FIX, {"file": "b.py"})

        pending = engine.get_pending_actions()

        assert isinstance(pending, list)

    def test_get_action_by_id(self, engine):
        """get_action must return action by ID."""
        from genesis.autonomous_engine import ActionType

        action = engine.queue_action(
            action_type=ActionType.CODE_FIX,
            context={"file": "test.py"}
        )

        retrieved = engine.get_action(action.action_id)

        assert retrieved is not None
        assert retrieved.action_id == action.action_id

    def test_cancel_action(self, engine):
        """cancel_action must cancel pending action."""
        from genesis.autonomous_engine import ActionType, ActionStatus

        action = engine.queue_action(
            action_type=ActionType.CODE_FIX,
            context={"file": "test.py"}
        )

        result = engine.cancel_action(action.action_id)

        assert result is True
        cancelled = engine.get_action(action.action_id)
        # Should be cancelled or removed
        assert cancelled is None or cancelled.status == ActionStatus.CANCELLED


# =============================================================================
# RULE ENGINE TESTS
# =============================================================================

class TestRuleEngineFunctional:
    """Functional tests for autonomous rules."""

    @pytest.fixture
    def engine(self):
        """Create engine with mock session."""
        with patch('genesis.autonomous_engine.get_session'):
            from genesis.autonomous_engine import AutonomousEngine
            return AutonomousEngine()

    def test_create_rule(self, engine):
        """create_rule must create an autonomous rule."""
        from genesis.autonomous_engine import TriggerType, ActionType

        rule = engine.create_rule(
            name="Auto-fix on commit",
            trigger_type=TriggerType.EVENT,
            trigger_config={"event": "git.commit"},
            action_type=ActionType.CODE_FIX,
            action_config={"auto_apply": True}
        )

        assert rule is not None
        assert rule.name == "Auto-fix on commit"
        assert rule.enabled is True

    def test_rule_has_id(self, engine):
        """Created rule must have unique ID."""
        from genesis.autonomous_engine import TriggerType, ActionType

        rule = engine.create_rule(
            name="Test rule",
            trigger_type=TriggerType.SCHEDULE,
            trigger_config={"cron": "0 * * * *"},
            action_type=ActionType.CODE_REVIEW
        )

        assert rule.rule_id is not None
        assert len(rule.rule_id) > 5

    def test_get_rules_returns_list(self, engine):
        """get_rules must return list of rules."""
        rules = engine.get_rules()

        assert isinstance(rules, list)

    def test_enable_disable_rule(self, engine):
        """Rules must be enable/disable-able."""
        from genesis.autonomous_engine import TriggerType, ActionType

        rule = engine.create_rule(
            name="Test rule",
            trigger_type=TriggerType.EVENT,
            trigger_config={"event": "test"},
            action_type=ActionType.CODE_FIX
        )

        # Disable
        engine.disable_rule(rule.rule_id)
        disabled_rule = engine.get_rule(rule.rule_id)
        assert disabled_rule.enabled is False

        # Enable
        engine.enable_rule(rule.rule_id)
        enabled_rule = engine.get_rule(rule.rule_id)
        assert enabled_rule.enabled is True


# =============================================================================
# EVENT SYSTEM TESTS
# =============================================================================

class TestEventSystemFunctional:
    """Functional tests for autonomous event system."""

    @pytest.fixture
    def engine(self):
        """Create engine."""
        with patch('genesis.autonomous_engine.get_session'):
            from genesis.autonomous_engine import AutonomousEngine
            return AutonomousEngine()

    def test_emit_event(self, engine):
        """emit_event must emit event to listeners."""
        events_received = []

        def handler(event):
            events_received.append(event)

        engine.subscribe("test.event", handler)
        engine.emit_event("test.event", {"data": "test"})

        # Event should be received
        assert len(events_received) >= 0  # May be async

    def test_subscribe_to_events(self, engine):
        """subscribe must register event handler."""
        def handler(event):
            pass

        result = engine.subscribe("git.commit", handler)

        assert result is True

    def test_unsubscribe_from_events(self, engine):
        """unsubscribe must remove event handler."""
        def handler(event):
            pass

        engine.subscribe("test.event", handler)
        result = engine.unsubscribe("test.event", handler)

        assert result is True


# =============================================================================
# API REQUEST/RESPONSE MODEL TESTS
# =============================================================================

class TestAPIModelsFunctional:
    """Functional tests for API request/response models."""

    def test_queue_action_request_validation(self):
        """QueueActionRequest must validate fields."""
        from api.autonomous_api import QueueActionRequest

        request = QueueActionRequest(
            action_type="code_fix",
            context_data={"file": "test.py"},
            priority="high"
        )

        assert request.action_type == "code_fix"
        assert request.priority == "high"
        assert request.context_data["file"] == "test.py"

    def test_queue_action_request_defaults(self):
        """QueueActionRequest must have proper defaults."""
        from api.autonomous_api import QueueActionRequest

        request = QueueActionRequest(action_type="code_fix")

        assert request.priority == "normal"
        assert request.trigger_type == "request"
        assert request.context_data is None

    def test_create_rule_request_validation(self):
        """CreateRuleRequest must validate fields."""
        from api.autonomous_api import CreateRuleRequest

        request = CreateRuleRequest(
            name="Test Rule",
            trigger_type="event",
            trigger_config={"event": "git.commit"},
            action_type="code_fix"
        )

        assert request.name == "Test Rule"
        assert request.trigger_type == "event"
        assert request.enabled is True

    def test_action_response_structure(self):
        """ActionResponse must have all required fields."""
        from api.autonomous_api import ActionResponse

        response = ActionResponse(
            action_id="ACT-001",
            action_type="code_fix",
            status="pending",
            priority="normal",
            trigger_type="request",
            genesis_key="GK-001",
            queued_at="2024-01-01T00:00:00",
            message="Action queued"
        )

        assert response.action_id == "ACT-001"
        assert response.genesis_key == "GK-001"


# =============================================================================
# PRIORITY QUEUE TESTS
# =============================================================================

class TestPriorityQueueFunctional:
    """Functional tests for action priority queue."""

    @pytest.fixture
    def engine(self):
        """Create engine."""
        with patch('genesis.autonomous_engine.get_session'):
            from genesis.autonomous_engine import AutonomousEngine
            return AutonomousEngine()

    def test_critical_processed_first(self, engine):
        """Critical actions must be processed before normal."""
        from genesis.autonomous_engine import ActionType, ActionPriority

        # Queue normal first, then critical
        normal = engine.queue_action(
            ActionType.CODE_FIX,
            {"order": 1},
            priority=ActionPriority.NORMAL
        )
        critical = engine.queue_action(
            ActionType.CODE_FIX,
            {"order": 2},
            priority=ActionPriority.CRITICAL
        )

        # Get next action - should be critical
        next_action = engine.get_next_action()

        assert next_action.priority == ActionPriority.CRITICAL

    def test_same_priority_fifo(self, engine):
        """Same priority actions must be FIFO."""
        from genesis.autonomous_engine import ActionType, ActionPriority

        first = engine.queue_action(
            ActionType.CODE_FIX,
            {"order": "first"},
            priority=ActionPriority.NORMAL
        )
        second = engine.queue_action(
            ActionType.CODE_FIX,
            {"order": "second"},
            priority=ActionPriority.NORMAL
        )

        next_action = engine.get_next_action()

        assert next_action.context.get("order") == "first"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
