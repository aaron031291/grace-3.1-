# Sandbox Integration Guide for Self-Modeling

## Overview

This guide explains how to test Grace's self-modeling mechanism in a sandbox environment before deploying to production.

## Sandbox Setup

### 1. Create Isolated Environment

```bash
# Create a test directory
mkdir grace_sandbox
cd grace_sandbox

# Copy Grace codebase
cp -r ../grace_3/* .

# Create isolated virtual environment
python -m venv venv_sandbox
source venv_sandbox/bin/activate  # On Windows: venv_sandbox\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt
```

### 2. Initialize Test Database

```bash
# Use a separate test database
export DATABASE_PATH="backend/data/grace_test.db"  # On Windows: set DATABASE_PATH=backend/data/grace_test.db

# Run migration
python database/migrate_add_telemetry.py
```

### 3. Generate Test Data

```bash
# Run comprehensive test script
python test_telemetry.py
```

This will:
- Create sample operations
- Establish baselines
- Trigger drift (intentional slow operation)
- Capture system state

## Testing Scenarios

### Scenario 1: Normal Operations

Test baseline learning with consistent performance:

```python
from telemetry.decorators import track_operation
from models.telemetry_models import OperationType
import time

@track_operation(OperationType.INGESTION, "test_normal")
def normal_operation():
    time.sleep(0.1)  # Consistent 100ms
    return {"status": "success"}

# Run 20 times to establish baseline
for i in range(20):
    normal_operation()
```

Expected result:
- Baseline created after ~10 operations
- Mean ~100ms, low std dev
- Success rate: 100%
- No drift alerts

### Scenario 2: Performance Degradation

Test drift detection with gradual slowdown:

```python
@track_operation(OperationType.INGESTION, "test_degradation")
def degrading_operation(iteration):
    # Gradually slow down
    time.sleep(0.1 + (iteration * 0.01))
    return {"status": "success"}

# Run 30 times with increasing latency
for i in range(30):
    degrading_operation(i)
```

Expected result:
- Baseline established at ~100ms
- Later operations: ~300-400ms
- Drift alert created (latency, high severity)
- Deviation: ~200-300%

### Scenario 3: Intermittent Failures

Test failure detection and replay:

```python
import random

@track_operation(OperationType.RETRIEVAL, "test_failures", capture_inputs=True)
def flaky_operation(query: str):
    if random.random() < 0.3:  # 30% failure rate
        raise Exception("Simulated failure")
    return {"results": 5, "confidence": 0.8}

# Run 50 times
for i in range(50):
    try:
        flaky_operation(f"query_{i}")
    except:
        pass
```

Expected result:
- Success rate: ~70%
- Drift alerts for failures (if baseline >90%)
- Failed operations available for replay

### Scenario 4: Confidence Drift

Test confidence score tracking:

```python
@track_operation(OperationType.RETRIEVAL, "test_confidence")
def confidence_drift_operation(iteration):
    # Confidence degrades over time
    base_confidence = 0.9
    drift_factor = iteration * 0.01
    confidence = max(0.5, base_confidence - drift_factor)

    telemetry = get_telemetry_service()
    telemetry.record_confidence(
        run_id=run_id,  # Passed by decorator
        confidence_score=confidence
    )

    return {"confidence": confidence}

for i in range(30):
    confidence_drift_operation(i)
```

Expected result:
- Initial confidence: 0.9
- Final confidence: 0.6
- Drift alert (confidence, medium severity)
- Deviation: ~33%

### Scenario 5: Replay Testing

Test the replay mechanism:

