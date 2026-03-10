"""
Ask Grace Connector — Layer 1 integration for unified system introspection.

Connects Ask Grace to the message bus so it can:
1. Respond to system queries via request-response
2. React to component health changes via pub-sub
3. Aggregate data from all three registries + probe agent + Genesis keys
4. Publish query events so other components can learn from what users ask
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from layer1.message_bus import (
    Layer1MessageBus,
    ComponentType,
    Message,
    get_message_bus,
)

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)


class AskGraceConnector:
    """
    Layer 1 connector that makes Ask Grace a first-class bus participant.

    Request Handlers:
      - ask_grace/query: answer natural language questions about the system
      - ask_grace/components: list components with optional filters
      - ask_grace/health: aggregated health from all registries

    Subscriptions:
      - system.health_changed: update cached health state
      - genesis_keys.*: track recent activity for context
      - trigger.probe_completed: capture fresh probe results

    Publications:
      - ask_grace.query_received: emitted on every user query (for analytics)
      - ask_grace.insight_generated: emitted when a useful pattern is found
    """

    def __init__(self, message_bus: Optional[Layer1MessageBus] = None):
        self.message_bus = message_bus or get_message_bus()
        self._recent_queries: List[Dict[str, Any]] = []
        self._max_recent = 200
        self._cached_health: Optional[Dict[str, Any]] = None
        self._cached_health_ts: Optional[datetime] = None

        self.message_bus.register_component(ComponentType.COGNITIVE_ENGINE, self)
        self._register_request_handlers()
        self._register_autonomous_actions()
        self._subscribe_to_events()

        logger.info("[ASK-GRACE-CONNECTOR] Registered with Layer 1 message bus")

    def _register_request_handlers(self):
        self.message_bus.register_request_handler(
            ComponentType.COGNITIVE_ENGINE,
            "ask_grace_query",
            self._handle_query_request,
        )
        self.message_bus.register_request_handler(
            ComponentType.COGNITIVE_ENGINE,
            "ask_grace_components",
            self._handle_components_request,
        )
        self.message_bus.register_request_handler(
            ComponentType.COGNITIVE_ENGINE,
            "ask_grace_health",
            self._handle_health_request,
        )
        logger.info("[ASK-GRACE-CONNECTOR] Registered 3 request handlers")

    def _register_autonomous_actions(self):
        self.message_bus.register_autonomous_action(
            trigger_event="trigger.probe_completed",
            action=self._on_probe_completed,
            component=ComponentType.COGNITIVE_ENGINE,
            description="Cache fresh probe results for Ask Grace context",
        )
        logger.info("[ASK-GRACE-CONNECTOR] Registered 1 autonomous action")

    def _subscribe_to_events(self):
        self.message_bus.subscribe(
            "system.health_changed", self._on_health_changed
        )
        logger.info("[ASK-GRACE-CONNECTOR] Subscribed to system.health_changed")

    async def _handle_query_request(self, message: Message) -> Dict[str, Any]:
        query = message.payload.get("query", "")
        context = await self.gather_system_context()
        return {"context": context, "query": query}

    async def _handle_components_request(self, message: Message) -> Dict[str, Any]:
        filters = message.payload.get("filters", {})
        components = self._get_all_components()

        if filters.get("category"):
            components = [
                c for c in components if c.get("category") == filters["category"]
            ]
        if filters.get("status"):
            components = [
                c for c in components if c.get("status") == filters["status"]
            ]

        return {"components": components, "total": len(components)}

    async def _handle_health_request(self, message: Message) -> Dict[str, Any]:
        return await self.gather_system_context()

    async def _on_probe_completed(self, message: Message):
        self._cached_health = message.payload
        self._cached_health_ts = datetime.now(timezone.utc)
        logger.info("[ASK-GRACE-CONNECTOR] Cached fresh probe results")

    async def _on_health_changed(self, message: Message):
        self._cached_health = message.payload
        self._cached_health_ts = datetime.now(timezone.utc)

    async def publish_query_event(self, query: str, intent: str, result_count: int):
        await self.message_bus.publish(
            topic="ask_grace.query_received",
            payload={
                "query": query,
                "intent": intent,
                "result_count": result_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            from_component=ComponentType.COGNITIVE_ENGINE,
        )

    def _get_all_components(self) -> List[Dict[str, Any]]:
        components = []

        try:
            from cognitive.system_registry import get_system_registry
            sr = get_system_registry()
            components.extend(sr.get_all())
        except Exception as e:
            logger.debug(f"[ASK-GRACE] SystemRegistry unavailable: {e}")

        try:
            from core.registry import get_component_registry
            cr = get_component_registry()
            for manifest in cr.get_manifests():
                if not any(c.get("id") == manifest["component_id"] for c in components):
                    components.append({
                        "id": manifest["component_id"],
                        "name": manifest["name"],
                        "category": manifest["role"],
                        "status": manifest["state"],
                        "description": manifest.get("description", ""),
                        "source": "component_registry",
                    })
        except Exception as e:
            logger.debug(f"[ASK-GRACE] ComponentRegistry unavailable: {e}")

        return components

    async def gather_system_context(self) -> Dict[str, Any]:
        """Aggregate system state from all available sources."""
        context: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources_queried": [],
        }

        try:
            from cognitive.system_registry import get_system_registry
            sr = get_system_registry()
            health = sr.check_health()
            all_comps = sr.get_all()
            by_cat = sr.get_by_category()
            context["system_registry"] = {
                "health": health,
                "total_components": len(all_comps),
                "categories": {k: len(v) for k, v in by_cat.items()},
                "broken": [c for c in all_comps if c.get("status") == "red"],
                "degraded": [c for c in all_comps if c.get("status") == "amber"],
                "new": [c for c in all_comps if c.get("is_new")],
            }
            context["sources_queried"].append("system_registry")
        except Exception as e:
            context["system_registry"] = {"error": str(e)}

        try:
            from core.registry import get_component_registry
            cr = get_component_registry()
            sys_health = cr.get_system_health()
            context["component_registry"] = {
                "health": sys_health,
                "stats": cr.get_stats(),
            }
            context["sources_queried"].append("component_registry")
        except Exception as e:
            context["component_registry"] = {"error": str(e)}

        bus_stats = self.message_bus.get_stats()
        context["message_bus"] = {
            "stats": bus_stats,
            "autonomous_actions": self.message_bus.get_autonomous_actions(),
        }
        context["sources_queried"].append("message_bus")

        try:
            from cognitive.event_bus import get_recent_events, get_subscriber_count
            context["event_bus"] = {
                "recent_events": get_recent_events(20),
                "subscriber_counts": get_subscriber_count(),
            }
            context["sources_queried"].append("cognitive_event_bus")
        except Exception as e:
            context["event_bus"] = {"error": str(e)}

        try:
            from api.live_console_api import live_status
            status = await live_status()
            context["live_status"] = status
            context["sources_queried"].append("live_console")
        except Exception as e:
            context["live_status"] = {"error": str(e)}

        if self._cached_health:
            context["last_probe"] = {
                "data": self._cached_health,
                "timestamp": self._cached_health_ts.isoformat() if self._cached_health_ts else None,
            }
            context["sources_queried"].append("probe_cache")

        return context

    def record_query(self, query: str, response: str, intent: str):
        self._recent_queries.append({
            "query": query,
            "response_preview": response[:200] if response else "",
            "intent": intent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if len(self._recent_queries) > self._max_recent:
            self._recent_queries = self._recent_queries[-self._max_recent:]

    def get_recent_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(reversed(self._recent_queries[-limit:]))


_connector: Optional[AskGraceConnector] = None


def get_ask_grace_connector() -> AskGraceConnector:
    global _connector
    if _connector is None:
        _connector = AskGraceConnector()
    return _connector
