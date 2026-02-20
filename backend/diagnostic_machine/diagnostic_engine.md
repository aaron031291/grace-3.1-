# Diagnostic Engine

**File:** `diagnostic_machine/diagnostic_engine.py`

## Overview

Diagnostic Engine - Main Orchestrator for 4-Layer Diagnostic Machine

Coordinates:
- Layer 1: Sensors (data collection)
- Layer 2: Interpreters (pattern analysis)
- Layer 3: Judgement (decision making)
- Layer 4: Action Routing (response execution)

Features:
- 60-second heartbeat for continuous monitoring
- Event-driven sensor triggering
- CI/CD pipeline integration
- Forensic analysis and AVN/AVM

## Classes

- `EngineState`
- `TriggerSource`
- `DiagnosticCycle`
- `EngineStats`
- `DiagnosticEngine`

## Key Methods

- `state()`
- `stats()`
- `start()`
- `stop()`
- `pause()`
- `resume()`
- `run_cycle()`
- `trigger_from_sensor()`
- `trigger_from_cicd()`
- `trigger_from_webhook()`
- `on_cycle_complete()`
- `on_alert()`
- `on_heal()`
- `on_freeze()`
- `get_recent_cycles()`

---
*Grace 3.1*
