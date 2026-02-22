"""
TimeSense Enhanced Capabilities

5 capabilities that give Grace real operational intelligence:

1. AUTO-INSTRUMENTATION: Automatically times every API request, database query,
   and embedding call without manual code. Grace learns her speed across
   every operation passively.

2. TASK DECOMPOSITION: Before a complex task starts, Grace breaks it down:
   "500MB repo = ~500 files, embedding ~3min, indexing ~1min, total ~4min."
   She plans before she acts.

3. THROUGHPUT BUDGET: Grace knows "I can handle 10 chat requests/second.
   At 15 I degrade. At 20 I'll timeout." She self-throttles to stay healthy.

4. MEMORY PRESSURE PREDICTION: Before starting a heavy operation, Grace
   predicts "This will push my RAM from 60% to 85%. I should batch it."

5. PERFORMANCE TRENDS: Is Grace getting faster or slower over time?
   She tracks daily averages and detects degradation trends across days.

Classes:
- `TimeSenseMiddleware`
- `TaskStep`
- `TaskPlan`
- `TaskPlanner`
- `ThroughputBudget`
- `ThroughputTracker`
- `MemoryPressurePredictor`
- `DailyPerformance`
- `PerformanceTrendTracker`

Key Methods:
- `total_estimated_formatted()`
- `to_dict()`
- `plan()`
- `get_available_tasks()`
- `to_dict()`
- `start_operation()`
- `end_operation()`
- `get_budget()`
- `should_throttle()`
- `get_all_budgets()`
- `record_memory_usage()`
- `predict_memory_impact()`
- `record()`
- `get_trend()`
- `get_all_trends()`
"""

import logging
import time
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# 1. AUTO-INSTRUMENTATION MIDDLEWARE
# =============================================================================

class TimeSenseMiddleware:
    """
    FastAPI middleware that automatically instruments every request.

    Grace learns the timing of every API endpoint without any manual
    instrumentation. She passively builds a complete performance map.

    Usage in app.py:
        from cognitive.timesense_enhanced import TimeSenseMiddleware
        app.add_middleware(TimeSenseMiddleware)
    """

    def __init__(self, app, timesense=None):
        self.app = app
        self._timesense = timesense

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        path = scope.get("path", "unknown")
        method = scope.get("method", "GET")

        status_code = 200
        response_size = 0

        async def send_wrapper(message):
            nonlocal status_code, response_size
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                response_size += len(body) if body else 0
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            ts = self._get_timesense()
            if ts:
                operation = f"api.{method.lower()}.{self._clean_path(path)}"
                ts.record_operation(
                    operation=operation,
                    duration_ms=elapsed_ms,
                    component="api",
                    success=status_code < 400,
                    data_bytes=float(response_size),
                )

    def _get_timesense(self):
        if self._timesense:
            return self._timesense
        try:
            from cognitive.timesense import get_timesense
            return get_timesense()
        except Exception:
            return None

    @staticmethod
    def _clean_path(path: str) -> str:
        """Clean API path for grouping (remove IDs)."""
        parts = path.strip("/").split("/")
        cleaned = []
        for part in parts:
            if part.isdigit():
                cleaned.append("{id}")
            else:
                cleaned.append(part)
        return ".".join(cleaned) if cleaned else "root"


# =============================================================================
# 2. TASK DECOMPOSITION & PLANNING
# =============================================================================

@dataclass
class TaskStep:
    """A single step in a decomposed task."""
    name: str
    operation: str
    estimated_data_bytes: float
    estimated_duration_ms: float
    confidence: float
    depends_on: List[str] = field(default_factory=list)


