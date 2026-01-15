# Grace Self-Modeling Mechanism

## Overview

Grace's self-modeling mechanism enables her to observe, measure, and understand her own execution. This is not consciousness—it's engineering. Through structured telemetry and replay capabilities, Grace can detect performance drift, learn baselines, and debug failures systematically.

## Philosophy

> "Genesis gives identity, provenance, and honesty—it's the spine. But introspection is what lets Grace say, 'this part of me is slow,' 'this gate is brittle,' or 'this parser should be offloaded.' That's not consciousness. It's engineering."

The self-modeling system turns silent degradation into visible problems by:
1. **Tracking every operation** - ingestion, retrieval, chat generation, embeddings
2. **Learning baselines** - knowing what "normal" looks like
3. **Detecting drift** - spotting when things get slower or less reliable
4. **Enabling replay** - debugging failures by rerunning with the same inputs

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│                    Operation Tracking                     │
│  Every operation emits events: what, when, how long,     │
│  how much CPU/memory, confidence scores, failures        │
└────────────────┬────────────────────────────────────────┘
                 │
                 ├──► OperationLog (run_id, timing, resources)
                 │
┌────────────────┴────────────────────────────────────────┐
│                  Baseline Learning                        │
│  Rolling window statistics: mean, median, P95, P99,     │
│  success rate, resource usage patterns                   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ├──► PerformanceBaseline (operation-specific)
                 │
┌────────────────┴────────────────────────────────────────┐
│                   Drift Detection                         │
│  Compare operations against baselines, create alerts     │
│  when latency, failure rate, or confidence drift         │
└────────────────┬────────────────────────────────────────┘
                 │
                 ├──► DriftAlert (severity, deviation %)
                 │
┌────────────────┴────────────────────────────────────────┐
│                  Replay Mechanism                         │
│  Store inputs, rerun failed operations, compare results  │
└────────────────┬────────────────────────────────────────┘
                 │
                 └──► OperationReplay (comparison, insights)
```

### Database Schema

#### OperationLog
Tracks every operation Grace performs:
```python
{
    "run_id": "uuid",
    "operation_type": "ingestion|retrieval|chat_generation|...",
    "operation_name": "ingest_pdf|retrieve_hybrid|...",
    "started_at": "timestamp",
    "completed_at": "timestamp",
    "duration_ms": 123.45,
    "status": "completed|failed|timeout",
    "error_message": "...",
    "cpu_percent": 45.2,
    "memory_mb": 256.0,
    "input_tokens": 100,
    "output_tokens": 200,
    "confidence_score": 0.85,
    "input_hash": "sha256",  # For replay
    "metadata": {...}  # Operation-specific data
}
```

#### PerformanceBaseline
Learned performance characteristics:
```python
{
    "operation_type": "ingestion",
    "operation_name": "ingest_pdf",
    "sample_count": 1234,
    "mean_duration_ms": 450.0,
    "median_duration_ms": 420.0,
    "p95_duration_ms": 850.0,
    "p99_duration_ms": 1200.0,
    "success_rate": 0.98,
    "mean_confidence_score": 0.82,
    "baseline_window_days": 7
}
```

#### DriftAlert
Abnormal behavior detection:
```python
{
    "run_id": "uuid",
    "drift_type": "latency|failure_rate|confidence",
    "baseline_value": 450.0,
    "observed_value": 950.0,
    "deviation_percent": 111.1,
    "severity": "low|medium|high|critical",
    "acknowledged": false,
    "resolved": false
}
```

#### SystemState
Periodic health snapshots:
```python
{
    "ollama_running": true,
    "qdrant_connected": true,
    "document_count": 156,
    "chunk_count": 3420,
    "average_confidence_score": 0.81,
    "cpu_percent": 23.4,
    "memory_percent": 45.6,
    "operations_last_24h": 1234
}
```

## Usage

### 1. Tracking Operations (Decorator Pattern)

The simplest way to add telemetry is using decorators:

```python
from telemetry.decorators import track_operation
from models.telemetry_models import OperationType

