# Telemetry

**File:** `api/telemetry.py`

## Overview

API endpoints for Grace's self-modeling and telemetry system.

Provides endpoints for viewing operation logs, baselines, drift alerts,
and triggering replays.

## Classes

- `OperationLogResponse`
- `BaselineResponse`
- `DriftAlertResponse`
- `SystemStateResponse`
- `ReplayResponse`
- `OperationStatsResponse`

## Key Methods

- `get_operations()`
- `get_operation()`
- `get_baselines()`
- `get_drift_alerts()`
- `acknowledge_alert()`
- `resolve_alert()`
- `get_current_system_state()`
- `capture_system_state()`
- `get_system_state_history()`
- `get_operation_stats()`
- `get_replays()`
- `replay_operation()`
- `telemetry_health()`

---
*Grace 3.1*
