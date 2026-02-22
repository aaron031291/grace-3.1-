# Governed Bridge

**File:** `execution/governed_bridge.py`

## Overview

Governed Execution Bridge

Wraps the ExecutionBridge with constitutional governance checks.
All actions must pass governance evaluation before execution.

Integration points:
- GovernanceEngine: Constitutional and policy checks
- Layer1MessageBus: Event publishing for audit
- GovernanceMetrics: KPI tracking

## Classes

- `GovernedExecutionBridge`

## Key Methods

- `config()`
- `action_history()`
- `get_stats()`
- `get_governance_log()`
- `get_governed_execution_bridge()`
- `reset_governed_bridge()`

---
*Grace 3.1*