@track_operation(
    OperationType.INGESTION,
    "ingest_pdf",
    capture_inputs=True,
    capture_outputs=False
)
def ingest_pdf(filename: str, content: bytes):
    # Your ingestion logic
    chunks = process_pdf(content)
    return {"chunks": len(chunks), "status": "success"}

# The decorator automatically:
# - Measures execution time
# - Tracks CPU and memory usage
# - Records inputs for replay
# - Updates baselines
# - Detects drift
# - Handles errors gracefully
```

### 2. Tracking Operations (Context Manager)

For more control, use the context manager:

```python
from telemetry.telemetry_service import get_telemetry_service
from models.telemetry_models import OperationType

telemetry = get_telemetry_service()

with telemetry.track_operation(
    operation_type=OperationType.RETRIEVAL,
    operation_name="retrieve_hybrid",
    input_data={"query": query, "limit": 5},
    metadata={"collection": "documents"}
) as run_id:
    # Perform retrieval
    results = vector_db.search(query, limit=5)

    # Optionally record additional metrics
    telemetry.record_confidence(
        run_id=run_id,
        confidence_score=0.85,
        contradiction_detected=False
    )

    return results
```

### 3. Recording Tokens and Confidence

```python
from telemetry.decorators import track_operation, track_tokens, track_confidence
from models.telemetry_models import OperationType

@track_operation(OperationType.CHAT_GENERATION, "generate_response")
@track_tokens
@track_confidence
def generate_response(prompt: str, run_id: str = None):
    response = llm.generate(prompt)

    return {
        "response": response["text"],
        "input_tokens": response["prompt_tokens"],
        "output_tokens": response["completion_tokens"],
        "confidence_score": 0.92,
        "contradiction_detected": False
    }
```

### 4. Capturing System State

System state is captured automatically every 5 minutes by a background thread. You can also trigger manual captures:

```python
from telemetry.telemetry_service import get_telemetry_service

telemetry = get_telemetry_service()
state = telemetry.capture_system_state()

print(f"Documents: {state.document_count}")
print(f"Chunks: {state.chunk_count}")
print(f"CPU: {state.cpu_percent}%")
print(f"Average confidence: {state.average_confidence_score}")
```

### 5. Replaying Failed Operations

When an operation fails, you can replay it to debug:

```python
from telemetry.replay_service import get_replay_service

replay_service = get_replay_service()

# Get recent failures that can be replayed
failures = replay_service.get_replayable_failures(
    limit=10,
    operation_type="ingestion"
)

# Replay a specific failure
if failures:
    failure = failures[0]
    replay_result = replay_service.replay_operation(
        original_run_id=failure.run_id,
        operation_func=ingest_pdf,
        reason="debug_timeout_issue"
    )

    print(f"Original status: {replay_result.original_status}")
    print(f"Replay status: {replay_result.replay_status}")
    print(f"Outputs match: {replay_result.outputs_match}")
    print(f"Insights: {replay_result.insights}")
```

## API Endpoints

Grace exposes REST endpoints for accessing telemetry data:

### Operation Logs
```bash
# Get recent operations
GET /telemetry/operations?limit=50&operation_type=ingestion

# Get specific operation
GET /telemetry/operations/{run_id}
```

### Performance Baselines
```bash
# Get all baselines
GET /telemetry/baselines

# Filter by operation type
GET /telemetry/baselines?operation_type=retrieval
```

### Drift Alerts
```bash
# Get unresolved alerts
GET /telemetry/drift-alerts?resolved=false

# Get critical alerts
GET /telemetry/drift-alerts?severity=critical

# Acknowledge an alert
POST /telemetry/drift-alerts/{alert_id}/acknowledge

