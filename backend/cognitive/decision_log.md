# Decision Log

**File:** `cognitive/decision_log.py`

## Overview

Decision Logger for Grace's Cognitive Engine.

Implements Invariant 6: Observability Is Mandatory.
All decisions are logged with full rationale and alternatives.

## Classes

- `DecisionLogger`

## Key Methods

- `log_decision_start()`
- `log_alternatives()`
- `log_decision_complete()`
- `log_decision_finalized()`
- `log_decision_aborted()`
- `log_warning()`
- `log_invariant_violation()`
- `get_decision_log()`
- `get_all_logs()`
- `get_recent_decisions()`
- `get_active_decisions()`
- `generate_decision_report()`

---
*Grace 3.1*
