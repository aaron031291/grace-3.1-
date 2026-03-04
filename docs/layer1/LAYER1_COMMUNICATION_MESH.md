# Layer 1 Communication Mesh Architecture

## Vision: Bidirectional Component Communication

All Layer 1 components should be able to **talk to each other** when needed, creating a **living, interconnected system** rather than isolated pipelines.

---

## Current State (Unidirectional Pipeline)

```
┌──────────────────────────────────────────────────────────┐
│              CURRENT: ONE-WAY PIPELINE                    │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Input → Genesis Key → Version Control → Librarian       │
│         → Memory Mesh → RAG → World Model                │
│                                                           │
│  Problem: No feedback, no cross-talk, no intelligence    │
└──────────────────────────────────────────────────────────┘
```

**Issues:**
- ❌ Genesis Keys can't query Memory Mesh
- ❌ Memory Mesh can't trigger Version Control
- ❌ Librarian can't request Learning Memory
- ❌ No component-to-component communication
- ❌ Each component works in isolation

---

## Proposed: Communication Mesh (Bidirectional)

```
┌────────────────────────────────────────────────────────────────┐
│         LAYER 1 COMMUNICATION MESH (Bidirectional)              │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│              ┌─────────────────────────────┐                   │
│              │   Message Bus/Event Router   │                   │
│              │   (Central Communication)    │                   │
│              └──────────────┬───────────────┘                   │
│                             │                                   │
│         ┌───────────────────┼───────────────────┐              │
│         │                   │                   │              │
│    ┌────▼────┐         ┌───▼────┐         ┌───▼────┐         │
│    │ Genesis │◄───────►│ Memory │◄───────►│Version │         │
│    │  Keys   │         │  Mesh  │         │Control │         │
│    └────┬────┘         └───┬────┘         └───┬────┘         │
│         │                  │                   │              │
│         │     ┌────────────┼────────────┐      │              │
│         │     │            │            │      │              │
│    ┌────▼────▼┐      ┌───▼────┐   ┌───▼─────▼┐              │
│    │ Librarian│◄────►│  RAG   │◄─►│ Learning │              │
│    │          │      │        │   │ Memory   │              │
│    └────┬─────┘      └───┬────┘   └─────┬────┘              │
│         │                │              │                    │
│         └────────────────┼──────────────┘                    │
│                          │                                   │
│                     ┌────▼────┐                              │
│                     │  World  │                              │
│                     │  Model  │                              │
│                     └─────────┘                              │
│                                                               │
│  ✅ Any component can message any other component           │
│  ✅ Bidirectional flow for intelligent coordination          │
│  ✅ Event-driven architecture                                │
└───────────────────────────────────────────────────────────────┘
```

---

## Communication Patterns

### 1. Request-Response
```
Memory Mesh → Genesis Keys: "Get user contribution history"
Genesis Keys → Memory Mesh: [list of learning examples]
```

### 2. Publish-Subscribe
```
Version Control: Publishes "new_commit" event
  ↓
Memory Mesh: Subscribes and creates snapshot
Librarian: Subscribes and re-categorizes
Genesis Keys: Subscribes and updates index
```

### 3. Command Pattern
```
Librarian: Sends "organize_learning_data" command
  ↓
Learning Memory: Executes organization
  ↓
Librarian: Receives completion notification
```

### 4. Event Stream
```
User provides correction
  ↓
Genesis Keys: Creates GK-learning-correction-xxx
  ↓
Memory Mesh: Ingests with trust scoring
  ↓
Learning Memory: Routes to episodic/procedural
  ↓
Version Control: Commits learning file
  ↓
Librarian: Categorizes by topic
  ↓
World Model: Updates knowledge
```

---

## Architecture Design

### Message Bus Implementation

