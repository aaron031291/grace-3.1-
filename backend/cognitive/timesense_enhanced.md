# Timesense Enhanced

**File:** `cognitive/timesense_enhanced.py`

## Overview

TimeSense Enhanced Capabilities

5 capabilities that give Grace real operational intelligence:

1. AUTO-INSTRUMENTATION: Automatically times every API request, database query,
   and embedding call without manual code. Grace learns her speed across
   every operation passively.

2. TASK DECOMPOSITION: Before a complex task starts, Grace breaks it down:
   "500MB repo = ~500 files, embedding ~3min, indexing ~1min, total ~4min."
   She plans before she acts.

3. THROUGHPUT BUDGET: Grace knows "I can handle 10 chat requests/second.
   At 15 I degrade. At 20 I'll timeout." She self-throttles to stay healthy.

4. MEMORY PRESSURE PREDICTION: Before starting a heavy operation, Grace
   predicts "This will push my RAM from 60% to 85%. I should batch it."

5. PERFORMANCE TRENDS: Is Grace getting faster or slower over time?
   She tracks daily averages and detects degradation trends across days.

## Classes

- `TimeSenseMiddleware`
- `TaskStep`
- `TaskPlan`
- `TaskPlanner`
- `ThroughputBudget`
- `ThroughputTracker`
- `MemoryPressurePredictor`
- `DailyPerformance`
- `PerformanceTrendTracker`

## Key Methods

- `total_estimated_formatted()`
- `to_dict()`
- `plan()`
- `get_available_tasks()`
- `to_dict()`
- `start_operation()`
- `end_operation()`
- `get_budget()`
- `should_throttle()`
- `get_all_budgets()`
- `record_memory_usage()`
- `predict_memory_impact()`
- `record()`
- `get_trend()`
- `get_all_trends()`

---
*Grace 3.1*
