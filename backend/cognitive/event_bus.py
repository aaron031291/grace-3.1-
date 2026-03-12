"""
Event Bus — In-process async event system for Grace.

Replaces the need for external message queues (Redis/RabbitMQ) for
intra-system communication. Components publish events, subscribers react.

Events:
  file.uploaded, file.organized, file.deleted
  llm.called, llm.failed
  healing.started, healing.completed, healing.failed
  learning.new_pattern, learning.feedback
  consensus.started, consensus.completed
  trust.updated, trust.threshold_crossed
  genesis.key_created
  system.health_changed
"""

import logging
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Event:
    topic: str
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "system"


EventHandler = Callable[[Event], None]

_subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
_event_log: List[Dict[str, Any]] = []
_lock = threading.Lock()
MAX_LOG = 500


def subscribe(topic: str, handler: EventHandler):
    """Subscribe to events on a topic. Supports wildcards: 'llm.*' matches 'llm.called'."""
    with _lock:
        _subscribers[topic].append(handler)


def publish(topic: str, data: Dict[str, Any] = None, source: str = "system"):
    """
    Publish an event. Handlers run synchronously in the caller's thread.
    For non-blocking, wrap the publish call in a thread.
    """
    event = Event(topic=topic, data=data or {}, source=source)

    with _lock:
        _event_log.append({"topic": topic, "source": source, "ts": event.timestamp})
        if len(_event_log) > MAX_LOG:
            _event_log.pop(0)

    # Exact match subscribers
    handlers = list(_subscribers.get(topic, []))

    # Wildcard subscribers (e.g., 'llm.*' matches 'llm.called')
    parts = topic.split(".")
    if len(parts) > 1:
        wildcard = parts[0] + ".*"
        handlers.extend(_subscribers.get(wildcard, []))

    # Global wildcard
    handlers.extend(_subscribers.get("*", []))

    for handler in handlers:
        try:
            handler(event)
        except Exception as e:
            logger.warning(f"Event handler error for '{topic}': {e}")


def publish_async(topic: str, data: Dict[str, Any] = None, source: str = "system"):
    """Non-blocking event publish."""
    t = threading.Thread(target=publish, args=(topic, data, source), daemon=True)
    t.start()


def get_recent_events(limit: int = 50) -> List[Dict[str, Any]]:
    with _lock:
        return list(reversed(_event_log[-limit:]))


def get_subscriber_count() -> Dict[str, int]:
    with _lock:
        return {topic: len(handlers) for topic, handlers in _subscribers.items()}