```python
from telemetry.replay_service import get_replay_service

@track_operation(OperationType.INGESTION, "test_replay", capture_inputs=True)
def replayable_operation(filename: str, size_kb: int):
    # Simulate a bug that's been fixed
    if filename == "bug_doc.pdf":
        # Fixed in later version
        return {"status": "success", "chunks": 10}
    return {"status": "success", "chunks": 5}

# Create a failed operation
try:
    result = replayable_operation("bug_doc.pdf", 100)
    original_run_id = result["run_id"]
except:
    pass

# Later, replay it
replay_service = get_replay_service()
replay_result = replay_service.replay_operation(
    original_run_id=original_run_id,
    operation_func=replayable_operation,
    reason="verify_bug_fix"
)

print(f"Original: {replay_result.original_status}")
print(f"Replay: {replay_result.replay_status}")
print(f"Insights: {replay_result.insights}")
```

Expected result:
- Original status: "failed"
- Replay status: "completed"
- Insights: "✓ Issue appears to be resolved"
- Outputs match: False (different chunk counts)

## Sandbox API Testing

### Test All Endpoints

```bash
# Set base URL
export API_URL="http://localhost:8000"

# Test health
curl $API_URL/telemetry/health

# Test operations
curl $API_URL/telemetry/operations?limit=10

# Test baselines
curl $API_URL/telemetry/baselines

# Test drift alerts
curl $API_URL/telemetry/drift-alerts?resolved=false

# Test system state
curl $API_URL/telemetry/system-state/current

# Test stats
curl $API_URL/telemetry/stats?hours=24

# Acknowledge alert
curl -X POST $API_URL/telemetry/drift-alerts/1/acknowledge

# Resolve alert
curl -X POST $API_URL/telemetry/drift-alerts/1/resolve
```

### Load Testing

Generate high volume of operations:

```bash
python -c "
from test_telemetry import test_ingestion_operation, test_retrieval_operation
import time

print('Starting load test: 1000 operations')
start = time.time()

for i in range(500):
    test_ingestion_operation(f'doc_{i}.pdf', size_kb=100)
    test_retrieval_operation(f'query_{i}', limit=5)

    if i % 100 == 0:
        print(f'Progress: {i}/500')

duration = time.time() - start
print(f'Completed in {duration:.2f}s')
print(f'Throughput: {1000/duration:.2f} ops/sec')
"
```

Expected results:
- All operations tracked
- Baselines updated continuously
- No performance degradation
- Database size increase: ~500KB per 1000 operations

## Performance Benchmarks

### Decorator Overhead

Measure the cost of telemetry:

```python
import time

def without_telemetry():
    time.sleep(0.01)

@track_operation(OperationType.INGESTION, "benchmark")
def with_telemetry():
    time.sleep(0.01)

# Benchmark without telemetry
start = time.time()
for _ in range(1000):
    without_telemetry()
baseline = time.time() - start

# Benchmark with telemetry
start = time.time()
for _ in range(1000):
    with_telemetry()
telemetry_time = time.time() - start

overhead = ((telemetry_time - baseline) / baseline) * 100
print(f"Overhead: {overhead:.2f}%")
print(f"Per-operation: {(telemetry_time - baseline) / 1000 * 1000:.2f}ms")
```

Expected results:
- Overhead: <2%
- Per-operation: ~1-2ms

### Database Performance

Test query performance with large dataset:

```python
from database.session import get_session
from models.telemetry_models import OperationLog
import time

session = next(get_session())

# Test query speed with 10,000 operations
start = time.time()
recent = session.query(OperationLog).order_by(
    OperationLog.started_at.desc()
).limit(100).all()
query_time = time.time() - start

print(f"Query time (100 ops from 10k): {query_time*1000:.2f}ms")
```

Expected results:
- Query time: <10ms for 100 operations
- Indexed queries remain fast up to 100k operations

## Dashboard Testing

### Frontend Integration

1. Start backend in sandbox:
```bash
cd backend
python app.py
```

2. Start frontend:
```bash
cd frontend
npm start
```

3. Navigate to Telemetry tab

4. Verify:
   - System overview cards populate
   - Operations table shows recent data
   - Baselines table displays learned stats
   - Drift alerts appear (if any)
   - Auto-refresh works (30s intervals)

### Visual Tests

