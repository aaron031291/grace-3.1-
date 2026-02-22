# Unified Memory

**File:** `cognitive/unified_memory.py`

## Overview

Grace Unified Memory System

The single memory system that unifies everything:

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED MEMORY API                            │
│  query() / remember() / recall() / forget() / consolidate()    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│              INTELLIGENCE LAYER (Magma)                          │
│  Intent Router → Graph Retrieval → RRF Fusion → Causal Inference│
│  Semantic Graph │ Temporal Graph │ Causal Graph │ Entity Graph  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│              MEMORY TYPES                                        │
│  Episodic (what happened) │ Procedural (how to do things)       │
│  Semantic (facts/knowledge) │ Learning (trust-scored examples)  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│              PERSISTENCE LAYER (Memory Mesh)                     │
│  SQLAlchemy DB │ Magma Graph Persistence │ Snapshots             │
│  Cache (LRU) │ Metrics │ Genesis Chains                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│              LIFECYCLE                                            │
│  Consolidation (short→long term) │ Forgetting Curve (decay)     │
│  Associative Recall │ Memory Pressure Management                 │
└─────────────────────────────────────────────────────────────────┘

This replaces calling Memory Mesh OR Magma separately.
One system. One API. Every memory type. Full lifecycle.

## Classes

- `MemoryType`
- `MemoryStrength`
- `Memory`
- `AssociativeRecallEngine`
- `ConsolidationEngine`
- `UnifiedMemory`

## Key Methods

- `current_retention()`
- `effective_score()`
- `reinforce()`
- `to_dict()`
- `record_co_access()`
- `get_associations()`
- `consolidate()`
- `get_stats()`
- `remember()`
- `recall()`
- `forget()`
- `reinforce()`
- `get_working_memory()`
- `add_to_working_memory()`
- `clear_working_memory()`
- `run_consolidation()`
- `start_consolidation_loop()`
- `stop_consolidation_loop()`
- `remember_episode()`
- `remember_procedure()`
- `remember_fact()`
- `remember_cause()`
- `learn()`
- `get_stats()`
- `get_dashboard()`

## Database Tables

None

## Connects To

- `cognitive.learning_hook`
- `cognitive.magma`

---
*Documentation for Grace 3.1*
