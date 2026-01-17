# Grace Self-Modeling - Quick Start Guide

## What Is This?

Grace can now see how she runs. Every time she processes a document, retrieves sources, or generates a response, she emits structured telemetry events. Over time, she learns baselines, detects drift, and can replay failures for debugging.

## Installation (3 steps)

### Step 1: Install Dependencies
```bash
cd backend
pip install psutil  # Only new dependency needed
```

### Step 2: Run Migration
```bash
cd backend
python database/migrate_add_telemetry.py
```

This creates 5 new tables:
- `operation_log` - Every tracked operation
- `performance_baseline` - Learned statistics
- `drift_alert` - Abnormal behavior detection
- `operation_replay` - Replay comparisons
- `system_state` - Health snapshots

### Step 3: Test It Works
```bash
cd backend
python test_telemetry.py
```

You should see:
- ✓ Database initialized
- ✓ Migration complete
- ✓ Operations tracked successfully
- ✓ System state captured
- ✓ Recent operations (5)
- ✓ Performance baselines (2)

## How to Use

### Access the Dashboard

1. Add the telemetry tab to your frontend navigation
2. Navigate to the Telemetry tab
3. View real-time metrics:
   - System overview (CPU, memory, documents, confidence)
   - Recent operations with timing and status
   - Performance baselines
   - Drift alerts (if any)

### Track Your Operations

Add a decorator to any function:

```python
from telemetry.decorators import track_operation
from models.telemetry_models import OperationType

@track_operation(OperationType.INGESTION, "ingest_pdf")
def ingest_pdf(filename: str, content: bytes):
    # Your code
    return result
```

That's it! The function is now tracked automatically.

### View Telemetry Data

Via API:
```bash
# Get recent operations
curl http://localhost:8000/telemetry/operations

# Get system state
curl http://localhost:8000/telemetry/system-state/current

# Get drift alerts
curl http://localhost:8000/telemetry/drift-alerts
```

Via Dashboard:
- Navigate to Telemetry tab in frontend
- Auto-refreshes every 30 seconds
- View operations, baselines, and alerts

## What Gets Tracked?

For every operation:
- ✓ Execution time (milliseconds)
- ✓ CPU usage (percentage)
- ✓ Memory usage (MB)
- ✓ Success/failure status
- ✓ Error messages (if failed)
- ✓ Input tokens and output tokens
- ✓ Confidence scores
- ✓ Contradiction detection

System-wide:
- ✓ Service health (Ollama, Qdrant, Database)
- ✓ Document and chunk counts
- ✓ Vector count
- ✓ Average confidence score
- ✓ CPU, memory, disk usage

## Drift Detection

Grace learns baselines over 7 days, then detects when things drift:

**Latency drift**: Operations taking 50%+ longer than usual
**Failure drift**: Failures when normally reliable (>90% success)
**Confidence drift**: 20%+ drop in confidence scores

Alerts appear in the dashboard with severity levels (low, medium, high, critical).

## Next Steps

1. **Start the backend**: `python app.py`
   - Telemetry monitor starts automatically (captures state every 5 minutes)

2. **Add telemetry to your operations**:
   - Ingestion: `@track_operation(OperationType.INGESTION, "ingest_text")`
   - Retrieval: `@track_operation(OperationType.RETRIEVAL, "retrieve_docs")`
   - Chat: `@track_operation(OperationType.CHAT_GENERATION, "generate")`

3. **Monitor the dashboard**:
   - Watch for drift alerts
   - Review baselines
   - Check system health

## Files to Review

- **`SELF_MODELING.md`** - Complete documentation (850+ lines)
- **`IMPLEMENTATION_SUMMARY.md`** - Technical details and architecture
- **`backend/test_telemetry.py`** - Working examples
- **`backend/api/telemetry.py`** - API endpoints
- **`frontend/src/components/TelemetryTab.jsx`** - Dashboard component

## API Endpoints (14 total)

All under `/telemetry/*`:

- `/operations` - List operations
- `/baselines` - View learned baselines
- `/drift-alerts` - View active alerts
- `/system-state/current` - Current health
- `/stats` - 24-hour statistics
- `/health` - Telemetry health check

Full API docs: `http://localhost:8000/docs`

## Support

If something doesn't work:

1. Check backend logs for `[TELEMETRY]` messages
2. Verify migration ran successfully
3. Ensure `psutil` is installed
4. Test with `test_telemetry.py`

## That's It!

Grace can now see herself run. She'll learn baselines, detect drift, and help you debug issues through replay. This is engineering, not consciousness—but it's what lets Grace improve over time.

Happy monitoring!
