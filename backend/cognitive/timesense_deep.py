"""
TimeSense Deep Capabilities - The Final Layer

Takes Grace's temporal intelligence to its absolute limit:

1. LEARNING CURVES: Grace gets faster at repeated tasks, like muscle memory.
   She tracks her improvement rate per operation and knows when she's plateaued.

2. PERSISTENCE: All timing data, rates, profiles, and trends survive restarts.
   Grace doesn't forget her own speed. She wakes up knowing herself.

3. PREDICTIVE SCALING: Grace forecasts when she'll exhaust capacity based on
   growth trends. "At current ingestion rate, disk full in 12 days."

4. TIME-AWARE SCHEDULING: Grace schedules heavy tasks during low-traffic windows.
   "Repo reindex is heavy. Best window: 2am-5am when query load is lowest."

5. OPERATION DEPENDENCY GRAPHS: Grace understands task ordering.
   "Can't embed until chunking is done. Can't store until embedding is done."
   She parallelizes what she can and sequences what she must.
"""

import logging
import json
import os
import math
import time
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# 1. LEARNING CURVES - Grace develops muscle memory
# =============================================================================

@dataclass
class LearningCurvePoint:
    """A point on Grace's learning curve for an operation."""
    invocation_number: int
    duration_ms: float
    timestamp: datetime


class LearningCurveTracker:
    """
    Tracks Grace's learning curves per operation.

    Like a human getting faster at a task with practice, Grace
    measures her improvement rate and knows when she's plateaued.

    Grace can say: "I've improved 35% at embedding since I started.
    My improvement rate is slowing -- I'm approaching my physical limit."
    """

    def __init__(self):
        self._curves: Dict[str, List[LearningCurvePoint]] = defaultdict(list)
        self._window_size = 50

    def record(self, operation: str, duration_ms: float):
        """Record a data point on the learning curve."""
        points = self._curves[operation]
        point = LearningCurvePoint(
            invocation_number=len(points) + 1,
            duration_ms=duration_ms,
            timestamp=datetime.now(),
        )
        points.append(point)
        if len(points) > 5000:
            self._curves[operation] = points[-5000:]

    def get_curve(self, operation: str) -> Dict[str, Any]:
        """Get the learning curve analysis for an operation."""
        points = self._curves.get(operation, [])
        if len(points) < 10:
            return {
                "operation": operation,
                "status": "insufficient_data",
                "data_points": len(points),
                "message": "Need at least 10 executions to analyze learning curve.",
            }

        first_window = [p.duration_ms for p in points[:self._window_size]]
        last_window = [p.duration_ms for p in points[-self._window_size:]]

        first_avg = sum(first_window) / len(first_window)
        last_avg = sum(last_window) / len(last_window)

        if first_avg > 0:
            improvement_percent = ((first_avg - last_avg) / first_avg) * 100
        else:
            improvement_percent = 0

        mid_point = len(points) // 2
        mid_window = [p.duration_ms for p in points[max(0,mid_point-25):mid_point+25]]
        mid_avg = sum(mid_window) / len(mid_window) if mid_window else first_avg

        early_improvement = ((first_avg - mid_avg) / first_avg * 100) if first_avg > 0 else 0
        late_improvement = ((mid_avg - last_avg) / mid_avg * 100) if mid_avg > 0 else 0

        if abs(late_improvement) < 2.0:
            phase = "plateaued"
            message = f"Grace has plateaued at {last_avg:.0f}ms. This is likely her physical limit for '{operation}'."
        elif late_improvement > 0:
            phase = "still_improving"
            message = f"Grace is still improving at '{operation}'. Current rate: {late_improvement:.1f}% improvement in recent half."
        else:
            phase = "degrading"
            message = f"Grace is getting slower at '{operation}'. Investigate for performance regression."

        return {
            "operation": operation,
            "total_executions": len(points),
            "first_avg_ms": round(first_avg, 1),
            "current_avg_ms": round(last_avg, 1),
            "best_ms": round(min(p.duration_ms for p in points), 1),
            "total_improvement_percent": round(improvement_percent, 1),
            "early_improvement_percent": round(early_improvement, 1),
            "late_improvement_percent": round(late_improvement, 1),
            "phase": phase,
            "message": message,
        }

    def get_all_curves(self) -> Dict[str, Any]:
        """Get learning curves for all operations."""
        curves = {}
        for op in self._curves:
            curves[op] = self.get_curve(op)

        improving = [op for op, c in curves.items() if c.get("phase") == "still_improving"]
        plateaued = [op for op, c in curves.items() if c.get("phase") == "plateaued"]
        degrading = [op for op, c in curves.items() if c.get("phase") == "degrading"]

        return {
            "curves": curves,
            "summary": {
                "total_operations": len(curves),
                "improving": improving,
                "plateaued": plateaued,
                "degrading": degrading,
            },
        }

    def to_json(self) -> Dict:
        """Serialize for persistence."""
        return {
            op: [{"n": p.invocation_number, "ms": p.duration_ms, "ts": p.timestamp.isoformat()}
                 for p in points[-500:]]
            for op, points in self._curves.items()
        }

    def from_json(self, data: Dict):
        """Deserialize from persistence."""
        for op, points in data.items():
            self._curves[op] = [
                LearningCurvePoint(
                    invocation_number=p["n"],
                    duration_ms=p["ms"],
                    timestamp=datetime.fromisoformat(p["ts"]),
                )
                for p in points
            ]