@dataclass
class TaskPlan:
    """A complete plan for a complex task."""
    task_name: str
    steps: List[TaskStep]
    total_estimated_ms: float
    total_data_bytes: float
    parallel_possible: bool
    bottleneck_step: Optional[str]
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_estimated_formatted(self) -> str:
        s = self.total_estimated_ms / 1000
        if s < 60:
            return f"{s:.1f} seconds"
        elif s < 3600:
            return f"{s/60:.1f} minutes"
        else:
            return f"{s/3600:.1f} hours"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task_name,
            "steps": [
                {
                    "name": s.name,
                    "operation": s.operation,
                    "data_size": _format_size(s.estimated_data_bytes),
                    "estimated_time_ms": round(s.estimated_duration_ms, 0),
                    "confidence": round(s.confidence, 2),
                    "depends_on": s.depends_on,
                }
                for s in self.steps
            ],
            "total_estimated_time": self.total_estimated_formatted,
            "total_estimated_ms": round(self.total_estimated_ms, 0),
            "total_data": _format_size(self.total_data_bytes),
            "parallel_possible": self.parallel_possible,
            "bottleneck": self.bottleneck_step,
        }


class TaskPlanner:
    """
    Plans complex tasks by decomposing them into estimated steps.

    Grace thinks before she acts: "This 500MB repo ingestion will take
    ~4 minutes across 3 stages. The bottleneck is embedding at 2.5 minutes."
    """

    TASK_TEMPLATES = {
        "ingest_repository": [
            ("scan_files", "file_scan", 0.001),
            ("parse_documents", "document_parse", 0.3),
            ("chunk_text", "text_chunk", 0.1),
            ("generate_embeddings", "embedding_generate", 0.5),
            ("store_vectors", "vector_store", 0.1),
        ],
        "ingest_document": [
            ("parse_document", "document_parse", 0.3),
            ("chunk_text", "text_chunk", 0.1),
            ("generate_embeddings", "embedding_generate", 0.5),
            ("store_vectors", "vector_store", 0.1),
        ],
        "chat_query": [
            ("embed_query", "query_embed", 0.01),
            ("retrieve_context", "retrieval_search", 0.05),
            ("rerank_results", "retrieval_rerank", 0.05),
            ("generate_response", "llm_generate", 0.89),
        ],
        "knowledge_base_rebuild": [
            ("scan_all_files", "file_scan", 0.005),
            ("parse_all_documents", "document_parse", 0.2),
            ("regenerate_embeddings", "embedding_generate", 0.6),
            ("rebuild_index", "vector_index_rebuild", 0.15),
            ("verify_integrity", "integrity_check", 0.045),
        ],
        "web_scrape": [
            ("fetch_page", "http_fetch", 0.4),
            ("extract_content", "content_extract", 0.1),
            ("parse_and_clean", "text_parse", 0.1),
            ("embed_content", "embedding_generate", 0.3),
            ("store_results", "vector_store", 0.1),
        ],
    }

    def __init__(self, timesense=None):
        self._timesense = timesense

    def plan(self, task_type: str, data_bytes: float) -> TaskPlan:
        """Create a task plan with time estimates.

        Args:
            task_type: One of the known task types
            data_bytes: Total data size in bytes

        Returns:
            TaskPlan with step-by-step estimates
        """
        template = self.TASK_TEMPLATES.get(task_type, self.TASK_TEMPLATES["ingest_document"])

        steps = []
        total_ms = 0
        max_step_ms = 0
        bottleneck = None

        for name, operation, data_fraction in template:
            step_bytes = data_bytes * data_fraction
            estimated_ms = self._estimate_step(operation, step_bytes)
            confidence = self._get_confidence(operation)

            step = TaskStep(
                name=name,
                operation=operation,
                estimated_data_bytes=step_bytes,
                estimated_duration_ms=estimated_ms,
                confidence=confidence,
            )
            steps.append(step)
            total_ms += estimated_ms

            if estimated_ms > max_step_ms:
                max_step_ms = estimated_ms
                bottleneck = name

        return TaskPlan(
            task_name=task_type,
            steps=steps,
            total_estimated_ms=total_ms,
            total_data_bytes=data_bytes,
            parallel_possible=len(steps) > 2,
            bottleneck_step=bottleneck,
        )

    def _estimate_step(self, operation: str, data_bytes: float) -> float:
        """Estimate step duration from TimeSense data or defaults."""
        if self._timesense:
            rate = self._timesense._rate_tracker.get_rate(operation)
            if rate and rate.bytes_per_second > 0:
                return (data_bytes / rate.bytes_per_second) * 1000

        defaults_ms_per_mb = {
            "file_scan": 5,
            "document_parse": 200,
            "text_chunk": 50,
            "embedding_generate": 500,
            "vector_store": 100,
            "query_embed": 50,
            "retrieval_search": 100,
            "retrieval_rerank": 80,
            "llm_generate": 2000,
            "vector_index_rebuild": 300,
            "integrity_check": 50,
            "http_fetch": 1000,
            "content_extract": 100,
            "text_parse": 50,
        }

        ms_per_mb = defaults_ms_per_mb.get(operation, 200)
        data_mb = data_bytes / (1024 * 1024)
        return max(ms_per_mb * data_mb, 1.0)

    def _get_confidence(self, operation: str) -> float:
        if self._timesense:
            rate = self._timesense._rate_tracker.get_rate(operation)
            if rate:
                return min(rate.sample_count / 50, 0.95)
        return 0.1

    def get_available_tasks(self) -> List[str]:
        return list(self.TASK_TEMPLATES.keys())


