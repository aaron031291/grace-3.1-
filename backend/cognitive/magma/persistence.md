# Persistence

**File:** `cognitive/magma/persistence.py`

## Overview

Magma Memory Persistence Layer

Saves and loads relation graphs to/from disk so Grace
doesn't lose her memory on restart.

Saves:
- All 4 relation graphs (semantic, temporal, causal, entity)
- Node data and edge data
- Graph statistics

Format: JSON files in data/magma/

## Classes

- `MagmaPersistence`

## Key Methods

- `save()`
- `load()`
- `get_info()`

---
*Grace 3.1*
