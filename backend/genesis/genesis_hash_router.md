# Genesis# Router

**File:** `genesis/genesis_hash_router.py`

## Purpose

Parses Genesis#component from user prompts and routes to system

## Overview

Genesis# Router

When a user types "Genesis#<component>" in a prompt, this router:
1. Parses the Genesis# reference
2. Looks up the component in the registry
3. Analyzes it via Oracle/LLM (Kimi analyzes the logic)
4. Wires it into all connected systems
5. Returns full acceptance + version control confirmation
6. Triggers handshake protocol for the component

This is the user-facing entry point for the Genesis# system.

## Classes

- `GenesisHashRouter`

## Key Methods

- `detect_genesis_refs()`
- `has_genesis_ref()`
- `route()`
- `get_genesis_hash_router()`

## Database Tables

None (no DB tables)

## Dataclasses

None

## Connects To

- `cognitive.timesense_governance`
- `genesis.component_registry`
- `genesis.unified_intelligence`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