# =============================================================================
# 3. THROUGHPUT BUDGET & CONCURRENCY AWARENESS
# =============================================================================

@dataclass
class ThroughputBudget:
    """Grace's understanding of how much she can handle concurrently."""
    operation: str
    max_safe_concurrent: int
    current_concurrent: int
    requests_per_second: float
    avg_latency_ms: float
    degradation_threshold: int
    is_at_capacity: bool
    headroom_percent: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "max_safe_concurrent": self.max_safe_concurrent,
            "current_concurrent": self.current_concurrent,
            "requests_per_second": round(self.requests_per_second, 1),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "degradation_threshold": self.degradation_threshold,
            "is_at_capacity": self.is_at_capacity,
            "headroom_percent": round(self.headroom_percent, 1),
        }


class ThroughputTracker:
    """
    Tracks Grace's throughput capacity and knows when to self-throttle.

    Grace knows: "I can handle 10 chat requests/second. At 15 I degrade.
    At 20 I start timing out. Right now I'm at 8/s with 20% headroom."
    """

    def __init__(self):
        self._active_operations: Dict[str, int] = defaultdict(int)
        self._request_timestamps: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._latency_at_concurrency: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
        self._max_observed_concurrent: Dict[str, int] = defaultdict(int)

    def start_operation(self, operation: str):
        """Mark operation as started (track concurrency)."""
        self._active_operations[operation] += 1
        self._request_timestamps[operation].append(datetime.now())
        current = self._active_operations[operation]
        if current > self._max_observed_concurrent[operation]:
            self._max_observed_concurrent[operation] = current

    def end_operation(self, operation: str, latency_ms: float):
        """Mark operation as completed."""
        self._active_operations[operation] = max(0, self._active_operations[operation] - 1)
        concurrent = self._active_operations[operation] + 1
        self._latency_at_concurrency[operation].append((concurrent, latency_ms))
        if len(self._latency_at_concurrency[operation]) > 2000:
            self._latency_at_concurrency[operation] = self._latency_at_concurrency[operation][-2000:]

    def get_budget(self, operation: str) -> ThroughputBudget:
        """Get throughput budget for an operation."""
        current = self._active_operations.get(operation, 0)

        now = datetime.now()
        one_sec_ago = now - timedelta(seconds=1)
        timestamps = self._request_timestamps.get(operation, deque())
        rps = sum(1 for t in timestamps if t > one_sec_ago)

        observations = self._latency_at_concurrency.get(operation, [])
        avg_latency = 0.0
        if observations:
            avg_latency = sum(lat for _, lat in observations[-100:]) / min(len(observations), 100)

        max_safe = self._estimate_max_safe(operation)
        degradation = int(max_safe * 1.5)
        headroom = ((max_safe - current) / max_safe * 100) if max_safe > 0 else 100

        return ThroughputBudget(
            operation=operation,
            max_safe_concurrent=max_safe,
            current_concurrent=current,
            requests_per_second=float(rps),
            avg_latency_ms=avg_latency,
            degradation_threshold=degradation,
            is_at_capacity=current >= max_safe,
            headroom_percent=max(0, headroom),
        )

    def should_throttle(self, operation: str) -> bool:
        """Should Grace throttle this operation?"""
        budget = self.get_budget(operation)
        return budget.is_at_capacity

    def _estimate_max_safe(self, operation: str) -> int:
        """Estimate max safe concurrent operations.

        Uses latency-at-concurrency data: find the concurrency level
        where latency starts increasing faster than linearly.
        """
        observations = self._latency_at_concurrency.get(operation, [])
        if len(observations) < 10:
            return 20

        by_concurrency: Dict[int, List[float]] = defaultdict(list)
        for conc, lat in observations:
            by_concurrency[conc].append(lat)

        avg_by_conc = {c: sum(lats)/len(lats) for c, lats in by_concurrency.items() if lats}

        if len(avg_by_conc) < 2:
            return 20

        sorted_conc = sorted(avg_by_conc.keys())
        base_latency = avg_by_conc.get(sorted_conc[0], 100)

        for conc in sorted_conc:
            if avg_by_conc[conc] > base_latency * 2.0:
                return max(1, conc - 1)

        return max(sorted_conc) if sorted_conc else 20

    def get_all_budgets(self) -> Dict[str, Dict[str, Any]]:
        all_ops = set(self._active_operations.keys()) | set(self._request_timestamps.keys())
        return {op: self.get_budget(op).to_dict() for op in all_ops}


