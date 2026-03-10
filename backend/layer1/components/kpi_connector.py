"""
KPI Connector - Layer 1 Integration

Connects KPI tracking system to Layer 1 message bus, enabling autonomous
KPI tracking and trust score generation from component performance.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from layer1.message_bus import (
    Layer1MessageBus,
    Message,
    ComponentType,
    MessageType,
    get_message_bus,
)
from layer1.autonomous_actions import AutonomousAction

# Import KPI tracker
try:
    from ml_intelligence.kpi_tracker import get_kpi_tracker, KPITracker
    KPI_TRACKER_AVAILABLE = True
except ImportError:
    get_kpi_tracker = None
    KPITracker = None
    KPI_TRACKER_AVAILABLE = False

logger = logging.getLogger(__name__)


class KPIConnector:
    """
    Connector for KPI tracking system.
    
    Integrates KPI tracker with Layer 1 message bus for:
    - Autonomous KPI tracking on component actions
    - KPI-to-trust score conversion
    - Component-level trust aggregation
    - System-wide trust metric
    - Integration with trust-aware systems
    """

    def __init__(
        self,
        message_bus: Optional[Layer1MessageBus] = None,
        kpi_tracker: Optional[KPITracker] = None,
    ):
        """
        Initialize KPI connector.

        Args:
            message_bus: Layer 1 message bus instance
            kpi_tracker: KPI tracker instance (optional, uses singleton if not provided)
        """
        if not KPI_TRACKER_AVAILABLE:
            raise ImportError("KPI tracker not available")
        
        self.message_bus = message_bus or get_message_bus()
        self.kpi_tracker = kpi_tracker or get_kpi_tracker()
        self.enabled = True

        # Register with message bus
        self.message_bus.register_component(
            ComponentType.COGNITIVE_ENGINE,  # Using COGNITIVE_ENGINE for KPI tracking
            self
        )
        logger.info("[KPI-CONNECTOR] Registered with message bus")
        
        self._register_request_handlers()
        self._register_autonomous_actions()
        self._subscribe_to_events()
        
        # Register common components
        self._register_common_components()

    def _register_common_components(self):
        """Register common components with default metric weights."""
        common_components = {
            "rag": {"requests_handled": 1.0, "successes": 2.0, "failures": -1.0},
            "ingestion": {"files_processed": 1.0, "files_succeeded": 2.0, "files_failed": -1.0},
            "memory_mesh": {"operations": 1.0, "successes": 2.0},
            "llm_orchestration": {"requests": 1.0, "successes": 2.0, "errors": -1.0},
            "neuro_symbolic": {"reasoning_queries": 1.0, "successful_reasoning": 2.0},
            "knowledge_base": {"repositories_ingested": 1.0, "verification_passed": 2.0},
        }
        
        for component_name, weights in common_components.items():
            self.kpi_tracker.register_component(component_name, weights)

    def _register_request_handlers(self):
        """Register request handlers with message bus."""
        self.message_bus.register_handler(
            MessageType.REQUEST,
            "kpi.increment",
            self._handle_increment_kpi,
        )
        self.message_bus.register_handler(
            MessageType.REQUEST,
            "kpi.get_component_trust",
            self._handle_get_component_trust,
        )
        self.message_bus.register_handler(
            MessageType.REQUEST,
            "kpi.get_system_trust",
            self._handle_get_system_trust,
        )
        self.message_bus.register_handler(
            MessageType.REQUEST,
            "kpi.get_health",
            self._handle_get_health,
        )

    def _register_autonomous_actions(self):
        """Register autonomous actions for automatic KPI tracking."""
        # Track component actions automatically
        action_patterns = [
            ("rag.query_received", "rag", "requests_handled"),
            ("rag.retrieval_success", "rag", "successes"),
            ("rag.retrieval_failure", "rag", "failures"),
            ("ingestion.file_processed", "ingestion", "files_processed"),
            ("ingestion.file_succeeded", "ingestion", "files_succeeded"),
            ("ingestion.file_failed", "ingestion", "files_failed"),
            ("memory_mesh.operation", "memory_mesh", "operations"),
            ("llm.request", "llm_orchestration", "requests"),
            ("llm.success", "llm_orchestration", "successes"),
            ("llm.error", "llm_orchestration", "errors"),
            ("neuro_symbolic.reasoning_complete", "neuro_symbolic", "reasoning_queries"),
            ("knowledge_base.ingestion_complete", "knowledge_base", "repositories_ingested"),
            ("knowledge_base.integrity_verified", "knowledge_base", "verification_passed"),
        ]
        
        for trigger_event, component_name, metric_name in action_patterns:
            # Create handler with proper closure
            def make_handler(comp, met):
                async def handler(message: Message):
                    await self._on_component_action(message, comp, met)
                return handler
            
            handler = make_handler(component_name, metric_name)
            
            self.message_bus.register_autonomous_action(
                trigger_event=trigger_event,
                action=handler,
                component=ComponentType.COGNITIVE_ENGINE,
                description=f"Auto-track KPI: {component_name}.{metric_name}",
            )

    def _subscribe_to_events(self):
        """Subscribe to relevant events."""
        # Subscribe to all component events for KPI tracking
        self.message_bus.subscribe(
            "*.success",
            self._on_success_event,
        )
        self.message_bus.subscribe(
            "*.failure",
            self._on_failure_event,
        )
        self.message_bus.subscribe(
            "*.error",
            self._on_error_event,
        )

    async def _handle_increment_kpi(self, message: Message) -> Dict[str, Any]:
        """Handle increment KPI request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        component_name = message.payload.get("component_name")
        metric_name = message.payload.get("metric_name")
        value = message.payload.get("value", 1.0)
        metadata = message.payload.get("metadata")

        if not component_name or not metric_name:
            return {"success": False, "error": "component_name and metric_name required"}

        try:
            self.kpi_tracker.increment_kpi(component_name, metric_name, value, metadata)
            
            # Publish KPI updated event
            await self.message_bus.publish(
                topic="kpi.updated",
                payload={
                    "component_name": component_name,
                    "metric_name": metric_name,
                    "value": value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                from_component=ComponentType.COGNITIVE_ENGINE,
            )
            
            return {"success": True}

        except Exception as e:
            logger.error(f"[KPI-CONNECTOR] Failed to increment KPI: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_get_component_trust(self, message: Message) -> Dict[str, Any]:
        """Handle get component trust request."""
        component_name = message.payload.get("component_name")

        if not component_name:
            return {"success": False, "error": "component_name required"}

        try:
            trust_score = self.kpi_tracker.get_component_trust_score(component_name)
            health = self.kpi_tracker.get_health_signal(component_name)
            
            return {
                "success": True,
                "component_name": component_name,
                "trust_score": trust_score,
                "health": health,
            }

        except Exception as e:
            logger.error(f"[KPI-CONNECTOR] Failed to get component trust: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_get_system_trust(self, message: Message) -> Dict[str, Any]:
        """Handle get system trust request."""
        component_weights = message.payload.get("component_weights")

        try:
            system_trust = self.kpi_tracker.get_system_trust_score(component_weights)
            system_health = self.kpi_tracker.get_system_health()
            
            return {
                "success": True,
                "system_trust_score": system_trust,
                "system_health": system_health,
            }

        except Exception as e:
            logger.error(f"[KPI-CONNECTOR] Failed to get system trust: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_get_health(self, message: Message) -> Dict[str, Any]:
        """Handle get health request."""
        component_name = message.payload.get("component_name")

        try:
            if component_name:
                health = self.kpi_tracker.get_health_signal(component_name)
            else:
                health = self.kpi_tracker.get_system_health()
            
            return {
                "success": True,
                "health": health,
            }

        except Exception as e:
            logger.error(f"[KPI-CONNECTOR] Failed to get health: {e}")
            return {"success": False, "error": str(e)}

    async def _on_component_action(self, message: Message, component_name: str, metric_name: str):
        """Autonomous action: Track component action."""
        if not self.enabled:
            return

        try:
            # Extract metadata from message
            metadata = {
                "topic": message.topic,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            # Increment KPI
            self.kpi_tracker.increment_kpi(component_name, metric_name, 1.0, metadata)
            
            logger.debug(f"[KPI-CONNECTOR] 🤖 Auto-tracked: {component_name}.{metric_name}")

        except Exception as e:
            logger.error(f"[KPI-CONNECTOR] Auto-tracking failed: {e}")

    async def _on_success_event(self, message: Message):
        """Handle success events."""
        # Extract component name from topic (e.g., "rag.success" -> "rag")
        topic_parts = message.topic.split(".")
        if len(topic_parts) >= 2:
            component_name = topic_parts[0]
            self.kpi_tracker.increment_kpi(component_name, "successes", 1.0)

    async def _on_failure_event(self, message: Message):
        """Handle failure events."""
        topic_parts = message.topic.split(".")
        if len(topic_parts) >= 2:
            component_name = topic_parts[0]
            self.kpi_tracker.increment_kpi(component_name, "failures", 1.0)

    async def _on_error_event(self, message: Message):
        """Handle error events."""
        topic_parts = message.topic.split(".")
        if len(topic_parts) >= 2:
            component_name = topic_parts[0]
            self.kpi_tracker.increment_kpi(component_name, "errors", 1.0)


def create_kpi_connector(
    message_bus: Optional[Layer1MessageBus] = None,
    kpi_tracker: Optional[KPITracker] = None,
) -> KPIConnector:
    """
    Factory function to create KPI connector.

    Args:
        message_bus: Layer 1 message bus instance
        kpi_tracker: KPI tracker instance (optional)

    Returns:
        KPIConnector instance
    """
    if not KPI_TRACKER_AVAILABLE:
        raise ImportError("KPI tracker not available")
    
    return KPIConnector(message_bus=message_bus, kpi_tracker=kpi_tracker)
