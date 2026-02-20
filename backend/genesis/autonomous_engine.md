# Autonomous Engine

**File:** `genesis/autonomous_engine.py`

## Overview

GRACE Autonomous Action Engine
==============================
The brain that allows GRACE to take autonomous actions.

Observes → Decides → Validates → Executes → Learns

Actions are triggered by:
- Events (file changes, errors, anomalies)
- Schedules (periodic maintenance)
- Conditions (thresholds, patterns)
- Self-improvement needs

Integrations:
- Genesis Key Service: Every action generates a tracked Genesis Key
- Mirror Self-Modeling: Actions are observed for self-improvement
- Cognitive Framework: Uses clarity framework for decision making
- Trust Scores: Actions are scored for reliability
- KPIs: Performance metrics tracked for all actions
- Version Control: All mutations are version controlled

## Classes

- `ActionType`
- `TriggerType`
- `ActionPriority`
- `ActionStatus`
- `ActionContext`
- `ActionResult`
- `AutonomousAction`
- `ActionRule`
- `AutonomousEngine`

## Key Methods

- `get_genesis_key_service()`
- `get_mirror_system()`
- `get_cognitive_engine()`
- `get_kpi_tracker()`
- `on_event()`
- `get_status()`
- `get_recent_actions()`
- `get_autonomous_engine()`

## Database Tables

None

## Connects To

- `cognitive.engine`
- `cognitive.learning_hook`
- `cognitive.mirror_self_modeling`
- `database.session`
- `genesis.adaptive_cicd`
- `genesis.cicd`
- `genesis.genesis_key_service`
- `genesis.librarian_pipeline`
- `models.genesis_key_models`

---
*Documentation for Grace 3.1*
