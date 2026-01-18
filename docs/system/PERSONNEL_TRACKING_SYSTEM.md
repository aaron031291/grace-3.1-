# GRACE Personnel Tracking System

## Overview

The Personnel Tracking System uses **Genesis Keys** to track personnel login/logout and all input/output throughout the day. It features **intelligent version control** designed for storage efficiency.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PERSONNEL TRACKING ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      API / MIDDLEWARE LAYER                         │ │
│  │  PersonnelTrackingMiddleware → Auto-capture API activities         │ │
│  │  SessionTrackingMiddleware → Auto-manage sessions                  │ │
│  │  Personnel API → Manual tracking endpoints                          │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    PERSONNEL TRACKER                                │ │
│  │  • Login/logout tracking with Genesis IDs                          │ │
│  │  • Session management                                               │ │
│  │  • Activity recording                                               │ │
│  │  • Genesis Key integration                                          │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                 SMART VERSION CONTROL                               │ │
│  │                                                                      │ │
│  │  REALTIME TIER          HOURLY TIER          DAILY TIER            │ │
│  │  ┌──────────────┐       ┌──────────────┐     ┌──────────────┐      │ │
│  │  │ Full Records │  →    │ Aggregated   │  →  │ Compressed   │      │ │
│  │  │ In Memory    │       │ Per Hour     │     │ Daily Rollup │      │ │
│  │  │ Max 1000/user│       │ Summaries    │     │ + Archive    │      │ │
│  │  └──────────────┘       └──────────────┘     └──────────────┘      │ │
│  │                                                                      │ │
│  │  DELTA COMPRESSION      DEDUPLICATION       STORAGE TIERING        │ │
│  │  • Only store diffs     • Skip duplicates   • Archive after 30d    │ │
│  │  • 60-80% savings       • 5-min window      • Compressed .gz       │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Features

### 1. Login/Logout Tracking

Every login and logout is recorded with:
- Genesis ID (user identifier)
- Timestamp
- IP address
- User agent
- Device fingerprint
- Geographic location (if available)
- Session duration (on logout)

### 2. Input/Output Tracking

Throughout the day, tracks:
- **Inputs**: User requests, commands, queries
- **Outputs**: System responses, generated content
- **Endpoints**: Which APIs were accessed
- **Duration**: How long each operation took
- **Sizes**: Input/output data sizes

### 3. Intelligent Storage

**Storage-saving features:**

| Feature | Savings | Description |
|---------|---------|-------------|
| Delta Compression | 60-80% | Only stores differences between records |
| Deduplication | 10-30% | Skips duplicate inputs within 5 minutes |
| Hourly Rollups | 70% | Aggregates detailed records to summaries |
| Daily Rollups | 90% | Further compresses to daily summaries |
| Archiving | 95% | Gzip compression for old data |
| Truncated Summaries | 80% | Stores 200-char summaries, not full content |

### 4. Tiered Storage

```
REALTIME (In Memory)
├── Full activity records
├── Max 1000 per user
├── Real-time queries
│
↓ (Automatic rollup when limit hit)
│
HOURLY (In Memory)
├── Aggregated per hour
├── Activity counts by type
├── Endpoint usage
│
↓ (On logout or daily)
│
DAILY (In Memory + Disk)
├── Full day summary
├── Hourly distribution
├── Peak usage times
├── Top endpoints
│
↓ (After 30 days)
│
ARCHIVED (Compressed Disk)
├── Gzip compressed JSON
├── Long-term retention
└── On-demand retrieval
```

---

## API Endpoints

### Session Management

```http
# Login
POST /personnel/login
{
  "genesis_id": "GU-abc123",
  "device_fingerprint": "fp-xyz"
}
Response: { "session_id": "SS-xxx", "login_time": "..." }

# Logout
POST /personnel/logout/{session_id}
{
  "reason": "user_initiated"
}

# Get session info
GET /personnel/session/{session_id}

# List active sessions
GET /personnel/sessions/active
```

### Activity Tracking

