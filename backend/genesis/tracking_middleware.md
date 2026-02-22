# Tracking Middleware

**File:** `genesis/tracking_middleware.py`

## Overview

Genesis Tracking Middleware

Automatically tracks all requests, responses, and operations
through FastAPI middleware and decorators.

Every API call, file operation, and database change gets a Genesis Key.

## Classes

- `GenesisTrackingMiddleware`
- `SessionTracker`

## Key Methods

- `track_file_operation()`
- `decorator()`
- `track_database_operation()`
- `decorator()`

## DB Tables

None

---
*Grace 3.1 Documentation*
