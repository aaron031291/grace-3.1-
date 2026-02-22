# Timesense Api

**File:** `api/timesense_api.py`

## Overview

TimeSense API - Grace's Understanding of Time, Scale, and Capacity

Endpoints:
- /api/timesense/dashboard - Full dashboard (timing + capacity + rates)
- /api/timesense/understand/{size_bytes} - What does this data size mean?
- /api/timesense/estimate/{operation}/{size_bytes} - How long will this take?
- /api/timesense/capacity - Grace's memory and storage self-awareness
- /api/timesense/can-handle/{size_bytes} - Can Grace handle this data?
- /api/timesense/rates - Processing rates per operation (MB/s)
- /api/timesense/context - Current temporal context
- /api/timesense/predict/{operation} - Predict operation duration
- /api/timesense/cost/{operation} - Estimate operation cost
- /api/timesense/anomalies - Temporal anomalies
- /api/timesense/ooda - OODA cycle timing

## Classes

None

## Key Methods

None

---
*Grace 3.1*
