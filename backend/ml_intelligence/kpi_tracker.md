# Kpi Tracker

**File:** `ml_intelligence/kpi_tracker.py`

## Overview

KPI Tracking System - Component Performance Metrics

Tracks Key Performance Indicators (KPIs) for all components, aggregating
performance data into operational health signals that feed into trust scores.

Key Features:
- Action frequency tracking (every action increments KPI)
- Component-level KPI aggregation
- KPI-to-trust score conversion
- System-wide trust aggregation
- Time-windowed metrics (recent vs. historical)

## Classes

- `KPI`
- `ComponentKPIs`
- `KPITracker`

## Key Methods

- `increment()`
- `get_kpi()`
- `increment_kpi()`
- `get_trust_score()`
- `get_recent_kpi()`
- `to_dict()`
- `register_component()`
- `increment_kpi()`
- `get_component_kpis()`
- `get_component_trust_score()`
- `get_system_trust_score()`
- `get_health_signal()`
- `get_system_health()`
- `to_dict()`
- `get_kpi_tracker()`
- `reset_kpi_tracker()`

## Database Tables

None

## Connects To

Self-contained

---
*Documentation for Grace 3.1*
