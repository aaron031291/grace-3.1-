# Aggressive Stress Test Runner - Setup Guide

## 💥 What This Does

Runs **aggressive, long-duration stress tests** every 30 minutes to **BREAK Grace** and find all breaking points.

**Not polite** - These tests are designed to push systems to their limits:
- 1000+ concurrent operations
- Memory bombs
- Resource exhaustion
- Rapid fire requests
- 60-minute endurance tests

---

## 🚀 Quick Start

### Option 1: Run Manually (Test First)

```bash
# Windows
python backend\tests\continuous_stress_runner.py

# Linux/Mac
python3 backend/tests/continuous_stress_runner.py
```

### Option 2: Run on Boot (Windows)

#### Method A: Task Scheduler (Recommended)

1. Open **Task Scheduler** (search "Task Scheduler" in Start menu)
2. Click **Create Basic Task**
3. Name: `Grace Stress Test Runner`
4. Trigger: **When the computer starts**
5. Action: **Start a program**
6. Program: `C:\Python314\python.exe` (or your Python path)
7. Arguments: `"C:\Users\aaron\grace 3.1\grace-3.1-\backend\tests\continuous_stress_runner.py"`
8. Start in: `C:\Users\aaron\grace 3.1\grace-3.1-`
9. Check **"Run whether user is logged on or not"**
10. Click **Finish**

#### Method B: Startup Folder

1. Press `Win + R`
2. Type: `shell:startup`
3. Create shortcut to: `backend\tests\start_stress_runner.bat`

### Option 3: Run on Boot (Linux)

#### systemd Service

```bash
# Install service
sudo python3 backend/tests/install_stress_runner_service.py

# Or manually:
sudo nano /etc/systemd/system/grace-stress-runner.service
# Copy service content from install script

sudo systemctl daemon-reload
sudo systemctl enable grace-stress-runner
sudo systemctl start grace-stress-runner
```

#### Check Status

```bash
sudo systemctl status grace-stress-runner
sudo journalctl -u grace-stress-runner -f
```

---

## 📊 What Gets Tested

### 1. Memory Bomb
- **1000 operations** in parallel
- Tests memory system under massive load
- **Goal**: Find memory leaks and crashes

### 2. Concurrent Chaos
- **2000 concurrent operations** with random delays
- Tests thread safety and race conditions
- **Goal**: Find deadlocks and data corruption

### 3. Resource Exhaustion
- Creates **10,000 objects** (1KB each)
- Monitors memory and CPU usage
- **Goal**: Find resource leaks

### 4. Rapid Fire Requests
- **5000 requests** with no delay
- Tests system responsiveness
- **Goal**: Find timeouts and bottlenecks

### 5. Long Duration Stress
- Runs for **60 minutes** continuously
- Tests system stability over time
- **Goal**: Find gradual degradation

---

## 📝 Logs

All results logged to:
- `backend/logs/aggressive_stress_tests.json` - Test results
- `backend/logs/continuous_stress_runner.log` - Runner logs
- `backend/logs/stress_runner_service.log` - Service logs (if installed)

---

## ⚙️ Configuration

Edit `backend/tests/continuous_stress_runner.py`:

```python
runner = ContinuousStressRunner(
    interval_minutes=30,      # Run every 30 minutes
    test_duration_minutes=60  # Each test runs for 60 minutes
)
```

Edit `backend/tests/aggressive_stress_tests.py`:

```python
self.concurrent_workers = 50  # Number of parallel workers
self.test_duration_minutes = 60  # Long duration test length
```

---

## 🛑 Stop the Runner

### Windows
- Task Manager → End `python.exe` process
- Or: `Ctrl+C` if running in terminal

### Linux
```bash
sudo systemctl stop grace-stress-runner
```

---

## 📈 Monitoring

Check logs to see:
- How many tests passed/failed
- What breaking points were found
- System performance under stress
- Resource usage patterns

---

## ⚠️ WARNING

These tests are **AGGRESSIVE** and will:
- Use significant CPU and memory
- Generate large log files
- May slow down your system
- Are designed to **BREAK** things

**Only run on systems where you want to find breaking points!**

---

## ✅ Status

- ✅ Aggressive stress tests created
- ✅ Continuous runner created
- ✅ Boot startup scripts created
- ✅ Service installer created
- ✅ Documentation complete

**Ready to BREAK Grace!** 💥
