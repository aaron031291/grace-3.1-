# Learning Hook

**File:** `cognitive/learning_hook.py`

## Overview

Universal Learning Hook

ONE function any subsystem calls to feed the learning tracker.
Eliminates duplicate boilerplate across 16+ systems.

Usage from any module:
    from cognitive.learning_hook import track_learning_event
    track_learning_event("my_system", "what happened", outcome="success", data={...})

Non-blocking, non-fatal. If tracker unavailable, silently drops.

## Classes

None

## Key Methods

- `track_learning_event()`

---
*Grace 3.1*
