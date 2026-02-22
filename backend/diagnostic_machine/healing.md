# Healing

**File:** `diagnostic_machine/healing.py`

## Overview

Self-Healing Actions for Diagnostic Machine

Implements concrete healing actions for:
- Database connection recovery
- Vector database reset
- Cache clearing
- Memory management
- Service restart coordination
- Log rotation
- Configuration reload

All actions are reversible where possible (Invariant 4).

## Classes

- `HealingActionType`
- `HealingRisk`
- `HealingResult`
- `HealingActionConfig`
- `HealingActionRegistry`
- `HealingExecutor`

## Key Methods

- `register_handler()`
- `get_action()`
- `get_handler()`
- `list_actions()`
- `execute()`
- `get_healing_executor()`
- `execute_healing()`

---
*Grace 3.1*
