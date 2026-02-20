# Healing Playbooks

**File:** `cognitive/healing_playbooks.py`

## Purpose

Reusable success configurations for self-healing

## Overview

Healing Playbooks - Reusable Success Configurations

Every time self-healing succeeds, the configuration is stored as a playbook
in the database. When the same anomaly type is detected again, the system
consults existing playbooks before deciding on a healing action.

This creates a growing library of proven healing strategies that:
1. Speed up healing (skip LLM consultation if playbook exists)
2. Increase trust (proven strategies get higher trust)
3. Enable knowledge transfer (playbooks survive restarts)
4. Support auditing (full Genesis Key trail per playbook)

## Classes

- `HealingPlaybook`
- `PlaybookManager`

## Key Methods

- `create_playbook()`
- `record_failure()`
- `find_playbook()`
- `list_playbooks()`
- `get_stats()`

## Database Tables

- `healing_playbooks`

## Dataclasses

None

## Connects To

- `genesis.unified_intelligence`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
