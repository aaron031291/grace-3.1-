# Trend Analysis

**File:** `diagnostic_machine/trend_analysis.py`

## Overview

Historical Trend Analysis for Diagnostic Machine

Provides:
- Time-series storage of diagnostic metrics
- Trend detection and visualization data
- Predictive alerting based on trends
- Baseline auto-calibration from historical data
- Anomaly detection using historical context

## Classes

- `TrendDirection`
- `TrendSignificance`
- `MetricPoint`
- `TrendResult`
- `HistoricalSummary`
- `TimeSeriesStore`
- `TrendAnalyzer`
- `DiagnosticMetricsCollector`

## Key Methods

- `store()`
- `store_batch()`
- `retrieve()`
- `get_latest()`
- `cleanup_old_data()`
- `analyze_trend()`
- `get_historical_summary()`
- `calibrate_baseline()`
- `detect_anomalies()`
- `collect_from_cycle()`
- `get_all_trends()`
- `get_time_series_store()`
- `get_trend_analyzer()`
- `get_metrics_collector()`

---
*Grace 3.1*
