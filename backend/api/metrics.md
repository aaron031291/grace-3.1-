# Metrics

**File:** `api/metrics.py`

## Overview

Prometheus Metrics Endpoint
===========================
Exposes application metrics in Prometheus format for monitoring.

## Classes

- `MetricValue`
- `MetricsRegistry`
- `MetricsMiddlewareHelper`

## Key Methods

- `register()`
- `counter_inc()`
- `counter_get()`
- `gauge_set()`
- `gauge_inc()`
- `gauge_dec()`
- `gauge_get()`
- `histogram_observe()`
- `summary_observe()`
- `format_prometheus()`
- `get_metrics_registry()`
- `record_request_start()`
- `record_request_end()`
- `collect_system_metrics()`
- `inc_request_count()`

---
*Grace 3.1*
