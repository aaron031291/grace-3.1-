"""
TimeSense Connector for Layer 1 Message Bus.
Provides time estimation and operation tracking through Layer 1.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

TIMESENSE_AVAILABLE = False
try:
    from timesense.engine import get_timesense_engine, TimeSenseEngine, EngineStatus
    TIMESENSE_AVAILABLE = True
except ImportError:
    get_timesense_engine = None
    TimeSenseEngine = None
    EngineStatus = None

try:
    from layer1.message_bus import (
        Layer1MessageBus,
        Message,
        ComponentType,
        MessageType,
        get_message_bus,
    )
except ImportError:
    Layer1MessageBus = None
    Message = None
    ComponentType = None
    MessageType = None
    get_message_bus = None


class TimeSenseConnector:
    """
    Connector for TimeSense engine integration with Layer 1.

    Provides:
    - Time estimation for operations
    - Operation tracking and learning
    - Calibration data access
    - Autonomous time-based triggers
    """

    def __init__(
        self,
        message_bus: Optional["Layer1MessageBus"] = None,
        engine: Optional["TimeSenseEngine"] = None,
    ):
        if not TIMESENSE_AVAILABLE:
            raise ImportError("TimeSense engine not available")

        self.message_bus = message_bus or get_message_bus()
        self.engine = engine or get_timesense_engine()
        self.enabled = True
        self._active_operations: Dict[str, datetime] = {}

        self.message_bus.register_component(
            ComponentType.TIMESENSE,
            self
        )
        logger.info("[TIMESENSE-CONNECTOR] Registered with message bus")

        self._register_request_handlers()
        self._subscribe_to_events()
        self._register_autonomous_actions()

    def _register_request_handlers(self):
        """Register request handlers with message bus."""
        self.message_bus.register_request_handler(
            ComponentType.TIMESENSE,
            "estimate_duration",
            self._handle_estimate_duration,
        )
        self.message_bus.register_request_handler(
            ComponentType.TIMESENSE,
            "track_operation",
            self._handle_track_operation,
        )
        self.message_bus.register_request_handler(
            ComponentType.TIMESENSE,
            "get_calibration",
            self._handle_get_calibration,
        )
        self.message_bus.register_request_handler(
            ComponentType.TIMESENSE,
            "timesense.get_stats",
            self._handle_get_stats,
        )
        self.message_bus.register_request_handler(
            ComponentType.TIMESENSE,
            "timesense.predict",
            self._handle_predict,
        )

    def _subscribe_to_events(self):
        """Subscribe to relevant events."""
        self.message_bus.subscribe(
            "operation.started",
            self._on_operation_started,
        )
        self.message_bus.subscribe(
            "operation.completed",
            self._on_operation_completed,
        )

    def _register_autonomous_actions(self):
        """Register autonomous actions for time-based triggers."""
        self.message_bus.register_autonomous_action(
            trigger_event="rag.query_received",
            action=self._auto_estimate_rag_query,
            component=ComponentType.TIMESENSE,
            description="Auto-estimate RAG query duration",
        )
        self.message_bus.register_autonomous_action(
            trigger_event="llm.request",
            action=self._auto_estimate_llm_request,
            component=ComponentType.TIMESENSE,
            description="Auto-estimate LLM request duration",
        )
        self.message_bus.register_autonomous_action(
            trigger_event="ingestion.file_processing",
            action=self._auto_estimate_file_processing,
            component=ComponentType.TIMESENSE,
            description="Auto-estimate file processing duration",
        )

    async def _handle_estimate_duration(self, message: Message) -> Dict[str, Any]:
        """Handle estimate duration request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        operation_type = message.payload.get("operation_type")
        size = message.payload.get("size", 1.0)
        model_name = message.payload.get("model_name")

        try:
            from timesense.primitives import PrimitiveType

            primitive_map = {
                "file_read": PrimitiveType.FILE_READ,
                "file_write": PrimitiveType.FILE_WRITE,
                "embedding": PrimitiveType.EMBEDDING,
                "llm_inference": PrimitiveType.LLM_INFERENCE,
                "vector_search": PrimitiveType.VECTOR_SEARCH,
                "chunking": PrimitiveType.CHUNKING,
                "complex_operation": PrimitiveType.COMPLEX_OPERATION,
            }

            primitive_type = primitive_map.get(operation_type, PrimitiveType.COMPLEX_OPERATION)
            prediction = self.engine.predict(primitive_type, size, model_name)

            await self.message_bus.publish(
                topic="timesense.estimation_ready",
                payload={
                    "operation_type": operation_type,
                    "estimated_ms": prediction.predicted_ms,
                    "confidence": prediction.confidence,
                    "p95_ms": prediction.p95_ms,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                from_component=ComponentType.TIMESENSE,
            )

            return {
                "success": True,
                "estimated_ms": prediction.predicted_ms,
                "confidence": prediction.confidence,
                "p95_ms": prediction.p95_ms,
                "p5_ms": prediction.p5_ms,
            }

        except Exception as e:
            logger.error(f"[TIMESENSE-CONNECTOR] Estimation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_track_operation(self, message: Message) -> Dict[str, Any]:
        """Handle track operation request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        operation_id = message.payload.get("operation_id")
        operation_type = message.payload.get("operation_type")
        action = message.payload.get("action", "start")
        size = message.payload.get("size", 1.0)

        try:
            if action == "start":
                task_id = self.engine.start_task(
                    primitive_type=operation_type,
                    size=size,
                    metadata={"operation_id": operation_id}
                )
                self._active_operations[operation_id] = datetime.utcnow()
                return {"success": True, "task_id": task_id}

            elif action == "complete":
                if operation_id in self._active_operations:
                    start_time = self._active_operations.pop(operation_id)
                    duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                    return {
                        "success": True,
                        "duration_ms": duration_ms,
                        "operation_id": operation_id,
                    }
                return {"success": False, "error": "Operation not found"}

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"[TIMESENSE-CONNECTOR] Track operation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_get_calibration(self, message: Message) -> Dict[str, Any]:
        """Handle get calibration request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        try:
            stats = self.engine.stats
            profiles = self.engine.profile_manager.get_all_profiles()

            calibration_data = {
                "status": stats.status.value if stats.status else "unknown",
                "last_calibration": stats.last_calibration.isoformat() if stats.last_calibration else None,
                "calibration_count": stats.calibration_count,
                "total_profiles": stats.total_profiles,
                "stable_profiles": stats.stable_profiles,
                "stale_profiles": stats.stale_profiles,
                "average_confidence": stats.average_confidence,
                "profiles": [
                    {
                        "primitive_type": p.primitive_type.value,
                        "status": p.status.value,
                        "confidence": p.confidence,
                        "sample_count": p.sample_count,
                    }
                    for p in profiles[:20]
                ],
            }

            await self.message_bus.publish(
                topic="timesense.calibration_updated",
                payload=calibration_data,
                from_component=ComponentType.TIMESENSE,
            )

            return {"success": True, **calibration_data}

        except Exception as e:
            logger.error(f"[TIMESENSE-CONNECTOR] Get calibration failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_get_stats(self, message: Message) -> Dict[str, Any]:
        """Handle get stats request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        try:
            stats = self.engine.stats.to_dict()
            return {"success": True, **stats}
        except Exception as e:
            logger.error(f"[TIMESENSE-CONNECTOR] Get stats failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_predict(self, message: Message) -> Dict[str, Any]:
        """Handle predict request."""
        return await self._handle_estimate_duration(message)

    async def _on_operation_started(self, message: Message):
        """Handle operation started event."""
        if not self.enabled:
            return

        operation_id = message.payload.get("operation_id")
        operation_type = message.payload.get("operation_type")
        size = message.payload.get("size", 1.0)

        if operation_id:
            self._active_operations[operation_id] = datetime.utcnow()
            logger.debug(f"[TIMESENSE-CONNECTOR] Tracking operation: {operation_id}")

    async def _on_operation_completed(self, message: Message):
        """Handle operation completed event."""
        if not self.enabled:
            return

        operation_id = message.payload.get("operation_id")
        actual_duration_ms = message.payload.get("duration_ms")

        if operation_id and operation_id in self._active_operations:
            start_time = self._active_operations.pop(operation_id)
            if not actual_duration_ms:
                actual_duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.debug(f"[TIMESENSE-CONNECTOR] Operation completed: {operation_id} ({actual_duration_ms:.1f}ms)")

    async def _auto_estimate_rag_query(self, message: Message):
        """Autonomous action: estimate RAG query duration."""
        if not self.enabled:
            return

        try:
            query_tokens = message.payload.get("query_tokens", 50)
            top_k = message.payload.get("top_k", 10)

            prediction = self.engine.estimate_retrieval(query_tokens, top_k)

            await self.message_bus.publish(
                topic="timesense.estimation_ready",
                payload={
                    "operation_type": "rag_query",
                    "estimated_ms": prediction.predicted_ms,
                    "confidence": prediction.confidence,
                    "correlation_id": message.correlation_id,
                },
                from_component=ComponentType.TIMESENSE,
            )
        except Exception as e:
            logger.debug(f"[TIMESENSE-CONNECTOR] Auto-estimate RAG failed: {e}")

    async def _auto_estimate_llm_request(self, message: Message):
        """Autonomous action: estimate LLM request duration."""
        if not self.enabled:
            return

        try:
            prompt_tokens = message.payload.get("prompt_tokens", 100)
            max_tokens = message.payload.get("max_tokens", 500)
            model_name = message.payload.get("model")

            prediction = self.engine.estimate_llm_response(prompt_tokens, max_tokens, model_name)

            await self.message_bus.publish(
                topic="timesense.estimation_ready",
                payload={
                    "operation_type": "llm_request",
                    "estimated_ms": prediction.predicted_ms,
                    "confidence": prediction.confidence,
                    "correlation_id": message.correlation_id,
                },
                from_component=ComponentType.TIMESENSE,
            )
        except Exception as e:
            logger.debug(f"[TIMESENSE-CONNECTOR] Auto-estimate LLM failed: {e}")

    async def _auto_estimate_file_processing(self, message: Message):
        """Autonomous action: estimate file processing duration."""
        if not self.enabled:
            return

        try:
            file_size = message.payload.get("file_size", 1024)
            include_embedding = message.payload.get("include_embedding", True)

            prediction = self.engine.estimate_file_processing(file_size, include_embedding)

            await self.message_bus.publish(
                topic="timesense.estimation_ready",
                payload={
                    "operation_type": "file_processing",
                    "estimated_ms": prediction.predicted_ms,
                    "confidence": prediction.confidence,
                    "correlation_id": message.correlation_id,
                },
                from_component=ComponentType.TIMESENSE,
            )
        except Exception as e:
            logger.debug(f"[TIMESENSE-CONNECTOR] Auto-estimate file processing failed: {e}")


def create_timesense_connector(
    message_bus: Optional["Layer1MessageBus"] = None,
    engine: Optional["TimeSenseEngine"] = None,
) -> TimeSenseConnector:
    """
    Factory function to create TimeSense connector.

    Args:
        message_bus: Layer 1 message bus instance
        engine: TimeSense engine instance (optional)

    Returns:
        TimeSenseConnector instance

    Raises:
        ImportError: If TimeSense engine is not available
    """
    if not TIMESENSE_AVAILABLE:
        raise ImportError("TimeSense engine not available")

    return TimeSenseConnector(message_bus=message_bus, engine=engine)