```http
# Record activity
POST /personnel/activity/{session_id}
{
  "activity_type": "input",
  "input_data": "user query...",
  "output_data": "system response...",
  "endpoint": "POST /chat",
  "duration_ms": 150
}

# Get user summary
GET /personnel/user/{genesis_id}/summary?date=2026-01-18

# Get user session history
GET /personnel/user/{genesis_id}/sessions
```

### Administration

```http
# Storage statistics
GET /personnel/stats

# Cleanup inactive sessions
POST /personnel/cleanup?inactive_minutes=30

# Archive old data
POST /personnel/archive?older_than_days=30

# List activity types
GET /personnel/activity-types
```

---

## Activity Types

| Type | Description |
|------|-------------|
| `input` | User input/message |
| `output` | System output/response |
| `command` | User command executed |
| `query` | Database/search query |
| `file_access` | File read/write |
| `code_change` | Code modification |
| `api_call` | External API call |
| `approval` | Approval action |
| `decision` | Decision made |
| `error` | Error occurred |

---

## Integration

### Enable Automatic Tracking

Add to your FastAPI app:

```python
from genesis.personnel_middleware import setup_personnel_tracking

app = FastAPI()
setup_personnel_tracking(app)
```

This enables:
- Automatic session creation on first request with Genesis ID
- Automatic activity tracking for all API requests
- Session timeout handling

### Manual Tracking

```python
from genesis.personnel_tracker import get_personnel_tracker, ActivityType

tracker = get_personnel_tracker()

# Login
session_id = tracker.record_login(
    genesis_id="GU-abc123",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
)

# Record activity
tracker.record_activity(
    session_id=session_id,
    activity_type=ActivityType.INPUT,
    input_data="User's question...",
    output_data="System's answer...",
    endpoint="/chat",
    duration_ms=250,
)

# Logout
tracker.record_logout(session_id)
```

---

## Genesis Key Integration

All session events create Genesis Keys automatically:

| Event | Genesis Key Type |
|-------|-----------------|
| Login | `USER_INPUT` |
| Logout | `SYSTEM_EVENT` |
| Activity | Via audit middleware |

This provides:
- Complete audit trail
- Immutable record of all personnel activity
- Integration with existing Genesis Key analytics

---

## Storage Estimates

Assuming 100 active users, 8-hour workdays:

| Metric | Estimate |
|--------|----------|
| Activities per user per day | ~500 |
| Raw data per activity | ~500 bytes |
| With compression | ~50 bytes |
| **Daily storage per user** | ~25 KB |
| **Monthly storage per user** | ~750 KB |
| **Annual storage per user** | ~9 MB |
| **100 users annual** | ~900 MB |

Without intelligent storage: **~45 GB/year** (50x more)

---

## Data Retention

Default policies:

| Tier | Retention | Storage |
|------|-----------|---------|
| Realtime | While session active | Memory |
| Hourly | 7 days | Memory |
| Daily | 30 days | Memory + Disk |
| Archive | 7 years | Compressed disk |

---

## Reports Available

### Daily Summary
- Login/logout times
- Total session duration
- Activity counts by type
- Hourly activity distribution
- Peak usage hour
- Top accessed endpoints
- Error count

### User Activity Report
- Current session status
- Today's activities
- Historical trends

### System Stats
- Active sessions
- Total tracked users
- Storage utilization
- Compression efficiency

---

## Security Considerations

1. **Input/Output Truncation**: Full content is hashed but not stored (only 200-char summaries)
2. **Hash Verification**: Content hashes allow verification without storing full data
3. **Audit Trail**: All tracking activities are themselves audited via Genesis Keys
4. **Access Control**: Integrate with RBAC for personnel data access
5. **Encryption**: Archive files can be encrypted at rest

---

## Files Created

| File | Purpose |
|------|---------|
| `backend/genesis/personnel_tracker.py` | Core tracking logic |
| `backend/genesis/personnel_middleware.py` | Auto-tracking middleware |
| `backend/api/personnel_api.py` | REST API endpoints |

---

*Last Updated: January 2026*
