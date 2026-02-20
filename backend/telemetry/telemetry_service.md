# Telemetry Service

**File:** `telemetry/telemetry_service.py`

## Overview

Telemetry service for Grace's self-modeling mechanism.

INTEGRATED with LLM Orchestrator for health monitoring.

This service provides context managers and utilities for tracking
operations, measuring performance, and enabling replay functionality.

Health checks prioritize LLM Orchestrator availability over direct
Ollama client access to ensure consistent system status reporting.

## Classes

- `TelemetryService`

## Key Methods

- `track_operation()`
- `record_tokens()`
- `record_confidence()`
- `capture_system_state()`
- `get_telemetry_service()`

---
*Grace 3.1*