```python
# backend/layer1/message_bus.py

from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages in Layer 1 mesh."""
    REQUEST = "request"              # Request-response pattern
    RESPONSE = "response"            # Response to request
    EVENT = "event"                  # Publish-subscribe pattern
    COMMAND = "command"              # Command pattern
    NOTIFICATION = "notification"    # One-way notification


class ComponentType(Enum):
    """Layer 1 components."""
    GENESIS_KEYS = "genesis_keys"
    VERSION_CONTROL = "version_control"
    LIBRARIAN = "librarian"
    MEMORY_MESH = "memory_mesh"
    LEARNING_MEMORY = "learning_memory"
    RAG = "rag"
    WORLD_MODEL = "world_model"


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
    correlation_id: Optional[str] = None  # For request-response
    requires_response: bool = False


class Layer1MessageBus:
    """
    Central message bus for Layer 1 component communication.

    Enables bidirectional, event-driven communication between
    all Layer 1 components.
    """

    def __init__(self):
        # Subscribers by topic
        self._subscribers: Dict[str, List[Callable]] = {}

        # Request handlers by component and topic
        self._request_handlers: Dict[ComponentType, Dict[str, Callable]] = {}

        # Pending requests (for request-response)
        self._pending_requests: Dict[str, asyncio.Future] = {}

        # Message history (for debugging)
        self._message_history: List[Message] = []

        # Component registry
        self._registered_components: Dict[ComponentType, Any] = {}

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
        logger.info(f"[MESSAGE-BUS] Registered component: {component_type.value}")

    def get_component(self, component_type: ComponentType) -> Optional[Any]:
        """Get registered component instance."""
        return self._registered_components.get(component_type)

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
        logger.info(f"[MESSAGE-BUS] New subscriber for topic: {topic}")

    async def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        from_component: ComponentType
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
            timestamp=datetime.utcnow()
        )

        self._message_history.append(message)

        if topic in self._subscribers:
            logger.info(
                f"[MESSAGE-BUS] Publishing to {len(self._subscribers[topic])} "
                f"subscribers: {topic}"
            )

            # Call all subscribers
            for handler in self._subscribers[topic]:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"[MESSAGE-BUS] Subscriber error: {e}")

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
            f"[MESSAGE-BUS] Registered request handler: "
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

        self._message_history.append(message)

        # Create future for response
        future = asyncio.Future()
        self._pending_requests[message_id] = future

        # Get handler
        if (to_component in self._request_handlers and
            topic in self._request_handlers[to_component]):

            handler = self._request_handlers[to_component][topic]

            logger.info(
                f"[MESSAGE-BUS] Request {from_component.value} → "
                f"{to_component.value}: {topic}"
            )

            try:
                # Execute handler
                response_payload = await handler(message)

                # Send response
                await self._send_response(message_id, response_payload, to_component)

            except Exception as e:
                logger.error(f"[MESSAGE-BUS] Request handler error: {e}")
                future.set_exception(e)
        else:
            error = f"No handler for {to_component.value}/{topic}"
            logger.error(f"[MESSAGE-BUS] {error}")
            future.set_exception(ValueError(error))

        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.error(f"[MESSAGE-BUS] Request timeout: {topic}")
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

            self._message_history.append(response)
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

        self._message_history.append(message)

        logger.info(
            f"[MESSAGE-BUS] Command {from_component.value} → "
            f"{to_component.value}: {command}"
        )

        # Execute command handler
        if (to_component in self._request_handlers and
            command in self._request_handlers[to_component]):

            handler = self._request_handlers[to_component][command]
            await handler(message)

    # ================================================================
    # UTILITIES
    # ================================================================

    def _generate_message_id(self) -> str:
        """Generate unique message ID."""
        import uuid
        return f"msg-{uuid.uuid4().hex[:12]}"

    def get_message_history(
        self,
        component: Optional[ComponentType] = None,
        limit: int = 100
    ) -> List[Message]:
        """Get message history, optionally filtered by component."""
        if component:
            history = [
                m for m in self._message_history
                if m.from_component == component or m.to_component == component
            ]
        else:
            history = self._message_history

        return history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics."""
        return {
            "total_messages": len(self._message_history),
            "registered_components": len(self._registered_components),
            "subscribers": {
                topic: len(handlers)
                for topic, handlers in self._subscribers.items()
            },
            "request_handlers": {
                component.value: list(handlers.keys())
                for component, handlers in self._request_handlers.items()
            },
            "pending_requests": len(self._pending_requests)
        }


# Global message bus instance
_message_bus: Optional[Layer1MessageBus] = None


def get_message_bus() -> Layer1MessageBus:
    """Get or create global message bus instance."""
    global _message_bus
    if _message_bus is None:
        _message_bus = Layer1MessageBus()
    return _message_bus
```

---

## Example Usage Scenarios

### Scenario 1: Memory Mesh Queries Genesis Keys

```python
# Memory Mesh wants user's learning history

from layer1.message_bus import get_message_bus, ComponentType

bus = get_message_bus()

# Memory Mesh requests user contributions
response = await bus.request(
    to_component=ComponentType.GENESIS_KEYS,
    topic="get_user_contributions",
    payload={"user_id": "GU-user123"},
    from_component=ComponentType.MEMORY_MESH
)

# Response contains all user's Genesis Keys
contributions = response["contributions"]
# [
#   {"genesis_key_id": "GK-learning-correction-abc", "trust_score": 0.91},
#   {"genesis_key_id": "GK-learning-feedback-def", "trust_score": 0.88}
# ]
```

### Scenario 2: Version Control Triggers Memory Mesh Snapshot

```python
# When new commit happens, create memory mesh snapshot

# Version Control publishes event
await bus.publish(
    topic="version_control.new_commit",
    payload={
        "commit_id": "VER-abc123",
        "files_changed": 15,
        "timestamp": datetime.utcnow()
    },
    from_component=ComponentType.VERSION_CONTROL
)

# Memory Mesh subscribes to this event
bus.subscribe(
    topic="version_control.new_commit",
    handler=memory_mesh.on_new_commit
)

# Handler in Memory Mesh:
async def on_new_commit(message):
    # Automatically create snapshot on every commit
    await create_memory_mesh_snapshot(
        session=session,
        kb_path=kb_path,
        save=True
    )

    logger.info(f"Snapshot created for commit: {message.payload['commit_id']}")
```

