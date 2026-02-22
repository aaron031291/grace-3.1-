# Reasoning Router

**File:** `llm_orchestrator/reasoning_router.py`

## Purpose

Tiered intelligence allocation T0/T1/T2/T3

## Overview

Reasoning Router — Tiered Intelligence Allocation

Automatically classifies every incoming request into the right reasoning
tier so the system is fast when it can be and deep when it needs to be.

Tier 0 — INSTANT (< 1s):
  Greetings, thanks, simple lookups, cache hits.
  No LLM call at all. Direct response or retrieval only.

Tier 1 — STANDARD (3-8s):
  Normal questions answerable from knowledge base.
  Single model + RAG. This is the default 80% path.

Tier 2 — CONSENSUS (10-30s):
  Complex or ambiguous queries where a single model might hallucinate.
  Layer 1 only (2+ models in parallel), pick the consensus.

Tier 3 — DEEP REASONING (30-180s):
  High-stakes decisions, contradictions detected, explicit user request,
  code changes to production, self-healing above Level 4.
  Full 3-layer pipeline: L1 parallel → L2 synthesis → L3 Grace verify.

Classification signals:
- Query length and complexity
- Ambiguity score from ChatIntelligence
- Confidence from initial RAG retrieval
- Action risk level (read-only vs write vs delete)
- User explicit request ("think deeply", "analyze carefully")
- Contradiction detection between sources
- Self-* agent requesting code/config changes

## Classes

- `ReasoningTier`
- `RoutingDecision`
- `ReasoningRouter`

## Key Methods

- `tier_name()`
- `classify()`
- `classify_self_agent_action()`
- `get_stats()`
- `get_reasoning_router()`

## Database Tables

None (no DB tables)

## Dataclasses

- `RoutingDecision`

## Connects To

- `cognitive.learning_hook`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
