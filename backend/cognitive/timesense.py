"""
TimeSense Engine - Grace's Understanding of Time, Data Scale, and Capacity

TimeSense gives Grace a true cognitive understanding of:

1. DATA SCALE AWARENESS: What KB, MB, GB, TB actually mean.
   Grace knows that 1MB is a document, 1GB is a book collection,
   1TB is an enterprise dataset. She knows her processing rate at
   each scale and can reason about feasibility.

2. TEMPORAL COMPREHENSION: How long things take at different scales.
   Grace calibrates herself: "Embedding 1MB takes me 200ms,
   so embedding 1GB will take ~200 seconds." She doesn't guess --
   she measures, learns, and predicts from real experience.

3. MEMORY CAPACITY SELF-AWARENESS: Grace knows her own limits.
   Total RAM, vector DB capacity, knowledge base size, disk space.
   She can say "I have 4GB of knowledge and room for 12GB more"
   or "This 50GB dataset won't fit without purging old data."

4. PROCESSING RATE INTELLIGENCE: MB/s throughput per operation type.
   Grace tracks how fast she ingests, embeds, retrieves, and reasons
   at every data scale. She knows her own speed.

5. TIME-TO-COMPLETION ESTIMATION: "This task will take ~45 minutes."
   Grace can estimate how long any task will take based on data size
   and her measured processing rates.

This is Grace understanding her own physical reality -- like a person
knowing they can carry 20kg but not 200kg, and walk 1km in 15 minutes.

Integrates with:
- Self-Mirror: Scale awareness feeds [T,M,P] telemetry
- OODA Loop: Measures each decision phase
- Diagnostic Engine: Scale anomalies trigger diagnostics
- Message Bus: Broadcasts capacity events
- Magma Memory: Stores temporal patterns for learning
"""

import logging
import time
import threading
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum

logger = logging.getLogger(__name__)

def _track_timesense(desc, **kwargs):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("timesense", desc, **kwargs)
    except Exception:
        pass


# =============================================================================
# DATA SCALE AWARENESS - Grace understands what KB, MB, GB, TB mean
# =============================================================================

class DataScale(str, Enum):
    """Data scale units that Grace understands."""
    BYTES = "B"
    KILOBYTES = "KB"
    MEGABYTES = "MB"
    GIGABYTES = "GB"
    TERABYTES = "TB"
    PETABYTES = "PB"


@dataclass
class DataScaleProfile:
    """Grace's understanding of what a data scale means operationally.

    This is Grace's 'intuition' about data sizes -- like a human
    knowing that a page is light but a filing cabinet is heavy.
    """
    scale: DataScale
    min_bytes: float
    max_bytes: float
    human_analogy: str
    processing_character: str
    typical_operations: List[str]

    def contains(self, size_bytes: float) -> bool:
        return self.min_bytes <= size_bytes < self.max_bytes


# Grace's innate understanding of data scales
DATA_SCALE_PROFILES = {
    DataScale.BYTES: DataScaleProfile(
        scale=DataScale.BYTES, min_bytes=0, max_bytes=1024,
        human_analogy="A single sentence or config value",
        processing_character="Instant. No measurable cost.",
        typical_operations=["config_read", "cache_lookup", "key_check"],
    ),
    DataScale.KILOBYTES: DataScaleProfile(
        scale=DataScale.KILOBYTES, min_bytes=1024, max_bytes=1024**2,
        human_analogy="A page of text, a small code file",
        processing_character="Trivial. Sub-millisecond for most operations.",
        typical_operations=["file_read", "embedding_single", "api_response"],
    ),
    DataScale.MEGABYTES: DataScaleProfile(
        scale=DataScale.MEGABYTES, min_bytes=1024**2, max_bytes=1024**3,
        human_analogy="A document, a PDF, a small dataset",
        processing_character="Fast. Seconds for embedding, milliseconds for retrieval.",
        typical_operations=["document_ingest", "pdf_parse", "batch_embed"],
    ),
    DataScale.GIGABYTES: DataScaleProfile(
        scale=DataScale.GIGABYTES, min_bytes=1024**3, max_bytes=1024**4,
        human_analogy="A book collection, a codebase, a knowledge base",
        processing_character="Significant. Minutes to hours for full processing.",
        typical_operations=["repo_index", "knowledge_base_rebuild", "full_reindex"],
    ),
    DataScale.TERABYTES: DataScaleProfile(
        scale=DataScale.TERABYTES, min_bytes=1024**4, max_bytes=1024**5,
        human_analogy="An enterprise dataset, a corporate knowledge library",
        processing_character="Heavy. Hours to days. Requires batching and throttling.",
        typical_operations=["enterprise_ingest", "full_retrain", "archive_process"],
    ),
    DataScale.PETABYTES: DataScaleProfile(
        scale=DataScale.PETABYTES, min_bytes=1024**5, max_bytes=float("inf"),
        human_analogy="A data lake, an entire organization's history",
        processing_character="Extreme. Days to weeks. Must stream, never load fully.",
        typical_operations=["data_lake_index", "distributed_process"],
    ),
}


