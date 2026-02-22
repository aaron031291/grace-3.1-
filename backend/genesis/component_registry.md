# Genesis Component Registry

**File:** `genesis/component_registry.py`

## Purpose

Every module self-registers with Genesis hash for liveness tracking

## Overview

Genesis# Component Registry

Every component in Grace self-registers here with:
- What it is (name, type, module path)
- What it does (capabilities, dependencies)
- Its Genesis hash (content hash for version tracking)
- Its health status (alive/degraded/dead)
- Last heartbeat timestamp

When a user sends "Genesis#" in a prompt, the system:
1. Parses the component reference
2. Looks it up in this registry
3. Routes to Oracle/Kimi for logic analysis
4. Wires it into all connected systems (memory, healing, version control)
5. Confirms acceptance with a handshake

This table is THE source of truth for what exists in the system.
No component can die silently because the handshake protocol checks this.

## Classes

- `ComponentEntry`
- `ComponentRegistry`

## Key Methods

- `register()`
- `heartbeat()`
- `find_silent_deaths()`
- `lookup()`
- `search()`
- `list_all()`
- `get_stats()`
- `auto_register_all_components()`

## Database Tables

- `genesis_component_registry`

## Dataclasses

None

## Connects To

- `security.honesty_integrity_accountability`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
