# Ambiguity

**File:** `cognitive/ambiguity.py`

## Overview

Ambiguity Accounting System for Grace.

Implements Invariant 2: Explicit Ambiguity Accounting.
Tracks what is known, inferred, assumed, and unknown.

## Classes

- `AmbiguityLevel`
- `AmbiguityEntry`
- `AmbiguityLedger`

## Key Methods

- `add_known()`
- `add_inferred()`
- `add_assumed()`
- `add_unknown()`
- `get()`
- `get_all()`
- `get_by_level()`
- `get_blocking_unknowns()`
- `get_blocking_items()`
- `has_blocking_unknowns()`
- `promote_to_known()`
- `to_dict()`
- `summary()`

## Database Tables

None

## Connects To

Self-contained

---
*Documentation for Grace 3.1*
