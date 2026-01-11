"""
Self-modeling telemetry models for Grace.

These models enable Grace to observe her own execution,
track performance baselines, detect drift, and replay operations.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Float, DateTime,
    JSON, Text, Boolean, Index, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from database.base import BaseModel
import enum


class OperationType(str, enum.Enum):
    """Types of operations Grace can perform."""
    INGESTION = "ingestion"
    RETRIEVAL = "retrieval"
    CHAT_GENERATION = "chat_generation"
    EMBEDDING = "embedding"
    VECTOR_SEARCH = "vector_search"
    CONFIDENCE_SCORING = "confidence_scoring"
    FILE_PROCESSING = "file_processing"
    DATABASE_QUERY = "database_query"
    API_REQUEST = "api_request"
    BACKGROUND_TASK = "background_task"


class OperationStatus(str, enum.Enum):
    """Status of an operation."""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class OperationLog(BaseModel):
    """
    Log of every operation Grace performs.

    Each operation gets a unique run_id that can be used to correlate
    related events and enable replay functionality.
    """
    __tablename__ = "operation_log"

    # Core identification
    run_id = Column(String(36), nullable=False, index=True, unique=True)
    parent_run_id = Column(String(36), nullable=True, index=True)  # For nested operations
    operation_type = Column(SQLEnum(OperationType), nullable=False, index=True)
    operation_name = Column(String(255), nullable=False)  # e.g., "ingest_pdf", "retrieve_hybrid"

    # Timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)  # Milliseconds

    # Status and errors
    status = Column(SQLEnum(OperationStatus), nullable=False, default=OperationStatus.STARTED)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Resource usage
    cpu_percent = Column(Float, nullable=True)  # CPU usage during operation
    memory_mb = Column(Float, nullable=True)  # Memory usage in MB
    gpu_memory_mb = Column(Float, nullable=True)  # GPU memory if available

    # Input/Output tracking
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    input_size_bytes = Column(Integer, nullable=True)
    output_size_bytes = Column(Integer, nullable=True)

    # Quality metrics
    confidence_score = Column(Float, nullable=True)  # For operations that produce scored results
    contradiction_detected = Column(Boolean, nullable=True)

    # Metadata
    input_hash = Column(String(64), nullable=True, index=True)  # SHA256 of inputs for replay
    operation_metadata = Column(JSON, nullable=True)  # Flexible storage for operation-specific data

    # Indexing for performance
    __table_args__ = (
        Index('idx_operation_type_status', 'operation_type', 'status'),
        Index('idx_started_at', 'started_at'),
        Index('idx_duration', 'duration_ms'),
    )

    def __repr__(self):
        return f"<OperationLog(run_id={self.run_id}, type={self.operation_type}, status={self.status})>"


class PerformanceBaseline(BaseModel):
    """
    Baseline performance metrics for each operation type.

    Grace learns what "normal" looks like over time, enabling
    drift detection when operations become slower or less reliable.
    """
    __tablename__ = "performance_baseline"

    operation_type = Column(SQLEnum(OperationType), nullable=False, index=True)
    operation_name = Column(String(255), nullable=False)

    # Statistical baselines
    sample_count = Column(Integer, nullable=False, default=0)
    mean_duration_ms = Column(Float, nullable=True)
    median_duration_ms = Column(Float, nullable=True)
    p95_duration_ms = Column(Float, nullable=True)
    p99_duration_ms = Column(Float, nullable=True)
    std_dev_duration_ms = Column(Float, nullable=True)

    # Success rate
    success_rate = Column(Float, nullable=True)  # 0.0 to 1.0
    failure_count = Column(Integer, nullable=False, default=0)

    # Resource baselines
    mean_cpu_percent = Column(Float, nullable=True)
    mean_memory_mb = Column(Float, nullable=True)

    # Quality baselines
    mean_confidence_score = Column(Float, nullable=True)
    contradiction_rate = Column(Float, nullable=True)

    # Last updated
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    baseline_window_days = Column(Integer, nullable=False, default=7)  # Rolling window

    # Unique constraint on operation type + name
    __table_args__ = (
        Index('idx_operation_baseline', 'operation_type', 'operation_name', unique=True),
    )

    def __repr__(self):
        return f"<PerformanceBaseline(type={self.operation_type}, mean={self.mean_duration_ms}ms)>"


class DriftAlert(BaseModel):
    """
    Alerts when operations drift from their baselines.

    Captures when Grace detects abnormal behavior - slower performance,
    higher failure rates, lower confidence scores, etc.
    """
    __tablename__ = "drift_alert"

    run_id = Column(String(36), nullable=False, index=True)
    operation_type = Column(SQLEnum(OperationType), nullable=False, index=True)
    operation_name = Column(String(255), nullable=False)

    # Drift detection
    drift_type = Column(String(100), nullable=False)  # e.g., "latency", "failure_rate", "confidence"
    baseline_value = Column(Float, nullable=True)
    observed_value = Column(Float, nullable=True)
    deviation_percent = Column(Float, nullable=True)  # How far from baseline

    # Severity
    severity = Column(String(20), nullable=False)  # "low", "medium", "high", "critical"

    # Resolution tracking
    acknowledged = Column(Boolean, nullable=False, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Metadata
    alert_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_drift_severity', 'severity', 'resolved'),
        Index('idx_drift_type', 'drift_type'),
    )

    def __repr__(self):
        return f"<DriftAlert(type={self.drift_type}, severity={self.severity}, resolved={self.resolved})>"


class OperationReplay(BaseModel):
    """
    Replay configuration and results for failed operations.

    When an operation fails, Grace can rerun it with the same inputs
    to debug and compare results.
    """
    __tablename__ = "operation_replay"

    original_run_id = Column(String(36), nullable=False, index=True)
    replay_run_id = Column(String(36), nullable=False, index=True, unique=True)

    # Replay configuration
    replay_reason = Column(String(255), nullable=True)  # Why we're replaying
    replayed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Comparison results
    original_duration_ms = Column(Float, nullable=True)
    replay_duration_ms = Column(Float, nullable=True)

    original_status = Column(String(50), nullable=True)
    replay_status = Column(String(50), nullable=True)

    original_output_hash = Column(String(64), nullable=True)
    replay_output_hash = Column(String(64), nullable=True)
    outputs_match = Column(Boolean, nullable=True)

    # Analysis
    differences = Column(JSON, nullable=True)  # Detailed diff of outputs
    insights = Column(Text, nullable=True)  # Human or AI-generated insights

    __table_args__ = (
        Index('idx_replay_original', 'original_run_id'),
    )

    def __repr__(self):
        return f"<OperationReplay(original={self.original_run_id}, replay={self.replay_run_id})>"


class SystemState(BaseModel):
    """
    Periodic snapshots of Grace's overall system state.

    Enables long-term trend analysis and capacity planning.
    """
    __tablename__ = "system_state"

    # Service health
    ollama_running = Column(Boolean, nullable=False)
    qdrant_connected = Column(Boolean, nullable=False)
    database_connected = Column(Boolean, nullable=False)

    # Database metrics
    db_size_bytes = Column(Integer, nullable=True)
    document_count = Column(Integer, nullable=True)
    chunk_count = Column(Integer, nullable=True)
    chat_count = Column(Integer, nullable=True)
    message_count = Column(Integer, nullable=True)

    # Vector database metrics
    vector_count = Column(Integer, nullable=True)
    index_size_bytes = Column(Integer, nullable=True)

    # Quality metrics
    average_confidence_score = Column(Float, nullable=True)
    contradiction_rate = Column(Float, nullable=True)

    # Resource usage
    cpu_percent = Column(Float, nullable=True)
    memory_percent = Column(Float, nullable=True)
    disk_usage_percent = Column(Float, nullable=True)
    gpu_memory_percent = Column(Float, nullable=True)

    # Operation statistics (last 24h)
    operations_last_24h = Column(Integer, nullable=True)
    failures_last_24h = Column(Integer, nullable=True)
    average_latency_ms = Column(Float, nullable=True)

    # Extended metrics
    state_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_state_timestamp', 'created_at'),
    )

    def __repr__(self):
        return f"<SystemState(timestamp={self.created_at}, ollama={self.ollama_running})>"
