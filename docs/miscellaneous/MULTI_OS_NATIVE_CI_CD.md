# GRACE Native CI/CD System

## Overview

GRACE has its own **native CI/CD and auto-actions system** that runs entirely within GRACE. No external services like GitHub Actions are required - everything is self-contained.

## Architecture

### Components

1. **Native Test Runner** (`backend/ci_cd/native_test_runner.py`)
   - Runs tests natively on current OS
   - Multi-OS compatibility checks
   - Generates test reports
   - No external dependencies

2. **Auto-Actions Manager** (`backend/ci_cd/auto_actions.py`)
   - Scheduled actions (cron-like)
   - Event-triggered actions
   - Manual triggers
   - All actions run natively

## Usage

### Running Tests

**Command:**
```bash
python -m backend.ci_cd.native_test_runner
```

**Output:**
```
======================================================================
GRACE NATIVE CI/CD - TEST RUNNER
======================================================================

Current OS: windows (Windows)
Python Version: 3.10.x

Running: OS Adapter...
  ✓ OS Adapter PASSED (0.05s)
Running: Path Operations...
  ✓ Path Operations PASSED (0.02s)
Running: Process Spawning...
  ✓ Process Spawning PASSED (0.10s)
Running: Startup Test...
  ✓ Startup Test PASSED (0.01s)
Running: Backend API...
  ⊘ Backend API SKIPPED (backend not running)
Running: Multi-OS Compatibility...
  ✓ Multi-OS Compatibility PASSED (0.30s)

======================================================================
TEST SUMMARY
======================================================================
Total Tests: 6
Passed: 5 ✓
Failed: 0 ✗
Skipped: 1 ⊘
Duration: 0.48s
======================================================================

Report saved to: logs/ci_cd_report.json
```

### Auto-Actions System

**Start Auto-Actions Manager:**
```bash
python -m backend.ci_cd.auto_actions start
```

**Check Status:**
```bash
python -m backend.ci_cd.auto_actions status
```

**Trigger Action Manually:**
```bash
python -m backend.ci_cd.auto_actions trigger --action-id daily_test
```

**List Actions:**
```bash
python -m backend.ci_cd.auto_actions list
```

## Default Auto-Actions

### 1. Daily Test Run
- **ID:** `daily_test`
- **Schedule:** 2 AM daily
- **Action:** Runs full test suite
- **Purpose:** Verify system health daily

### 2. Pre-Commit Tests
- **ID:** `pre_commit_test`
- **Trigger:** File changes in `backend/`
- **Action:** Runs test suite
- **Purpose:** Catch issues before commit

### 3. Weekly Cleanup
- **ID:** `weekly_cleanup`
- **Schedule:** 3 AM Sunday
- **Action:** Cleans up logs, temp files
- **Purpose:** Maintain system health

### 4. Health Check
- **ID:** `health_check`
- **Schedule:** Every 30 minutes
- **Action:** Checks backend health
- **Purpose:** Monitor system status

## Configuration

**Config File:** `backend/ci_cd/auto_actions_config.json`

**Example:**
```json
{
  "actions": [
    {
      "id": "daily_test",
      "name": "Daily Test Run",
      "action_type": "test",
      "trigger_type": "schedule",
      "command": "python -m backend.ci_cd.native_test_runner",
      "schedule": "0 2 * * *",
      "enabled": true,
      "last_run": "2026-01-16T02:00:00",
      "next_run": "2026-01-17T02:00:00"
    }
  ],
  "updated": "2026-01-16T10:00:00"
}
```

## Adding Custom Actions

**Programmatically:**
```python
from backend.ci_cd.auto_actions import AutoActionsManager, Action, ActionType, TriggerType

manager = AutoActionsManager()

custom_action = Action(
    id="my_custom_action",
    name="My Custom Action",
    action_type=ActionType.TEST,
    trigger_type=TriggerType.SCHEDULE,
    command="python my_script.py",
    schedule="0 */6 * * *",  # Every 6 hours
    enabled=True,
)

manager.register_action(custom_action)
manager.start()
```

