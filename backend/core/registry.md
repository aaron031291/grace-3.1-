# Registry

**File:** `core/registry.py`

## Overview

Component Registry - Central Component Management

Addresses Clarity Class 4 (Subsystem Activation Ambiguity):
- Component registration and discovery
- Lifecycle orchestration
- Dependency management
- Health monitoring

The registry enables:
- Centralized component tracking
- Dependency-aware startup/shutdown
- Component discovery by role/capability
- System-wide health monitoring

## Classes

- `RegistryEntry`
- `ComponentRegistry`

## Key Methods

- `register()`
- `unregister()`
- `get()`
- `get_by_name()`
- `get_by_role()`
- `get_by_capability()`
- `get_by_tag()`
- `get_active()`
- `get_all()`
- `get_system_health()`
- `get_stats()`
- `get_manifests()`
- `set_message_bus()`
- `get_component_registry()`
- `reset_registry()`

---
*Grace 3.1*
