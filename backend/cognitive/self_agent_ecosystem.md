# Self-Agent Ecosystem

**File:** `cognitive/self_agent_ecosystem.py`

## Purpose

6 autonomous agents with micro-DB tables in a closed-loop improvement cycle

## Overview

Self-* Agent Ecosystem

Six autonomous agents, each with their own micro-DB table, that form a
closed-loop self-improvement system:

1. SelfHealingAgent - Detects and fixes system issues
2. SelfMirrorAgent  - Observes and reflects on performance
3. SelfModelAgent   - Builds behavioral models from data
4. SelfLearnerAgent - Studies training data and improves skills
5. CodeAgent        - Writes and fixes code autonomously
6. SelfEvolver      - Orchestrates evolution across all agents

Each agent:
- Has its own micro-DB table logging attempts, passes, failures
- Can self-analyze its own performance via KPIs/trust scores
- Can ask Kimi (LLM) "why am I at X% efficiency?"
- Can access training data and ingestion pipeline
- Can trigger self-healing when degraded
- Reports to the closed-loop so all agents help each other

The closed loop:
  Mirror observes -> Model analyzes -> Healer fixes -> Learner studies ->
  Code Agent implements -> Evolver scales -> Mirror observes again...

When all agents reach 100% KPI, Evolver switches to scaling mode.

## Classes

- `SelfHealingLog`
- `SelfMirrorLog`
- `SelfModelLog`
- `SelfLearnerLog`
- `CodeAgentLog`
- `SelfEvolverLog`
- `BaseSelfAgent`
- `SelfHealingAgent`
- `SelfMirrorAgent`
- `SelfModelAgent`
- `SelfLearnerAgent`
- `CodeAgentSelf`
- `SelfEvolverAgent`
- `ClosedLoopOrchestrator`

## Key Methods

- `log_attempt()`
- `get_pass_rate()`
- `get_recent_failures()`
- `get_kpi_score()`
- `ask_kimi_why_low()`
- `self_analyze()`
- `execute_heal()`
- `execute_observation()`
- `execute_study()`
- `start()`
- `stop()`
- `run_cycle()`
- `get_status()`
- `get_closed_loop()`

## Database Tables

- `self_healing_log`
- `self_mirror_log`
- `self_model_log`
- `self_learner_log`
- `code_agent_log`
- `self_evolver_log`

## Dataclasses

None

## Connects To

- `cognitive.active_learning_system`
- `cognitive.autonomous_healing_system`
- `cognitive.autonomous_sandbox_lab`
- `cognitive.learning_hook`
- `cognitive.mirror_self_modeling`
- `cognitive.timesense_governance`
- `security.honesty_integrity_accountability`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
