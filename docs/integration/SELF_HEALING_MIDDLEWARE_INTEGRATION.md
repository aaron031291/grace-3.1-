# Self-Healing Middleware Integration

## Overview

This document describes the new self-healing middleware system that automatically captures all API errors and feeds them into Grace's learning and self-healing pipelines.

## What Was Added

### 1. Self-Healing Middleware (`backend/middleware/self_healing_middleware.py`)

A comprehensive middleware system that:

- **Automatically captures all API errors** - No need to manually add error handling to each endpoint
- **Pattern recognition** - Tracks recurring errors and escalates severity automatically
- **Severity classification** - Classifies errors based on type (critical, high, medium, low)
- **Feeds to learning pipeline** - All errors are recorded with Genesis Keys and fed to Learning Memory
- **Triggers healing** - High/critical errors trigger the self-healing system

### 2. Components Added

| Component | Purpose |
|-----------|---------|
| `SelfHealingMiddleware` | FastAPI middleware that catches all errors |
| `ErrorPatternTracker` | Tracks recurring error patterns for escalation |
| `self_healing_endpoint` decorator | Enhanced context for specific endpoints |
| `cache_error_handler` decorator | For cache operations |
| `database_error_handler` decorator | For database operations |
| `test_runner_error_handler` decorator | For test execution |

### 3. Integration Points

The middleware is now integrated into:

1. **app.py** - Global middleware catches all API errors
2. **redis_cache.py** - Cache connection and operation errors
3. **autonomous_test_runner.py** - Test execution errors and timeouts

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                     API Request                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              SelfHealingMiddleware                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 1. Capture any exception                                    ││
│  │ 2. Classify severity (low/medium/high/critical)             ││
│  │ 3. Track error pattern for recurring issues                 ││
│  │ 4. Escalate if pattern threshold reached (3+ in 60 mins)    ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              ErrorLearningIntegration                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 1. Create Genesis Key for error                             ││
│  │ 2. Feed to Learning Memory                                  ││
│  │ 3. Trigger healing cycle (if high/critical)                 ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Self-Healing System                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 1. Analyze error patterns                                   ││
│  │ 2. Decide healing actions                                   ││
│  │ 3. Execute fixes (with trust level)                         ││
│  │ 4. Learn from outcomes                                      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Severity Classification

| Error Type | Default Severity | Escalated After 3+ |
|------------|-----------------|-------------------|
| DatabaseError, ConnectionError, MemoryError | critical | critical |
| TimeoutError, AuthenticationError, PermissionError | high | critical |
| ValueError, TypeError, KeyError, HTTPException | medium | high |
| ValidationError, FileNotFoundError | low | medium |

## API Endpoints

### GET /api/error-patterns

Returns current error pattern statistics:

```json
{
  "status": "ok",
  "patterns": {
    "api.chat:ValueError": {
      "count": 2,
      "first_seen": "2026-01-17T10:00:00",
      "last_seen": "2026-01-17T10:05:00",
      "escalated": false
    }
  },
  "total_patterns": 1,
  "escalated_count": 0
}
```

## Usage Examples

### Using the Decorator for Enhanced Context

```python
from middleware.self_healing_middleware import self_healing_endpoint

@router.get("/items/{item_id}")
@self_healing_endpoint(component="inventory", severity_override="high")
async def get_item(item_id: int):
    # Any errors here will be recorded with enhanced context
    ...
```

### Manual Error Recording

```python
from cognitive.error_learning_integration import get_error_learning_integration

error_learning = get_error_learning_integration(session=session)
error_learning.record_error(
    error=exception,
    context={
        "location": "my_component",
        "reason": "Custom operation failed",
        "method": "my_method"
    },
    component="my_component",
    severity="medium"
)
```

## Components Still Needing Manual Integration

The following components would benefit from adding the decorators:

- [ ] `database/session.py` - Add `@database_error_handler` to session operations
- [ ] `api/file_management.py` - Add `@self_healing_endpoint` to file operations
- [ ] `api/ingest.py` - Add `@self_healing_endpoint` to ingestion endpoints
- [ ] `api/librarian_api.py` - Add `@self_healing_endpoint` to tag operations

## Benefits

1. **Complete Error Visibility** - All API errors are captured automatically
2. **Pattern Detection** - Recurring issues are identified and escalated
3. **Automatic Learning** - Errors feed into Learning Memory for future prevention
4. **Proactive Healing** - High-severity errors trigger automatic healing
5. **Zero Manual Work** - Middleware handles everything transparently
6. **Historical Tracking** - Genesis Keys provide full error lineage

## Monitoring

Access the error patterns dashboard at:
- **API**: `GET /api/error-patterns`
- **Health**: Integrated with `/health/live` and `/health/ready`
