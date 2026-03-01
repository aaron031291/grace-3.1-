"""
Event Bridge — Connects Grace OS EventSystem ↔ cognitive event_bus.

These two event systems were operating independently:
- Grace OS EventSystem: session-scoped, structured GraceEvent, 9-layer pipeline
- Cognitive event_bus: topic-based, global, thread-based

The bridge forwards events between them so the entire system has unified
observability. Mirror, self-healing, sandbox, and horizon planner all
benefit from seeing events from both sides.
"""

import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_bridge_active = False
_bridge_lock = threading.Lock()


def activate_bridge():
    """
    Activate the event bridge between Grace OS and cognitive event systems.
    Call once at startup. Safe to call multiple times.
    """
    global _bridge_active
    with _bridge_lock:
        if _bridge_active:
            return
        _bridge_active = True

    _bridge_graceos_to_cognitive()
    _bridge_cognitive_to_graceos()
    logger.info("[EVENT-BRIDGE] Grace OS EventSystem ↔ cognitive event_bus bridge activated")


def _bridge_graceos_to_cognitive():
    """Forward Grace OS events → cognitive event_bus."""
    try:
        from grace_os.kernel.event_system import (
            EventSystem, GraceEvent,
            MESSAGE_SENT, RESPONSE_RETURNED,
            LAYER_STARTED, LAYER_STOPPED,
            TRUST_UPDATED, SESSION_STARTED, SESSION_COMPLETED,
            TOOL_CALLED,
        )
        from cognitive.event_bus import publish_async

        grace_os_to_topic = {
            MESSAGE_SENT: "graceos.message_sent",
            RESPONSE_RETURNED: "graceos.response_returned",
            LAYER_STARTED: "graceos.layer_started",
            LAYER_STOPPED: "graceos.layer_stopped",
            TRUST_UPDATED: "trust.updated",
            SESSION_STARTED: "graceos.session_started",
            SESSION_COMPLETED: "graceos.session_completed",
            TOOL_CALLED: "graceos.tool_called",
        }

        def _forward_to_cognitive(event: GraceEvent):
            topic = grace_os_to_topic.get(event.event_type, f"graceos.{event.event_type.lower()}")
            try:
                publish_async(topic, {
                    "trace_id": event.trace_id,
                    "layer": event.layer,
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "timestamp": event.timestamp,
                    "source": "grace_os_bridge",
                }, source="grace_os_bridge")
            except Exception as e:
                logger.debug(f"[EVENT-BRIDGE] Forward to cognitive failed: {e}")

        # Subscribe to all Grace OS event types
        try:
            from grace_os.kernel.message_bus import get_message_bus
            bus = get_message_bus()
            if hasattr(bus, 'event_system') and bus.event_system:
                for event_type in grace_os_to_topic:
                    bus.event_system.subscribe(event_type, _forward_to_cognitive)
                logger.info(f"[EVENT-BRIDGE] Subscribed to {len(grace_os_to_topic)} Grace OS event types")
        except Exception as e:
            logger.debug(f"[EVENT-BRIDGE] Grace OS subscription failed (bus not ready): {e}")

    except ImportError as e:
        logger.debug(f"[EVENT-BRIDGE] Grace OS import not available: {e}")


def _bridge_cognitive_to_graceos():
    """Forward key cognitive events → Grace OS EventSystem for session tracking."""
    try:
        from cognitive.event_bus import subscribe

        important_topics = [
            "consensus.*",
            "genesis.*",
            "healing.*",
            "learning.*",
            "trust.*",
            "file.*",
            "graceos.*",
        ]

        def _forward_to_graceos(event):
            try:
                from grace_os.kernel.event_system import EventSystem
                from grace_os.kernel.message_bus import get_message_bus
                bus = get_message_bus()
                if hasattr(bus, 'event_system') and bus.event_system:
                    bus.event_system.emit(
                        event_type=f"COGNITIVE_{event.topic.upper().replace('.', '_')}",
                        trace_id=event.data.get("trace_id", "cognitive_bridge"),
                        layer="cognitive",
                        payload={
                            "topic": event.topic,
                            "data": event.data,
                            "source": event.source,
                            "timestamp": event.timestamp,
                        },
                    )
            except Exception:
                pass

        for topic in important_topics:
            try:
                subscribe(topic, _forward_to_graceos)
            except Exception:
                pass

        logger.info(f"[EVENT-BRIDGE] Subscribed to {len(important_topics)} cognitive event topics")

    except ImportError as e:
        logger.debug(f"[EVENT-BRIDGE] Cognitive event_bus import not available: {e}")


def _subscribe_mirror():
    """Wire mirror self-modeling to event bus so it observes everything."""
    try:
        from cognitive.event_bus import subscribe
        from cognitive.mirror_self_modeling import get_mirror

        def _mirror_observer(event):
            try:
                mirror = get_mirror()
                if hasattr(mirror, 'observe_event'):
                    mirror.observe_event(event.topic, event.data)
            except Exception:
                pass

        subscribe("genesis.*", _mirror_observer)
        subscribe("healing.*", _mirror_observer)
        subscribe("learning.*", _mirror_observer)
        subscribe("consensus.*", _mirror_observer)
        subscribe("trust.*", _mirror_observer)
        logger.info("[EVENT-BRIDGE] Mirror self-modeling subscribed to event bus")
    except Exception as e:
        logger.debug(f"[EVENT-BRIDGE] Mirror subscription failed: {e}")


def _subscribe_self_healing():
    """Wire self-healing tracker to observe error events."""
    try:
        from cognitive.event_bus import subscribe
        from cognitive.self_healing_tracker import get_self_healing_tracker

        def _healing_observer(event):
            try:
                tracker = get_self_healing_tracker()
                component = event.data.get("component", event.source or "unknown")
                if "error" in event.topic or "failure" in event.topic or "failed" in event.topic:
                    error_msg = event.data.get("error", event.data.get("message", str(event.data)[:200]))
                    tracker.report_error(component, error_msg, auto_heal=True)
                elif "completed" in event.topic or "success" in event.topic:
                    tracker.report_healthy(component)
            except Exception:
                pass

        subscribe("healing.*", _healing_observer)
        subscribe("*.failed", _healing_observer)
        subscribe("*.error", _healing_observer)
        subscribe("consensus.completed", _healing_observer)
        subscribe("learning.*", _healing_observer)
        logger.info("[EVENT-BRIDGE] Self-healing tracker subscribed to event bus")
    except Exception as e:
        logger.debug(f"[EVENT-BRIDGE] Self-healing subscription failed: {e}")


def activate_all_bridges():
    """Activate event bridge + wire mirror + wire self-healing."""
    activate_bridge()
    _subscribe_mirror()
    _subscribe_self_healing()