# Resolve an alert
POST /telemetry/drift-alerts/{alert_id}/resolve
```

### System State
```bash
# Get current state
GET /telemetry/system-state/current

# Get state history (last 24 hours)
GET /telemetry/system-state/history?hours=24

# Manually trigger state capture
POST /telemetry/system-state/capture
```

### Statistics
```bash
# Get aggregated stats for last 24 hours
GET /telemetry/stats?hours=24

# Filter by operation type
GET /telemetry/stats?hours=24&operation_type=chat_generation
```

### Health Check
```bash
# Check telemetry system health
GET /telemetry/health
```

## Drift Detection Rules

Grace automatically detects drift based on:

### Latency Drift
- **Medium**: 50% slower or faster than baseline
- **High**: 100% slower or faster than baseline

### Failure Rate Drift
- **High**: Operation failed when baseline shows >90% success rate

### Confidence Drift
- **Medium**: 20% drop in confidence score

### Example Alert
```json
{
  "drift_type": "latency",
  "operation_name": "ingest_pdf",
  "baseline_value": 450.0,
  "observed_value": 950.0,
  "deviation_percent": 111.1,
  "severity": "high",
  "created_at": "2026-01-11T10:30:00Z"
}
```

## Baseline Learning

Baselines are computed using a rolling 7-day window:

```python
# Statistics calculated:
- mean_duration_ms: Average execution time
- median_duration_ms: Median execution time
- p95_duration_ms: 95th percentile (most operations under this)
- p99_duration_ms: 99th percentile (almost all operations under this)
- std_dev_duration_ms: Standard deviation
- success_rate: Percentage of successful operations
- mean_cpu_percent: Average CPU usage
- mean_memory_mb: Average memory usage
- mean_confidence_score: Average confidence
- contradiction_rate: Percentage with contradictions
```

Baselines are updated after each operation, providing continuous learning.

## Replay Mechanism

Replay enables debugging by rerunning operations with identical inputs:

```python
# Stored for replay:
{
    "inputs": {"filename": "doc.pdf", "size_kb": 100},
    "input_hash": "sha256(...)",
    "outputs": {...},
    "output_hash": "sha256(...)"
}

# Replay comparison:
{
    "original_duration_ms": 450.0,
    "replay_duration_ms": 420.0,
    "original_status": "failed",
    "replay_status": "completed",
    "outputs_match": false,
    "differences": {
        "duration_diff_percent": -6.7,
        "status_changed": {
            "original": "failed",
            "replay": "completed"
        }
    },
    "insights": "✓ Issue appears to be resolved - replay succeeded where original failed."
}
```

## Integration Examples

### Example 1: Tracking Ingestion

```python
from telemetry.decorators import track_operation
from models.telemetry_models import OperationType

class TextIngestionService:
    @track_operation(
        OperationType.INGESTION,
        "ingest_text",
        capture_inputs=True
    )
    def ingest_text(self, filename: str, content: str, run_id: str = None):
        # Track the operation
        chunks = self.chunker.chunk_text(content)
        embeddings = self.embedding_model.embed_texts([c["text"] for c in chunks])
        self.qdrant_client.upsert_vectors(embeddings)

        # Record confidence if available
        if run_id:
            telemetry = get_telemetry_service()
            telemetry.record_confidence(
                run_id=run_id,
                confidence_score=self.confidence_scorer.calculate_score(chunks),
                contradiction_detected=False
            )

        return {"chunks": len(chunks)}
```

### Example 2: Tracking Retrieval

```python
from telemetry.decorators import track_operation, track_confidence
from models.telemetry_models import OperationType

class DocumentRetriever:
    @track_operation(
        OperationType.RETRIEVAL,
        "retrieve_hybrid",
        capture_inputs=True
    )
    @track_confidence
    def retrieve(self, query: str, limit: int = 5, run_id: str = None):
        results = self.vector_db.search(query, limit=limit)

        # Calculate aggregate confidence
        avg_confidence = sum(r["score"] for r in results) / len(results)

        return {
            "results": results,
            "confidence_score": avg_confidence,
            "contradiction_detected": self.detect_contradictions(results)
        }
