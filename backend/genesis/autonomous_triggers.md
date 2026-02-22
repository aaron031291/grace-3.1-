# Autonomous Triggers

**File:** `genesis/autonomous_triggers.py`

## Overview

Genesis Key Autonomous Trigger Pipeline

Genesis Keys are the CENTRAL TRIGGER for all autonomous actions.

Every Genesis Key creation can trigger:
1. Autonomous learning (study new files)
2. Recursive practice loops (mirror → study → practice)
3. Predictive context loading (prefetch related topics)
4. Memory mesh integration (store high-trust patterns)

Architecture:
- Trigger Pipeline Checks Type
  ↓
- Spawns Appropriate Autonomous Actions
  ↓
- Results Create New Genesis Keys
  ↓
- RECURSIVE LOOP if needed

## Classes

- `GenesisTriggerPipeline`

## Key Methods

- `set_orchestrator()`
- `on_genesis_key_created()`
- `get_status()`
- `get_genesis_trigger_pipeline()`

## Database Tables

None

## Connects To

- `cognitive.autonomous_healing_system`
- `cognitive.learning_subagent_system`
- `cognitive.mirror_self_modeling`
- `database.session`
- `llm_orchestrator.llm_orchestrator`
- `models.genesis_key_models`

---
*Documentation for Grace 3.1*
