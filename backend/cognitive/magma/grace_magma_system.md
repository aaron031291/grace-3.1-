# Grace Magma System

**File:** `cognitive/magma/grace_magma_system.py`

## Overview

Grace Magma System - Unified Memory Architecture

This is the single unified entry point that integrates Magma Memory
with ALL Grace systems:

Core Memory:
- MagmaMemory: Graph-based memory with 4 relation types
- RRF Fusion: Multi-source retrieval fusion
- Causal Inference: LLM-powered cause-effect reasoning

Layer Integration:
- Layer 1: Message Bus connector (event-driven memory)
- Layer 2: Interpreter pattern memory (recurring issues)
- Layer 3: Judgement decision memory (precedents)
- Layer 4: Action Router memory (learned procedures)

Security Integration:
- Genesis Keys: Full provenance tracking
- Trust Scoring: Neural trust-aware retrieval
- Governance: Constitutional enforcement

Usage:
    from cognitive.magma.grace_magma_system import GraceMagmaSystem, get_grace_magma

    # Get singleton instance
    magma = get_grace_magma()

    # Ingest content
    magma.ingest("Learning experience about Python error handling")

    # Query memory
    results = magma.query("How do I handle errors?")

    # Get context for LLM
    context = magma.get_context("What causes timeout errors?")

    # Causal inference
    causes = magma.why("What causes database connection failures?")

    # Store a pattern from Layer 2
    magma.store_pattern("error_cluster", "Database timeout pattern")

    # Store a decision from Layer 3
    magma.store_decision("heal", "database", "Reconnect database")

    # Store a procedure from Layer 4
    magma.store_procedure("heal", "Reconnect DB", ["Stop pool", "Restart"])

## Classes

- `GraceMagmaConfig`
- `GraceMagmaSystem`

## Key Methods

- `initialize()`
- `save_state()`
- `ingest()`
- `query()`
- `get_context()`
- `why()`
- `explain()`
- `store_pattern()`
- `find_similar_patterns()`
- `store_decision()`
- `find_precedents()`
- `record_decision_outcome()`
- `store_procedure()`
- `find_procedures()`
- `get_best_procedure()`
- `graphs()`
- `semantic_graph()`
- `temporal_graph()`
- `causal_graph()`
- `entity_graph()`
- `get_stats()`
- `health_check()`
- `shutdown()`
- `get_grace_magma()`
- `reset_grace_magma()`

## Database Tables

None

## Connects To

- `cognitive.learning_hook`
- `cognitive.magma`
- `cognitive.magma.grace_magma_system`
- `cognitive.magma.layer_integrations`
- `cognitive.magma.persistence`

---
*Documentation for Grace 3.1*
