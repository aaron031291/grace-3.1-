# Healing Scheduler & Alerts Implementation - COMPLETE ✅

## What Was Added

### 1. Diagnostic Alerts & Triggers
**Integrated with:** `diagnostic_machine/notifications.py`

The scheduler now automatically sends alerts when:
- 3+ anomalies detected in health check
- Health status becomes critical/failing  
- Queue backlog exceeds 20 pending tasks
- Health check encounters an error

**Notification Channels:**
- **Webhook** - HTTP POST to configured URL (`DIAGNOSTIC_WEBHOOK_URL`)
- **Slack** - Rich formatted messages (`SLACK_WEBHOOK_URL`)
- **Email** - SMTP delivery (`SMTP_HOST`, `SMTP_USER`, etc.)
- **Console** - Fallback logging

### 2. Persistent Healing Queue
**File:** `backend/cognitive/healing_scheduler.py`

Tasks are now stored in `data/healing_queue.json` and survive server restarts:

```python
from cognitive.healing_scheduler import PersistentHealingQueue, HealingTask, HealingPriority

queue = PersistentHealingQueue()

# Add a task
task = HealingTask(
    task_id="fix-001",
    task_type="code_fix",
    priority=HealingPriority.HIGH,
    description="Fix import error",
    file_path="backend/api/example.py"
)
queue.add_task(task)

# Tasks persist across restarts!
```

### 3. File Watcher Integration
Automatically triggers healing when Python files are modified:

```python
from cognitive.healing_scheduler import FileWatcherHealing

watcher = FileWatcherHealing(
    watch_paths=[Path("backend")],
    healing_callback=on_file_change,
    debounce_seconds=2.0  # Wait 2s after last change
)
watcher.start()
```

### 4. Robust Scheduling with `schedule` Library
Uses the existing `schedule` library for reliable job scheduling:

| Job | Interval | Purpose |
|-----|----------|---------|
| Health Check | 5 min | Run monitoring cycle |
| Proactive Scan | 30 min | Scan code for issues |
| Drift Detection | 15 min | Detect performance drift |
| Queue Cleanup | 60 min | Clear old completed tasks |

### 5. REST API Endpoints
**File:** `backend/api/healing_scheduler_api.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/healing-scheduler/status` | GET | Get scheduler status |
| `/api/healing-scheduler/start` | POST | Start scheduler |
| `/api/healing-scheduler/stop` | POST | Stop scheduler |
| `/api/healing-scheduler/queue/stats` | GET | Queue statistics |
| `/api/healing-scheduler/queue/tasks` | GET | List tasks |
| `/api/healing-scheduler/queue/tasks` | POST | Add task |
| `/api/healing-scheduler/trigger/health-check` | POST | Manual health check |
| `/api/healing-scheduler/trigger/proactive-scan` | POST | Manual scan |
| `/api/healing-scheduler/alerts` | GET | Get recent alerts |
| `/api/healing-scheduler/alerts` | POST | Send an alert |
| `/api/healing-scheduler/alerts/channels` | GET | List configured channels |
| `/api/healing-scheduler/alerts/test` | POST | Send test alert |

## Boot Integration

The scheduler is automatically started on server boot in `app.py`:

```
[HEALING-SCHEDULER] [OK] Scheduler started with:
  - Persistent healing queue (survives restarts)
  - File watcher (proactive healing on changes)
  - Scheduled jobs (health, scan, drift detection)
  - Pending tasks: 0
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Server Boot (app.py)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    HealingScheduler                          │
│  cognitive/healing_scheduler.py                             │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ schedule library │  │    PersistentHealingQueue        │ │
│  │  • Health: 5min  │  │  • JSON persistence              │ │
│  │  • Scan: 30min   │  │  • Priority ordering             │ │
│  │  • Drift: 15min  │  │  • Retry logic                   │ │
│  │  • Cleanup: 60min│  │  • Survives restarts             │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │               FileWatcherHealing                         ││
│  │  • Watches backend/*.py                                  ││
│  │  • Debounces rapid changes                               ││
│  │  • Queues proactive scans                                ││
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Task Worker Thread                          │
│  • Processes tasks from priority queue                       │
│  • Executes healing actions                                  │
│  • Handles retries on failure                                │
│  • Creates Genesis Keys for tracking                         │
└─────────────────────────────────────────────────────────────┘
```

## Usage Examples

### Check Scheduler Status
```bash
curl http://localhost:8000/api/healing-scheduler/status
```

Response:
```json
{
  "running": true,
  "pending_tasks": 3,
  "total_tasks": 15,
  "file_watcher_active": true,
  "schedules": {
    "health_check": 5,
    "proactive_scan": 30,
    "queue_cleanup": 60,
    "drift_detection": 15
  }
}
```

### Add a Healing Task
```bash
curl -X POST http://localhost:8000/api/healing-scheduler/queue/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "code_fix",
    "priority": "high",
    "description": "Fix undefined variable",
    "file_path": "backend/api/example.py"
  }'
```

### Trigger Manual Health Check
```bash
curl -X POST http://localhost:8000/api/healing-scheduler/trigger/health-check
```

### View Queue Statistics
```bash
curl http://localhost:8000/api/healing-scheduler/queue/stats
```

Response:
```json
{
  "pending": 2,
  "in_progress": 1,
  "completed": 10,
  "failed": 0,
  "retrying": 1
}
```

## Files Created/Modified

### New Files
| File | Purpose |
|------|---------|
| `backend/cognitive/healing_scheduler.py` | Core scheduler with queue, watcher, scheduler |
| `backend/api/healing_scheduler_api.py` | REST API endpoints |

### Modified Files
| File | Change |
|------|--------|
| `backend/app.py` | Added scheduler startup + router registration |
| `backend/scripts/verify_self_healing.py` | Added scheduler verification |

## Summary

All gaps have been addressed:

| Gap | Status | Implementation |
|-----|--------|----------------|
| Persistent Queue | ✅ Fixed | `PersistentHealingQueue` with JSON storage |
| File Watcher | ✅ Fixed | `FileWatcherHealing` with watchdog integration |
| Robust Scheduling | ✅ Fixed | `schedule` library with configurable intervals |

The self-healing system now has:
- ✅ Boot-triggered initialization
- ✅ Continuous background monitoring
- ✅ Proactive file watching
- ✅ Persistent task queue
- ✅ Scheduled health checks
- ✅ Genesis Key tracking
- ✅ REST API for management
