# Timesense

**File:** `cognitive/timesense.py`

## Overview

TimeSense Engine - Grace's Understanding of Time, Data Scale, and Capacity

TimeSense gives Grace a true cognitive understanding of:

1. DATA SCALE AWARENESS: What KB, MB, GB, TB actually mean.
   Grace knows that 1MB is a document, 1GB is a book collection,
   1TB is an enterprise dataset. She knows her processing rate at
   each scale and can reason about feasibility.

2. TEMPORAL COMPREHENSION: How long things take at different scales.
   Grace calibrates herself: "Embedding 1MB takes me 200ms,
   so embedding 1GB will take ~200 seconds." She doesn't guess --
   she measures, learns, and predicts from real experience.

3. MEMORY CAPACITY SELF-AWARENESS: Grace knows her own limits.
   Total RAM, vector DB capacity, knowledge base size, disk space.
   She can say "I have 4GB of knowledge and room for 12GB more"
   or "This 50GB dataset won't fit without purging old data."

4. PROCESSING RATE INTELLIGENCE: MB/s throughput per operation type.
   Grace tracks how fast she ingests, embeds, retrieves, and reasons
   at every data scale. She knows her own speed.

5. TIME-TO-COMPLETION ESTIMATION: "This task will take ~45 minutes."
   Grace can estimate how long any task will take based on data size
   and her measured processing rates.

This is Grace understanding her own physical reality -- like a person
knowing they can carry 20kg but not 200kg, and walk 1km in 15 minutes.

Integrates with:
- Self-Mirror: Scale awareness feeds [T,M,P] telemetry
- OODA Loop: Measures each decision phase
- Diagnostic Engine: Scale anomalies trigger diagnostics
- Message Bus: Broadcasts capacity events
- Magma Memory: Stores temporal patterns for learning

## Classes

- `DataScale`
- `DataScaleProfile`
- `CapacitySnapshot`
- `ProcessingRate`
- `ProcessingRateTracker`
- `TimeOfDay`
- `WorkPattern`
- `TemporalContext`
- `TimingRecord`
- `TimePrediction`
- `CostEstimate`
- `TemporalAnomaly`
- `OperationTimer`
- `OODACycleTimer`
- `TimeSenseEngine`
- `_TimeSenseContext`

## Key Methods

- `contains()`
- `classify_data_scale()`
- `format_data_size()`
- `total_knowledge_formatted()`
- `remaining_capacity_formatted()`
- `ram_formatted()`
- `to_dict()`
- `measure_capacity()`
- `mb_per_second()`
- `formatted_rate()`
- `estimate_time()`
- `estimate_time_formatted()`
- `record()`
- `get_rate()`
- `estimate_time()`
- `get_all_rates()`
- `to_dict()`
- `record()`
- `mean()`
- `std()`
- `median()`
- `p95()`
- `success_rate()`
- `last_duration()`
- `predict()`

## Database Tables

None

## Connects To

- `cognitive.learning_hook`
- `cognitive.self_mirror`
- `cognitive.timesense_deep`
- `cognitive.timesense_enhanced`

---
*Documentation for Grace 3.1*
