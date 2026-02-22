# Loop Output

**File:** `core/loop_output.py`

## Overview

Grace Loop Output - Standardized Loop Output Format

Addresses Clarity Class 3 (Loop Identity Ambiguity):
- Standard output format for all cognitive loops
- Reasoning chain tracking
- Metadata for audit and learning

All cognitive loops should return GraceLoopOutput.

## Classes

- `LoopType`
- `LoopStatus`
- `ReasoningStep`
- `LoopMetadata`
- `GraceLoopOutput`

## Key Methods

- `to_dict()`
- `to_dict()`
- `add_reasoning_step()`
- `get_reasoning_trace()`
- `start()`
- `complete()`
- `fail()`
- `interrupt()`
- `success()`
- `failed()`
- `step_count()`
- `average_step_confidence()`
- `to_dict()`
- `from_dict()`

---
*Grace 3.1*
