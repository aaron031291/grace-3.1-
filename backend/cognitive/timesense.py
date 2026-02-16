"""
TimeSense Engine - Temporal Reasoning and OODA Timing

Grace's temporal awareness system that:
1. Tracks execution timing for every operation (OODA cycle times)
2. Builds temporal context (time-of-day patterns, session duration)
3. Predicts operation durations based on historical data
4. Detects temporal anomalies (operations taking longer than expected)
5. Provides cost estimation (time + compute cost per operation)
6. Feeds timing data into the Self-Mirror as [T,M,P] vectors

Integrates with:
- Self-Mirror: All timing data feeds [T,M,P] telemetry
- OODA Loop: Measures each phase (observe/orient/decide/act)
- Diagnostic Engine: Temporal anomalies trigger diagnostics
- Message Bus: Broadcasts timing events
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
    Grace's temporal reasoning engine.

    Tracks all operation timings, builds temporal context,
    predicts durations, detects anomalies, and estimates costs.
    """

    def __init__(self, message_bus=None, self_mirror=None):
        self.message_bus = message_bus
        self.self_mirror = self_mirror

        self._operation_timers: Dict[str, OperationTimer] = {}
        self._ooda_timer = OODACycleTimer()

        self._session_start = datetime.utcnow()
        self._last_action_time = datetime.utcnow()
        self._action_timestamps: deque = deque(maxlen=1000)

        self._anomalies: deque = deque(maxlen=500)

        self._stats = {
            "total_operations_timed": 0,
            "total_anomalies_detected": 0,
            "total_predictions_made": 0,
            "total_ooda_cycles": 0,
        }

        logger.info("[TIMESENSE] Engine initialized")

    # =========================================================================
    # OPERATION TIMING
    # =========================================================================

    def record_operation(
        self,
        operation: str,
        duration_ms: float,
        component: str = "",
        success: bool = True,
        metadata: Dict[str, Any] = None,
    ):
        """Record an operation's execution time."""
        if operation not in self._operation_timers:
            self._operation_timers[operation] = OperationTimer(operation)

        timer = self._operation_timers[operation]
        timer.record(duration_ms, success)

        self._last_action_time = datetime.utcnow()
        self._action_timestamps.append(datetime.utcnow())
        self._stats["total_operations_timed"] += 1

        anomaly = timer.is_anomalous(duration_ms)
        if anomaly:
            anomaly.component = component
            self._anomalies.append(anomaly)
            self._stats["total_anomalies_detected"] += 1
            logger.warning(
                f"[TIMESENSE] ANOMALY: {operation} took {duration_ms:.0f}ms "
                f"(expected {anomaly.expected_ms:.0f}ms, {anomaly.severity})"
            )

        if self.self_mirror:
            try:
                from cognitive.self_mirror import TelemetryVector
                vector = TelemetryVector(
                    T=duration_ms,
                    M=float(metadata.get("data_size", 0)) if metadata else 0.0,
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
    # DASHBOARD
    # =========================================================================

    def get_dashboard(self) -> Dict[str, Any]:
        """Get the TimeSense dashboard."""
        context = self.get_temporal_context()

        return {
            "temporal_context": context.to_dict(),
            "operations": {
                name: timer.get_stats()
                for name, timer in sorted(
                    self._operation_timers.items(),
                    key=lambda x: -x[1].total_invocations,
                )
            },
            "ooda_timing": self._ooda_timer.get_stats(),
            "anomalies": self.get_anomalies(20),
            "stats": self._stats,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "tracked_operations": len(self._operation_timers),
            "session_duration_s": (datetime.utcnow() - self._session_start).total_seconds(),
        }


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