# =============================================================================
# 4. MEMORY PRESSURE PREDICTION
# =============================================================================

class MemoryPressurePredictor:
    """
    Predicts memory impact before starting heavy operations.

    Grace thinks: "This 2GB ingestion will push my RAM from 60% to ~85%.
    I should batch it into 500MB chunks to stay under 75%."
    """

    def __init__(self):
        self._operation_memory_profiles: Dict[str, List[Tuple[float, float]]] = defaultdict(list)

    def record_memory_usage(self, operation: str, data_bytes: float, memory_delta_bytes: float):
        """Record how much memory an operation used."""
        self._operation_memory_profiles[operation].append((data_bytes, memory_delta_bytes))
        if len(self._operation_memory_profiles[operation]) > 500:
            self._operation_memory_profiles[operation] = self._operation_memory_profiles[operation][-500:]

    def predict_memory_impact(self, operation: str, data_bytes: float) -> Dict[str, Any]:
        """Predict memory impact of an operation."""
        import psutil

        current_mem = psutil.virtual_memory()
        current_used = current_mem.used
        total_mem = current_mem.total
        current_percent = current_mem.percent

        profiles = self._operation_memory_profiles.get(operation, [])
        if profiles:
            total_data = sum(d for d, _ in profiles)
            total_mem_used = sum(m for _, m in profiles)
            bytes_per_data_byte = total_mem_used / total_data if total_data > 0 else 1.0
            predicted_delta = data_bytes * bytes_per_data_byte
            confidence = "measured"
        else:
            predicted_delta = data_bytes * 2.5
            confidence = "estimated"

        predicted_used = current_used + predicted_delta
        predicted_percent = (predicted_used / total_mem) * 100

        if predicted_percent > 95:
            recommendation = "BLOCK: This will cause memory exhaustion. Reduce batch size or free memory first."
            safe_batch = self._calculate_safe_batch(total_mem, current_used, data_bytes)
        elif predicted_percent > 85:
            recommendation = f"WARN: RAM will hit {predicted_percent:.0f}%. Consider batching into smaller chunks."
            safe_batch = self._calculate_safe_batch(total_mem, current_used, data_bytes)
        elif predicted_percent > 75:
            recommendation = f"CAUTION: RAM will reach {predicted_percent:.0f}%. Monitor during execution."
            safe_batch = None
        else:
            recommendation = f"OK: RAM will be at {predicted_percent:.0f}%. Safe to proceed."
            safe_batch = None

        result = {
            "operation": operation,
            "data_size": _format_size(data_bytes),
            "current_ram_percent": round(current_percent, 1),
            "predicted_ram_percent": round(predicted_percent, 1),
            "predicted_memory_delta": _format_size(predicted_delta),
            "confidence": confidence,
            "recommendation": recommendation,
        }

        if safe_batch:
            result["suggested_batch_size"] = _format_size(safe_batch)
            result["suggested_batch_count"] = math.ceil(data_bytes / safe_batch)

        return result

    def _calculate_safe_batch(self, total_mem: float, current_used: float, data_bytes: float) -> float:
        """Calculate a safe batch size that keeps RAM under 75%."""
        target_available = total_mem * 0.25
        available = total_mem - current_used
        safe_budget = min(available * 0.5, target_available)
        return max(safe_budget / 2.5, 1024 * 1024)