# =============================================================================
# 2. PERSISTENCE - Grace remembers herself across restarts
# =============================================================================

class TimeSensePersistence:
    """
    Saves and loads TimeSense state to disk.

    Grace doesn't forget her own speed on restart. She wakes up
    knowing her processing rates, capacity history, learning curves,
    and performance trends.
    """

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent / "data" / "timesense"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save(self, timesense_engine) -> bool:
        """Save TimeSense state to disk."""
        try:
            state = {
                "saved_at": datetime.now().isoformat(),
                "stats": timesense_engine._stats,
                "operation_stats": {
                    name: timer.get_stats()
                    for name, timer in timesense_engine._operation_timers.items()
                },
                "processing_rates": timesense_engine._rate_tracker.get_all_rates(),
                "learning_curves": timesense_engine.learning_curves.to_json()
                    if hasattr(timesense_engine, 'learning_curves') else {},
            }

            filepath = self.data_dir / "timesense_state.json"
            with open(filepath, "w") as f:
                json.dump(state, f, indent=2, default=str)

            logger.info(f"[TIMESENSE] State saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"[TIMESENSE] Failed to save state: {e}")
            return False

    def load(self, timesense_engine) -> bool:
        """Load TimeSense state from disk."""
        try:
            filepath = self.data_dir / "timesense_state.json"
            if not filepath.exists():
                return False

            with open(filepath, "r") as f:
                state = json.load(f)

            if "learning_curves" in state and hasattr(timesense_engine, 'learning_curves'):
                timesense_engine.learning_curves.from_json(state["learning_curves"])

            saved_at = state.get("saved_at", "unknown")
            logger.info(f"[TIMESENSE] State restored from {saved_at}")
            return True
        except Exception as e:
            logger.error(f"[TIMESENSE] Failed to load state: {e}")
            return False


# =============================================================================
# 3. PREDICTIVE SCALING - Grace forecasts capacity exhaustion
# =============================================================================

class PredictiveScaler:
    """
    Grace forecasts when she'll run out of resources.

    "At current ingestion rate of 2GB/day, my 50GB disk will be full
    in 12 days. At current query growth of 10%/week, I'll need to
    scale embedding capacity in 3 weeks."
    """

    def __init__(self):
        self._capacity_history: List[Tuple[datetime, Dict[str, float]]] = []
        self._ingestion_history: List[Tuple[datetime, float]] = []

    def record_capacity(self, snapshot: Dict[str, float]):
        """Record a capacity snapshot for trend analysis."""
        self._capacity_history.append((datetime.now(), snapshot))
        if len(self._capacity_history) > 1000:
            self._capacity_history = self._capacity_history[-1000:]

    def record_ingestion(self, bytes_ingested: float):
        """Record data ingestion for growth projection."""
        self._ingestion_history.append((datetime.now(), bytes_ingested))
        if len(self._ingestion_history) > 1000:
            self._ingestion_history = self._ingestion_history[-1000:]

    def predict_disk_exhaustion(self, available_bytes: float) -> Dict[str, Any]:
        """Predict when disk will be full based on ingestion rate."""
        if len(self._ingestion_history) < 2:
            return {
                "prediction": "insufficient_data",
                "message": "Need more ingestion history to predict disk exhaustion.",
            }

        now = datetime.now()
        one_day_ago = now - timedelta(days=1)
        recent = [b for ts, b in self._ingestion_history if ts > one_day_ago]
        daily_bytes = sum(recent)

        if daily_bytes <= 0:
            return {
                "prediction": "no_growth",
                "daily_ingestion": "0 B/day",
                "message": "No data ingested recently. Disk exhaustion not imminent.",
            }

        days_remaining = available_bytes / daily_bytes

        from cognitive.timesense import format_data_size
        return {
            "prediction": "estimated",
            "daily_ingestion": format_data_size(daily_bytes) + "/day",
            "available_space": format_data_size(available_bytes),
            "days_until_full": round(days_remaining, 1),
            "exhaustion_date": (now + timedelta(days=days_remaining)).strftime("%Y-%m-%d"),
            "recommendation": self._scaling_recommendation(days_remaining),
        }

    def _scaling_recommendation(self, days_remaining: float) -> str:
        if days_remaining < 3:
            return "CRITICAL: Disk full within 3 days. Archive old data or expand storage immediately."
        elif days_remaining < 14:
            return "WARNING: Disk full within 2 weeks. Plan for archival or storage expansion."
        elif days_remaining < 30:
            return "NOTICE: Disk full within a month. Schedule maintenance window for cleanup."
        return "HEALTHY: Over a month of capacity remaining at current growth rate."


# =============================================================================
# 4. TIME-AWARE SCHEDULING
# =============================================================================

class TimeAwareScheduler:
    """
    Grace schedules heavy tasks during optimal windows.

    She tracks hourly load patterns and recommends when to run
    expensive operations (reindexing, bulk ingestion, model retraining).
    """

    def __init__(self):
        self._hourly_load: Dict[int, List[float]] = defaultdict(list)

    def record_load(self, hour: int, load_factor: float):
        """Record system load for an hour."""
        self._hourly_load[hour].append(load_factor)
        if len(self._hourly_load[hour]) > 100:
            self._hourly_load[hour] = self._hourly_load[hour][-100:]

    def get_optimal_window(self, duration_hours: int = 2) -> Dict[str, Any]:
        """Find the best time window for a heavy operation."""
        if not self._hourly_load:
            return {
                "window": "02:00-05:00",
                "confidence": "default",
                "message": "No load data yet. Using default low-traffic window (2am-5am).",
            }

        hourly_avg = {}
        for hour in range(24):
            loads = self._hourly_load.get(hour, [])
            hourly_avg[hour] = sum(loads) / len(loads) if loads else 0.5

        best_start = 0
        best_score = float("inf")
        for start in range(24):
            score = sum(
                hourly_avg.get((start + h) % 24, 0.5)
                for h in range(duration_hours)
            )
            if score < best_score:
                best_score = score
                best_start = start

        end = (best_start + duration_hours) % 24

        return {
            "window": f"{best_start:02d}:00-{end:02d}:00",
            "avg_load_in_window": round(best_score / duration_hours, 2),
            "confidence": "measured" if sum(len(v) for v in self._hourly_load.values()) > 48 else "low",
            "hourly_load_map": {
                f"{h:02d}:00": round(hourly_avg.get(h, 0.5), 2)
                for h in range(24)
            },
        }

    def is_good_time_now(self, threshold: float = 0.4) -> Dict[str, Any]:
        """Is right now a good time for heavy operations?"""
        current_hour = datetime.now().hour
        loads = self._hourly_load.get(current_hour, [])
        current_avg = sum(loads) / len(loads) if loads else 0.5

        is_good = current_avg < threshold
        return {
            "hour": current_hour,
            "avg_load": round(current_avg, 2),
            "threshold": threshold,
            "is_good_time": is_good,
            "recommendation": "Go ahead" if is_good else "Consider waiting for a lower-traffic window",
        }


# =============================================================================
# 5. OPERATION DEPENDENCY GRAPHS
# =============================================================================

@dataclass
class OperationNode:
    """A node in the operation dependency graph."""
    name: str
    operation: str
    estimated_ms: float = 0
    depends_on: List[str] = field(default_factory=list)
    can_parallel: bool = False


class OperationDependencyGraph:
    """
    Grace understands task ordering and parallelization.

    "Can't embed until chunking is done. Can chunk and scan in parallel.
    Critical path: parse -> chunk -> embed -> store = 7 minutes."
    """

    KNOWN_DEPENDENCIES = {
        "file_scan": [],
        "document_parse": ["file_scan"],
        "text_chunk": ["document_parse"],
        "embedding_generate": ["text_chunk"],
        "vector_store": ["embedding_generate"],
        "query_embed": [],
        "retrieval_search": ["query_embed"],
        "retrieval_rerank": ["retrieval_search"],
        "llm_generate": ["retrieval_rerank"],
        "integrity_check": ["vector_store"],
        "http_fetch": [],
        "content_extract": ["http_fetch"],
        "text_parse": ["content_extract"],
    }

    def __init__(self):
        self._custom_deps: Dict[str, List[str]] = {}

    def add_dependency(self, operation: str, depends_on: str):
        """Add a custom dependency."""
        if operation not in self._custom_deps:
            self._custom_deps[operation] = []
        self._custom_deps[operation].append(depends_on)

    def get_dependencies(self, operation: str) -> List[str]:
        """Get all dependencies for an operation."""
        deps = list(self.KNOWN_DEPENDENCIES.get(operation, []))
        deps.extend(self._custom_deps.get(operation, []))
        return deps

    def get_execution_order(self, operations: List[str]) -> Dict[str, Any]:
        """Calculate execution order with parallelization opportunities."""
        all_deps = {op: self.get_dependencies(op) for op in operations}

        levels: List[List[str]] = []
        scheduled = set()
        remaining = set(operations)

        max_iterations = len(operations) + 1
        iteration = 0
        while remaining and iteration < max_iterations:
            iteration += 1
            ready = []
            for op in remaining:
                deps = [d for d in all_deps.get(op, []) if d in remaining or d not in scheduled]
                unmet = [d for d in deps if d not in scheduled]
                if not unmet:
                    ready.append(op)

            if not ready:
                ready = list(remaining)[:1]

            levels.append(ready)
            for op in ready:
                scheduled.add(op)
                remaining.discard(op)

        critical_path = self._find_critical_path(operations, all_deps)

        return {
            "execution_levels": [
                {
                    "level": i,
                    "operations": level,
                    "parallel": len(level) > 1,
                }
                for i, level in enumerate(levels)
            ],
            "total_levels": len(levels),
            "max_parallelism": max(len(level) for level in levels) if levels else 0,
            "critical_path": critical_path,
            "can_parallelize": any(len(level) > 1 for level in levels),
        }

    def _find_critical_path(self, operations: List[str], deps: Dict[str, List[str]]) -> List[str]:
        """Find the critical (longest) path through the dependency graph."""
        if not operations:
            return []

        roots = [op for op in operations if not deps.get(op)]
        if not roots:
            return operations[:1]

        def longest_path(op, visited=None):
            if visited is None:
                visited = set()
            if op in visited:
                return [op]
            visited.add(op)
            dependents = [o for o in operations if op in deps.get(o, [])]
            if not dependents:
                return [op]
            paths = [longest_path(d, visited.copy()) for d in dependents]
            longest = max(paths, key=len) if paths else []
            return [op] + longest

        all_paths = [longest_path(root) for root in roots]
        return max(all_paths, key=len) if all_paths else []