### Scenario 3: Librarian Requests Learning Memory Organization

```python
# Librarian wants to reorganize learning data by topic

response = await bus.request(
    to_component=ComponentType.LEARNING_MEMORY,
    topic="get_topics_summary",
    payload={"min_trust_score": 0.7},
    from_component=ComponentType.LIBRARIAN
)

# Response contains topic statistics
topics = response["topics"]
# {
#   "geography": {"count": 45, "avg_trust": 0.89},
#   "programming": {"count": 120, "avg_trust": 0.85}
# }

# Librarian uses this to organize folders
await bus.send_command(
    to_component=ComponentType.LEARNING_MEMORY,
    command="organize_by_topic",
    payload={"topics": topics},
    from_component=ComponentType.LIBRARIAN
)
```

### Scenario 4: Cross-Component Learning Pipeline

```python
# Complete bidirectional learning flow

# 1. User provides feedback
user_input = {
    "user_id": "GU-user123",
    "feedback": "Capital is Canberra, not Sydney",
    "context": {"question": "Australian capital"}
}

# 2. Genesis Keys creates GK and publishes event
genesis_key_id = create_genesis_key(user_input)

await bus.publish(
    topic="genesis_keys.new_learning_key",
    payload={
        "genesis_key_id": genesis_key_id,
        "user_id": user_input["user_id"]
    },
    from_component=ComponentType.GENESIS_KEYS
)

# 3. Memory Mesh subscribes and ingests
# (Handler automatically trust-scores and routes to episodic/procedural)

# 4. Version Control subscribes and commits
# (Handler automatically commits learning file to git)

# 5. Librarian subscribes and categorizes
# (Handler automatically categorizes by topic: "geography")

# 6. World Model subscribes and updates knowledge
# (Handler automatically updates knowledge graph)

# All happens automatically through event subscriptions!
```

---

## Recommended Communication Patterns

### Genesis Keys ↔ Memory Mesh

**Genesis Keys → Memory Mesh:**
- Request: "create_learning_example" (with Genesis Key attached)
- Response: learning_example_id + trust_score

**Memory Mesh → Genesis Keys:**
- Request: "get_user_contributions" (for user_id)
- Response: List of all user's learning Genesis Keys

### Memory Mesh ↔ Version Control

**Memory Mesh → Version Control:**
- Event: "memory_mesh.snapshot_created"
- Payload: snapshot_path, statistics

**Version Control → Memory Mesh:**
- Event: "version_control.new_commit"
- Trigger: Memory Mesh creates snapshot

### Librarian ↔ Learning Memory

**Librarian → Learning Memory:**
- Request: "get_topics_summary"
- Response: Topic statistics for organization

**Learning Memory → Librarian:**
- Event: "learning_memory.new_pattern_extracted"
- Trigger: Librarian recategorizes related content

### RAG ↔ Memory Mesh

**RAG → Memory Mesh:**
- Request: "get_relevant_procedures"
- Response: Procedural memories for query

**Memory Mesh → RAG:**
- Event: "memory_mesh.new_procedure_created"
- Trigger: RAG re-indexes procedures

---

## Implementation Roadmap

### Phase 1: Core Message Bus ✅
```python
# backend/layer1/message_bus.py
- Basic pub-sub
- Request-response
- Component registration
```

### Phase 2: Component Integration
```python
# backend/layer1/components/genesis_keys_connector.py
# backend/layer1/components/memory_mesh_connector.py
# backend/layer1/components/version_control_connector.py
# backend/layer1/components/librarian_connector.py

Each component gets connector class that:
- Registers with message bus
- Subscribes to relevant topics
- Handles requests
- Publishes events
```

### Phase 3: API Endpoints
```python
# POST /layer1/message-bus/publish
# POST /layer1/message-bus/request
# GET /layer1/message-bus/stats
# GET /layer1/message-bus/history
```

### Phase 4: Monitoring Dashboard
```
Real-time view of:
- Active messages
- Component communication
- Event flows
- Request/response patterns
```

---

## Benefits

### 1. Intelligent Coordination
Components can coordinate without hardcoded dependencies

### 2. Event-Driven Architecture
Decoupled, reactive system that responds to changes

### 3. Bidirectional Flow
Information flows both ways, creating feedback loops

### 4. Scalability
Easy to add new components and communication patterns

### 5. Debugging
Complete message history for troubleshooting

### 6. Flexibility
Change communication patterns without changing components

---

## Summary

**YES - Create a Layer 1 Communication Mesh!**

This design enables:
✅ Bidirectional component communication
✅ Event-driven architecture
✅ Request-response patterns
✅ Publish-subscribe for events
✅ Command pattern for actions
✅ Complete message history
✅ Component decoupling
✅ Intelligent coordination

**Next Step**: Implement the message bus and start connecting components. Want me to code the full implementation?