def classify_data_scale(size_bytes: float) -> DataScaleProfile:
    """Grace classifies a data size into her scale understanding."""
    for profile in DATA_SCALE_PROFILES.values():
        if profile.contains(size_bytes):
            return profile
    return DATA_SCALE_PROFILES[DataScale.PETABYTES]


def format_data_size(size_bytes: float) -> str:
    """Format bytes into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes:.0f} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/1024**2:.1f} MB"
    elif size_bytes < 1024**4:
        return f"{size_bytes/1024**3:.2f} GB"
    elif size_bytes < 1024**5:
        return f"{size_bytes/1024**4:.3f} TB"
    else:
        return f"{size_bytes/1024**5:.4f} PB"


# =============================================================================
# MEMORY CAPACITY SELF-AWARENESS
# =============================================================================

@dataclass
class CapacitySnapshot:
    """Grace's awareness of her own memory and storage capacity."""
    total_ram_bytes: float = 0
    available_ram_bytes: float = 0
    ram_usage_percent: float = 0.0
    total_disk_bytes: float = 0
    available_disk_bytes: float = 0
    disk_usage_percent: float = 0.0
    knowledge_base_bytes: float = 0
    vector_db_entries: int = 0
    estimated_vector_db_bytes: float = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_knowledge_formatted(self) -> str:
        return format_data_size(self.knowledge_base_bytes)

    @property
    def remaining_capacity_formatted(self) -> str:
        return format_data_size(self.available_disk_bytes)

    @property
    def ram_formatted(self) -> str:
        return f"{format_data_size(self.available_ram_bytes)} free / {format_data_size(self.total_ram_bytes)} total"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ram": {
                "total": format_data_size(self.total_ram_bytes),
                "available": format_data_size(self.available_ram_bytes),
                "usage_percent": round(self.ram_usage_percent, 1),
            },
            "disk": {
                "total": format_data_size(self.total_disk_bytes),
                "available": format_data_size(self.available_disk_bytes),
                "usage_percent": round(self.disk_usage_percent, 1),
            },
            "knowledge": {
                "size": format_data_size(self.knowledge_base_bytes),
                "vector_entries": self.vector_db_entries,
                "vector_db_size": format_data_size(self.estimated_vector_db_bytes),
            },
            "self_assessment": self._self_assessment(),
        }

    def _self_assessment(self) -> str:
        """Grace's self-assessment of her capacity."""
        if self.ram_usage_percent > 90:
            return "Critical: RAM nearly full. Must reduce active data or expand memory."
        elif self.ram_usage_percent > 75:
            return "Elevated: RAM usage high. Large operations may cause pressure."
        elif self.disk_usage_percent > 90:
            return "Critical: Disk nearly full. Cannot ingest more data without cleanup."
        elif self.disk_usage_percent > 75:
            return "Elevated: Disk filling up. Plan for archival or expansion."
        else:
            return "Healthy: Sufficient capacity for normal operations."


def measure_capacity(knowledge_base_path: str = None) -> CapacitySnapshot:
    """Measure Grace's current capacity."""
    import psutil
    import os

    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    kb_size = 0
    if knowledge_base_path and os.path.isdir(knowledge_base_path):
        for root, dirs, files in os.walk(knowledge_base_path):
            for f in files:
                try:
                    kb_size += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass

    return CapacitySnapshot(
        total_ram_bytes=float(mem.total),
        available_ram_bytes=float(mem.available),
        ram_usage_percent=mem.percent,
        total_disk_bytes=float(disk.total),
        available_disk_bytes=float(disk.free),
        disk_usage_percent=disk.percent,
        knowledge_base_bytes=float(kb_size),
    )


# =============================================================================
# PROCESSING RATE TRACKER
# =============================================================================

