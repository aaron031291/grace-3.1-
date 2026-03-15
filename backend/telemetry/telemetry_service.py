"""
Telemetry service for Grace's self-modeling mechanism.

INTEGRATED with LLM Orchestrator for health monitoring.

This service provides context managers and utilities for tracking
operations, measuring performance, and enabling replay functionality.

Health checks prioritize LLM Orchestrator availability over direct
Ollama client access to ensure consistent system status reporting.
"""
import uuid
import time
import hashlib
import json
import traceback
import psutil
import logging
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
from sqlalchemy.orm import Session

from models.telemetry_models import (
    OperationLog, OperationType, OperationStatus,
    PerformanceBaseline, DriftAlert, SystemState
)
from database.session import get_session

logger = logging.getLogger(__name__)


class TelemetryService:
    """
    Service for emitting and tracking telemetry events.

    Provides context managers for operation tracking, baseline learning,
    and drift detection.
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self._process = psutil.Process()

    @contextmanager
    def track_operation(
        self,
        operation_type: OperationType,
        operation_name: str,
        parent_run_id: Optional[str] = None,
        input_data: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """
        Context manager that tracks an operation from start to finish.

        Usage:
            with telemetry.track_operation(
                OperationType.INGESTION,
                "ingest_pdf",
                input_data={"filename": "doc.pdf"}
            ) as run_id:
                # Do work
                result = process_document()
                return result

        Args:
            operation_type: Type of operation being performed
            operation_name: Specific name of the operation
            parent_run_id: ID of parent operation (for nested tracking)
            input_data: Input data for hashing and replay
            metadata: Additional metadata to store

        Yields:
            run_id: Unique identifier for this operation run
        """
        run_id = str(uuid.uuid4())
        session = self.session or next(get_session())
        close_session = self.session is None

        # Compute input hash for replay
        input_hash = None
        if input_data is not None:
            input_str = json.dumps(input_data, sort_keys=True, default=str)
            input_hash = hashlib.sha256(input_str.encode()).hexdigest()

        # Initial resource measurement
        cpu_before = self._process.cpu_percent()
        memory_before = self._process.memory_info().rss / (1024 * 1024)  # MB

        # Create operation log entry
        operation = OperationLog(
            run_id=run_id,
            parent_run_id=parent_run_id,
            operation_type=operation_type,
            operation_name=operation_name,
            started_at=datetime.now(timezone.utc),
            status=OperationStatus.STARTED,
            input_hash=input_hash,
            metadata=metadata or {}
        )

        session.add(operation)
        try:
            session.commit()
        except Exception as e:
            logger.warning(f"Failed to log operation start: {e}")
            if close_session:
                session.close()
            # Continue execution even if logging fails
            yield run_id
            return

        start_time = time.time()

        try:
            # Yield control to the operation
            yield run_id

            # Operation completed successfully
            duration_ms = (time.time() - start_time) * 1000

            # Measure resource usage
            cpu_after = self._process.cpu_percent()
            memory_after = self._process.memory_info().rss / (1024 * 1024)

            operation.completed_at = datetime.now(timezone.utc)
            operation.duration_ms = duration_ms
            operation.status = OperationStatus.COMPLETED
            operation.cpu_percent = (cpu_before + cpu_after) / 2
            operation.memory_mb = memory_after - memory_before

            session.commit()

            # Check for drift and update baselines
            self._check_drift(session, operation)
            self._update_baseline(session, operation)

        except Exception as e:
            # Operation failed
            duration_ms = (time.time() - start_time) * 1000

            operation.completed_at = datetime.now(timezone.utc)
            operation.duration_ms = duration_ms
            operation.status = OperationStatus.FAILED
            operation.error_message = str(e)
            operation.error_traceback = traceback.format_exc()

            try:
                session.commit()
            except Exception as commit_error:
                logger.error(f"Failed to log operation failure: {commit_error}")

            # Check for drift even on failure
            try:
                self._check_drift(session, operation)
                self._update_baseline(session, operation)
            except Exception as drift_error:
                logger.warning(f"Drift detection failed: {drift_error}")

            # Re-raise the original exception
            raise

        finally:
            if close_session:
                session.close()

    def record_tokens(
        self,
        run_id: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None
    ):
        """Record token counts for an operation."""
        session = self.session or next(get_session())
        close_session = self.session is None

        try:
            operation = session.query(OperationLog).filter(
                OperationLog.run_id == run_id
            ).first()

            if operation:
                if input_tokens is not None:
                    operation.input_tokens = input_tokens
                if output_tokens is not None:
                    operation.output_tokens = output_tokens
                session.commit()
        except Exception as e:
            logger.warning(f"Failed to record tokens: {e}")
        finally:
            if close_session:
                session.close()

    def record_confidence(
        self,
        run_id: str,
        confidence_score: float,
        contradiction_detected: bool = False
    ):
        """Record confidence metrics for an operation."""
        session = self.session or next(get_session())
        close_session = self.session is None

        try:
            operation = session.query(OperationLog).filter(
                OperationLog.run_id == run_id
            ).first()

            if operation:
                operation.confidence_score = confidence_score
                operation.contradiction_detected = contradiction_detected
                session.commit()
        except Exception as e:
            logger.warning(f"Failed to record confidence: {e}")
        finally:
            if close_session:
                session.close()

    def _update_baseline(self, session: Session, operation: OperationLog):
        """Update performance baselines based on completed operation."""
        try:
            # Get or create baseline
            baseline = session.query(PerformanceBaseline).filter(
                PerformanceBaseline.operation_type == operation.operation_type,
                PerformanceBaseline.operation_name == operation.operation_name
            ).first()

            if not baseline:
                baseline = PerformanceBaseline(
                    operation_type=operation.operation_type,
                    operation_name=operation.operation_name,
                    sample_count=0,
                    mean_duration_ms=0.0,
                    success_rate=1.0
                )
                session.add(baseline)

            # Get recent operations for rolling window calculation
            window_days = baseline.baseline_window_days if baseline.baseline_window_days is not None else 7
            window_start = datetime.now(timezone.utc) - timedelta(days=window_days)
            recent_ops = session.query(OperationLog).filter(
                OperationLog.operation_type == operation.operation_type,
                OperationLog.operation_name == operation.operation_name,
                OperationLog.completed_at >= window_start,
                OperationLog.status.in_([OperationStatus.COMPLETED, OperationStatus.FAILED])
            ).all()

            if recent_ops:
                # Calculate statistics
                durations = [op.duration_ms for op in recent_ops if op.duration_ms is not None]
                if durations:
                    durations.sort()
                    baseline.sample_count = len(durations)
                    baseline.mean_duration_ms = sum(durations) / len(durations)
                    baseline.median_duration_ms = durations[len(durations) // 2]
                    baseline.p95_duration_ms = durations[int(len(durations) * 0.95)]
                    baseline.p99_duration_ms = durations[int(len(durations) * 0.99)]

                    # Standard deviation
                    mean = baseline.mean_duration_ms
                    variance = sum((d - mean) ** 2 for d in durations) / len(durations)
                    baseline.std_dev_duration_ms = variance ** 0.5

                # Success rate
                completed = sum(1 for op in recent_ops if op.status == OperationStatus.COMPLETED)
                baseline.success_rate = completed / len(recent_ops)
                baseline.failure_count = len(recent_ops) - completed

                # Resource usage
                cpu_values = [op.cpu_percent for op in recent_ops if op.cpu_percent is not None]
                if cpu_values:
                    baseline.mean_cpu_percent = sum(cpu_values) / len(cpu_values)

                memory_values = [op.memory_mb for op in recent_ops if op.memory_mb is not None]
                if memory_values:
                    baseline.mean_memory_mb = sum(memory_values) / len(memory_values)

                # Quality metrics
                confidence_values = [
                    op.confidence_score for op in recent_ops
                    if op.confidence_score is not None
                ]
                if confidence_values:
                    baseline.mean_confidence_score = sum(confidence_values) / len(confidence_values)

                contradictions = sum(
                    1 for op in recent_ops
                    if op.contradiction_detected is True
                )
                baseline.contradiction_rate = contradictions / len(recent_ops)

                baseline.last_updated = datetime.now(timezone.utc)
                session.commit()

        except Exception as e:
            logger.warning(f"Failed to update baseline: {e}")
            session.rollback()

    def _check_drift(self, session: Session, operation: OperationLog):
        """Check if operation has drifted from baseline and create alert if needed."""
        try:
            baseline = session.query(PerformanceBaseline).filter(
                PerformanceBaseline.operation_type == operation.operation_type,
                PerformanceBaseline.operation_name == operation.operation_name
            ).first()

            if not baseline or baseline.sample_count < 10:
                # Need at least 10 samples to establish baseline
                return

            alerts = []

            # Check latency drift
            if operation.duration_ms and baseline.mean_duration_ms:
                deviation = (
                    (operation.duration_ms - baseline.mean_duration_ms) /
                    baseline.mean_duration_ms * 100
                )

                if abs(deviation) > 50:  # 50% slower or faster
                    severity = "high" if abs(deviation) > 100 else "medium"
                    alerts.append({
                        "drift_type": "latency",
                        "baseline_value": baseline.mean_duration_ms,
                        "observed_value": operation.duration_ms,
                        "deviation_percent": deviation,
                        "severity": severity
                    })

            # Check failure rate drift
            if operation.status == OperationStatus.FAILED:
                if baseline.success_rate > 0.9:  # Normally reliable
                    alerts.append({
                        "drift_type": "failure",
                        "baseline_value": baseline.success_rate,
                        "observed_value": 0.0,
                        "deviation_percent": -100.0,
                        "severity": "high"
                    })

            # Check confidence drift
            if operation.confidence_score and baseline.mean_confidence_score:
                deviation = (
                    (operation.confidence_score - baseline.mean_confidence_score) /
                    baseline.mean_confidence_score * 100
                )

                if deviation < -20:  # 20% drop in confidence
                    alerts.append({
                        "drift_type": "confidence",
                        "baseline_value": baseline.mean_confidence_score,
                        "observed_value": operation.confidence_score,
                        "deviation_percent": deviation,
                        "severity": "medium"
                    })

            # Create drift alerts
            for alert_data in alerts:
                alert = DriftAlert(
                    run_id=operation.run_id,
                    operation_type=operation.operation_type,
                    operation_name=operation.operation_name,
                    **alert_data
                )
                session.add(alert)

            if alerts:
                session.commit()
                logger.warning(
                    f"Drift detected for {operation.operation_name}: "
                    f"{len(alerts)} alert(s) created"
                )

        except Exception as e:
            logger.warning(f"Drift detection failed: {e}")
            session.rollback()

    def capture_system_state(self) -> SystemState:
        """Capture current system state snapshot."""
        session = self.session or next(get_session())
        close_session = self.session is None

        try:
            # Import here to avoid circular dependencies
            from vector_db.client import get_qdrant_client
            from models.database_models import Document, DocumentChunk, Chat, ChatHistory

            # Check LLM health - prefer orchestrator over direct Ollama
            ollama_running = False
            try:
                # Try orchestrator first (preferred)
                from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
                orchestrator = get_llm_orchestrator()
                ollama_running = orchestrator is not None
                if ollama_running:
                    logger.debug("[TELEMETRY] LLM health via orchestrator: OK")
            except Exception:
                pass

            # Fallback to direct Ollama check
            if not ollama_running:
                try:
                    from ollama_client.client import check_ollama_running
                    ollama_running = check_ollama_running()
                    if ollama_running:
                        logger.debug("[TELEMETRY] LLM health via direct client: OK")
                except Exception:
                    pass

            qdrant_connected = False
            vector_count = None
            try:
                qdrant = get_qdrant_client()
                collection_info = qdrant.get_collection_info()
                qdrant_connected = True
                vector_count = collection_info.vectors_count if collection_info else None
            except Exception:
                pass

            # Database metrics
            document_count = session.query(Document).count()
            chunk_count = session.query(DocumentChunk).count()
            chat_count = session.query(Chat).count()
            message_count = session.query(ChatHistory).count()

            # Quality metrics
            avg_confidence = session.query(
                Document.confidence_score
            ).filter(
                Document.confidence_score.isnot(None)
            ).all()
            average_confidence_score = (
                sum(c[0] for c in avg_confidence) / len(avg_confidence)
                if avg_confidence else None
            )

            # System resources
            cpu_percent = self._process.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Create snapshot
            state = SystemState(
                ollama_running=ollama_running,
                qdrant_connected=qdrant_connected,
                database_connected=True,
                document_count=document_count,
                chunk_count=chunk_count,
                chat_count=chat_count,
                message_count=message_count,
                vector_count=vector_count,
                average_confidence_score=average_confidence_score,
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent
            )

            session.add(state)
            session.commit()

            logger.info(f"System state captured: {document_count} docs, {chunk_count} chunks")
            return state

        except Exception as e:
            logger.error(f"Failed to capture system state: {e}")
            raise
        finally:
            if close_session:
                session.close()


# Global telemetry service instance
_telemetry_service: Optional[TelemetryService] = None


def get_telemetry_service(session: Optional[Session] = None) -> TelemetryService:
    """Get or create the global telemetry service instance."""
    global _telemetry_service
    if _telemetry_service is None or session is not None:
        _telemetry_service = TelemetryService(session=session)
    return _telemetry_service
