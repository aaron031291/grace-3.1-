# Grace Planning Api

**File:** `api/grace_planning_api.py`

## Overview

Grace Planning API

Full planning workflow system that flows from high-level concepts
through technical decisions to IDE execution.

Planning Flow:
1. CONCEPT - Big overarching concepts, product, feature
2. QUESTIONS - Non-technical questions about how concepts work
3. TECHNICAL_STACK - Technical discussion about implementation
4. TECHNICAL_ACCEPTANCE - Accept and apply technical decisions
5. EXECUTE - Execute the plan
6. IDE_HANDOFF - Hand off to IDE for implementation

Author: Grace Autonomous System

## Classes

- `PlanningPhase`
- `ConceptStatus`
- `QuestionType`
- `TechnicalDecisionStatus`
- `ExecutionStatus`
- `PlanningConcept`
- `ConceptQuestion`
- `TechnicalStackItem`
- `TechnicalDecision`
- `ExecutionPlan`
- `IDEHandoff`
- `PlanningSession`

## Key Methods

- `generate_grace_ide_instructions()`

---
*Grace 3.1*