@dataclass
class ProcessingRate:
    """Grace's measured processing rate for an operation at a given scale."""
    operation: str
    bytes_per_second: float
    data_scale: DataScale
    sample_count: int

    @property
    def mb_per_second(self) -> float:
        return self.bytes_per_second / (1024 * 1024)

    @property
    def formatted_rate(self) -> str:
        if self.bytes_per_second > 1024**3:
            return f"{self.bytes_per_second/1024**3:.1f} GB/s"
        elif self.bytes_per_second > 1024**2:
            return f"{self.bytes_per_second/1024**2:.1f} MB/s"
        elif self.bytes_per_second > 1024:
            return f"{self.bytes_per_second/1024:.1f} KB/s"
        return f"{self.bytes_per_second:.0f} B/s"

    def estimate_time(self, data_bytes: float) -> float:
        """Estimate processing time for a given data size in seconds."""
        if self.bytes_per_second <= 0:
            return float("inf")
        return data_bytes / self.bytes_per_second

    def estimate_time_formatted(self, data_bytes: float) -> str:
        """Human-readable time estimate."""
        seconds = self.estimate_time(data_bytes)
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f} minutes"
        elif seconds < 86400:
            return f"{seconds/3600:.1f} hours"
        else:
            return f"{seconds/86400:.1f} days"


class ProcessingRateTracker:
    """Tracks Grace's processing speed at different data scales."""

    def __init__(self):
        self._rates: Dict[str, List[Tuple[float, float]]] = defaultdict(list)

    def record(self, operation: str, data_bytes: float, duration_seconds: float):
        """Record a processing observation."""
        if duration_seconds > 0 and data_bytes > 0:
            self._rates[operation].append((data_bytes, duration_seconds))
            if len(self._rates[operation]) > 500:
                self._rates[operation] = self._rates[operation][-500:]

    def get_rate(self, operation: str) -> Optional[ProcessingRate]:
        """Get Grace's measured processing rate for an operation."""
        observations = self._rates.get(operation, [])
        if not observations:
            return None

        total_bytes = sum(b for b, _ in observations)
        total_seconds = sum(s for _, s in observations)
        if total_seconds <= 0:
            return None

        bps = total_bytes / total_seconds
        scale = classify_data_scale(total_bytes / len(observations))

        return ProcessingRate(
            operation=operation,
            bytes_per_second=bps,
            data_scale=scale.scale,
            sample_count=len(observations),
        )

    def estimate_time(self, operation: str, data_bytes: float) -> Optional[str]:
        """Estimate how long an operation will take for a given data size."""
        rate = self.get_rate(operation)
        if not rate:
            return None
        return rate.estimate_time_formatted(data_bytes)

    def get_all_rates(self) -> Dict[str, Dict[str, Any]]:
        """Get all measured processing rates."""
        result = {}
        for op in self._rates:
            rate = self.get_rate(op)
            if rate:
                result[op] = {
                    "rate": rate.formatted_rate,
                    "bytes_per_second": round(rate.bytes_per_second, 0),
                    "scale": rate.data_scale.value,
                    "samples": rate.sample_count,
                    "estimates": {
                        "1MB": rate.estimate_time_formatted(1024**2),
                        "100MB": rate.estimate_time_formatted(100 * 1024**2),
                        "1GB": rate.estimate_time_formatted(1024**3),
                        "10GB": rate.estimate_time_formatted(10 * 1024**3),
                    },
                }
        return result


# =============================================================================
# CORE DATA STRUCTURES
# =============================================================================

class TimeOfDay(str, Enum):
    MORNING = "morning"      # 06:00 - 12:00
    AFTERNOON = "afternoon"  # 12:00 - 18:00
    EVENING = "evening"      # 18:00 - 22:00
    NIGHT = "night"          # 22:00 - 06:00


class WorkPattern(str, Enum):
    FOCUSED = "focused"        # Consistent, fast operations
    VARIABLE = "variable"      # Mixed speeds
    DEGRADED = "degraded"      # Slowing down
    IDLE = "idle"              # No recent activity


@dataclass
class TemporalContext:
    """Grace's awareness of time."""
    current_time: datetime = field(default_factory=datetime.utcnow)
    session_start: datetime = field(default_factory=datetime.utcnow)
    session_duration_seconds: float = 0.0
    time_since_last_action_seconds: float = 0.0
    time_of_day: TimeOfDay = TimeOfDay.MORNING
    work_pattern: WorkPattern = WorkPattern.FOCUSED
    recent_activity_rate: float = 0.0  # operations per minute
    ooda_cycles_completed: int = 0
    avg_ooda_cycle_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_time": self.current_time.isoformat(),
            "session_duration_s": round(self.session_duration_seconds, 1),
            "time_since_last_action_s": round(self.time_since_last_action_seconds, 1),
            "time_of_day": self.time_of_day.value,
            "work_pattern": self.work_pattern.value,
            "activity_rate_per_min": round(self.recent_activity_rate, 2),
            "ooda_cycles": self.ooda_cycles_completed,
            "avg_ooda_ms": round(self.avg_ooda_cycle_ms, 1),
        }


