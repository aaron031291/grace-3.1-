# Realtime

**File:** `diagnostic_machine/realtime.py`

## Overview

Real-time WebSocket Updates for Diagnostic Machine

Provides live streaming of:
- Diagnostic cycle results
- Health status changes
- Alert notifications
- Healing action progress
- System metrics

Supports multiple concurrent clients with room-based subscriptions.

## Classes

- `EventType`
- `RealtimeEvent`
- `ClientInfo`
- `ConnectionManager`
- `DiagnosticEventEmitter`

## Key Methods

- `to_json()`
- `client_count()`
- `on_event()`
- `get_client_info()`
- `get_all_clients()`
- `get_event_history()`
- `get_connection_manager()`
- `get_event_emitter()`

---
*Grace 3.1*
