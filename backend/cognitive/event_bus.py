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

# ── ZeroMQ IPC Bridge (Spindle Autonomy Integration) ─────────────────────
import json
import threading

_zmq_context = None
_zmq_pub_socket = None
_zmq_thread = None

# We use local TCP instead of strict IPC for robust Windows compatibility.
ZMQ_PUB_ENDPOINT = "tcp://127.0.0.1:5520"  # Grace broadcasts here (Spindle SUBs to this)
ZMQ_SUB_ENDPOINT = "tcp://127.0.0.1:5521"  # Grace listens here (Spindle PUBs to this)

def _zmq_bridge_loop():
    import zmq
    global _zmq_context, _zmq_pub_socket
    _zmq_context = zmq.Context()
    
    # Grace PUB socket (broadcasts internal events to Spindle)
    _zmq_pub_socket = _zmq_context.socket(zmq.PUB)
    _zmq_pub_socket.bind(ZMQ_PUB_ENDPOINT)
    
    # Grace SUB socket (listens for events from Spindle)
    sub_socket = _zmq_context.socket(zmq.SUB)
    sub_socket.bind(ZMQ_SUB_ENDPOINT)
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all topics

    logger.info(f"[ZMQ-BRIDGE] Bound PUB to {ZMQ_PUB_ENDPOINT}, SUB to {ZMQ_SUB_ENDPOINT}")

    # Listen to the internal event bus to forward out via ZMQ
    def _forward_to_zmq(event: Event):
        if event.source == "zmq_peer":
            return # Don't echo back events we just received
        if _zmq_pub_socket:
            try:
                msg = {"topic": event.topic, "data": event.data, "source": event.source, "timestamp": event.timestamp}
                _zmq_pub_socket.send_string(f"{event.topic} {json.dumps(msg)}")
            except Exception as e:
                logger.error(f"[ZMQ-BRIDGE] Error forwarding event {event.topic}: {e}")
                
    # Subscribe to EVERYTHING internally so we can broadcast it
    subscribe("*", _forward_to_zmq)

    # Listen for incoming ZMQ events from Spindle and publish them to local bus
    while True:
        try:
            raw_msg = sub_socket.recv_string()
            topic, payload_str = raw_msg.split(" ", 1)
            payload = json.loads(payload_str)
            # Publish locally. Mark source as 'zmq_peer' so we don't infinitely loop
            publish_async(topic=topic, data=payload.get("data", {}), source="zmq_peer")
        except Exception as e:
            logger.error(f"[ZMQ-BRIDGE] Error receiving event: {e}")
            time.sleep(1)

def start_zmq_bridge():
    """Initializes the ZeroMQ pub/sub bridge for isolated parallel runtimes (e.g. Spindle)."""
    global _zmq_thread
    import os
    if os.environ.get("IS_SPINDLE_DAEMON") == "1":
        logger.debug("[ZMQ-BRIDGE] Running inside Spindle daemon. Skipping host ZMQ bind.")
        return

    if _zmq_thread is None:
        try:
            import zmq
            _zmq_thread = threading.Thread(target=_zmq_bridge_loop, daemon=True, name="zmq-event-bridge")
            _zmq_thread.start()
        except ImportError:
            logger.warning("[ZMQ-BRIDGE] pyzmq not installed. IPC bridge for Spindle will not start.")

# Auto-start the bridge when the module loads
start_zmq_bridge()
