"""
Layer 1 Message Bus - Bidirectional Component Communication

Enables all Layer 1 components to communicate, coordinate, and trigger
autonomous actions intelligently.

Components:
- Genesis Keys
- Memory Mesh
- Learning Memory
- RAG (Retrieval)
- Ingestion
- World Model
- Autonomous Learning
- LLM Orchestration
- Version Control
- Librarian
"""

from typing import Dict, Any, Callable, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import logging
import uuid
import json

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages in Layer 1 mesh."""
    REQUEST = "request"              # Request-response pattern
    RESPONSE = "response"            # Response to request
    EVENT = "event"                  # Publish-subscribe pattern
    COMMAND = "command"              # Command pattern
    NOTIFICATION = "notification"    # One-way notification
    TRIGGER = "trigger"              # Autonomous action trigger


class ComponentType(Enum):
    """Layer 1 components."""
    GENESIS_KEYS = "genesis_keys"
    VERSION_CONTROL = "version_control"
    LIBRARIAN = "librarian"
    MEMORY_MESH = "memory_mesh"
    LEARNING_MEMORY = "learning_memory"
    RAG = "rag"
    INGESTION = "ingestion"
    WORLD_MODEL = "world_model"
    AUTONOMOUS_LEARNING = "autonomous_learning"
    LLM_ORCHESTRATION = "llm_orchestration"
    COGNITIVE_ENGINE = "cognitive_engine"


@dataclass
class Message:
    """Message in Layer 1 communication mesh."""
    message_id: str
    message_type: MessageType
    from_component: ComponentType
    to_component: Optional[ComponentType]  # None = broadcast
    topic: str
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None
    requires_response: bool = False
    priority: int = 5  # 1-10, higher = more urgent
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AutonomousAction:
    """Autonomous action triggered by events."""
    action_id: str
    trigger_event: str
    conditions: List[Callable]  # Conditions that must be met
    action: Callable  # Action to execute
    component: ComponentType
    description: str
    enabled: bool = True


class Layer1MessageBus:
    """
    Central message bus for Layer 1 component communication.

    Enables:
    - Bidirectional communication
    - Event-driven architecture
    - Autonomous action triggering
    - Request-response patterns
    - Publish-subscribe
    """

    def __init__(self):
        # Subscribers by topic
        self._subscribers: Dict[str, List[Callable]] = {}

        # Request handlers by component and topic
        self._request_handlers: Dict[ComponentType, Dict[str, Callable]] = {}

        # Pending requests (for request-response)
        self._pending_requests: Dict[str, asyncio.Future] = {}

        # Message history (for debugging/audit)
        self._message_history: List[Message] = []
        self._max_history = 1000  # Keep last 1000 messages

        # Component registry
        self._registered_components: Dict[ComponentType, Any] = {}

        # Autonomous actions
        self._autonomous_actions: Dict[str, AutonomousAction] = {}

        # Message queue for priority handling
        self._message_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()

        # Stats
        self._stats = {
            "total_messages": 0,
            "requests": 0,
            "events": 0,
            "commands": 0,
            "autonomous_actions_triggered": 0
        }

    # ================================================================
    # COMPONENT REGISTRATION
    # ================================================================

    def register_component(
        self,
        component_type: ComponentType,
        component_instance: Any
    ):
        """Register a component with the message bus."""
        self._registered_components[component_type] = component_instance
        logger.info(f"[MESSAGE-BUS] ✓ Registered: {component_type.value}")

    def get_component(self, component_type: ComponentType) -> Optional[Any]:
        """Get registered component instance."""
        return self._registered_components.get(component_type)

    # ================================================================
    # AUTONOMOUS ACTIONS
    # ================================================================

    def register_autonomous_action(
        self,
        trigger_event: str,
        action: Callable,
        component: ComponentType,
        description: str,
        conditions: Optional[List[Callable]] = None
    ) -> str:
        """
        Register autonomous action that triggers on events.

        Args:
            trigger_event: Event topic to listen for
            action: Async function to execute
            component: Component that owns this action
            description: Human-readable description
            conditions: Optional conditions that must be met

        Returns:
            Action ID
        """
        action_id = f"action-{uuid.uuid4().hex[:12]}"

        autonomous_action = AutonomousAction(
            action_id=action_id,
            trigger_event=trigger_event,
            conditions=conditions or [],
            action=action,
            component=component,
            description=description
        )

        self._autonomous_actions[action_id] = autonomous_action

        # Auto-subscribe to trigger event
        self.subscribe(trigger_event, self._create_action_handler(autonomous_action))

        logger.info(
            f"[MESSAGE-BUS] ⭐ Autonomous action registered: "
            f"{component.value} → {description} (trigger: {trigger_event})"
        )

        return action_id

    def _create_action_handler(self, autonomous_action: AutonomousAction) -> Callable:
        """Create handler for autonomous action."""
        async def handler(message: Message):
            if not autonomous_action.enabled:
                return

            # Check conditions
            try:
                conditions_met = all(
                    condition(message) for condition in autonomous_action.conditions
                )
            except Exception as e:
                logger.error(f"[MESSAGE-BUS] Condition check failed: {e}")
                return

            if not conditions_met:
                logger.debug(
                    f"[MESSAGE-BUS] Conditions not met for: "
                    f"{autonomous_action.description}"
                )
                return

            # Execute autonomous action
            logger.info(
                f"[MESSAGE-BUS] 🤖 Executing autonomous action: "
                f"{autonomous_action.description}"
            )

            try:
                await autonomous_action.action(message)
                self._stats["autonomous_actions_triggered"] += 1
            except Exception as e:
                logger.error(
                    f"[MESSAGE-BUS] Autonomous action failed: "
                    f"{autonomous_action.description} - {e}"
                )

        return handler

    # ================================================================
    # PUBLISH-SUBSCRIBE
    # ================================================================

    def subscribe(self, topic: str, handler: Callable):
        """
        Subscribe to a topic.

        Args:
            topic: Topic name (e.g., "learning.new_example")
            handler: Async function to call when message published
        """
        if topic not in self._subscribers:
            self._subscribers[topic] = []

        self._subscribers[topic].append(handler)
        logger.info(f"[MESSAGE-BUS] 📡 Subscribed to: {topic}")

    async def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        from_component: ComponentType,
        priority: int = 5
    ):
        """
        Publish message to topic.

        All subscribers will receive the message.
        """
        message = Message(
            message_id=self._generate_message_id(),
            message_type=MessageType.EVENT,
            from_component=from_component,
            to_component=None,  # Broadcast
            topic=topic,
            payload=payload,
            timestamp=datetime.utcnow(),
            priority=priority
        )

        self._add_to_history(message)
        self._stats["total_messages"] += 1
        self._stats["events"] += 1

        if topic in self._subscribers:
            logger.info(
                f"[MESSAGE-BUS] 📢 Publishing: {topic} "
                f"({len(self._subscribers[topic])} subscribers)"
            )

            # Call all subscribers
            tasks = []
            for handler in self._subscribers[topic]:
                tasks.append(self._safe_call_handler(handler, message))

            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_call_handler(self, handler: Callable, message: Message):
        """Safely call handler with error handling."""
        try:
            await handler(message)
        except Exception as e:
            logger.error(f"[MESSAGE-BUS] Handler error: {e}", exc_info=True)

    # ================================================================
    # REQUEST-RESPONSE
    # ================================================================

    def register_request_handler(
        self,
        component: ComponentType,
        topic: str,
        handler: Callable
    ):
        """
        Register handler for requests to a component.

        Args:
            component: Component that handles requests
            topic: Request topic (e.g., "get_user_contributions")
            handler: Async function that returns response
        """
        if component not in self._request_handlers:
            self._request_handlers[component] = {}

        self._request_handlers[component][topic] = handler
        logger.info(
            f"[MESSAGE-BUS] 🔧 Request handler: "
            f"{component.value}/{topic}"
        )

    async def request(
        self,
        to_component: ComponentType,
        topic: str,
        payload: Dict[str, Any],
        from_component: ComponentType,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Send request and wait for response.

        Args:
            to_component: Component to send request to
            topic: Request topic
            payload: Request data
            from_component: Requesting component
            timeout: Timeout in seconds

        Returns:
            Response payload
        """
        message_id = self._generate_message_id()

        message = Message(
            message_id=message_id,
            message_type=MessageType.REQUEST,
            from_component=from_component,
            to_component=to_component,
            topic=topic,
            payload=payload,
            timestamp=datetime.utcnow(),
            correlation_id=message_id,
            requires_response=True
        )

        self._add_to_history(message)
        self._stats["total_messages"] += 1
        self._stats["requests"] += 1

        # Create future for response
        future = asyncio.Future()
        self._pending_requests[message_id] = future

        # Get handler
        if (to_component in self._request_handlers and
            topic in self._request_handlers[to_component]):

            handler = self._request_handlers[to_component][topic]

            logger.info(
                f"[MESSAGE-BUS] 💬 Request: {from_component.value} → "
                f"{to_component.value}/{topic}"
            )

            try:
                # Execute handler
                response_payload = await handler(message)

                # Send response
                await self._send_response(message_id, response_payload, to_component)

            except Exception as e:
                logger.error(f"[MESSAGE-BUS] Request handler error: {e}")
                if message_id in self._pending_requests:
                    self._pending_requests[message_id].set_exception(e)
        else:
            error = f"No handler for {to_component.value}/{topic}"
            logger.error(f"[MESSAGE-BUS] {error}")
            if message_id in self._pending_requests:
                self._pending_requests[message_id].set_exception(ValueError(error))

        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.error(f"[MESSAGE-BUS] Request timeout: {topic}")
            if message_id in self._pending_requests:
                del self._pending_requests[message_id]
            raise TimeoutError(f"Request timeout: {topic}")

    async def _send_response(
        self,
        correlation_id: str,
        payload: Dict[str, Any],
        from_component: ComponentType
    ):
        """Send response to pending request."""
        if correlation_id in self._pending_requests:
            future = self._pending_requests[correlation_id]

            response = Message(
                message_id=self._generate_message_id(),
                message_type=MessageType.RESPONSE,
                from_component=from_component,
                to_component=None,
                topic="response",
                payload=payload,
                timestamp=datetime.utcnow(),
                correlation_id=correlation_id
            )

            self._add_to_history(response)
            future.set_result(payload)

            del self._pending_requests[correlation_id]

    # ================================================================
    # COMMANDS
    # ================================================================

    async def send_command(
        self,
        to_component: ComponentType,
        command: str,
        payload: Dict[str, Any],
        from_component: ComponentType
    ):
        """
        Send command to component (no response expected).

        Args:
            to_component: Target component
            command: Command name
            payload: Command data
            from_component: Sending component
        """
        message = Message(
            message_id=self._generate_message_id(),
            message_type=MessageType.COMMAND,
            from_component=from_component,
            to_component=to_component,
            topic=command,
            payload=payload,
            timestamp=datetime.utcnow()
        )

        self._add_to_history(message)
        self._stats["total_messages"] += 1
        self._stats["commands"] += 1

        logger.info(
            f"[MESSAGE-BUS] ⚡ Command: {from_component.value} → "
            f"{to_component.value}/{command}"
        )

        # Execute command handler
        if (to_component in self._request_handlers and
            command in self._request_handlers[to_component]):

            handler = self._request_handlers[to_component][command]
            await self._safe_call_handler(handler, message)

    # ================================================================
    # TRIGGERS (Autonomous)
    # ================================================================

    async def trigger(
        self,
        trigger_name: str,
        payload: Dict[str, Any],
        from_component: ComponentType
    ):
        """
        Trigger autonomous actions.

        Similar to publish but specifically for autonomous workflows.
        """
        await self.publish(
            topic=f"trigger.{trigger_name}",
            payload=payload,
            from_component=from_component,
            priority=8  # Higher priority for triggers
        )

    # ================================================================
    # UTILITIES
    # ================================================================

    def _generate_message_id(self) -> str:
        """Generate unique message ID."""
        return f"msg-{uuid.uuid4().hex[:12]}"

    def _add_to_history(self, message: Message):
        """Add message to history with size limit."""
        self._message_history.append(message)

        # Keep only last N messages
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history:]

    def get_message_history(
        self,
        component: Optional[ComponentType] = None,
        message_type: Optional[MessageType] = None,
        limit: int = 100
    ) -> List[Message]:
        """Get message history with optional filters."""
        history = self._message_history

        if component:
            history = [
                m for m in history
                if m.from_component == component or m.to_component == component
            ]

        if message_type:
            history = [m for m in history if m.message_type == message_type]

        return history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics."""
        return {
            **self._stats,
            "registered_components": len(self._registered_components),
            "components": [c.value for c in self._registered_components.keys()],
            "subscribers": {
                topic: len(handlers)
                for topic, handlers in self._subscribers.items()
            },
            "request_handlers": {
                component.value: list(handlers.keys())
                for component, handlers in self._request_handlers.items()
            },
            "autonomous_actions": len(self._autonomous_actions),
            "pending_requests": len(self._pending_requests)
        }

    def get_autonomous_actions(self) -> List[Dict[str, Any]]:
        """Get list of registered autonomous actions."""
        return [
            {
                "action_id": action.action_id,
                "component": action.component.value,
                "trigger_event": action.trigger_event,
                "description": action.description,
                "enabled": action.enabled
            }
            for action in self._autonomous_actions.values()
        ]

    def enable_autonomous_action(self, action_id: str):
        """Enable autonomous action."""
        if action_id in self._autonomous_actions:
            self._autonomous_actions[action_id].enabled = True
            logger.info(f"[MESSAGE-BUS] ✓ Enabled action: {action_id}")

    def disable_autonomous_action(self, action_id: str):
        """Disable autonomous action."""
        if action_id in self._autonomous_actions:
            self._autonomous_actions[action_id].enabled = False
            logger.info(f"[MESSAGE-BUS] ✗ Disabled action: {action_id}")


# Global message bus instance
_message_bus: Optional[Layer1MessageBus] = None


def get_message_bus() -> Layer1MessageBus:
    """Get or create global message bus instance."""
    global _message_bus
    if _message_bus is None:
        _message_bus = Layer1MessageBus()
        logger.info("[MESSAGE-BUS] 🚀 Initialized Layer 1 Message Bus")
    return _message_bus


def reset_message_bus():
    """Reset message bus (for testing)."""
    global _message_bus
    _message_bus = None
