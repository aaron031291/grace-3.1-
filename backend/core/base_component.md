# Base Component

**File:** `core/base_component.py`

## Overview

Base Component - Unified Component Abstraction

Addresses Clarity Class 1 (Structural Ambiguity):
- Consistent component definitions
- Clear lifecycle methods
- Standardized status reporting
- Trust and role tracking

All Grace components should inherit from BaseComponent.

## Classes

- `ComponentState`
- `ComponentRole`
- `ComponentManifest`
- `BaseComponent`

## Key Methods

- `to_dict()`
- `component_id()`
- `name()`
- `manifest()`
- `state()`
- `is_active()`
- `is_available()`
- `trust_level()`
- `get_status()`
- `adjust_trust()`
- `set_trusted()`
- `record_operation()`
- `get_success_rate()`
- `set_message_bus()`

---
*Grace 3.1*
