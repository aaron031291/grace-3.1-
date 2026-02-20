# Governance Enforcement Middleware

**File:** `security/governance_middleware.py`

## Purpose

Runtime constitutional rule enforcement on AI outputs

## Overview

Governance Enforcement Middleware

Runtime enforcement of constitutional rules and governance policies
on all LLM outputs before they reach the user.

Integrates with:
- Constitutional DNA (immutable rules)
- Policy Engine (runtime-configurable)
- Security logging (audit trail)
- Trust system (autonomy tiers)

## Classes

- `GovernanceEnforcementMiddleware`
- `OutputSafetyValidator`
- `AuditTrailManager`

## Key Methods

- `get_stats()`
- `validate()`
- `record()`
- `get_recent()`
- `get_violation_summary()`
- `get_audit_trail_manager()`

## Database Tables

None (no DB tables)

## Dataclasses

None

## Connects To

- `security.logging`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
