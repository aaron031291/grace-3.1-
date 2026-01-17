import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import weakref

logger = logging.getLogger(__name__)

class EventType(str, Enum):
    """Types of real-time events."""
    # Diagnostic events
    CYCLE_STARTED = "cycle_started"
    CYCLE_COMPLETED = "cycle_completed"
    CYCLE_FAILED = "cycle_failed"

    # Health events
    HEALTH_UPDATE = "health_update"
    HEALTH_DEGRADED = "health_degraded"
    HEALTH_CRITICAL = "health_critical"
    HEALTH_RECOVERED = "health_recovered"

    # Alert events
    ALERT_CREATED = "alert_created"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    AVN_TRIGGERED = "avn_triggered"
    AVM_STATUS_CHANGE = "avm_status_change"

    # Action events
    HEALING_STARTED = "healing_started"
    HEALING_COMPLETED = "healing_completed"
    HEALING_FAILED = "healing_failed"
    FREEZE_ACTIVATED = "freeze_activated"
    FREEZE_DEACTIVATED = "freeze_deactivated"

    # Sensor events
    SENSOR_DATA = "sensor_data"
    ANOMALY_DETECTED = "anomaly_detected"
    PATTERN_DETECTED = "pattern_detected"

    # System events
    ENGINE_STARTED = "engine_started"
    ENGINE_STOPPED = "engine_stopped"
    HEARTBEAT = "heartbeat"
    CONNECTION_STATUS = "connection_status"


@dataclass
class RealtimeEvent:
    """A real-time event to broadcast."""
    event_id: str
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "diagnostic_machine"
    priority: str = "normal"  # low, normal, high, critical

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "priority": self.priority,
        })


@dataclass
class ClientInfo:
    """Information about a connected WebSocket client."""
    client_id: str
    websocket: WebSocket
    connected_at: datetime = field(default_factory=datetime.utcnow)
    subscriptions: Set[str] = field(default_factory=set)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0