```

### Example 3: Monitoring Dashboard

```python
from fastapi import FastAPI, Depends
from telemetry.telemetry_service import get_telemetry_service

app = FastAPI()

@app.get("/monitoring/dashboard")
async def get_dashboard():
    telemetry = get_telemetry_service()
    state = telemetry.capture_system_state()

    # Get recent operations
    from database.session import get_session
    from models.telemetry_models import OperationLog, DriftAlert

    session = next(get_session())

    recent_ops = session.query(OperationLog).order_by(
        OperationLog.started_at.desc()
    ).limit(10).all()

    unresolved_alerts = session.query(DriftAlert).filter(
        DriftAlert.resolved == False
    ).count()

    return {
        "system_state": {
            "documents": state.document_count,
            "chunks": state.chunk_count,
            "cpu": state.cpu_percent,
            "memory": state.memory_percent
        },
        "recent_operations": [
            {
                "name": op.operation_name,
                "duration_ms": op.duration_ms,
                "status": op.status.value
            }
            for op in recent_ops
        ],
        "alerts": {
            "unresolved": unresolved_alerts
        }
    }
```

## Setup and Installation

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
# Includes: SQLAlchemy, psutil, FastAPI, etc.
```

### 2. Run Migration

```bash
cd backend
python database/migrate_add_telemetry.py
```

This creates 5 new tables:
- `operation_log`
- `performance_baseline`
- `drift_alert`
- `operation_replay`
- `system_state`

### 3. Test the System

```bash
cd backend
python test_telemetry.py
```

This will:
- Run the migration
- Execute sample operations
- Capture system state
- Display telemetry data
- Show available API endpoints

### 4. Start the API

```bash
cd backend
python app.py
```

The telemetry endpoints are now available at `http://localhost:8000/telemetry/*`

## Benefits

1. **Visibility**: Silent failures become visible through drift alerts
2. **Debugging**: Replay mechanism makes failures reproducible
3. **Performance**: Baseline tracking reveals regressions immediately
4. **Quality**: Confidence and contradiction tracking surfaces data quality issues
5. **Capacity Planning**: System state snapshots show growth trends
6. **Self-Improvement**: Grace can identify slow components and suggest optimizations

## Best Practices

1. **Always track critical operations**: Ingestion, retrieval, generation
2. **Capture inputs for replay**: Set `capture_inputs=True` for debugging
3. **Monitor drift alerts**: Check `/telemetry/drift-alerts` regularly
4. **Set up baseline windows**: Default 7 days works for most cases
5. **Review system state trends**: Weekly review of state history
6. **Acknowledge and resolve alerts**: Keep alert queue clean
7. **Use replay for root cause analysis**: Don't just log failures—understand them

## Future Enhancements

- **Automatic remediation**: Retry failed operations with adjusted parameters
- **Predictive alerting**: ML-based prediction of impending failures
- **Distributed tracing**: Track operations across multiple Grace instances
- **Custom metrics**: User-defined performance indicators
- **A/B testing**: Compare different ingestion/retrieval strategies
- **Cost tracking**: Monitor API costs, token usage, compute time
- **Anomaly detection**: Unsupervised learning for unusual patterns

## Conclusion

Grace's self-modeling mechanism transforms her from a black box into a transparent, self-aware system. It's not magic—it's measurement. It's not consciousness—it's engineering. But it's what lets Grace improve herself over time, detect problems before they become critical, and maintain high reliability as she scales.

> "With this mirror in place, Grace can safely ingest research from APIs (papers, benchmarks, datasets), monitor quality and performance, and improve herself over time. Without it, anything built on top is fragile. With it, Grace becomes a system that can self-correct and scale without going blind."