**Via Config File:**
Edit `backend/ci_cd/auto_actions_config.json` and add your action.

## Test Reports

**Location:** `logs/ci_cd_report.json`

**Format:**
```json
{
  "timestamp": "2026-01-16T10:00:00",
  "os_info": {
    "family": "windows",
    "system": "Windows",
    "python_version": "3.10.x"
  },
  "summary": {
    "total": 6,
    "passed": 5,
    "failed": 0,
    "skipped": 1,
    "duration": 0.48
  },
  "results": [
    {
      "name": "OS Adapter",
      "status": "passed",
      "duration": 0.05,
      "output": "All OS adapter tests passed",
      "os_family": "windows"
    }
  ]
}
```

## Integration with GRACE

### Startup Integration

Add to `backend/app.py`:
```python
from backend.ci_cd.auto_actions import AutoActionsManager

# Start auto-actions on startup
auto_actions = AutoActionsManager()
auto_actions.start()
```

### API Endpoints

Add to `backend/api/ci_cd.py`:
```python
from fastapi import APIRouter
from backend.ci_cd.auto_actions import AutoActionsManager
from backend.ci_cd.native_test_runner import NativeTestRunner

router = APIRouter(prefix="/ci-cd", tags=["CI/CD"])

@router.post("/test/run")
async def run_tests():
    """Run tests."""
    runner = NativeTestRunner()
    report = runner.run_all_tests()
    return report

@router.get("/actions/status")
async def get_actions_status():
    """Get auto-actions status."""
    manager = AutoActionsManager()
    return manager.get_status()

@router.post("/actions/trigger/{action_id}")
async def trigger_action(action_id: str):
    """Trigger an action."""
    manager = AutoActionsManager()
    return manager.trigger_action(action_id)
```

## Multi-OS Testing

### Current OS Testing

Tests run on the current OS automatically:
- Windows → Windows tests
- Linux → Linux tests
- macOS → macOS tests

### Multi-OS Validation

The system checks for:
- OS checks outside `os_adapter.py`
- Platform-specific code
- Path operations that aren't portable
- Process spawning that isn't portable

### Cross-OS Testing

For full multi-OS testing:
1. Run tests on Windows
2. Run tests on Linux (VM or container)
3. Run tests on macOS (if available)

All reports can be combined for complete coverage.

## Benefits

### Self-Contained
- No external services required
- Works offline
- No API keys or credentials needed

### Native
- Runs in GRACE's environment
- Uses GRACE's dependencies
- Tests actual GRACE behavior

### Flexible
- Custom actions easy to add
- Schedule any task
- Trigger from events

### Transparent
- All actions logged
- Reports generated
- Status always visible

## Comparison: Native vs. GitHub Actions

| Feature | Native CI/CD | GitHub Actions |
|---------|--------------|----------------|
| **Setup** | Built-in, no config | Requires YAML files |
| **Dependencies** | Uses GRACE's env | Separate environment |
| **Offline** | ✅ Works offline | ❌ Requires internet |
| **Customization** | ✅ Full control | ⚠️ Limited by platform |
| **Multi-OS** | ✅ Native per OS | ✅ Can test all OSes |
| **Cost** | ✅ Free | ✅ Free (public repos) |
| **Privacy** | ✅ All local | ⚠️ Cloud-based |

## Quick Start

1. **Run tests:**
   ```bash
   python -m backend.ci_cd.native_test_runner
   ```

2. **Start auto-actions:**
   ```bash
   python -m backend.ci_cd.auto_actions start
   ```

3. **Check status:**
   ```bash
   python -m backend.ci_cd.auto_actions status
   ```

That's it! GRACE now has native CI/CD and auto-actions.

## Next Steps

1. Add custom actions for your workflow
2. Integrate with GRACE startup
3. Add API endpoints for web interface
4. Schedule regular tests
5. Monitor system health automatically

**GRACE is now self-testing and self-automating.**
