# Stress Test Scheduler - Boot Integration Complete ✅

**Date:** 2026-01-16  
**Status:** ✅ **INTEGRATED INTO STARTUP**

---

## Summary

The autonomous stress testing scheduler is now integrated into Grace's startup sequence and will **automatically start on boot**.

---

## Integration Details

### ✅ **Automatic Startup on Boot**

The stress test scheduler is now part of Grace's startup lifecycle:

**Location:** `backend/app.py` → `lifespan()` function

**Integration Point:** After all other systems initialize, before server is ready

### ✅ **Startup Sequence**

1. Database initialization
2. Self-healing system startup
3. Embedding model pre-loading
4. TimeSense engine initialization
5. **→ Stress Test Scheduler starts here ←**
6. File watcher starts
7. ML Intelligence initialization
8. Auto-ingestion starts
9. Continuous learning starts
10. Server ready to accept connections

### ✅ **Shutdown Handling**

The scheduler is properly stopped during Grace shutdown:
- Clean shutdown on app termination
- Thread joins with timeout
- Graceful cleanup

---

## Configuration

### **Default Settings**

```python
start_stress_test_scheduler(
    interval_minutes=10,              # Run every 10 minutes
    base_url="http://localhost:8000", # API base URL
    enable_genesis_logging=True,      # Log to Genesis Keys
    enable_diagnostic_alerts=True     # Alert diagnostic engine
)
```

### **Environment Variables** (Optional)

- `STRESS_TEST_INTERVAL_MINUTES` - Override default 10 minutes
- `STRESS_TEST_BASE_URL` - Override API base URL
- `STRESS_TEST_ENABLE_GENESIS` - Enable/disable Genesis logging (default: true)
- `STRESS_TEST_ENABLE_DIAGNOSTIC` - Enable/disable diagnostic alerts (default: true)

---

## Startup Behavior

### **On Boot:**

```
[STARTUP] Starting autonomous stress test scheduler...
[STARTUP] [OK] Stress test scheduler started - running every 10 minutes
```

### **After 10 Minutes:**

```
[STRESS-SCHEDULER] Running stress test suite #1
[STRESS-SCHEDULER] Test #1 complete. Next test in 10 minutes
```

### **If Issues Found:**

```
[STRESS-SCHEDULER] Alerting diagnostic engine: 2 issues found, pass rate: 86.7%
[STRESS-SCHEDULER] Critical issues detected - triggering proactive scan
[STRESS-SCHEDULER] Proactive scan fixed 3/5 issues
```

---

## Verification

### **Check Scheduler Status**

```python
from backend.autonomous_stress_testing.scheduler import get_stress_test_scheduler

scheduler = get_stress_test_scheduler()
status = scheduler.get_status()

print(f"Running: {status['running']}")
print(f"Tests run: {status['test_count']}")
print(f"Last test: {status['last_test_time']}")
```

### **View Genesis Keys**

Query for stress test keys:

```python
from genesis.genesis_key_service import get_genesis_service

session = next(get_session())
genesis_service = get_genesis_service(session=session)

# Query stress test keys
keys = genesis_service.query_keys(
    tags=["stress_test"],
    limit=10
)

for key in keys:
    print(f"Run #{key.context_data.get('test_run_number')}: "
          f"{key.context_data.get('passed')}/{key.context_data.get('total_tests')} "
          f"({key.context_data.get('pass_rate'):.1f}%)")
```

### **View Diagnostic Alerts**

```bash
# List alert files
ls logs/diagnostic/stress_test_alert_*.json

# View latest alert
cat $(ls -t logs/diagnostic/stress_test_alert_*.json | head -1) | jq .
```

---

## Manual Control

### **Start Manually** (if needed)

```python
from backend.autonomous_stress_testing.scheduler import start_stress_test_scheduler

scheduler = start_stress_test_scheduler()
```

### **Stop Manually** (if needed)

```python
from backend.autonomous_stress_testing.scheduler import stop_stress_test_scheduler

stop_stress_test_scheduler()
```

### **Check Status**

```bash
# Via API (if server is running)
curl http://localhost:8000/stress-test/status

# Or programmatically
python -c "from backend.autonomous_stress_testing.scheduler import get_stress_test_scheduler; import json; print(json.dumps(get_stress_test_scheduler().get_status(), indent=2))"
```

---

## Testing the Integration

### **Verify Startup Integration**

1. Start Grace:
   ```bash
   python backend/app.py
   ```

2. Look for startup message:
   ```
   [STARTUP] Starting autonomous stress test scheduler...
   [STARTUP] [OK] Stress test scheduler started - running every 10 minutes
   ```

3. Wait 10 minutes and check logs:
   ```
   [STRESS-SCHEDULER] Running stress test suite #1
   ```

### **Verify Genesis Key Logging**

1. Wait for first test run (10 minutes)
2. Query Genesis Keys:
   ```python
   from backend.autonomous_stress_testing.scheduler import get_stress_test_scheduler
   # Check scheduler ran
   status = get_stress_test_scheduler().get_status()
   print(f"Tests run: {status['test_count']}")
   ```

3. Check Genesis Keys database or files

### **Verify Diagnostic Alerts**

1. Create a test failure scenario
2. Wait for test run
3. Check alert file:
   ```bash
   ls logs/diagnostic/stress_test_alert_*.json
   ```

---

## Files Modified

### **`backend/app.py`**
- Added stress test scheduler startup in `lifespan()` function
- Added scheduler shutdown on app termination

### **New Files Created**
- `backend/autonomous_stress_testing/stress_test_suite.py` - 15 stress tests
- `backend/autonomous_stress_testing/scheduler.py` - Background scheduler
- `start_stress_test_scheduler.py` - Standalone entry point

---

## Benefits

### ✅ **Automatic Monitoring**

- Runs every 10 minutes automatically
- No manual intervention required
- Continuous system validation

### ✅ **Complete Audit Trail**

- Every test run logged with Genesis Keys
- Searchable by tags: `stress_test`, `automated`
- Full history available

### ✅ **Proactive Healing**

- Issues detected automatically
- Diagnostic engine alerted immediately
- Automatic fixes when possible

### ✅ **Production Ready**

- Integrated into startup sequence
- Graceful shutdown handling
- Background thread (non-blocking)

---

## Next Steps

The stress test scheduler is now fully integrated and will:

1. ✅ **Start automatically** when Grace boots
2. ✅ **Run every 10 minutes** in the background
3. ✅ **Log with Genesis Keys** for complete audit trail
4. ✅ **Alert diagnostic engine** when issues found
5. ✅ **Trigger automatic fixes** for critical issues

**Grace is now self-monitoring and self-healing from boot!** 🎉

---

## Status

✅ **FULLY INTEGRATED AND OPERATIONAL**

The stress test scheduler will automatically start when Grace boots and run continuously every 10 minutes.
