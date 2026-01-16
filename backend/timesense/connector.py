"""
TimeSense Connector - Layer 1 Message Bus Integration

Connects TimeSense to Grace's event-driven architecture.
Subscribes to task events and emits time estimates.

Events:
- Subscribes: TASK_STARTED, TASK_FINISHED, ingestion.*, retrieval.*
- Emits: TIME_ESTIMATE_UPDATED, CALIBRATION_COMPLETE, PROFILE_STALE
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from timesense.engine import TimeSenseEngine, get_timesense_engine, EngineStatus
from timesense.primitives import PrimitiveType
from timesense.predictor import PredictionResult

logger = logging.getLogger(__name__)


# Define ComponentType locally to avoid circular imports
# This should match the Layer1 ComponentType enum
class TimeSenseComponentType:
    """Component type identifier for TimeSense."""
    TIMESENSE = "timesense"


class TimeSenseConnector:
    """
    Connector between TimeSense and Layer 1 Message Bus.

    Handles:
    - Automatic task tracking from events
    - Time estimate publishing
    - Calibration event notifications
    - Integration with diagnostic system
    """

    def __init__(
        self,
        engine: Optional[TimeSenseEngine] = None,
        message_bus: Optional[Any] = None
    ):
        self.engine = engine or get_timesense_engine()
        self.message_bus = message_bus
        self._registered = False

    def register(self, message_bus: Any):
        """
        Register with the message bus.

        Sets up subscriptions and request handlers.
        """
        self.message_bus = message_bus

        # Import ComponentType from layer1
        try:
            from layer1.message_bus import ComponentType

            # Register component
            self.message_bus.register_component(
                ComponentType.TIMESENSE if hasattr(ComponentType, 'TIMESENSE') else 'timesense',
                self.engine
            )
        except (ImportError, AttributeError):
            logger.warning("[TIMESENSE] Could not register with message bus ComponentType")

        # Subscribe to events
        self._subscribe_to_events()

        # Register request handlers
        self._register_request_handlers()

        # Register autonomous actions
        self._register_autonomous_actions()

        self._registered = True
        logger.info("[TIMESENSE] Registered with message bus")

    def _subscribe_to_events(self):
        """Subscribe to relevant events."""
        if not self.message_bus:
            return

        # Subscribe to task lifecycle events
        self.message_bus.subscribe("task.started", self._on_task_started)
        self.message_bus.subscribe("task.finished", self._on_task_finished)
        self.message_bus.subscribe("task.failed", self._on_task_failed)

        # Subscribe to ingestion events for file processing tracking
        self.message_bus.subscribe("ingestion.file_uploaded", self._on_file_uploaded)
        self.message_bus.subscribe("ingestion.file_processed", self._on_file_processed)
        self.message_bus.subscribe("ingestion.processing_failed", self._on_processing_failed)

        # Subscribe to retrieval events
        self.message_bus.subscribe("retrieval.query_started", self._on_retrieval_started)
        self.message_bus.subscribe("retrieval.query_completed", self._on_retrieval_completed)

        # Subscribe to LLM events
        self.message_bus.subscribe("llm.generation_started", self._on_llm_started)
        self.message_bus.subscribe("llm.generation_completed", self._on_llm_completed)

        # Subscribe to embedding events
        self.message_bus.subscribe("embedding.started", self._on_embedding_started)
        self.message_bus.subscribe("embedding.completed", self._on_embedding_completed)

        logger.info("[TIMESENSE] Subscribed to task and operation events")

    def _register_request_handlers(self):
        """Register handlers for request-response patterns."""
        if not self.message_bus:
            return

        try:
            from layer1.message_bus import ComponentType
            component = ComponentType.TIMESENSE if hasattr(ComponentType, 'TIMESENSE') else None

            if component:
                # Handler for time estimates
                self.message_bus.register_request_handler(
                    component,
                    "estimate_time",
                    self._handle_estimate_request
                )

                # Handler for status
                self.message_bus.register_request_handler(
                    component,
                    "get_status",
                    self._handle_status_request
                )

                # Handler for profile info
                self.message_bus.register_request_handler(
                    component,
                    "get_profile",
                    self._handle_profile_request
                )

                logger.info("[TIMESENSE] Registered request handlers")
        except Exception as e:
            logger.warning(f"[TIMESENSE] Could not register request handlers: {e}")

    def _register_autonomous_actions(self):
        """Register autonomous actions triggered by events."""
        if not self.message_bus:
            return

        try:
            from layer1.message_bus import ComponentType
            component = ComponentType.TIMESENSE if hasattr(ComponentType, 'TIMESENSE') else None

            if component:
                # Auto-recalibrate when errors are high
                self.message_bus.register_autonomous_action(
                    trigger_event="timesense.prediction_error_high",
                    action=self._auto_recalibrate,
                    component=component,
                    description="Auto-recalibrate when prediction errors are high",
                    conditions=[lambda msg: msg.payload.get("error_rate", 0) > 0.3]
                )

                logger.info("[TIMESENSE] Registered autonomous actions")
        except Exception as e:
            logger.warning(f"[TIMESENSE] Could not register autonomous actions: {e}")

    # ================================================================
    # EVENT HANDLERS
    # ================================================================

    async def _on_task_started(self, message: Any):
        """Handle task started event."""
        payload = message.payload
        task_id = payload.get("task_id")
        primitive = payload.get("primitive_type")
        size = payload.get("size", 0)

        if not task_id:
            return

        primitive_type = None
        if primitive:
            try:
                primitive_type = PrimitiveType(primitive)
            except ValueError:
                pass

        prediction = self.engine.start_task(
            task_id=task_id,
            primitive_type=primitive_type,
            size=size,
            metadata=payload.get("metadata", {})
        )

        # Emit time estimate
        if prediction:
            await self._emit_time_estimate(task_id, prediction)

    async def _on_task_finished(self, message: Any):
        """Handle task finished event."""
        payload = message.payload
        task_id = payload.get("task_id")
        actual_size = payload.get("actual_size")

        if not task_id:
            return

        actual_ms = self.engine.end_task(task_id, actual_size)

        if actual_ms:
            task = self.engine.get_task(task_id)
            if task and task.prediction:
                # Check prediction accuracy
                error_ratio = abs(actual_ms - task.prediction.p50_ms) / task.prediction.p50_ms
                if error_ratio > 0.5:
                    await self._emit_prediction_error(task_id, task.prediction, actual_ms)

    async def _on_task_failed(self, message: Any):
        """Handle task failed event."""
        payload = message.payload
        task_id = payload.get("task_id")

        if task_id:
            self.engine.end_task(task_id)

    async def _on_file_uploaded(self, message: Any):
        """Handle file upload for time estimation."""
        payload = message.payload
        file_size = payload.get("file_size", 0)
        file_id = payload.get("file_id") or payload.get("document_id")

        if file_size > 0 and file_id:
            prediction = self.engine.estimate_file_processing(file_size)

            # Start tracking
            self.engine.start_task(
                task_id=f"file_process_{file_id}",
                size=file_size,
                metadata={"file_id": file_id, "operation": "file_processing"}
            )

            await self._emit_time_estimate(f"file_process_{file_id}", prediction)

    async def _on_file_processed(self, message: Any):
        """Handle file processing complete."""
        payload = message.payload
        file_id = payload.get("file_id") or payload.get("document_id")

        if file_id:
            self.engine.end_task(f"file_process_{file_id}")

    async def _on_processing_failed(self, message: Any):
        """Handle file processing failure."""
        payload = message.payload
        file_id = payload.get("file_id") or payload.get("document_id")

        if file_id:
            self.engine.end_task(f"file_process_{file_id}")

    async def _on_retrieval_started(self, message: Any):
        """Handle retrieval query started."""
        payload = message.payload
        query_id = payload.get("query_id")
        query_tokens = payload.get("query_tokens", 50)
        top_k = payload.get("top_k", 10)

        if query_id:
            prediction = self.engine.estimate_retrieval(
                query_tokens=query_tokens,
                top_k=top_k
            )

            self.engine.start_task(
                task_id=f"retrieval_{query_id}",
                primitive_type=PrimitiveType.VECTOR_SEARCH,
                metadata={"query_id": query_id}
            )

            await self._emit_time_estimate(f"retrieval_{query_id}", prediction)

    async def _on_retrieval_completed(self, message: Any):
        """Handle retrieval query completed."""
        payload = message.payload
        query_id = payload.get("query_id")

        if query_id:
            self.engine.end_task(f"retrieval_{query_id}")

    async def _on_llm_started(self, message: Any):
        """Handle LLM generation started."""
        payload = message.payload
        request_id = payload.get("request_id")
        prompt_tokens = payload.get("prompt_tokens", 100)
        max_tokens = payload.get("max_tokens", 500)
        model_name = payload.get("model_name")

        if request_id:
            prediction = self.engine.estimate_llm_response(
                prompt_tokens=prompt_tokens,
                max_output_tokens=max_tokens,
                model_name=model_name
            )

            self.engine.start_task(
                task_id=f"llm_{request_id}",
                primitive_type=PrimitiveType.LLM_TOKENS_GENERATE,
                size=max_tokens,
                metadata={"request_id": request_id, "model": model_name}
            )

            await self._emit_time_estimate(f"llm_{request_id}", prediction)

    async def _on_llm_completed(self, message: Any):
        """Handle LLM generation completed."""
        payload = message.payload
        request_id = payload.get("request_id")
        actual_tokens = payload.get("actual_tokens")

        if request_id:
            self.engine.end_task(f"llm_{request_id}", actual_tokens)

    async def _on_embedding_started(self, message: Any):
        """Handle embedding started."""
        payload = message.payload
        batch_id = payload.get("batch_id")
        num_tokens = payload.get("num_tokens", 100)

        if batch_id:
            prediction = self.engine.predict(
                PrimitiveType.EMBED_TEXT,
                num_tokens
            )

            self.engine.start_task(
                task_id=f"embed_{batch_id}",
                primitive_type=PrimitiveType.EMBED_TEXT,
                size=num_tokens
            )

            await self._emit_time_estimate(f"embed_{batch_id}", prediction)

    async def _on_embedding_completed(self, message: Any):
        """Handle embedding completed."""
        payload = message.payload
        batch_id = payload.get("batch_id")

        if batch_id:
            self.engine.end_task(f"embed_{batch_id}")

    # ================================================================
    # REQUEST HANDLERS
    # ================================================================

    async def _handle_estimate_request(self, message: Any) -> Dict[str, Any]:
        """Handle time estimate request."""
        payload = message.payload
        primitive = payload.get("primitive_type")
        size = payload.get("size", 0)
        model_name = payload.get("model_name")

        if not primitive:
            return {"error": "primitive_type required"}

        try:
            primitive_type = PrimitiveType(primitive)
        except ValueError:
            return {"error": f"Unknown primitive type: {primitive}"}

        prediction = self.engine.predict(primitive_type, size, model_name)
        return prediction.to_dict()

    async def _handle_status_request(self, message: Any) -> Dict[str, Any]:
        """Handle status request."""
        return self.engine.get_status()

    async def _handle_profile_request(self, message: Any) -> Dict[str, Any]:
        """Handle profile info request."""
        payload = message.payload
        primitive = payload.get("primitive_type")

        if not primitive:
            return self.engine.get_profile_summary()

        try:
            primitive_type = PrimitiveType(primitive)
        except ValueError:
            return {"error": f"Unknown primitive type: {primitive}"}

        profile = self.engine.get_profile(primitive_type)
        if profile:
            return profile.to_dict()
        return {"error": "Profile not found"}

    # ================================================================
    # EMIT EVENTS
    # ================================================================

    async def _emit_time_estimate(self, task_id: str, prediction: PredictionResult):
        """Emit time estimate event."""
        if not self.message_bus:
            return

        try:
            from layer1.message_bus import ComponentType
            component = ComponentType.TIMESENSE if hasattr(ComponentType, 'TIMESENSE') else None

            await self.message_bus.publish(
                topic="timesense.estimate_updated",
                payload={
                    "task_id": task_id,
                    "estimate": prediction.to_dict(),
                    "p50_ms": prediction.p50_ms,
                    "p95_ms": prediction.p95_ms,
                    "confidence": prediction.confidence,
                    "human_readable": prediction.human_readable()
                },
                from_component=component or "timesense",
                priority=3
            )
        except Exception as e:
            logger.debug(f"[TIMESENSE] Could not emit time estimate: {e}")

    async def _emit_prediction_error(
        self,
        task_id: str,
        prediction: PredictionResult,
        actual_ms: float
    ):
        """Emit prediction error event."""
        if not self.message_bus:
            return

        error_rate = abs(actual_ms - prediction.p50_ms) / prediction.p50_ms

        try:
            from layer1.message_bus import ComponentType
            component = ComponentType.TIMESENSE if hasattr(ComponentType, 'TIMESENSE') else None

            await self.message_bus.publish(
                topic="timesense.prediction_error_high",
                payload={
                    "task_id": task_id,
                    "predicted_ms": prediction.p50_ms,
                    "actual_ms": actual_ms,
                    "error_rate": error_rate,
                    "primitive_type": prediction.primitive_type.value if prediction.primitive_type else None
                },
                from_component=component or "timesense",
                priority=5
            )
        except Exception as e:
            logger.debug(f"[TIMESENSE] Could not emit prediction error: {e}")

    async def emit_calibration_complete(self, report: Any):
        """Emit calibration complete event."""
        if not self.message_bus:
            return

        try:
            from layer1.message_bus import ComponentType
            component = ComponentType.TIMESENSE if hasattr(ComponentType, 'TIMESENSE') else None

            await self.message_bus.publish(
                topic="timesense.calibration_complete",
                payload={
                    "duration_seconds": report.duration_seconds,
                    "primitives_calibrated": report.primitives_calibrated,
                    "measurements_collected": report.measurements_collected,
                    "errors": report.errors
                },
                from_component=component or "timesense",
                priority=4
            )
        except Exception as e:
            logger.debug(f"[TIMESENSE] Could not emit calibration complete: {e}")

    # ================================================================
    # AUTONOMOUS ACTIONS
    # ================================================================

    async def _auto_recalibrate(self, message: Any):
        """Automatically recalibrate when errors are high."""
        logger.info("[TIMESENSE] Auto-recalibrating due to high prediction errors...")

        primitive = message.payload.get("primitive_type")
        if primitive:
            try:
                primitive_type = PrimitiveType(primitive)
                self.engine.force_recalibrate(primitive_type)
            except ValueError:
                pass
        else:
            self.engine.force_recalibrate()


# Global connector instance
_timesense_connector: Optional[TimeSenseConnector] = None


def get_timesense_connector(
    engine: Optional[TimeSenseEngine] = None
) -> TimeSenseConnector:
    """Get or create the global TimeSense connector."""
    global _timesense_connector
    if _timesense_connector is None:
        _timesense_connector = TimeSenseConnector(engine)
    return _timesense_connector


def initialize_timesense_connector(message_bus: Any) -> TimeSenseConnector:
    """Initialize and register the TimeSense connector."""
    connector = get_timesense_connector()
    connector.register(message_bus)
    return connector