Check that:
- CPU/Memory progress bars update
- Status chips show correct colors (green=success, red=failure)
- Severity chips color-code properly (info, warning, error)
- Timestamps format correctly
- Numbers format with proper units (ms, %, MB)

## Stress Testing

### Memory Leak Test

Run telemetry for extended period:

```bash
# Run for 1 hour with operation every second
python -c "
import time
from test_telemetry import test_ingestion_operation

start = time.time()
count = 0

while time.time() - start < 3600:  # 1 hour
    test_ingestion_operation(f'doc_{count}.pdf', 100)
    count += 1
    time.sleep(1)

print(f'Completed {count} operations')
"
```

Monitor:
- Memory usage (should remain stable)
- Database size growth
- CPU usage (should be minimal)

Expected results:
- No memory leaks
- Linear database growth (~0.5KB per operation)
- CPU usage <5%

### Concurrent Operations

Test thread safety:

```python
import threading
from test_telemetry import test_ingestion_operation

def worker(thread_id):
    for i in range(100):
        test_ingestion_operation(f"thread_{thread_id}_doc_{i}.pdf", 100)

threads = []
for i in range(10):
    t = threading.Thread(target=worker, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("Concurrent test complete: 1000 operations from 10 threads")
```

Expected results:
- All operations tracked correctly
- No database conflicts
- Correct run_id uniqueness

## Validation Checklist

Before moving to production, verify:

- [ ] Migration runs successfully
- [ ] All 5 tables created
- [ ] Operations tracked automatically
- [ ] Baselines established (>10 operations)
- [ ] Drift alerts generated correctly
- [ ] System state captured every 5 minutes
- [ ] All 14 API endpoints responding
- [ ] Dashboard displays data correctly
- [ ] Auto-refresh works (30s)
- [ ] Alert acknowledge/resolve functions
- [ ] Performance overhead <2%
- [ ] No memory leaks in 1-hour test
- [ ] Concurrent operations safe
- [ ] Database queries fast (<10ms)
- [ ] Replay mechanism works

## Sandbox Cleanup

After testing:

```bash
# Remove test database
rm backend/data/grace_test.db

# Deactivate virtual environment
deactivate

# Remove sandbox directory
cd ..
rm -rf grace_sandbox
```

## Production Deployment

Once sandbox tests pass:

1. **Backup production database**
```bash
cp backend/data/grace.db backend/data/grace_backup_$(date +%Y%m%d).db
```

2. **Run migration on production**
```bash
cd backend
python database/migrate_add_telemetry.py
```

3. **Restart backend**
```bash
python app.py
```

4. **Monitor for 24 hours**
- Check drift alerts
- Review baselines
- Verify system state captures

5. **Integrate decorators gradually**
- Start with ingestion
- Add retrieval
- Add chat generation
- Add other operations

## Rollback Plan

If issues occur:

1. **Stop backend**
```bash
pkill -f "python app.py"
```

2. **Restore database**
```bash
cp backend/data/grace_backup_*.db backend/data/grace.db
```

3. **Remove telemetry router**
```python
# In app.py, comment out:
# app.include_router(telemetry_router)
```

4. **Restart backend**
```bash
python app.py
```

## Monitoring in Production

### Daily Checks

- Review drift alerts
- Check system state trends
- Monitor success rates
- Verify baseline updates

### Weekly Reviews

- Analyze performance trends
- Review resolved alerts
- Check for recurring issues
- Update baseline windows if needed

### Monthly Analysis

- Capacity planning from state history
- Identify optimization opportunities
- Review token usage trends
- Adjust drift thresholds if needed

## Conclusion

The sandbox environment lets you safely test all aspects of Grace's self-modeling mechanism before production deployment. Follow this guide to ensure smooth integration and reliable operation.

For questions or issues, refer to:
- `SELF_MODELING.md` - Complete documentation
- `IMPLEMENTATION_SUMMARY.md` - Technical details
- `QUICKSTART.md` - Quick reference
