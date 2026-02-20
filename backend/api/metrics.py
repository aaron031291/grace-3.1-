"""
Prometheus Metrics Endpoint
===========================
Exposes application metrics in Prometheus format for monitoring.
"""

from fastapi import APIRouter, Response
from typing import Dict, Any, Optional
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@dataclass
class MetricValue:
    """Represents a metric value with labels."""
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsRegistry:
    """
    Simple metrics registry compatible with Prometheus format.
    Supports Counter, Gauge, Histogram, and Summary metric types.
    """

    def __init__(self):
        self._counters: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._gauges: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._histograms: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
        self._summaries: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
        self._metadata: Dict[str, Dict[str, str]] = {}
        self._lock = threading.Lock()

    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to a string key."""
        if not labels:
            return ""
        return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))

    def register(self, name: str, metric_type: str, help_text: str):
        """Register metric metadata."""
        self._metadata[name] = {
            "type": metric_type,
            "help": help_text
        }

    # Counter methods
    def counter_inc(self, name: str, value: float = 1, labels: Dict[str, str] = None):
        """Increment a counter."""
        with self._lock:
            key = self._labels_to_key(labels or {})
            self._counters[name][key] += value

    def counter_get(self, name: str, labels: Dict[str, str] = None) -> float:
        """Get counter value."""
        key = self._labels_to_key(labels or {})
        return self._counters[name][key]

    # Gauge methods
    def gauge_set(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge value."""
        with self._lock:
            key = self._labels_to_key(labels or {})
            self._gauges[name][key] = value

    def gauge_inc(self, name: str, value: float = 1, labels: Dict[str, str] = None):
        """Increment a gauge."""
        with self._lock:
            key = self._labels_to_key(labels or {})
            self._gauges[name][key] += value

    def gauge_dec(self, name: str, value: float = 1, labels: Dict[str, str] = None):
        """Decrement a gauge."""
        with self._lock:
            key = self._labels_to_key(labels or {})
            self._gauges[name][key] -= value

    def gauge_get(self, name: str, labels: Dict[str, str] = None) -> float:
        """Get gauge value."""
        key = self._labels_to_key(labels or {})
        return self._gauges[name][key]

    # Histogram methods
    def histogram_observe(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe a value for histogram."""
        with self._lock:
            key = self._labels_to_key(labels or {})
            self._histograms[name][key].append(value)
            # Keep only last 10000 observations
            if len(self._histograms[name][key]) > 10000:
                self._histograms[name][key] = self._histograms[name][key][-10000:]

    # Summary methods
    def summary_observe(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe a value for summary."""
        with self._lock:
            key = self._labels_to_key(labels or {})
            self._summaries[name][key].append(value)
            # Keep only last 10000 observations
            if len(self._summaries[name][key]) > 10000:
                self._summaries[name][key] = self._summaries[name][key][-10000:]

    def _format_histogram(self, name: str) -> str:
        """Format histogram in Prometheus format."""
        lines = []
        buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, float('inf')]

        for key, values in self._histograms[name].items():
            labels_str = f"{{{key}}}" if key else ""

            # Calculate bucket counts
            for bucket in buckets:
                count = sum(1 for v in values if v <= bucket)
                bucket_label = f'le="{bucket}"' if bucket != float('inf') else 'le="+Inf"'
                full_labels = f"{{{key},{bucket_label}}}" if key else f"{{{bucket_label}}}"
                lines.append(f"{name}_bucket{full_labels} {count}")

            # Sum and count
            total = sum(values)
            count = len(values)
            sum_labels = f"{{{key}}}" if key else ""
            lines.append(f"{name}_sum{sum_labels} {total}")
            lines.append(f"{name}_count{sum_labels} {count}")

        return "\n".join(lines)

    def _format_summary(self, name: str) -> str:
        """Format summary in Prometheus format."""
        lines = []
        quantiles = [0.5, 0.9, 0.99]

        for key, values in self._summaries[name].items():
            if not values:
                continue

            sorted_values = sorted(values)
            labels_str = f"{{{key}}}" if key else ""

            # Calculate quantiles
            for q in quantiles:
                idx = int(len(sorted_values) * q)
                idx = min(idx, len(sorted_values) - 1)
                value = sorted_values[idx]
                q_label = f'quantile="{q}"'
                full_labels = f"{{{key},{q_label}}}" if key else f"{{{q_label}}}"
                lines.append(f"{name}{full_labels} {value}")

            # Sum and count
            total = sum(values)
            count = len(values)
            lines.append(f"{name}_sum{labels_str} {total}")
            lines.append(f"{name}_count{labels_str} {count}")

        return "\n".join(lines)

    def format_prometheus(self) -> str:
        """Format all metrics in Prometheus text format."""
        lines = []

        # Counters
        for name, values in self._counters.items():
            if name in self._metadata:
                lines.append(f"# HELP {name} {self._metadata[name]['help']}")
                lines.append(f"# TYPE {name} counter")
            for key, value in values.items():
                labels_str = f"{{{key}}}" if key else ""
                lines.append(f"{name}{labels_str} {value}")
            lines.append("")

        # Gauges
        for name, values in self._gauges.items():
            if name in self._metadata:
                lines.append(f"# HELP {name} {self._metadata[name]['help']}")
                lines.append(f"# TYPE {name} gauge")
            for key, value in values.items():
                labels_str = f"{{{key}}}" if key else ""
                lines.append(f"{name}{labels_str} {value}")
            lines.append("")

        # Histograms
        for name in self._histograms:
            if name in self._metadata:
                lines.append(f"# HELP {name} {self._metadata[name]['help']}")
                lines.append(f"# TYPE {name} histogram")
            lines.append(self._format_histogram(name))
            lines.append("")

        # Summaries
        for name in self._summaries:
            if name in self._metadata:
                lines.append(f"# HELP {name} {self._metadata[name]['help']}")
                lines.append(f"# TYPE {name} summary")
            lines.append(self._format_summary(name))
            lines.append("")

        return "\n".join(lines)


