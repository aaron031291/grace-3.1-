# Self Mirror

**File:** `cognitive/self_mirror.py`

## Overview

Grace Self-Mirror: Unified Telemetry Core

The Self-Mirror is the central nervous system that translates raw computational
signals into Operational Intelligence using the [T, M, P] telemetry vector.

T = Time (latency in milliseconds)
M = Mass (data size in bytes)
P = Pressure (load factor 0.0-1.0)

Phase 1: Telemetry Vector Protocol + Self-Mirror Core
Phase 2: Statistical Self-Modeling with pillar triggers
Phase 3: Bi-directional challenging + RFI protocol + autonomous resolution

Connects to existing subsystems:
- Layer 1 Message Bus (broadcasts [T,M,P] vectors)
- Diagnostic Machine (sensor data feeds the mirror)
- Cognitive Engine (OODA loop heartbeat timing)
- Magma Memory (stores performance patterns)
- Healing System (triggered by statistical anomalies)
- Governance (triggered by risk thresholds)
- Agent (triggered for self-building)
- Continuous Learning (triggered for knowledge acquisition)

## Classes

- `TelemetryVector`
- `PillarType`
- `PillarTrigger`
- `StatisticalProfile`
- `Challenge`
- `RFI`
- `AutonomousResolutionEngine`
- `SelfMirror`
- `_OperationMeasurer`

## Key Methods

- `to_dict()`
- `observe()`
- `mean_time()`
- `mean_mass()`
- `mean_pressure()`
- `mode_time()`
- `variance_time()`
- `std_time()`
- `variance_pressure()`
- `is_degraded()`
- `is_below_mode()`
- `is_slower_than_previous()`
- `is_high_risk_ingestion()`
- `is_evolution_ready()`
- `get_dashboard_row()`
- `create_rfi()`
- `get_stats()`
- `receive_vector()`
- `broadcast_system_pulse()`
- `measure_operation()`
- `create_rfi()`
- `start_heartbeat()`
- `stop_heartbeat()`
- `get_dashboard()`
- `get_stats()`

## Database Tables

None

## Connects To

- `cognitive.learning_hook`

---
*Documentation for Grace 3.1*
