# Chat Intelligence Layer

**File:** `cognitive/chat_intelligence.py`

## Purpose

Bridges cognitive systems into the chat pipeline

## Overview

Chat Intelligence Layer

Wires cognitive systems into the chat pipeline:
1. Ambiguity detection - asks clarifying questions when input is vague
2. Episodic memory - learns from every conversation
3. Governance checks - validates outputs against constitutional rules
4. Oracle predictions - routes queries using ML predictions
5. Conversation memory - cross-session context persistence

This is the missing integration bridge between the rich cognitive backend
and the user-facing chat endpoints.

## Classes

- `ChatIntelligence`

## Key Methods

- `ambiguity_engine()`
- `episodic_buffer()`
- `detect_ambiguity()`
- `record_episode()`
- `check_governance()`
- `use_three_layer_reasoning()`
- `predict_query_routing()`
- `enrich_response()`
- `get_chat_intelligence()`

## Database Tables

None (no DB tables)

## Dataclasses

None

## Connects To

- `cognitive.engine`
- `cognitive.episodic_memory`
- `diagnostic_machine.interpreters`
- `llm_orchestrator.three_layer_reasoning`
- `security.honesty_integrity_accountability`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
