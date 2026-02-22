# Code Agent Playbooks

**File:** `agent/code_playbooks.py`

## Purpose

Tracks and stores successful coding configurations

## Overview

Code Agent Playbooks — Successful Configuration Tracking

The coding agent tracks every task it executes and stores successful
configurations as playbooks. When a similar task comes in, it consults
its playbook library first.

Playbooks capture:
- Task type (write/fix/refactor/test/debug)
- File patterns affected
- Strategy used (steps taken)
- Tests that passed
- Trust score earned
- Duration and efficiency

The code agent also monitors its own systems:
- Tracks its own pass/fail rate
- Creates playbooks from every success
- Records failures with root cause
- Self-analyzes performance trends
- Asks Kimi when stuck
- Consults healing system when degraded

## Classes

- `CodePlaybook`
- `CodePlaybookManager`

## Key Methods

- `create_from_success()`
- `record_failure()`
- `find_playbook()`
- `get_agent_performance()`
- `list_playbooks()`

## Database Tables

- `code_playbooks`

## Dataclasses

None

## Connects To

- `genesis.unified_intelligence`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
