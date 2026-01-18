import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import deque
import statistics
logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """
    Tracks performance metrics for Memory Mesh operations.

    Provides:
    - Real-time latency tracking
    - P50/P95/P99 percentiles
    - Cache hit rates
    - Throughput metrics
    - Performance alerts
    """

    def __init__(self, max_samples: int = 1000):
        """
        Initialize performance metrics tracker.

        Args:
            max_samples: Maximum samples to keep for calculations
        """
        self.max_samples = max_samples

        # Latency tracking (recent samples)
        self.query_latencies = deque(maxlen=max_samples)
        self.embedding_latencies = deque(maxlen=max_samples)
        self.vector_search_latencies = deque(maxlen=max_samples)
        self.stats_query_latencies = deque(maxlen=max_samples)

        # Cache metrics
        self.cache_hits = 0
        self.cache_misses = 0

        # Throughput tracking
        self.total_queries = 0
        self.queries_per_minute = deque(maxlen=60)  # Last 60 minutes
        self.start_time = datetime.utcnow()
        self.last_minute_count = 0
        self.current_minute = datetime.utcnow().minute

        # Alerts
        self.performance_alerts = []

        logger.info("[METRICS] Performance monitoring initialized")

    # ================================================================
    # LATENCY TRACKING
    # ================================================================

    def record_query_latency(self, latency_ms: float):
        """Record query latency in milliseconds"""
        self.query_latencies.append(latency_ms)
        self.total_queries += 1

        # Track per-minute throughput
        current_minute = datetime.utcnow().minute
        if current_minute != self.current_minute:
            self.queries_per_minute.append(self.last_minute_count)
            self.last_minute_count = 1
            self.current_minute = current_minute
        else:
            self.last_minute_count += 1

        # Alert if latency is high
        if latency_ms > 1000:  # > 1 second
            self._add_alert(
                f"High query latency: {latency_ms:.0f}ms",
                severity="warning"
            )

    def record_embedding_latency(self, latency_ms: float):
        """Record embedding generation latency"""
        self.embedding_latencies.append(latency_ms)

        if latency_ms > 5000:  # > 5 seconds
            self._add_alert(
                f"High embedding latency: {latency_ms:.0f}ms",
                severity="warning"
            )

    def record_vector_search_latency(self, latency_ms: float):
        """Record vector search latency"""
        self.vector_search_latencies.append(latency_ms)

    def record_stats_query_latency(self, latency_ms: float):
        """Record stats query latency"""
        self.stats_query_latencies.append(latency_ms)

    # ================================================================
    # CACHE METRICS
    # ================================================================

    def record_cache_hit(self):
        """Record cache hit"""
        self.cache_hits += 1

    def record_cache_miss(self):
        """Record cache miss"""
        self.cache_misses += 1

    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate (0-1)"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    # ================================================================
    # PERCENTILE CALCULATIONS
    # ================================================================

    def _calculate_percentiles(
        self,
        values: deque
    ) -> Dict[str, float]:
        """Calculate percentile statistics"""
        if not values:
            return {
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0
            }

        sorted_values = sorted(values)
        n = len(sorted_values)

        return {
            "p50": sorted_values[int(n * 0.50)] if n > 0 else 0.0,
            "p95": sorted_values[int(n * 0.95)] if n > 0 else 0.0,
            "p99": sorted_values[int(n * 0.99)] if n > 0 else 0.0,
            "mean": statistics.mean(sorted_values) if n > 0 else 0.0,
            "min": min(sorted_values) if n > 0 else 0.0,
            "max": max(sorted_values) if n > 0 else 0.0
        }

    def get_query_percentiles(self) -> Dict[str, float]:
        """Get query latency percentiles"""
        return self._calculate_percentiles(self.query_latencies)

    def get_embedding_percentiles(self) -> Dict[str, float]:
        """Get embedding latency percentiles"""
        return self._calculate_percentiles(self.embedding_latencies)

    def get_vector_search_percentiles(self) -> Dict[str, float]:
        """Get vector search latency percentiles"""
        return self._calculate_percentiles(self.vector_search_latencies)

    # ================================================================
    # THROUGHPUT METRICS
    # ================================================================

    def get_throughput_metrics(self) -> Dict[str, Any]:
        """Get throughput metrics"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        # Queries per second (overall average)
        qps = self.total_queries / uptime if uptime > 0 else 0

        # Recent queries per minute
        recent_qpm = (
            statistics.mean(self.queries_per_minute)
            if self.queries_per_minute
            else 0
        )

        return {
            "total_queries": self.total_queries,
            "uptime_seconds": uptime,
            "queries_per_second": qps,
            "queries_per_minute_recent": recent_qpm,
            "current_minute_count": self.last_minute_count
        }

    # ================================================================
    # COMPREHENSIVE METRICS
    # ================================================================

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all performance metrics"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "query_latency": self.get_query_percentiles(),
            "embedding_latency": self.get_embedding_percentiles(),
            "vector_search_latency": self.get_vector_search_percentiles(),
            "stats_query_latency": self._calculate_percentiles(self.stats_query_latencies),
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": self.get_cache_hit_rate()
            },
            "throughput": self.get_throughput_metrics(),
            "alerts": self.performance_alerts[-10:]  # Last 10 alerts
        }

    # ================================================================
    # ALERTS
    # ================================================================

    def _add_alert(self, message: str, severity: str = "info"):
        """Add performance alert"""
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "severity": severity
        }

        self.performance_alerts.append(alert)

        # Keep only recent alerts
        if len(self.performance_alerts) > 100:
            self.performance_alerts = self.performance_alerts[-100:]

        if severity in ["warning", "error"]:
            logger.warning(f"[METRICS] {message}")

    def check_performance_health(self) -> Dict[str, Any]:
        """
        Check overall performance health.

        Returns:
            Health status and recommendations
        """
        issues = []
        recommendations = []

        # Check query latency
        query_p95 = self.get_query_percentiles().get("p95", 0)
        if query_p95 > 500:
            issues.append(f"High P95 query latency: {query_p95:.0f}ms")
            recommendations.append("Consider adding more indexes or caching")

        # Check cache hit rate
        hit_rate = self.get_cache_hit_rate()
        if hit_rate < 0.5 and (self.cache_hits + self.cache_misses) > 100:
            issues.append(f"Low cache hit rate: {hit_rate:.1%}")
            recommendations.append("Review caching strategy and TTL settings")

        # Check embedding latency
        embedding_p95 = self.get_embedding_percentiles().get("p95", 0)
        if embedding_p95 > 3000:
            issues.append(f"High P95 embedding latency: {embedding_p95:.0f}ms")
            recommendations.append("Consider batching or async processing")

        # Overall health score
        health_score = 100
        health_score -= min(len(issues) * 20, 80)  # Deduct for issues

        if health_score >= 80:
            status = "healthy"
        elif health_score >= 60:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "health_score": health_score,
            "issues": issues,
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat()
        }

    # ================================================================
    # RESET & MANAGEMENT
    # ================================================================

    def reset_metrics(self):
        """Reset all metrics"""
        self.query_latencies.clear()
        self.embedding_latencies.clear()
        self.vector_search_latencies.clear()
        self.stats_query_latencies.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_queries = 0
        self.queries_per_minute.clear()
        self.start_time = datetime.utcnow()
        self.performance_alerts = []

        logger.info("[METRICS] All metrics reset")


# ================================================================
# CONTEXT MANAGER FOR TIMING
# ================================================================

class TimedOperation:
    """
    Context manager for timing operations.

    Usage:
        with TimedOperation(metrics, "query") as timer:
            # ... perform operation ...
            pass
    """

    def __init__(
        self,
        metrics: PerformanceMetrics,
        operation_type: str
    ):
        """
        Initialize timed operation.

        Args:
            metrics: PerformanceMetrics instance
            operation_type: Type of operation (query, embedding, etc.)
        """
        self.metrics = metrics
        self.operation_type = operation_type
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        """Start timing"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and record"""
        self.end_time = time.time()
        latency_ms = (self.end_time - self.start_time) * 1000

        # Record based on operation type
        if self.operation_type == "query":
            self.metrics.record_query_latency(latency_ms)
        elif self.operation_type == "embedding":
            self.metrics.record_embedding_latency(latency_ms)
        elif self.operation_type == "vector_search":
            self.metrics.record_vector_search_latency(latency_ms)
        elif self.operation_type == "stats":
            self.metrics.record_stats_query_latency(latency_ms)


# ================================================================
# GLOBAL METRICS INSTANCE
# ================================================================

_global_metrics: Optional[PerformanceMetrics] = None


def get_performance_metrics() -> PerformanceMetrics:
    """Get or create global performance metrics instance"""
    global _global_metrics

    if _global_metrics is None:
        _global_metrics = PerformanceMetrics()

    return _global_metrics
