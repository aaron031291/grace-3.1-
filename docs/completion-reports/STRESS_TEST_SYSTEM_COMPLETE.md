# Aggressive Stress Test System - COMPLETE 💥

## ✅ Status: READY TO BREAK GRACE

An **aggressive, long-duration stress test system** has been created that runs every 30 minutes on boot to find all breaking points.

---

## 🎯 What Was Created

### 1. Aggressive Stress Tests (`aggressive_stress_tests.py`)

**5 Aggressive Tests Designed to BREAK Grace:**

1. **Memory Bomb** 💣
   - 1000 operations in parallel
   - Tests memory system under massive load
   - Goal: Find memory leaks and crashes

2. **Concurrent Chaos** 🌪️
   - 2000 concurrent operations with random delays
   - Tests thread safety and race conditions
   - Goal: Find deadlocks and data corruption

3. **Resource Exhaustion** 🔥
   - Creates 10,000 objects (1KB each)
   - Monitors memory and CPU usage
   - Goal: Find resource leaks

4. **Rapid Fire Requests** ⚡
   - 5000 requests with no delay
   - Tests system responsiveness
   - Goal: Find timeouts and bottlenecks

5. **Long Duration Stress** ⏰
   - Runs for 60 minutes continuously
   - Tests system stability over time
   - Goal: Find gradual degradation

**Features:**
- **NOT POLITE** - Designed to push systems to breaking point
- 50 concurrent workers by default
- 60-minute endurance tests
- Comprehensive error logging
- Automatic issue detection

---

### 2. Continuous Stress Runner (`continuous_stress_runner.py`)

**Runs Every 30 Minutes:**
- Starts immediately on boot
- Runs aggressive tests every 30 minutes
- Each test cycle runs for 60 minutes
- Logs all results
- Graceful shutdown handling

**Features:**
- Signal handling (SIGINT, SIGTERM)
- Automatic retry on errors
- Progress logging
- Cycle counting

---

### 3. Boot Startup Scripts

**Windows:**
- `start_stress_runner.bat` - Manual start
- `start_stress_runner_startup.bat` - For startup folder
- Task Scheduler instructions

**Linux:**
- `start_stress_runner.sh` - Manual start
- systemd service installer
- Service management commands

---

### 4. Service Installer (`install_stress_runner_service.py`)

**Auto-Installation:**
- Windows: Uses NSSM (Non-Sucking Service Manager)
- Linux: Creates systemd service
- Automatic configuration
- Log file setup

---

## 🚀 How to Use

### Quick Start (Test First)

```bash
# Run once to test
python backend/tests/aggressive_stress_tests.py

# Run continuous (every 30 minutes)
python backend/tests/continuous_stress_runner.py
```

### Install on Boot (Windows)

**Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task
3. Name: `Grace Stress Test Runner`
4. Trigger: **When computer starts**
5. Action: Start program
6. Program: `python.exe`
7. Arguments: `backend\tests\continuous_stress_runner.py`
8. Start in: Project root
9. Check "Run whether user is logged on or not"

**Startup Folder:**
1. Press `Win + R`
2. Type: `shell:startup`
3. Copy `start_stress_runner_startup.bat` there

### Install on Boot (Linux)

```bash
# Install service
sudo python3 backend/tests/install_stress_runner_service.py

# Check status
sudo systemctl status grace-stress-runner

# View logs
sudo journalctl -u grace-stress-runner -f
```

---

## 📊 Test Configuration

### Test Interval
Edit `continuous_stress_runner.py`:
```python
interval_minutes=30  # Run every 30 minutes
```

### Test Duration
Edit `aggressive_stress_tests.py`:
```python
test_duration_minutes=60  # Each test runs for 60 minutes
```

### Concurrency Level
Edit `aggressive_stress_tests.py`:
```python
self.concurrent_workers = 50  # Parallel workers
```

---

## 📝 Logs

**Test Results:**
- `backend/logs/aggressive_stress_tests.json` - All test results
- `backend/logs/continuous_stress_runner.log` - Runner logs
- `backend/logs/stress_runner_service.log` - Service logs (if installed)

**Log Format:**
```json
{
  "test_name": "Memory Bomb",
  "perspective": "Massive Volume Attack",
  "passed": false,
  "duration_ms": 12345.6,
  "metrics": {
    "operations_completed": 850,
    "operations_failed": 150,
    "success_rate": 0.85
  },
  "errors": [...],
  "warnings": [...],
  "timestamp": "2024-01-01T12:00:00",
  "aggressive": true
}
```

---

## 🛑 Stopping Tests

**Windows:**
- Task Manager → End `python.exe` process
- Or `Ctrl+C` in terminal

**Linux:**
```bash
sudo systemctl stop grace-stress-runner
```

---

## ⚠️ WARNING

These tests are **AGGRESSIVE** and will:
- ✅ Use significant CPU and memory
- ✅ Generate large log files
- ✅ May slow down your system
- ✅ **Designed to BREAK things**

**Only run on systems where you want to find breaking points!**

---

## 📈 What Gets Tested

### Volume Tests
- 1000+ operations in parallel
- 2000+ concurrent operations
- 5000+ rapid requests

### Duration Tests
- 60-minute continuous stress
- Long-running operations
- Stability over time

### Resource Tests
- Memory exhaustion
- CPU stress
- Storage pressure

### Concurrency Tests
- Thread safety
- Race conditions
- Deadlock detection

---

## ✅ Status

- ✅ **Aggressive tests created**: 5 breaking-point tests
- ✅ **Continuous runner created**: Every 30 minutes
- ✅ **Boot startup scripts**: Windows & Linux
- ✅ **Service installer**: Auto-installation
- ✅ **Documentation**: Complete setup guide

---

## 🎯 Next Steps

1. **Test First**: Run manually to verify it works
2. **Install on Boot**: Set up Task Scheduler or systemd
3. **Monitor Logs**: Check `backend/logs/` for results
4. **Review Breaking Points**: Analyze failures to improve Grace

---

**Status**: ✅ **AGGRESSIVE STRESS TEST SYSTEM COMPLETE**

**Ready to BREAK Grace every 30 minutes!** 💥

See `AGGRESSIVE_STRESS_TEST_SETUP.md` for detailed setup instructions.
