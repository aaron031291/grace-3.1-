# Sensors

**File:** `diagnostic_machine/sensors.py`

## Overview

Layer 1 - Sensors: Data Collection Layer

INTEGRATED with LLM Orchestrator for health monitoring.

Collects raw data from:
- Test results (passed/failed/skipped)
- System logs (tail logs)
- Metrics (CPU, memory, disk, latency)
- Agent outputs (cognitive decisions)
- Genesis Keys (provenance data)
- GRACE Mirror (self-reflection state)
- LLM Orchestrator health status (preferred over direct Ollama)

Health checks prioritize LLM Orchestrator availability over direct
Ollama client access to ensure consistent system status reporting.

## Classes

- `SensorType`
- `TestResultData`
- `LogData`
- `MetricsData`
- `AgentOutputData`
- `GenesisKeyData`
- `GraceMirrorData`
- `SensorData`
- `SensorLayer`

## Key Methods

- `collect_all()`
- `to_dict()`

---
*Grace 3.1*
