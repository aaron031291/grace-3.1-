"""Bus bridge utilities.

Purpose
-------
Grace currently has multiple internal messaging/event mechanisms:

- Cognitive event bus: backend.cognitive.event_bus (topic-based, wildcard support)
- Layer1 message bus: backend.layer1.message_bus.Layer1MessageBus (connector-oriented)
- Grace OS kernel buses: backend.grace_os.kernel.message_bus / event_system

This module provides a *thin* runtime bridge so events published on one bus can
be mirrored to others.

Design goals
------------
- Safe by default: best-effort bridging and never crash the app
- Avoid infinite loops: mark forwarded events with a dedicated source
- Low coupling: keep bridge logic out of domain components

NOTE: This is not a guarantee of delivery; it is an integration convenience.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


FORWARDED_SOURCE = "bus_bridge"


@dataclass
class BridgeConfig:
    enable_cognitive_to_layer1: bool = True
    enable_layer1_to_cognitive: bool = False
    # Leave GraceOS bridging off by default until the kernel bus API stabilizes.
    enable_graceos_to_cognitive: bool = False


class BusBridge:
    """Bridges events between internal Grace buses."""

    def __init__(self, config: Optional[BridgeConfig] = None):
        self.config = config or BridgeConfig()
        self._started = False

        self._layer1_bus = None
        self._layer1_publish: Optional[Callable[..., Any]] = None
        self._layer1_subscribe: Optional[Callable[..., Any]] = None

        # For cognitive bus we always call the module-level functions.
        self._cog_publish_async: Optional[Callable[..., Any]] = None
        self._cog_subscribe: Optional[Callable[..., Any]] = None

    def start(self) -> None:
        """Start the bridge.

        Safe to call multiple times.
        """

        if self._started:
            return

        self._wire_cognitive_bus()
        self._wire_layer1_bus()

        if self.config.enable_cognitive_to_layer1:
            self._bridge_cognitive_to_layer1()

        if self.config.enable_layer1_to_cognitive:
            self._bridge_layer1_to_cognitive()

        # GraceOS bridging is currently opt-in and will be added as kernel API stabilizes.

        self._started = True
        logger.info(
            "[BUS_BRIDGE] started (cog→l1=%s, l1→cog=%s, graceos→cog=%s)",
            self.config.enable_cognitive_to_layer1,
            self.config.enable_layer1_to_cognitive,
            self.config.enable_graceos_to_cognitive,
        )

    def _wire_cognitive_bus(self) -> None:
        try:
            from cognitive.event_bus import publish_async, subscribe

            self._cog_publish_async = publish_async
            self._cog_subscribe = subscribe
        except Exception as e:  # pragma: no cover
            logger.warning("[BUS_BRIDGE] cognitive event bus not available: %s", e)

    def _wire_layer1_bus(self) -> None:
        try:
            from layer1.message_bus import get_message_bus

            self._layer1_bus = get_message_bus()
            self._layer1_publish = getattr(self._layer1_bus, "publish", None)
            self._layer1_subscribe = getattr(self._layer1_bus, "subscribe", None)
        except Exception as e:  # pragma: no cover
            logger.warning("[BUS_BRIDGE] layer1 message bus not available: %s", e)

    def _bridge_cognitive_to_layer1(self) -> None:
        if not (self._cog_subscribe and self._layer1_publish):
            return

        async def _publish_to_layer1(topic: str, data: Dict[str, Any]) -> None:
            from layer1.message_bus import ComponentType
            await self._layer1_publish(topic=topic, payload=data, from_component=ComponentType.COGNITIVE_ENGINE)

        def _handler(evt: Any) -> None:
            try:
                # evt is cognitive.event_bus.Event
                topic = getattr(evt, "topic", "")
                data = getattr(evt, "data", None) or {}
                source = getattr(evt, "source", "")

                if source == FORWARDED_SOURCE or source == "layer1_bus":
                    return

                # Best-effort fire-and-forget.
                coro = _publish_to_layer1(topic, {"data": data, "source": source})
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(coro)
                except RuntimeError:
                    # No running loop (sync context). Use a temporary loop.
                    asyncio.run(coro)
            except Exception as e:  # pragma: no cover
                logger.debug("[BUS_BRIDGE] cog→l1 forward failed: %s", e)

        try:
            # Subscribe to all cognitive events.
            self._cog_subscribe("*", _handler)
        except Exception as e:  # pragma: no cover
            logger.warning("[BUS_BRIDGE] failed to subscribe to cognitive bus: %s", e)

    def _bridge_layer1_to_cognitive(self) -> None:
        # This is disabled by default because Layer1 may publish high-volume messages.
        if not (self._layer1_subscribe and self._cog_publish_async):
            return

        def _handler(msg: Any) -> None:
            try:
                topic = getattr(msg, "topic", "")
                payload = getattr(msg, "payload", None) or {}
                source = getattr(msg, "source", "")

                if source == FORWARDED_SOURCE:
                    return

                self._cog_publish_async(
                    topic=f"layer1.{topic}",
                    data={"payload": payload, "source": source},
                    source=FORWARDED_SOURCE,
                )
            except Exception as e:  # pragma: no cover
                logger.debug("[BUS_BRIDGE] l1→cog forward failed: %s", e)

        try:
            # Subscribe to all layer1 topics if supported; otherwise skip.
            self._layer1_subscribe("*", _handler)
        except Exception:
            # Layer1 doesn't necessarily support wildcard; keep bridge opt-in.
            logger.info("[BUS_BRIDGE] layer1 wildcard subscribe not supported; l1→cog bridge inactive")


_bridge_singleton: Optional[BusBridge] = None


def start_bus_bridge(config: Optional[BridgeConfig] = None) -> BusBridge:
    """Start a singleton bridge for the current process."""

    global _bridge_singleton
    if _bridge_singleton is None:
        _bridge_singleton = BusBridge(config=config)
    _bridge_singleton.start()
    return _bridge_singleton
