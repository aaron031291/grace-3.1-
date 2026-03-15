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


def unsubscribe(topic: str, handler: EventHandler):
    """Remove a handler from a topic."""
    with _lock:
        handlers = _subscribers.get(topic, [])
        if handler in handlers:
            handlers.remove(handler)
        if not handlers and topic in _subscribers:
            del _subscribers[topic]


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

BRIDGE_SOURCES = {"layer1_bus", "deterministic_bus", "grace_os_kernel", "zmq_peer"}


def is_bridge_event(source: str) -> bool:
    """Check if an event originated from a bus bridge (to prevent echo loops)."""
    return source in BRIDGE_SOURCES


# ── ZeroMQ IPC Bridge (Spindle Autonomy Integration) ─────────────────────
import json
import os as _os
import socket as _socket
import threading

_zmq_context = None
_zmq_pub_socket = None
_zmq_thread = None

# Configurable via env vars; defaults to local TCP for Windows compatibility.
# Topology: Main app BINDS on both ports. Spindle daemon CONNECTS.
#   PUB port (5520): Grace broadcasts, Spindle subscribes
#   SUB port (5521): Spindle publishes, Grace subscribes
ZMQ_PUB_ENDPOINT = _os.environ.get("GRACE_ZMQ_PUB_ENDPOINT", "tcp://127.0.0.1:5520")
ZMQ_SUB_ENDPOINT = _os.environ.get("GRACE_ZMQ_SUB_ENDPOINT", "tcp://127.0.0.1:5521")

_ZMQ_BIND_RETRIES = 3
_ZMQ_BIND_RETRY_DELAY = 1.0  # seconds


def _is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a TCP port is already bound."""
    with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def _bind_with_retry(zmq_socket, endpoint: str, retries: int = _ZMQ_BIND_RETRIES):
    """Bind a ZMQ socket with SO_REUSEADDR and retry logic."""
    import zmq
    zmq_socket.setsockopt(zmq.LINGER, 0)
    try:
        zmq_socket.setsockopt(zmq.TCP_KEEPALIVE, 1)
    except Exception:
        pass

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            zmq_socket.bind(endpoint)
            return True
        except zmq.error.ZMQError as e:
            last_err = e
            if attempt < retries:
                logger.warning(f"[ZMQ-BRIDGE] Bind attempt {attempt}/{retries} for {endpoint} failed: {e}. Retrying in {_ZMQ_BIND_RETRY_DELAY}s...")
                time.sleep(_ZMQ_BIND_RETRY_DELAY)
    raise last_err


def _zmq_bridge_loop():
    import zmq
    global _zmq_context, _zmq_pub_socket
    _zmq_context = zmq.Context()

    # Grace PUB socket (broadcasts internal events to Spindle)
    _zmq_pub_socket = _zmq_context.socket(zmq.PUB)
    try:
        _bind_with_retry(_zmq_pub_socket, ZMQ_PUB_ENDPOINT)
    except zmq.error.ZMQError as e:
        logger.warning(f"[ZMQ-BRIDGE] Could not bind {ZMQ_PUB_ENDPOINT} after {_ZMQ_BIND_RETRIES} attempts: {e}. Skipping ZMQ bridge.")
        try:
            _zmq_pub_socket.close()
        except Exception:
            pass
        _zmq_pub_socket = None
        publish_async("system.zmq_bridge_failed", {"error": str(e), "endpoint": ZMQ_PUB_ENDPOINT}, source="zmq_bridge")
        return

    # Grace SUB socket (listens for events from Spindle)
    sub_socket = _zmq_context.socket(zmq.SUB)
    sub_socket.setsockopt(zmq.RCVTIMEO, 5000)
    try:
        _bind_with_retry(sub_socket, ZMQ_SUB_ENDPOINT)
    except zmq.error.ZMQError as e:
        logger.warning(f"[ZMQ-BRIDGE] Could not bind {ZMQ_SUB_ENDPOINT} after {_ZMQ_BIND_RETRIES} attempts: {e}. Skipping.")
        publish_async("system.zmq_bridge_failed", {"error": str(e), "endpoint": ZMQ_SUB_ENDPOINT}, source="zmq_bridge")
        try:
            _zmq_pub_socket.close()
        except Exception:
            pass
        return
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

    logger.info(f"[ZMQ-BRIDGE] Bound PUB to {ZMQ_PUB_ENDPOINT}, SUB to {ZMQ_SUB_ENDPOINT}")
    publish_async("system.zmq_bridge_started", {"pub": ZMQ_PUB_ENDPOINT, "sub": ZMQ_SUB_ENDPOINT}, source="zmq_bridge")

    # Listen to the internal event bus to forward out via ZMQ
    def _forward_to_zmq(event: Event):
        if event.source == "zmq_peer":
            return  # Don't echo back events we just received
        if _zmq_pub_socket:
            try:
                msg = {"topic": event.topic, "data": event.data, "source": event.source, "timestamp": event.timestamp}
                _zmq_pub_socket.send_string(f"{event.topic} {json.dumps(msg)}")
            except Exception as e:
                logger.error(f"[ZMQ-BRIDGE] Error forwarding event {event.topic}: {e}")

    # Subscribe to EVERYTHING internally so we can broadcast it
    subscribe("*", _forward_to_zmq)

    consecutive_errors = 0
    max_consecutive_errors = 50

    # Listen for incoming ZMQ events from Spindle and publish them to local bus
    while True:
        try:
            raw_msg = sub_socket.recv_string()
            consecutive_errors = 0  # Reset on success
            topic, payload_str = raw_msg.split(" ", 1)
            payload = json.loads(payload_str)
            # Publish locally. Mark source as 'zmq_peer' so we don't infinitely loop
            publish_async(topic=topic, data=payload.get("data", {}), source="zmq_peer")
        except zmq.Again:
            # RCVTIMEO fired — no message within 5s, this is normal
            continue
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"[ZMQ-BRIDGE] Error receiving event ({consecutive_errors}/{max_consecutive_errors}): {e}")
            if consecutive_errors >= max_consecutive_errors:
                logger.critical(f"[ZMQ-BRIDGE] Too many consecutive errors. Publishing alert and resetting counter.")
                publish_async("system.zmq_bridge_degraded", {
                    "consecutive_errors": consecutive_errors,
                    "last_error": str(e),
                }, source="zmq_bridge")
                consecutive_errors = 0
            time.sleep(1)

def start_zmq_bridge():
    """Initializes the ZeroMQ pub/sub bridge for isolated parallel runtimes (e.g. Spindle)."""
    global _zmq_thread
    import os
    if os.environ.get("IS_SPINDLE_DAEMON") == "1":
        logger.debug("[ZMQ-BRIDGE] Running inside Spindle daemon. Skipping host ZMQ bind.")
        return

    if _zmq_pub_socket is not None:
        return  # Already running

    if _zmq_thread is None or not _zmq_thread.is_alive():
        try:
            import zmq
            _zmq_thread = threading.Thread(target=_zmq_bridge_loop, daemon=True, name="zmq-event-bridge")
            _zmq_thread.start()
        except ImportError:
            logger.warning("[ZMQ-BRIDGE] pyzmq not installed. IPC bridge for Spindle will not start.")

# Bridge is started explicitly during app lifespan via _init_spindle_services()
