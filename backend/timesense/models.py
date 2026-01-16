"""
TimeSense Database Models

SQLAlchemy models for persisting time profiles and calibration data.
Integrates with Grace's existing database infrastructure.
"""

import enum
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Float, DateTime,
    JSON, Text, Boolean, Index, Enum as SQLEnum, ForeignKey
)
from sqlalchemy.orm import relationship

# Import base model from Grace's database
try:
    from database.base import BaseModel
except ImportError:
    # Fallback for standalone testing
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()

    class BaseModel(Base):
        __abstract__ = True
        id = Column(Integer, primary_key=True, autoincrement=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PrimitiveTypeEnum(str, enum.Enum):
    """Primitive operation types (mirrors timesense.primitives.PrimitiveType)."""
    # Disk I/O
    DISK_READ_SEQ = "disk_read_seq"
    DISK_READ_RANDOM = "disk_read_random"
    DISK_WRITE_SEQ = "disk_write_seq"
    DISK_WRITE_RANDOM = "disk_write_random"

    # Network I/O
    NET_UPLOAD = "net_upload"
    NET_DOWNLOAD = "net_download"
    NET_LATENCY = "net_latency"
    NET_DNS = "net_dns"

    # CPU compute
    CPU_HASH_SHA256 = "cpu_hash_sha256"
    CPU_JSON_PARSE = "cpu_json_parse"
    CPU_JSON_SERIALIZE = "cpu_json_serialize"
    CPU_GZIP_COMPRESS = "cpu_gzip_compress"
    CPU_GZIP_DECOMPRESS = "cpu_gzip_decompress"
    CPU_REGEX_MATCH = "cpu_regex_match"
    CPU_TEXT_CHUNK = "cpu_text_chunk"

    # LLM inference
    LLM_TOKENS_GENERATE = "llm_tokens_generate"
    LLM_PROMPT_PROCESS = "llm_prompt_process"
    LLM_CONTEXT_LOAD = "llm_context_load"

    # Embedding
    EMBED_TEXT = "embed_text"
    EMBED_BATCH = "embed_batch"

    # Database
    DB_INSERT_SINGLE = "db_insert_single"
    DB_INSERT_BATCH = "db_insert_batch"
    DB_QUERY_SIMPLE = "db_query_simple"
    DB_QUERY_COMPLEX = "db_query_complex"
    DB_QUERY_FULL_SCAN = "db_query_full_scan"

    # Vector DB
    VECTOR_INSERT = "vector_insert"
    VECTOR_SEARCH = "vector_search"
    VECTOR_SEARCH_FILTERED = "vector_search_filtered"

    # Memory
    MEM_ALLOC = "mem_alloc"
    MEM_COPY = "mem_copy"


class ProfileStatusEnum(str, enum.Enum):
    """Status of a time profile."""
    UNCALIBRATED = "uncalibrated"
    CALIBRATING = "calibrating"
    STABLE = "stable"
    UNSTABLE = "unstable"
    STALE = "stale"
    DEGRADED = "degraded"


class TimeProfileModel(BaseModel):
    """
    Persistent storage for time profiles.

    Each profile captures the empirical timing characteristics
    of a primitive operation on a specific machine.
    """
    __tablename__ = "timesense_profiles"

    # Identity
    primitive_type = Column(String(100), nullable=False, index=True)
    machine_id = Column(String(100), nullable=False, default="default", index=True)
    model_name = Column(String(255), nullable=True)  # For LLM/embedding primitives

    # Status
    status = Column(SQLEnum(ProfileStatusEnum), nullable=False, default=ProfileStatusEnum.UNCALIBRATED)

    # Unit of measurement
    unit = Column(String(50), nullable=False, default="bytes")
    time_unit = Column(String(20), nullable=False, default="ms")

    # Linear model coefficients: time = a + b * size
    model_a = Column(Float, nullable=True)  # Overhead (intercept)
    model_b = Column(Float, nullable=True)  # Slope (time per unit)
    model_r_squared = Column(Float, nullable=True)  # Goodness of fit
    model_residual_std = Column(Float, nullable=True)  # Residual standard deviation
    model_n_points = Column(Integer, nullable=True)  # Data points used for fitting

    # Confidence and freshness
    confidence = Column(Float, nullable=False, default=0.0)
    freshness = Column(Float, nullable=False, default=1.0)

    # Calibration history
    last_calibrated = Column(DateTime, nullable=True)
    calibration_count = Column(Integer, nullable=False, default=0)

    # Prediction error tracking
    mean_absolute_error = Column(Float, nullable=True)

    # Context tags (JSON: {"disk_type": "SSD", "gpu": "RTX 3080", ...})
    context_tags = Column(JSON, nullable=True)

    # Size-specific distributions (JSON: {size: {p50, p90, p95, ...}})
    size_distributions = Column(JSON, nullable=True)

    # Unique constraint
    __table_args__ = (
        Index('idx_profile_lookup', 'primitive_type', 'machine_id', 'model_name', unique=True),
        Index('idx_profile_status', 'status'),
        Index('idx_profile_calibration', 'last_calibrated'),
    )

    def __repr__(self):
        return f"<TimeProfile(primitive={self.primitive_type}, machine={self.machine_id}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'primitive_type': self.primitive_type,
            'machine_id': self.machine_id,
            'model_name': self.model_name,
            'status': self.status.value if self.status else None,
            'unit': self.unit,
            'model': {
                'a': self.model_a,
                'b': self.model_b,
                'r_squared': self.model_r_squared,
                'n_points': self.model_n_points
            },
            'confidence': self.confidence,
            'freshness': self.freshness,
            'last_calibrated': self.last_calibrated.isoformat() if self.last_calibrated else None,
            'calibration_count': self.calibration_count,
            'mean_absolute_error': self.mean_absolute_error,
            'context_tags': self.context_tags
        }