# Global metrics registry
metrics = MetricsRegistry()

# Register standard metrics
metrics.register("grace_http_requests_total", "counter", "Total HTTP requests")
metrics.register("grace_http_request_duration_seconds", "histogram", "HTTP request duration in seconds")
metrics.register("grace_http_requests_in_progress", "gauge", "Number of HTTP requests in progress")
metrics.register("grace_chat_messages_total", "counter", "Total chat messages processed")
metrics.register("grace_chat_response_time_seconds", "histogram", "Chat response generation time")
metrics.register("grace_embeddings_generated_total", "counter", "Total embeddings generated")
metrics.register("grace_documents_ingested_total", "counter", "Total documents ingested")
metrics.register("grace_active_websocket_connections", "gauge", "Active WebSocket connections")
metrics.register("grace_ollama_requests_total", "counter", "Total Ollama API requests")
metrics.register("grace_ollama_errors_total", "counter", "Total Ollama API errors")
metrics.register("grace_db_queries_total", "counter", "Total database queries")
metrics.register("grace_db_query_duration_seconds", "histogram", "Database query duration")
metrics.register("grace_cache_hits_total", "counter", "Cache hit count")
metrics.register("grace_cache_misses_total", "counter", "Cache miss count")
metrics.register("grace_memory_usage_bytes", "gauge", "Memory usage in bytes")
metrics.register("grace_cpu_usage_percent", "gauge", "CPU usage percentage")


def get_metrics_registry() -> MetricsRegistry:
    """Get the global metrics registry."""
    return metrics


# =============================================================================
# Metrics Middleware Helper
# =============================================================================

class MetricsMiddlewareHelper:
    """Helper class for recording HTTP metrics."""

    @staticmethod
    def record_request_start(method: str, path: str):
        """Record request start."""
        metrics.gauge_inc("grace_http_requests_in_progress", labels={"method": method, "path": path})

    @staticmethod
    def record_request_end(method: str, path: str, status_code: int, duration: float):
        """Record request completion."""
        labels = {"method": method, "path": path, "status": str(status_code)}
        metrics.counter_inc("grace_http_requests_total", labels=labels)
        metrics.histogram_observe("grace_http_request_duration_seconds", duration, labels={"method": method, "path": path})
        metrics.gauge_dec("grace_http_requests_in_progress", labels={"method": method, "path": path})


