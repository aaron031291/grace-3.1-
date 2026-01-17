# Watchdog Self-Healing System

## Overview

The Watchdog Self-Healing System is a **standalone monitoring process** that runs independently of the main GRACE runtime. It can detect crashes, diagnose issues, apply fixes, and automatically restart the system - even if the main process completely crashes.

## Key Features

✅ **Independent Operation**: Runs as a separate process, survives main runtime crashes  
✅ **Automatic Crash Detection**: Monitors process health every 30 seconds  
✅ **Intelligent Diagnosis**: Analyzes logs and error patterns to identify root causes  
✅ **Automatic Fixes**: Applies fixes for common issues (database, ports, dependencies, etc.)  
✅ **Auto-Restart**: Automatically restarts the system after fixing issues  
✅ **Persistent State**: Tracks restart count and fixes applied across sessions  

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│              Watchdog Process (Independent)              │
│                                                           │
│  1. Start Main GRACE Process                             │
│  2. Monitor Every 30 Seconds                             │
│  3. Detect Crashes/Failures                              │
│  4. Diagnose Root Cause                                  │
│  5. Apply Automatic Fixes                                │
│  6. Restart Main Process                                 │
│  7. Repeat                                               │
└─────────────────────────────────────────────────────────┘
```

## Usage

### Start with Watchdog

**Windows:**
```batch
start_watchdog.bat
```

**Linux/Mac:**
```bash
python start_watchdog.py
```

### Command Line Options

```bash
python -m backend.cognitive.watchdog_healing \
    --script launch_grace.py \
    --check-interval 30 \
    --max-restarts 10 \
    --restart-delay 5
```

**Parameters:**
- `--script`: Path to main launcher script (default: `launch_grace.py`)
- `--check-interval`: Seconds between health checks (default: 30)
- `--max-restarts`: Maximum restart attempts before giving up (default: 10)
- `--restart-delay`: Seconds to wait before restarting (default: 5)

## What It Can Fix

### 1. Database Connection Issues
- **Detection**: Database connection errors in logs
- **Fix**: Reset database connection
- **Severity**: High

### 2. Embedding Model Issues
- **Detection**: Missing model path or CUDA errors
- **Fix**: Skip embedding or download model
- **Severity**: Medium

### 3. Missing Dependencies
- **Detection**: Import errors in logs
- **Fix**: Install missing packages from requirements.txt
- **Severity**: High

### 4. Port Conflicts
- **Detection**: Port 8000 already in use
- **Fix**: Kill process using the port
- **Severity**: Medium

### 5. Memory Issues
- **Detection**: Out of memory errors
- **Fix**: Clear memory, garbage collection
- **Severity**: Critical

### 6. Permission Issues
- **Detection**: Permission denied errors
- **Fix**: Restart with proper permissions
- **Severity**: Medium

## Monitoring

### Watchdog Logs

Logs are stored in: `logs/watchdog/`

- `watchdog_state.json`: Current state (restart count, fixes applied)
- `main_process_stdout.log`: Main process stdout
- `main_process_stderr.log`: Main process stderr
- `fixes.jsonl`: History of all fixes applied

### Status Check

The watchdog logs its status regularly:
```
[WATCHDOG] Main process started (PID: 12345)
[WATCHDOG] System health: healthy
[WATCHDOG] Main process is not running!
[WATCHDOG] Diagnosing crash...
[WATCHDOG] Diagnosed 2 issue(s)
[WATCHDOG] Fixing: Database connection error (severity: high)
[WATCHDOG] ✓ Fixed: Database connection error
[WATCHDOG] Restarting main process (attempt 1/10)
```

## Safety Features

### Maximum Restarts
- Default: 10 restarts
- Prevents infinite restart loops
- Stops if max restarts reached

### Restart Delay
- Default: 5 seconds
- Gives system time to clean up
- Prevents rapid restart cycles

### State Persistence
- Tracks restart count across sessions
- Logs all fixes applied
- Can resume monitoring after watchdog restart

## Integration with Self-Healing

The watchdog works alongside the existing self-healing system:

1. **Self-Healing** (in-process): Fixes issues while system is running
2. **Watchdog** (out-of-process): Fixes issues when system crashes

Together, they provide:
- **Proactive healing**: Self-healing fixes issues before crashes
- **Reactive healing**: Watchdog fixes issues after crashes
- **Complete coverage**: System can recover from any failure

## Example Scenarios

### Scenario 1: Database Crash
```
1. Main process crashes due to database error
2. Watchdog detects crash
3. Diagnoses: Database connection issue
4. Fixes: Resets database connection
5. Restarts: Main process
6. System recovers
```

### Scenario 2: Port Conflict
```
1. Main process fails to start (port 8000 in use)
2. Watchdog detects failure
3. Diagnoses: Port conflict
4. Fixes: Kills process using port 8000
5. Restarts: Main process
6. System starts successfully
```

### Scenario 3: Missing Dependency
```
1. Main process crashes with import error
2. Watchdog detects crash
3. Diagnoses: Missing dependency
4. Fixes: Installs missing package
5. Restarts: Main process
6. System runs with new dependency
```

## Troubleshooting

### Watchdog Not Starting
- Check Python version (3.8+)
- Verify `psutil` is installed: `pip install psutil`
- Check script path is correct

### Watchdog Not Detecting Crashes
- Verify main process PID is correct
- Check watchdog logs in `logs/watchdog/`
- Increase check interval if needed

### Too Many Restarts
- Check logs for recurring issues
- Increase `max-restarts` if needed
- Investigate root cause manually

### Fixes Not Working
- Check `fixes.jsonl` for fix history
- Verify fix commands are correct for your OS
- Some fixes may require manual intervention

## Advanced Configuration

### Custom Fix Actions

You can extend the watchdog with custom fix actions:

```python
from backend.cognitive.watchdog_healing import WatchdogHealing, DiagnosedIssue

watchdog = WatchdogHealing(...)

# Add custom fix
def custom_fix():
    # Your fix logic here
    pass

watchdog._fix_issues = custom_fix
```

### Integration with Existing Self-Healing

The watchdog can trigger the in-process self-healing system:

```python
# In watchdog_healing.py
def _fix_issues(self, issues):
    # First try in-process healing
    try:
        from cognitive.autonomous_healing_system import get_autonomous_healing
        healing = get_autonomous_healing(...)
        healing.run_monitoring_cycle()
    except:
        pass
    
    # Then apply watchdog fixes
    # ...
```

## Best Practices

1. **Start with Watchdog**: Always use watchdog in production
2. **Monitor Logs**: Regularly check watchdog logs for patterns
3. **Set Appropriate Limits**: Adjust max-restarts based on your needs
4. **Combine with Self-Healing**: Use both systems for complete coverage
5. **Review Fixes**: Periodically review `fixes.jsonl` to understand issues

## Limitations

- **OS-Specific**: Some fixes (like port killing) are OS-specific
- **Limited Diagnosis**: Can only diagnose issues visible in logs
- **No Code Fixes**: Cannot fix code bugs automatically (use self-healing for that)
- **Requires Logs**: Needs access to log files for diagnosis

## Future Enhancements

- [ ] Machine learning-based diagnosis
- [ ] Integration with diagnostic machine
- [ ] Code-level fixes
- [ ] Remote monitoring
- [ ] Alert notifications
- [ ] Performance metrics

## See Also

- [Self-Healing System](SELF_HEALING_SYSTEM_COMPLETE.md)
- [Diagnostic Machine](backend/diagnostic_machine/README.md)
- [Autonomous Healing](backend/cognitive/autonomous_healing_system.py)