@dataclass
class TimingRecord:
    """A single operation timing record."""
    operation: str
    component: str
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimePrediction:
    """Prediction for how long an operation will take."""
    operation: str
    predicted_ms: float
    confidence: float  # 0.0-1.0
    lower_bound_ms: float
    upper_bound_ms: float
    based_on_samples: int
    historical_mean_ms: float
    historical_std_ms: float


@dataclass
class CostEstimate:
    """Time and compute cost estimate for an operation."""
    operation: str
    estimated_time_ms: float
    estimated_cpu_cost: float  # 0.0-1.0 (fraction of CPU)
    estimated_memory_bytes: float
    confidence: float
    is_expensive: bool  # True if exceeds thresholds


@dataclass
class TemporalAnomaly:
    """A temporal anomaly (operation outside expected range)."""
    operation: str
    component: str
    expected_ms: float
    actual_ms: float
    deviation_factor: float  # actual / expected
    severity: str  # minor, moderate, severe
    timestamp: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# OPERATION TIMING TRACKER
# =============================================================================

class OperationTimer:
    """Tracks timing for a specific operation type."""

    def __init__(self, operation: str, window_size: int = 200):
        self.operation = operation
        self._durations: deque = deque(maxlen=window_size)
        self._timestamps: deque = deque(maxlen=window_size)
        self._success_count = 0
        self._failure_count = 0
        self.total_invocations = 0

    def record(self, duration_ms: float, success: bool = True):
        self._durations.append(duration_ms)
        self._timestamps.append(datetime.utcnow())
        self.total_invocations += 1
        if success:
            self._success_count += 1
        else:
            self._failure_count += 1

    @property
    def mean(self) -> float:
        return sum(self._durations) / len(self._durations) if self._durations else 0.0

    @property
    def std(self) -> float:
        if len(self._durations) < 2:
            return 0.0
        m = self.mean
        variance = sum((d - m) ** 2 for d in self._durations) / (len(self._durations) - 1)
        return math.sqrt(variance)

    @property
    def median(self) -> float:
        if not self._durations:
            return 0.0
        sorted_d = sorted(self._durations)
        n = len(sorted_d)
        if n % 2 == 0:
            return (sorted_d[n // 2 - 1] + sorted_d[n // 2]) / 2
        return sorted_d[n // 2]

    @property
    def p95(self) -> float:
        if not self._durations:
            return 0.0
        sorted_d = sorted(self._durations)
        idx = int(len(sorted_d) * 0.95)
        return sorted_d[min(idx, len(sorted_d) - 1)]

    @property
    def success_rate(self) -> float:
        total = self._success_count + self._failure_count
        return self._success_count / total if total > 0 else 1.0

    @property
    def last_duration(self) -> Optional[float]:
        return self._durations[-1] if self._durations else None

    def predict(self) -> TimePrediction:
        """Predict the next operation duration."""
        if len(self._durations) < 3:
            return TimePrediction(
                operation=self.operation,
                predicted_ms=self.mean or 100.0,
                confidence=0.1,
                lower_bound_ms=0,
                upper_bound_ms=1000,
                based_on_samples=len(self._durations),
                historical_mean_ms=self.mean,
                historical_std_ms=self.std,
            )

        mean = self.mean
        std = self.std
        samples = len(self._durations)
        confidence = min(samples / 100, 0.95)

        return TimePrediction(
            operation=self.operation,
            predicted_ms=mean,
            confidence=confidence,
            lower_bound_ms=max(0, mean - 2 * std),
            upper_bound_ms=mean + 2 * std,
            based_on_samples=samples,
            historical_mean_ms=mean,
            historical_std_ms=std,
        )

    def is_anomalous(self, duration_ms: float) -> Optional[TemporalAnomaly]:
        """Check if a duration is anomalous."""
        if len(self._durations) < 10:
            return None

        mean = self.mean
        std = self.std
        if std == 0:
            return None

        deviation = abs(duration_ms - mean) / std

        if deviation < 2.0:
            return None

        severity = "minor" if deviation < 3.0 else "moderate" if deviation < 5.0 else "severe"

        return TemporalAnomaly(
            operation=self.operation,
            component="",
            expected_ms=mean,
            actual_ms=duration_ms,
            deviation_factor=duration_ms / mean if mean > 0 else 0,
            severity=severity,
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "total_invocations": self.total_invocations,
            "mean_ms": round(self.mean, 2),
            "median_ms": round(self.median, 2),
            "std_ms": round(self.std, 2),
            "p95_ms": round(self.p95, 2),
            "success_rate": round(self.success_rate, 3),
            "last_ms": round(self.last_duration, 2) if self.last_duration else None,
            "samples": len(self._durations),
        }


# =============================================================================
# OODA CYCLE TIMER
# =============================================================================

class OODACycleTimer:
    """Times individual OODA cycle phases and complete cycles."""

    def __init__(self):
        self._phase_timers: Dict[str, OperationTimer] = {
            "observe": OperationTimer("ooda.observe"),
            "orient": OperationTimer("ooda.orient"),
            "decide": OperationTimer("ooda.decide"),
            "act": OperationTimer("ooda.act"),
        }
        self._cycle_timer = OperationTimer("ooda.full_cycle")
        self._current_cycle_start: Optional[float] = None
        self._current_phase_start: Optional[float] = None
        self._current_phase: Optional[str] = None

    def start_cycle(self):
        self._current_cycle_start = time.perf_counter()

    def start_phase(self, phase: str):
        self._current_phase = phase
        self._current_phase_start = time.perf_counter()

    def end_phase(self, phase: str):
        if self._current_phase_start and self._current_phase == phase:
            elapsed = (time.perf_counter() - self._current_phase_start) * 1000
            if phase in self._phase_timers:
                self._phase_timers[phase].record(elapsed)
            self._current_phase_start = None
            self._current_phase = None
            return elapsed
        return 0.0

    def end_cycle(self) -> float:
        if self._current_cycle_start:
            elapsed = (time.perf_counter() - self._current_cycle_start) * 1000
            self._cycle_timer.record(elapsed)
            self._current_cycle_start = None
            return elapsed
        return 0.0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "full_cycle": self._cycle_timer.get_stats(),
            "phases": {
                phase: timer.get_stats()
                for phase, timer in self._phase_timers.items()
            },
        }


# =============================================================================
# TIMESENSE ENGINE
# =============================================================================

class TimeSenseEngine:
    """
    Grace's temporal and scale reasoning engine.

    Grace's understanding of her own physical reality:
    - What KB, MB, GB, TB mean in processing time
    - How fast she processes at each scale (MB/s)
    - Her own memory capacity and limits
    - How long any task will take based on data size
    - When she's operating outside normal parameters
    """

    def __init__(self, message_bus=None, self_mirror=None, knowledge_base_path=None):
        self.message_bus = message_bus
        self.self_mirror = self_mirror
        self.knowledge_base_path = knowledge_base_path

        self._operation_timers: Dict[str, OperationTimer] = {}
        self._ooda_timer = OODACycleTimer()
        self._rate_tracker = ProcessingRateTracker()
        self._capacity: Optional[CapacitySnapshot] = None
        self._capacity_last_check: Optional[datetime] = None

        # Enhanced capabilities
        from cognitive.timesense_enhanced import (
            TaskPlanner, ThroughputTracker,
            MemoryPressurePredictor, PerformanceTrendTracker,
        )
        self.task_planner = TaskPlanner(timesense=self)
        self.throughput = ThroughputTracker()
        self.memory_predictor = MemoryPressurePredictor()
        self.trends = PerformanceTrendTracker()

        # Deep capabilities
        from cognitive.timesense_deep import (
            LearningCurveTracker, TimeSensePersistence,
            PredictiveScaler, TimeAwareScheduler,
            OperationDependencyGraph,
        )
        self.learning_curves = LearningCurveTracker()
        self.persistence = TimeSensePersistence()
        self.scaler = PredictiveScaler()
        self.scheduler = TimeAwareScheduler()
        self.dep_graph = OperationDependencyGraph()

        self._session_start = datetime.utcnow()
        self._last_action_time = datetime.utcnow()
        self._action_timestamps: deque = deque(maxlen=1000)

        self._anomalies: deque = deque(maxlen=500)

        self._stats = {
            "total_operations_timed": 0,
            "total_anomalies_detected": 0,
            "total_predictions_made": 0,
            "total_ooda_cycles": 0,
            "total_data_processed_bytes": 0,
        }

        self._refresh_capacity()

        logger.info("[TIMESENSE] Engine initialized - Grace understands time and scale")

    # =========================================================================
    # OPERATION TIMING
    # =========================================================================

    def record_operation(
        self,
        operation: str,
        duration_ms: float,
        component: str = "",
        success: bool = True,
        data_bytes: float = 0,
        metadata: Dict[str, Any] = None,
    ):
        """Record an operation's execution time and data size.

        Args:
            operation: Operation name (e.g. "ingestion.embed", "retrieval.search")
            duration_ms: How long it took in milliseconds
            component: Which component performed it
            success: Whether it succeeded
            data_bytes: How many bytes were processed (for rate calculation)
            metadata: Additional metadata
        """
        if operation not in self._operation_timers:
            self._operation_timers[operation] = OperationTimer(operation)

        timer = self._operation_timers[operation]
        timer.record(duration_ms, success)

        self._last_action_time = datetime.utcnow()
        self._action_timestamps.append(datetime.utcnow())
        self._stats["total_operations_timed"] += 1

        if data_bytes > 0:
            self._stats["total_data_processed_bytes"] += data_bytes
            duration_seconds = duration_ms / 1000.0
            if duration_seconds > 0:
                self._rate_tracker.record(operation, data_bytes, duration_seconds)

        anomaly = timer.is_anomalous(duration_ms)
        if anomaly:
            anomaly.component = component
            self._anomalies.append(anomaly)
            self._stats["total_anomalies_detected"] += 1
            logger.warning(
                f"[TIMESENSE] ANOMALY: {operation} took {duration_ms:.0f}ms "
                f"(expected {anomaly.expected_ms:.0f}ms, {anomaly.severity})"
            )

        # Feed enhanced trackers
        self.trends.record(operation, duration_ms, success)
        self.learning_curves.record(operation, duration_ms)
        self.scheduler.record_load(datetime.utcnow().hour, min(duration_ms / 1000.0, 1.0))

        if self.self_mirror:
            try:
                from cognitive.self_mirror import TelemetryVector
                vector = TelemetryVector(
                    T=duration_ms,
                    M=float(data_bytes) if data_bytes else (float(metadata.get("data_size", 0)) if metadata else 0.0),
                    P=min(duration_ms / 1000.0, 1.0),
                    component=component or operation.split(".")[0],
                    task_domain=operation,
                )
                self.self_mirror.receive_vector(vector)
            except Exception:
                pass

    def time_operation(self, operation: str, component: str = ""):
        """Context manager to time an operation.

        Usage:
            with timesense.time_operation("db.query", "database"):
                result = db.execute(query)
        """
        return _TimeSenseContext(self, operation, component)

    # =========================================================================
    # OODA CYCLE TIMING
    # =========================================================================

    def start_ooda_cycle(self):
        self._ooda_timer.start_cycle()

    def start_ooda_phase(self, phase: str):
        self._ooda_timer.start_phase(phase)

    def end_ooda_phase(self, phase: str) -> float:
        return self._ooda_timer.end_phase(phase)

    def end_ooda_cycle(self) -> float:
        elapsed = self._ooda_timer.end_cycle()
        self._stats["total_ooda_cycles"] += 1
        return elapsed

    # =========================================================================
    # TEMPORAL CONTEXT
    # =========================================================================

    def get_temporal_context(self) -> TemporalContext:
        """Get Grace's current temporal awareness."""
        now = datetime.utcnow()
        session_duration = (now - self._session_start).total_seconds()
        time_since_last = (now - self._last_action_time).total_seconds()

        hour = now.hour
        if 6 <= hour < 12:
            tod = TimeOfDay.MORNING
        elif 12 <= hour < 18:
            tod = TimeOfDay.AFTERNOON
        elif 18 <= hour < 22:
            tod = TimeOfDay.EVENING
        else:
            tod = TimeOfDay.NIGHT

        one_min_ago = now - timedelta(minutes=1)
        recent_ops = sum(1 for t in self._action_timestamps if t > one_min_ago)
        activity_rate = float(recent_ops)

        if time_since_last > 300:
            pattern = WorkPattern.IDLE
        elif activity_rate > 10:
            std_sum = sum(
                t.std for t in self._operation_timers.values()
                if t.total_invocations > 5
            )
            if std_sum < 50:
                pattern = WorkPattern.FOCUSED
            else:
                pattern = WorkPattern.VARIABLE
        else:
            pattern = WorkPattern.VARIABLE

        ooda_stats = self._ooda_timer._cycle_timer
        avg_ooda = ooda_stats.mean if ooda_stats.total_invocations > 0 else 0.0

        return TemporalContext(
            current_time=now,
            session_start=self._session_start,
            session_duration_seconds=session_duration,
            time_since_last_action_seconds=time_since_last,
            time_of_day=tod,
            work_pattern=pattern,
            recent_activity_rate=activity_rate,
            ooda_cycles_completed=self._stats["total_ooda_cycles"],
            avg_ooda_cycle_ms=avg_ooda,
        )

    # =========================================================================
    # PREDICTIONS
    # =========================================================================

    def predict(self, operation: str) -> TimePrediction:
        """Predict how long an operation will take."""
        self._stats["total_predictions_made"] += 1

        if operation in self._operation_timers:
            return self._operation_timers[operation].predict()

        return TimePrediction(
            operation=operation,
            predicted_ms=100.0,
            confidence=0.0,
            lower_bound_ms=0,
            upper_bound_ms=10000,
            based_on_samples=0,
            historical_mean_ms=0,
            historical_std_ms=0,
        )

    def estimate_cost(self, operation: str) -> CostEstimate:
        """Estimate the time and compute cost of an operation."""
        prediction = self.predict(operation)

        cpu_cost = min(prediction.predicted_ms / 5000.0, 1.0)
        memory_est = prediction.predicted_ms * 1024

        return CostEstimate(
            operation=operation,
            estimated_time_ms=prediction.predicted_ms,
            estimated_cpu_cost=cpu_cost,
            estimated_memory_bytes=memory_est,
            confidence=prediction.confidence,
            is_expensive=prediction.predicted_ms > 1000 or cpu_cost > 0.5,
        )

    # =========================================================================
    # ANOMALIES
    # =========================================================================

    def get_anomalies(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent temporal anomalies."""
        return [
            {
                "operation": a.operation,
                "component": a.component,
                "expected_ms": round(a.expected_ms, 1),
                "actual_ms": round(a.actual_ms, 1),
                "deviation_factor": round(a.deviation_factor, 1),
                "severity": a.severity,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in list(self._anomalies)[-limit:]
        ]

    # =========================================================================
    # DATA SCALE AWARENESS
    # =========================================================================

    def understand_data_size(self, size_bytes: float) -> Dict[str, Any]:
        """Grace's cognitive understanding of a data size.

        Returns what the size means, how long it'll take to process,
        and whether it's feasible given current capacity.
        """
        profile = classify_data_scale(size_bytes)
        capacity = self.get_capacity()

        fits_in_ram = size_bytes < capacity.available_ram_bytes if capacity else True
        fits_on_disk = size_bytes < capacity.available_disk_bytes if capacity else True

        time_estimates = {}
        for op, rate in self._rate_tracker.get_all_rates().items():
            rate_obj = self._rate_tracker.get_rate(op)
            if rate_obj:
                time_estimates[op] = rate_obj.estimate_time_formatted(size_bytes)

        return {
            "size": format_data_size(size_bytes),
            "size_bytes": size_bytes,
            "scale": profile.scale.value,
            "analogy": profile.human_analogy,
            "processing_character": profile.processing_character,
            "typical_operations": profile.typical_operations,
            "fits_in_ram": fits_in_ram,
            "fits_on_disk": fits_on_disk,
            "estimated_processing_time": time_estimates or "No rate data yet. Process some data first.",
            "feasibility": "feasible" if fits_in_ram and fits_on_disk else "requires_streaming" if fits_on_disk else "exceeds_capacity",
        }

    def estimate_task_time(self, operation: str, data_bytes: float) -> Dict[str, Any]:
        """Estimate how long a task will take for a given data size.

        Grace uses her measured processing rates to predict duration.
        """
        rate = self._rate_tracker.get_rate(operation)
        scale = classify_data_scale(data_bytes)

        if rate:
            estimated_seconds = rate.estimate_time(data_bytes)
            return {
                "operation": operation,
                "data_size": format_data_size(data_bytes),
                "data_scale": scale.scale.value,
                "measured_rate": rate.formatted_rate,
                "estimated_time": rate.estimate_time_formatted(data_bytes),
                "estimated_seconds": round(estimated_seconds, 2),
                "confidence": "high" if rate.sample_count > 20 else "medium" if rate.sample_count > 5 else "low",
                "samples_used": rate.sample_count,
            }
        else:
            return {
                "operation": operation,
                "data_size": format_data_size(data_bytes),
                "data_scale": scale.scale.value,
                "measured_rate": None,
                "estimated_time": "Unknown - no measurements for this operation yet",
                "confidence": "none",
                "hint": f"Process some {operation} tasks first so I can learn my speed.",
            }

    def get_processing_rates(self) -> Dict[str, Any]:
        """Get Grace's measured processing rates for all operations."""
        return {
            "rates": self._rate_tracker.get_all_rates(),
            "total_data_processed": format_data_size(self._stats["total_data_processed_bytes"]),
        }

    # =========================================================================
    # MEMORY CAPACITY SELF-AWARENESS
    # =========================================================================

    def get_capacity(self) -> CapacitySnapshot:
        """Get Grace's current capacity awareness.

        Refreshes every 60 seconds to avoid excessive IO.
        """
        now = datetime.utcnow()
        if (
            self._capacity is None
            or self._capacity_last_check is None
            or (now - self._capacity_last_check).total_seconds() > 60
        ):
            self._refresh_capacity()
        return self._capacity

    def _refresh_capacity(self):
        """Refresh capacity measurements."""
        try:
            self._capacity = measure_capacity(self.knowledge_base_path)
            self._capacity_last_check = datetime.utcnow()
        except Exception as e:
            logger.warning(f"[TIMESENSE] Capacity measurement failed: {e}")
            if self._capacity is None:
                self._capacity = CapacitySnapshot()

    def can_handle(self, data_bytes: float) -> Dict[str, Any]:
        """Can Grace handle this amount of data right now?

        Grace's honest self-assessment of whether she has the capacity.
        """
        capacity = self.get_capacity()
        scale = classify_data_scale(data_bytes)

        fits_ram = data_bytes < capacity.available_ram_bytes * 0.8
        fits_disk = data_bytes < capacity.available_disk_bytes * 0.9

        if fits_ram and fits_disk:
            verdict = "yes"
            reason = f"I have {format_data_size(capacity.available_ram_bytes)} RAM and {format_data_size(capacity.available_disk_bytes)} disk available."
        elif fits_disk and not fits_ram:
            verdict = "partially"
            reason = f"Data ({format_data_size(data_bytes)}) exceeds available RAM ({format_data_size(capacity.available_ram_bytes)}). I'll need to stream/batch it."
        else:
            verdict = "no"
            reason = f"Data ({format_data_size(data_bytes)}) exceeds my storage ({format_data_size(capacity.available_disk_bytes)}). Need cleanup or expansion."

        return {
            "can_handle": verdict,
            "data_size": format_data_size(data_bytes),
            "scale": scale.scale.value,
            "reason": reason,
            "capacity": capacity.to_dict(),
        }

    # =========================================================================
    # DASHBOARD
    # =========================================================================

    def get_dashboard(self) -> Dict[str, Any]:
        """Get the full TimeSense dashboard - Grace's temporal self-awareness."""
        context = self.get_temporal_context()
        capacity = self.get_capacity()

        return {
            "temporal_context": context.to_dict(),
            "capacity": capacity.to_dict(),
            "processing_rates": self._rate_tracker.get_all_rates(),
            "operations": {
                name: timer.get_stats()
                for name, timer in sorted(
                    self._operation_timers.items(),
                    key=lambda x: -x[1].total_invocations,
                )
            },
            "ooda_timing": self._ooda_timer.get_stats(),
            "anomalies": self.get_anomalies(20),
            "stats": {
                **self._stats,
                "total_data_processed": format_data_size(self._stats["total_data_processed_bytes"]),
            },
            "scale_understanding": {
                scale.value: {
                    "analogy": profile.human_analogy,
                    "character": profile.processing_character,
                }
                for scale, profile in DATA_SCALE_PROFILES.items()
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "total_data_processed": format_data_size(self._stats["total_data_processed_bytes"]),
            "tracked_operations": len(self._operation_timers),
            "tracked_rates": len(self._rate_tracker._rates),
            "session_duration_s": (datetime.utcnow() - self._session_start).total_seconds(),
        }

    def save_state(self) -> bool:
        """Save all TimeSense state to disk. Grace remembers herself."""
        return self.persistence.save(self)

    def load_state(self) -> bool:
        """Load TimeSense state from disk. Grace wakes up knowing herself."""
        return self.persistence.load(self)


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class _TimeSenseContext:
    def __init__(self, engine: TimeSenseEngine, operation: str, component: str):
        self.engine = engine
        self.operation = operation
        self.component = component
        self._start = None

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        self.engine.record_operation(
            operation=self.operation,
            duration_ms=elapsed_ms,
            component=self.component,
            success=exc_type is None,
        )
        return False


# =============================================================================
# SINGLETON
# =============================================================================

_timesense: Optional[TimeSenseEngine] = None


def get_timesense(message_bus=None, self_mirror=None) -> TimeSenseEngine:
    global _timesense
    if _timesense is None:
        _timesense = TimeSenseEngine(message_bus=message_bus, self_mirror=self_mirror)
    return _timesense


def reset_timesense():
    global _timesense
    _timesense = None