# =============================================================================
# 5. PERFORMANCE TREND TRACKING
# =============================================================================

@dataclass
class DailyPerformance:
    """Performance summary for a single day."""
    date: str
    operation: str
    avg_ms: float
    p95_ms: float
    count: int
    error_rate: float


class PerformanceTrendTracker:
    """
    Tracks whether Grace is getting faster or slower over time.

    Grace monitors her own evolution: "My average query time was 200ms
    last week but it's 250ms this week. I'm degrading by 25%."
    """

    def __init__(self):
        self._daily_data: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._daily_errors: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._daily_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def record(self, operation: str, duration_ms: float, success: bool = True):
        """Record a data point for trend tracking."""
        today = datetime.now().strftime("%Y-%m-%d")
        self._daily_data[today][operation].append(duration_ms)
        self._daily_counts[today][operation] += 1
        if not success:
            self._daily_errors[today][operation] += 1

    def get_trend(self, operation: str, days: int = 7) -> Dict[str, Any]:
        """Get performance trend for an operation over N days."""
        daily_summaries = []
        today = datetime.now()

        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            data = self._daily_data.get(date, {}).get(operation, [])
            count = self._daily_counts.get(date, {}).get(operation, 0)
            errors = self._daily_errors.get(date, {}).get(operation, 0)

            if data:
                sorted_d = sorted(data)
                p95_idx = int(len(sorted_d) * 0.95)
                daily_summaries.append(DailyPerformance(
                    date=date,
                    operation=operation,
                    avg_ms=sum(data) / len(data),
                    p95_ms=sorted_d[min(p95_idx, len(sorted_d)-1)],
                    count=count,
                    error_rate=errors / count if count > 0 else 0.0,
                ))

        if len(daily_summaries) < 2:
            return {
                "operation": operation,
                "trend": "insufficient_data",
                "days_tracked": len(daily_summaries),
                "message": "Need at least 2 days of data to detect trends.",
            }

        recent = daily_summaries[0].avg_ms if daily_summaries else 0
        oldest = daily_summaries[-1].avg_ms if daily_summaries else 0

        if oldest > 0:
            change_percent = ((recent - oldest) / oldest) * 100
        else:
            change_percent = 0

        if change_percent > 20:
            trend = "degrading"
            message = f"Performance degrading: {change_percent:+.1f}% slower over {days} days."
        elif change_percent < -20:
            trend = "improving"
            message = f"Performance improving: {abs(change_percent):.1f}% faster over {days} days."
        else:
            trend = "stable"
            message = f"Performance stable: {change_percent:+.1f}% change over {days} days."

        return {
            "operation": operation,
            "trend": trend,
            "change_percent": round(change_percent, 1),
            "message": message,
            "daily": [
                {
                    "date": d.date,
                    "avg_ms": round(d.avg_ms, 1),
                    "p95_ms": round(d.p95_ms, 1),
                    "count": d.count,
                    "error_rate": round(d.error_rate, 3),
                }
                for d in reversed(daily_summaries)
            ],
        }

    def get_all_trends(self, days: int = 7) -> Dict[str, Any]:
        """Get trends for all tracked operations."""
        all_ops = set()
        for date_ops in self._daily_data.values():
            all_ops.update(date_ops.keys())

        trends = {}
        for op in all_ops:
            trends[op] = self.get_trend(op, days)

        degrading = [op for op, t in trends.items() if t.get("trend") == "degrading"]
        improving = [op for op, t in trends.items() if t.get("trend") == "improving"]

        return {
            "trends": trends,
            "summary": {
                "total_operations": len(trends),
                "degrading": degrading,
                "improving": improving,
                "degrading_count": len(degrading),
                "improving_count": len(improving),
            },
        }


# =============================================================================
# HELPERS
# =============================================================================

def _format_size(size_bytes: float) -> str:
    from cognitive.timesense import format_data_size
    return format_data_size(size_bytes)
