# Action Router

**File:** `diagnostic_machine/action_router.py`

## Overview

Layer 4 - Action Router: Response Execution Layer

Routes decisions to appropriate actions:
- Alert Human: Notify operators of issues
- Trigger Self-Healing: Attempt automatic fixes
- Freeze System: Halt operations for safety
- Recommend Learning: Capture patterns for improvement
- Do Nothing: System is healthy, no action needed
- Trigger CI/CD: Initiate pipeline for testing/deployment

Enhanced with Grace's cognitive systems:
- OODA Loop for structured decision-making
- Sandbox Lab for action testing
- Multi-LLM Orchestration for complex decisions
- Memory Mesh for learned procedures and episodic memory
- RAG System for knowledge retrieval
- World Model for system context understanding
- Neuro-Symbolic Reasoner for hybrid reasoning
- Genesis Keys for complete tracking
- Learning Efficiency Tracking for metrics

## Classes

- `ActionType`
- `ActionPriority`
- `ActionStatus`
- `ActionResult`
- `ActionDecision`
- `HealingAction`
- `AlertConfig`
- `CICDConfig`
- `ActionRouter`

## Key Methods

- `register_healing_function()`
- `route()`
- `to_dict()`

---
*Grace 3.1*