class ConnectionManager:
    """
    Manages WebSocket connections for real-time diagnostic updates.

    Features:
    - Multiple concurrent clients
    - Subscription-based filtering
    - Automatic heartbeat
    - Graceful disconnection handling
    """

    def __init__(self, heartbeat_interval: int = 30):
        self._clients: Dict[str, ClientInfo] = {}
        self._event_counter = 0
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._event_history: List[RealtimeEvent] = []
        self._max_history = 100
        self._callbacks: Dict[EventType, List[Callable]] = {}

    @property
    def client_count(self) -> int:
        """Get number of connected clients."""
        return len(self._clients)

    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        """Accept a new WebSocket connection."""
        await websocket.accept()

        if not client_id:
            client_id = f"client-{len(self._clients) + 1:04d}-{datetime.utcnow().timestamp():.0f}"

        client = ClientInfo(
            client_id=client_id,
            websocket=websocket,
            subscriptions={"all"},  # Subscribe to all by default
        )

        self._clients[client_id] = client

        logger.info(f"WebSocket client connected: {client_id}")

        # Send connection confirmation
        await self._send_to_client(client_id, RealtimeEvent(
            event_id=self._next_event_id(),
            event_type=EventType.CONNECTION_STATUS,
            data={
                "status": "connected",
                "client_id": client_id,
                "subscriptions": list(client.subscriptions),
            }
        ))

        # Start heartbeat if this is first client
        if len(self._clients) == 1 and self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        return client_id

    async def disconnect(self, client_id: str):
        """Handle client disconnection."""
        if client_id in self._clients:
            del self._clients[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")

        # Stop heartbeat if no clients
        if len(self._clients) == 0 and self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    async def subscribe(self, client_id: str, topics: List[str]):
        """Subscribe client to specific event types."""
        if client_id in self._clients:
            self._clients[client_id].subscriptions.update(topics)
            await self._send_to_client(client_id, RealtimeEvent(
                event_id=self._next_event_id(),
                event_type=EventType.CONNECTION_STATUS,
                data={
                    "status": "subscribed",
                    "topics": topics,
                    "subscriptions": list(self._clients[client_id].subscriptions),
                }
            ))

    async def unsubscribe(self, client_id: str, topics: List[str]):
        """Unsubscribe client from specific event types."""
        if client_id in self._clients:
            self._clients[client_id].subscriptions.difference_update(topics)

    async def broadcast(self, event: RealtimeEvent):
        """Broadcast event to all subscribed clients."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Fire local callbacks
        if event.event_type in self._callbacks:
            for callback in self._callbacks[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

        disconnected = []
        for client_id, client in self._clients.items():
            # Check if client is subscribed
            if "all" in client.subscriptions or event.event_type.value in client.subscriptions:
                try:
                    await self._send_to_client(client_id, event)
                except Exception as e:
                    logger.warning(f"Failed to send to {client_id}: {e}")
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)

    async def _send_to_client(self, client_id: str, event: RealtimeEvent):
        """Send event to specific client."""
        if client_id not in self._clients:
            return

        client = self._clients[client_id]
        try:
            if client.websocket.client_state == WebSocketState.CONNECTED:
                await client.websocket.send_text(event.to_json())
                client.message_count += 1
        except Exception as e:
            logger.warning(f"Send to {client_id} failed: {e}")
            raise

    async def _heartbeat_loop(self):
        """Send periodic heartbeat to all clients."""
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)

                heartbeat_event = RealtimeEvent(
                    event_id=self._next_event_id(),
                    event_type=EventType.HEARTBEAT,
                    data={
                        "timestamp": datetime.utcnow().isoformat(),
                        "clients": self.client_count,
                    },
                    priority="low"
                )

                await self.broadcast(heartbeat_event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    def _next_event_id(self) -> str:
        """Generate next event ID."""
        self._event_counter += 1
        return f"EVT-{self._event_counter:08d}"

    def on_event(self, event_type: EventType, callback: Callable):
        """Register callback for event type."""
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    def get_client_info(self, client_id: str) -> Optional[Dict]:
        """Get info about specific client."""
        if client_id not in self._clients:
            return None

        client = self._clients[client_id]
        return {
            "client_id": client.client_id,
            "connected_at": client.connected_at.isoformat(),
            "subscriptions": list(client.subscriptions),
            "message_count": client.message_count,
        }

    def get_all_clients(self) -> List[Dict]:
        """Get info about all clients."""
        return [self.get_client_info(cid) for cid in self._clients]

    def get_event_history(self, limit: int = 50) -> List[Dict]:
        """Get recent event history."""
        return [
            {
                "event_id": e.event_id,
                "event_type": e.event_type.value,
                "timestamp": e.timestamp.isoformat(),
                "priority": e.priority,
            }
            for e in self._event_history[-limit:]
        ]


class DiagnosticEventEmitter:
    """
    Emits diagnostic events to WebSocket clients.

    Integrates with DiagnosticEngine to broadcast:
    - Cycle completions
    - Health changes
    - Alerts
    - Healing actions
    """

    def __init__(self, connection_manager: ConnectionManager = None):
        self.manager = connection_manager or ConnectionManager()
        self._previous_health_status: Optional[str] = None

    async def emit_cycle_started(self, cycle_id: str):
        """Emit cycle started event."""
        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=EventType.CYCLE_STARTED,
            data={"cycle_id": cycle_id},
        ))

    async def emit_cycle_completed(self, cycle_data: Dict):
        """Emit cycle completed event with full data."""
        # Check for health status changes
        health_status = cycle_data.get('health_status', 'unknown')
        if self._previous_health_status and health_status != self._previous_health_status:
            await self._emit_health_change(self._previous_health_status, health_status, cycle_data)

        self._previous_health_status = health_status

        # Determine priority based on health
        priority = "normal"
        if health_status == "critical":
            priority = "critical"
        elif health_status == "degraded":
            priority = "high"

        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=EventType.CYCLE_COMPLETED,
            data=cycle_data,
            priority=priority,
        ))

    async def emit_cycle_failed(self, cycle_id: str, error: str):
        """Emit cycle failed event."""
        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=EventType.CYCLE_FAILED,
            data={"cycle_id": cycle_id, "error": error},
            priority="high",
        ))

    async def _emit_health_change(self, previous: str, current: str, cycle_data: Dict):
        """Emit health status change event."""
        event_type = EventType.HEALTH_UPDATE
        priority = "normal"

        if current == "critical":
            event_type = EventType.HEALTH_CRITICAL
            priority = "critical"
        elif current == "degraded":
            event_type = EventType.HEALTH_DEGRADED
            priority = "high"
        elif previous in ["critical", "degraded"] and current == "healthy":
            event_type = EventType.HEALTH_RECOVERED
            priority = "high"

        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=event_type,
            data={
                "previous_status": previous,
                "current_status": current,
                "health_score": cycle_data.get('health_score', 0),
            },
            priority=priority,
        ))

    async def emit_alert(self, alert_data: Dict):
        """Emit alert event."""
        priority = alert_data.get('severity', 'medium')
        if priority == 'critical':
            priority = "critical"
        elif priority in ['high', 'warning']:
            priority = "high"
        else:
            priority = "normal"

        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=EventType.ALERT_CREATED,
            data=alert_data,
            priority=priority,
        ))

    async def emit_avn_triggered(self, avn_data: Dict):
        """Emit AVN triggered event."""
        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=EventType.AVN_TRIGGERED,
            data=avn_data,
            priority="high",
        ))

    async def emit_avm_status(self, avm_data: Dict):
        """Emit AVM status change event."""
        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=EventType.AVM_STATUS_CHANGE,
            data=avm_data,
        ))

    async def emit_healing_started(self, healing_id: str, action_name: str, target: str):
        """Emit healing started event."""
        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=EventType.HEALING_STARTED,
            data={
                "healing_id": healing_id,
                "action_name": action_name,
                "target": target,
            },
        ))

    async def emit_healing_completed(self, healing_id: str, success: bool, details: Dict = None):
        """Emit healing completed event."""
        event_type = EventType.HEALING_COMPLETED if success else EventType.HEALING_FAILED

        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=event_type,
            data={
                "healing_id": healing_id,
                "success": success,
                "details": details or {},
            },
            priority="normal" if success else "high",
        ))

    async def emit_freeze(self, reason: str, components: List[str]):
        """Emit system freeze event."""
        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=EventType.FREEZE_ACTIVATED,
            data={
                "reason": reason,
                "affected_components": components,
            },
            priority="critical",
        ))

    async def emit_anomaly(self, anomaly_data: Dict):
        """Emit anomaly detected event."""
        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=EventType.ANOMALY_DETECTED,
            data=anomaly_data,
            priority="high" if anomaly_data.get('severity', 0) > 0.7 else "normal",
        ))

    async def emit_pattern(self, pattern_data: Dict):
        """Emit pattern detected event."""
        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=EventType.PATTERN_DETECTED,
            data=pattern_data,
        ))

    async def emit_sensor_data(self, sensor_summary: Dict):
        """Emit sensor data summary event."""
        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=EventType.SENSOR_DATA,
            data=sensor_summary,
            priority="low",
        ))

    async def emit_engine_started(self, config: Dict):
        """Emit engine started event."""
        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=EventType.ENGINE_STARTED,
            data=config,
        ))

    async def emit_engine_stopped(self, stats: Dict):
        """Emit engine stopped event."""
        await self.manager.broadcast(RealtimeEvent(
            event_id=self.manager._next_event_id(),
            event_type=EventType.ENGINE_STOPPED,
            data=stats,
        ))


# Global instances
_connection_manager: Optional[ConnectionManager] = None
_event_emitter: Optional[DiagnosticEventEmitter] = None


def get_connection_manager() -> ConnectionManager:
    """Get or create global connection manager."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


def get_event_emitter() -> DiagnosticEventEmitter:
    """Get or create global event emitter."""
    global _event_emitter
    if _event_emitter is None:
        _event_emitter = DiagnosticEventEmitter(get_connection_manager())
    return _event_emitter
