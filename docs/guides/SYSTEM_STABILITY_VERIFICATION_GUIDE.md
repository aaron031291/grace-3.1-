# System Stability Verification Guide

## How to Know if Grace 3.1 is Definitively Stable

This guide provides comprehensive methods to verify that your Grace system is stable and operational.

---

## Quick Health Check (30 seconds)

### 1. Check Main System Status
```bash
curl http://localhost:8000/grace/status
```

**Expected Response:**
```json
{
  "status": "operational",
  "systems": {
    "layer1": {...},
    "genesis_keys": {...},
    "learning_orchestrator": {...}
  }
}
```

### 2. Check Overall Health
```bash
curl http://localhost:8000/grace/health
```

**Expected Response:**
```json
{
  "overall": "healthy",
  "components": {
    "layer1": true,
    "trigger_pipeline": true,
    "learning_orchestrator": true,
    "memory_learner": true
  }
}
```

### 3. Check API Health
```bash
curl http://localhost:8000/health
```

---

## Comprehensive Verification (5 minutes)

### Automated Verification Script

Run the complete system verification:

**Windows:**
```batch
python backend/scripts/verify_grace_complete.py
```

**Linux/Mac:**
```bash
python backend/scripts/verify_grace_complete.py
```

**What it checks:**
- ✅ All imports work correctly
- ✅ Neuro-symbolic components instantiate
- ✅ Layer 1 components create successfully
- ✅ API structure is correct
- ✅ Key files exist
- ✅ KPI tracking functionality
- ✅ Package exports work

**Success Criteria:** All tests should pass with 100% success rate.

---

## Component-by-Component Health Checks

### 1. Database Health
```bash
curl http://localhost:8000/health
```

### 2. Vector Database (Qdrant)
```bash
# Check if Qdrant is running
curl http://localhost:6333/collections

# Should return list of collections including "documents"
```

### 3. LLM Service (Ollama)
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Should return list of available models
```

### 4. Librarian System
```bash
curl http://localhost:8000/librarian/health
```

**Expected:**
```json
{
  "overall_status": "healthy",
  "components": {
    "tag_manager": "operational",
    "rule_categorizer": "operational",
    "relationship_manager": "operational"
  }
}
```

### 5. ML Intelligence
```bash
curl http://localhost:8000/ml-intelligence/status
```

### 6. Telemetry System
```bash
curl http://localhost:8000/telemetry/health
```

### 7. Ingestion System
```bash
curl http://localhost:8000/ingest/status
```

### 8. File Management
```bash
curl http://localhost:8000/file-ingestion/status
```

---

## Integration Tests

### Run Full Integration Test Suite
```bash
# From project root
python tests/test_complete_integration_now.py
```

**Expected:** 9/9 tests passed

### Run E2E Tests
```bash
cd backend
pytest tests/ -v --cov=. --cov-report=html
```

**Success Criteria:**
- All tests pass
- Coverage > 80%
- No critical errors

---

## Stability Indicators

### ✅ System is Stable When:

1. **All Health Checks Pass**
   - `/grace/health` returns `"overall": "healthy"`
   - All components show `true` or `"operational"`

2. **No Error Logs**
   - Check backend logs for exceptions
   - No repeated errors in last 24 hours

3. **Database Integrity**
   - All tables exist
   - No migration errors
   - Data consistency maintained

4. **Service Connectivity**
   - Qdrant responds on port 6333
   - Ollama responds on port 11434 (if used)
   - Database connection stable

5. **API Endpoints Respond**
   - All 48+ API routers accessible
   - No 500 errors on critical endpoints
   - Response times < 2 seconds

6. **Background Processes Running**
   - Auto-ingestion monitor active
   - File watcher operational
   - Telemetry collecting data

7. **Memory & Performance**
   - No memory leaks (stable memory usage)
   - CPU usage reasonable (< 50% idle)
   - No resource exhaustion

---

## Continuous Monitoring

### Check System Status Regularly
```bash
# Create a monitoring script
watch -n 30 'curl -s http://localhost:8000/grace/status | jq .'
```

### Monitor Telemetry
```bash
# View system metrics
curl http://localhost:8000/telemetry/operations/recent?limit=10
```

### Check Genesis Keys (Audit Trail)
```bash
curl http://localhost:8000/genesis-keys/recent?limit=50
```

---

## Stability Checklist

Use this checklist to verify definitive stability:

### Core Systems
- [ ] Database connection stable
- [ ] Qdrant vector database accessible
- [ ] Embedding model loads successfully
- [ ] All API endpoints respond

### Layer 1 (Deterministic Foundation)
- [ ] Layer 1 initialized
- [ ] Message bus operational
- [ ] Genesis Keys tracking active
- [ ] Trust scoring working

### Layer 2 (Intelligent Processing)
- [ ] LLM orchestrator functional
- [ ] Retrieval system working
- [ ] Ingestion pipeline operational
- [ ] ML Intelligence active

### Integration
- [ ] Layer 1 ↔ Layer 2 integration working
- [ ] Neuro-symbolic bridge functional
- [ ] Trust-aware processing active
- [ ] Learning memory updating

### Background Processes
- [ ] Auto-ingestion monitor running
- [ ] File watcher active
- [ ] Telemetry collecting
- [ ] Self-healing operational (if enabled)

### Tests
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] No flaky tests

### Performance
- [ ] Response times acceptable
- [ ] No memory leaks
- [ ] CPU usage normal
- [ ] Database queries optimized

---

## Red Flags (System NOT Stable)

### ⚠️ Warning Signs:

1. **Health Checks Fail**
   - `/grace/health` returns `"unhealthy"`
   - Components show `false` or `"error"`

2. **Repeated Errors**
   - Same error appearing multiple times
   - Error rate > 5% of requests

3. **Service Unavailable**
   - Qdrant not responding
   - Database connection failures
   - Ollama timeout errors

4. **Performance Degradation**
   - Response times > 5 seconds
   - Memory usage continuously increasing
   - CPU at 100% for extended periods

5. **Data Integrity Issues**
   - Missing data in database
   - Vector search returning no results
   - Inconsistent state between services

6. **Test Failures**
   - Integration tests failing
   - Critical path tests broken
   - Regression in previously passing tests

---

## Automated Stability Verification Script

Create a script to run all checks automatically:

```python
#!/usr/bin/env python3
"""
Automated Stability Verification
Run this script to verify Grace is definitively stable.
"""

