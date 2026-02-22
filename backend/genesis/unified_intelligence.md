# Unified Intelligence Table

**File:** `genesis/unified_intelligence.py`

## Purpose

Single source of truth aggregating intelligence from 20+ subsystems

## Overview

Unified Intelligence Table

Single source of truth that aggregates intelligence from ALL subsystems:
- Component registry health
- Healing playbook outcomes
- KPI metrics
- Trust scores
- Learning progress
- Memory mesh state
- Diagnostic signals
- Oracle predictions
- Pipeline statuses

ML/DL algorithms run ON TOP of this table to:
- Predict failures before they happen
- Optimize resource allocation
- Identify improvement opportunities
- Drive autonomous decisions

This is the "brain dashboard" — everything in one place.

## Classes

- `UnifiedIntelligenceRecord`
- `UnifiedIntelligenceEngine`
- `UnifiedIntelligenceDaemon`

## Key Methods

- `record()`
- `collect_from_registry()`
- `collect_from_kpis()`
- `collect_from_healing()`
- `collect_from_pipeline()`
- `collect_from_self_agents()`
- `collect_from_memory_mesh()`
- `collect_from_magma()`
- `collect_from_episodic_memory()`
- `collect_from_learning_memory()`
- `collect_from_genesis_keys()`
- `collect_from_documents()`
- `collect_from_llm_tracking()`
- `collect_from_handshake()`
- `collect_from_governance()`
- `collect_from_closed_loop()`
- `collect_from_three_layer_reasoning()`
- `collect_from_author_discovery()`
- `collect_from_hia()`
- `collect_from_timesense_governance()`

## Database Tables

- `unified_intelligence`

## Dataclasses

None

## Connects To

- `cognitive.author_discovery_engine`
- `cognitive.deduplication_engine`
- `cognitive.episodic_memory`
- `cognitive.healing_playbooks`
- `cognitive.learning_memory`
- `cognitive.magma.grace_magma_system`
- `cognitive.memory_mesh_cache`
- `cognitive.self_agent_ecosystem`
- `cognitive.timesense_governance`
- `cognitive.training_data_sources`
- `cognitive.unified_learning_pipeline`
- `genesis.component_registry`
- `genesis.handshake_protocol`
- `llm_orchestrator.three_layer_reasoning`
- `ml_intelligence.kpi_tracker`
- `security.governance_middleware`
- `security.honesty_integrity_accountability`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