class CalibrationMeasurement(BaseModel):
    """
    Individual calibration measurements.

    Stores raw benchmark data for analysis and recalibration.
    """
    __tablename__ = "timesense_measurements"

    # Link to profile
    profile_id = Column(Integer, ForeignKey('timesense_profiles.id'), nullable=True, index=True)

    # Measurement data
    primitive_type = Column(String(100), nullable=False, index=True)
    machine_id = Column(String(100), nullable=False, default="default")
    model_name = Column(String(255), nullable=True)

    # Measurement values
    size = Column(Integer, nullable=False)  # Size in native unit
    duration_ms = Column(Float, nullable=False)  # Duration in milliseconds
    throughput = Column(Float, nullable=True)  # Calculated throughput

    # Context
    cache_state = Column(String(20), nullable=True)  # cold, warm, hot
    iteration = Column(Integer, nullable=True)

    # Metadata
    metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_measurement_primitive', 'primitive_type', 'size'),
        Index('idx_measurement_time', 'created_at'),
    )

    def __repr__(self):
        return f"<Measurement(primitive={self.primitive_type}, size={self.size}, duration={self.duration_ms}ms)>"


class CalibrationRun(BaseModel):
    """
    Record of calibration runs.

    Tracks when calibration was performed and what was measured.
    """
    __tablename__ = "timesense_calibration_runs"

    # Run identity
    run_id = Column(String(36), nullable=False, unique=True, index=True)
    machine_id = Column(String(100), nullable=False, default="default")

    # Timing
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Results
    primitives_calibrated = Column(Integer, nullable=False, default=0)
    measurements_collected = Column(Integer, nullable=False, default=0)
    profiles_updated = Column(Integer, nullable=False, default=0)

    # Status
    status = Column(String(50), nullable=False, default="running")  # running, completed, failed
    errors = Column(JSON, nullable=True)  # List of error messages

    # System info at calibration time
    system_info = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_calibration_run_time', 'started_at'),
        Index('idx_calibration_run_machine', 'machine_id'),
    )

    def __repr__(self):
        return f"<CalibrationRun(id={self.run_id}, status={self.status}, primitives={self.primitives_calibrated})>"


class PredictionLog(BaseModel):
    """
    Log of predictions for accuracy tracking.

    Stores predicted vs actual durations for learning.
    """
    __tablename__ = "timesense_predictions"

    # Task identity
    task_id = Column(String(100), nullable=False, index=True)
    primitive_type = Column(String(100), nullable=True, index=True)

    # Prediction
    size = Column(Float, nullable=True)
    predicted_p50_ms = Column(Float, nullable=False)
    predicted_p95_ms = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)

    # Actual (filled in when task completes)
    actual_ms = Column(Float, nullable=True)
    error_ratio = Column(Float, nullable=True)  # (actual - predicted) / predicted

    # Status
    within_p95 = Column(Boolean, nullable=True)  # Was actual within p95?

    # Context
    model_name = Column(String(255), nullable=True)
    metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_prediction_task', 'task_id'),
        Index('idx_prediction_primitive', 'primitive_type'),
        Index('idx_prediction_error', 'error_ratio'),
    )

    def __repr__(self):
        return f"<Prediction(task={self.task_id}, predicted={self.predicted_p50_ms}ms, actual={self.actual_ms}ms)>"


class SystemBenchmark(BaseModel):
    """
    System-level benchmark snapshots.

    Captures overall system performance at a point in time.
    """
    __tablename__ = "timesense_system_benchmarks"

    machine_id = Column(String(100), nullable=False, index=True)

    # System info
    platform = Column(String(100), nullable=True)
    processor = Column(String(255), nullable=True)
    cpu_count = Column(Integer, nullable=True)
    memory_total_gb = Column(Float, nullable=True)

    # Benchmark results (throughput in MB/s or ops/s)
    disk_read_seq_mbps = Column(Float, nullable=True)
    disk_write_seq_mbps = Column(Float, nullable=True)
    cpu_hash_mbps = Column(Float, nullable=True)
    cpu_json_mbps = Column(Float, nullable=True)
    memory_copy_gbps = Column(Float, nullable=True)

    # LLM/Embedding (if available)
    llm_tokens_per_sec = Column(Float, nullable=True)
    embed_tokens_per_sec = Column(Float, nullable=True)
    llm_model_name = Column(String(255), nullable=True)
    embed_model_name = Column(String(255), nullable=True)

    # Vector DB (if available)
    vector_search_qps = Column(Float, nullable=True)  # Queries per second
    vector_insert_vps = Column(Float, nullable=True)  # Vectors per second

    __table_args__ = (
        Index('idx_benchmark_machine', 'machine_id'),
        Index('idx_benchmark_time', 'created_at'),
    )

    def __repr__(self):
        return f"<SystemBenchmark(machine={self.machine_id}, disk_read={self.disk_read_seq_mbps}MB/s)>"