# =============================================================================
# System Metrics Collection
# =============================================================================

def collect_system_metrics():
    """Collect system-level metrics."""
    import psutil

    # Memory
    memory = psutil.virtual_memory()
    metrics.gauge_set("grace_memory_usage_bytes", memory.used)
    metrics.gauge_set("grace_memory_total_bytes", memory.total)
    metrics.gauge_set("grace_memory_percent", memory.percent)

    # CPU
    cpu_percent = psutil.cpu_percent(interval=None)
    metrics.gauge_set("grace_cpu_usage_percent", cpu_percent)

    # Disk
    disk = psutil.disk_usage('/')
    metrics.gauge_set("grace_disk_usage_bytes", disk.used)
    metrics.gauge_set("grace_disk_total_bytes", disk.total)
    metrics.gauge_set("grace_disk_percent", disk.percent)


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("")
@router.get("/")
async def get_metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text exposition format.
    """
    # Collect fresh system metrics
    try:
        collect_system_metrics()
    except Exception:
        pass  # psutil may not be available

    output = metrics.format_prometheus()
    return Response(
        content=output,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@router.get("/json")
async def get_metrics_json():
    """
    Get metrics in JSON format for easier debugging.
    """
    return {
        "counters": dict(metrics._counters),
        "gauges": dict(metrics._gauges),
        "histograms": {k: {kk: len(vv) for kk, vv in v.items()} for k, v in metrics._histograms.items()},
        "summaries": {k: {kk: len(vv) for kk, vv in v.items()} for k, v in metrics._summaries.items()},
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# Convenience functions for use throughout the app
# =============================================================================

def inc_request_count(method: str, path: str, status: int):
    """Increment HTTP request counter."""
    metrics.counter_inc("grace_http_requests_total", labels={
        "method": method,
        "path": path,
        "status": str(status)
    })


def observe_request_duration(method: str, path: str, duration: float):
    """Record HTTP request duration."""
    metrics.histogram_observe("grace_http_request_duration_seconds", duration, labels={
        "method": method,
        "path": path
    })


def inc_chat_messages(model: str = "unknown"):
    """Increment chat message counter."""
    metrics.counter_inc("grace_chat_messages_total", labels={"model": model})


def observe_chat_response_time(duration: float, model: str = "unknown"):
    """Record chat response time."""
    metrics.histogram_observe("grace_chat_response_time_seconds", duration, labels={"model": model})


def inc_embeddings(model: str = "unknown", count: int = 1):
    """Increment embeddings counter."""
    metrics.counter_inc("grace_embeddings_generated_total", value=count, labels={"model": model})


def inc_documents_ingested(doc_type: str = "unknown"):
    """Increment documents ingested counter."""
    metrics.counter_inc("grace_documents_ingested_total", labels={"type": doc_type})


def set_websocket_connections(count: int, channel: str = "all"):
    """Set active WebSocket connection count."""
    metrics.gauge_set("grace_active_websocket_connections", count, labels={"channel": channel})


def inc_ollama_request(endpoint: str = "chat"):
    """Increment Ollama request counter."""
    metrics.counter_inc("grace_ollama_requests_total", labels={"endpoint": endpoint})


def inc_ollama_error(endpoint: str = "chat", error_type: str = "unknown"):
    """Increment Ollama error counter."""
    metrics.counter_inc("grace_ollama_errors_total", labels={"endpoint": endpoint, "error": error_type})


def inc_db_query(operation: str = "select"):
    """Increment database query counter."""
    metrics.counter_inc("grace_db_queries_total", labels={"operation": operation})


def observe_db_query_duration(duration: float, operation: str = "select"):
    """Record database query duration."""
    metrics.histogram_observe("grace_db_query_duration_seconds", duration, labels={"operation": operation})


def inc_cache_hit(cache_name: str = "default"):
    """Increment cache hit counter."""
    metrics.counter_inc("grace_cache_hits_total", labels={"cache": cache_name})


def inc_cache_miss(cache_name: str = "default"):
    """Increment cache miss counter."""
    metrics.counter_inc("grace_cache_misses_total", labels={"cache": cache_name})
