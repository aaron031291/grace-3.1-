"""
Grace OS — Event & Audit System

Full observability for Grace OS. Every layer action emits a structured event.
Provides an immutable audit trail, replay capability, and subscriber support.
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Event type constants
MESSAGE_SENT = "MESSAGE_SENT"
MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
RESPONSE_RETURNED = "RESPONSE_RETURNED"
LAYER_STARTED = "LAYER_STARTED"
LAYER_STOPPED = "LAYER_STOPPED"
TRUST_UPDATED = "TRUST_UPDATED"
SESSION_STARTED = "SESSION_STARTED"
SESSION_COMPLETED = "SESSION_COMPLETED"
TOOL_CALLED = "TOOL_CALLED"


@dataclass
class GraceEvent:
    """A structured event emitted by the Grace OS system."""
    event_type: str
    trace_id: str
    layer: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: f"evt_{int(time.time()*1000)}")


# Type alias for event subscribers
EventSubscriber = Callable[[GraceEvent], None]


class EventSystem:
    """
    Central event bus for Grace OS observability.
    Provides append-only event logs, subscription, and replay.
    """

    def __init__(self):
        # trace_id -> list of events (append-only per session)
        self._events: Dict[str, List[GraceEvent]] = {}
        # Global event log (all sessions)
        self._global_log: List[GraceEvent] = []
        # event_type -> list of subscribers
        self._subscribers: Dict[str, List[EventSubscriber]] = {}

    def emit(
        self,
        event_type: str,
        trace_id: str,
        layer: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> GraceEvent:
        """Emit a structured event. Appends to session and global logs."""
        event = GraceEvent(
            event_type=event_type,
            trace_id=trace_id,
            layer=layer,
            payload=payload or {},
        )

        # Append to session log
        if trace_id not in self._events:
            self._events[trace_id] = []
        self._events[trace_id].append(event)

        # Append to global log
        self._global_log.append(event)

        # Notify subscribers
        for subscriber in self._subscribers.get(event_type, []):
            try:
                subscriber(event)
            except Exception as e:
                logger.error(f"[EventSystem] Subscriber error: {e}")

        # Also notify wildcard subscribers
        for subscriber in self._subscribers.get("*", []):
            try:
                subscriber(event)
            except Exception as e:
                logger.error(f"[EventSystem] Wildcard subscriber error: {e}")

        logger.debug(
            f"[EventSystem] {event_type} | "
            f"{layer} | session={trace_id[:8]}"
        )

        return event

    def subscribe(self, event_type: str, subscriber: EventSubscriber):
        """
        Subscribe to a specific event type.
        Use '*' to subscribe to all events.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(subscriber)

    def unsubscribe(self, event_type: str, subscriber: EventSubscriber):
        """Remove a subscriber."""
        if event_type in self._subscribers:
            if subscriber in self._subscribers[event_type]:
                self._subscribers[event_type].remove(subscriber)

    def get_events(
        self,
        trace_id: str,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get events for a session, optionally filtered by type.
        Used for replay and debugging.
        """
        events = self._events.get(trace_id, [])
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "trace_id": e.trace_id,
                "layer": e.layer,
                "payload": e.payload,
                "timestamp": e.timestamp,
            }
            for e in events
        ]

    def get_event_count(self, trace_id: str) -> int:
        """Get total event count for a session."""
        return len(self._events.get(trace_id, []))

    def get_global_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get the most recent events across all sessions."""
        recent = self._global_log[-limit:]
        return [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "trace_id": e.trace_id,
                "layer": e.layer,
                "timestamp": e.timestamp,
            }
            for e in recent
        ]

    def get_session_timeline(self, trace_id: str) -> List[str]:
        """Get a human-readable timeline of events for a session."""
        events = self._events.get(trace_id, [])
        return [
            f"[{e.event_type}] {e.layer} @ {datetime.fromtimestamp(e.timestamp).strftime('%H:%M:%S.%f')[:-3]}"
            for e in events
        ]