import requests
import sys
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:8000"

def check_endpoint(name: str, endpoint: str) -> Tuple[bool, str]:
    """Check if an endpoint responds correctly."""
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
        if response.status_code == 200:
            return True, "OK"
        else:
            return False, f"Status {response.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    """Run all stability checks."""
    checks = [
        ("Main Health", "/grace/health"),
        ("System Status", "/grace/status"),
        ("Librarian Health", "/librarian/health"),
        ("ML Intelligence", "/ml-intelligence/status"),
        ("Telemetry", "/telemetry/health"),
        ("Ingestion", "/ingest/status"),
        ("File Management", "/file-ingestion/status"),
    ]
    
    print("=" * 70)
    print("GRACE SYSTEM STABILITY VERIFICATION")
    print("=" * 70)
    print()
    
    all_passed = True
    for name, endpoint in checks:
        passed, message = check_endpoint(name, endpoint)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name:30} {message}")
        if not passed:
            all_passed = False
    
    print()
    print("=" * 70)
    if all_passed:
        print("✅ SYSTEM IS STABLE - All checks passed!")
    else:
        print("❌ SYSTEM UNSTABLE - Some checks failed!")
    print("=" * 70)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
```

**Usage:**
```bash
python verify_stability.py
```

---

## Production Readiness Criteria

### System is Production-Ready When:

1. ✅ **All automated tests pass** (100% success rate)
2. ✅ **Health checks return healthy** for 24+ hours
3. ✅ **No critical errors** in logs for 7+ days
4. ✅ **Performance metrics** within acceptable ranges
5. ✅ **Data integrity** verified (no corruption)
6. ✅ **Backup/restore** procedures tested
7. ✅ **Monitoring/alerting** configured
8. ✅ **Documentation** complete and up-to-date

---

## Quick Reference

### Most Important Checks:
```bash
# 1. Overall system health
curl http://localhost:8000/grace/health

# 2. Complete system status
curl http://localhost:8000/grace/status

# 3. Run verification script
python backend/scripts/verify_grace_complete.py

# 4. Run integration tests
python tests/test_complete_integration_now.py
```

### If Any Check Fails:
1. Check logs: `backend/logs/` or console output
2. Verify services: Qdrant, Ollama, Database
3. Review recent changes
4. Check system resources (memory, CPU, disk)
5. Review error messages for specific issues

---

## Summary

**System is definitively stable when:**
- ✅ All health endpoints return healthy
- ✅ All verification scripts pass
- ✅ All integration tests pass
- ✅ No errors in logs
- ✅ All services connected
- ✅ Performance metrics normal
- ✅ Background processes running

**Run these checks regularly to ensure ongoing stability!**
