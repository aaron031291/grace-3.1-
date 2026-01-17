# Stress Test System - Complete Guide

## 🎯 Overview

Two types of stress tests:

1. **Enterprise Stress Tests** (`enterprise_stress_tests.py`)
   - Polite, comprehensive testing
   - 15 tests from different perspectives
   - Designed to validate functionality

2. **Aggressive Stress Tests** (`aggressive_stress_tests.py`)
   - **NOT POLITE** - Designed to BREAK Grace
   - Massive volume, concurrent chaos, resource exhaustion
   - Long-duration endurance tests
   - Finds breaking points

---

## 🚀 Running Tests

### Enterprise Tests (Polite)

```bash
python backend/tests/run_stress_tests.py
```

### Aggressive Tests (Break Grace)

```bash
# Single run
python backend/tests/aggressive_stress_tests.py

# Continuous (every 30 minutes)
python backend/tests/continuous_stress_runner.py
```

---

## 📅 Auto-Start on Boot

### Windows

**Task Scheduler Method:**
1. Open Task Scheduler
2. Create Basic Task
3. Name: `Grace Stress Test Runner`
4. Trigger: **When computer starts**
5. Action: Start program
6. Program: `python.exe`
7. Arguments: `backend\tests\continuous_stress_runner.py`
8. Start in: Project root directory

**Startup Folder Method:**
1. Press `Win + R`
2. Type: `shell:startup`
3. Copy `start_stress_runner_startup.bat` there

### Linux

```bash
# Install as systemd service
sudo python3 backend/tests/install_stress_runner_service.py

# Or manually create service file
sudo nano /etc/systemd/system/grace-stress-runner.service
```

---

## 📊 Test Results

**Enterprise Tests:**
- `backend/logs/enterprise_stress_tests.json`

**Aggressive Tests:**
- `backend/logs/aggressive_stress_tests.json`
- `backend/logs/continuous_stress_runner.log`

---

## ⚙️ Configuration

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

### Concurrency
Edit `aggressive_stress_tests.py`:
```python
self.concurrent_workers = 50  # Parallel workers
```

---

## 🛑 Stopping Tests

**Windows:**
- Task Manager → End `python.exe`
- Or `Ctrl+C` in terminal

**Linux:**
```bash
sudo systemctl stop grace-stress-runner
```

---

## ⚠️ WARNING

Aggressive tests will:
- Use significant CPU/memory
- Generate large logs
- May slow system
- **Designed to BREAK things**

Only run where you want to find breaking points!

---

## ✅ Status

- ✅ Enterprise tests: 15 comprehensive tests
- ✅ Aggressive tests: 5 breaking-point tests
- ✅ Continuous runner: Every 30 minutes
- ✅ Boot startup: Windows & Linux
- ✅ Auto-upgrade: Diagnostic/healing systems

**Ready to stress test Grace!** 💥
