# Websocket Manager

**File:** `api/websocket_manager.py`

## Overview

Central WebSocket Manager - Real-time Event Bridge

Provides a single persistent WebSocket connection for the frontend.
Bridges internal subsystem events to the frontend in real-time.

Events pushed to frontend:
- system.health: Periodic health updates
- diagnostic.scan: Diagnostic scan results  
- ingestion.complete: New document ingested
- learning.update: Learning progress
- message_bus.event: Any message bus event
- agent.status: Agent task updates

## Classes

- `ConnectionManager`

## Key Methods

- `disconnect()`
- `get_stats()`
- `get_ws_manager()`

---
*Grace 3.1*