# ================================================================
# DATABASE SERVICE
# ================================================================

class TimeSenseDBService:
    """
    Database service for TimeSense persistence.

    Provides CRUD operations for time profiles and measurements.
    """

    def __init__(self, session):
        self.session = session

    def get_profile(
        self,
        primitive_type: str,
        machine_id: str = "default",
        model_name: Optional[str] = None
    ) -> Optional[TimeProfileModel]:
        """Get a profile from the database."""
        query = self.session.query(TimeProfileModel).filter(
            TimeProfileModel.primitive_type == primitive_type,
            TimeProfileModel.machine_id == machine_id
        )

        if model_name:
            query = query.filter(TimeProfileModel.model_name == model_name)
        else:
            query = query.filter(TimeProfileModel.model_name.is_(None))

        return query.first()

    def save_profile(self, profile: TimeProfileModel) -> TimeProfileModel:
        """Save or update a profile."""
        existing = self.get_profile(
            profile.primitive_type,
            profile.machine_id,
            profile.model_name
        )

        if existing:
            # Update existing
            existing.status = profile.status
            existing.model_a = profile.model_a
            existing.model_b = profile.model_b
            existing.model_r_squared = profile.model_r_squared
            existing.model_residual_std = profile.model_residual_std
            existing.model_n_points = profile.model_n_points
            existing.confidence = profile.confidence
            existing.freshness = profile.freshness
            existing.last_calibrated = profile.last_calibrated
            existing.calibration_count = profile.calibration_count
            existing.mean_absolute_error = profile.mean_absolute_error
            existing.context_tags = profile.context_tags
            existing.size_distributions = profile.size_distributions
            self.session.commit()
            return existing
        else:
            self.session.add(profile)
            self.session.commit()
            return profile

    def get_all_profiles(self, machine_id: str = "default") -> list:
        """Get all profiles for a machine."""
        return self.session.query(TimeProfileModel).filter(
            TimeProfileModel.machine_id == machine_id
        ).all()

    def save_measurement(self, measurement: CalibrationMeasurement):
        """Save a calibration measurement."""
        self.session.add(measurement)
        self.session.commit()

    def save_measurements_batch(self, measurements: list):
        """Save multiple measurements."""
        self.session.add_all(measurements)
        self.session.commit()

    def save_calibration_run(self, run: CalibrationRun):
        """Save a calibration run record."""
        self.session.add(run)
        self.session.commit()

    def save_prediction(self, prediction: PredictionLog):
        """Save a prediction log entry."""
        self.session.add(prediction)
        self.session.commit()

    def update_prediction_actual(
        self,
        task_id: str,
        actual_ms: float
    ) -> Optional[PredictionLog]:
        """Update a prediction with actual duration."""
        prediction = self.session.query(PredictionLog).filter(
            PredictionLog.task_id == task_id
        ).first()

        if prediction:
            prediction.actual_ms = actual_ms
            if prediction.predicted_p50_ms > 0:
                prediction.error_ratio = (actual_ms - prediction.predicted_p50_ms) / prediction.predicted_p50_ms
            if prediction.predicted_p95_ms:
                prediction.within_p95 = actual_ms <= prediction.predicted_p95_ms
            self.session.commit()

        return prediction

    def get_prediction_accuracy_stats(
        self,
        primitive_type: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get prediction accuracy statistics."""
        from datetime import timedelta
        from sqlalchemy import func

        cutoff = datetime.utcnow() - timedelta(hours=hours)

        query = self.session.query(PredictionLog).filter(
            PredictionLog.created_at >= cutoff,
            PredictionLog.actual_ms.isnot(None)
        )

        if primitive_type:
            query = query.filter(PredictionLog.primitive_type == primitive_type)

        predictions = query.all()

        if not predictions:
            return {'sample_count': 0}

        error_ratios = [p.error_ratio for p in predictions if p.error_ratio is not None]
        within_p95_count = sum(1 for p in predictions if p.within_p95)

        return {
            'sample_count': len(predictions),
            'mean_error_ratio': sum(error_ratios) / len(error_ratios) if error_ratios else 0,
            'mean_absolute_error': sum(abs(e) for e in error_ratios) / len(error_ratios) if error_ratios else 0,
            'within_p95_percent': (within_p95_count / len(predictions)) * 100,
            'hours_analyzed': hours
        }


def create_timesense_tables(engine):
    """Create TimeSense tables in the database."""
    BaseModel.metadata.create_all(engine)
